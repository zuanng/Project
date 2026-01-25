from django.core.management.base import BaseCommand
from orders.models import Order, OrderItem
from django.db import transaction


class Command(BaseCommand):
    help = "Xóa tất cả các đơn hàng đã tạo (giữ lại 2 đơn hàng gốc)"

    def handle(self, *args, **options):
        # Đếm số lượng đơn hàng trước khi xóa
        total_orders_before = Order.objects.count()
        
        self.stdout.write(f"Tổng số đơn hàng trước khi xóa: {total_orders_before}")
        
        # Xóa tất cả các đơn hàng ngoại trừ 2 đơn hàng gốc (ORD1769332619 và ORD1769331379)
        orders_to_delete = Order.objects.exclude(
            order_number__in=['ORD1769332619', 'ORD1769331379']
        )
        
        # Xóa các OrderItem liên quan trước
        order_items_deleted = 0
        for order in orders_to_delete:
            deleted_count, _ = order.items.all().delete()
            order_items_deleted += deleted_count
        
        # Xóa các đơn hàng
        orders_deleted_count, _ = orders_to_delete.delete()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Đã xóa thành công {orders_deleted_count} đơn hàng và {order_items_deleted} mục đơn hàng"
            )
        )
        
        total_orders_after = Order.objects.count()
        self.stdout.write(f"Tổng số đơn hàng sau khi xóa: {total_orders_after}")
        
        # Hiển thị các đơn hàng còn lại
        remaining_orders = Order.objects.all()
        self.stdout.write("Các đơn hàng còn lại:")
        for order in remaining_orders:
            self.stdout.write(f"- {order.order_number} - {order.created_at.strftime('%Y-%m-%d %H:%M:%S')} - {order.total_amount}đ")