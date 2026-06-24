# Design Spec: Homepage Text Contrast & Hero Crop

**Date:** 2026-06-25
**Status:** Draft
**Scope:** `project2/templates/base.html` (CSS variables + card-title rule), `project2/restaurant/templates/restaurant/home.html` (hero background crop)

## 1. Goal

Make text readable across the homepage and crop the hero background image so the focal point shifts upward to the restaurant space (rather than the lower 30% which is typically floor/empty ambiance).

User reported:
- Card titles ("tên món �n") blend into the dark background.
- Muted/secondary text ("phần màu chữ hoà với màu nền") is hard to read.
- Hero image feels too large/centered on the bottom 30%; wants that portion cropped to highlight the restaurant atmosphere.

## 2. Approach

Approach 1 (chosen): Update CSS variables globally + targeted hero crop. Smallest blast radius, fastest, meets the requirement.

Rejected alternatives:
- Scoped fix inside `home.html` only — duplicates logic, doesn't fix same contrast issue on other design-system surfaces (cards, forms, sidebars).
- Full palette/typography refresh — scope creep, not needed.

## 3. Changes

### 3.1 Text contrast (CSS variables)
File: `project2/templates/base.html` `:root` block

| Variable | Old | New | Reason |
|---|---|---|---|
| `--text-secondary` | `#b0b0b0` | `#d4d4d8` | Brighter, improved contrast against dark card/glass surfaces while still clearly subordinate to `--text-primary`. |
| `--text-muted` | `#666666` | `#9ca3af` | `#666` over `--bg-glass (#141414)` was ~4.1:1 (below WCAG AA 4.5:1). New value yields ~6.8:1 (passes AA). |

`--text-primary` (`#f5f5f5`) remains unchanged — already passes against all dark surfaces.

### 3.2 Card title color
Add a new rule after the `.card-body` block in `project2/templates/base.html` so card titles inherit the design-system primary color instead of Bootstrap's default `rgba(0,0,0,0.54)` (which is effectively transparent on dark glass card backgrounds):

```css
.card-title {
    color: var(--text-primary);
}
```

No font-size or font-weight changes needed — `home.html` already sets `font-family: var(--font-heading); font-size: 1rem;` inline.

### 3.3 Hero background crop
File: `project2/restaurant/templates/restaurant/home.html`, `.hero-section` CSS block.

Current:
```css
background: url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920') center/cover no-repeat;
```

Change to:
```css
background: url('https://images.unsplash.com/photo-1517248135467-4c7edcad34c4?w=1920') center 70%/cover no-repeat;
```

Why `center 70%`: `background-position: <horizontal> <vertical>`. A vertical value of `70%` means "align the 70% point of the image with the 70% point of the container," which pushes the image downward relative to the frame — effectively hiding the bottom 30% of the image (floor/ceiling-margin) and showcasing the upper 70% (tables, lighting, ambiance).

## 4. Out of Scope

- Cropping food card images in `menu_list.html`, `category_detail.html`, `chefs_list.html`, `menu_detail.html` — user did not request this; revisit separately if food-card crops become relevant.
- Changes to font families, font sizes, or spacing.
- Changes to any color outside `--text-secondary`, `--text-muted`.

## 5. Verification Checklist

- [ ] Homepage hero image shows the upper 70% (restaurant interior, decor, tables) and the bottom 30% is cropped.
- [ ] Card titles in featured items (`Món Ăn Nổi Bật`) section are clearly readable on the dark glass card.
- [ ] Muted subtitles ("Những món ăn được yêu thích nhất", "�ặt bàn trước để…") are legible at a normal reading distance on a 1080p display.
- [ ] Secondary text in the "Về chúng tôi" feature block is legible.
- [ ] No regression in menu/menu-detail/category pages that inherit the same CSS variables (they should all become slightly brighter, not broken).
- [ ] Contrast ratio ≥ 4.5:1 for all body/secondary text against card/glass backgrounds (use a contrast checker on `--text-muted #9ca3af` over `--bg-glass #141414` and `--bg-tertiary #1e1e1e`).
- [ ] `--text-primary` still passes against `--bg-primary #0a0a0a` (it does: `#f5f5f5` over `#0a0a0a` ≈ 15.7:1).

## 6. Files Touched

1. `project2/templates/base.html` — `--text-secondary`, `--text-muted`, new `.card-title` rule.
2. `project2/restaurant/templates/restaurant/home.html` — `.hero-section` background-position.

## 7. Risks

- **`object-position` for cards is NOT changed** — the original request confused "ảnh trên phần món �n" with the hero image. If the user later wants food-card crops as well, use `object-position: center 30%` on the relevant `.card-img-top` elements in a follow-up change.
- **`--text-secondary` was used by many components globally** (labels, nav links, button icons). The new `#d4d4d8` is still visually distinct from `--text-primary`; no component should break, but visually it will be slightly brighter everywhere on dark backgrounds. Run a global grep for `var(--text-secondary)` if regression is suspected.

## 8. Post-Deploy Checklist

- Pull the branch, run `python manage.py runserver`, open http://localhost:8000/ Chrome DevTools → Lighthouse → Accessibility → Contrast. Should clear all "text contrast" warnings.
- Visually verify hero crop on mobile (375px wide) and desktop (1440px wide) — crop should still frame the restaurant decor reasonably at both widths.
