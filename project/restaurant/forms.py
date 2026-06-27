from django import forms
from .models import Review


class CartAddItemForm(forms.Form):
    """Form thêm món vào giỏ hàng"""

    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "style": "width: 80px;"}
        ),
    )
    override = forms.BooleanField(
        required=False, initial=False, widget=forms.HiddenInput
    )


class MenuItemSearchForm(forms.Form):
    """Form tìm kiếm món ăn"""

    q = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Tìm kiếm món ăn...",
            }
        ),
    )
    category = forms.ChoiceField(
        required=False,
        choices=[],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
    min_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Giá từ"}
        ),
    )
    max_price = forms.DecimalField(
        required=False,
        widget=forms.NumberInput(
            attrs={"class": "form-control", "placeholder": "Giá đến"}
        ),
    )
    vegetarian = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={"class": "form-check-input"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from .models import Category

        categories = Category.objects.filter(is_active=True)
        self.fields["category"].choices = [("", "Tất cả danh mục")] + [
            (cat.id, cat.name) for cat in categories
        ]


class ReviewForm(forms.ModelForm):
    """Form đánh giá món ăn"""

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.Select(
                choices=[(i, f"{i} sao") for i in range(1, 6)],
                attrs={"class": "form-select"},
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Chia sẻ trải nghiệm của bạn...",
                }
            ),
        }
