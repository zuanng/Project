from django.urls import path
from . import views

app_name = "restaurant"

urlpatterns = [
    # Home
    path("", views.home, name="home"),
    # Menu
    path("menu/", views.menu_list, name="menu_list"),
    path("menu/<slug:slug>/", views.menu_detail, name="menu_detail"),
    # Category
    path(
        "category/<slug:slug>/", views.category_detail, name="category_detail"
    ),
    # Cart / Order tại bàn
    path("cart/", views.cart_detail, name="cart_detail"),
    path("cart/add/<int:menu_item_id>/", views.cart_add, name="cart_add"),
    path(
        "cart/remove/<int:menu_item_id>/",
        views.cart_remove,
        name="cart_remove",
    ),
    path("cart/submit/", views.cart_submit, name="cart_submit"),
    # Chefs
    path("chefs/", views.chefs_list, name="chefs_list"),
]
