from django.core.management.base import BaseCommand
from orders.models import Order, OrderItem
from accounts.models import User
from restaurant.models import MenuItem, Category
from django.utils import timezone
from decimal import Decimal
from datetime import datetime, timedelta
import random
import pytz


class Command(BaseCommand):
    help = "Tạo dữ liệu doanh thu 2 tháng cho biểu đồ"

    def handle(self, *args, **options):
        # Lấy hoặc tạo user mẫu
        user, created = User.objects.get_or_create(
            username='test_customer',
            defaults={
                'email': 'customer@example.com',
                'first_name': 'Test',
                'last_name': 'Customer',
                'role': 'customer'
            }
        )
        if created:
            user.set_password('password123')
            user.save()
            self.stdout.write("Tạo user mẫu thành công")

        # Tạo hoặc lấy danh mục
        category, created = Category.objects.get_or_create(
            name='Món chính',
            defaults={'description': 'Các món ăn chính'}
        )

        # Tạo các món ăn mẫu
        menu_items_data = [
            {'name': 'Phở bò', 'price': Decimal('70000')},
            {'name': 'Bún chả', 'price': Decimal('60000')},
            {'name': 'Cơm tấm', 'price': Decimal('50000')},
            {'name': 'Bánh mì', 'price': Decimal('30000')},
            {'name': 'Bún bò Huế', 'price': Decimal('65000')},
            {'name': 'Gỏi cuốn', 'price': Decimal('40000')},
            {'name': 'Chả cá Lã Vọng', 'price': Decimal('120000')},
            {'name': 'Bánh xèo', 'price': Decimal('45000')},
        ]

        menu_items = []
        for item_data in menu_items_data:
            item, created = MenuItem.objects.get_or_create(
                name=item_data['name'],
                defaults={
                    'category': category,
                    'description': f'Mô tả cho {item_data["name"]}',
                    'price': item_data['price'],
                    'is_available': True
                }
            )
            menu_items.append(item)

        # Tạo đơn hàng trong 2 tháng gần đây
        current_time = timezone.now()
        start_date = current_time - timedelta(days=60)  # 2 tháng trước

        orders_created = 0
        for day_offset in range(60):  # 2 tháng
            # Tạo từ 1-3 đơn hàng mỗi ngày
            daily_orders = random.randint(1, 3)
            
            for _ in range(daily_orders):
                # Tạo thời gian ngẫu nhiên trong ngày
                order_time = start_date + timedelta(days=day_offset) + timedelta(
                    hours=random.randint(9, 21),  # Giờ từ 9h sáng đến 9h tối
                    minutes=random.randint(0, 59)
                )
                
                # Tạo đơn hàng với số thứ tự duy nhất
                import time
                order_number = f"ORD{int(time.time())}{random.randint(1000, 9999)}"
                
                order = Order.objects.create(
                    order_number=order_number,
                    customer=user,
                    order_type=random.choice(['delivery', 'pickup', 'dine_in']),
                    status=random.choice(['completed', 'cancelled', 'pending', 'confirmed']),
                    delivery_name=f'Khách hàng {random.randint(100, 999)}',
                    delivery_phone=f'0{random.randint(100000000, 999999999)}',
                    delivery_address='123 Đường ABC, Quận XYZ, TP.HCM',
                    subtotal=Decimal('0'),
                    delivery_fee=Decimal('0'),
                    discount=Decimal('0'),
                    total_amount=Decimal('0'),
                    payment_method=random.choice(['cod', 'momo', 'zalopay', 'bank_transfer']),
                    payment_status=random.choice(['paid', 'pending']) if random.random() > 0.3 else 'paid',  # 70% đã thanh toán
                    created_at=order_time,
                    updated_at=order_time
                )
                
                # Chỉ tính doanh thu cho đơn hàng đã hoàn thành và đã thanh toán
                if order.status == 'completed' and order.payment_status == 'paid':
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
                    self.stdout.write(
                        f"Tạo đơn hàng: {order.order_number}, "
                        f"Ngày: {order.created_at.strftime('%Y-%m-%d')}, "
                        f"Tổng: {order.total_amount:,}đ, "
                        f"Trạng thái: {order.get_status_display()}, "
                        f"Thanh toán: {order.get_payment_status_display()}"
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nTạo thành công {orders_created} đơn hàng đã hoàn thành và đã thanh toán "
                f"trong 2 tháng qua."
            )
        )
        
        # Thống kê
        completed_paid_orders = Order.objects.filter(
            status='completed',
            payment_status='paid'
        )
        total_revenue = sum(order.total_amount for order in completed_paid_orders)
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Tổng doanh thu từ các đơn đã hoàn thành và đã thanh toán: {total_revenue:,}đ"
            )
        )