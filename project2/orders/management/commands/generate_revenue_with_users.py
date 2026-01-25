from django.core.management.base import BaseCommand
from orders.models import Order, OrderItem
from accounts.models import User
from restaurant.models import MenuItem
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random
import pytz


class Command(BaseCommand):
    help = "Tạo dữ liệu doanh thu 2 tháng với 5 user khác nhau, giữ nguyên món ăn"

    def handle(self, *args, **options):
        # Tạo 5 user khác nhau (nếu chưa tồn tại)
        usernames = ['customer1', 'customer2', 'customer3', 'customer4', 'customer5']
        emails = ['customer1@example.com', 'customer2@example.com', 'customer3@example.com', 'customer4@example.com', 'customer5@example.com']
        names = [('Nguyen', 'Van A'), ('Le', 'Thi B'), ('Tran', 'Van C'), ('Pham', 'Thi D'), ('Hoang', 'Van E')]
        
        users = []
        for i, username in enumerate(usernames):
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': emails[i],
                    'first_name': names[i][1],
                    'last_name': names[i][0],
                    'role': 'customer'
                }
            )
            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f"Tạo user: {username}")
            users.append(user)

        # Lấy tất cả các món ăn hiện có
        menu_items = list(MenuItem.objects.all())
        if not menu_items:
            self.stdout.write("Không tìm thấy món ăn nào trong hệ thống")
            return

        self.stdout.write(f"Tìm thấy {len(menu_items)} món ăn trong hệ thống")

        # Tạo đơn hàng trong 2 tháng gần đây
        current_time = timezone.now()
        orders_created = 0
        total_revenue = Decimal('0')
        
        # Tạo tổng cộng khoảng 120 đơn hàng trải đều trong 2 tháng
        total_orders_to_create = 120
        
        for _ in range(total_orders_to_create):
            # Chọn ngẫu nhiên một user
            user = random.choice(users)
            
            # Chọn ngẫu nhiên một ngày trong khoảng 2 tháng qua
            random_days_back = random.randint(0, 59)  # 0 to 59 days back
            random_date = current_time - timedelta(days=random_days_back)
            
            # Tạo thời gian ngẫu nhiên trong ngày được chọn
            order_time = random_date.replace(
                hour=random.randint(9, 21),  # Giờ từ 9h sáng đến 9h tối
                minute=random.randint(0, 59),
                second=random.randint(0, 59),
                microsecond=random.randint(0, 999999)
            )
            
            # Tạo đơn hàng với số đơn hàng duy nhất
            import time
            while True:
                order_number = f"ORD{int(time.time())}{random.randint(10000, 99999)}"
                if not Order.objects.filter(order_number=order_number).exists():
                    break
            
            order = Order.objects.create(
                order_number=order_number,
                customer=user,
                order_type=random.choice(['delivery', 'pickup', 'dine_in']),
                status='completed',  # Đặt tất cả là completed
                delivery_name=f'{user.first_name} {user.last_name}',
                delivery_phone=f'0{random.randint(100000000, 999999999)}',
                delivery_address=f'{random.randint(1, 999)} Đường ABC, Quận {random.choice(["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8", "Q9", "Q10", "Q11", "Q12"])}',
                subtotal=Decimal('0'),
                delivery_fee=Decimal('0'),
                discount=Decimal('0'),
                total_amount=Decimal('0'),
                payment_method=random.choice(['cod', 'momo', 'zalopay', 'bank_transfer']),
                payment_status='paid',  # Đặt tất cả là paid
                created_at=order_time,
                updated_at=order_time
            )
            
            # Tạo các mục đơn hàng
            num_items = random.randint(1, 4)  # 1-4 món mỗi đơn
            subtotal = Decimal('0')
            
            for _ in range(num_items):
                menu_item = random.choice(menu_items)
                quantity = random.randint(1, 3)
                price = menu_item.price
                
                order_item = OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=quantity,
                    price=price
                )
                
                subtotal += price * quantity
            
            # Áp dụng phí vận chuyển và giảm giá
            order.subtotal = subtotal
            if subtotal >= 200000:
                order.delivery_fee = Decimal('0')  # Miễn phí vận chuyển
            else:
                order.delivery_fee = Decimal('30000')  # Phí vận chuyển
            
            order.total_amount = subtotal + order.delivery_fee - order.discount
            order.save()
            
            orders_created += 1
            total_revenue += order.total_amount
            self.stdout.write(
                f"Tạo đơn hàng: {order.order_number}, "
                f"Khách: {user.username}, "
                f"Ngày: {order.created_at.strftime('%Y-%m-%d')}, "
                f"Tổng: {order.total_amount:,}đ"
            )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"\nTạo thành công {orders_created} đơn hàng đã hoàn thành và đã thanh toán "
                f"cho 5 user khác nhau trong 2 tháng qua."
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Tổng doanh thu từ các đơn đã hoàn thành và đã thanh toán: {total_revenue:,}đ"
            )
        )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTạo thành công {orders_created} đơn hàng đã hoàn thành và đã thanh toán "
                f"cho 5 user khác nhau trong 2 tháng qua."
            )
        )
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Tổng doanh thu từ các đơn đã hoàn thành và đã thanh toán: {total_revenue:,}đ"
            )
        )