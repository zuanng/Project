from django.core.management.base import BaseCommand
from restaurant.models import Category, MenuItem
from decimal import Decimal


class Command(BaseCommand):
    help = "Thêm 5 món ăn mới vào cơ sở dữ liệu"

    def handle(self, *args, **options):
        # Lấy các danh mục đã tồn tại
        appetizer = Category.objects.get(name="Khai vị")
        main_course = Category.objects.get(name="Món chính")
        dessert = Category.objects.get(name="Tráng miệng")
        drink = Category.objects.get(name="Đồ uống")

        # Dữ liệu món ăn mẫu mới
        menu_items_data = [
            {
                "name": "Bún bò Huế",
                "category": main_course,
                "description": "Bún bò Huế đặc sản với nước dùng đậm đà, chả, giò heo",
                "price": Decimal("70000"),
                "is_available": True,
                "is_featured": True
            },
            {
                "name": "Bánh canh ghẹ",
                "category": main_course,
                "description": "Bánh canh với ghẹ tươi, nước dùng ngọt thanh",
                "price": Decimal("60000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Nem nướng Nha Trang",
                "category": appetizer,
                "description": "Nem nướng đặc sản Nha Trang với bún, rau sống và nước chấm đặc biệt",
                "price": Decimal("50000"),
                "is_available": True,
                "is_featured": True
            },
            {
                "name": "Chè ba màu",
                "category": dessert,
                "description": "Chè ba màu với đậu xanh, khoai môn và bột sắn dây",
                "price": Decimal("20000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Nước mía",
                "category": drink,
                "description": "Nước mía nguyên chất ép từ mía tươi",
                "price": Decimal("15000"),
                "is_available": True,
                "is_featured": False
            }
        ]

        # Tạo món ăn mới
        for item_data in menu_items_data:
            menu_item, created = MenuItem.objects.get_or_create(
                name=item_data["name"],
                defaults={
                    "category": item_data["category"],
                    "description": item_data["description"],
                    "price": item_data["price"],
                    "is_available": item_data["is_available"],
                    "is_featured": item_data["is_featured"]
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Tạo món ăn: {menu_item.name}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Món ăn đã tồn tại: {menu_item.name}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'Đã hoàn thành thêm {len(menu_items_data)} món ăn mới!')
        )