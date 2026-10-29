# 🧾 Advance Billing System

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/Tests-155%20Passing-success?style=for-the-badge)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

A feature-packed, production-ready Django Billing, QR Payment, and Financial Intelligence System designed for managing distributors, customers, dynamic UPI QR code billing, audit reporting, tax receipts, and ledger tracking.

🔗 **GitHub Repository Link**: [https://github.com/parmarkhushi2026-max/AdvanceBillingSystem](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

## 📥 🌟 Feature: Download Buttons & Success/Failure Alerts Notification Engine

Full-stack document export and download infrastructure with real-time UI feedback, progress states, and success/failure alerts:
- **Download Action Buttons**:
  - **Server-Side Official PDF**: Certified Tax Invoice export with verified embedded QR code via `xhtml2pdf` (`GET /invoice/<id>/pdf/`).
  - **Client-Side High-Res PDF**: Instant browser-side PDF rendering via `html2pdf.js` with A4 GST / Thermal receipt mode presets.
  - **Complete Invoice Details JSON**: Export complete fetched invoice metadata (ID, customer name, total amount, date, line items, and QR payload) via `GET /api/invoice/<id>/details/?download=1`.
  - **All Invoices Batch Export**: Export all database invoices as JSON via `GET /api/invoices/details/?download=1`.
  - **QR Code PNG Image**: Direct binary download of high-resolution QR image (`GET /invoice/<id>/qr/image/`).
- **Interactive Success & Failure Alert Notifications**:
  - **Real-Time Button Loading State**: Buttons dynamically toggle to `<i class="fa-solid fa-spinner fa-spin"></i> Downloading...` and disable during fetching to prevent accidental duplicate clicks.
  - **Success Alerts**: Triggers prominent emerald alert toast banners (`"Invoice #INV-xxx PDF downloaded successfully!"`) with auto-dismiss and close controls.
  - **Failure / Error Alerts**: Automatically catches HTTP 4xx, 5xx, or network issues and displays clear red diagnostic alerts (`"Failed to download PDF: Invoice not found or server error"`), restoring button states safely.
  - **Inline Alert Containers**: `<div id="download-alert-container">` updates dynamically within pages for seamless visual feedback.
  - **Graceful Fallbacks**: Intelligent fallback to native browser print preview (`window.print()`) if client generation libraries are unavailable.
- **Universal JavaScript Engine (`static/js/main.js`)**:
  - `window.showAppAlert(type, message, duration)`: Toast banner alert notification dispatcher.
  - `window.downloadFileWithAlerts(buttonEl, url, filename, successMsg, failureMsg)`: Blob fetch with progress and alert dispatching.
  - `window.downloadServerPDF(buttonEl, invoiceId, invoiceNumber)`: Dedicated invoice PDF downloader.
  - `window.downloadInvoiceJSON(buttonEl, invoiceId, invoiceNumber)`: Dedicated invoice JSON downloader.
  - `window.downloadAllInvoicesJSON(buttonEl, evt)`: Batch invoices downloader.
- **Verified Across All Views**:
  - **Preview Invoice Page** (`/invoice/<id>/preview/`)
  - **Invoice Detail View** (`/invoice/<id>/`)
  - **Invoice List View** (`/invoices/`)
  - **Invoice QR Code Showcase** (`/invoice/<id>/qr/`)
  - **QR Decoder Studio** (`/qr-decoder/`)
  - **Audit Reports Section** (`/reports/invoices/`)
- **Unit & Integration Tests**:
  - 9 automated unit tests in `billing_app/test_download_alerts.py` verifying file streaming, attachment headers, error responses (404/500), template button presence, and alert hooks.

---

## 📱 🌟 New Feature: Saved Invoice Model QR Code Generation Engine

Fetch invoice data directly from the saved database model and dynamically generate high-resolution QR codes encoding these values:
- **Core Fetched Model Attributes**:
  - **Invoice ID**: Database primary key ID (`#1`) and formatted invoice reference (`INV-2026-001`).
  - **Customer Name**: Exact customer recipient name (`customer_name`) and verified contact phone.
  - **Total Amount**: Certified `grand_total` invoice bill amount (e.g. `₹23,234.00`).
  - **Date**: Exact invoice creation timestamp (`created_at`) formatted in readable date/time.
  - **Itemized Breakdown**: Complete line items with product names, quantities, unit prices, and GST rates.
- **Flexible Payload Formats**:
  - **Scanner-Readable Text Format**: Formatted key-value string optimized for smartphone cameras, QR scanner hardware, and UPI decoder studio.
  - **Structured JSON Format**: Machine-readable JSON payload with complete metadata.
- **Model Methods (`Invoice`)**:
  - `invoice.get_qr_data()`: Extracts dictionary with ID, customer name, total amount, and date.
  - `invoice.get_qr_text_payload()`: Builds formatted key-value text payload.
  - `invoice.get_qr_json_payload()`: Builds formatted JSON string payload.
  - `invoice.generate_qr_code(as_base64=True, payload_format='text')`: Generates PNG image or Base64 Data URI.
  - `invoice.qr_code_base64`: Property returning `data:image/png;base64,...` for HTML templates.
- **Interactive UI & Direct Image Endpoints**:
  - **QR Code Showcase Page**: Dedicated inspection view (`GET /invoice/<id>/qr/`) with large QR preview, fetched value summary cards, raw payload viewer, copy to clipboard, print card, and download buttons.
  - **Direct PNG Image Endpoint**: `GET /invoice/<id>/qr.png` returns binary image (`image/png`) for direct embedding in `<img>` tags or receipts.
  - **REST API Endpoint**: `GET /api/invoice/<id>/qr-code/` returns JSON with fetched invoice attributes, payload, and QR data URI.
- **Management Command**:
  - `python manage.py generate_invoice_qr [invoice_id]`: Fetch invoice and generate QR in terminal.
  - Supports `--format json|text`, `--save <path.png>`, and `--all` batch generation.
- **Comprehensive Test Suite**:
  - 12 comprehensive unit tests in `billing_app/test_invoice_qr_generation.py` testing database fetching, QR generation, decoding/verification, views, endpoints, and management commands (100% passing).

---

## 🛡️ 🌟 Feature: Route Protection Middleware & Role-Based Decorators

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

## 🔐 🌟 Feature: Complete Login & Logout Flow & Session Security

Tested and validated authentication flow covering Web and REST API sessions:
- **Admin Authentication**:
  - Secure login via username or email address (`EmailOrUsernameBackend`).
  - Redirection to `/admin/dashboard/` (or custom `?next=` destination).
  - Configurable persistent session via *Remember Me* (30 days vs session close expiry).
- **Distributor Authentication**:
  - Dedicated distributor portal login (`/login/distributor/`) redirecting to distributor dashboard.
  - Profile auto-initialization and role binding (`DISTRIBUTOR`).
- **Complete Logout & Session Flushing**:
  - Web logout (`/logout/`) invalidates the session, flushes cookies from browser, and destroys the database session.
  - Post-logout route protection prevents back-button bypass and immediately redirects unauthenticated attempts to login.
- **REST API Login & Logout Suite**:
  - JSON authentication via `/api/login/admin/`, `/api/login/distributor/`, and `/api/login/`.
  - Live session status query via `/api/auth/session/` (returns user metadata, role, and session expiry age).
  - Programmatic session termination via `/api/auth/logout/`.
- **Test Suite**: Fully verified across 17 dedicated tests in `billing_app/test_login_logout_flow.py` (100% passing).

---

## 🧾 🌟 Feature: Database Invoice Data Engine & Seeder

Guarantees that complete, realistic invoice data exists in the database:
- **Core Attributes Ensured**:
  - **Invoice ID**: Unique sequential ID (`#1`, `#2`, ...) and formatted number (`INV-2026-001`).
  - **Customer Name**: Linked customer details (`Pooja Electronics & Retail`, `Rajesh General Stores`, `Anil Medical & Diagnostics`).
  - **Total Amount**: Verified `grand_total` with taxes, subtotal, and discounts.
  - **Date**: Timestamped `created_at` records across date ranges for financial reporting.
  - **Line Items**: Linked items with product name, quantity, unit price, and GST rate.
- **Auto-Initialization**: Automatically creates representative data if none exists when views load.
- **Management Command**: Run anytime via `python manage.py seed_invoices` (supports `--force`).
- **Test Coverage**: Tested in `billing_app/test_invoice_database_data.py`.

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
