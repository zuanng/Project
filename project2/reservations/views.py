from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Reservation, Table
from .forms import ReservationForm
from accounts.decorators import customer_required

@login_required
@customer_required
def reservation_create(request):
    """Tạo đặt bàn mới"""
    if request.method == 'POST':
        form = ReservationForm(request.POST, user=request.user)
        
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.customer = request.user
            
            # Tìm bàn phù hợp
            suitable_table = Table.objects.filter(
                capacity__gte=reservation.number_of_guests,
                is_active=True,
                status='available'
            ).order_by('capacity').first()
            
            if suitable_table:
                reservation.table = suitable_table
                reservation.save()
                
                messages.success(
                    request,
                    f'Đặt bàn thành công! Mã đặt bàn: {reservation.reservation_number}'
                )
                return redirect('reservations:reservation_detail',
                              reservation_number=reservation.reservation_number)
            else:
                # Vẫn lưu reservation nhưng chưa có bàn
                reservation.save()
                messages.warning(
                    request,
                    'Đặt bàn thành công! Chúng tôi sẽ sắp xếp bàn phù hợp và liên hệ lại với bạn.'
                )
                return redirect('reservations:reservation_detail',
                              reservation_number=reservation.reservation_number)
        else:
            # Nếu form có lỗi, hiển thị lại form với errors
            messages.error(request, 'Có lỗi trong thông tin đặt bàn. Vui lòng kiểm tra lại.')
    else:
        form = ReservationForm(user=request.user)
    
    context = {
        'form': form,
    }
    return render(request, 'reservations/reservation_form.html', context)

@login_required
@customer_required
def reservation_list(request):
    """Danh sách đặt bàn của khách"""
    reservations = Reservation.objects.filter(
        customer=request.user
    ).select_related("table")

    context = {
        "reservations": reservations,
    }
    return render(request, "reservations/reservation_list.html", context)


@login_required
@customer_required
def reservation_detail(request, reservation_number):
    """Chi tiết đặt bàn"""
    reservation = get_object_or_404(
        Reservation,
        reservation_number=reservation_number,
        customer=request.user,
    )

    context = {
        "reservation": reservation,
    }
    return render(request, "reservations/reservation_detail.html", context)


@login_required
@customer_required
def cancel_reservation(request, reservation_number):
    """Hủy đặt bàn"""
    reservation = get_object_or_404(
        Reservation,
        reservation_number=reservation_number,
        customer=request.user,
    )

    if reservation.status in ["pending", "confirmed"]:
        reservation.status = "cancelled"
        reservation.save()

        if reservation.table:
            reservation.table.status = "available"
            reservation.table.save()

        messages.success(request, "Đã hủy đặt bàn thành công")
    else:
        messages.error(request, "Không thể hủy đặt bàn này")

    return redirect(
        "reservations:reservation_detail",
        reservation_number=reservation_number,
    )
