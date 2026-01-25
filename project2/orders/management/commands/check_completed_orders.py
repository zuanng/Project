from django.core.management.base import BaseCommand
from orders.models import Order
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Kiểm tra các đơn hàng đã hoàn thành và đã thanh toán trong cơ sở dữ liệu"

    def handle(self, *args, **options):
        # Lấy tất cả các đơn hàng đã hoàn thành và đã thanh toán
        completed_paid_orders = Order.objects.filter(
            status="completed",
            payment_status="paid"
        ).order_by('-created_at')

        self.stdout.write(
            self.style.SUCCESS(f"\n=== ĐƠN HÀNG ĐÃ HOÀN THÀNH VÀ ĐÃ THANH TOÁN ===")
        )
        self.stdout.write(
            self.style.SUCCESS(f"Tổng số: {completed_paid_orders.count()} đơn hàng\n")
        )

        for order in completed_paid_orders:
            days_ago = (timezone.now() - order.created_at).days
            self.stdout.write(f"Mã đơn: {order.order_number}")
            self.stdout.write(f"  - Trạng thái: {order.get_status_display()}")
            self.stdout.write(f"  - Trạng thái thanh toán: {order.get_payment_status_display()}")
            self.stdout.write(f"  - Tổng tiền: {order.total_amount:,}đ")
            self.stdout.write(f"  - Ngày tạo: {order.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
            self.stdout.write(f"  - Cách đây: {days_ago} ngày")
            self.stdout.write(f"  - Có trong báo cáo doanh thu (nếu trong 12 tuần): {'✓' if days_ago <= 84 else '✗'}")
            self.stdout.write("-" * 50)

        # Thống kê theo khoảng thời gian
        self.stdout.write(
            self.style.SUCCESS(f"\n=== THỐNG KÊ THEO KHOẢNG THỜI GIAN ===")
        )
        
        periods = [
            ("7 ngày", 7),
            ("30 ngày", 30),
            ("3 tháng (90 ngày)", 90),
            ("6 tháng (180 ngày)", 180),
            ("1 năm (365 ngày)", 365),
        ]
        
        for period_name, days in periods:
            orders_in_period = completed_paid_orders.filter(
                created_at__gte=timezone.now() - timedelta(days=days)
            )
            self.stdout.write(
                f"{period_name}: {orders_in_period.count()} đơn hàng"
            )