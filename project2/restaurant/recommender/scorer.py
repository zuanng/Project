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
