from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from .models import MenuItem, Category, Chef, Review, TableOrder, OrderItem
from .cart import Cart
from .forms import CartAddItemForm, MenuItemSearchForm, ReviewForm


def home(request):
    """Trang chủ"""
    featured_items = MenuItem.objects.filter(
        is_featured=True, is_available=True
    )[:6]

    categories = Category.objects.filter(is_active=True)[:6]
    chefs = Chef.objects.filter(is_active=True)[:4]

    context = {
        "featured_items": featured_items,
        "categories": categories,
        "chefs": chefs,
    }
    return render(request, "restaurant/home.html", context)


def menu_list(request):
    """Danh sách món ăn với tìm kiếm và filter"""
    menu_items = MenuItem.objects.filter(is_available=True).annotate(
        avg_rating=Avg("reviews__rating"), review_count=Count("reviews")
    )

    # Search form
    form = MenuItemSearchForm(request.GET)

    # Tìm kiếm theo tên
    query = request.GET.get("q")
    if query:
        menu_items = menu_items.filter(
            Q(name__icontains=query)
            | Q(description__icontains=query)
            | Q(ingredients__icontains=query)
        )

    # Filter theo category
    category_id = request.GET.get("category")
    if category_id:
        menu_items = menu_items.filter(category_id=category_id)

    # Filter theo giá
    min_price = request.GET.get("min_price")
    if min_price:
        menu_items = menu_items.filter(price__gte=min_price)

    max_price = request.GET.get("max_price")
    if max_price:
        menu_items = menu_items.filter(price__lte=max_price)

    # Filter vegetarian
    if request.GET.get("vegetarian"):
        menu_items = menu_items.filter(is_vegetarian=True)

    # Sorting
    sort_by = request.GET.get("sort", "-created_at")
    valid_sorts = ["-created_at", "price", "-price", "name"]
    if sort_by in valid_sorts:
        menu_items = menu_items.order_by(sort_by)

    # Pagination
    paginator = Paginator(menu_items, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "form": form,
        "total_items": menu_items.count(),
    }
    return render(request, "restaurant/menu_list.html", context)


def menu_detail(request, slug):
    """Chi tiết món ăn"""
    menu_item = get_object_or_404(MenuItem, slug=slug)

    # Tăng lượt xem
    menu_item.views_count += 1
    menu_item.save(update_fields=["views_count"])

    # Lấy reviews
    reviews = menu_item.reviews.select_related("user")[:10]
    avg_rating = reviews.aggregate(Avg("rating"))["rating__avg"]

    # Form thêm vào giỏ
    cart_form = CartAddItemForm()

    # Form đánh giá
    review_form = None
    user_review = None
    if request.user.is_authenticated:
        user_review = Review.objects.filter(
            menu_item=menu_item, user=request.user
        ).first()

        if request.method == "POST":
            review_form = ReviewForm(request.POST, instance=user_review)
            if review_form.is_valid():
                review = review_form.save(commit=False)
                review.menu_item = menu_item
                review.user = request.user
                review.save()
                messages.success(request, "Cảm ơn bạn đã đánh giá!")
                return redirect("restaurant:menu_detail", slug=slug)
        else:
            review_form = ReviewForm(instance=user_review)

    # Món ăn liên quan
    related_items = MenuItem.objects.filter(
        category=menu_item.category, is_available=True
    ).exclude(id=menu_item.id)[:4]

    context = {
        "menu_item": menu_item,
        "cart_form": cart_form,
        "reviews": reviews,
        "avg_rating": avg_rating,
        "review_count": reviews.count(),
        "review_form": review_form,
        "user_review": user_review,
        "related_items": related_items,
    }
    return render(request, "restaurant/menu_detail.html", context)


def category_detail(request, slug):
    """Xem món theo danh mục"""
    category = get_object_or_404(Category, slug=slug, is_active=True)
    menu_items = MenuItem.objects.filter(
        category=category, is_available=True
    ).annotate(avg_rating=Avg("reviews__rating"))

    # Pagination
    paginator = Paginator(menu_items, 6)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "category": category,
        "page_obj": page_obj,
    }
    return render(request, "restaurant/category_detail.html", context)


# ============ CART VIEWS ============


@require_POST
def cart_add(request, menu_item_id):
    """Thêm món vào giỏ hàng"""
    cart = Cart(request)
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    form = CartAddItemForm(request.POST)

    if form.is_valid():
        cd = form.cleaned_data
        cart.add(
            menu_item=menu_item,
            quantity=cd["quantity"],
            override_quantity=cd["override"],
        )
        messages.success(request, f'Đã thêm "{menu_item.name}" vào giỏ hàng!')

    return redirect("restaurant:cart_detail")


@require_POST
def cart_remove(request, menu_item_id):
    """Xóa món khỏi giỏ hàng"""
    cart = Cart(request)
    menu_item = get_object_or_404(MenuItem, id=menu_item_id)
    cart.remove(menu_item)
    messages.info(request, f'Đã xóa "{menu_item.name}" khỏi giỏ hàng!')
    return redirect("restaurant:cart_detail")


def cart_detail(request):
    """Xem giỏ hàng"""
    cart = Cart(request)

    # Form để update số lượng
    for item in cart:
        item["update_quantity_form"] = CartAddItemForm(
            initial={"quantity": item["quantity"], "override": True}
        )

    context = {
        "cart": cart,
    }
    return render(request, "restaurant/cart_detail.html", context)


def chefs_list(request):
    """Danh sách đầu bếp"""
    chefs = Chef.objects.filter(is_active=True)

    context = {
        "chefs": chefs,
    }
    return render(request, "restaurant/chefs_list.html", context)


@login_required
def cart_submit(request):
    """Gửi order tại bàn — chuyển giỏ hàng thành TableOrder"""
    cart = Cart(request)

    if len(cart) == 0:
        messages.warning(request, "Giỏ hàng trống!")
        return redirect("restaurant:menu_list")

    # Tạo TableOrder từ giỏ hàng
    order = TableOrder.objects.create(
        customer=request.user if request.user.is_authenticated else None,
        subtotal=cart.get_total_price(),
        total_amount=cart.get_total_price(),
    )

    # Tạo OrderItem từ cart
    for item in cart:
        OrderItem.objects.create(
            order=order,
            menu_item=item["menu_item"],
            quantity=item["quantity"],
            price=item["price"],
        )

    # Xóa giỏ hàng
    cart.clear()

    messages.success(
        request,
        f"Đã gửi order #{order.order_number} cho nhà bếp! "
        f"Nhân viên sẽ sớm xác nhận.",
    )
    return redirect("restaurant:cart_detail")
