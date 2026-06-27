from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from accounts.models import User


class Table(models.Model):
    TABLE_STATUS_CHOICES = (
        ("available", "Có sẵn"),
        ("occupied", "Đang sử dụng"),
        ("reserved", "Đã đặt"),
        ("maintenance", "Bảo trì"),
    )

    number = models.CharField(
        max_length=10, unique=True, verbose_name="Số bàn"
    )
    capacity = models.IntegerField(
        validators=[MinValueValidator(1)], verbose_name="Sức chứa"
    )
    location = models.CharField(
        max_length=50,
        choices=(
            ("indoor", "Trong nhà"),
            ("outdoor", "Ngoài trời"),
            ("vip", "Phòng VIP"),
        ),
        default="indoor",
        verbose_name="Vị trí",
    )
    status = models.CharField(
        max_length=20,
        choices=TABLE_STATUS_CHOICES,
        default="available",
        verbose_name="Trạng thái",
    )
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")
    description = models.TextField(blank=True, verbose_name="Mô tả")

    class Meta:
        verbose_name = "Bàn"
        verbose_name_plural = "Bàn"
        ordering = ["number"]

    def __str__(self):
        return f"Bàn {self.number} ({self.capacity} người)"


class Reservation(models.Model):
    STATUS_CHOICES = (
        ("pending", "Chờ xác nhận"),
        ("confirmed", "Đã xác nhận"),
        ("checked_in", "Đã check-in"),
        ("completed", "Hoàn thành"),
        ("cancelled", "Đã hủy"),
        ("no_show", "Không đến"),
    )

    # Reservation info
    reservation_number = models.CharField(
        max_length=20, unique=True, editable=False
    )
    customer = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name="reservations"
    )
    table = models.ForeignKey(
        Table,
        on_delete=models.SET_NULL,
        null=True,
        related_name="reservations",
    )

    # Guest info
    guest_name = models.CharField(max_length=100, verbose_name="Tên khách")
    guest_phone = models.CharField(max_length=15, verbose_name="SĐT khách")
    guest_email = models.EmailField(blank=True, verbose_name="Email")

    # Booking details
    date = models.DateField(verbose_name="Ngày đặt")
    time = models.TimeField(verbose_name="Giờ đặt")
    number_of_guests = models.IntegerField(
        validators=[MinValueValidator(1)], verbose_name="Số khách"
    )
    duration_hours = models.IntegerField(
        default=2, verbose_name="Thời gian (giờ)"
    )

    # Additional info
    special_request = models.TextField(
        blank=True, verbose_name="Yêu cầu đặc biệt"
    )
    occasion = models.CharField(
        max_length=50,
        blank=True,
        choices=(
            ("birthday", "Sinh nhật"),
            ("anniversary", "Kỷ niệm"),
            ("business", "Công việc"),
            ("other", "Khác"),
        ),
        verbose_name="Dịp",
    )

    # Status
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )

    # Deposit
    deposit_required = models.BooleanField(
        default=False, verbose_name="Yêu cầu đặt cọc"
    )
    deposit_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Số tiền cọc"
    )
    deposit_paid = models.BooleanField(
        default=False, verbose_name="Đã đặt cọc"
    )

    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Đặt bàn"
        verbose_name_plural = "Đặt bàn"
        ordering = ["-date", "-time"]

    def __str__(self):
        return f"Reservation #{self.reservation_number} - {self.guest_name}"

    def save(self, *args, **kwargs):
        if not self.reservation_number:
            import time

            self.reservation_number = f"RES{int(time.time())}"
        super().save(*args, **kwargs)

    @property
    def is_upcoming(self):
        """Kiểm tra đặt bàn sắp tới"""
        from datetime import datetime

        reservation_datetime = datetime.combine(self.date, self.time)
        return reservation_datetime > timezone.now() and self.status in [
            "pending",
            "confirmed",
        ]

    @property
    def is_past(self):
        """Kiểm tra đặt bàn đã qua"""
        from datetime import datetime

        reservation_datetime = datetime.combine(self.date, self.time)
        return reservation_datetime < timezone.now()

    def get_status_display_class(self):
        """Trả về class Bootstrap cho status badge"""
        status_classes = {
            "pending": "warning",
            "confirmed": "success",
            "checked_in": "primary",
            "completed": "success",
            "cancelled": "danger",
            "no_show": "secondary",
        }
        return status_classes.get(self.status, "secondary")
