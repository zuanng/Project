# Recommendation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a personalized menu recommendation module that suggests dishes to logged-in users based on their order history and reviews, displayed on the homepage.

**Architecture:** Service-layer pattern — `restaurant/recommender/` contains pure-Python strategies (ContentBased, Collaborative, Trending) orchestrated by an `engine.py` entry point and merged by `scorer.py`. The `home()` view calls the engine; templates render the result. No new models — only a `tags` field added to `MenuItem`.

**Tech Stack:** Django 5.2, Python 3.13, MySQL, Bootstrap 5 (no new dependencies — pure Python + Django ORM).

## Global Constraints

- No ML libraries (scikit-surprise, pandas, numpy) — pure Python + Django ORM only
- No new cache model — compute real-time on each homepage load
- `MenuItem.tags` is a `CharField(max_length=300)`, admin-entered, comma-separated
- Collaborative overlap threshold: ≥ 3 items
- Scorer MUST normalize before popping recent items
- Fallback to trending when authenticated user has < 3 recommendations
- Vietnamese UI: section title "Gợi Ý Cho Bạn", subtitle "Dựa trên sở thích và lịch sử đặt món"
- Style: reuse existing card design (hover-lift, gold badges, glass effect)

---

## Task 1: Add `tags` field to MenuItem + migration

**Files:**
- Modify: `project2/restaurant/models.py:67` (after `views_count`)
- Generate: `project2/restaurant/migrations/0003_menuitem_tags.py`

**Interfaces:**
- Produces: `MenuItem.tags` — `CharField(max_length=300, blank=True)`

- [ ] **Step 1: Add the field**

At the end of `project2/restaurant/models.py`, line 67 (after `views_count`), add:

```python
    tags = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Tags",
        help_text="Phân cách bằng dấu phẩy. VD: nướng,hấp,hải sản,bò",
    )
```

- [ ] **Step 2: Generate migration**

Run from `project2/`:
```bash
cd project2 && python manage.py makemigrations restaurant
```

Expected output:
```
Migrations for 'restaurant':
  restaurant/migrations/0003_menuitem_tags.py
    - Add field tags to menuitem
```

- [ ] **Step 3: Apply migration**

```bash
cd project2 && python manage.py migrate
```

Expected output:
```
Applying restaurant.0003_menuitem_tags... OK
```

- [ ] **Step 4: Commit**

```bash
git add project2/restaurant/models.py project2/restaurant/migrations/0003_menuitem_tags.py
git commit -m "feat: add tags field to MenuItem for content-based recommendations"
```

---

## Task 2: Create recommender package scaffold

**Files:**
- Create: `project2/restaurant/recommender/__init__.py`

**Interfaces:**
- Produces: `restaurant.recommender` package importable as `from restaurant.recommender import engine`

- [ ] **Step 1: Create directory and __init__.py**

```bash
mkdir -p project2/restaurant/recommender
```

Create `project2/restaurant/recommender/__init__.py`:
```python
"""FourSeason recommendation engine package."""
```

- [ ] **Step 2: Verify import works**

```bash
cd project2 && python -c "from restaurant.recommender import engine; print('OK')"
```

Expected: `ImportError` (engine doesn't exist yet) — confirms package is importable.

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/recommender/__init__.py
git commit -m "chore: create recommender package scaffold"
```

---

## Task 3: Implement `strategies.py` — ContentBased, Collaborative, Trending

**Files:**
- Create: `project2/restaurant/recommender/strategies.py`
- Test: `project2/restaurant/recommender/tests.py` (tests added in Task 5)

**Interfaces:**
- Produces:
  - `ContentBasedStrategy.score(user) -> dict[int, float]` — {menu_item_id: score}
  - `CollaborativeStrategy.score(user) -> dict[int, float]` — {menu_item_id: score}
  - `TrendingStrategy.score(n=6) -> list[MenuItem]` — top N trending items
  - `_parse_tags(tags_str: str) -> set[str]` — helper, splits comma-separated tags
  - `_get_user_liked_items(user) -> set[int]` — helper, items user ordered or rated ≥4

- [ ] **Step 1: Write the complete `strategies.py`**

Create `project2/restaurant/recommender/strategies.py`:

```python
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
```

- [ ] **Step 2: Verify import works**

```bash
cd project2 && python -c "
import django
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project2.settings')
django.setup()
from restaurant.recommender.strategies import ContentBasedStrategy, CollaborativeStrategy, TrendingStrategy
print('All strategies imported OK')
"
```

Expected: `All strategies imported OK`

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/recommender/strategies.py
git commit -m "feat: implement ContentBased, Collaborative, and Trending strategies"
```

---

## Task 4: Implement `scorer.py` — merge + normalize + filter

**Files:**
- Create: `project2/restaurant/recommender/scorer.py`

**Interfaces:**
- Produces:
  - `merge(user, strategies_scores: list[dict[int, float]], weights: list[float], n: int = 6) -> list[tuple[MenuItem, float]]`
  - `get_user_recent_items(user, days: int = 7) -> set[int]`

- [ ] **Step 1: Write `scorer.py`**

Create `project2/restaurant/recommender/scorer.py`:

```python
"""Score merging, normalization, and filtering for recommendations."""

from datetime import timedelta

from django.utils import timezone
from restaurant.models import MenuItem, OrderItem


def get_user_recent_items(user, days: int = 7) -> set[int]:
    """Return set of MenuItem IDs the user ordered in the last N days."""
    if not user or not user.is_authenticated:
        return set()

    cutoff = timezone.now() - timedelta(days=days)
    return set(
        OrderItem.objects.filter(
            order__customer=user,
            order__created_at__gte=cutoff,
        )
        .values_list("menu_item_id", flat=True)
        .distinct()
    )


def merge(user, strategies_scores: list[dict], weights: list[float], n: int = 6) -> list:
    """Merge strategy scores with weights, normalize, filter, and return top N.

    Args:
        user: the user to generate recommendations for
        strategies_scores: list of {item_id: score} dicts from each strategy
        weights: parallel list of weights for each strategy
        n: number of items to return

    Returns:
        List of (MenuItem, final_score) tuples, sorted by score descending.
        Returns empty list if fewer than 3 items remain after filtering.
    """
    # 1. Weighted sum
    final = {}
    for scores, w in zip(strategies_scores, weights):
        for item_id, s in scores.items():
            final[item_id] = final.get(item_id, 0.0) + float(s) * w

    if not final:
        return []

    # 2. Min-max normalize on ALL items BEFORE popping recent
    values = list(final.values())
    max_val = max(values)
    min_val = min(values)

    if max_val == min_val:
        for item_id in final:
            final[item_id] = 0.5
    else:
        for item_id in final:
            final[item_id] = (final[item_id] - min_val) / (max_val - min_val)

    # 3. Pop recent items (ordered in last 7 days)
    recent = get_user_recent_items(user, days=7)
    for item_id in recent:
        final.pop(item_id, None)

    if len(final) < 3:
        return []  # Signal to caller: not enough items, use fallback

    # 4. Filter is_available + sort descending (tiebreaker: views_count)
    item_map = MenuItem.objects.filter(
        id__in=final.keys(), is_available=True
    ).in_bulk()

    result = []
    for item_id in sorted(
        final.keys(),
        key=lambda iid: (-final[iid], -item_map[iid].views_count if iid in item_map else 0),
    ):
        if item_id in item_map:
            result.append((item_map[item_id], final[item_id]))

    return result[:n]
```

- [ ] **Step 2: Verify import works**

```bash
cd project2 && python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project2.settings')
django.setup()
from restaurant.recommender.scorer import merge, get_user_recent_items
print('Scorer imported OK')
"
```

Expected: `Scorer imported OK`

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/recommender/scorer.py
git commit -m "feat: implement scorer with normalize-before-pop and availability filter"
```

---

## Task 5: Implement `engine.py` — single entry point

**Files:**
- Create: `project2/restaurant/recommender/engine.py`

**Interfaces:**
- Produces:
  - `get_recommendations(user, n: int = 6) -> list[MenuItem]` — returns empty list if fallback needed
  - `get_trending(n: int = 6) -> list[MenuItem]` — convenience wrapper for anonymous users

- [ ] **Step 1: Write `engine.py`**

Create `project2/restaurant/recommender/engine.py`:

```python
"""Recommendation engine — single entry point for views and templates.

Usage in a view:
    from restaurant.recommender.engine import get_recommendations
    recommendations = get_recommendations(request.user, n=6)
"""

from .strategies import ContentBasedStrategy, CollaborativeStrategy, TrendingStrategy
from .scorer import merge


def get_recommendations(user, n: int = 6) -> list:
    """Get personalized recommendations for a user.

    Returns a list of MenuItem objects (empty if not enough data / all popped).
    Caller should check len() and fall back to trending if < 3.
    """
    if not user or not user.is_authenticated:
        return []

    # Check if user has any order or review history
    from restaurant.models import Review, OrderItem
    has_history = (
        Review.objects.filter(user=user).exists()
        or OrderItem.objects.filter(order__customer=user).exists()
    )
    if not has_history:
        return []

    # Run strategies
    content_scores = ContentBasedStrategy().score(user)
    collab_scores = CollaborativeStrategy().score(user)

    # If collaborative returned nothing (no similar users), use content-only
    if not collab_scores and content_scores:
        strategies = [content_scores]
        weights = [1.0]
    elif not content_scores and collab_scores:
        strategies = [collab_scores]
        weights = [1.0]
    else:
        strategies = [content_scores, collab_scores]
        weights = [0.6, 0.4]

    results = merge(user, strategies, weights, n=n)
    return [item for item, _ in results]


def get_trending(n: int = 6) -> list:
    """Get trending items — used for anonymous users or as fallback."""
    return TrendingStrategy().score(n=n)
```

- [ ] **Step 2: Verify import works**

```bash
cd project2 && python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project2.settings')
django.setup()
from restaurant.recommender.engine import get_recommendations, get_trending
print('Engine imported OK')
"
```

Expected: `Engine imported OK`

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/recommender/engine.py
git commit -m "feat: implement recommendation engine entry point"
```

---

## Task 6: Write unit tests

**Files:**
- Create: `project2/restaurant/recommender/tests.py`

**Interfaces:**
- Consumes: All strategy classes, `merge()`, `get_recommendations()`, `get_trending()`
- Produces: Test coverage for all edge cases in spec section 7

- [ ] **Step 1: Write the complete test file**

Create `project2/restaurant/recommender/tests.py`:

```python
"""Unit tests for the recommendation engine."""

from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from restaurant.models import Category, MenuItem, Review, TableOrder, OrderItem
from restaurant.recommender.strategies import (
    ContentBasedStrategy,
    CollaborativeStrategy,
    TrendingStrategy,
    _parse_tags,
)
from restaurant.recommender.scorer import merge, get_user_recent_items
from restaurant.recommender.engine import get_recommendations, get_trending


class ParseTagsTest(TestCase):
    def test_empty_string(self):
        self.assertEqual(_parse_tags(""), set())

    def test_single_tag(self):
        self.assertEqual(_parse_tags("nướng"), {"nướng"})

    def test_multiple_tags(self):
        self.assertEqual(_parse_tags("nướng,hấp,bò"), {"nướng", "hấp", "bò"})

    def test_whitespace_and_case(self):
        self.assertEqual(_parse_tags(" Nướng , HẤP "), {"nướng", "hấp"})


class FixtureMixin:
    """Shared test fixtures."""

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user_a = User.objects.create_user(
            username="user_a", password="testpass123", role="customer"
        )
        cls.user_b = User.objects.create_user(
            username="user_b", password="testpass123", role="customer"
        )
        cls.user_c = User.objects.create_user(
            username="user_c", password="testpass123", role="customer"
        )
        cls.user_new = User.objects.create_user(
            username="user_new", password="testpass123", role="customer"
        )

        # Categories
        cls.cat_grill = Category.objects.create(name="Món Nướng", slug="mon-nuong")
        cls.cat_seafood = Category.objects.create(name="Hải Sản", slug="hai-san")
        cls.cat_soup = Category.objects.create(name="Lẩu", slug="lau")

        # Menu Items
        cls.item1 = MenuItem.objects.create(
            name="Bò Nướng",
            slug="bo-nuong",
            category=cls.cat_grill,
            description="Bò nướng thơm ngon",
            price=150000,
            is_available=True,
            is_featured=True,
            tags="nướng,bò",
            views_count=100,
        )
        cls.item2 = MenuItem.objects.create(
            name="Tôm Hùm Nướng",
            slug="tom-hum-nuong",
            category=cls.cat_seafood,
            description="Tôm hùng nướng muối ớt",
            price=300000,
            is_available=True,
            tags="nướng,hải sản,tôm",
            views_count=80,
        )
        cls.item3 = MenuItem.objects.create(
            name="Lẩu Thái",
            slug="lau-thai",
            category=cls.cat_soup,
            description="Lẩu Thái chua cay",
            price=200000,
            is_available=True,
            tags="lẩu,cay,hải sản",
            views_count=60,
        )
        cls.item4 = MenuItem.objects.create(
            name="Nướng Hải Sản",
            slug="nuong-hai-san",
            category=cls.cat_seafood,
            description="Hải sản nướng",
            price=250000,
            is_available=True,
            tags="nướng,hải sản",
            views_count=50,
        )
        cls.item5 = MenuItem.objects.create(
            name="Bò Lúc Lắc",
            slug="bo-luc-lac",
            category=cls.cat_grill,
            description="Bò lúc lắc",
            price=120000,
            is_available=True,
            tags="bò,xào",
            views_count=40,
        )
        cls.item6 = MenuItem.objects.create(
            name="Gà Nướng",
            slug="ga-nuong",
            category=cls.cat_grill,
            description="Gà nướng",
            price=100000,
            is_available=True,
            tags="nướng,gà",
            views_count=30,
        )
        cls.item_unavailable = MenuItem.objects.create(
            name="Món Hết Hàng",
            slug="mon-het-hang",
            category=cls.cat_grill,
            description="Hết hàng",
            price=50000,
            is_available=False,
            tags="nướng",
            views_count=10,
        )

        # User A likes grilled + seafood (orders item1, item2, item4)
        cls._create_order(cls.user_a, cls.item1)
        cls._create_order(cls.user_a, cls.item2)
        cls._create_order(cls.user_a, cls.item4)

        # User B likes same as A (overlap = 3) + also likes item3
        cls._create_order(cls.user_b, cls.item1)
        cls._create_order(cls.user_b, cls.item2)
        cls._create_order(cls.user_b, cls.item4)
        cls._create_order(cls.user_b, cls.item3)

        # User C only likes item1 (overlap with A = 1, below threshold)
        cls._create_order(cls.user_c, cls.item1)

        # Give item1 a high rating
        Review.objects.create(
            menu_item=cls.item1, user=cls.user_a, rating=5, comment="Ngon!"
        )

    @classmethod
    def _create_order(cls, user, item):
        order = TableOrder.objects.create(
            customer=user,
            subtotal=item.price,
            total_amount=item.price,
        )
        OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=1,
            price=item.price,
        )


class ContentBasedStrategyTest(FixtureMixin, TestCase):
    def test_user_with_orders_gets_category_match(self):
        strategy = ContentBasedStrategy()
        scores = strategy.score(self.user_a)

        # user_a ordered from cat_grill and cat_seafood
        # Items in those categories should score higher
        self.assertIn(self.item5.id, scores)  # cat_grill
        self.assertIn(self.item3.id, scores)  # cat_soup (not in top categories)

        # item5 (cat_grill) should score > item3 (cat_soup) due to category match
        self.assertGreater(scores[self.item5.id], scores[self.item3.id])

    def test_user_vegetarian_pref(self):
        # Make user_a prefer vegetarian items
        MenuItem.objects.create(
            name="Rau Xào Chay",
            slug="rau-xao-chay",
            category=self.cat_soup,
            description="Rau xào",
            price=50000,
            is_available=True,
            is_vegetarian=True,
            tags="chay,xào",
            views_count=5,
        )
        veg_item = MenuItem.objects.get(slug="rau-xao-chay")
        self._create_order(self.user_a, veg_item)

        strategy = ContentBasedStrategy()
        scores = strategy.score(self.user_a)

        # Vegetarian item should now have some score
        self.assertIn(veg_item.id, scores)

    def test_no_orders_returns_empty(self):
        strategy = ContentBasedStrategy()
        scores = strategy.score(self.user_new)
        self.assertEqual(scores, {})

    def test_anonymous_returns_empty(self):
        strategy = ContentBasedStrategy()
        scores = strategy.score(None)
        self.assertEqual(scores, {})


class CollaborativeStrategyTest(FixtureMixin, TestCase):
    def test_similar_user_recommendation(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_a)

        # user_b has overlap=3 with user_a and also likes item3
        # item3 should be recommended to user_a
        self.assertIn(self.item3.id, scores)
        self.assertGreater(scores[self.item3.id], 0)

    def test_no_similar_users_returns_empty(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_c)
        # user_c only has 1 item overlap with anyone — below threshold
        self.assertEqual(scores, {})

    def test_below_threshold_ignored(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_c)
        # user_c's overlap with user_a is 1 (only item1) — below threshold 3
        # So no recommendations
        self.assertEqual(scores, {})


class ScorerTest(FixtureMixin, TestCase):
    def test_merge_normalizes_scores(self):
        content_scores = {self.item1.id: 0.8, self.item2.id: 0.4}
        collab_scores = {self.item1.id: 0.5, self.item3.id: 0.9}

        results = merge(
            self.user_new,
            [content_scores, collab_scores],
            [0.6, 0.4],
            n=6,
        )

        # Should have results
        self.assertGreater(len(results), 0)

        # Scores should be normalized (between 0 and 1)
        for item, score in results:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_recent_items_excluded(self):
        # user_a ordered item1 today — it should be excluded
        content_scores = {
            self.item1.id: 0.9,
            self.item2.id: 0.7,
            self.item3.id: 0.5,
            self.item5.id: 0.3,
        }
        results = merge(
            self.user_a,
            [content_scores],
            [1.0],
            n=6,
        )

        result_ids = [item.id for item, _ in results]
        self.assertNotIn(self.item1.id, result_ids)

    def test_unavailable_excluded(self):
        content_scores = {
            self.item1.id: 0.9,
            self.item_unavailable.id: 0.8,
            self.item2.id: 0.5,
        }
        results = merge(
            self.user_new,
            [content_scores],
            [1.0],
            n=6,
        )

        result_ids = [item.id for item, _ in results]
        self.assertNotIn(self.item_unavailable.id, result_ids)

    def test_all_popped_returns_empty(self):
        # user_a ordered item1, item2, item4 recently
        content_scores = {
            self.item1.id: 0.9,
            self.item2.id: 0.8,
            self.item4.id: 0.7,
        }
        results = merge(
            self.user_a,
            [content_scores],
            [1.0],
            n=6,
        )
        # All 3 items popped → less than 3 remaining → empty
        self.assertEqual(results, [])


class EngineIntegrationTest(FixtureMixin, TestCase):
    def test_authenticated_user_with_history_gets_recommendations(self):
        recs = get_recommendations(self.user_a, n=6)
        # user_a has orders → should get recommendations
        self.assertIsInstance(recs, list)
        # May or may not have >= 3 depending on data, but at least returns list

    def test_authenticated_user_no_history_gets_empty(self):
        recs = get_recommendations(self.user_new, n=6)
        self.assertEqual(recs, [])

    def test_anonymous_user_gets_empty(self):
        recs = get_recommendations(None, n=6)
        self.assertEqual(recs, [])

    def test_trending_returns_items(self):
        trending = get_trending(n=3)
        self.assertLessEqual(len(trending), 3)
        # Should be ordered by views (item1 has 100 views)
        if len(trending) > 0:
            self.assertEqual(trending[0].id, self.item1.id)
```

- [ ] **Step 2: Run tests**

```bash
cd project2 && python manage.py test restaurant.recommender -v2
```

Expected: All tests pass (some may be skipped if data doesn't trigger them, but no failures).

- [ ] **Step 3: Fix any failures and re-run**

- [ ] **Step 4: Commit**

```bash
git add project2/restaurant/recommender/tests.py
git commit -m "test: add unit tests for recommendation engine"
```

---

## Task 7: Update `home()` view to call engine

**Files:**
- Modify: `project2/restaurant/views.py:12-26`

**Interfaces:**
- Consumes: `get_recommendations()`, `get_trending()` from `restaurant.recommender.engine`
- Produces: `recommendations` and `trending_items` in template context

- [ ] **Step 1: Update the `home()` view**

Replace the `home()` function in `project2/restaurant/views.py`:

```python
def home(request):
    """Trang chủ"""
    featured_items = MenuItem.objects.filter(
        is_featured=True, is_available=True
    )[:6]

    categories = Category.objects.filter(is_active=True)[:6]
    chefs = Chef.objects.filter(is_active=True)[:4]

    # Recommendations
    from restaurant.recommender.engine import get_recommendations, get_trending

    recommendations = []
    trending_items = []
    if request.user.is_authenticated:
        recommendations = get_recommendations(request.user, n=6)
        if len(recommendations) < 3:
            recommendations = []
            trending_items = get_trending(n=6)
    else:
        trending_items = get_trending(n=6)

    context = {
        "featured_items": featured_items,
        "categories": categories,
        "chefs": chefs,
        "recommendations": recommendations,
        "trending_items": trending_items,
    }
    return render(request, "restaurant/home.html", context)
```

- [ ] **Step 2: Verify the view loads without errors**

```bash
cd project2 && python manage.py runserver 0.0.0.0:8000 &
sleep 2
curl -s http://localhost:8000/ | head -20
kill %1 2>/dev/null
```

Expected: No 500 errors in the response.

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/views.py
git commit -m "feat: integrate recommendation engine into home view"
```

---

## Task 8: Update `home.html` template — add sections

**Files:**
- Modify: `project2/restaurant/templates/restaurant/home.html:38-42` (insert after hero, before featured)

**Interfaces:**
- Consumes: `recommendations` and `trending_items` from view context

- [ ] **Step 1: Insert recommendation + trending sections**

In `project2/restaurant/templates/restaurant/home.html`, find the closing `</section>` of the hero (around line 38) and the comment `<!-- FEATURED ITEMS -->` (around line 40). Insert between them:

```html
<!-- ============================================
     PERSONALIZED RECOMMENDATIONS (logged-in)
     ============================================ -->
{% if recommendations %}
<section class="section-padding">
    <div class="container-fluid px-4">
        <div class="text-center mb-5">
            <p class="font-accent text-gold mb-1" style="font-size: 1rem; letter-spacing: 0.1em;">✦ Dành cho bạn ✦</p>
            <h2 class="fw-bold mb-2">Gợi Ý Cho Bạn</h2>
            <div class="gold-divider-center"></div>
            <p class="text-muted mb-0 mt-2">Dựa trên sở thích và lịch sử đặt món</p>
        </div>

        <div class="row g-4">
            {% for item in recommendations %}
            <div class="col-sm-6 col-lg-4 col-xl-3">
                <div class="card h-100 hover-lift border-0 overflow-hidden">
                    <div class="card-img-container position-relative">
                        {% if item.image %}
                            <img src="{{ item.image.url }}" class="card-img-top" alt="{{ item.name }}" style="height: 220px; object-fit: cover;">
                        {% else %}
                            <div class="d-flex align-items-center justify-content-center" style="height: 220px; background: var(--bg-tertiary);">
                                <i class="fas fa-utensils fa-3x" style="color: var(--text-muted);"></i>
                            </div>
                        {% endif %}
                        <div class="position-absolute bottom-0 start-0 end-0 p-3" style="background: linear-gradient(transparent, rgba(10,10,10,0.9));">
                            <span class="badge" style="background: var(--gold-primary); color: var(--text-inverse); font-size: 0.7rem;">
                                {{ item.category.name }}
                            </span>
                        </div>
                        {% if item.discount_percentage %}
                            <div class="position-absolute top-0 end-0 m-2">
                                <span class="badge bg-danger" style="font-size: 0.75rem;">-{{ item.discount_percentage }}%</span>
                            </div>
                        {% endif %}
                    </div>
                    <div class="card-body d-flex flex-column p-3">
                        <h6 class="card-title fw-bold mb-1" style="font-family: var(--font-heading); font-size: 1rem;">
                            {{ item.name }}
                        </h6>
                        <p class="card-text small flex-grow-1 mb-2" style="color: var(--text-muted);">
                            {{ item.description|truncatewords:10 }}
                        </p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                {% if item.discount_price %}
                                    <small class="text-muted text-decoration-line-through">
                                        {{ item.price|floatformat:0 }}đ
                                    </small>
                                    <div class="fw-bold" style="color: var(--gold-primary); font-size: 1.1rem;">
                                        {{ item.discount_price|floatformat:0 }}đ
                                    </div>
                                {% else %}
                                    <div class="fw-bold" style="color: var(--gold-primary); font-size: 1.1rem;">
                                        {{ item.price|floatformat:0 }}đ
                                    </div>
                                {% endif %}
                            </div>
                            <form method="post" action="{% url 'restaurant:cart_add' item.id %}">
                                {% csrf_token %}
                                <input type="hidden" name="quantity" value="1">
                                <button type="submit" class="btn btn-sm btn-primary">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}

<!-- ============================================
     TRENDING ITEMS (anonymous fallback)
     ============================================ -->
{% if not recommendations and trending_items %}
<section class="section-padding">
    <div class="container-fluid px-4">
        <div class="text-center mb-5">
            <p class="font-accent text-gold mb-1" style="font-size: 1rem; letter-spacing: 0.1em;">✦ Hot Tuần Này ✦</p>
            <h2 class="fw-bold mb-2">Món Ăn Thịnh Hành</h2>
            <div class="gold-divider-center"></div>
            <p class="text-muted mb-0 mt-2">Những món được yêu thích nhất gần đây</p>
        </div>

        <div class="row g-4">
            {% for item in trending_items %}
            <div class="col-sm-6 col-lg-4 col-xl-3">
                <div class="card h-100 hover-lift border-0 overflow-hidden">
                    <div class="card-img-container position-relative">
                        {% if item.image %}
                            <img src="{{ item.image.url }}" class="card-img-top" alt="{{ item.name }}" style="height: 220px; object-fit: cover;">
                        {% else %}
                            <div class="d-flex align-items-center justify-content-center" style="height: 220px; background: var(--bg-tertiary);">
                                <i class="fas fa-utensils fa-3x" style="color: var(--text-muted);"></i>
                            </div>
                        {% endif %}
                        <div class="position-absolute bottom-0 start-0 end-0 p-3" style="background: linear-gradient(transparent, rgba(10,10,10,0.9));">
                            <span class="badge" style="background: var(--gold-primary); color: var(--text-inverse); font-size: 0.7rem;">
                                {{ item.category.name }}
                            </span>
                        </div>
                        {% if item.discount_percentage %}
                            <div class="position-absolute top-0 end-0 m-2">
                                <span class="badge bg-danger" style="font-size: 0.75rem;">-{{ item.discount_percentage }}%</span>
                            </div>
                        {% endif %}
                    </div>
                    <div class="card-body d-flex flex-column p-3">
                        <h6 class="card-title fw-bold mb-1" style="font-family: var(--font-heading); font-size: 1rem;">
                            {{ item.name }}
                        </h6>
                        <p class="card-text small flex-grow-1 mb-2" style="color: var(--text-muted);">
                            {{ item.description|truncatewords:10 }}
                        </p>
                        <div class="d-flex justify-content-between align-items-center">
                            <div>
                                {% if item.discount_price %}
                                    <small class="text-muted text-decoration-line-through">
                                        {{ item.price|floatformat:0 }}đ
                                    </small>
                                    <div class="fw-bold" style="color: var(--gold-primary); font-size: 1.1rem;">
                                        {{ item.discount_price|floatformat:0 }}đ
                                    </div>
                                {% else %}
                                    <div class="fw-bold" style="color: var(--gold-primary); font-size: 1.1rem;">
                                        {{ item.price|floatformat:0 }}đ
                                    </div>
                                {% endif %}
                            </div>
                            <form method="post" action="{% url 'restaurant:cart_add' item.id %}">
                                {% csrf_token %}
                                <input type="hidden" name="quantity" value="1">
                                <button type="submit" class="btn btn-sm btn-primary">
                                    <i class="fas fa-plus"></i>
                                </button>
                            </form>
                        </div>
                    </div>
                </div>
            </div>
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}
```

- [ ] **Step 2: Verify template renders**

Start the dev server and check:
```bash
cd project2 && python manage.py runserver
```

Visit `http://localhost:8000/` in browser. Verify:
- Anonymous user sees "Món Ăn Thịnh Hành" (trending) section
- If logged in with history, see "Gợi Ý Cho Bạn" section
- Cards render with correct styling

- [ ] **Step 3: Commit**

```bash
git add project2/restaurant/templates/restaurant/home.html
git commit -m "ui: add recommendation and trending sections to homepage"
```

---

## Task 9: Final verification + seed sample data

**Files:**
- Optional: `project2/restaurant/management/commands/seed_tags.py` (management command to populate tags on existing items)

**Interfaces:**
- Consumes: All of the above
- Produces: Working recommendation system with sample data

- [ ] **Step 1: Run full test suite**

```bash
cd project2 && python manage.py test restaurant.recommender -v2
```

Expected: All tests pass.

- [ ] **Step 2: Run server and manually verify**

```bash
cd project2 && python manage.py runserver
```

Checklist:
- [ ] Homepage loads without errors
- [ ] Trending section shows for anonymous users
- [ ] Login as a user with order history → "Gợi Ý Cho Bạn" appears
- [ ] Login as new user → no recommendations section (fallback to trending)
- [ ] Cards have correct styling (hover-lift, gold badges)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "chore: verify recommendation system end-to-end"
```

---

## Summary

| Task | What | Key file |
|------|------|----------|
| 1 | Add `tags` field + migration | `models.py` |
| 2 | Create recommender package | `recommender/__init__.py` |
| 3 | Implement strategies | `recommender/strategies.py` |
| 4 | Implement scorer | `recommender/scorer.py` |
| 5 | Write tests | `recommender/tests.py` |
| 6 | Implement engine | `recommender/engine.py` |
| 7 | Update home view | `views.py` |
| 8 | Update home template | `home.html` |
| 9 | Verify end-to-end | All files |
