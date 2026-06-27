from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from functools import wraps


def customer_required(view_func):
    """Decorator cho phép chỉ khách hàng truy cập"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.is_customer:
            return view_func(request, *args, **kwargs)
        return redirect("restaurant:home")

    return _wrapped_view


def admin_required(view_func):
    """Decorator cho phép chỉ admin truy cập"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.is_admin or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("restaurant:home")

    return _wrapped_view


def staff_required(view_func):
    """Decorator cho phép nhân viên và admin truy cập"""

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect("accounts:login")
        if request.user.is_staff_member or request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        return redirect("restaurant:home")

    return _wrapped_view
