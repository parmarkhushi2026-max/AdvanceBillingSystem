# 🧾 Advance Billing System

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/Tests-58%20Passing-success?style=for-the-badge)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

A feature-packed, production-ready Django Billing, QR Payment, and Financial Intelligence System designed for managing distributors, customers, dynamic UPI QR code billing, audit reporting, tax receipts, and ledger tracking.

🔗 **GitHub Repository Link**: [https://github.com/parmarkhushi2026-max/AdvanceBillingSystem](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

## 🛡️ 🌟 New Feature: Route Protection Middleware & Role-Based Decorators

Defense-in-depth security enforcing route and role protection across the entire system:
- **`RouteProtectionMiddleware`**: Intercepts requests globally before view execution:
  - Guards `/admin/*` routes strictly for authenticated users with `ADMIN` role / superuser.
  - Guards `/distributor/*` routes strictly for authenticated users.
  - Guards core management routes (`/invoices/*`, `/customers/*`, `/products/*`).
  - Distinguishes browser page visits (redirect with friendly flash messages) from API/AJAX requests (returns HTTP 401 Unauthorized / HTTP 403 Forbidden JSON).
  - Clean whitelist for public authentication, password recovery, and onboarding endpoints.
- **Enhanced Role Decorators (`billing_app/decorators.py`)**:
  - `@admin_required`: Ensures ADMIN privileges, redirecting or returning JSON 401/403.
  - `@distributor_required`: Enforces Distributor access with session verification.
  - `@role_required(['ADMIN', 'DISTRIBUTOR'])`: Flexible multi-role authorization.
  - `@api_login_required` & `@api_admin_required`: API-specific decorators returning JSON status payloads.
- **Comprehensive Test Coverage**: Tested with dedicated unit tests in `billing_app/test_route_protection.py`.

---

## 📊 🌟 Feature: Invoice Report Generator & Date Range Filtering Engine

Generate custom financial ledgers, audit invoices by date range, and export certified records:
- **Date Range Filter Form**: Filter invoices seamlessly by custom `start_date` (From Date) and `end_date` (To Date).
- **1-Click Quick Presets**: Instant filter buttons for *Today*, *Yesterday*, *Last 7 Days*, *Last 30 Days*, *This Month*, *Last Month*, *This Year*, and *All Time*.
- **Comprehensive Multi-Criteria Filters**: Filter by Payment Status (*PAID*, *PENDING*, *FAILED*), Payment Method (*UPI QR Code*, *Cash*, *Card*, *Net Banking*), Customer Name/Phone/Invoice # search, and Min/Max amount range.
- **Real-Time Financial Aggregates**:
  - Total Invoices Count
  - Total Net Billed Revenue (₹)
  - Realized Collections / Paid (₹)
  - Outstanding Dues / Pending (₹)
  - Total GST Tax Collected (₹)
  - Average Invoice Ticket Size (₹)
- **Download PDF Report (xhtml2pdf)**: Download certified landscape audit PDF reports with selected range summary KPIs, tax breakdowns, and complete invoice ledger tables generated via the `xhtml2pdf` engine (`GET /reports/invoices/pdf/`).
- **Export Filtered CSV**: Download audit-ready CSV spreadsheets filtered exactly by the selected date range and criteria.
- **Printable Audit Ledger**: Formatted print view (`@media print`) for clean paper or browser PDF ledger export.
- **Direct Route**: `http://127.0.0.1:8000/reports/invoices/`

---

## 🚀 Key Features & Architectural Stack

- **Framework**: Django (Python 3.x)
- **Database**: SQLite3 (`db.sqlite3` pre-configured for seamless development)
- **Installed Core App**: `billing_app` (Main billing & invoice logic, auth portals, customer directory, dashboards)
- **Security & CSRF**: Configured `CSRF_TRUSTED_ORIGINS`, session cookie policies, and custom CSRF failure fallback handler.
- **Static & Media File Management**:
  - Centralized `static/` directory for CSS design system (`style.css`), JS (`main.js`), and assets.
  - Pre-configured `STATIC_ROOT` and `MEDIA_ROOT` for production deployment.

---

## 📁 Clean Directory Architecture

```text
AdvanceBillingSystem/
├── billing_app/            # Main application directory
│   ├── migrations/         # Database migration scripts (UserProfile, OTPToken, Customer)
│   ├── admin.py            # Django Admin registration for all models
│   ├── decorators.py       # Role-based access control (@admin_required, @distributor_required)
│   ├── forms.py            # Form validation (Auth, Profile, Register, Customer, OTP)
│   ├── models.py           # Database models (UserProfile, Product, Invoice, InvoiceItem, Customer, OTPToken)
│   ├── urls.py             # App URL routing
│   └── views.py            # Business logic, auth flows, billing, PDF export, CSRF handlers
├── billing_system/         # Core Django project configuration
│   ├── settings.py         # App configuration, security settings, database setup
│   ├── urls.py             # Root URL resolver (includes static & media handlers)
│   ├── wsgi.py             # WSGI web server interface
│   └── asgi.py             # ASGI asynchronous server interface
├── static/                 # Centralized CSS, JS, and image assets
│   ├── css/style.css       # Design system (variables, glassmorphism, responsive grids, modals)
│   └── js/main.js          # Core frontend scripts
├── templates/              # Structured HTML templates
│   ├── auth/               # Admin login, distributor login, distributor register, forgot password
│   ├── billing/            # Create QR bill, invoice detail receipt, add customer, customer list
│   ├── dashboard/          # Admin dashboard, distributor dashboard, distributor profile
│   ├── base.html           # Master navigation & footer layout
│   └── home.html           # Portal landing page
├── .gitignore              # Git ignore rules for Django & Python
├── db.sqlite3              # Local SQLite database
├── manage.py               # Django management CLI script
├── README.md               # Project architecture documentation
└── requirements.txt        # Python package dependencies
```

---

## ⚙️ Core Project Settings Overview (`billing_system/settings.py`)

### 1. Database Setup (SQLite3)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 2. Registered App (`INSTALLED_APPS`)
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'billing_app',
]
```

### 3. Static & Media Files Configuration
```python
STATIC_URL = '/static/'
STATICFILES_DIRS = [ BASE_DIR / 'static' ]
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
```

---

## 📦 Setup & Execution

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/parmarkhushi2026-max/AdvanceBillingSystem.git
   cd AdvanceBillingSystem
   ```

2. **Create & Activate Virtual Environment:**
   - **Windows:**
     ```bash
     python -m venv venv
     .\venv\Scripts\activate
     ```
   - **Linux / macOS:**
     ```bash
     python -m venv venv
     source venv/bin/activate
     ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Apply Database Migrations:**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   ```

5. **Run Development Server:**
   ```bash
   python manage.py runserver 8001
   ```
   Open `http://127.0.0.1:8001/` in your browser.
