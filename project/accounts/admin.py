from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, CustomerProfile


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = [
        "username",
        "email",
        "first_name",
        "last_name",
        "role",
        "is_active",
    ]
    list_filter = ["role", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "Thông tin bổ sung",
            {"fields": ("role", "phone", "avatar", "date_of_birth")},
        ),
    )

    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("Thông tin bổ sung", {"fields": ("role", "email", "phone")}),
    )


@admin.register(CustomerProfile)
class CustomerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "city", "loyalty_points"]
    search_fields = ["user__username", "user__email", "city"]
    list_filter = ["city"]
