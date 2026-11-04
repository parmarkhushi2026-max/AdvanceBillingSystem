# 🧾 Advance Billing System

[![GitHub Repository](https://img.shields.io/badge/GitHub-Repository-181717?style=for-the-badge&logo=github)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)
[![Django](https://img.shields.io/badge/Django-5.x-092E20?style=for-the-badge&logo=django)](https://www.djangoproject.com/)
[![Tests](https://img.shields.io/badge/Tests-225%20Passing-success?style=for-the-badge)](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

A feature-packed, production-ready Django Billing, QR Payment, and Financial Intelligence System designed for managing distributors, customers, dynamic UPI QR code billing, audit reporting, tax receipts, and ledger tracking.

🔗 **GitHub Repository Link**: [https://github.com/parmarkhushi2026-max/AdvanceBillingSystem](https://github.com/parmarkhushi2026-max/AdvanceBillingSystem)

## 🎨 🌟 Feature: Clean & Professional Bootstrap 5 Styling for Login & Dashboard Pages

A complete, modern redesign and styling pass for the Login and Dashboard pages utilizing **Bootstrap 5.3 CDN** alongside custom fintech CSS, delivering a clean, executive, and responsive user experience across desktop and mobile devices:

- **Bootstrap 5.3 Integration in Base Layout (`templates/base.html`)**:
  - Global integration of **Bootstrap 5.3.3 CSS** and **Bootstrap 5.3.3 JS Bundle** via CDN.
  - Added smooth `.hover-lift` transition utilities for interactive dashboard cards and stat counters.
  - Seamlessly harmonized with custom layout styles (`.sidebar`, `.main-content`, and `.toast-container`).

- **Redesigned Admin Authorization Portal (`templates/auth/login_admin.html`)**:
  - **Split-Card Layout (`card border-0 shadow-lg rounded-4 overflow-hidden`)**:
    - **Executive Dark Indigo Showcase Column (`col-lg-5 text-white`)**: Gradients (`#0f172a` to `#312e81`), clearance badge, 256-bit cryptography highlights, audit studio features, and live database engine status.
    - **Interactive Sign-In Column (`col-lg-7 bg-white`)**:
      - Bootstrap pill navigation (`nav nav-pills nav-fill p-1 bg-light rounded-pill mb-4`) for 1-click switching between Admin Console and Distributor Portal.
      - Modern input groups (`input-group input-group-lg rounded-3 border overflow-hidden`) with FontAwesome icons.
      - Password visibility toggle (`togglePasswordBtn` / `togglePasswordIcon`) and interactive Caps Lock indicator (`capsWarningAlert`).
      - Styled Remember Me checkbox (`form-check`), SSL protection badge, and animated loading state on submission.
      - Quick demo credentials card (`card bg-light border-0 rounded-3 p-3`) with 1-click Auto-fill for `admin / admin123`.

- **Redesigned Distributor POS Terminal Login (`templates/auth/login_distributor.html`)**:
  - **POS & QR Smart Billing Theme**: Emerald/teal gradient showcase (`#022c22` to `#0f766e`) with dynamic UPI QR and thermal printing badges.
  - Matching clean Bootstrap inputs, tab switchers, Caps Lock warning, and quick Auto-fill for demo distributor credentials (`distributor / dist123`).

- **Executive Admin Welcome Dashboard (`templates/dashboard/admin_dashboard.html`)**:
  - **Welcome Hero Card**: Styled with Bootstrap card, live database connectivity pill, and quick-action buttons (`Quick QR Bill`, `Reports Studio`, `Backend Admin`).
  - **KPI Metrics Grid (`row g-3 mb-4`)**: 5 responsive stat cards (`col-12 col-sm-6 col-xl`) with custom `.hover-lift`, color-coded borders (Primary, Info, Warning, Success, Purple), big numbers, and direct navigation links.
  - **Live Database Tables Overview**: Customers & Products cards in `row g-4` with Bootstrap `table table-hover align-middle mb-0` and light headers.
  - **Registered Distributors Master Table**: Bootstrap responsive table with firm names, contact details, assigned UPI ID codes, active status badges (`badge bg-success-subtle text-success border`), and inline edit actions.
  - **Reports & Intelligence Hub**: Bootstrap 3-card grid for 1-click CSV downloads (Sales Ledger, GST Tax Breakdown, Distributor Performance).
  - **Recent Invoices Table**: Clean Bootstrap table with customer details, payment badges, and button groups (`Preview`, `PDF`, `View`).

- **Distributor Operational Dashboard (`templates/dashboard/distributor_dashboard.html`)**:
  - **Terminal Hero Banner**: Bootstrap card featuring distributor firm name, linked UPI ID code, and "+ Create New QR Bill" button.
  - **Collection Metrics Grid**: 4 clean Bootstrap stat cards (My Collections, Invoices Issued, Catalog Products, and My Customers).
  - **Recent Invoices Ledger**: Responsive Bootstrap table with one-click invoice preview, PDF download, and print actions.

- **Automated Test Suite (`billing_app/test_bootstrap_styling_login_dashboard.py`)**:
  - 5 automated unit tests verifying Bootstrap 5 CDN link presence, Admin Login Bootstrap components and form controls, Distributor Login components, Admin Dashboard hero card and metrics grid, and Distributor Dashboard layout. (225 total passing tests across the entire application).

---

## 👑 🌟 Feature: Admin Welcome Dashboard with Live DB Metrics (Customers, Products & Invoices)

A modern, high-aesthetic Welcome Dashboard page designed exclusively for System Administrators, displaying live database counts fetched directly from DB tables (`Customer`, `Product`, `Invoice`, and `Distributor`):
- **Welcome Hero Banner (`templates/dashboard/admin_dashboard.html`)**:
  - Personalized greeting with the logged-in administrator's name: *"Welcome, {{ admin_name }}! 👋"*.
  - Live system connectivity indicator: *"Live DB Connected • System Admin Portal"*.
  - Direct quick-action shortcuts for Quick QR Bill creation, Reports Studio, and Django Backend Admin.
- **Primary Database Metric Cards (Directly Powered by DB Queries)**:
  - **Total Customers (`{{ total_customers }}`)**: Real-time count from the `Customer` table (`Customer.objects.count()`), with quick link to the Customer Directory.
  - **Total Products (`{{ total_products }}`)**: Real-time count from the `Product` table (`Product.objects.count()`), with quick link to Product Inventory.
  - **Total Invoices (`{{ total_invoices }}`)**: Real-time count from the `Invoice` table (`Invoice.objects.count()`), with quick link to All Invoices.
  - **Total Settled Revenue (`₹{{ total_revenue }}`)**: Sum of all PAID invoices across the entire system.
  - **Distributor Network (`{{ total_distributor_records }}`)**: Total registered distributor entities from `Distributor` master table.
- **Live Database Overview Tables**:
  - **Customer Database Glance**: Table displaying recently registered customers with phone, city, GSTIN, and linked invoice counts.
  - **Product Database Glance**: Table displaying catalog products with SKU, category, price, stock quantity, and low-stock alerts.
  - **Registered Distributors Master Table**: Comprehensive table of distributors with firm name, contact, phone, GSTIN, UPI ID, active status, and inline actions.
  - **Recent Invoices Ledger**: Displays recent invoices with customer name, payment method, grand total, status, and one-click actions for Preview, PDF download, and QR bill view.
- **Automated Route Protection (`@admin_required`)**:
  - Restricts dashboard access to authenticated Administrators only. Unauthenticated users are redirected to login, while Distributors are denied access and redirected to their operational portal.

---

## 🔒 🌟 Feature: Multi-Tenant Role Isolation (Distributors See ONLY Their Customers, Products & Invoices)

Robust multi-tenant user role logic ensuring complete data isolation so that Distributors can view, search, and manage ONLY their own customers, products, and invoices, while System Administrators retain full centralized oversight:
- **Foreign Key Relational Architecture Across Models (`billing_app/models.py`)**:
  - **`Customer`**: Linked to distributor user via `created_by` (FK to `User`) and `distributor_ref` (FK to `Distributor`).
  - **`Product`**: Linked to distributor user via `created_by` (FK to `User`) and `distributor_ref` (FK to `Distributor`).
  - **`Invoice`**: Linked to distributor user via `distributor` (FK to `User`), `distributor_ref` (FK to `Distributor`), and `customer` (FK to `Customer`).
  - **`InvoiceItem`**: Linked to parent invoice via `invoice` (FK to `Invoice`) and catalog item via `product` (FK to `Product`).
  - Automatic `save()` synchronization keeps `created_by` and `distributor_ref` in sync across all models.
- **View-Level Tenant Isolation (`billing_app/views.py`)**:
  - **Customer Isolation (`customer_list_view`)**:
    - If user is Distributor: Strictly filters `Customer.objects.filter(Q(created_by=request.user) | Q(distributor_ref__user=request.user))`. Customers of other distributors are completely hidden.
    - If user is Admin: Displays all customers across all distributors.
  - **Product Isolation (`product_list_view` & `product_manage_frontend_view`)**:
    - If user is Distributor: Strictly filters `Product.objects.filter(Q(created_by=request.user) | Q(distributor_ref__user=request.user))`. Products of other distributors are completely hidden.
    - If user is Admin: Displays all catalog products.
  - **Invoice Isolation (`invoice_list_view` & `invoice_bootstrap_table_view`)**:
    - If user is Distributor: Strictly filters `Invoice.objects.filter(Q(distributor=request.user) | Q(distributor_ref__user=request.user))`. Other distributors' invoices are completely hidden.
    - If user is Admin: Displays all invoices across the entire network.
  - **Distributor Dashboard Isolation (`distributor_dashboard_view`)**:
    - Distributor metrics (Total Revenue, Invoices Issued, Catalog Products, and Registered Customers) are calculated strictly from the logged-in distributor's data.
  - **Invoice Creation Dropdown Isolation (`create_invoice_view` & `InvoiceCreationForm`)**:
    - Dynamic Customer dropdown is filtered strictly to the logged-in distributor's customers (`Q(created_by=user) | Q(distributor_ref__user=user)`).
    - Available Products for billing are restricted strictly to that distributor's catalog.
  - **Cross-Tenant Access Prevention (`invoice_detail_view` & `invoice_preview_view`)**:
    - Blocks distributors from viewing, previewing, or downloading invoices issued by another distributor (redirects with Access Denied message).
  - **API Tenant Isolation (`api_products` & `api_all_invoices_details`)**:
    - REST API endpoints enforce role-based filtering, ensuring distributors only receive their own records via JSON responses.
- **Automated Test Suite (`billing_app/test_admin_welcome_dashboard_and_distributor_isolation.py`)**:
  - 10 comprehensive unit tests verifying Admin Welcome Dashboard DB counts, hero greeting, foreign key integrity, Distributor 1 vs Distributor 2 customer isolation, product isolation, invoice isolation, cross-tenant detail/preview blocking, distributor dashboard metric isolation, and invoice creation dropdown filtering. (220 total passing tests across the entire application suite).

---

## 🏢 🌟 Feature: Distributor Table Model & Admin Data Management

Dedicated database table structure (`billing_app_distributor`) and comprehensive administrative workflows enabling System Admins to create, view, search, and manage distributor master records directly via Django Admin and the Admin Web Portal:
- **Dedicated Distributor Database Model (`billing_app/models.py::Distributor`)**:
  - Creates the physical database table `billing_app_distributor` with rich enterprise master data:
    - `name`: Authorized proprietor / contact person name.
    - `business_name`: Distributor trade / firm name.
    - `user`: One-to-one foreign key relationship to `auth.User` (optional login account linking).
    - `phone` & `email`: Primary commercial contact channels.
    - `address`, `city`, `state`, `pincode`: Physical warehouse and operational billing location.
    - `gstin`: 15-character Indian Goods & Services Tax Identification Number.
    - `upi_id`: Dedicated UPI Virtual Payment Address (VPA) for dynamic QR payment routing.
    - `is_active`: Status flag controlling distributor operational state.
    - `created_at` & `updated_at`: Audit timestamps.
  - **Dynamic Financial & Invoice Aggregates**:
    - `total_invoices`: Computes count of invoices issued by this distributor.
    - `total_revenue`: Aggregates settled revenue across all PAID invoices.
  - **Automatic Two-Way Profile Sync**:
    - Saving a `Distributor` record linked to a `User` automatically synchronizes role, business name, contact phone, and payment UPI ID with `UserProfile`.
- **Admin Data Addition & Management in Django Admin (`billing_app/admin.py::DistributorAdmin`)**:
  - Registered under the Django Admin portal (`/django-admin/billing_app/distributor/` and `/django-admin/billing_app/distributor/add/`):
    - **Structured Form Fieldsets**: Segmented into *Distributor Enterprise Profile*, *Contact & Location Details*, and *Tax & QR Payment Setup*.
    - **Interactive List Display**: Shows Firm Name, Contact Person, Phone, Email, City, GSTIN, UPI ID Badge, Linked User Account link, Invoices count, Settled Revenue, and Active status.
    - **Distributor Invoices Inline (`DistributorInvoiceInline`)**: Direct inline table showing all invoices issued by the distributor inside the distributor change page.
    - **Search & Filters**: Comprehensive search across business name, proprietor, phone, email, GSTIN, UPI ID, and city, with status and location filters.
- **Admin Portal Web Interface (`/admin/distributors/` & `/admin/distributors/add/`)**:
  - **Distributor Master Table View (`templates/admin/distributor_list.html`)**:
    - Bootstrap fintech-styled table with search bar, status filter (Active/Inactive), summary statistics cards, pagination, and direct links to add or edit records via Django Admin.
  - **Distributor Creation Form (`templates/admin/distributor_form.html` & `billing_app/forms.py::DistributorForm`)**:
    - Clean web form with full validation for business credentials, contact info, GSTIN, and UPI ID.
  - **Admin Dashboard Integration (`templates/dashboard/admin_dashboard.html`)**:
    - Enhanced "Registered Distributors Master Table" card with one-click links to the full distributor table, add form, and backend admin portal.
  - **Navigation Integration (`templates/base.html`)**:
    - Sidebar link to "Distributors" under Admin Controls for quick access.
- **Automated Test Suite (`billing_app/test_distributor_model_admin.py`)**:
  - 10 comprehensive unit tests covering model table creation, field integrity, string formatting, profile synchronization, computed invoice metrics, adding data via Django Admin, admin changelist search, portal access control (`@admin_required`), portal search/filter, model form validation, and automatic invoice foreign key linking. (210 total passing tests across the entire application suite).

---

## 🛡️ 🌟 Feature: Custom Middleware & Decorators for Admin vs Distributor Role Distinction

Comprehensive role-based architecture distinguishing between Admin and Distributor users across the request lifecycle, view controllers, API endpoints, and templates:
- **Custom Role Middleware (`billing_app/middleware.py::UserRoleMiddleware`)**:
  - Automatically identifies and distinguishes authenticated user roles on every incoming request:
    - `request.user_role`: Evaluates to `'ADMIN'`, `'DISTRIBUTOR'`, or `'ANONYMOUS'`.
    - `request.is_admin`: Boolean flag (`True` for Superusers and users with `ADMIN` role).
    - `request.is_distributor`: Boolean flag (`True` for `DISTRIBUTOR` role).
    - `request.user_profile`: Resolves and attaches the associated `UserProfile` model instance.
  - Positioned directly in the Django middleware pipeline after `AuthenticationMiddleware`.
- **Custom View & Dispatcher Decorators (`billing_app/decorators.py`)**:
  - **`@admin_required`**: Restricts view execution to Admin users only. Unauthenticated requests are redirected to login (or return HTTP 401 for AJAX); Distributor users attempting access are detected and redirected to `/distributor/dashboard/` with an Access Denied alert (or HTTP 403 Forbidden for AJAX).
  - **`@distributor_required`**: Restricts access to Distributor accounts, redirecting unauthenticated requests to the distributor login portal.
  - **`@role_required(allowed_roles=['ADMIN', 'DISTRIBUTOR'])`**: Flexible decorator accepting a role or list of authorized roles.
  - **`@distinguish_role(admin_func=..., distributor_func=...)`**: Smart role dispatcher decorator that detects whether the logged-in user is an Admin or a Distributor and dispatches execution to the corresponding handler automatically.
  - **`@api_admin_required` & `@api_distributor_required`**: Dedicated JSON API decorators returning structured HTTP 401/403 responses.
  - **`get_user_role(user)`**: Utility helper returning `'ADMIN'`, `'DISTRIBUTOR'`, or `'ANONYMOUS'`.
- **Template Context Processor (`billing_app/context_processors.py::user_role_context`)**:
  - Injects `user_role`, `is_admin`, `is_distributor`, and `user_profile` into all template contexts, allowing frontends to cleanly render role-specific navigation bars, actions, and sidebars (`{% if is_admin %}...{% elif is_distributor %}...{% endif %}`).
- **Automated Test Suite (`billing_app/test_role_distinction_middleware_decorators.py`)**:
  - 12 comprehensive unit tests verifying middleware role resolution, Admin vs Distributor access control, role dispatching, API 401/403 responses, template context processors, and helper functions. (63 total passing tests across authentication, RBAC, and route protection suites).

---

## 🔐 🌟 Feature: Django-based Login/Logout with Session Control & Restricted Dashboard Access

Enterprise-grade authentication, session management, and role-based route protection:
- **Django-Based Login & Session Control (`billing_app/views.py` & `settings.py`)**:
  - **Multi-Role Authentication**: Dedicated and unified login views (`admin_login_view`, `distributor_login_view`, `general_login_view`) supporting both username and email authentication backends.
  - **Dynamic Session Lifetime ("Remember Me")**:
    - **Remember Me Active**: Configures persistent session lasting 30 days (`request.session.set_expiry(60 * 60 * 24 * 30)`), persisting across browser restarts (`expire_at_browser_close == False`).
    - **Standard Login**: Sets session to expire immediately upon browser closure (`request.session.set_expiry(0)`), enhancing workstation security.
  - **Session Fixation Prevention**: Rotates session keys upon successful authentication via `request.session.cycle_key()`.
  - **Secure Session Termination (`user_logout`)**:
    - Invokes `auth_logout(request)` and purges the session store via `request.session.flush()`, removing session records from the database and wiping browser cookies.
- **Restricted Dashboard Access & Route Protection (`billing_app/middleware.py` & `billing_app/decorators.py`)**:
  - **Strict Access Restriction**: All dashboards (`/admin/dashboard/`, `/distributor/dashboard/`, and central `/dashboard/`) are protected by `@login_required`, `@admin_required`, `@distributor_required`, and `RouteProtectionMiddleware`.
  - **Unauthenticated Handling**:
    - Web browser requests are automatically redirected to login pages with friendly alert messages and preserved `next` redirect parameters.
    - AJAX/API requests receive standardized HTTP 401 Unauthorized JSON responses (`{'success': False, 'message': 'Authentication required...'}`).
  - **Role Isolation (RBAC)**:
    - Admin users have full oversight across `/admin/dashboard/`.
    - Distributors are restricted to their operational `/distributor/dashboard/` and forbidden from accessing Admin views (HTTP 403 Forbidden on AJAX / redirect with Access Denied message).
    - Central `/dashboard/` dynamically routes authenticated users to their corresponding dashboard based on their role.
- **Live Session Status API (`/api/auth/session/`)**:
  - Enables real-time frontend session heartbeat monitoring, reporting authentication state, user identity, active role, and session TTL.
- **Automated Test Suite (`billing_app/test_session_control_dashboard_protection.py`)**:
  - 16 comprehensive unit tests covering unauthenticated dashboard redirection, AJAX 401 responses, authenticated role routing, distributor access denial to admin dashboards, Remember Me session lifespan, session flush upon logout, post-logout dashboard blocking, and REST session management. (51 total tests in authentication and route guarding suites).

---

## 🔎 🌟 Feature: Customer Name & Invoice ID Search with Query Filters & Results Pagination

Comprehensive search functionality filtering by Customer Name and Invoice ID using Django `Q` query filters, accompanied by customizable pagination limiting results per page:
- **Search Functionality Using Django Query Filters (`billing_app/views.py`)**:
  - **Search by Customer Name**:
    - Evaluates query filters across both the direct `customer_name` string and foreign-key relational `customer__name`:
      ```python
      invoices = invoices.filter(
          Q(customer_name__icontains=customer_name) |
          Q(customer__name__icontains=customer_name)
      )
      ```
    - Case-insensitive substring matching (`__icontains`) allowing partial name searches.
  - **Search by Invoice ID & Invoice Number**:
    - Automatically parses integer primary key IDs (`Q(id=int(clean_id))`) and alphanumeric invoice number references (`Q(invoice_number__icontains=...)`).
    - Strips prefixes such as `#` or `INV-` gracefully.
  - **Combined Multi-Criteria Filtering**:
    - Allows combining `customer_name`, `invoice_id`, date range, and payment status simultaneously using sequential AND filter chaining.
    - Also supports unified search query (`q`) spanning customer name, customer phone, and invoice numbers.
- **Pagination Limiting Results Per Page (`templates/billing/invoice_list.html` & `views.py`)**:
  - Implements Django `Paginator` with customizable limits per page (`?per_page=5|10|20|50|all`).
  - Interactive page size selector dropdown in the filter toolbar (`5 / page`, `10 / page`, `20 / page`, `50 / page`, `View All`).
  - Pagination navigation controls (Previous, Page numbers, Next) cleanly preserve all active search parameters (`customer_name`, `invoice_id`, `q`, `start_date`, `end_date`, `status`, `per_page`).
  - Displays dynamic summary caption: *"Showing X to Y of Z invoices (Limit: N per page)"*.
- **REST API Search & Pagination (`api_all_invoices_details`)**:
  - `GET /api/invoices/details/?customer_name=...&invoice_id=...&page=1&limit=10` returns paginated JSON results with total count, current page, and num_pages.
- **Automated Test Suite (`billing_app/test_invoice_search_pagination.py`)**:
  - 12 comprehensive unit tests verifying customer name query filters, integer invoice ID lookup, invoice number string search, hash prefix handling, combined search, universal query search, pagination limits per page, page navigation isolation, search filter URL preservation, unpaginated view-all, dedicated table endpoint, and REST API search.

---

## 📥 🌟 Feature: Download PDF Button Beside Each Row (With DB Customer & Invoice Data)

A dedicated, styled "Download PDF" button placed beside each invoice row in the table, fetching accurate data directly from the corresponding Invoice ID and Customer DB records:
- **Dedicated Row-Level "Download PDF" Button (`templates/billing/invoice_list.html`)**:
  - Embedded prominently beside each invoice entry in the Actions table column:
    - Styled with high-visibility Bootstrap button design: `<a href="/invoice/<id>/pdf/" class="btn btn-danger btn-sm download-pdf-btn" ...>` with `<i class="fa-solid fa-file-pdf"></i> Download PDF`.
    - Distinct semantic data attributes: `data-invoice-id="{{ invoice.id }}"` and `data-customer-id="{{ invoice.customer_id }}"`.
    - Integrated with instant client-side download streaming and alert notifications via `downloadServerPDF(this, '<id>', '<number>')`.
- **Accurate Database-Driven PDF Generation (`billing_app/views.py` & `billing_app/pdf_generator.py`)**:
  - Backend query fetches full relational data from the database using:
    ```python
    Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').get(id=invoice_id)
    ```
  - Accurately resolves the linked `Customer` model entry:
    - Customer Name, Contact Number, Email, Billing Address, City, and GSTIN are retrieved directly from the DB entry.
    - Graceful fallback for walk-in / legacy invoices without an attached foreign key customer record (`invoice.customer_name`, `invoice.customer_phone`).
- **Comprehensive Dual-Engine PDF Export**:
  - **`xhtml2pdf` Engine**: Certified HTML/CSS template (`templates/billing/invoice_pdf.html`) displaying full customer information box (name, contact, email, address, GSTIN) and dynamically generated QR code.
  - **`ReportLab` Engine**: Programmatic canvas PDF generation with customer profile block and itemized billing ledger.
- **Automated Test Suite (`billing_app/test_download_pdf_row_button.py`)**:
  - 5 comprehensive automated tests:
    - `test_download_pdf_button_rendered_beside_each_row`: Verifies presence, attributes, and styling of the "Download PDF" button for all invoices in the list.
    - `test_pdf_view_fetches_customer_from_db`: Asserts that PDF export pulls exact customer data (Name, Phone, Email, GSTIN, Address) from the `Customer` DB record.
    - `test_download_pdf_streams_valid_pdf_content`: Tests both `xhtml2pdf` and `reportlab` engines stream valid `%PDF` headers and attachment filenames.
    - `test_download_pdf_404_for_nonexistent_invoice`: Handles invalid invoice IDs with proper 404 responses.
    - `test_distributor_download_pdf_access_control`: Enforces distributor tenant isolation and unauthorized access prevention.

---

## 🔍 🌟 Feature: Preview Icon Beside Each Invoice Entry for Dynamic QR Code

Interactive on-the-fly QR code preview directly inside the invoice table view:
- **Interactive Preview Icon (`templates/billing/invoice_list.html`)**:
  - Placed directly beside each invoice entry in the primary table column:
    - Dedicated icon button `<button type="button" class="btn btn-sm btn-outline-primary qr-preview-icon" ...>` featuring `<i class="fa-solid fa-qrcode"></i>`.
    - Clicking the icon immediately launches the dynamic QR preview modal (`#qrPreviewModal`) for that specific invoice.
    - Also available inside the Action button group as `QR Preview`.
- **Dynamic QR Code Preview Modal (`#qrPreviewModal`)**:
  - **Dynamic Generation & Real-Time Loading**: Calls backend API `/api/invoice/<id>/qr-code/?mode=...` and streams live PNG data URIs.
  - **Interactive Mode Switcher**:
    - **`Instant UPI Pay`**: Generates live `upi://pay?pa=...` string scannable by Google Pay, PhonePe, Paytm, and BHIM.
    - **`Certified Summary`**: Generates formatted key-value invoice verification text (Invoice ID, Customer, Date, Total Amount).
    - **`JSON Metadata`**: Generates structured machine-readable JSON for automated accounting verification.
  - **Live Verification Badge**: Displays `[ INSTANT UPI PAYMENT QR ]` or `[ DIGITALLY VERIFIED QR INVOICE ]`.
  - **Live Financial & Customer Breakdown**: Displays Invoice Number, Customer Name, Grand Total amount, and Creation timestamp.
  - **Decoded QR Payload Accordion**: Expandable view to inspect the exact encoded string payload.
  - **Direct Export Actions**: "Save PNG" and "Certified PDF Download" with instant alert notifications.
- **REST API Enhancement (`billing_app/views.py`)**:
  - `GET /api/invoice/<id>/qr-code/?mode=upi|text|json`: Generates and returns dynamic QR metadata, active payload string, and Base64 Data URI on-the-fly without stale cache.
  - `GET /invoice/<id>/qr.png?format=upi|text|json`: Delivers raw PNG image bytes.
- **Automated Test Suite (`billing_app/test_invoice_qr_preview_icon.py`)**:
  - 5 comprehensive unit tests verifying preview icon presence in table rows, modal DOM structure, dynamic payload formats via API, and raw PNG image streaming.

---

## 📊 🌟 Feature: Fetch All Invoices & Display in Bootstrap-Styled Table

Full-stack database querying and frontend presentation displaying all invoice records in a clean, modern, responsive Bootstrap-styled table:
- **Optimized Database Fetching (`billing_app/views.py`)**:
  - Fetches complete invoice records from the database using high-efficiency SQL joins:
    ```python
    invoices = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').all().order_by('-created_at')
    ```
  - Eliminates N+1 queries by eager-loading foreign key customer profiles, distributors, and itemized invoice line items simultaneously.
  - Supports both standard pagination (`?page=1&per_page=10`) and full database retrieval (`?per_page=all`) to view all records in a single unified view.
  - Granular real-time search across Invoice Number, Customer Name, and Customer Phone (`?q=...`), alongside payment status filtering (`?status=PAID|PENDING|FAILED`).
- **Bootstrap 5 Table Presentation (`templates/billing/invoice_list.html`)**:
  - Built with responsive Bootstrap 5 components:
    - **Table Structure**: `<table class="table table-striped table-hover table-bordered align-middle app-table invoice-bootstrap-table mb-0">`
    - **Header Strip**: `<thead class="table-dark">` with uppercase typography, sorting indicators, and fixed column width ratios.
    - **Record Cells**:
      - **Invoice Number & ID**: Bold `#INV-...` reference with unique primary key badge (`#ID`).
      - **Customer Details**: Registered Customer Name with phone icon and direct contact string.
      - **Line Items Badges**: Itemized product pill badges (`<span class="badge bg-light text-dark border">Product &times;Qty</span>`).
      - **Timestamp**: Formatted date (`M d, Y`) with human-readable time (`h:i A`).
      - **Financial Grand Total**: Highlighted bold currency format (`₹X,XXX.XX`).
      - **Status Badges**: Semantic Bootstrap pill badges (`badge bg-success` for PAID, `badge bg-warning text-dark` for PENDING, `badge bg-danger` for FAILED).
      - **Action Group**: Bootstrap button group (`btn-group btn-group-sm`) providing Preview, PDF Download (with success/failure alerts), QR Code, and Detailed view.
    - **Bootstrap Pagination**: `<nav class="pagination pagination-sm justify-content-center">` with `page-item` and `page-link`.
- **Dedicated & Canonical Endpoints**:
  - Canonical URL: `GET /invoices/`
  - Dedicated Bootstrap Table URL: `GET /invoices/table/` (and alias `GET /invoices/bootstrap/`)
- **Automated Test Suite (`billing_app/test_invoice_bootstrap_table.py`)**:
  - 8 comprehensive unit tests verifying database record retrieval, Bootstrap class assertions, core field table rendering, dedicated endpoint routing, view-all query parameter, and real-time filtering.

---

## 📱 🌟 Feature: Dynamically Generated QR Code Embedded into PDF Layout

Enterprise-grade on-the-fly QR code generation and direct embedding into both PDF generation pipelines (`xhtml2pdf` HTML/CSS and `ReportLab` Direct Flowable Canvas):
- **Dynamic On-The-Fly Generation (`billing_app/invoice_qr.py`)**:
  - Live model values are extracted and encoded dynamically without relying on stale disk caches:
    - **Invoice ID & Number**: e.g., `#INV-2026-QR-999`
    - **Customer Name & Contact**: e.g., `Vikramaditya Singhania`
    - **Total Amount**: Live `grand_total` formatting e.g., `Rs. 2310.00`
    - **Invoice Date**: Creation timestamp formatted to Indian standard datetime
    - **Itemized Breakdown**: Dynamic product names and quantities
  - **Selectable Payload Modes (`qr_mode`)**:
    - **`'text'` (Default)**: Human and optical-scanner-readable verification summary.
    - **`'upi'`**: Instant UPI payment intent URI compliant with NPCI specification (`upi://pay?pa={upi_id}&pn={business_name}&am={grand_total}&cu=INR&tn=Invoice_{invoice_number}`). Scannable by Google Pay, PhonePe, Paytm, and BHIM.
    - **`'json'`**: Machine-readable JSON string formatted for automated accounting and verification parsers.
  - **Dual Engine Backends**:
    - Works with `qrcode` or `segno` libraries via auto-detection (`qr_engine='auto'|'qrcode'|'segno'`).
- **Direct PDF Layout Embedding (`billing_app/pdf_generator.py`)**:
  - **`xhtml2pdf` Layout**: Encodes the dynamic QR bundle into high-density base64 data URIs (`data:image/png;base64,...`), rendered in a dedicated verification card alongside dynamic scan instructions and status captions.
  - **`ReportLab` Canvas Layout**: Directly streams PNG byte buffers into ReportLab `Image` Flowable elements embedded seamlessly into summary tables.
- **HTTP Endpoint & CLI Integration**:
  - **HTTP View**: `GET /invoice/<id>/pdf/?qr_mode=upi&engine=reportlab`
  - **CLI Command**: `python manage.py generate_invoice_pdf <invoice_id> --qr-mode upi --engine auto --output invoice.pdf`
- **Comprehensive Test Suite**:
  - 7 automated tests in `billing_app/test_embed_dynamic_qr_pdf.py` verifying dynamic QR payload construction, PDF context bundling, xhtml2pdf QR embedding, ReportLab Flowable QR embedding, unified entrypoint, view query parameters, and CLI commands.

---

## 📄 🌟 Feature: Dual-Engine PDF Generation Integration (xhtml2pdf & ReportLab)

High-performance, enterprise-grade PDF rendering service integrating both `xhtml2pdf` and `ReportLab` into a unified pipeline:
- **Architecture (`billing_app/pdf_generator.py`)**:
  - **`xhtml2pdf` Engine**: Translates responsive HTML/CSS templates (`templates/billing/invoice_pdf.html`) directly into certified A4 PDF documents with custom typography, table styles, and embedded QR codes.
  - **`ReportLab` Engine**: Direct canvas & Flowable pipeline (`SimpleDocTemplate`, `Table`, `Paragraph`, `Image`, `NumberedCanvas`) generating crisp, vector-sharp PDFs with minimal memory footprint and high concurrency throughput.
  - **Unified Entrypoint (`generate_invoice_pdf_bytes`)**:
    ```python
    from billing_app.pdf_generator import generate_invoice_pdf_bytes
    # Supports engine='auto', engine='xhtml2pdf', or engine='reportlab'
    pdf_bytes = generate_invoice_pdf_bytes(invoice, engine='auto')
    ```
  - **Automatic Fallback Protection**: If one engine encounters a library or system limitation, `engine='auto'` automatically falls back to the complementary engine seamlessly without interrupting user downloads.
- **HTTP View Integration (`/invoice/<id>/pdf/`)**:
  - Supports query parameter selection:
    - `GET /invoice/<id>/pdf/?engine=xhtml2pdf`: Force HTML template rendering via `xhtml2pdf`.
    - `GET /invoice/<id>/pdf/?engine=reportlab`: Force direct canvas document rendering via `ReportLab`.
    - `GET /invoice/<id>/pdf/`: Default automatic selection.
- **CLI Management Command**:
  - Command: `python manage.py generate_invoice_pdf <invoice_id> [--engine xhtml2pdf|reportlab|auto] [--output <path.pdf>]`
  - Example: `python manage.py generate_invoice_pdf 1 --engine reportlab --output test_invoice.pdf`
- **Automated Test Suite**:
  - 5 comprehensive tests in `billing_app/test_pdf_integration.py` verifying `xhtml2pdf` binary generation, `ReportLab` binary generation, auto-fallback, HTTP view parameters, and CLI command execution.

---

## 🎨 🌟 Feature: Styled Invoice HTML/CSS Template for Certified PDF Export

Production-grade, pixel-perfect A4 GST Tax Invoice template engineered specifically for PDF export engines (`xhtml2pdf` and `WeasyPrint`):
- **Visual Design & Typography (`templates/billing/invoice_pdf.html`)**:
  - **A4 Portrait Page Spec**: Exact `@page` frame geometry (`size: a4 portrait; margin: 1cm;`) with dynamic bottom page numbering (`Page <pdf:pagenumber> of <pdf:pagecount>`).
  - **Corporate Header**: Deep Indigo accent border with issuing business name, registered business address, contact phone, merchant UPI ID, and official GSTIN badge.
  - **Tax Invoice Block**: Prominent invoice title, reference ID (`#INV-xxxx`), billing timestamp, and color-coded status badge (`PAID` in emerald / `PENDING` in amber).
  - **Dual Party Cards**: Shaded slate containers (`#f8fafc`) separating *Billed To Customer Details* (Name, Phone, Email, Address, GSTIN) from *Invoice & Tax Logistics* (Payment method, place of supply, reverse charge).
  - **High-Contrast Line Items Table**: Dark header strip with item index, itemized product names, HSN codes, quantity count, unit price, GST rate %, and line totals.
  - **Embedded Certified QR Code Box**: High-resolution dynamic QR code image, verification caption (`[ DIGITALLY VERIFIED QR INVOICE ]`), and decoded parameters.
  - **Financial Breakdown & Indian Currency In Words**: Taxable subtotal, CGST, SGST, discount, bold grand total divider, and Indian numbering currency words strip (`Rupees Six Thousand Eight Hundred Forty Four Only`).
  - **Legal Terms & Signature Block**: Standard commercial warranty terms, digital verification seal, and authorized signatory signature box.
  - **Engine Compatibility**: Formatted strictly without unsupported CSS (`border-collapse` or missing Unicode font glyphs) ensuring 100% warning-free, fast generation under `xhtml2pdf`.
- **Automated Test Suite**:
  - 2 automated unit tests in `billing_app/test_invoice_pdf_template.py` verifying document content-type, attachment headers, `%PDF-` binary signature, template structure, and Indian currency words rendering.

---

## 🛠️ 🌟 Feature: Manual Entries via Django Admin & Management Command

Complete administrative interface supporting rapid, verified manual entry of Customers, Invoices, and itemized billing line items directly through Django Admin (`/django-admin/`):
- **Django Admin Customization (`billing_app/admin.py`)**:
  - **`InvoiceAdmin` with `InvoiceItemInline`**:
    - Manage invoice details, select Customer from registered database records (ForeignKey), and add multiple `InvoiceItem` rows simultaneously on the same page.
    - Automatic customer pre-fill: selecting a `Customer` automatically fills `customer_name` and `customer_phone`.
    - Automatic total calculation: line item quantities, unit prices, discounts, and GST rates are automatically summed into `subtotal`, `tax_amount`, and `grand_total` when saving.
    - Automatic QR generation: verified dynamic QR code PNG and structured payload are generated and displayed with preview upon save.
  - **`CustomerAdmin` with `CustomerInvoiceInline`**:
    - Manage customer profiles, GSTIN numbers, and view complete history of invoices issued to the customer directly within the customer view.
  - **`InvoiceItemAdmin`**:
    - Direct audit table for all individual invoice line items across the system.
  - **Admin Site Branding**:
    - Header: *"Advance Billing System - Administration"*
    - Title: *"Advance Billing Admin Portal"*
- **Default Superuser Credentials**:
  - **URL**: `http://127.0.0.1:8000/django-admin/`
  - **Username**: `admin`
  - **Password**: `admin123`
- **CLI Management Command**:
  - `python manage.py seed_admin_manual_entries [--count 3]`: Performs realistic manual entries of Customers, Invoices, and line items, printing full terminal audit logs with verified QR status.
- **Automated Test Suite**:
  - 3 unit tests in `billing_app/test_admin_manual_entries.py` verifying admin dashboard access, manual customer creation via admin form, and manual invoice creation with inlined item rows and automatic QR generation.

---

## 🗄️ 🌟 Core Database Models: Invoice, InvoiceItem & Customer Architecture

Clean, scalable relational data layer designed for high-throughput billing, financial audits, and multi-tenant distributor invoicing:
- **`Customer` Model (`billing_app/models.py`)**:
  - `name`: Retail/wholesale client business or customer name (`CharField`).
  - `email`: Customer email address for digital receipts and tax summaries (`EmailField`).
  - `phone`: Customer contact mobile/phone number (`CharField`).
  - `address` & `city`: Geographic billing address details (`TextField` / `CharField`).
  - `gstin`: 15-character GST Identification Number for B2B tax credits (`CharField`).
  - `created_by`: Foreign key to `User` (Distributor/Admin owner) with reverse relation `user.customers`.
  - `created_at`: Automatic creation timestamp.
- **`Invoice` Model (`billing_app/models.py`)**:
  - `invoice ID`: Database primary key ID (`id`) and formatted unique business reference (`invoice_number` / `invoice_id`).
  - `customer`: ForeignKey relationship linking to `Customer` model with reverse relation `customer.invoices.all()`.
  - `total amount`: Verified bill amount (`grand_total` and `total_amount` property), subtotal, discount, and tax totals.
  - `date`: Invoice billing timestamp (`created_at` and `date` property).
  - `distributor`: ForeignKey linking to the issuing distributor user account (`User`).
  - `payment_status` & `payment_method`: Payment lifecycle state (`PAID`, `PENDING`, `FAILED`) and payment instrument (`UPI QR Code`, `Cash`, `Net Banking`).
  - `qr_code_image` & `qr_code_payload`: Dynamic QR code storage generated automatically on model save.
  - Helper methods: `get_complete_details()`, `get_qr_data()`, `get_qr_text_payload()`, `get_qr_json_payload()`, `generate_qr_code()`.
- **`InvoiceItem` Model (`billing_app/models.py`)**:
  - `invoice`: ForeignKey linking to parent `Invoice` model with cascading delete and reverse query `invoice.items.all()`.
  - `product`: Optional ForeignKey linking to inventory catalog `Product` model.
  - `product_name`: Snapshot of item name preserving historical bill accuracy even if catalog items change.
  - `quantity`: Number of units sold (`PositiveIntegerField`).
  - `unit_price`: Item rate per unit (`DecimalField`).
  - `discount`: Line-item specific discount (`DecimalField`).
  - `tax_rate`: GST tax percentage (`5%`, `12%`, `18%`, `28%`).
  - `total` / `total_amount`: Final line item amount including taxes with auto-calculation fallback on save.
- **Automated Test Suite**:
  - Verified with 4 unit tests in `billing_app/test_models_structure.py` covering model creation, foreign keys, auto calculations, and reverse queries.

---

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
