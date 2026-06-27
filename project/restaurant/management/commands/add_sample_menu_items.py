from django.core.management.base import BaseCommand
from restaurant.models import Category, MenuItem
from decimal import Decimal
import os
from django.core.files import File


class Command(BaseCommand):
    help = "Thêm 10 món ăn mẫu vào cơ sở dữ liệu"

    def handle(self, *args, **options):
        # Tạo các danh mục nếu chưa tồn tại
        appetizer, created = Category.objects.get_or_create(
            name="Khai vị",
            defaults={"description": "Các món khai vị ngon miệng"}
        )
        main_course, created = Category.objects.get_or_create(
            name="Món chính",
            defaults={"description": "Các món chính đặc sắc"}
        )
        dessert, created = Category.objects.get_or_create(
            name="Tráng miệng",
            defaults={"description": "Các món tráng miệng hấp dẫn"}
        )
        drink, created = Category.objects.get_or_create(
            name="Đồ uống",
            defaults={"description": "Các loại nước giải khát"}
        )

        # Dữ liệu món ăn mẫu
        menu_items_data = [
            {
                "name": "Phở bò truyền thống",
                "category": main_course,
                "description": "Phở bò truyền thống với nước dùng thơm ngon, thịt bò mềm",
                "price": Decimal("75000"),
                "is_available": True,
                "is_featured": True
            },
            {
                "name": "Bún chả Hà Nội",
                "category": main_course,
                "description": "Bún chả đặc sản Hà Nội với chả nướng thơm phức và nước chấm đặc biệt",
                "price": Decimal("65000"),
                "is_available": True,
                "is_featured": True
            },
            {
                "name": "Gỏi cuốn tôm thịt",
                "category": appetizer,
                "description": "Gỏi cuốn tươi ngon với tôm và thịt heo, ăn kèm tương đặc biệt",
                "price": Decimal("45000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Cơm tấm sườn bì",
                "category": main_course,
                "description": "Cơm tấm với sườn nướng, bì và trứng ốp la",
                "price": Decimal("55000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Bánh xèo miền Trung",
                "category": appetizer,
                "description": "Bánh xèo giòn rụm với nhân tôm, thịt và giá đỗ",
                "price": Decimal("40000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Chè đậu trắng hạt sen",
                "category": dessert,
                "description": "Chè đậu trắng nấu nhừ cùng hạt sen thơm ngon, bổ dưỡng",
                "price": Decimal("25000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Sinh tố bơ",
                "category": drink,
                "description": "Sinh tố bơ tươi nguyên chất, béo ngậy và thơm ngon",
                "price": Decimal("35000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Cà phê sữa đá",
                "category": drink,
                "description": "Cà phê phin truyền thống với sữa đặc, đậm đà hương vị Việt",
                "price": Decimal("30000"),
                "is_available": True,
                "is_featured": False
            },
            {
                "name": "Cơm gà Hội An",
                "category": main_course,
                "description": "Cơm gà đặc sản Hội An với gà ta luộc mềm, thơm ngon",
                "price": Decimal("60000"),
                "is_available": True,
                "is_featured": True
            },
            {
                "name": "Bánh mì thịt nướng",
                "category": appetizer,
                "description": "Bánh mì giòn rụm với thịt nướng đậm đà, rau sống và pate",
                "price": Decimal("35000"),
                "is_available": True,
                "is_featured": False
            }
        ]

        # Tạo món ăn mẫu
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
            self.style.SUCCESS(f'Đã hoàn thành thêm {len(menu_items_data)} món ăn mẫu!')
        )