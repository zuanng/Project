from decimal import Decimal
from django.conf import settings
from .models import MenuItem


class Cart:
    """Giỏ hàng sử dụng session"""

    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def add(self, menu_item, quantity=1, override_quantity=False):
        """Thêm món vào giỏ hàng"""
        menu_item_id = str(menu_item.id)
        if menu_item_id not in self.cart:
            self.cart[menu_item_id] = {
                "quantity": 0,
                "price": str(menu_item.get_price),
            }

        if override_quantity:
            self.cart[menu_item_id]["quantity"] = quantity
        else:
            self.cart[menu_item_id]["quantity"] += quantity

        self.save()

    def save(self):
        """Lưu giỏ hàng vào session"""
        self.session.modified = True

    def remove(self, menu_item):
        """Xóa món khỏi giỏ hàng"""
        menu_item_id = str(menu_item.id)
        if menu_item_id in self.cart:
            del self.cart[menu_item_id]
            self.save()

    def __iter__(self):
        """Lặp qua các món trong giỏ hàng"""
        menu_item_ids = self.cart.keys()
        menu_items = MenuItem.objects.filter(id__in=menu_item_ids)
        cart = self.cart.copy()

        for menu_item in menu_items:
            cart[str(menu_item.id)]["menu_item"] = menu_item

        for item in cart.values():
            item["price"] = Decimal(item["price"])
            item["total_price"] = item["price"] * item["quantity"]
            yield item

    def __len__(self):
        """Đếm tổng số món trong giỏ"""
        return sum(item["quantity"] for item in self.cart.values())

    def get_total_price(self):
        """Tính tổng giá trị giỏ hàng"""
        return sum(
            Decimal(item["price"]) * item["quantity"]
            for item in self.cart.values()
        )

    def clear(self):
        """Xóa toàn bộ giỏ hàng"""
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_item_quantity(self, menu_item_id):
        """Lấy số lượng của một món"""
        return self.cart.get(str(menu_item_id), {}).get("quantity", 0)
