"""Recommendation strategies: ContentBased, Collaborative, Trending.

Pure Python — no Django request objects passed in. Strategies accept a User
instance (or None for anonymous) and return scores or item lists. This makes
them independently testable.
"""

from collections import Counter
from django.db.models import Avg, Count
from restaurant.models import MenuItem, Review, TableOrder, OrderItem


# ============================================================
# Helpers
# ============================================================

def _parse_tags(tags_str: str) -> set[str]:
    """Parse comma-separated tag string into a set of lowercase tags."""
    if not tags_str:
        return set()
    return {t.strip().lower() for t in tags_str.split(",") if t.strip()}


def _get_user_liked_items(user) -> set[int]:
    """Return set of MenuItem IDs the user ordered or rated >= 4."""
    if not user or not user.is_authenticated:
        return set()

    ordered = set(
        OrderItem.objects.filter(order__customer=user)
        .values_list("menu_item_id", flat=True)
    )
    reviewed_high = set(
        Review.objects.filter(user=user, rating__gte=4)
        .values_list("menu_item_id", flat=True)
    )
    return ordered | reviewed_high


def _get_user_top_categories(user, top_n: int = 3) -> list[int]:
    """Return top N category IDs from user's liked items."""
    liked = _get_user_liked_items(user)
    if not liked:
        return []

    category_counts = Counter(
        MenuItem.objects.filter(id__in=liked)
        .values_list("category_id", flat=True)
    )
    return [cat_id for cat_id, _ in category_counts.most_common(top_n)]


def _get_user_top_tags(user) -> set[str]:
    """Return set of tags appearing in user's liked items."""
    liked = _get_user_liked_items(user)
    if not liked:
        return set()

    tags = set()
    for item in MenuItem.objects.filter(id__in=liked):
        tags |= _parse_tags(item.tags)
    return tags


# ============================================================
# Content-Based Strategy
# ============================================================

class ContentBasedStrategy:
    """Score items by similarity to user's preference profile.

    Score = category_match * 0.4 + tag_match * 0.3 + rating_boost * 0.2 + discount_boost * 0.1
    """

    def score(self, user) -> dict[int, float]:
        if not user or not user.is_authenticated:
            return {}

        top_categories = _get_user_top_categories(user)
        top_tags = _get_user_top_tags(user)

        if not top_categories and not top_tags:
            return {}

        items = MenuItem.objects.filter(is_available=True).annotate(
            avg_rating=Avg("reviews__rating")
        )

        scores = {}
        for item in items:
            # category_match
            category_match = 1.0 if item.category_id in top_categories else 0.0

            # tag_match (Jaccard)
            item_tags = _parse_tags(item.tags)
            if item_tags and top_tags:
                intersection = len(item_tags & top_tags)
                union = len(item_tags | top_tags)
                tag_match = intersection / union if union > 0 else 0.0
            else:
                tag_match = 0.0

            # rating_boost
            avg = item.avg_rating or 0.0
            rating_boost = float(avg) / 5.0

            # discount_boost
            discount_boost = (
                0.1
                if item.discount_price and item.discount_price < item.price
                else 0.0
            )

            score = (
                category_match * 0.4
                + tag_match * 0.3
                + rating_boost * 0.2
                + discount_boost * 0.1
            )
            scores[item.id] = score

        return scores


# ============================================================
# Collaborative Strategy
# ============================================================

class CollaborativeStrategy:
    """Score items by what similar users liked.

    1. Find user's liked items.
    2. Find other users with >= 3 overlap (Jaccard similarity).
    3. Recommend items those similar users liked that target user hasn't.
    """

    OVERLAP_THRESHOLD = 3

    def score(self, user) -> dict[int, float]:
        if not user or not user.is_authenticated:
            return {}

        user_liked = _get_user_liked_items(user)
        if not user_liked:
            return {}

        # Find candidate users who have liked items in common
        candidate_users = (
            Review.objects.filter(menu_item_id__in=user_liked, rating__gte=4)
            .exclude(user=user)
            .values_list("user_id", flat=True)
            .distinct()
        )
        # Also include users who ordered the same items
        candidate_users = set(candidate_users)
        candidate_users |= set(
            OrderItem.objects.filter(
                menu_item_id__in=user_liked, order__customer__isnull=False
            )
            .exclude(order__customer=user)
            .values_list("order__customer_id", flat=True)
            .distinct()
        )

        scores = {}
        for other_id in candidate_users:
            other_liked = _get_user_liked_items_from_ids(other_id)
            if not other_liked:
                continue

            overlap = len(user_liked & other_liked)
            if overlap < self.OVERLAP_THRESHOLD:
                continue

            union = len(user_liked | other_liked)
            jaccard = overlap / union if union > 0 else 0.0

            # Items the other user liked but target user hasn't
            new_items = other_liked - user_liked
            for item_id in new_items:
                scores[item_id] = scores.get(item_id, 0.0) + jaccard

        return scores


def _get_user_liked_items_from_ids(user_id: int) -> set[int]:
    """Same as _get_user_liked_items but accepts a raw user ID (no DB hit for User)."""
    ordered = set(
        OrderItem.objects.filter(order__customer_id=user_id)
        .values_list("menu_item_id", flat=True)
    )
    reviewed_high = set(
        Review.objects.filter(user_id=user_id, rating__gte=4)
        .values_list("menu_item_id", flat=True)
    )
    return ordered | reviewed_high


# ============================================================
# Trending Strategy (Fallback)
# ============================================================

class TrendingStrategy:
    """Score items by popularity — views, rating, recency.

    Score = views_normalized * 0.4 + rating_normalized * 0.4 + recency * 0.2
    """

    def score(self, n: int = 6) -> list[MenuItem]:
        from django.utils import timezone
        from datetime import timedelta

        items = MenuItem.objects.filter(is_available=True).annotate(
            avg_rating=Avg("reviews__rating")
        )

        if not items:
            return []

        max_views = max((i.views_count for i in items), default=1)
        if max_views == 0:
            max_views = 1

        now = timezone.now()

        def trending_score(item):
            views_norm = item.views_count / max_views
            rating_norm = float(item.avg_rating or 0) / 5.0

            days_old = (now - item.created_at).days
            if days_old <= 7:
                recency = 1.0
            elif days_old <= 30:
                recency = 0.5
            else:
                recency = 0.0

            return views_norm * 0.4 + rating_norm * 0.4 + recency * 0.2

        scored = [(item, trending_score(item)) for item in items]
        scored.sort(key=lambda x: (-x[1], -x[0].views_count))

        return [item for item, _ in scored[:n]]
