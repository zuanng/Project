from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver


class User(AbstractUser):
    ROLE_CHOICES = (
        ("customer", "Khách hàng"),
        ("staff", "Nhân viên"),
        ("admin", "Quản trị viên"),
    )

    role = models.CharField(
        max_length=20,
        choices=ROLE_CHOICES,
        default="customer",
        verbose_name="Vai trò",
    )
    phone = models.CharField(
        max_length=15, blank=True, verbose_name="Số điện thoại"
    )
    avatar = models.ImageField(
        upload_to="avatars/",
        blank=True,
        null=True,
        verbose_name="Ảnh đại diện",
    )
    date_of_birth = models.DateField(
        blank=True, null=True, verbose_name="Ngày sinh"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Người dùng"
        verbose_name_plural = "Người dùng"

    def __str__(self):
        return self.username

    @property
    def is_customer(self):
        return self.role == "customer"

    @property
    def is_staff_member(self):
        return self.role in ["staff", "admin"]

    @property
    def is_admin(self):
        return self.role == "admin"


class CustomerProfile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="customer_profile"
    )
    address = models.TextField(blank=True, verbose_name="Địa chỉ")
    city = models.CharField(
        max_length=100, blank=True, verbose_name="Thành phố"
    )
    postal_code = models.CharField(
        max_length=10, blank=True, verbose_name="Mã bưu điện"
    )
    loyalty_points = models.IntegerField(
        default=0, verbose_name="Điểm tích lũy"
    )

    class Meta:
        verbose_name = "Hồ sơ khách hàng"
        verbose_name_plural = "Hồ sơ khách hàng"

    def __str__(self):
        return f"Profile của {self.user.username}"


# Signal để tự động tạo profile khi user được tạo
@receiver(post_save, sender=User)
def create_customer_profile(sender, instance, created, **kwargs):
    if created and instance.role == "customer":
        CustomerProfile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_customer_profile(sender, instance, **kwargs):
    if instance.role == "customer":
        if hasattr(instance, "customer_profile"):
            instance.customer_profile.save()
        else:
            CustomerProfile.objects.create(user=instance)
