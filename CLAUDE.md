# CLAUDE.md — Hệ thống Quản lý Nhà hàng FourSeason

## 📋 Tổng quan dự án

**Đề tài:** Phát triển hệ thống quản lý nhà hàng tích hợp hệ thống gợi ý món ăn thông minh dựa trên Machine Learning.

**Mục tiêu:** Xây dựng hệ thống quản lý nhà hàng hoàn chỉnh, tập trung vào **trải nghiệm tại nhà hàng** (đặt bàn, order tại bàn, quản lý nhà bếp) và **gợi ý món ăn bằng ML**.

**Công nghệ:**
- **Backend:** Django 5.2.4, Python 3.13
- **Database:** MySQL (`restaurant_db`)
- **Frontend:** Bootstrap 5, Font Awesome 6, Chart.js
- **Timezone:** Asia/Ho_Chi_Minh

## 🏗️ Cấu trúc project

```
Project/
├── CLAUDE.md
├── project2/                    # Django project root
│   ├── manage.py
│   ├── project2/                # Project settings
│   │   ├── settings.py
│   │   ├── urls.py              # Root URL config
│   │   ├── wsgi.py
│   │   └── asgi.py
│   ├── accounts/                # App: Quản lý tài khoản
│   ├── restaurant/              # App: Menu, order tại bàn, đầu bếp, đánh giá
│   ├── reservations/            # App: Đặt bàn, quản lý bàn
│   ├── dashboard/               # App: Admin dashboard, báo cáo
│   ├── media/                   # Uploaded files
│   │   └── menu/
│   └── templates/
│       └── base.html            # Base template
└── venv/                        # Python virtual environment
```

## 📱 Django Apps

### 1. `accounts` — Quản lý người dùng

**Models:**
- `User` (extends `AbstractUser`): Custom user với `role` (customer/staff/admin), `phone`, `avatar`, `date_of_birth`
- `CustomerProfile`: Một-một với User, chứa `address`, `city`, `postal_code`, `loyalty_points`
- Signal tự động tạo `CustomerProfile` khi user có role `customer` được tạo

**Views:** `register_view`, `login_view`, `logout_view`, `profile_view`, `profile_edit_view`

**URLs:** `accounts/register`, `accounts/login`, `accounts/logout`, `accounts/profile`, `accounts/profile_edit`

**Decorators:**
- `customer_required` — chỉ khách hàng
- `admin_required` — chỉ admin
- `staff_required` — nhân viên hoặc admin

### 2. `restaurant` — Lõi chính của hệ thống

**Models:**
- `Category`: Danh mục món ăn (name, slug, image, is_active, order)
- `MenuItem`: Món ăn (name, slug, category, description, recipe, ingredients, price, discount_price, image, is_available, is_featured, is_vegetarian, is_spicy, preparation_time, views_count)
- `MenuItemImage`: Ảnh phụ cho món ăn
- `Chef`: Đầu bếp (name, position, bio, specialization, image, social links)
- `Review`: Đánh giá món ăn (menu_item, user, rating 1-5, comment)
- `TableOrder`: **Order tại bàn** (order_number, table→reservations.Table, customer, server, status, payment_status, subtotal, discount, total_amount, note)
- `OrderItem`: Chi tiết order (order→TableOrder, menu_item, quantity, price, note)

**Trạng thái TableOrder:**
- `pending` → `confirmed` → `preparing` → `serving` → `completed`
- `cancelled` (hủy ở bất kỳ bước nào)

**Cart System** (`restaurant/cart.py`):
- Session-based cart, lưu trong `request.session['cart']`
- Hỗ trợ: add, remove, update quantity, clear, get_total_price

**Views:**
- `home`: Trang chủ (featured items, categories, chefs)
- `menu_list`: Danh sách món (search, filter category/giá/vegetarian, sort, pagination)
- `menu_detail`: Chi tiết món (reviews, related items, add to cart)
- `category_detail`: Món theo danh mục
- `cart_add`/`cart_remove`/`cart_detail`: Quản lý giỏ hàng
- `cart_submit`: **Gửi order cho nhà bếp** (chuyển cart → TableOrder + OrderItem)
- `chefs_list`: Danh sách đầu bếp

**URLs:**
- `/` → home
- `/menu/` → menu_list
- `/menu/<slug>/` → menu_detail
- `/category/<slug>/` → category_detail
- `/cart/` → cart_detail
- `/cart/add/<id>/` → cart_add
- `/cart/remove/<id>/` → cart_remove
- `/cart/submit/` → cart_submit
- `/chefs/` → chefs_list

### 3. `reservations` — Đặt bàn

**Models:**
- `Table`: Bàn ăn (number, capacity, location [indoor/outdoor/vip], status [available/occupied/reserved/maintenance], is_active)
- `Reservation`: Đặt bàn (reservation_number, customer, table, guest_name/phone/email, date, time, number_of_guests, duration_hours, special_request, occasion, status, deposit info)

**Trạng thái Reservation:**
- `pending` → `confirmed` → `checked_in` → `completed`
- `cancelled`, `no_show`

**Views:** `reservation_create`, `reservation_list`, `reservation_detail`, `cancel_reservation`

**URLs:** `reservations/book/`, `reservations/my-reservations/`, `reservations/reservation/<number>/`, `reservations/reservation/<number>/cancel/`

### 4. `dashboard` — Admin dashboard

**Models:** `SystemSettings` (key-value config)

**Views:**
- `admin_dashboard`: Tổng quan (stats, revenue chart, top items, recent orders/reservations/reviews)
- `orders_management`: Quản lý order tại bàn (filter theo status/payment/bàn/ngày)
- `reservations_management`: Quản lý đặt bàn
- `revenue_report`: Báo cáo doanh thu (theo danh mục, vị trí bàn, top customers)
- `menu_statistics`: Thống kê món ăn (bán chạy, theo danh mục, rating, low performing)
- `customer_statistics`: Thống kê khách hàng (tổng, mới, top spenders, active/inactive)
- `api_revenue_chart`: API cho Chart.js
- `update_order_status`: AJAX cập nhật trạng thái order
- `update_payment_status`: AJAX cập nhật trạng thái thanh toán
- `update_reservation_status`: AJAX cập nhật trạng thái đặt bàn

**URLs:**
- `/dashboard/` → admin_dashboard
- `/dashboard/orders/` → orders_management
- `/dashboard/reservations/` → reservations_management
- `/dashboard/revenue/` → revenue_report
- `/dashboard/menu-stats/` → menu_statistics
- `/dashboard/customer-stats/` → customer_statistics
- `/dashboard/api/revenue-chart/` → api_revenue_chart
- `/dashboard/api/order/<id>/status/` → update_order_status
- `/dashboard/api/order/<id>/payment-status/` → update_payment_status
- `/dashboard/api/reservation/<id>/status/` → update_reservation_status

## ⚙️ Cài đặt & Chạy

```bash
# Kích hoạt virtual environment
source venv/bin/activate

# Chạy migrations
cd project2
python manage.py migrate

# Tạo superuser
python manage.py createsuperuser

# Chạy development server
python manage.py runserver
```

**Database:** MySQL — database `restaurant_db`, user `restaurant_user`

## 🔑 Quy ước quan trọng

### Tên biến/tiếng Việt
- Models dùng `verbose_name` tiếng Việt (hiển thị trong admin)
- Status choices dùng tiếng Việt (hiển thị cho user)
- Code logic bằng tiếng Anh

### Order number format
- TableOrder: `TB` + timestamp (ví dụ: `TB1718886400`)
- Reservation: `RES` + timestamp (ví dụ: `RES1718886400`)

### Cart flow
1. User chọn món → `cart_add` (POST)
2. Xem giỏ → `cart_detail`
3. Gửi order → `cart_submit` (login required) → tạo `TableOrder` + `OrderItem` → clear cart
4. Nhân viên admin xác nhận qua dashboard

### Role-based access
- **Customer:** đặt bàn, order món, xem profile, review
- **Staff:** (chưa phát triển đầy đủ)
- **Admin:** toàn quyền dashboard, quản lý order/reservation/menu

### Context processors
- `restaurant.context_processors.cart` — biến `cart` available trong mọi template

## 📝 Kế hoạch phát triển tiếp theo

### Ưu tiên cao (tuần 8-10)
1. **Hệ thống gợi ý món ăn ML** — collaborative filtering hoặc content-based
2. **Giao diện nhà bếp (Kitchen Display)** — xem order đang chờ, cập nhật trạng thái
3. **Thanh toán tại quầy** — admin xác nhận thanh toán, in hóa đơn

### Ưu tiên trung bình (tuần 11-13)
4. **Quản lý kho nguyên liệu** — theo dõi tồn kho, cảnh báo
5. **Phân quyền nhân viên** — staff view riêng, phân công bàn
6. **Thông báo real-time** — WebSocket cho kitchen khi có order mới

### Ưu tiên thấp (tuần 14+)
7. **Mobile responsive** — tối ưu cho tablet (nhân viên), phone (khách)
8. **Báo cáo nâng cao** — xuất PDF/Excel, so sánh theo mùa
9. **Tích hợp ML nâng cao** — dự đoán nhu cầu, tối ưu menu

## ⚠️ Lưu ý khi code

- **Không tạo app `orders` cũ** — đã xóa, dùng `restaurant.TableOrder` thay thế
- **Không dùng `orders:` URL namespace** — đã xóa khỏi hệ thống
- **Khi thêm model mới** — chạy `makemigrations` + `migrate` ngay
- **Khi thay đổi model có FK cross-app** — kiểm tra import path (VD: `restaurant.TableOrder.table` → `"reservations.Table"`)
- **Template URLs** — luôn dùng `{% url 'app_name:url_name' %}`, không hardcode path
- **Admin actions** — thêm `short_description` cho custom actions
