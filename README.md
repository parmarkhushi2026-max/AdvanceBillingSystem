# 🧾 Advance Billing System

A feature-packed, production-ready Django Billing and Invoice Management System designed for managing distributors, customers, dynamic QR code billing, tax receipts, and payment tracking.

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
