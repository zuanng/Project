from django.urls import path
from . import views

app_name = "dashboard"

urlpatterns = [
    # Main dashboard
    path("", views.admin_dashboard, name="admin_dashboard"),
    # Management pages
    path("orders/", views.orders_management, name="orders_management"),
    path(
        "reservations/",
        views.reservations_management,
        name="reservations_management",
    ),
    # Reports
    path("revenue/", views.revenue_report, name="revenue_report"),
    path("menu-stats/", views.menu_statistics, name="menu_statistics"),
    path(
        "customer-stats/",
        views.customer_statistics,
        name="customer_statistics",
    ),
    # API endpoints
    path(
        "api/revenue-chart/", views.api_revenue_chart, name="api_revenue_chart"
    ),
    path(
        "api/order/<int:order_id>/status/",
        views.update_order_status,
        name="update_order_status",
    ),
    path(
        "api/reservation/<int:reservation_id>/status/",
        views.update_reservation_status,
        name="update_reservation_status",
    ),
]
