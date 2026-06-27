from django import forms
from .models import Reservation, Table
from django.utils import timezone
from datetime import datetime, timedelta

class ReservationForm(forms.ModelForm):
    """Form đặt bàn"""
    
    class Meta:
        model = Reservation
        fields = [
            'guest_name',
            'guest_phone',
            'guest_email',
            'date',
            'time',
            'number_of_guests',
            'occasion',
            'special_request'
        ]
        widgets = {
            'guest_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Họ và tên'
            }),
            'guest_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Số điện thoại'
            }),
            'guest_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email (tùy chọn)'
            }),
            'date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'min': timezone.now().date()
            }),
            'time': forms.TimeInput(attrs={
                'class': 'form-control',
                'type': 'time'
            }),
            'number_of_guests': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 20
            }),
            'occasion': forms.Select(attrs={'class': 'form-select'}),
            'special_request': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Yêu cầu đặc biệt (tùy chọn)'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Pre-fill user information
        if user and user.is_authenticated:
            self.fields['guest_name'].initial = user.get_full_name()
            self.fields['guest_phone'].initial = user.phone
            self.fields['guest_email'].initial = user.email
    
    def clean_date(self):
        """Validate date không được trong quá khứ"""
        date = self.cleaned_data.get('date')
        if date < timezone.now().date():
            raise forms.ValidationError('Không thể đặt bàn cho ngày trong quá khứ')
        return date
    
    def clean(self):
        """Validate datetime và kiểm tra bàn trống"""
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')
        number_of_guests = cleaned_data.get('number_of_guests')
        
        if date and time:
            # Tạo datetime với timezone aware
            naive_datetime = datetime.combine(date, time)
            reservation_datetime = timezone.make_aware(
                naive_datetime,
                timezone.get_current_timezone()
            )
            
            # Lấy thời gian hiện tại (timezone aware)
            now = timezone.now()
            
            # Kiểm tra thời gian đặt bàn
            # Phải đặt trước ít nhất 2 giờ
            min_booking_time = now + timedelta(hours=2)
            if reservation_datetime < min_booking_time:
                raise forms.ValidationError(
                    'Vui lòng đặt bàn trước ít nhất 2 giờ'
                )
            
            # Kiểm tra giờ hoạt động (10:00 - 22:00)
            if time.hour < 10 or time.hour >= 22:
                raise forms.ValidationError(
                    'Nhà hàng chỉ phục vụ từ 10:00 đến 22:00'
                )
        
        return cleaned_data