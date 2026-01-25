from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from restaurant.cart import Cart
from .models import Order, OrderItem, Coupon
from .forms import CheckoutForm
from accounts.decorators import customer_required
from django.core.paginator import Paginator


@login_required
@customer_required
def checkout(request):
    """Trang thanh toán"""
    cart = Cart(request)
    
    if len(cart) == 0:
        messages.warning(request, 'Giỏ hàng trống!')
        return redirect('restaurant:menu_list')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST, user=request.user)
        
        if form.is_valid():
            # Tạo order
            order = form.save(commit=False)
            order.customer = request.user
            order.subtotal = cart.get_total_price()
            
            # Xử lý mã giảm giá
            coupon_code = form.cleaned_data.get('coupon_code')
            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    is_valid, message = coupon.is_valid()
                    
                    if is_valid:
                        if order.subtotal >= coupon.min_order_amount:
                            order.discount = coupon.calculate_discount(order.subtotal)
                            coupon.used_count += 1
                            coupon.save()
                            messages.success(request, f'Áp dụng mã giảm giá thành công!')
                        else:
                            messages.warning(
                                request,
                                f'Đơn hàng tối thiểu {coupon.min_order_amount}đ'
                            )
                    else:
                        messages.warning(request, message)
                except Coupon.DoesNotExist:
                    messages.warning(request, 'Mã giảm giá không tồn tại')
            
            # Tính phí ship
            if order.subtotal >= 200000:
                order.delivery_fee = 0
            else:
                order.delivery_fee = 30000
            
            order.total_amount = order.subtotal + order.delivery_fee - order.discount
            order.save()
            
            # Tạo order items từ cart
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    menu_item=item['menu_item'],
                    quantity=item['quantity'],
                    price=item['price']
                )
            
            # Xóa giỏ hàng
            cart.clear()
            
            messages.success(
                request,
                f'Đặt hàng thành công! Mã đơn hàng: {order.order_number}'
            )
            return redirect('orders:order_detail', order_number=order.order_number)
        else:
            # Hiển thị lỗi
            messages.error(request, 'Có lỗi trong thông tin đặt hàng. Vui lòng kiểm tra lại.')
    else:
        form = CheckoutForm(user=request.user)
    
    context = {
        'form': form,
        'cart': cart,
    }
    return render(request, 'orders/checkout.html', context)


@login_required
@customer_required
def order_list(request):
    """Danh sách đơn hàng của khách với phân trang"""
    orders = Order.objects.filter(
        customer=request.user
    ).prefetch_related('items').order_by('-created_at')
    
    # Phân trang - 10 đơn/trang
    paginator = Paginator(orders, 10)
    page_obj = paginator.get_page(request.GET.get('page'))
    
    context = {
        'orders': page_obj,
        'page_obj': page_obj,
    }
    return render(request, 'orders/order_list.html', context)

@login_required
@customer_required
def order_detail(request, order_number):
    """Chi tiết đơn hàng"""
    order = get_object_or_404(
        Order, order_number=order_number, customer=request.user
    )

    context = {
        "order": order,
    }
    return render(request, "orders/order_detail.html", context)


@login_required
@customer_required
def cancel_order(request, order_number):
    """Hủy đơn hàng"""
    order = get_object_or_404(
        Order, order_number=order_number, customer=request.user
    )

    if order.status in ["pending", "confirmed"]:
        order.status = "cancelled"
        order.save()
        messages.success(request, "Đã hủy đơn hàng thành công")
    else:
        messages.error(request, "Không thể hủy đơn hàng này")

    return redirect("orders:order_detail", order_number=order_number)
