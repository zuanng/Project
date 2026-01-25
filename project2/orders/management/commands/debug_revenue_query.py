from django.core.management.base import BaseCommand
from orders.models import Order
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Debug revenue query to see what's happening with the data"

    def handle(self, *args, **options):
        # Replicate the exact query from revenue_report view
        start_date = timezone.now().date() - timedelta(weeks=12)
        date_field = TruncDate("created_at")

        revenue_data = (
            Order.objects.filter(
                created_at__date__gte=start_date,
                status="completed",
                payment_status="paid",
            )
            .annotate(period=date_field)
            .values("period")
            .annotate(revenue=Sum("total_amount"), orders_count=Count("id"))
            .order_by("period")
        )

        self.stdout.write(
            self.style.SUCCESS(f"\n=== KẾT QUẢ TRUY VẤN REVENUE REPORT ===")
        )
        self.stdout.write(f"Start date: {start_date}")
        self.stdout.write(f"Số lượng bản ghi sau query: {len(list(revenue_data))}\n")

        for item in revenue_data:
            self.stdout.write(f"Ngày: {item['period']}")
            self.stdout.write(f"  - Doanh thu: {item['revenue']:,}đ")
            self.stdout.write(f"  - Số đơn: {item['orders_count']}")
            self.stdout.write("-" * 30)

        # Check all completed and paid orders separately
        all_completed_paid = Order.objects.filter(
            status="completed",
            payment_status="paid"
        )
        self.stdout.write(
            self.style.SUCCESS(f"\n=== TẤT CẢ ĐƠN HÀNG COMPLETED & PAID ===")
        )
        self.stdout.write(f"Tổng cộng: {all_completed_paid.count()} đơn")
        
        for order in all_completed_paid:
            self.stdout.write(f"- {order.order_number}: {order.total_amount:,}đ (created: {order.created_at.date()})")

        # Check specifically for today's orders
        today_orders = Order.objects.filter(
            created_at__date=timezone.now().date(),
            status="completed",
            payment_status="paid"
        )
        self.stdout.write(
            self.style.SUCCESS(f"\n=== ĐƠN HÔM NAY (COMPLETED & PAID) ===")
        )
        self.stdout.write(f"Số lượng: {today_orders.count()}")
        for order in today_orders:
            self.stdout.write(f"- {order.order_number}: {order.total_amount:,}đ")