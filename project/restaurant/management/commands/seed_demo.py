"""Seed demo data for FourSeason recommendation system.

Creates:
- Tags for existing menu items
- Demo users (customers) with overlapping orders
- Orders with various items (to generate recommendation signals)
- Reviews with ratings

Usage:
    python manage.py seed_demo
"""

import random
import time
from decimal import Decimal
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import User
from restaurant.models import (
    Category,
    MenuItem,
    Review,
    TableOrder,
    OrderItem,
)


_order_counter = 1000


def _next_order_number():
    """Generate unique order number using incrementing counter."""
    global _order_counter
    _order_counter += 1
    return f"TB{int(time.time())}{_order_counter:04d}"


class Command(BaseCommand):
    help = "Seed demo data for recommendation system"

    def add_arguments(self, parser):
        parser.add_argument(
            '--users', type=int, default=25,
            help='Number of additional demo users (default: 25)'
        )
        parser.add_argument(
            '--reset', action='store_true',
            help='Clear all existing demo data before seeding'
        )

    def handle(self, *args, **options):
        num_users = options['users']
        reset = options['reset']

        self.stdout.write("=" * 60)
        self.stdout.write("Seeding demo data for FourSeason")
        self.stdout.write("=" * 60)

        if reset:
            self._reset_data()

        self._seed_tags()
        self._seed_users(num_users)
        self._seed_orders()
        self._seed_reviews()
        self._seed_views()

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Seed completed!"))
        self.stdout.write("")
        self._print_summary()

    def _reset_data(self):
        self.stdout.write("\n[RESET] Clearing existing demo data...")
        Review.objects.all().delete()
        OrderItem.objects.all().delete()
        TableOrder.objects.all().delete()
        User.objects.filter(role='customer').exclude(
            username__in=['admin', 'quanglee', 'customer1', 'customer2',
                          'customer3', 'customer4', 'customer5', 'test123']
        ).delete()
        for item in MenuItem.objects.all():
            item.tags = ""
            item.views_count = 0
            item.save()
        self.stdout.write("  -> Cleared all orders, reviews, reset tags/views")

    def _seed_tags(self):
        self.stdout.write("\n[1/5] Adding tags to menu items...")

        tag_map = {
            "Nước mía": "đồ uống,nước ép,giải khát",
            "Chè ba màu": "tráng miệng,chè,miền Nam",
            "Nem nướng Nha Trang": "khai vị,nướng,hải sản,miền Trung",
            "Bánh canh ghẹ": "món chính,hải sản,bún,miền Nam",
            "Bánh mì thịt nướng": "khai vị,nướng,bánh mì,đường phố",
            "Cơm gà Hội An": "món chính,cơm,gà,miền Trung",
            "Cà phê sữa đá": "đồ uống,cà phê,giải khát,việt nam",
            "Sinh tố bơ": "đồ uống,sinh tố,trái cây,healthy",
            "Chè đậu trắng hạt sen": "tráng miệng,chè,healthy,miền Bắc",
            "Bánh xèo miền Trung": "khai vị,nướng,bánh,miền Trung",
            "Cơm tấm sườn bì": "món chính,cơm,sườn,miền Nam",
            "Gỏi cuốn tôm thịt": "khai vị,gỏi,tôm,healthy",
            "Bún chả Hà Nội": "món chính,bún,thịt nướng,miền Bắc",
            "Phở bò truyền thống": "món chính,phở,bò,miền Bắc",
        }

        count = 0
        for item in MenuItem.objects.all():
            if item.name in tag_map:
                item.tags = tag_map[item.name]
                item.save(update_fields=["tags"])
                count += 1
                self.stdout.write(f"  + {item.name}: {item.tags}")

        self.stdout.write(self.style.SUCCESS(f"  -> Updated {count} items with tags"))

    def _seed_users(self, num_users):
        self.stdout.write(f"\n[2/5] Creating {num_users} demo users...")

        # Create users with different taste profiles
        taste_profiles = [
            # (username_prefix, preferred_categories, preferred_tags)
            ("foodie", ["Món chính", "Khai vị"], "nướng,cơm,bún"),
            ("healthy", ["Khai vị", "Tráng miệng"], "healthy,gỏi,chè"),
            ("drinker", ["Đồ uống"], "đồ uống,cà phê,sinh tố"),
            ("foodlover", ["Món chính", "Đồ uống"], "bò,phở,cơm"),
            ("snack_lover", ["Khai vị", "Tráng miệng"], "bánh,nướng,chè"),
        ]

        created = 0
        for i in range(num_users):
            prefix = taste_profiles[i % len(taste_profiles)][0]
            username = f"{prefix}_{i+1:02d}"

            user, was_created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "role": "customer",
                    "first_name": f"User {i+1}",
                    "last_name": prefix.capitalize(),
                },
            )
            if was_created:
                user.set_password("Demo12345")
                user.save()
                created += 1

        self.stdout.write(self.style.SUCCESS(f"  -> Created {created} new users"))

    def _seed_orders(self):
        self.stdout.write("\n[3/5] Creating demo orders with overlapping items...")

        users = list(User.objects.filter(role="customer"))
        items = list(MenuItem.objects.filter(is_available=True))

        if not users or not items:
            self.stdout.write(self.style.WARNING("  -> Skipped: no users or items"))
            return

        order_count = 0
        now = timezone.now()

        # Define item groups for creating overlap
        # Group A: items 0-6 (grilled + seafood + mains)
        # Group B: items 4-10 (mains + snacks + desserts)
        # Group C: items 7-13 (drinks + healthy + noodles)
        # Group D: items 0-3 + 7-10 (mixed)

        order_scenarios = [
            # Each tuple: (user_indices, item_indices_per_order)
            # Create multiple orders per user with overlapping items
            ([0, 1, 2, 3], [0, 1, 2, 3, 4]),      # Users 0-3 share items 0-4
            ([0, 1, 4, 5], [0, 1, 2, 3, 4, 5]),   # Users 0,1,4,5 share items 0-5
            ([2, 3, 6, 7], [2, 3, 4, 5, 6]),      # Users 2,3,6,7 share items 2-6
            ([4, 5, 8, 9], [4, 5, 6, 7, 8]),      # Users 4,5,8,9 share items 4-8
            ([6, 7, 10, 11], [7, 8, 9, 10]),      # Users 6,7,10,11 share items 7-10
            ([8, 9, 12, 13], [9, 10, 11, 12]),    # Users 8,9,12,13 share items 9-12
            ([10, 11, 14, 15], [10, 11, 12, 13]), # Users 10,11,14,15 share items 10-13
            ([12, 13, 16, 17], [0, 1, 8, 9]),     # Users 12,13,16,17 share items 0,1,8,9
            ([14, 15, 18, 19], [3, 4, 10, 11]),   # Users 14,15,18,19 share items 3,4,10,11
            ([16, 17, 20, 21], [1, 2, 12, 13]),   # Users 16,17,20,21 share items 1,2,12,13
            ([18, 19, 22, 23], [0, 5, 9, 13]),    # Users 18,19,22,23 share items 0,5,9,13
            ([20, 21, 0, 1], [6, 7, 8, 9]),       # Users 20,21,0,1 share items 6-9
            ([22, 23, 2, 3], [10, 11, 12, 13]),   # Users 22,23,2,3 share items 10-13
        ]

        for user_indices, item_indices in order_scenarios:
            for ui in user_indices:
                if ui >= len(users):
                    continue
                user = users[ui]
                # Create 1-3 orders per scenario per user
                num_orders = random.randint(1, 3)
                for _ in range(num_orders):
                    order = TableOrder.objects.create(
                        customer=user,
                        order_number=_next_order_number(),
                        subtotal=Decimal("0"),
                        total_amount=Decimal("0"),
                        created_at=now - timedelta(days=random.randint(1, 14)),
                        status="completed",
                        payment_status="paid",
                    )
                    total = Decimal("0")
                    # Each order has 2-4 items from the scenario
                    order_items = random.sample(
                        item_indices,
                        min(random.randint(2, 4), len(item_indices))
                    )
                    for ii in order_items:
                        if ii >= len(items):
                            continue
                        item = items[ii]
                        qty = random.randint(1, 3)
                        OrderItem.objects.create(
                            order=order,
                            menu_item=item,
                            quantity=qty,
                            price=item.get_price,
                        )
                        total += item.get_price * qty
                    order.subtotal = total
                    order.total_amount = total
                    order.save()
                    order_count += 1

        self.stdout.write(self.style.SUCCESS(f"  -> Created {order_count} orders"))

    def _seed_reviews(self):
        self.stdout.write("\n[4/5] Creating demo reviews...")

        users = list(User.objects.filter(role="customer"))
        items = list(MenuItem.objects.filter(is_available=True))

        # Create reviews: each user reviews 3-6 items they ordered
        count = 0
        positive_comments = [
            "Rất ngon, sẽ quay lại!",
            "Món ngon đậm đà, giá hợp lý.",
            "Chất lượng ổn định, phục vụ nhanh.",
            "Đặc sản địa phương, rất đáng thử.",
            "Vị truyền thống, authentic.",
            "Healthy và ngon, phù hợp ăn kiêng.",
            "Giá rẻ, chất lượng tốt.",
            "Best dish in the menu!",
            "Sẽ order lại lần sau.",
            "Đề cử cho bạn bè.",
        ]

        neutral_comments = [
            "Bình thường, không đặc biệt.",
            "Ổn, giá hơi cao.",
            "Tạm được, cần cải thiện.",
        ]

        for user in users:
            # Get items this user ordered
            ordered_item_ids = set(
                OrderItem.objects.filter(order__customer=user)
                .values_list("menu_item_id", flat=True)
            )
            if not ordered_item_ids:
                continue

            # Review 3-6 items
            num_reviews = min(random.randint(3, 6), len(ordered_item_ids))
            review_items = random.sample(list(ordered_item_ids), num_reviews)

            for item_id in review_items:
                item = items[item_id] if item_id < len(items) else None
                if not item:
                    continue

                # 70% positive (4-5 stars), 30% neutral (3 stars)
                if random.random() < 0.7:
                    rating = random.choice([4, 5, 5, 4, 5])  # bias toward 5
                    comment = random.choice(positive_comments)
                else:
                    rating = 3
                    comment = random.choice(neutral_comments)

                review, created = Review.objects.get_or_create(
                    user=user,
                    menu_item=item,
                    defaults={"rating": rating, "comment": comment},
                )
                if created:
                    count += 1

        self.stdout.write(self.style.SUCCESS(f"  -> Created {count} reviews"))

    def _seed_views(self):
        self.stdout.write("\n[5/5] Adding view counts to menu items...")

        view_map = {
            "Phở bò truyền thống": 250,
            "Bún chả Hà Nội": 180,
            "Cơm tấm sườn bì": 150,
            "Bánh mì thịt nướng": 120,
            "Cơm gà Hội An": 100,
            "Bánh xèo miền Trung": 85,
            "Gỏi cuốn tôm thịt": 70,
            "Nem nướng Nha Trang": 65,
            "Bánh canh ghẹ": 50,
            "Cà phê sữa đá": 45,
            "Sinh tố bơ": 35,
            "Chè ba màu": 30,
            "Chè đậu trắng hạt sen": 25,
            "Nước mía": 20,
        }

        count = 0
        for item in MenuItem.objects.all():
            if item.name in view_map:
                item.views_count = view_map[item.name]
                item.save(update_fields=["views_count"])
                count += 1

        self.stdout.write(self.style.SUCCESS(f"  -> Updated {count} items with views"))

    def _print_summary(self):
        self.stdout.write("=" * 60)
        self.stdout.write("SUMMARY")
        self.stdout.write("=" * 60)
        self.stdout.write(f"  Categories:    {Category.objects.count()}")
        self.stdout.write(f"  Menu Items:    {MenuItem.objects.count()}")
        self.stdout.write(f"  Users:         {User.objects.count()}")
        self.stdout.write(f"  Orders:        {TableOrder.objects.count()}")
        self.stdout.write(f"  Order Items:   {OrderItem.objects.count()}")
        self.stdout.write(f"  Reviews:       {Review.objects.count()}")
        self.stdout.write("")
        self.stdout.write("Demo accounts (password: Demo12345):")
        for user in User.objects.filter(role="customer"):
            orders = OrderItem.objects.filter(order__customer=user).values_list(
                "menu_item_id", flat=True
            )
            reviews = Review.objects.filter(
                user=user, rating__gte=4
            ).values_list("menu_item_id", flat=True)
            liked = len(set(orders) | set(reviews))
            self.stdout.write(f"  - {user.username} ({liked} liked items)")
        self.stdout.write("")
        self.stdout.write("Test the recommendation system:")
        self.stdout.write("  1. Open http://localhost:8000/")
        self.stdout.write("  2. Login as foodie_01 (or any demo user)")
        self.stdout.write("  3. See 'Gợi Ý Cho Bạn' section on homepage")
        self.stdout.write("=" * 60)
