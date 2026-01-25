from django.core.management.base import BaseCommand
from orders.models import Order
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta, datetime
import pytz


class Command(BaseCommand):
    help = "Debug raw SQL queries to see what's happening"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f"\n=== DEBUG RAW QUERIES ===")
        )
        
        # Get current date in local timezone
        local_tz = pytz.timezone('Asia/Ho_Chi_Minh')
        today_local = timezone.now().astimezone(local_tz).date()
        
        self.stdout.write(f"Today in local timezone (Asia/Ho_Chi_Minh): {today_local}")
        self.stdout.write(f"Today in UTC: {timezone.now().date()}")
        
        # Direct query for completed and paid orders without date filter
        all_completed_paid = Order.objects.filter(
            status="completed",
            payment_status="paid"
        )
        self.stdout.write(f"\nAll completed & paid orders: {all_completed_paid.count()}")
        
        for order in all_completed_paid:
            # Convert order time to local timezone for comparison
            order_local_time = order.created_at.astimezone(local_tz)
            self.stdout.write(f"- Order: {order.order_number}")
            self.stdout.write(f"  - UTC time: {order.created_at} (date: {order.created_at.date()})")
            self.stdout.write(f"  - Local time: {order_local_time} (date: {order_local_time.date()})")
            self.stdout.write(f"  - Local date == today_local: {order_local_time.date() == today_local}")
            self.stdout.write(f"  - UTC date == today_utc: {order.created_at.date() == timezone.now().date()}")
            self.stdout.write("-" * 50)
        
        # Test different date filtering approaches
        from django.db import connection
        
        # Query 1: Using __date field lookup (this is what's failing)
        q1 = Order.objects.filter(
            created_at__date=today_local,  # Using local date
            status="completed",
            payment_status="paid"
        )
        self.stdout.write(f"\nQuery 1 (using local date {today_local}): {q1.count()}")
        
        # Query 2: Using exact date comparison in UTC
        q2 = Order.objects.filter(
            created_at__date=timezone.now().date(),  # Using UTC date
            status="completed", 
            payment_status="paid"
        )
        self.stdout.write(f"Query 2 (using UTC date {timezone.now().date()}): {q2.count()}")
        
        # Query 3: Using range query to avoid timezone issues
        start_of_day = timezone.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end_of_day = timezone.now().replace(hour=23, minute=59, second=59, microsecond=999999)
        
        q3 = Order.objects.filter(
            created_at__range=(start_of_day, end_of_day),
            status="completed",
            payment_status="paid"
        )
        self.stdout.write(f"Query 3 (using datetime range): {q3.count()}")
        
        # Check what the actual dates are
        self.stdout.write(f"\nActual date comparisons:")
        self.stdout.write(f"  - Order 1 date: {all_completed_paid[0].created_at.date()}")
        self.stdout.write(f"  - Order 2 date: {all_completed_paid[1].created_at.date()}")
        self.stdout.write(f"  - Today UTC: {timezone.now().date()}")
        self.stdout.write(f"  - Today Local: {today_local}")