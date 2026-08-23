from django.urls import path
from . import views

urlpatterns = [
    # Portal Landing & Authentication
    path('', views.portal_select, name='portal_select'),
    path('login/admin/', views.admin_login_view, name='admin_login'),
    path('login/distributor/', views.distributor_login_view, name='distributor_login'),
    path('register/distributor/', views.distributor_register_view, name='distributor_register'),
    path('forgot-password/', views.forgot_password_view, name='forgot_password'),
    path('forgot-password/resend-otp/', views.resend_otp_view, name='resend_otp'),
    path('logout/', views.user_logout, name='logout'),


    # Admin Portal
    path('admin/dashboard/', views.admin_dashboard_view, name='admin_dashboard'),

    # Distributor Portal & QR Billing
    path('distributor/dashboard/', views.distributor_dashboard_view, name='distributor_dashboard'),
    path('distributor/profile/', views.distributor_profile_view, name='distributor_profile'),
    path('distributor/billing/', views.create_invoice_view, name='create_invoice'),
    path('invoice/<int:invoice_id>/', views.invoice_detail_view, name='invoice_detail'),
]
