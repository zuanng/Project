from django.core.management.base import BaseCommand
import os
from django.core.files import File
from restaurant.models import Category, MenuItem, Chef
from decimal import Decimal


class Command(BaseCommand):
    help = "Tạo dữ liệu mẫu cho restaurant"

    def handle(self, *args, **kwargs):
        # Tạo Categories
        categories_data = [
            {"name": "Khai vị", "description": "Các món khai vị ngon miệng"},
            {"name": "Món chính", "description": "Các món chính đặc sắc"},
            {
                "name": "Tráng miệng",
                "description": "Các món tráng miệng hấp dẫn",
            },
            {"name": "Đồ uống", "description": "Các loại nước giải khát"},
            {"name": "Món chay", "description": "Các món ăn chay dinh dưỡng"},
        ]

        for cat_data in categories_data:
            Category.objects.get_or_create(
                name=cat_data["name"],
                defaults={"description": cat_data["description"]},
            )

        self.stdout.write(self.style.SUCCESS("Created categories"))

        # Tạo Menu Items
        appetizer = Category.objects.get(name="Khai vị")
        main = Category.objects.get(name="Món chính")

        menu_items_data = [
            {
                "name": "Đậu hũ chiên",
                "category": appetizer,
                "description": "Đậu hũ chiên giòn rụm, ăn kèm nước mắm chua ngọt",
                "price": Decimal("49000"),
                "is_featured": True,
            },
            {
                "name": "Gỏi cuốn tôm thịt",
                "category": appetizer,
                "description": "Gỏi cuốn tươi ngon với tôm và thịt heo",
                "price": Decimal("50000"),
                "is_featured": True,
            },
            {
                "name": "Phở bò",
                "category": main,
                "description": "Phở bò truyền thống Hà Nội",
                "price": Decimal("70000"),
                "discount_price": Decimal("60000"),
                "is_featured": True,
            },
            {
                "name": "Bún chả Hà Nội",
                "category": main,
                "description": "Bún chả đặc sản Hà Nội",
                "price": Decimal("65000"),
                "is_featured": True,
            },
        ]

        base_dir = os.path.dirname(__file__)  # restaurant/management/commands
        images_dir = os.path.join(base_dir, "sample_images", "menu")

        for item_data in menu_items_data:
            # chỉ cung cấp những trường có trong model làm defaults
            defaults = {
                "category": item_data.get("category"),
                "description": item_data.get("description", ""),
                "price": item_data.get("price", 0),
            }
            obj, created = MenuItem.objects.get_or_create(
                name=item_data["name"], defaults=defaults
            )

            # gán ảnh mẫu nếu là món Đậu hũ chiên và file tồn tại
            if obj.name == "Đậu hũ chiên":
                img_filename = "dauhu_chien.jpg"
                img_path = os.path.join(images_dir, img_filename)
                if os.path.exists(img_path):
                    # chỉ gán nếu chưa có ảnh
                    if not getattr(obj, "image", None):
                        with open(img_path, "rb") as f:
                            obj.image.save(img_filename, File(f), save=True)

        self.stdout.write(self.style.SUCCESS("Created menu items"))

        # Tạo Chefs
        chefs_data = [
            {
                "name": "Nguyễn Văn A",
                "position": "Head Chef",
                "bio": "Với hơn 15 năm kinh nghiệm trong nghề",
                "specialization": "Món Việt truyền thống",
            },
            {
                "name": "Trần Thị B",
                "position": "Sous Chef",
                "bio": "Chuyên gia về các món tráng miệng",
                "specialization": "Pastry & Dessert",
            },
        ]

        for chef_data in chefs_data:
            Chef.objects.get_or_create(
                name=chef_data["name"], defaults=chef_data
            )

        self.stdout.write(self.style.SUCCESS("Created chefs"))
        self.stdout.write(
            self.style.SUCCESS("Sample data created successfully!")
        )
