from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg, Q
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone
from django.http import JsonResponse
from datetime import timedelta, datetime
from decimal import Decimal

from accounts.decorators import admin_required, staff_required
from accounts.models import User
from orders.models import Order, OrderItem
from reservations.models import Reservation, Table
from restaurant.models import MenuItem, Category, Review


@login_required
@admin_required
def admin_dashboard(request):
    """Dashboard tổng quan cho admin"""
    today = timezone.now().date()

    # Stats tổng quan
    stats = {
        "total_orders": Order.objects.count(),
        "pending_orders": Order.objects.filter(status="pending").count(),
        "total_revenue": Order.objects.filter(
            status="completed", payment_status="paid"
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0,
        "total_customers": User.objects.filter(role="customer").count(),
        "total_reservations": Reservation.objects.count(),
        "pending_reservations": Reservation.objects.filter(
            status="pending"
        ).count(),
        "total_menu_items": MenuItem.objects.filter(is_available=True).count(),
    }

    # Doanh thu hôm nay
    today_revenue = (
        Order.objects.filter(
            created_at__date=today, status="completed", payment_status="paid"
        ).aggregate(total=Sum("total_amount"))["total"]
        or 0
    )

    # Đơn hàng hôm nay
    today_orders = Order.objects.filter(created_at__date=today).count()

    # Top món ăn bán chạy
    top_items = (
        OrderItem.objects.filter(order__status="completed")
        .values("menu_item__name", "menu_item__image")
        .annotate(total_quantity=Sum("quantity"), total_revenue=Sum("price"))
        .order_by("-total_quantity")[:5]
    )

    # Đơn hàng gần đây
    recent_orders = Order.objects.select_related("customer").order_by(
        "-created_at"
    )[:10]

    # Đặt bàn gần đây
    recent_reservations = Reservation.objects.select_related(
        "customer", "table"
    ).order_by("-created_at")[:10]

    # Đánh giá gần đây
    recent_reviews = Review.objects.select_related(
        "user", "menu_item"
    ).order_by("-created_at")[:5]

    context = {
        "stats": stats,
        "today_revenue": today_revenue,
        "today_orders": today_orders,
        "top_items": top_items,
        "recent_orders": recent_orders,
        "recent_reservations": recent_reservations,
        "recent_reviews": recent_reviews,
    }

    return render(request, "dashboard/admin_dashboard.html", context)


@login_required
@admin_required
def orders_management(request):
    """Quản lý đơn hàng"""
    status_filter = request.GET.get("status", "")
    payment_filter = request.GET.get("payment", "")
    date_from = request.GET.get("date_from", "")
    date_to = request.GET.get("date_to", "")

    orders = Order.objects.select_related("customer").prefetch_related("items")

    # Filters
    if status_filter:
        orders = orders.filter(status=status_filter)

    if payment_filter:
        orders = orders.filter(payment_status=payment_filter)

    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)

    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)

    orders = orders.order_by("-created_at")

    # Statistics
    stats = {
        "total": orders.count(),
        "pending": orders.filter(status="pending").count(),
        "confirmed": orders.filter(status="confirmed").count(),
        "preparing": orders.filter(status="preparing").count(),
        "delivering": orders.filter(status="delivering").count(),
        "completed": orders.filter(status="completed").count(),
        "cancelled": orders.filter(status="cancelled").count(),
        "total_revenue": orders.filter(
            status="completed", payment_status="paid"
        ).aggregate(Sum("total_amount"))["total_amount__sum"]
        or 0,
    }

    context = {
        "orders": orders[:50],  # Limit 50 orders
        "stats": stats,
        "status_filter": status_filter,
        "payment_filter": payment_filter,
        "date_from": date_from,
        "date_to": date_to,
    }

    return render(request, "dashboard/orders_management.html", context)


@login_required
@admin_required
def reservations_management(request):
    """Quản lý đặt bàn"""
    status_filter = request.GET.get("status", "")
    date_filter = request.GET.get("date", "")

    reservations = Reservation.objects.select_related("customer", "table")

    # Filters
    if status_filter:
        reservations = reservations.filter(status=status_filter)

    if date_filter:
        reservations = reservations.filter(date=date_filter)

    reservations = reservations.order_by("-date", "-time")

    # Statistics
    stats = {
        "total": reservations.count(),
        "pending": reservations.filter(status="pending").count(),
        "confirmed": reservations.filter(status="confirmed").count(),
        "completed": reservations.filter(status="completed").count(),
        "cancelled": reservations.filter(status="cancelled").count(),
    }

    # Tables status
    tables = Table.objects.all()

    context = {
        "reservations": reservations[:50],
        "stats": stats,
        "tables": tables,
        "status_filter": status_filter,
        "date_filter": date_filter,
    }

    return render(request, "dashboard/reservations_management.html", context)


@login_required
@admin_required
def revenue_report(request):
    """Báo cáo doanh thu"""
    period = request.GET.get("period", "week")  # day, week, month, year

    # Calculate date range
    today = timezone.now().date()

    if period == "day":
        start_date = today - timedelta(days=7)
        date_field = TruncDate("created_at")
    elif period == "week":
        start_date = today - timedelta(weeks=12)
        date_field = TruncDate("created_at")
    elif period == "month":
        start_date = today - timedelta(days=365)
        date_field = TruncMonth("created_at")
    else:  # year
        start_date = today - timedelta(days=365 * 3)
        date_field = TruncMonth("created_at")

    # Revenue data
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

    # Monthly comparison
    current_month = today.replace(day=1)
    last_month = (current_month - timedelta(days=1)).replace(day=1)

    current_month_revenue = (
        Order.objects.filter(
            created_at__date__gte=current_month,
            status="completed",
            payment_status="paid",
        ).aggregate(Sum("total_amount"))["total_amount__sum"]
        or 0
    )

    last_month_revenue = (
        Order.objects.filter(
            created_at__date__gte=last_month,
            created_at__date__lt=current_month,
            status="completed",
            payment_status="paid",
        ).aggregate(Sum("total_amount"))["total_amount__sum"]
        or 0
    )

    # Revenue by category
    revenue_by_category = (
        OrderItem.objects.filter(
            order__status="completed",
            order__payment_status="paid",
            order__created_at__date__gte=start_date,
        )
        .values("menu_item__category__name")
        .annotate(revenue=Sum("price"), quantity=Sum("quantity"))
        .order_by("-revenue")
    )

    # Revenue by payment method
    revenue_by_payment = (
        Order.objects.filter(
            status="completed",
            payment_status="paid",
            created_at__date__gte=start_date,
        )
        .values("payment_method")
        .annotate(revenue=Sum("total_amount"), count=Count("id"))
        .order_by("-revenue")
    )

    # Top customers
    top_customers = (
        Order.objects.filter(
            status="completed",
            payment_status="paid",
            created_at__date__gte=start_date,
        )
        .values(
            "customer__username", "customer__first_name", "customer__last_name"
        )
        .annotate(total_spent=Sum("total_amount"), orders_count=Count("id"))
        .order_by("-total_spent")[:10]
    )

    context = {
        "period": period,
        "revenue_data": list(revenue_data),
        "current_month_revenue": current_month_revenue,
        "last_month_revenue": last_month_revenue,
        "revenue_by_category": revenue_by_category,
        "revenue_by_payment": revenue_by_payment,
        "top_customers": top_customers,
    }

    return render(request, "dashboard/revenue_report.html", context)


@login_required
@admin_required
def menu_statistics(request):
    """Thống kê món ăn"""

    # Top selling items
    top_selling = (
        OrderItem.objects.filter(order__status="completed")
        .values(
            "menu_item__id",
            "menu_item__name",
            "menu_item__category__name",
            "menu_item__price",
        )
        .annotate(
            total_quantity=Sum("quantity"),
            total_revenue=Sum("price"),
            orders_count=Count("order", distinct=True),
        )
        .order_by("-total_quantity")[:20]
    )

    # Items by category
    items_by_category = (
        MenuItem.objects.values("category__name")
        .annotate(
            count=Count("id"),
            available=Count("id", filter=Q(is_available=True)),
            unavailable=Count("id", filter=Q(is_available=False)),
        )
        .order_by("-count")
    )

    # Average ratings
    avg_ratings = (
        Review.objects.values("menu_item__name")
        .annotate(avg_rating=Avg("rating"), review_count=Count("id"))
        .order_by("-avg_rating")[:10]
    )

    # Low stock items (items not ordered recently)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    low_performing = (
        MenuItem.objects.annotate(
            recent_orders=Count(
                "orderitem",
                filter=Q(orderitem__order__created_at__gte=thirty_days_ago),
            )
        )
        .filter(is_available=True, recent_orders__lt=5)
        .order_by("recent_orders")[:10]
    )

    context = {
        "top_selling": top_selling,
        "items_by_category": items_by_category,
        "avg_ratings": avg_ratings,
        "low_performing": low_performing,
    }

    return render(request, "dashboard/menu_statistics.html", context)


@login_required
@admin_required
def customer_statistics(request):
    """Thống kê khách hàng"""

    # Total customers
    total_customers = User.objects.filter(role="customer").count()

    # New customers this month
    current_month = timezone.now().replace(day=1)
    new_customers_this_month = User.objects.filter(
        role="customer", date_joined__gte=current_month
    ).count()

    # Customer registration trend
    six_months_ago = timezone.now() - timedelta(days=180)
    registration_trend = (
        User.objects.filter(role="customer", date_joined__gte=six_months_ago)
        .annotate(month=TruncMonth("date_joined"))
        .values("month")
        .annotate(count=Count("id"))
        .order_by("month")
    )

    # Top spending customers
    top_spenders = (
        Order.objects.filter(status="completed", payment_status="paid")
        .values(
            "customer__id",
            "customer__username",
            "customer__first_name",
            "customer__last_name",
            "customer__email",
        )
        .annotate(total_spent=Sum("total_amount"), orders_count=Count("id"))
        .order_by("-total_spent")[:20]
    )

    # Active vs Inactive customers
    active_threshold = timezone.now() - timedelta(days=30)
    active_customers = (
        Order.objects.filter(created_at__gte=active_threshold)
        .values("customer")
        .distinct()
        .count()
    )

    context = {
        "total_customers": total_customers,
        "new_customers_this_month": new_customers_this_month,
        "registration_trend": list(registration_trend),
        "top_spenders": top_spenders,
        "active_customers": active_customers,
        "inactive_customers": total_customers - active_customers,
    }

    return render(request, "dashboard/customer_statistics.html", context)


# API endpoints for AJAX requests
@login_required
@admin_required
def api_revenue_chart(request):
    """API cho chart doanh thu"""
    period = request.GET.get("period", "week")

    today = timezone.now().date()

    if period == "week":
        start_date = today - timedelta(days=7)
    elif period == "month":
        start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=365)

    revenue_data = (
        Order.objects.filter(
            created_at__date__gte=start_date,
            status="completed",
            payment_status="paid",
        )
        .annotate(date=TruncDate("created_at"))
        .values("date")
        .annotate(revenue=Sum("total_amount"), orders=Count("id"))
        .order_by("date")
    )

    return JsonResponse(
        {
            "labels": [
                item["date"].strftime("%d/%m") for item in revenue_data
            ],
            "revenue": [float(item["revenue"]) for item in revenue_data],
            "orders": [item["orders"] for item in revenue_data],
        }
    )


@login_required
@admin_required
def update_order_status(request, order_id):
    """Cập nhật trạng thái đơn hàng"""
    if request.method == "POST":
        order = get_object_or_404(Order, id=order_id)
        new_status = request.POST.get("status")

        if new_status in dict(Order.STATUS_CHOICES):
            order.status = new_status

            if new_status == "confirmed":
                order.confirmed_at = timezone.now()
            elif new_status == "completed":
                order.completed_at = timezone.now()

            order.save()

            return JsonResponse(
                {"success": True, "message": "Cập nhật trạng thái thành công"}
            )

    return JsonResponse({"success": False, "message": "Invalid request"})


@login_required
@admin_required
def update_reservation_status(request, reservation_id):
    """Cập nhật trạng thái đặt bàn"""
    if request.method == "POST":
        reservation = get_object_or_404(Reservation, id=reservation_id)
        new_status = request.POST.get("status")

        if new_status in dict(Reservation.STATUS_CHOICES):
            reservation.status = new_status

            if new_status == "confirmed":
                reservation.confirmed_at = timezone.now()

            reservation.save()

            return JsonResponse(
                {"success": True, "message": "Cập nhật trạng thái thành công"}
            )

    return JsonResponse({"success": False, "message": "Invalid request"})
