from django.db import models
from django.utils import timezone
from datetime import timedelta


class SystemSettings(models.Model):
    """Cài đặt hệ thống"""

    key = models.CharField(max_length=100, unique=True)
    value = models.TextField()
    description = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cài đặt hệ thống"
        verbose_name_plural = "Cài đặt hệ thống"

    def __str__(self):
        return self.key
