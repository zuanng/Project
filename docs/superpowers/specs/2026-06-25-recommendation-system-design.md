# FourSeason — Hệ thống Gợi Ý Món Ăn Thông Minh

> Spec đã duyệt: 2026-06-25

## 1. Tổng quan

Xây dựng module gợi ý món ăn cá nhân hóa cho khách hàng đã đăng nhập, hiển thị tại trang chủ. Hệ thống kết hợp Content-Based và Collaborative Filtering, dữ liệu từ lịch sử order và review hiện có.

**Mục tiêu đồ án:** Minh họa rõ ràng 2 thuật toán recommendation phổ biến, code thuần Python + Django ORM (không dùng ML library nặng), có test và giải thích được trong báo cáo.

## 2. Kiến trúc

```
restaurant/
├── recommender/                    # Module mới
│   ├── __init__.py
│   ├── engine.py                   # API chính: get_recommendations(user, n)
│   ├── strategies.py                 # Các chiến lược gợi ý
│   ├── scorer.py                   # Gộp điểm + normalize + lọc
│   └── tests.py                    # Unit tests
├── models.py                       # Thêm field tags vào MenuItem
├── views.py                        # home() gọi recommender.engine
└── templates/restaurant/
    └── home.html                   # Thêm section "Gợi ý cho bạn"
```

**Nguyên tắc:**
- `engine.py` là single entry point — view chỉ gọi 1 hàm
- `strategies.py` chứa logic thuần (không phụ thuộc Django request), test được độc lập
- `scorer.py` gộp kết quả, normalize, lọc
- Không model mới, không migration cho recommendation logic
- Thêm 1 migration cho `MenuItem.tags`

## 3. Model thay đổi

### MenuItem.tags (mới)

```python
tags = models.CharField(
    max_length=300,
    blank=True,
    verbose_name="Tags",
    help_text="Phân cách bằng dấu phẩy. VD: nướng,hấp,hải sản,bò",
)
```

- Admin nhập tay
- Dùng cho Content-Based tag_match
- Migration: `python manage.py makemigrations restaurant && python manage.py migrate`

## 4. Thuật toán

### 4.1 Content-Based Strategy (trọng số 0.6)

```
score_content(item) =
    category_match(item, user_top_categories) * 0.4
  + tag_match(item, user_top_tags) * 0.3
  + rating_boost(item) * 0.2
  + discount_boost(item) * 0.1
```

- `user_top_categories`: top 3 category user đã order/rating≥4 nhiều nhất
- `user_top_tags`: set tags xuất hiện trong món user đã order/rating≥4
- `category_match`: 1.0 nếu item.category ∈ top_categories, else 0
- `tag_match`: Jaccard similarity — |item.tags ∩ user_top_tags| / |item.tags ∪ user_top_tags|, mặc định 0 nếu cả hai rỗng
- `rating_boost`: item.avg_rating / 5.0
- `discount_boost`: 0.1 nếu discount_price tồn tại và < price, else 0

### 4.2 Collaborative Strategy (trọng số 0.4)

```
1. Lấy set món user A đã "thích" (order hoặc rating≥4)
2. Tìm user khác thỏa 2 điều kiện:
   a. Overlap: |items_A ∩ items_B| >= 3  (phải có ít nhất 3 món chung)
   b. Jaccard similarity = |items_A ∩ items_B| / |items_A ∪ items_B|
3. Gộp món mà similar users đã thích mà A chưa thích
4. score_collab(item) = tổng Jaccard similarity của những user đã thích item
```

- Overlap threshold: ≥ 3 (tăng từ 2 để giảm noise)
- Similarity metric: Jaccard (dùng để tính điểm, không dùng làm ngưỡng)
- Chỉ tính trên user có ≥ 1 món "thích"

### 4.3 Scorer.merge()

```python
def merge(strategies_scores, weights, n=6):
    # 1. Weighted sum
    final = {}
    for scores, w in zip(strategies_scores, weights):
        for item_id, s in scores.items():
            final[item_id] = final.get(item_id, 0) + s * w

    # 2. Min-max normalize trên TẤT CẢ items
    values = list(final.values())
    max_val, min_val = max(values), min(values)
    for item_id in final:
        if max_val == min_val:
            final[item_id] = 0.5
        else:
            final[item_id] = (final[item_id] - min_val) / (max_val - min_val)

    # 3. Pop recent_items (món order trong 7 ngày gần nhất)
    recent = get_user_recent_items(user, days=7)
    for item_id in recent:
        final.pop(item_id, None)

    # 4. Filter is_available + sort giảm dần
    available_items = MenuItem.objects.filter(
        id__in=final.keys(), is_available=True
    ).in_bulk()

    result = []
    for item_id, score in sorted(final.items(), key=lambda x: (-x[1], -available_items[x_id].views_count if x_id in available_items else 0)):
        if item_id in available_items:
            result.append((available_items[item_id], score))

    return result[:n]
```

**Lưu ý quan trọng:** Normalize phải trước khi pop recent_items. Nếu pop trước → min/max tính trên tập thiếu → điểm item còn lại bị lệch.

### 4.4 Fallback Strategy (khách vãng lai hoặc không đủ data)

```
score_trending(item) =
    views_normalized(item) * 0.4
  + rating_normalized(item) * 0.4
  + recency(item) * 0.2
```

- `views_normalized`: item.views_count / max_views_toàn_menu
- `rating_normalized`: avg_rating / 5.0
- `recency`:
  - 1.0 nếu created_at trong 7 ngày
  - 0.5 nếu created_at trong 8-30 ngày
  - 0.0 nếu > 30 ngày

## 5. Data flow

```
home() view
    │
    ├── user.is_authenticated?
    │   ├── NO → featured + trending
    │   └── YES →
    │       ├── Có ≥1 order HOẶC ≥1 review?
    │       │   ├── NO → featured + trending
    │       │   └── YES →
    │       │       └── engine.get_recommendations(user, n=6)
    │       │           ├── ContentBasedStrategy.score(user)
    │       │           ├── CollaborativeStrategy.score(user)
    │       │           └── Scorer.merge([content, collab], [0.6, 0.4])
    │       │               → [(MenuItem, score), ...]
    │       │
    │       └── Nếu recommendations < 3 → fallback trending
    │
    └── Template render
```

## 6. UI — home.html

Thêm section "Gợi ý cho bạn" **dưới hero, trước "Món ăn nổi bật"**:

```html
{% if user.is_authenticated and recommendations %}
<section class="section-padding">
    <div class="container-fluid px-4">
        <div class="text-center mb-5">
            <p class="font-accent text-gold mb-1">✦ Dành cho bạn ✦</p>
            <h2 class="fw-bold mb-2">Gợi Ý Cho Bạn</h2>
            <div class="gold-divider-center"></div>
            <p class="text-muted mb-0 mt-2">Dựa trên sở thích và lịch sử đặt món</p>
        </div>
        <div class="row g-4">
            {% for item in recommendations %}
                <!-- Card: image, category badge, discount badge, title, description, price, button -->
            {% endfor %}
        </div>
    </div>
</section>
{% endif %}
```

Style: dùng chung card design với featured items (hover-lift, gold badge, glass effect).

## 7. Xử lý biên

| Tình huống | Xử lý |
|-----------|-------|
| User chưa login | Hiện featured + trending, không có section gợi ý |
| Login nhưng chưa order/review | Fallback → featured + trending |
| Có order nhưng tất cả món đã bị pop (7 ngày) | Fallback → featured + trending |
| Không đủ user khác để collaborative | Chỉ dùng content-based (trọng sộ 1.0) |
| Món gợi ý hết hàng | Scorer lọc `is_available=True` |
| Món không có tags | `tag_match` trả về 0 |
| Rating trùng nhau | Tiebreaker: `views_count` descending |
| Không đủ 6 món | Trả về bao nhiêu có bấy nhiêu |
| Sau pop recent_items còn < 3 | Fallback → featured + trending |

## 8. Testing

File: `restaurant/recommender/tests.py`

```python
class ContentBasedStrategyTest(TestCase):
    - test_user_with_orders_gets_category_match
    - test_user_vegetarian_pref
    - test_no_orders_returns_empty

class CollaborativeStrategyTest(TestCase):
    - test_similar_user_recommendation (≥3 overlap)
    - test_no_similar_users_returns_empty
    - test_below_threshold_ignored

class ScorerTest(TestCase):
    - test_merge_normalizes_scores
    - test_recent_items_excluded
    - test_unavailable_excluded
    - test_all_popped_falls_back

class EngineIntegrationTest(TestCase):
    - test_authenticated_user_with_history_gets_recommendations
    - test_authenticated_user_no_history_gets_fallback
    - test_anonymous_user_gets_fallback
```

Test data: ~5 users, ~20 menu items, ~10 orders, ~5 reviews.

## 9. File changes

| File | Action |
|------|--------|
| `restaurant/models.py` | Thêm `tags` field vào MenuItem |
| `restaurant/recommender/__init__.py` | Tạo |
| `restaurant/recommender/engine.py` | Tạo |
| `restaurant/recommender/strategies.py` | Tạo |
| `restaurant/recommender/scorer.py` | Tạo |
| `restaurant/recommender/tests.py` | Tạo |
| `restaurant/views.py` | Sửa `home()` |
| `restaurant/templates/restaurant/home.html` | Thêm section |
| Migration | `00XX_menuitem_tags.py` |

## 10. Không làm (out of scope)

- Không có admin quản lý gợi ý
- Không có model cache `RecommendationResult`
- Không dùng scikit-surprise hay ML library nặng
- Không API endpoint cho recommendation
- Không mobile-specific UI
- Không WebSocket real-time
