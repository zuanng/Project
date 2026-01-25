from django.core.management.base import BaseCommand
from orders.models import Order
from django.db.models import Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta


class Command(BaseCommand):
    help = "Kiểm tra phân bố ngày tháng của đơn hàng"

    def handle(self, *args, **options):
        # Lấy tất cả các đơn hàng đã hoàn thành và đã thanh toán
        orders = Order.objects.filter(
            status="completed",
            payment_status="paid"
        )
        
        self.stdout.write(f"Tổng số đơn hàng hoàn thành và đã thanh toán: {orders.count()}")
        
        # Tính toán khoảng thời gian 2 tháng qua
        today = timezone.now().date()
        start_date = today - timedelta(days=60)
        
        self.stdout.write(f"Khoảng thời gian kiểm tra: {start_date} đến {today}")
        
        # Lấy các đơn hàng trong khoảng thời gian này
        orders_in_range = orders.filter(
            created_at__date__gte=start_date
        )
        
        self.stdout.write(f"Số đơn hàng trong 2 tháng qua: {orders_in_range.count()}")
        
        # Thống kê theo ngày
        daily_stats = (
            orders_in_range
            .annotate(date=TruncDate("created_at"))
            .values("date")
            .annotate(count=Count("id"))
            .order_by("date")
        )
        
        self.stdout.write("\n--- Thống kê theo ngày ---")
        for stat in daily_stats:
            self.stdout.write(f"Ngày {stat['date']}: {stat['count']} đơn hàng")
        
        # Thống kê theo tuần
        weekly_stats = (
            orders_in_range
            .annotate(week=TruncDate("created_at") - timedelta(days=timezone.now().date().weekday()))
            .values("week")
            .annotate(count=Count("id"))
            .order_by("week")
        )
        
        self.stdout.write(f"\n--- Thống kê theo tuần ---")
        for stat in weekly_stats:
            self.stdout.write(f"Tuần bắt đầu {stat['week']}: {stat['count']} đơn hàng")
        
        # Kiểm tra xem có đơn hàng từ các ngày khác nhau không
        dates_with_orders = [stat['date'] for stat in daily_stats]
        if len(dates_with_orders) > 0:
            earliest_date = min(dates_with_orders)
            latest_date = max(dates_with_orders)
            self.stdout.write(f"\nNgày sớm nhất có đơn: {earliest_date}")
            self.stdout.write(f"Ngày muộn nhất có đơn: {latest_date}")
            self.stdout.write(f"Số ngày khác nhau có đơn: {len(dates_with_orders)}")
            
            if earliest_date <= start_date:
                self.stdout.write(self.style.SUCCESS("✓ Có đơn hàng từ nhiều ngày trong khoảng 2 tháng"))
            else:
                self.stdout.write(self.style.WARNING("⚠ Đơn hàng có thể chưa được phân bố đúng theo ngày"))
        else:
            self.stdout.write(self.style.WARNING("⚠ Không tìm thấy đơn hàng trong khoảng thời gian 2 tháng"))