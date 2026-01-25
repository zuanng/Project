from django.core.management.base import BaseCommand
from orders.models import Order
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from datetime import timedelta, date
import pytz


class Command(BaseCommand):
    help = "Debug timezone issues with orders"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f"\n=== DEBUG TIMEZONE & DATE ISSUES ===")
        )
        
        # Get current time in different formats
        now = timezone.now()
        today = timezone.now().date()
        
        self.stdout.write(f"Current time (now): {now}")
        self.stdout.write(f"Current date (today): {today}")
        self.stdout.write(f"Timezone: {timezone.get_current_timezone()}")
        
        # Get all completed and paid orders
        orders = Order.objects.filter(
            status="completed",
            payment_status="paid"
        )
        
        self.stdout.write(f"\nCompleted & Paid Orders:")
        for order in orders:
            self.stdout.write(f"- Order: {order.order_number}")
            self.stdout.write(f"  - Created at (full): {order.created_at}")
            self.stdout.write(f"  - Created date: {order.created_at.date()}")
            self.stdout.write(f"  - Is today?: {order.created_at.date() == today}")
            self.stdout.write(f"  - Timezone: {order.created_at.tzinfo}")
            self.stdout.write("-" * 40)
        
        # Test the specific query used in revenue_report
        start_date = today - timedelta(weeks=12)
        self.stdout.write(f"\nStart date for revenue report: {start_date}")
        
        # Try different query approaches
        q1 = Order.objects.filter(
            created_at__date__gte=start_date,
            status="completed",
            payment_status="paid",
        )
        self.stdout.write(f"Query 1 (__date__gte): {q1.count()}")
        
        q2 = Order.objects.filter(
            created_at__date=today,  # Today's date specifically
            status="completed",
            payment_status="paid",
        )
        self.stdout.write(f"Query 2 (today's date): {q2.count()}")
        
        # Check if dates match exactly
        for order in orders:
            self.stdout.write(f"Order date {order.created_at.date()} >= Start date {start_date}? {order.created_at.date() >= start_date}")