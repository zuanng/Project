from django.db import models
from django.utils.text import slugify
from django.urls import reverse
from django.core.validators import MinValueValidator
from decimal import Decimal
from accounts.models import User


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên danh mục")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    description = models.TextField(blank=True, verbose_name="Mô tả")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="Kích hoạt")
    order = models.IntegerField(default=0, verbose_name="Thứ tự")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Danh mục"
        verbose_name_plural = "Danh mục"
        ordering = ["order", "name"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse(
            "restaurant:category_detail", kwargs={"slug": self.slug}
        )


class MenuItem(models.Model):
    name = models.CharField(max_length=200, verbose_name="Tên món")
    slug = models.SlugField(unique=True, verbose_name="Slug")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="menu_items",
        verbose_name="Danh mục",
    )
    description = models.TextField(verbose_name="Mô tả")
    recipe = models.TextField(blank=True, verbose_name="Công thức")
    ingredients = models.TextField(blank=True, verbose_name="Nguyên liệu")
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Giá"
    )
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name="Giá khuyến mãi",
    )
    image = models.ImageField(upload_to="menu/", verbose_name="Ảnh")
    is_available = models.BooleanField(default=True, verbose_name="Còn hàng")
    is_featured = models.BooleanField(default=False, verbose_name="Nổi bật")
    is_vegetarian = models.BooleanField(default=False, verbose_name="Chay")
    is_spicy = models.BooleanField(default=False, verbose_name="Cay")
    preparation_time = models.IntegerField(
        default=15, verbose_name="Thời gian chuẩn bị (phút)"
    )
    views_count = models.IntegerField(default=0, verbose_name="Lượt xem")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Món ăn"
        verbose_name_plural = "Món ăn"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("restaurant:menu_detail", kwargs={"slug": self.slug})

    @property
    def get_price(self):
        """Trả về giá hiện tại (có khuyến mãi thì lấy giá KM)"""
        if self.discount_price:
            return self.discount_price
        return self.price

    @property
    def discount_percentage(self):
        """Tính % giảm giá"""
        if self.discount_price and self.discount_price < self.price:
            return int(((self.price - self.discount_price) / self.price) * 100)
        return 0


class MenuItemImage(models.Model):
    """Ảnh phụ cho món ăn"""

    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name="images"
    )
    image = models.ImageField(upload_to="menu/gallery/")
    caption = models.CharField(max_length=200, blank=True)
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"Image for {self.menu_item.name}"


class Chef(models.Model):
    name = models.CharField(max_length=100, verbose_name="Tên")
    slug = models.SlugField(unique=True)
    position = models.CharField(max_length=100, verbose_name="Chức vụ")
    bio = models.TextField(verbose_name="Tiểu sử")
    specialization = models.CharField(
        max_length=200, blank=True, verbose_name="Chuyên môn"
    )
    image = models.ImageField(upload_to="chefs/", verbose_name="Ảnh")
    facebook = models.URLField(blank=True)
    instagram = models.URLField(blank=True)
    twitter = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, verbose_name="Đang làm việc")
    order = models.IntegerField(default=0)

    class Meta:
        verbose_name = "Đầu bếp"
        verbose_name_plural = "Đầu bếp"
        ordering = ["order", "name"]

    def __str__(self):
        return f"{self.name} - {self.position}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Review(models.Model):
    """Đánh giá món ăn"""

    menu_item = models.ForeignKey(
        MenuItem, on_delete=models.CASCADE, related_name="reviews"
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Đánh giá"
        verbose_name_plural = "Đánh giá"
        ordering = ["-created_at"]
        unique_together = ["menu_item", "user"]

    def __str__(self):
        return f"{self.user.username} - {self.menu_item.name} ({self.rating}★)"


class TableOrder(models.Model):
    """Order tại bàn — khách đặm món tại nhà hàng"""

    STATUS_CHOICES = (
        ("pending", "Chờ xác nhận"),
        ("confirmed", "Đã xác nhận"),
        ("preparing", "Đang pha chế"),
        ("serving", "Đang phục vụ"),
        ("completed", "Hoàn thành"),
        ("cancelled", "Đã hủy"),
    )

    PAYMENT_STATUS_CHOICES = (
        ("pending", "Chờ thanh toán"),
        ("paid", "Đã thanh toán"),
    )

    order_number = models.CharField(max_length=20, unique=True, editable=False)
    table = models.ForeignKey(
        "reservations.Table",
        on_delete=models.SET_NULL,
        null=True,
        related_name="orders",
        verbose_name="Bàn",
    )
    customer = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="table_orders",
        verbose_name="Khách hàng",
    )
    server = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="served_orders",
        verbose_name="Nhân viên phục vụ",
    )

    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending"
    )
    payment_status = models.CharField(
        max_length=20, choices=PAYMENT_STATUS_CHOICES, default="pending"
    )

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Tạm tính"
    )
    discount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Giảm giá"
    )
    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="Tổng tiền"
    )

    note = models.TextField(blank=True, verbose_name="Ghi chú")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Order tại bàn"
        verbose_name_plural = "Order tại bàn"
        ordering = ["-created_at"]

    def __str__(self):
        return f"Order #{self.order_number} - Bàn {self.table}"

    def save(self, *args, **kwargs):
        if not self.order_number:
            import time
            self.order_number = f"TB{int(time.time())}"
        super().save(*args, **kwargs)

    def calculate_total(self):
        self.subtotal = sum(
            item.get_total_price() for item in self.items.all()
        )
        self.total_amount = self.subtotal - self.discount
        self.save()

    def get_status_display_class(self):
        status_classes = {
            "pending": "warning",
            "confirmed": "info",
            "preparing": "primary",
            "serving": "info",
            "completed": "success",
            "cancelled": "danger",
        }
        return status_classes.get(self.status, "secondary")


class OrderItem(models.Model):
    """Chi tiết order tại bàn"""

    order = models.ForeignKey(
        TableOrder, on_delete=models.CASCADE, related_name="items"
    )
    menu_item = models.ForeignKey(MenuItem, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(
        default=1, validators=[MinValueValidator(1)]
    )
    price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name="Đơn giá"
    )
    note = models.TextField(blank=True, verbose_name="Ghi chú món")

    class Meta:
        verbose_name = "Chi tiết order"
        verbose_name_plural = "Chi tiết order"

    def __str__(self):
        return f"{self.quantity}x {self.menu_item.name}"

    def get_total_price(self):
        return self.price * self.quantity
