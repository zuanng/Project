from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.generic import CreateView, UpdateView
from django.urls import reverse_lazy
from .forms import (
    UserRegistrationForm,
    UserLoginForm,
    UserUpdateForm,
    CustomerProfileUpdateForm,
)
from .decorators import customer_required


# Function-Based Views
def register_view(request):
    """Đăng ký tài khoản"""
    if request.user.is_authenticated:
        return redirect("restaurant:home")

    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Đăng ký tài khoản thành công!")
            return redirect("restaurant:home")
        else:
            messages.error(
                request, "Có lỗi xảy ra. Vui lòng kiểm tra lại thông tin."
            )
    else:
        form = UserRegistrationForm()

    return render(request, "accounts/register.html", {"form": form})


def login_view(request):
    """Đăng nhập"""
    if request.user.is_authenticated:
        return redirect("restaurant:home")

    if request.method == "POST":
        form = UserLoginForm(data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get("username")
            password = form.cleaned_data.get("password")
            user = authenticate(username=username, password=password)

            if user is not None:
                login(request, user)
                messages.success(request, f"Chào mừng {user.username}!")

                # Redirect based on role
                next_url = request.GET.get("next")
                if next_url:
                    return redirect(next_url)
                elif user.is_admin or user.is_superuser:
                    return redirect("dashboard:admin_dashboard")
                else:
                    return redirect("restaurant:home")
        else:
            messages.error(request, "Tên đăng nhập hoặc mật khẩu không đúng.")
    else:
        form = UserLoginForm()

    return render(request, "accounts/login.html", {"form": form})


def logout_view(request):
    """Đăng xuất"""
    logout(request)
    messages.info(request, "Bạn đã đăng xuất.")
    return redirect("restaurant:home")


@login_required
def profile_view(request):
    """Xem thông tin cá nhân"""
    user = request.user
    context = {
        "user": user,
    }

    # Nếu là khách hàng thì lấy thêm profile
    if user.is_customer:
        context["profile"] = user.customer_profile

    return render(request, "accounts/profile.html", context)


@login_required
def profile_edit_view(request):
    """Chỉnh sửa thông tin cá nhân"""
    if request.method == "POST":
        user_form = UserUpdateForm(
            request.POST, request.FILES, instance=request.user
        )

        # Nếu là khách hàng thì có thêm profile form
        if request.user.is_customer:
            profile_form = CustomerProfileUpdateForm(
                request.POST, instance=request.user.customer_profile
            )

            if user_form.is_valid() and profile_form.is_valid():
                user_form.save()
                profile_form.save()
                messages.success(request, "Cập nhật thông tin thành công!")
                return redirect("accounts:profile")
        else:
            if user_form.is_valid():
                user_form.save()
                messages.success(request, "Cập nhật thông tin thành công!")
                return redirect("accounts:profile")
    else:
        user_form = UserUpdateForm(instance=request.user)
        profile_form = None

        if request.user.is_customer:
            profile_form = CustomerProfileUpdateForm(
                instance=request.user.customer_profile
            )

    context = {
        "user_form": user_form,
        "profile_form": profile_form,
    }

    return render(request, "accounts/profile_edit.html", context)
