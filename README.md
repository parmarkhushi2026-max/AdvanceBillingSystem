# 🧾 Advance Billing System

A feature-packed Django-based Billing and Invoice Management System designed for managing distributors, customers, invoices, and payment tracking.

---

## 🚀 Key Features & Project Configurations

- **Framework**: Django (Python 3.x)
- **Database**: SQLite3 (`db.sqlite3` pre-configured for seamless development)
- **Installed Apps**:
  - `billing_app` (Main billing & invoice logic, auth portals, dashboards)
  - `billing` (Supporting billing models)
- **Static & Media File Management**:
  - Centralized `static/` directory for global CSS, JavaScript, and asset files.
  - Pre-configured `STATIC_ROOT` and `MEDIA_ROOT` for production build readiness.

---

## 📁 Directory Structure

```text
AdvanceBillingSystem/
├── billing/                # Django app for billing models
├── billing_app/            # Main application (Views, Forms, Models, URLs)
├── billing_system/         # Core Django project configuration (settings.py, urls.py, wsgi.py)
├── static/                 # CSS, JS, and image assets
├── templates/              # HTML templates (Auth, Billing, Dashboard)
├── .gitignore              # Git ignore rules for Django & Python
├── db.sqlite3              # Local SQLite database
├── manage.py               # Django management script
├── README.md               # Project documentation
└── requirements.txt        # Project dependencies
```

---

## ⚙️ Project Settings Overview (`billing_system/settings.py`)

### 1. Database Setup (SQLite3)
```python
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}
```

### 2. Registered Apps (`INSTALLED_APPS`)
```python
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'billing',
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

## 📦 Setup & Installation

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
