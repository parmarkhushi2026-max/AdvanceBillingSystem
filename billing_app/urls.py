from django.urls import path
from . import views

urlpatterns = [
    # Portal Landing & Authentication
    path('', views.portal_select, name='portal_select'),
    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('register/admin/', views.admin_register_view, name='admin_register'),
    path('login/distributor/', views.distributor_login_view, name='distributor_login'),
    path('register/distributor/', views.distributor_register_view, name='distributor_register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('admin/forgot-password/', views.admin_forgot_password_view, name='admin_forgot_password'),
    path('admin/forgot-password/resend-otp/', views.admin_resend_otp_view, name='admin_resend_otp'),
    path('logout/', views.user_logout, name='logout'),
    
    # API endpoints
    path('api/register/admin/', views.api_register_admin, name='api_register_admin'),
    path('api/register/distributor/', views.api_register_distributor, name='api_register_distributor'),
    path('api/customer/register/', views.api_register_customer, name='api_register_customer'),
    path('api/register/customer/', views.api_register_customer, name='api_register_customer_alt'),
    path('api/distributor/customers/register/', views.api_register_customer, name='api_distributor_register_customer'),
    
    # Product CRUD API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/products/create/', views.api_products, name='api_product_create'),
    path('api/products/<int:product_id>/', views.api_product_detail, name='api_product_detail'),
    path('api/products/<int:product_id>/update/', views.api_product_detail, name='api_product_update'),
    path('api/products/<int:product_id>/delete/', views.api_product_delete, name='api_product_delete'),


    # Admin Portal
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
    path('admin/reports/', views.admin_reports_view, name='admin_reports'),
    path('admin/reports/export/csv/', views.admin_reports_export_csv_view, name='admin_reports_export_csv'),

    # Distributor Portal & QR Billing
    path('distributor/dashboard/', views.distributor_dashboard_view, name='distributor_dashboard'),
    path('distributor/profile/', views.distributor_profile_view, name='distributor_profile'),
    path('distributor/billing/', views.create_invoice_view, name='create_invoice'),
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
    path('invoice/<int:invoice_id>/pdf/', views.generate_invoice_pdf_view, name='invoice_pdf'),

    # Customer Management
    path('invoices/', views.invoice_list_view, name='invoice_list'),
    path('customers/', views.customer_list_view, name='customer_list'),
    path('customers/add/', views.add_customer_view, name='add_customer'),
    path('customers/register/', views.customer_register_frontend_view, name='customer_register_frontend'),
    path('register/customer/', views.customer_register_frontend_view, name='customer_register_page'),
    path('distributor/customer/register/', views.customer_register_frontend_view, name='distributor_customer_register'),
    path('customers/<int:customer_id>/edit/', views.edit_customer_view, name='edit_customer'),
    path('customers/<int:customer_id>/delete/', views.delete_customer_view, name='delete_customer'),
    
    # Product Management
    path('products/', views.product_list_view, name='product_list'),
    path('products/manage/', views.product_manage_frontend_view, name='product_manage_frontend'),
    path('manage/products/', views.product_manage_frontend_view, name='manage_products_alt'),
    path('products/add/', views.add_product_view, name='add_product'),
    path('products/<int:product_id>/edit/', views.edit_product_view, name='edit_product'),
    path('products/<int:product_id>/delete/', views.delete_product_view, name='delete_product'),
]




