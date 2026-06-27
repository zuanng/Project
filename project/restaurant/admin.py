from django.contrib import admin
from .models import (
    Category, MenuItem, MenuItemImage, Chef, Review,
    TableOrder, OrderItem,
)


class MenuItemImageInline(admin.TabularInline):
    model = MenuItemImage
    extra = 1


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["price", "get_total_price"]

    def get_total_price(self, obj):
        return f"{obj.get_total_price():,.0f}đ"

    get_total_price.short_description = "Thành tiền"


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["name"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = [
        "name",
        "category",
        "price",
        "discount_price",
        "is_available",
        "is_featured",
        "views_count",
    ]
    list_filter = [
        "category",
        "is_available",
        "is_featured",
        "is_vegetarian",
        "is_spicy",
    ]
    search_fields = ["name", "description"]
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MenuItemImageInline]
    readonly_fields = ["views_count"]


@admin.register(Chef)
class ChefAdmin(admin.ModelAdmin):
    list_display = ["name", "position", "is_active", "order"]
    list_filter = ["is_active"]
    search_fields = ["name", "position"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["user", "menu_item", "rating", "created_at"]
    list_filter = ["rating", "created_at"]
    search_fields = ["user__username", "menu_item__name", "comment"]


@admin.register(TableOrder)
class TableOrderAdmin(admin.ModelAdmin):
    list_display = [
        "order_number", "table", "status", "payment_status",
        "total_amount", "created_at",
    ]
    list_filter = ["status", "payment_status", "created_at"]
    search_fields = ["order_number"]
    readonly_fields = [
        "order_number", "subtotal", "discount",
        "total_amount", "created_at", "updated_at",
    ]
    inlines = [OrderItemInline]

    actions = ["mark_as_confirmed", "mark_as_completed"]

    def mark_as_confirmed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.filter(status="pending").update(
            status="confirmed", confirmed_at=timezone.now()
        )
        self.message_user(request, f"Đã xác nhận {updated} order")

    mark_as_confirmed.short_description = "Xác nhận order đã chọn"

    def mark_as_completed(self, request, queryset):
        from django.utils import timezone
        updated = queryset.update(
            status="completed", completed_at=timezone.now()
        )
        self.message_user(request, f"Đã hoàn thành {updated} order")

    mark_as_completed.short_description = "Đánh dấu hoàn thành"
