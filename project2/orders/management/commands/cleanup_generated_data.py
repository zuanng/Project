from django.core.management.base import BaseCommand
from orders.models import Order, OrderItem
from restaurant.models import MenuItem, Category
from accounts.models import User
from django.db import transaction


class Command(BaseCommand):
    help = "Xóa dữ liệu đã được tạo trong quá trình sinh dữ liệu mẫu"

    def handle(self, *args, **options):
        self.stdout.write("Đang xóa dữ liệu đã tạo...")

        # Xóa các đơn hàng được tạo trong quá trình sinh dữ liệu
        # (chúng ta biết rằng các đơn hàng này có order_number bắt đầu bằng 'ORD' và có timestamp gần đây)
        with transaction.atomic():
            # Xóa các order items trước
            orders_to_delete = Order.objects.filter(
                delivery_name__contains='Khách hàng'  # Những đơn hàng được tạo bởi script có delivery_name như này
            )
            
            order_item_count = 0
            for order in orders_to_delete:
                order_item_count += order.items.count()
                order.items.all().delete()  # Xóa các OrderItem liên quan
            
            # Sau đó xóa các đơn hàng
            deleted_orders_count, _ = orders_to_delete.delete()
            
            # Xóa các món ăn được tạo trong quá trình sinh dữ liệu mẫu
            menu_items_to_delete = MenuItem.objects.filter(
                name__in=[
                    'Phở bò', 'Bún chả', 'Cơm tấm', 'Bánh mì', 'Bún bò Huế', 
                    'Gỏi cuốn', 'Chả cá Lã Vọng', 'Bánh xèo'
                ]
            )
            deleted_menu_items_count, _ = menu_items_to_delete.delete()
            
            # Xóa danh mục được tạo nếu không còn món ăn nào sử dụng
            try:
                category_to_delete = Category.objects.get(name='Món chính')
                if category_to_delete.menu_items.count() == 0:  # Nếu không còn món nào trong danh mục
                    category_to_delete.delete()
                    deleted_categories_count = 1
                else:
                    deleted_categories_count = 0
            except Category.DoesNotExist:
                deleted_categories_count = 0
            
            # Xóa user test nếu tồn tại
            try:
                test_user = User.objects.get(username='test_customer')
                test_user.delete()
                deleted_users_count = 1
            except User.DoesNotExist:
                deleted_users_count = 0

        self.stdout.write(
            self.style.SUCCESS(
                f"Đã xóa thành công:\n"
                f"- {deleted_orders_count} đơn hàng\n"
                f"- {order_item_count} mục đơn hàng\n"
                f"- {deleted_menu_items_count} món ăn\n"
                f"- {deleted_categories_count} danh mục\n"
                f"- {deleted_users_count} người dùng"
            )
        )