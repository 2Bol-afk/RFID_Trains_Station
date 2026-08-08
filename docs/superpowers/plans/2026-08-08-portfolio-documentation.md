# RFID Train Station Portfolio Documentation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Brand the real Django application, create a reproducible synthetic demo, capture four authentic UI screenshots, and publish accurate portfolio-grade project documentation.

**Architecture:** Keep the existing Django application and Bootstrap templates intact. Add a shared static brand asset, make the existing `setup_system` command reliably create screenshot-safe demo data, capture pages through Selenium and the installed Google Chrome, then reference those artifacts from a concise README and focused documents.

**Tech Stack:** Python 3.11+, Django 4.2, Django REST Framework, Bootstrap 5, Selenium 4, Google Chrome, Markdown, Mermaid.

## Global Constraints

- Do not generate or add Graphify outputs.
- Use only synthetic demo users, cards, stations, names, email addresses, and transactions.
- Capture the real application at a 1440×900 desktop viewport; do not substitute mockups.
- Keep the approved navy, teal, amber, and off-white logo unchanged.
- Keep `.venv`, `db.sqlite3`, logs, and browser profiles untracked.
- Do not claim behavior in documentation unless it is present and verified.
- Preserve unrelated user changes.

---

### Task 1: Reproducible synthetic demo setup

**Files:**
- Create: `rfid_station/cards/tests/__init__.py`
- Create: `rfid_station/cards/tests/test_setup_system.py`
- Modify: `rfid_station/cards/management/commands/setup_system.py`

**Interfaces:**
- Consumes: Django's `call_command("setup_system", create_users=True, create_demo_data=True)`.
- Produces: cashier/admin demo users, four fare categories, at least one active station, three valid cards, and representative transactions.

- [ ] **Step 1: Write the failing management-command test**

```python
from django.contrib.auth.models import Group, User
from django.core.management import call_command
from django.test import TestCase

from cards.models import Card, FareCategory, TrainStation, Transaction


class SetupSystemCommandTests(TestCase):
    def test_creates_complete_synthetic_demo(self):
        call_command("setup_system", create_users=True, create_demo_data=True)

        self.assertTrue(Group.objects.filter(name="cashier").exists())
        self.assertTrue(Group.objects.filter(name="admin").exists())
        self.assertTrue(User.objects.filter(username="cashier").exists())
        self.assertTrue(User.objects.filter(username="admin").exists())
        self.assertEqual(
            set(FareCategory.objects.values_list("name", flat=True)),
            {"regular", "student", "senior", "pwd"},
        )
        self.assertTrue(TrainStation.objects.filter(is_active=True).exists())
        self.assertEqual(Card.objects.count(), 3)
        self.assertFalse(Card.objects.filter(passenger_name="").exists())
        self.assertFalse(Card.objects.filter(passenger_email="").exists())
        self.assertGreaterEqual(Transaction.objects.count(), 8)
```

- [ ] **Step 2: Run the test and verify the current setup is incomplete**

Run: `.venv/bin/python manage.py test cards.tests.test_setup_system -v 2`

Expected: FAIL because fare categories/stations are not seeded and demo cards cannot satisfy the current required passenger fields.

- [ ] **Step 3: Implement deterministic demo records**

Update `setup_system.py` to:

```python
from cards.models import Card, FareCategory, TrainStation, Transaction
```

Create fare categories with `update_or_create`, using discounts `0.00`, `20.00`, `25.00`, and `20.00`. Create an active `Central Station` with code `CTR` and fare `20.00`. Pass unique synthetic names, `example.com` email addresses, and a valid category into each `CardService.purchase_card` call. Keep the existing three UID values and representative reload, ride, and status transactions so screenshots remain deterministic.

- [ ] **Step 4: Run the focused and full test suites**

Run: `.venv/bin/python manage.py test cards.tests.test_setup_system -v 2`

Expected: PASS with one test.

Run: `.venv/bin/python manage.py test -v 2`

Expected: all discovered tests PASS.

- [ ] **Step 5: Commit the demo setup**

```bash
git add rfid_station/cards/tests rfid_station/cards/management/commands/setup_system.py
git commit -m "test: make demo setup reproducible"
```

---

### Task 2: Application branding and route clarity

**Files:**
- Create: `rfid_station/cards/tests/test_branding.py`
- Create: `rfid_station/cards/tests/test_routes.py`
- Create: `rfid_station/cards/static/cards/images/rfid-train-station-logo.png`
- Modify: `rfid_station/cards/templates/cards/base.html`
- Modify: `rfid_station/cards/templates/cards/home.html`
- Modify: `rfid_station/templates/registration/login.html`
- Modify: `rfid_station/cards/urls.py`

**Interfaces:**
- Consumes: Django `{% static %}` template tag and existing named routes.
- Produces: `/static/cards/images/rfid-train-station-logo.png`, branded public/login pages, HTML reports at `/api/reports/`, and JSON report data at `/api/reports/data/`.

- [ ] **Step 1: Write failing branding tests**

```python
from django.test import TestCase
from django.urls import reverse


class BrandingTemplateTests(TestCase):
    logo_path = "/static/cards/images/rfid-train-station-logo.png"

    def test_home_uses_logo_in_navigation_and_hero(self):
        response = self.client.get(reverse("home"))
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.content.decode().count(self.logo_path), 2)
        self.assertContains(response, 'rel="icon"')

    def test_login_page_uses_project_logo(self):
        response = self.client.get(reverse("login"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.logo_path)
        self.assertContains(response, 'rel="icon"')
```

- [ ] **Step 2: Write a failing report-route test**

```python
from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.urls import reverse


class ReportRouteTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("route-cashier", password="test-pass")
        group, _ = Group.objects.get_or_create(name="cashier")
        self.user.groups.add(group)
        self.client.force_login(self.user)

    def test_report_page_and_json_api_have_distinct_routes(self):
        page = self.client.get(reverse("reports"))
        api = self.client.get(reverse("reports-api"), {"type": "summary"})

        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "System Reports")
        self.assertEqual(api.status_code, 200)
        self.assertEqual(api["Content-Type"], "application/json")
```

- [ ] **Step 3: Run both tests and verify the missing branding/route failures**

Run: `.venv/bin/python manage.py test cards.tests.test_branding cards.tests.test_routes -v 2`

Expected: FAIL because templates do not reference the logo and `reports-api` does not exist.

- [ ] **Step 4: Add the approved static logo and template references**

Copy `docs/assets/rfid-train-station-logo.png` to `rfid_station/cards/static/cards/images/rfid-train-station-logo.png` without altering the approved source. Load `static` in `base.html` and `login.html`. Add:

```html
<link rel="icon" type="image/png" href="{% static 'cards/images/rfid-train-station-logo.png' %}">
```

Replace the navbar credit-card icon with a 36×36 logo image, add a responsive 132×132 logo above the home-page title, and add a 96×96 logo above the login heading. Preserve existing accessible text and add meaningful `alt="RFID Train Station"` text.

- [ ] **Step 5: Give the JSON report API a unique route**

Replace the second duplicate route with:

```python
path("reports/data/", views.ReportsView.as_view(), name="reports-api"),
```

- [ ] **Step 6: Run focused and full tests**

Run: `.venv/bin/python manage.py test cards.tests.test_branding cards.tests.test_routes -v 2`

Expected: four assertions across the focused tests PASS.

Run: `.venv/bin/python manage.py test -v 2`

Expected: all discovered tests PASS.

- [ ] **Step 7: Commit branding and route changes**

```bash
git add rfid_station/cards/static rfid_station/cards/templates/cards/base.html rfid_station/cards/templates/cards/home.html rfid_station/templates/registration/login.html rfid_station/cards/urls.py rfid_station/cards/tests
git commit -m "feat: add RFID Train Station branding"
```

---

### Task 3: Reproducible browser capture

**Files:**
- Create: `rfid_station/requirements-dev.txt`
- Create: `scripts/capture_screenshots.py`
- Create: `docs/assets/screenshots/home.png`
- Create: `docs/assets/screenshots/passenger.png`
- Create: `docs/assets/screenshots/cashier.png`
- Create: `docs/assets/screenshots/admin-dashboard.png`

**Interfaces:**
- Consumes: local server at `SCREENSHOT_BASE_URL` (default `http://127.0.0.1:8000`), users `cashier` and `admin`, and Selenium's `webdriver.Chrome`.
- Produces: four 1440×900 PNG files under `docs/assets/screenshots/`.

- [ ] **Step 1: Add development-only capture dependency**

```text
-r requirements.txt
selenium>=4.25,<5.0
```

- [ ] **Step 2: Create the screenshot script**

Implement `scripts/capture_screenshots.py` with these exact behaviors:

```python
BASE_URL = os.environ.get("SCREENSHOT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
OUTPUT_DIR = ROOT / "docs" / "assets" / "screenshots"

options = webdriver.ChromeOptions()
options.add_argument("--headless=new")
options.add_argument("--window-size=1440,900")
options.add_argument("--hide-scrollbars")
options.add_argument("--force-device-scale-factor=1")
```

Add helpers `visit_and_capture(driver, path, filename)` and `login(driver, username, password, next_path)`. Wait for `document.readyState == "complete"` and a visible page-specific heading before saving. Capture `/`, `/passenger/`, `/cashier/` after logging in as `cashier`, and `/admin-dashboard/` after clearing cookies and logging in as `admin`. Read demo passwords from `SCREENSHOT_CASHIER_PASSWORD` and `SCREENSHOT_ADMIN_PASSWORD`, defaulting to the checked-in demo command's synthetic local passwords.

- [ ] **Step 3: Install dependencies and initialize local demo data**

Run:

```bash
.venv/bin/pip install -r rfid_station/requirements-dev.txt
cd rfid_station
../.venv/bin/python manage.py migrate
../.venv/bin/python manage.py setup_system --create-users --create-demo-data
```

Expected: migrations succeed and three demo cards are created.

- [ ] **Step 4: Start the loopback server and capture screenshots**

Run the Django server on `127.0.0.1:8000`, wait until `/` returns HTTP 200, run `.venv/bin/python scripts/capture_screenshots.py`, and stop the server after the script exits.

Expected: the script reports all four output paths and exits with code 0.

- [ ] **Step 5: Validate screenshot files**

Use Pillow to assert every file is PNG, exactly 1440×900, and has non-empty color variance. Visually inspect each image for the correct page, approved logo, complete viewport, synthetic-only information, and absence of browser chrome or error messages.

- [ ] **Step 6: Commit capture tooling and screenshots**

```bash
git add rfid_station/requirements-dev.txt scripts/capture_screenshots.py docs/assets/screenshots
git commit -m "docs: capture application interface"
```

---

### Task 4: Portfolio README and supporting documentation

**Files:**
- Modify: `README.md`
- Create: `docs/ARCHITECTURE.md`
- Create: `docs/API.md`
- Create: `docs/HARDWARE.md`
- Create: `LICENSE`

**Interfaces:**
- Consumes: verified routes, actual models/services, approved logo, and four screenshot paths.
- Produces: GitHub-renderable Markdown with valid local links and Mermaid diagrams.

- [ ] **Step 1: Rewrite the README as a portfolio landing page**

Use a centered HTML logo at `docs/assets/rfid-train-station-logo.png`, preserve accurate badges, add a two-column table linking the four screenshots, and document the problem, solution, core capabilities, architecture summary, stack, quick start, demo setup, role matrix, API summary, bridge command, test command, project team, production limitations, and documentation links.

Correct all paths so root-level commands use `rfid_station/requirements.txt` or explicitly `cd rfid_station`. Document `/api/reports/data/` as the JSON report route and `/api/reports/` as the HTML report interface. Do not claim PostgreSQL is configured; state that SQLite is the checked-in development configuration and PostgreSQL is a production recommendation.

- [ ] **Step 2: Add architecture documentation**

Create `docs/ARCHITECTURE.md` with:

- a Mermaid flowchart connecting RFID reader → Python bridge → DRF view → `CardService` → ORM/database;
- an entity relationship diagram for User, Card, Passenger, FareCategory, TrainStation, and Transaction;
- a sequence diagram for a ride charge;
- concise component-responsibility and concurrency sections;
- current security boundaries and clearly labeled limitations.

- [ ] **Step 3: Add API documentation**

Create `docs/API.md` from `cards/urls.py`, serializers, and permissions. For each route include method, access requirement, request body or query fields, successful response shape, and relevant errors. Clearly distinguish public passenger endpoints, session-authenticated cashier/admin endpoints, and bridge-token ride charging.

- [ ] **Step 4: Add hardware documentation**

Create `docs/HARDWARE.md` describing supported serial UID input, command-line options, environment alignment, expected line format, request flow, logs, troubleshooting, and the current lack of bundled physical-reader firmware.

- [ ] **Step 5: Add the declared MIT license file**

Add the standard MIT license text with:

```text
Copyright (c) 2025 RFID Train Station contributors
```

- [ ] **Step 6: Validate documentation**

Run a link/image-path check over every relative Markdown link and HTML image `src`. Run `git diff --check`. Manually compare every endpoint table against `rfid_station/cards/urls.py` and every setup command against the actual repository layout.

- [ ] **Step 7: Commit documentation**

```bash
git add README.md docs/ARCHITECTURE.md docs/API.md docs/HARDWARE.md docs/assets/rfid-train-station-logo.png LICENSE
git commit -m "docs: publish portfolio documentation"
```

---

### Task 5: Final verification and GitHub publication

**Files:**
- Verify only; no planned new files.

**Interfaces:**
- Consumes: completed commits and configured `origin` remote.
- Produces: verified `master` branch pushed to GitHub.

- [ ] **Step 1: Run Django verification**

Run:

```bash
cd rfid_station
../.venv/bin/python manage.py check
../.venv/bin/python manage.py makemigrations --check --dry-run
../.venv/bin/python manage.py test -v 2
```

Expected: system check has no issues, no model changes are pending, and all tests pass.

- [ ] **Step 2: Run repository verification**

Run `git diff --check`, verify all required assets exist, inspect `git status --short`, and inspect the commits since `55d2433`.

Expected: no unstaged tracked changes, only intentional commits, logo and four screenshots present.

- [ ] **Step 3: Confirm GitHub target**

Run `git remote -v` and `git status -sb`. Verify that `origin` is the existing project repository and `master` is ahead only by the reviewed documentation/branding commits.

- [ ] **Step 4: Push**

Run: `git push origin master`

Expected: push succeeds and the remote branch advances to the final local commit.

- [ ] **Step 5: Report publication**

Provide the GitHub repository URL, final commit hash, verification results, screenshot paths, documentation paths, and any explicitly documented limitations.
