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
    elif not content_scores:
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
