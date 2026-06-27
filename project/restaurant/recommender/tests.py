"""Unit tests for the FourSeason recommendation engine.

Covers:
- _parse_tags helper
- ContentBasedStrategy (category match, vegetarian, empty cases)
- CollaborativeStrategy (similar user, below threshold)
- Scorer (normalize, recent exclusion, unavailable exclusion, fallback)
- Engine integration (authenticated, anonymous, trending)
"""

from django.test import TestCase
from accounts.models import User
from restaurant.models import Category, MenuItem, Review, TableOrder, OrderItem
from restaurant.recommender.strategies import (
    ContentBasedStrategy,
    CollaborativeStrategy,
    _parse_tags,
)
from restaurant.recommender.scorer import merge
from restaurant.recommender.engine import get_recommendations, get_trending

_order_counter = 0


class ParseTagsTest(TestCase):
    """Tests for the _parse_tags helper."""

    def test_empty_string(self):
        self.assertEqual(_parse_tags(""), set())

    def test_single_tag(self):
        self.assertEqual(_parse_tags("nướng"), {"nướng"})

    def test_multiple_tags(self):
        self.assertEqual(_parse_tags("nướng,hấp,bò"), {"nướng", "hấp", "bò"})

    def test_whitespace_and_case(self):
        self.assertEqual(_parse_tags(" Nướng , HẤP "), {"nướng", "hấp"})


class FixtureMixin:
    """Shared test data for recommendation tests."""

    @classmethod
    def _create_order(cls, user, item):
        global _order_counter
        _order_counter += 1
        order = TableOrder.objects.create(
            customer=user,
            order_number=f"TB{_order_counter}",
            subtotal=item.price,
            total_amount=item.price,
        )
        OrderItem.objects.create(
            order=order,
            menu_item=item,
            quantity=1,
            price=item.price,
        )

    @classmethod
    def setUpTestData(cls):
        # Users
        cls.user_a = User.objects.create_user(
            username="user_a", password="pw", role="customer"
        )
        cls.user_b = User.objects.create_user(
            username="user_b", password="pw", role="customer"
        )
        cls.user_c = User.objects.create_user(
            username="user_c", password="pw", role="customer"
        )
        cls.user_new = User.objects.create_user(
            username="user_new", password="pw", role="customer"
        )

        # Categories
        cls.cat_grill = Category.objects.create(name="Món Nướng", slug="mon-nuong")
        cls.cat_seafood = Category.objects.create(name="Hải Sản", slug="hai-san")
        cls.cat_soup = Category.objects.create(name="Lẩu", slug="lau")

        # Menu items
        cls.item1 = MenuItem.objects.create(
            name="Bò Nướng",
            slug="bo-nuong",
            category=cls.cat_grill,
            description="Bò nướng thơm ngon",
            price=150000,
            is_available=True,
            is_featured=True,
            views_count=100,
            tags="nướng,bò",
        )
        cls.item2 = MenuItem.objects.create(
            name="Tôm Hùm Nướng",
            slug="tom-hum-nuong",
            category=cls.cat_seafood,
            description="Tôm hùng nướng mỡ hành",
            price=200000,
            is_available=True,
            views_count=80,
            tags="nướng,hải sản,tôm",
        )
        cls.item3 = MenuItem.objects.create(
            name="Lẩu Thái",
            slug="lau-thai",
            category=cls.cat_soup,
            description="Lẩu Thái cay cay",
            price=180000,
            is_available=True,
            views_count=60,
            tags="lẩu,cay,hải sản",
        )
        cls.item4 = MenuItem.objects.create(
            name="Nướng Hải Sản",
            slug="nuong-hai-san",
            category=cls.cat_seafood,
            description="Nướng hải sản tươi",
            price=170000,
            is_available=True,
            views_count=50,
            tags="nướng,hải sản",
        )
        cls.item5 = MenuItem.objects.create(
            name="Bò Lúc Lắc",
            slug="bo-luc-lac",
            category=cls.cat_grill,
            description="Bò lúc lắc kiểu Pháp",
            price=140000,
            is_available=True,
            views_count=40,
            tags="bò,xào",
        )
        cls.item6 = MenuItem.objects.create(
            name="Gà Nướng",
            slug="ga-nuong",
            category=cls.cat_grill,
            description="Gà nướng muối ớt",
            price=120000,
            is_available=True,
            views_count=30,
            tags="nướng,gà",
        )
        cls.item_unavailable = MenuItem.objects.create(
            name="Món Hết Hàng",
            slug="mon-het-hang",
            category=cls.cat_grill,
            description="Hết hàng",
            price=100000,
            is_available=False,
            views_count=10,
            tags="nướng",
        )

        # Orders
        cls._create_order(cls.user_a, cls.item1)
        cls._create_order(cls.user_a, cls.item2)
        cls._create_order(cls.user_a, cls.item4)

        cls._create_order(cls.user_b, cls.item1)
        cls._create_order(cls.user_b, cls.item2)
        cls._create_order(cls.user_b, cls.item4)
        cls._create_order(cls.user_b, cls.item3)

        cls._create_order(cls.user_c, cls.item1)

        # Reviews
        Review.objects.create(
            menu_item=cls.item1,
            user=cls.user_a,
            rating=5,
            comment="Rất ngon",
        )


class ContentBasedStrategyTest(FixtureMixin, TestCase):
    """Tests for ContentBasedStrategy."""

    def test_user_with_orders_gets_category_match(self):
        strategy = ContentBasedStrategy()
        scores = strategy.score(self.user_a)
        # user_a ordered items in cat_grill and cat_seafood
        # item5 is cat_grill (matches), item3 is cat_soup (no match)
        self.assertIn(self.item5.id, scores)
        self.assertIn(self.item3.id, scores)
        self.assertGreater(scores[self.item5.id], scores[self.item3.id])

    def test_user_vegetarian_pref(self):
        # Create a vegetarian item and have user_a order it
        veg_item = MenuItem.objects.create(
            name="Rau Xào",
            slug="rau-xao",
            category=self.cat_grill,
            description="Rau xào tỏi",
            price=50000,
            is_available=True,
            views_count=5,
            tags="xào,rau,chay",
        )
        self._create_order(self.user_a, veg_item)

        strategy = ContentBasedStrategy()
        scores = strategy.score(self.user_a)
        # The vegetarian-tagged item should now appear in scores
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
    """Tests for CollaborativeStrategy."""

    def test_similar_user_recommendation(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_a)
        # user_b shares item1, item2, item4 with user_a (3 overlap)
        # user_b also likes item3, which user_a hasn't ordered
        # So item3 should be recommended to user_a
        self.assertIn(self.item3.id, scores)

    def test_no_similar_users_returns_empty(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_c)
        # user_c only ordered item1 — overlap with anyone is 1 (< threshold 3)
        self.assertEqual(scores, {})

    def test_below_threshold_ignored(self):
        strategy = CollaborativeStrategy()
        scores = strategy.score(self.user_c)
        self.assertEqual(scores, {})


class ScorerTest(FixtureMixin, TestCase):
    """Tests for scorer.merge and get_user_recent_items."""

    def test_merge_normalizes_scores(self):
        content = {self.item5.id: 0.8, self.item3.id: 0.2}
        collaborative = {self.item3.id: 0.5, self.item6.id: 0.3}
        result = merge(
            self.user_a,
            strategies_scores=[content, collaborative],
            weights=[0.6, 0.4],
            n=6,
        )
        # All scores should be between 0 and 1
        for item, score in result:
            self.assertGreaterEqual(score, 0.0)
            self.assertLessEqual(score, 1.0)

    def test_recent_items_excluded(self):
        # item1 was ordered today by user_a — should be excluded
        content = {
            self.item1.id: 0.9,
            self.item5.id: 0.5,
            self.item6.id: 0.4,
            self.item3.id: 0.3,
        }
        result = merge(
            self.user_a,
            strategies_scores=[content],
            weights=[1.0],
            n=6,
        )
        returned_ids = [item.id for item, _ in result]
        self.assertNotIn(self.item1.id, returned_ids)

    def test_unavailable_excluded(self):
        content = {
            self.item_unavailable.id: 0.9,
            self.item5.id: 0.5,
            self.item6.id: 0.4,
            self.item3.id: 0.3,
        }
        result = merge(
            self.user_a,
            strategies_scores=[content],
            weights=[1.0],
            n=6,
        )
        returned_ids = [item.id for item, _ in result]
        self.assertNotIn(self.item_unavailable.id, returned_ids)

    def test_all_popped_returns_empty(self):
        # Only 2 items remain after popping recent — should return []
        content = {self.item5.id: 0.5, self.item6.id: 0.4}
        result = merge(
            self.user_a,
            strategies_scores=[content],
            weights=[1.0],
            n=6,
        )
        # Less than 3 items → empty list (fallback signal)
        self.assertEqual(result, [])


class EngineIntegrationTest(FixtureMixin, TestCase):
    """Tests for the high-level recommendation engine."""

    def test_authenticated_user_with_history_gets_recommendations(self):
        recs = get_recommendations(self.user_a)
        self.assertIsInstance(recs, list)
        self.assertGreater(len(recs), 0)

    def test_authenticated_user_no_history_gets_empty(self):
        recs = get_recommendations(self.user_new)
        self.assertIsInstance(recs, list)
        # user_new has no history → falls back to trending (returns items)
        # But since trending returns items, this returns non-empty per engine logic.
        # Per brief: "user_new gets []" — so engine should return [] for no history.
        # We adjust: engine returns [] when no content/collaborative and no fallback.
        # Actually, per our engine impl, no history → get_trending fallback.
        # Re-reading brief: "test_authenticated_user_no_history_gets_empty — user_new gets []"
        # This means the engine should return [] for a user with no history.
        self.assertEqual(recs, [])

    def test_anonymous_user_gets_empty(self):
        recs = get_recommendations(None)
        self.assertEqual(recs, [])

    def test_trending_returns_items(self):
        trending = get_trending()
        self.assertIsInstance(trending, list)
        self.assertGreater(len(trending), 0)
        # Should be ordered by views descending
        views = [item.views_count for item in trending]
        self.assertEqual(views, sorted(views, reverse=True))
