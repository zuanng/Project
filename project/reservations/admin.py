from django.contrib import admin
from .models import Table, Reservation


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ["number", "capacity", "location", "status", "is_active"]
    list_filter = ["location", "status", "is_active"]
    search_fields = ["number"]


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = [
        "reservation_number",
        "customer",
        "table",
        "date",
        "time",
        "number_of_guests",
        "status",
        "created_at",
    ]
    list_filter = ["status", "date", "occasion"]
    search_fields = ["reservation_number", "customer__username", "guest_phone"]
    readonly_fields = ["reservation_number", "created_at", "updated_at"]

    fieldsets = (
        (
            "Thông tin đặt bàn",
            {"fields": ("reservation_number", "customer", "table", "status")},
        ),
        (
            "Thông tin khách",
            {"fields": ("guest_name", "guest_phone", "guest_email")},
        ),
        (
            "Chi tiết đặt bàn",
            {
                "fields": (
                    "date",
                    "time",
                    "number_of_guests",
                    "duration_hours",
                    "occasion",
                )
            },
        ),
        ("Yêu cầu đặc biệt", {"fields": ("special_request",)}),
        (
            "Đặt cọc",
            {"fields": ("deposit_required", "deposit_amount", "deposit_paid")},
        ),
        (
            "Thời gian",
            {"fields": ("created_at", "updated_at", "confirmed_at")},
        ),
    )

    actions = ["mark_as_confirmed", "mark_as_completed"]

    def mark_as_confirmed(self, request, queryset):
        from django.utils import timezone

        updated = queryset.filter(status="pending").update(
            status="confirmed", confirmed_at=timezone.now()
        )
        self.message_user(request, f"Đã xác nhận {updated} đặt bàn")

    mark_as_confirmed.short_description = "Xác nhận đặt bàn đã chọn"

    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status="completed")
        self.message_user(request, f"Đã hoàn thành {updated} đặt bàn")

    mark_as_completed.short_description = "Đánh dấu hoàn thành"
