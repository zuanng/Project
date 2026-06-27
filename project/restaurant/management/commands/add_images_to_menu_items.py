from django.core.management.base import BaseCommand
from restaurant.models import MenuItem
import os
from django.conf import settings


class Command(BaseCommand):
    help = "Thêm hình ảnh cho các món ăn"

    def handle(self, *args, **options):
        # Danh sách món ăn và hình ảnh tương ứng
        menu_items_with_images = {
            "Phở bò truyền thống": "pho_bo.jpg",
            "Bún chả Hà Nội": "bun_cha.jpg",
            "Gỏi cuốn tôm thịt": "goi_cuon.jpg",
            "Cơm tấm sườn bì": "com_tam.jpg",
            "Bánh xèo miền Trung": "banh_xeo.jpg",
            "Chè đậu trắng hạt sen": "che_dau_trang.jpg",
            "Sinh tố bơ": "sinh_to_bo.jpg",
            "Cà phê sữa đá": "ca_phe_sua_da.jpg",
            "Cơm gà Hội An": "com_ga_hoi_an.jpg",
            "Bánh mì thịt nướng": "banh_mi_thit_nuong.jpg",
            "Bún bò Huế": "bun_bo_hue.jpg",
            "Bánh canh ghẹ": "banh_canh_ghe.jpg",
            "Nem nướng Nha Trang": "nem_nuong.jpg",
            "Chè ba màu": "che_ba_mau.jpg",
            "Nước mía": "nuoc_mia.jpg"
        }

        # Cập nhật hình ảnh cho các món ăn
        for name, image_filename in menu_items_with_images.items():
            try:
                menu_item = MenuItem.objects.get(name=name)
                
                # Tạo đường dẫn đến file ảnh
                image_path = os.path.join("menu", image_filename)
                
                # Chỉ cập nhật nếu món ăn chưa có hình
                if not menu_item.image:
                    menu_item.image = image_path
                    menu_item.save()
                    self.stdout.write(
                        self.style.SUCCESS(f'Đã thêm hình ảnh cho: {name}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'{name} đã có hình ảnh rồi')
                    )
                    
            except MenuItem.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'Không tìm thấy món ăn: {name}')
                )

        self.stdout.write(
            self.style.SUCCESS('Đã hoàn thành thêm hình ảnh cho các món ăn!')
        )