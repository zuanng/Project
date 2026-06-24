"""High-level recommendation API for views and templates.

Thin orchestration layer over strategies + scorer. The engine chooses
which strategies to run, with what weights, and handles the trending
fallback when there is not enough signal.
"""

from restaurant.recommender.strategies import (
    ContentBasedStrategy,
    CollaborativeStrategy,
    TrendingStrategy,
)
from restaurant.recommender.scorer import merge


def get_recommendations(user, n: int = 6) -> list:
    """Return recommendations for a user.

    - Anonymous users or users with no order/review history get [].
    - Authenticated users with history get a ordered list of MenuItems.
    """
    if not user or not user.is_authenticated:
        return []

    content = ContentBasedStrategy().score(user)
    collaborative = CollaborativeStrategy().score(user)

    # No signal — return empty (no history to base recommendations on)
    if not content and not collaborative:
        return []

    merged = merge(
        user,
        strategies_scores=[content, collaborative],
        weights=[0.6, 0.4],
        n=n,
    )

    # scorer returns empty list when < 3 items remain
    if not merged:
        return []

    return [item for item, _score in merged]


def get_trending(n: int = 6) -> list:
    """Return top-N trending items (popularity fallback)."""
    strategy = TrendingStrategy()
    return strategy.score(n=n)
