# Task 9: Final verification + seed sample data

## What to do

### 1. Run full test suite

```bash
cd /Users/ltyancts/Desktop/Project II/project2 && python manage.py test restaurant.recommender -v2
```

All 19 tests must pass.

### 2. Verify model changes

```bash
cd /Users/ltyancts/Desktop/Project II/project2 && python manage.py check
```

No errors.

### 3. Verify the view loads

```bash
cd /Users/ltyancts/Desktop/Project II/project2 && python -c "
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project2.settings')
django.setup()
from django.test import RequestFactory
from restaurant.views import home
rf = RequestFactory()
request = rf.get('/')
# Anonymous user
response = home(request)
print(f'Status: {response.status_code}')
print(f'Context keys: {list(response.context_data.keys()) if hasattr(response, \"context_data\") else \"N/A\"}')
"
```

Expected: Status 200, context has 'recommendations' and 'trending_items'.

### 4. Verify template renders correctly

Check that home.html has all sections:
- Hero section
- Recommendations section (with `{% if recommendations %}`)
- Trending section (with `{% if not recommendations and trending_items %}`)
- Featured items section
- About section
- CTA section

### 5. Manual browser test (if possible)

Start server:
```bash
cd /Users/ltyancts/Desktop/Project II/project2 && python manage.py runserver
```

Visit http://localhost:8000/ and verify:
- Anonymous user sees trending items section
- The page loads without errors (check terminal for 500 errors)

### 6. Final commit

```bash
git add -A
git commit -m "chore: verify recommendation system end-to-end"
```

### 7. Final report
Write report to: `/Users/ltyancts/Desktop/Project II/.superpowers/sdd/task-9-report.md`

Include:
- Test results (pass/fail count)
- Files changed summary
- Any remaining concerns
