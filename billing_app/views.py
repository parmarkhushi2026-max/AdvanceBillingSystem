import json
import csv
import uuid
import random
import time
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count, Q
from django.utils import timezone
from datetime import datetime, date, timedelta
from django.core.paginator import Paginator
from .models import UserProfile, Product, Invoice, InvoiceItem, OTPToken, Customer
from .forms import (
    AdminLoginForm, DistributorLoginForm, ForgotPasswordForm, VerifyOTPForm,
    ResetPasswordForm, DistributorRegistrationForm, DistributorProfileForm,
    CustomerForm, ProductForm, InvoiceCreationForm, InvoiceItemForm
)
from .decorators import (
    admin_required, distributor_required, role_required,
    api_login_required, api_admin_required
)
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods


def initialize_default_users():
    """Ensure default admin, distributor and demo products exist in the database."""
    # Admin Account
    admin_user = User.objects.filter(username='admin').first()
    if not admin_user:
        admin_user = User.objects.create_superuser('admin', 'admin@advancebilling.com', 'admin123')
        admin_user.first_name = 'Super'
        admin_user.last_name = 'Admin'
        admin_user.save()
    UserProfile.objects.get_or_create(
        user=admin_user,
        defaults={
            'role': 'ADMIN',
            'business_name': 'Advance Billing HQ',
            'phone': '+91 98765 43210',
            'upi_id': 'advancebilling@upi'
        }
    )

    # Distributor Account
    dist_user = User.objects.filter(username='distributor').first()
    if not dist_user:
        dist_user = User.objects.create_user('distributor', 'distributor@agency.com', 'dist123')
        dist_user.first_name = 'Rahul'
        dist_user.last_name = 'Sharma'
        dist_user.save()
    UserProfile.objects.get_or_create(
        user=dist_user,
        defaults={
            'role': 'DISTRIBUTOR',
            'business_name': 'Sharma Tech & Retail Distribution',
            'phone': '+91 98123 45678',
            'upi_id': 'sharmadist@upi'
        }
    )

    # Sample Products
    if Product.objects.count() == 0:
        Product.objects.bulk_create([
            Product(name='Wireless Barcode Scanner Pro', sku='HW-SCN-01', category='Hardware', price=Decimal('2499.00'), gst_rate=18.00, hsn_code='847160', unit='Pcs', stock=45),
            Product(name='Thermal Receipt Printer 80mm', sku='HW-PRN-02', category='Hardware', price=Decimal('4890.00'), gst_rate=18.00, hsn_code='844332', unit='Pcs', stock=30),
            Product(name='Advance POS Touch Terminal', sku='HW-POS-03', category='Hardware', price=Decimal('18500.00'), gst_rate=18.00, hsn_code='847130', unit='Pcs', stock=12),
            Product(name='Billing Software Annual License', sku='SW-LIC-01', category='Software', price=Decimal('5999.00'), gst_rate=18.00, hsn_code='997331', unit='License', stock=999),
            Product(name='Thermal Paper Rolls (Box of 50)', sku='SUP-PAP-01', category='Supplies', price=Decimal('850.00'), gst_rate=12.00, hsn_code='482340', unit='Box', stock=150),
            Product(name='QR Payment Display Stand', sku='ACC-STD-01', category='Accessories', price=Decimal('450.00'), gst_rate=18.00, hsn_code='392690', unit='Pcs', stock=80),
        ])

    # Sample Invoices (ID, customer name, total amount, and date)
    from .invoice_seeder import ensure_invoice_data_exists
    ensure_invoice_data_exists(skip_in_test=True)

# 1. Landing Page / Portal Selector
def portal_select(request):
    initialize_default_users()
    if request.user.is_authenticated:
        try:
            if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
                return redirect('admin_dashboard')
            return redirect('distributor_dashboard')
        except Exception:
            return redirect('distributor_dashboard')
    return render(request, 'home.html')

# 2. Admin Login View (Django Auth Backend)
def admin_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
            return redirect('admin_dashboard')
        return redirect('distributor_dashboard')

    if request.method == 'POST':
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            return api_login_admin(request)

        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            # Session-based authentication: configure expiry based on Remember Me
            if request.POST.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days persistent session
            else:
                request.session.set_expiry(0)  # Session cookie expires on browser close
            messages.success(request, f'Welcome back, Administrator {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or 'admin_dashboard'
            return redirect(next_url)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = AdminLoginForm(request)

    return render(request, 'auth/login_admin.html', {'form': form})

# 2.1 Admin Register View (Front-end)
def admin_register_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
            return redirect('admin_dashboard')
        return redirect('distributor_dashboard')
    
    # Render the pure HTML form which connects to the API via JS
    return render(request, 'auth/register_admin.html')

# 3. Distributor Login View (Django Auth Backend)
def distributor_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
            return redirect('admin_dashboard')
        return redirect('distributor_dashboard')

    if request.method == 'POST':
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            return api_login_distributor(request)

        form = DistributorLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            # Session-based authentication: configure expiry based on Remember Me
            if request.POST.get('remember_me'):
                request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days persistent session
            else:
                request.session.set_expiry(0)  # Session cookie expires on browser close
            messages.success(request, f'Welcome back, Distributor {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or 'distributor_dashboard'
            return redirect(next_url)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, error)
    else:
        form = DistributorLoginForm(request)

    return render(request, 'auth/login_distributor.html', {'form': form})

# 4. Logout View
def user_logout(request):
    username = request.user.username if request.user.is_authenticated else ''
    auth_logout(request)
    request.session.flush()  # Securely purge and invalidate session cookie and database session
    if username:
        messages.info(request, f'Goodbye {username}, you have been securely logged out.')
    else:
        messages.info(request, 'You have been securely logged out.')
    return redirect('portal_select')

# Dashboard Charts Data Preparation Helper
def prepare_dashboard_charts(queryset=None, is_distributor=False, distributor_user=None):
    if queryset is None:
        queryset = Invoice.objects.all()
    
    today = timezone.now().date()
    latest_inv = queryset.order_by('-created_at').first()
    
    if latest_inv and (today - latest_inv.created_at.date()).days > 6:
        end_date = latest_inv.created_at.date()
    else:
        end_date = today

    chart_dates = []
    chart_billed = []
    chart_collected = []
    chart_projected = []
    chart_invoices = []
    
    for i in reversed(range(7)):
        d = end_date - timedelta(days=i)
        chart_dates.append(d.strftime('%b %d'))
        day_qs = queryset.filter(created_at__date=d)
        
        day_billed = float(day_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
        day_collected = float(day_qs.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
        day_projected = round(day_billed * 1.08, 2)
        day_count = day_qs.count()
        
        chart_billed.append(day_billed)
        chart_collected.append(day_collected)
        chart_projected.append(day_projected)
        chart_invoices.append(day_count)

    # Total metrics
    total_billed = float(queryset.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
    total_collected = float(queryset.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
    total_inv_count = queryset.count()

    # Latest active day HUD
    latest_b = chart_billed[-1]
    latest_c = chart_collected[-1]
    hud_eff = round((latest_c / latest_b * 100), 1) if latest_b > 0 else (round((total_collected / total_billed * 100), 1) if total_billed > 0 else 100.0)

    # Status Breakdown
    paid_qs = queryset.filter(payment_status='PAID')
    pending_qs = queryset.filter(~Q(payment_status='PAID'))
    qr_qs = queryset.filter(payment_method__icontains='QR')
    cash_qs = queryset.filter(payment_method__icontains='Cash')

    paid_tot = float(paid_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
    pending_tot = float(pending_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
    qr_tot = float(qr_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
    cash_tot = float(cash_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))

    base_tot = total_billed if total_billed > 0 else 1.0
    paid_pct = round((paid_tot / base_tot) * 100, 1)
    pending_pct = round((pending_tot / base_tot) * 100, 1)
    qr_pct = round((qr_tot / base_tot) * 100, 1)
    cash_pct = round((cash_tot / base_tot) * 100, 1)

    # Compact notation
    if total_billed >= 100000:
        compact_total_billed = f"₹{total_billed/100000:.1f}L"
    elif total_billed >= 1000:
        compact_total_billed = f"₹{total_billed/1000:.1f}K"
    else:
        compact_total_billed = f"₹{total_billed:.0f}"

    # Donut slices data (Paid, Pending, UPI QR, Cash)
    donut_labels = ['Paid / Settled', 'Pending / Due', 'UPI QR Code', 'Cash / Direct']
    donut_values = [paid_tot, pending_tot, qr_tot, cash_tot]

    return {
        'chart_dates_json': json.dumps(chart_dates),
        'chart_billed_json': json.dumps(chart_billed),
        'chart_collected_json': json.dumps(chart_collected),
        'chart_revenue_json': json.dumps(chart_collected),
        'chart_projected_json': json.dumps(chart_projected),
        'chart_invoices_json': json.dumps(chart_invoices),
        
        'hud_date_label': f"{chart_dates[-1]}, {today.year}",
        'hud_billed_val': f"₹{latest_b:,.2f}",
        'hud_collected_val': f"₹{latest_c:,.2f}",
        'hud_efficiency_pct': f"{hud_eff}%",
        
        'compact_total_billed': compact_total_billed,
        'total_invoices_count': total_inv_count,
        
        'status_paid_tot': paid_tot,
        'status_paid_pct': paid_pct,
        'status_pending_tot': pending_tot,
        'status_pending_pct': pending_pct,
        'status_qr_tot': qr_tot,
        'status_qr_pct': qr_pct,
        'status_cash_tot': cash_tot,
        'status_cash_pct': cash_pct,
        
        'donut_labels_json': json.dumps(donut_labels),
        'donut_values_json': json.dumps(donut_values),
        'chart_window_label': f"{chart_dates[0]} - {chart_dates[-1]}",
    }


# 5. Admin Dashboard (Protected by @admin_required)
@admin_required
def admin_dashboard_view(request):
    initialize_default_users()
    total_invoices = Invoice.objects.count()
    total_revenue = Invoice.objects.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_distributors = UserProfile.objects.filter(role='DISTRIBUTOR').count()
    total_products = Product.objects.count()

    recent_invoices = Invoice.objects.all().order_by('-created_at')[:10]
    distributors = UserProfile.objects.filter(role='DISTRIBUTOR').select_related('user')

    # Prepare visual charts data
    charts_data = prepare_dashboard_charts(Invoice.objects.all(), is_distributor=False)

    context = {
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'total_distributors': total_distributors,
        'total_products': total_products,
        'recent_invoices': recent_invoices,
        'distributors': distributors,
        'role': 'Admin',
        **charts_data,
    }
    return render(request, 'dashboard/admin_dashboard.html', context)


# 5.1 Dedicated Reports Section View for Admin Dashboard
@admin_required
def admin_reports_view(request):
    """
    Dedicated Reports & Financial Analytics View for System Admin.
    Allows filtering by date range, distributor, payment status, and exports CSV.
    """
    initialize_default_users()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    distributor_id = request.GET.get('distributor_id', '').strip()
    status_filter = request.GET.get('status', '').strip()
    report_type = request.GET.get('type', 'sales').strip()

    invoices = Invoice.objects.all().select_related('distributor', 'distributor__profile')

    if distributor_id:
        invoices = invoices.filter(distributor_id=distributor_id)
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)
    date_range_error = None
    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if d_start > d_end:
                date_range_error = f"Invalid date range: From Date ({start_date_str}) cannot be after To Date ({end_date_str})."
                messages.error(request, date_range_error)
            else:
                invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            date_range_error = "Invalid date format. Please use YYYY-MM-DD."
            messages.error(request, date_range_error)
    elif start_date_str and not end_date_str:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            invoices = invoices.filter(created_at__date__gte=start_date_str)
        except Exception:
            pass
    elif end_date_str and not start_date_str:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            invoices = invoices.filter(created_at__date__lte=end_date_str)
        except Exception:
            pass

    # Aggregated Financial Metrics
    total_invoices_count = invoices.count()
    total_billed_val = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_tax_collected = invoices.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
    total_subtotal = invoices.aggregate(Sum('subtotal'))['subtotal__sum'] or Decimal('0.00')
    total_discount = invoices.aggregate(Sum('discount'))['discount__sum'] or Decimal('0.00')
    
    paid_qs = invoices.filter(payment_status='PAID')
    total_paid_val = paid_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    pending_qs = invoices.filter(payment_status='PENDING')
    total_pending_val = pending_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    avg_ticket_size = round(float(total_billed_val) / total_invoices_count, 2) if total_invoices_count > 0 else 0.0

    # Distributor Performance Summary
    distributor_perf = []
    distributors = User.objects.filter(profile__role='DISTRIBUTOR').select_related('profile')
    for d in distributors:
        d_invoices = Invoice.objects.filter(distributor=d)
        d_count = d_invoices.count()
        d_billed = d_invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
        d_collected = d_invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
        distributor_perf.append({
            'distributor': d,
            'business_name': getattr(d.profile, 'business_name', '') or d.username,
            'invoice_count': d_count,
            'total_billed': d_billed,
            'total_collected': d_collected,
        })
    distributor_perf.sort(key=lambda x: x['total_billed'], reverse=True)

    # Top selling items
    top_items = (
        InvoiceItem.objects.values('product_name')
        .annotate(total_qty=Sum('quantity'), total_sales=Sum('total'))
        .order_by('-total_qty')[:10]
    )

    context = {
        'invoices': invoices.order_by('-created_at')[:50],
        'distributors': distributors,
        'distributor_perf': distributor_perf,
        'top_items': top_items,
        'total_invoices_count': total_invoices_count,
        'total_billed_val': total_billed_val,
        'total_paid_val': total_paid_val,
        'total_pending_val': total_pending_val,
        'total_tax_collected': total_tax_collected,
        'total_subtotal': total_subtotal,
        'total_discount': total_discount,
        'avg_ticket_size': avg_ticket_size,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'distributor_id': distributor_id,
        'status_filter': status_filter,
        'report_type': report_type,
        'date_range_error': date_range_error,
        'role': 'Admin',
    }
    return render(request, 'dashboard/admin_reports.html', context)


@admin_required
def admin_reports_export_csv_view(request):
    """
    Exports CSV reports for Sales, GST Tax, or Distributor Performance.
    Respects date range, distributor, and payment status filters if provided.
    """
    report_type = request.GET.get('type', 'sales').lower()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    distributor_id = request.GET.get('distributor_id', '').strip()
    status_filter = request.GET.get('status', '').strip()

    invoices = Invoice.objects.all().select_related('distributor', 'distributor__profile')
    if distributor_id:
        invoices = invoices.filter(distributor_id=distributor_id)
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)
    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if d_start > d_end:
                messages.error(request, f"Cannot export CSV: Invalid date range (From Date {start_date_str} is after To Date {end_date_str}).")
                return redirect('admin_reports')
            invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format for CSV export.")
            return redirect('admin_reports')
    elif start_date_str:
        try:
            invoices = invoices.filter(created_at__date__gte=start_date_str)
        except Exception:
            pass
    elif end_date_str:
        try:
            invoices = invoices.filter(created_at__date__lte=end_date_str)
        except Exception:
            pass

    response = HttpResponse(content_type='text/csv')
    
    if report_type == 'gst':
        response['Content-Disposition'] = 'attachment; filename="AdvanceBilling_GST_Report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice Number', 'Date', 'Distributor', 'Customer Name', 'Taxable Subtotal (INR)', 'GST Tax Amount (INR)', 'Grand Total (INR)', 'Status'])
        for inv in invoices.order_by('-created_at'):
            writer.writerow([
                inv.invoice_number,
                inv.created_at.strftime('%Y-%m-%d %H:%M'),
                inv.distributor.username if inv.distributor else 'System',
                inv.customer_name,
                float(inv.subtotal),
                float(inv.tax_amount),
                float(inv.grand_total),
                inv.payment_status
            ])
    elif report_type == 'distributor':
        response['Content-Disposition'] = 'attachment; filename="AdvanceBilling_Distributors_Report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Distributor Username', 'Business Name', 'Phone', 'Total Invoices', 'Total Billed (INR)', 'Total Collected (INR)'])
        d_queryset = User.objects.filter(profile__role='DISTRIBUTOR').select_related('profile')
        if distributor_id:
            d_queryset = d_queryset.filter(id=distributor_id)
        for d in d_queryset:
            d_invs = invoices.filter(distributor=d)
            b_name = getattr(d.profile, 'business_name', '') or d.username
            phone = getattr(d.profile, 'phone', '')
            inv_count = d_invs.count()
            billed = float(d_invs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
            collected = float(d_invs.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00'))
            writer.writerow([d.username, b_name, phone, inv_count, billed, collected])
    else: # sales
        response['Content-Disposition'] = 'attachment; filename="AdvanceBilling_Sales_Report.csv"'
        writer = csv.writer(response)
        writer.writerow(['Invoice Number', 'Date', 'Distributor', 'Customer Name', 'Customer Phone', 'Payment Method', 'Subtotal', 'Tax Amount', 'Discount', 'Grand Total', 'Status'])
        for inv in invoices.order_by('-created_at'):
            writer.writerow([
                inv.invoice_number,
                inv.created_at.strftime('%Y-%m-%d %H:%M'),
                inv.distributor.username if inv.distributor else 'System',
                inv.customer_name,
                inv.customer_phone,
                inv.payment_method,
                float(inv.subtotal),
                float(inv.tax_amount),
                float(inv.discount),
                float(inv.grand_total),
                inv.payment_status
            ])
    return response


# 6. Distributor Dashboard (Protected by @distributor_required)

@distributor_required
def distributor_dashboard_view(request):
    initialize_default_users()
    distributor = request.user
    profile = getattr(distributor, 'profile', None)
    upi_id = profile.upi_id if profile else 'merchant@upi'
    business_name = profile.business_name if profile else 'Distributor Agency'

    my_invoices = Invoice.objects.filter(distributor=distributor).order_by('-created_at')
    if not my_invoices.exists() and request.user.is_superuser:
        my_invoices = Invoice.objects.all().order_by('-created_at')

    my_revenue = my_invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    my_invoice_count = my_invoices.count()
    products = Product.objects.all()

    # Prepare distributor-specific visual charts data
    charts_data = prepare_dashboard_charts(my_invoices, is_distributor=True, distributor_user=distributor)

    context = {
        'invoices': my_invoices[:8],
        'total_revenue': my_revenue,
        'invoice_count': my_invoice_count,
        'products_count': products.count(),
        'upi_id': upi_id,
        'business_name': business_name,
        'products': products,
        'role': 'Distributor',
        **charts_data,
    }
    return render(request, 'dashboard/distributor_dashboard.html', context)

# 7. Create QR Bill & Invoice View (Protected by @distributor_required)
@distributor_required
def create_invoice_view(request):
    initialize_default_users()
    products = Product.objects.all().order_by('name')
    profile = getattr(request.user, 'profile', None)
    upi_id = profile.upi_id if profile else 'advancebilling@upi'
    business_name = profile.business_name if profile else 'Advance Billing Agency'

    if request.method == 'POST':
        form = InvoiceCreationForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                invoice = form.save(distributor=request.user)
                messages.success(request, f'Invoice #{invoice.invoice_number} created with QR Code successfully!')
                return redirect('invoice_detail', invoice_id=invoice.id)
            except Exception as e:
                messages.error(request, f'Failed to generate invoice: {str(e)}')
        else:
            for field, errs in form.errors.items():
                for err in errs:
                    field_label = field.replace('_', ' ').capitalize() if field != '__all__' else 'Error'
                    messages.error(request, f'{field_label}: {err}')
    else:
        initial_data = {}
        if request.GET.get('customer_id'):
            initial_data['customer'] = request.GET.get('customer_id')
        if request.GET.get('customer_name'):
            initial_data['customer_name'] = request.GET.get('customer_name')
        if request.GET.get('customer_phone'):
            initial_data['customer_phone'] = request.GET.get('customer_phone')
        form = InvoiceCreationForm(user=request.user, initial=initial_data)

    customers = form.fields['customer'].queryset

    # Products JSON representation for instant dynamic dropdown line items
    products_catalog = [
        {
            'id': p.id,
            'name': p.name,
            'sku': p.sku or '',
            'price': str(p.price),
            'tax': str(p.gst_rate),
            'stock': p.stock,
            'unit': p.unit or 'Pcs'
        }
        for p in products
    ]

    context = {
        'form': form,
        'products': products,
        'products_catalog_json': json.dumps(products_catalog),
        'customers': customers,
        'upi_id': upi_id,
        'business_name': business_name,
        'role': 'Admin' if (request.user.is_superuser or (profile and profile.role == 'ADMIN')) else 'Distributor',
    }
    return render(request, 'billing/create_invoice.html', context)

# 8. Invoice Detail & Printable QR Receipt
@login_required
def invoice_detail_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    profile = getattr(invoice.distributor, 'profile', None) if invoice.distributor else None
    upi_id = profile.upi_id if profile else 'advancebilling@upi'
    business_name = profile.business_name if profile else 'Advance Billing Agency'

    # Dynamic UPI Payment format
    upi_payment_url = f"upi://pay?pa={upi_id}&pn={business_name.replace(' ', '%20')}&am={invoice.grand_total}&tn={invoice.invoice_number}&cu=INR"

    # Build dynamic product summary
    product_summary = ", ".join([f"{item.product_name} (x{item.quantity})" for item in invoice.items.all()])
    formatted_date = invoice.created_at.strftime('%Y-%m-%d %H:%M')
    
    qr_data = (
        f"Invoice No: {invoice.invoice_number}\n"
        f"Date: {formatted_date}\n"
        f"Customer: {invoice.customer_name}\n"
        f"Products: {product_summary}\n"
        f"Total Bill: Rs.{invoice.grand_total}"
    )

    # Generate UPI Payment QR base64 for interactive switcher
    import qrcode
    from io import BytesIO
    import base64
    upi_qr_obj = qrcode.QRCode(box_size=6, border=2)
    upi_qr_obj.add_data(upi_payment_url)
    upi_qr_obj.make(fit=True)
    buf_upi = BytesIO()
    upi_qr_obj.make_image(fill_color="black", back_color="white").save(buf_upi, format="PNG")
    upi_qr_base64 = f"data:image/png;base64,{base64.b64encode(buf_upi.getvalue()).decode('utf-8')}"

    server_qr_base64 = invoice.qr_code_base64

    context = {
        'invoice': invoice,
        'items': invoice.items.all(),
        'upi_id': upi_id,
        'business_name': business_name,
        'upi_payment_url': upi_payment_url,
        'qr_data': qr_data,
        'server_qr_base64': server_qr_base64,
        'invoice_qr_base64': server_qr_base64,
        'upi_qr_base64': upi_qr_base64,
    }
    return render(request, 'billing/invoice_detail.html', context)


def number_to_indian_currency_words(amount):
    """Convert a numeric amount into standard Indian currency words (Rupees ... Only)."""
    try:
        val = int(round(float(amount)))
    except (ValueError, TypeError):
        return ""
    if val == 0:
        return "Rupees Zero Only"
    
    ones = ["", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten",
            "Eleven", "Twelve", "Thirteen", "Fourteen", "Fifteen", "Sixteen", "Seventeen", "Eighteen", "Nineteen"]
    tens = ["", "", "Twenty", "Thirty", "Forty", "Fifty", "Sixty", "Seventy", "Eighty", "Ninety"]
    
    def two_digits(n):
        if n < 20:
            return ones[n]
        return tens[n // 10] + (" " + ones[n % 10] if n % 10 != 0 else "")
    
    def three_digits(n):
        if n >= 100:
            return ones[n // 100] + " Hundred" + (" and " + two_digits(n % 100) if n % 100 != 0 else "")
        return two_digits(n)
    
    parts = []
    crore = val // 10000000
    val %= 10000000
    lakh = val // 100000
    val %= 100000
    thousand = val // 1000
    val %= 1000
    remainder = val
    
    if crore > 0:
        parts.append(three_digits(crore) + " Crore")
    if lakh > 0:
        parts.append(two_digits(lakh) + " Lakh")
    if thousand > 0:
        parts.append(two_digits(thousand) + " Thousand")
    if remainder > 0:
        parts.append(three_digits(remainder))
    
    words = " ".join(parts).strip()
    return f"Rupees {words} Only"


# 8-Preview. Dedicated Preview Invoice Page with Complete Details & Verified QR Code
@login_required
def invoice_preview_view(request, invoice_id):
    """
    Renders a comprehensive, high-aesthetic 'Preview Invoice' page for any invoice.
    Includes full company & customer metadata, line items, taxes (CGST/SGST),
    amount in words, verified dynamic QR code, and interactive UPI payment QR switcher.
    Supports both standard A4 Tax Invoice preview and 80mm Thermal POS Slip preview modes.
    """
    from .invoice_qr import generate_invoice_qr_bundle
    invoice = get_object_or_404(Invoice, id=invoice_id)
    profile = getattr(invoice.distributor, 'profile', None) if invoice.distributor else None
    
    business_name = getattr(profile, 'business_name', None) or 'Advance Billing Agency'
    business_phone = getattr(profile, 'phone', None) or '+91 98765 43210'
    business_email = invoice.distributor.email if (invoice.distributor and invoice.distributor.email) else 'billing@advancebilling.com'
    business_address = getattr(profile, 'address', None) or 'Commercial Hub, Business Park, Phase II'
    business_gstin = getattr(profile, 'gstin', None) or '27AABCU9603R1ZM'
    upi_id = getattr(profile, 'upi_id', None) or 'advancebilling@upi'

    # Build QR Code bundle encoding core database attributes
    qr_bundle = generate_invoice_qr_bundle(invoice)

    # Dynamic UPI Payment format & QR
    upi_payment_url = f"upi://pay?pa={upi_id}&pn={business_name.replace(' ', '%20')}&am={invoice.grand_total}&tn={invoice.invoice_number}&cu=INR"
    
    import qrcode
    from io import BytesIO
    import base64
    upi_qr_obj = qrcode.QRCode(box_size=6, border=2)
    upi_qr_obj.add_data(upi_payment_url)
    upi_qr_obj.make(fit=True)
    buf_upi = BytesIO()
    upi_qr_obj.make_image(fill_color="black", back_color="white").save(buf_upi, format="PNG")
    upi_qr_base64 = f"data:image/png;base64,{base64.b64encode(buf_upi.getvalue()).decode('utf-8')}"

    # Financial and Tax calculations
    subtotal = float(invoice.subtotal) if invoice.subtotal else 0.0
    tax_amount = float(invoice.tax_amount) if invoice.tax_amount else 0.0
    cgst_amount = round(tax_amount / 2, 2)
    sgst_amount = round(tax_amount / 2, 2)
    grand_total = float(invoice.grand_total) if invoice.grand_total else 0.0
    grand_total_words = number_to_indian_currency_words(grand_total)

    items = list(invoice.items.all())
    enriched_items = []
    for idx, it in enumerate(items, 1):
        rate = float(it.unit_price) if it.unit_price else 0.0
        tax_pct = float(it.tax_rate) if it.tax_rate else 18.0
        line_tot = float(it.total) if it.total else 0.0
        base_line = round(rate * it.quantity, 2)
        it_tax = round(line_tot - base_line, 2) if line_tot > base_line else round(base_line * (tax_pct / 100), 2)
        enriched_items.append({
            'index': idx,
            'item': it,
            'name': it.product_name,
            'quantity': it.quantity,
            'unit_price': rate,
            'tax_rate': tax_pct,
            'cgst_rate': tax_pct / 2,
            'sgst_rate': tax_pct / 2,
            'tax_amount': it_tax,
            'total': line_tot,
        })

    is_admin = request.user.is_superuser or (profile and profile.role == 'ADMIN')

    context = {
        'invoice': invoice,
        'items': items,
        'enriched_items': enriched_items,
        'bundle': qr_bundle,
        'qr_base64': qr_bundle['qr_base64'],
        'invoice_qr_base64': qr_bundle['qr_base64'],
        'upi_qr_base64': upi_qr_base64,
        'upi_payment_url': upi_payment_url,
        'text_payload': qr_bundle['text_payload'],
        'json_payload': qr_bundle['json_payload'],
        'business_name': business_name,
        'business_phone': business_phone,
        'business_email': business_email,
        'business_address': business_address,
        'business_gstin': business_gstin,
        'upi_id': upi_id,
        'subtotal': subtotal,
        'tax_amount': tax_amount,
        'cgst_amount': cgst_amount,
        'sgst_amount': sgst_amount,
        'grand_total': grand_total,
        'grand_total_words': grand_total_words,
        'is_admin': is_admin,
    }
    return render(request, 'billing/invoice_preview.html', context)


# 8-Preview-API. REST API endpoint to fetch complete Preview Invoice data & QR as JSON
def api_invoice_preview(request, invoice_id):
    """
    JSON API returning all structured invoice details, line items, tax split,
    amount in words, and QR Data URIs for client-side consumption or mobile preview.
    """
    from .invoice_qr import generate_invoice_qr_bundle
    invoice = get_object_or_404(Invoice, id=invoice_id)
    profile = getattr(invoice.distributor, 'profile', None) if invoice.distributor else None
    
    business_name = profile.business_name if profile and profile.business_name else 'Advance Billing Agency'
    upi_id = profile.upi_id if profile and profile.upi_id else 'advancebilling@upi'
    bundle = generate_invoice_qr_bundle(invoice)

    subtotal = float(invoice.subtotal) if invoice.subtotal else 0.0
    tax_amount = float(invoice.tax_amount) if invoice.tax_amount else 0.0
    grand_total = float(invoice.grand_total) if invoice.grand_total else 0.0

    items_data = [
        {
            'name': item.product_name,
            'quantity': item.quantity,
            'unit_price': float(item.unit_price) if item.unit_price else 0.0,
            'tax_rate': float(item.tax_rate) if item.tax_rate else 18.0,
            'total': float(item.total) if item.total else 0.0,
        }
        for item in invoice.items.all()
    ]

    return JsonResponse({
        'status': 'success',
        'success': True,
        'invoice': {
            'id': invoice.id,
            'invoice_number': invoice.invoice_number,
            'created_at': invoice.created_at.strftime('%Y-%m-%d %H:%M'),
            'customer_name': invoice.customer_name,
            'customer_phone': invoice.customer_phone or '',
            'payment_method': invoice.payment_method,
            'payment_status': invoice.payment_status,
            'subtotal': subtotal,
            'tax_amount': tax_amount,
            'cgst_amount': round(tax_amount / 2, 2),
            'sgst_amount': round(tax_amount / 2, 2),
            'grand_total': grand_total,
            'grand_total_words': number_to_indian_currency_words(grand_total),
            'business_name': business_name,
            'upi_id': upi_id,
            'items': items_data,
            'qr_code_base64': bundle['qr_base64'],
            'qr_payload': bundle['text_payload'],
        }
    })


    # 8-Details-API. Fetch complete invoice details (ID, customer name, total, date) from database
def api_invoice_details(request, invoice_id):
    """
    Fetch complete invoice details directly from the database:
    - ID: Invoice primary key ID and Invoice Number
    - Customer Name: Customer name and contact
    - Total: Grand Total, Subtotal, and Tax
    - Date: Creation Date
    - Line items summary and QR payload
    Supports ?download=1 to export/download as JSON attachment.
    """
    try:
        # Fetch corresponding invoice record and related customer entry from DB
        invoice = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').get(id=invoice_id)
    except Invoice.DoesNotExist:
        return JsonResponse({
            'status': 'error',
            'success': False,
            'error': f'Invoice with ID #{invoice_id} not found in database.'
        }, status=404)

    details = invoice.get_complete_details()
    
    response = JsonResponse({
        'status': 'success',
        'success': True,
        'invoice': {
            'id': details['id'],
            'invoice_id': details['invoice_id'],
            'invoice_number': details['invoice_number'],
            'customer_name': details['customer_name'],
            'customer_phone': details['customer_phone'],
            'total': details['total'],
            'total_amount': details['total_amount'],
            'grand_total': details['total'],
            'subtotal': details['subtotal'],
            'tax_amount': details['tax_amount'],
            'date': details['date'],
            'iso_date': details['iso_date'],
            'payment_method': details['payment_method'],
            'payment_status': details['payment_status'],
            'items_count': len(details['items']),
            'items': details['items'],
            'qr_payload': details['qr_payload'],
            'qr_code_base64': details['qr_code_base64'],
        }
    }, json_dumps_params={'indent': 2})

    if request.GET.get('download') in ('1', 'true', 'yes'):
        response['Content-Disposition'] = f'attachment; filename="Invoice_{details["invoice_number"]}_Details.json"'
    return response


def api_all_invoices_details(request):
    """
    Fetch complete invoice details (ID, customer name, total, date) for all invoices from the database.
    Supports limit, query parameters, and ?download=1 for file download.
    """
    limit = int(request.GET.get('limit', 100))
    invoices = Invoice.objects.prefetch_related('items').all().order_by('-created_at')[:limit]
    
    results = []
    for inv in invoices:
        d = inv.get_complete_details()
        results.append({
            'id': d['id'],
            'invoice_id': d['invoice_id'],
            'invoice_number': d['invoice_number'],
            'customer_name': d['customer_name'],
            'customer_phone': d['customer_phone'],
            'total': d['total'],
            'total_amount': d['total_amount'],
            'grand_total': d['total'],
            'date': d['date'],
            'iso_date': d['iso_date'],
            'payment_status': d['payment_status'],
            'payment_method': d['payment_method'],
            'items_count': len(d['items']),
        })
        
    response = JsonResponse({
        'status': 'success',
        'success': True,
        'total_count': len(results),
        'invoices': results
    }, json_dumps_params={'indent': 2})

    if request.GET.get('download') in ('1', 'true', 'yes'):
        response['Content-Disposition'] = 'attachment; filename="All_Invoices_Details.json"'
    return response


# 8b. Dedicated Invoice QR Inspection & Showcase View
@login_required
def invoice_qr_view(request, invoice_id):
    """
    Fetches the saved invoice model from the database, extracts core values
    (Invoice ID, Customer Name, Total Amount, Date), and renders a dedicated QR showcase.
    """
    from .invoice_qr import generate_invoice_qr_bundle
    invoice = get_object_or_404(Invoice, id=invoice_id)
    qr_bundle = generate_invoice_qr_bundle(invoice)
    
    context = {
        'invoice': invoice,
        'bundle': qr_bundle,
        'encoded_payload': qr_bundle['text_payload'],
        'json_payload': qr_bundle['json_payload'],
        'qr_base64': qr_bundle['qr_base64'],
        'items': qr_bundle['items'],
    }
    return render(request, 'billing/invoice_qr.html', context)


# 8c. Direct Invoice QR PNG Image View
def invoice_qr_image_view(request, invoice_id):
    """
    Fetches the saved invoice model and generates a raw PNG QR code image encoding these values
    using libraries like qrcode or segno.
    Returns HTTP 200 with Content-Type: image/png.
    """
    from .invoice_qr import generate_invoice_qr
    invoice = get_object_or_404(Invoice, id=invoice_id)
    fmt = request.GET.get('format', 'text')
    engine = request.GET.get('engine', 'auto')
    try:
        box_size = int(request.GET.get('size', 6))
    except (ValueError, TypeError):
        box_size = 6
    qr_bytes = generate_invoice_qr(invoice, engine=engine, payload_format=fmt, box_size=box_size, as_base64=False)
    return HttpResponse(qr_bytes, content_type='image/png')


# 8d. REST API Endpoint for Invoice QR Code
def api_invoice_qr_code(request, invoice_id):
    """
    JSON API returning fetched invoice data and the generated QR code (base64 Data URI)
    supporting both qrcode and segno engines and multiple payload formats ('text', 'upi', 'json').
    """
    from .invoice_qr import generate_invoice_qr_bundle
    invoice = get_object_or_404(Invoice, id=invoice_id)
    engine = request.GET.get('engine', 'auto')
    fmt = request.GET.get('mode', request.GET.get('format', 'text'))
    bundle = generate_invoice_qr_bundle(invoice, engine=engine, payload_format=fmt)
    return JsonResponse({
        'status': 'success',
        'success': True,
        'invoice_id': bundle['invoice_id'],
        'invoice_number': bundle['invoice_number'],
        'customer_name': bundle['customer_name'],
        'customer_phone': bundle['customer_phone'],
        'total_amount': bundle['total_amount'],
        'date': bundle['date'],
        'active_payload': bundle.get('active_payload', bundle['text_payload']),
        'encoded_payload': bundle['text_payload'],
        'json_payload': bundle['json_payload'],
        'qr_data_uri': bundle['qr_base64'],
        'qr_image_url': f"/invoice/{invoice.id}/qr.png?engine={bundle.get('engine_used', 'auto')}&format={fmt}",
        'engine_used': bundle.get('engine_used', 'auto'),
    })


# 9. Forgot Password View (Multi-step DB-backed OTP flow)
def forgot_password_view(request):
    initialize_default_users()
    
    # Reset flow if requested
    if request.GET.get('reset') == '1':
        for key in ['reset_user_id', 'reset_otp', 'reset_identity', 'reset_step']:
            if key in request.session:
                del request.session[key]
        return redirect('forgot_password')

    step = request.session.get('reset_step', 1)
    user_id = request.session.get('reset_user_id')
    stored_otp = request.session.get('reset_otp')
    identity = request.session.get('reset_identity', '')

    forgot_form = ForgotPasswordForm()
    verify_form = VerifyOTPForm()
    reset_form = ResetPasswordForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        # STEP 1: Request & Generate DB-backed OTP for Username/Email
        if action == 'request_otp' or step == 1:
            forgot_form = ForgotPasswordForm(request.POST)
            if forgot_form.is_valid():
                input_id = forgot_form.cleaned_data['identity'].strip()
                user = User.objects.filter(Q(username__iexact=input_id) | Q(email__iexact=input_id)).first()
                
                if user:
                    # Generate OTP and save to Database (OTPToken table)
                    token = OTPToken.generate_otp_for_user(user, validity_minutes=10)
                    otp_code = token.otp_code

                    request.session['reset_user_id'] = user.id
                    request.session['reset_otp'] = otp_code
                    request.session['reset_identity'] = user.username
                    request.session['reset_step'] = 2
                    
                    messages.success(
                        request,
                        f"🔐 DB OTP GENERATED & STORED: Your 6-digit code is [{otp_code}]. (Saved in Database, Valid 10 mins)"
                    )
                    return redirect('forgot_password')
                else:
                    messages.error(request, "No account found matching that username or email address.")

        # STEP 2: Validate 6-digit OTP from Database
        elif action == 'verify_otp' or (step == 2 and action != 'request_otp'):
            verify_form = VerifyOTPForm(request.POST)
            otp_entered = request.POST.get('otp_code', '').strip()
            
            # Combine input boxes if multi-box OTP sent
            if not otp_entered:
                digit_keys = [f'otp_{i}' for i in range(1, 7)]
                if all(k in request.POST for k in digit_keys):
                    otp_entered = "".join([request.POST.get(k, '') for k in digit_keys])

            # Query DB for OTP matching user and code
            token = OTPToken.objects.filter(
                user_id=user_id,
                otp_code=otp_entered
            ).order_by('-created_at').first()

            if token and token.is_valid():
                # Mark as verified in DB so it cannot be reused
                token.is_verified = True
                token.save()

                request.session['reset_step'] = 3
                messages.success(request, "✅ Database OTP validated successfully! Please enter your new password.")
                return redirect('forgot_password')
            elif token and not token.is_valid():
                messages.error(request, "⏰ This OTP code has expired or was already used. Please click 'Resend OTP Code'.")
                verify_form = VerifyOTPForm(initial={'otp_code': otp_entered})
            else:
                messages.error(request, "❌ Invalid OTP code. Please check the code and try again.")
                verify_form = VerifyOTPForm(initial={'otp_code': otp_entered})

        # STEP 3: Reset Password
        elif action == 'reset_password' or step == 3:
            reset_form = ResetPasswordForm(request.POST)
            if reset_form.is_valid():
                new_pass = reset_form.cleaned_data['new_password']
                try:
                    user = User.objects.get(id=user_id)
                    user.set_password(new_pass)
                    user.save()

                    # Clear reset session
                    for key in ['reset_user_id', 'reset_otp', 'reset_identity', 'reset_step']:
                        if key in request.session:
                            del request.session[key]

                    messages.success(request, "🎉 Password reset successful! You can now log in with your new password.")
                    return redirect('portal_select')
                except User.DoesNotExist:
                    messages.error(request, "Session expired or invalid user. Please start again.")
                    request.session['reset_step'] = 1
                    return redirect('forgot_password')

    context = {
        'step': step,
        'identity': identity,
        'stored_otp': stored_otp,
        'forgot_form': forgot_form,
        'verify_form': verify_form,
        'reset_form': reset_form,
    }
    return render(request, 'auth/forgot_password.html', context)

# Admin Specific Forgot Password View (Multi-step DB-backed OTP flow)
def admin_forgot_password_view(request):
    initialize_default_users()
    
    # Reset flow if requested
    if request.GET.get('reset') == '1':
        for key in ['admin_reset_user_id', 'admin_reset_otp', 'admin_reset_identity', 'admin_reset_step']:
            if key in request.session:
                del request.session[key]
        return redirect('admin_forgot_password')

    step = request.session.get('admin_reset_step', 1)
    user_id = request.session.get('admin_reset_user_id')
    stored_otp = request.session.get('admin_reset_otp')
    identity = request.session.get('admin_reset_identity', '')

    forgot_form = ForgotPasswordForm()
    verify_form = VerifyOTPForm()
    reset_form = ResetPasswordForm()

    if request.method == 'POST':
        action = request.POST.get('action')

        # STEP 1: Request & Generate DB-backed OTP for Username/Email
        if action == 'request_otp' or step == 1:
            forgot_form = ForgotPasswordForm(request.POST)
            if forgot_form.is_valid():
                input_id = forgot_form.cleaned_data['identity'].strip()
                user = User.objects.filter(Q(username__iexact=input_id) | Q(email__iexact=input_id)).first()
                
                if user and (user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'ADMIN')):
                    # Generate OTP and save to Database (OTPToken table)
                    token = OTPToken.generate_otp_for_user(user, validity_minutes=10)
                    otp_code = token.otp_code

                    request.session['admin_reset_user_id'] = user.id
                    request.session['admin_reset_otp'] = otp_code
                    request.session['admin_reset_identity'] = user.username
                    request.session['admin_reset_step'] = 2
                    
                    messages.success(
                        request,
                        f"🔐 DB OTP GENERATED & STORED: Your 6-digit code is [{otp_code}]. (Saved in Database, Valid 10 mins)"
                    )
                    return redirect('admin_forgot_password')
                else:
                    messages.error(request, "No admin account found matching that username or email address.")

        # STEP 2: Validate 6-digit OTP from Database
        elif action == 'verify_otp' or (step == 2 and action != 'request_otp'):
            verify_form = VerifyOTPForm(request.POST)
            otp_entered = request.POST.get('otp_code', '').strip()
            
            # Combine input boxes if multi-box OTP sent
            if not otp_entered:
                digit_keys = [f'otp_{i}' for i in range(1, 7)]
                if all(k in request.POST for k in digit_keys):
                    otp_entered = "".join([request.POST.get(k, '') for k in digit_keys])

            # Query DB for OTP matching user and code
            token = OTPToken.objects.filter(
                user_id=user_id,
                otp_code=otp_entered
            ).order_by('-created_at').first()

            if token and token.is_valid():
                # Mark as verified in DB so it cannot be reused
                token.is_verified = True
                token.save()

                request.session['admin_reset_step'] = 3
                messages.success(request, "✅ Database OTP validated successfully! Please enter your new password.")
                return redirect('admin_forgot_password')
            elif token and not token.is_valid():
                messages.error(request, "⏰ This OTP code has expired or was already used. Please click 'Resend OTP Code'.")
                verify_form = VerifyOTPForm(initial={'otp_code': otp_entered})
            else:
                messages.error(request, "❌ Invalid OTP code. Please check the code and try again.")
                verify_form = VerifyOTPForm(initial={'otp_code': otp_entered})

        # STEP 3: Reset Password
        elif action == 'reset_password' or step == 3:
            reset_form = ResetPasswordForm(request.POST)
            if reset_form.is_valid():
                new_pass = reset_form.cleaned_data['new_password']
                try:
                    user = User.objects.get(id=user_id)
                    user.set_password(new_pass)
                    user.save()

                    # Clear reset session
                    for key in ['admin_reset_user_id', 'admin_reset_otp', 'admin_reset_identity', 'admin_reset_step']:
                        if key in request.session:
                            del request.session[key]

                    messages.success(request, "🎉 Admin Password reset successful! You can now log in with your new password.")
                    return redirect('admin_login')
                except User.DoesNotExist:
                    messages.error(request, "Session expired or invalid user. Please start again.")
                    request.session['admin_reset_step'] = 1
                    return redirect('admin_forgot_password')

    context = {
        'step': step,
        'identity': identity,
        'stored_otp': stored_otp,
        'forgot_form': forgot_form,
        'verify_form': verify_form,
        'reset_form': reset_form,
    }
    return render(request, 'auth/admin_forgot_password.html', context)


# 10. Resend DB OTP View (AJAX / POST)
def resend_otp_view(request):
    if request.method == 'POST':
        user_id = request.session.get('reset_user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'Session expired. Please request OTP again.'}, status=400)
        
        try:
            user = User.objects.get(id=user_id)
            token = OTPToken.generate_otp_for_user(user, validity_minutes=10)
            new_otp = token.otp_code
            request.session['reset_otp'] = new_otp

            return JsonResponse({
                'success': True,
                'otp': new_otp,
                'message': f'New OTP code [{new_otp}] generated & saved to database successfully!'
            })
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User account not found.'}, status=404)
    return JsonResponse({'success': False, 'message': 'Method not allowed.'}, status=405)


def admin_resend_otp_view(request):
    if request.method == 'POST':
        user_id = request.session.get('admin_reset_user_id')
        if not user_id:
            return JsonResponse({'success': False, 'message': 'Session expired. Please request OTP again.'}, status=400)
        
        try:
            user = User.objects.get(id=user_id)
            token = OTPToken.generate_otp_for_user(user, validity_minutes=10)
            new_otp = token.otp_code
            request.session['admin_reset_otp'] = new_otp

            return JsonResponse({
                'success': True,
                'otp': new_otp,
                'message': f'New OTP code [{new_otp}] generated & saved to database successfully!'
            })
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'User account not found.'}, status=404)
    return JsonResponse({'success': False, 'message': 'Method not allowed.'}, status=405)

# 11. Distributor Registration View
def distributor_register_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        return redirect('distributor_dashboard')

    if request.method == 'POST':
        form = DistributorRegistrationForm(request.POST)
        if form.is_valid():
            full_name = form.cleaned_data['full_name'].strip()
            name_parts = full_name.split(' ', 1)
            first_name = name_parts[0]
            last_name = name_parts[1] if len(name_parts) > 1 else ''

            username = form.cleaned_data['username'].strip()
            email = form.cleaned_data['email'].strip()
            password = form.cleaned_data['password']
            business_name = form.cleaned_data.get('business_name', '').strip() or f"{first_name}'s Agency"
            phone = form.cleaned_data.get('phone', '').strip()
            upi_id = form.cleaned_data.get('upi_id', 'merchant@upi').strip()

            # Create User
            user = User.objects.create_user(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name
            )

            # Update UserProfile created by post_save signal
            profile, _ = UserProfile.objects.get_or_create(user=user)
            profile.role = 'DISTRIBUTOR'
            profile.business_name = business_name
            profile.phone = phone
            profile.upi_id = upi_id
            profile.save()

            # Save User & UserProfile to Database
            messages.success(
                request,
                f"🎉 Registration successful! Account created for '{username}'. Please sign in with your credentials to access the distributor portal."
            )
            return redirect('distributor_login')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = DistributorRegistrationForm()

    return render(request, 'auth/register_distributor.html', {'form': form})


# 12. Distributor Profile View
@distributor_required
def distributor_profile_view(request):
    initialize_default_users()
    user = request.user
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={'role': 'DISTRIBUTOR'})

    # Calculate statistics for this distributor
    my_invoices = Invoice.objects.filter(distributor=user)
    if not my_invoices.exists() and user.is_superuser:
        my_invoices = Invoice.objects.all()

    total_invoices = my_invoices.count()
    total_earnings = my_invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    full_name = user.get_full_name() or user.username

    if request.method == 'POST':
        form = DistributorProfileForm(request.POST, user=user)
        if form.is_valid():
            pwd_changed = bool(form.cleaned_data.get('new_password'))
            user, profile = form.save_profile(user)

            if pwd_changed:
                from django.contrib.auth import update_session_auth_hash
                update_session_auth_hash(request, user)
                messages.success(request, "🎉 Profile and password updated successfully in Database!")
            else:
                messages.success(request, "🎉 Profile details updated and saved to Database successfully!")
                
            return redirect('distributor_profile')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = DistributorProfileForm(user=user, initial={
            'full_name': full_name,
            'email': user.email or '',
            'business_name': profile.business_name or '',
            'phone': profile.phone or '',
            'upi_id': profile.upi_id or 'merchant@upi',
        })

    context = {
        'user_obj': user,
        'profile': profile,
        'form': form,
        'total_invoices': total_invoices,
        'total_earnings': total_earnings,
        'role': 'Admin' if (user.is_superuser or (profile and profile.role == 'ADMIN')) else 'Distributor',
    }
    return render(request, 'dashboard/distributor_profile.html', context)


# 13. Customer Management: Add Customer View
@login_required
def add_customer_view(request):
    initialize_default_users()
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.save_customer(created_by=request.user)
            messages.success(request, f"🎉 Customer '{customer.name}' ({customer.phone}) added successfully to database!")
            return redirect('customer_list')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = CustomerForm()

    context = {
        'form': form,
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/add_customer.html', context)


# 13.1 Interactive Customer Registration Frontend View (Connected to API)
def customer_register_frontend_view(request):
    initialize_default_users()
    distributors = User.objects.filter(profile__role='DISTRIBUTOR').select_related('profile')
    current_distributor = None
    if request.user.is_authenticated:
        if hasattr(request.user, 'profile') and request.user.profile.role == 'DISTRIBUTOR':
            current_distributor = request.user
    if not current_distributor:
        current_distributor = distributors.first()

    is_admin = request.user.is_authenticated and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'))

    context = {
        'distributors': distributors,
        'current_distributor': current_distributor,
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/register_customer.html', context)



# 14. Customer Management: Customer List View
@login_required
def customer_list_view(request):
    initialize_default_users()
    query = request.GET.get('q', '').strip()
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    
    customers = Customer.objects.all()
    if not is_admin:
        customers = customers.filter(Q(created_by=request.user) | Q(created_by__isnull=True))

    if query:
        customers = customers.filter(
            Q(name__icontains=query) |
            Q(phone__icontains=query) |
            Q(email__icontains=query) |
            Q(city__icontains=query) |
            Q(gstin__icontains=query)
        )

    context = {
        'customers': customers,
        'query': query,
        'total_count': customers.count(),
        'gst_count': customers.filter(gstin__isnull=False).exclude(gstin='').count(),
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/customer_list.html', context)


# 15. Edit Customer View
@login_required
def edit_customer_view(request, customer_id):
    initialize_default_users()
    customer = get_object_or_404(Customer, pk=customer_id)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    if not is_admin and customer.created_by and customer.created_by != request.user:
        messages.error(request, "Access denied: You do not have permission to edit this customer profile.")
        return redirect('customer_list')

    if request.method == 'POST':
        form = CustomerForm(request.POST)
        if form.is_valid():
            customer = form.update_customer(customer)
            messages.success(request, f"🎉 Customer '{customer.name}' updated successfully!")
            return redirect('customer_list')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = CustomerForm(initial={
            'name': customer.name,
            'email': customer.email or '',
            'phone': customer.phone,
            'address': customer.address or '',
            'city': customer.city or '',
            'gstin': customer.gstin or '',
        })

    context = {
        'form': form,
        'customer': customer,
        'is_edit': True,
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/add_customer.html', context)


# 16. Delete Customer View
@login_required
def delete_customer_view(request, customer_id):
    initialize_default_users()
    customer = get_object_or_404(Customer, pk=customer_id)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    if not is_admin and customer.created_by and customer.created_by != request.user:
        messages.error(request, "Access denied: You do not have permission to delete this customer profile.")
        return redirect('customer_list')
    name = customer.name
    customer.delete()
    messages.success(request, f"🗑️ Customer '{name}' deleted successfully.")
    return redirect('customer_list')


# 17. Custom CSRF Failure Handler
def csrf_failure_view(request, reason=""):
    """User-friendly CSRF failure view that automatically redirects or alerts."""
    messages.warning(request, "⚠️ Session security token updated. Please re-submit your action.")
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    return redirect('portal_select')




# 18. Product Management: List Products
@login_required
def product_list_view(request):
    initialize_default_users()
    query = request.GET.get('q', '').strip()
    category_filter = request.GET.get('category', '').strip()
    
    products = Product.objects.all().order_by('-id')
    
    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(sku__icontains=query) |
            Q(hsn_code__icontains=query)
        )
    
    if category_filter:
        products = products.filter(category__iexact=category_filter)
        
    categories = Product.objects.values_list('category', flat=True).distinct()

    # Pagination: 10 products per page
    paginator = Paginator(products, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'products': page_obj,
        'query': query,
        'category_filter': category_filter,
        'categories': [c for c in categories if c],
        'total_count': products.count(),
        'role': 'Admin' if (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')) else 'Distributor',
    }
    return render(request, 'billing/product_list.html', context)


# 18.1 Interactive Product Management Workspace (API & Modals driven)
def product_manage_frontend_view(request):
    initialize_default_users()
    products = Product.objects.all().order_by('-id')
    categories = Product.objects.values_list('category', flat=True).distinct()
    is_admin = request.user.is_authenticated and (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'))

    total_stock = products.aggregate(Sum('stock'))['stock__sum'] or 0
    total_val = sum(float(p.price) * p.stock for p in products)
    low_stock_count = products.filter(stock__lte=15, stock__gt=0).count()
    out_of_stock_count = products.filter(stock=0).count()

    context = {
        'products': products,
        'categories': [c for c in categories if c],
        'total_count': products.count(),
        'total_stock': total_stock,
        'total_catalog_val': round(total_val, 2),
        'low_stock_count': low_stock_count,
        'out_of_stock_count': out_of_stock_count,
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/manage_products.html', context)


# 19. Product Management: Add Product

@login_required
def add_product_view(request):
    initialize_default_users()
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save(commit=False)
            product.created_by = request.user
            product.save()
            messages.success(request, f"🎉 Product '{product.name}' added successfully to inventory!")
            return redirect('product_list')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = ProductForm()

    context = {
        'form': form,
        'role': 'Admin' if (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')) else 'Distributor',
    }
    return render(request, 'billing/add_product.html', context)


# 20. Product Management: Edit Product
@login_required
def edit_product_view(request, product_id):
    initialize_default_users()
    product = get_object_or_404(Product, pk=product_id)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    if not is_admin and product.created_by and product.created_by != request.user:
        messages.error(request, "Access denied: You do not have permission to edit this product.")
        return redirect('product_list')

    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            product = form.save()
            messages.success(request, f"🎉 Product '{product.name}' updated successfully!")
            return redirect('product_list')
        else:
            for field, errors in form.errors.items():
                for err in errors:
                    messages.error(request, f"{field.replace('_', ' ').title()}: {err}")
    else:
        form = ProductForm(instance=product)

    context = {
        'form': form,
        'product': product,
        'is_edit': True,
        'role': 'Admin' if is_admin else 'Distributor',
    }
    return render(request, 'billing/add_product.html', context)


# 21. Product Management: Delete Product
@login_required
def delete_product_view(request, product_id):
    initialize_default_users()
    product = get_object_or_404(Product, pk=product_id)
    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')
    if not is_admin and product.created_by and product.created_by != request.user:
        messages.error(request, "Access denied: You do not have permission to delete this product.")
        return redirect('product_list')
    name = product.name
    product.delete()
    messages.success(request, f"🗑️ Product '{name}' deleted successfully from inventory.")
    return redirect('product_list')


from django.http import HttpResponse
from django.template.loader import get_template
try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

try:
    import weasyprint
except ImportError:
    weasyprint = None

import qrcode
import base64
from io import BytesIO

@login_required
def generate_invoice_pdf_view(request, invoice_id):
    """
    Exports a certified Tax Invoice as a PDF with embedded verified QR code
    using xhtml2pdf or ReportLab.
    Supports ?engine=xhtml2pdf|reportlab|auto (defaults to auto).
    Provides structured error responses for AJAX/fetch requests and friendly alerts.
    """
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest' or request.GET.get('format') == 'json'
    engine = request.GET.get('engine', 'auto')
    qr_mode = request.GET.get('qr_mode', request.GET.get('mode', 'text')).strip().lower()
    qr_engine = request.GET.get('qr_engine', 'auto').strip().lower()

    try:
        # Fetch corresponding invoice record and related customer entry from DB
        invoice = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').get(id=invoice_id)
    except Invoice.DoesNotExist:
        if is_ajax:
            return JsonResponse({'status': 'error', 'success': False, 'error': f'Invoice #{invoice_id} not found in database.'}, status=404)
        messages.error(request, f"Invoice #{invoice_id} not found.")
        return redirect('invoice_list')

    from .pdf_generator import generate_invoice_pdf_bytes, pisa, REPORTLAB_AVAILABLE
    if not pisa and not REPORTLAB_AVAILABLE and not weasyprint:
        if is_ajax:
            return JsonResponse({'status': 'error', 'success': False, 'error': 'No PDF generation library (xhtml2pdf / ReportLab) is installed.'}, status=500)
        messages.error(request, "PDF generation library (xhtml2pdf or ReportLab) is not installed.")
        return redirect('invoice_detail', invoice_id=invoice_id)

    try:
        pdf_bytes = generate_invoice_pdf_bytes(invoice, engine=engine, qr_mode=qr_mode, qr_engine=qr_engine)
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
        return response
    except Exception as exc:
        if is_ajax:
            return JsonResponse({'status': 'error', 'success': False, 'error': f'Failed to generate invoice PDF: {str(exc)}'}, status=500)
        messages.error(request, f"Error generating PDF: {str(exc)}")
        return redirect('invoice_detail', invoice_id=invoice_id)
    
@login_required
def invoice_list_view(request):
    """
    Fetch all invoice records from the database and display them in a
    responsive Bootstrap-styled table with filters, KPI statistics, and actions.
    """
    initialize_default_users()
    query = request.GET.get('q', '').strip()
    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()
    status_filter = request.GET.get('status', '').strip()
    per_page_param = request.GET.get('per_page', '10').strip().lower()
    
    # Fetch all invoice records from database with related customer, distributor, and line items
    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN') or request.GET.get('all') in ('1', 'true'):
        invoices = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').all().order_by('-created_at')
        role = 'Admin'
    else:
        invoices = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').filter(distributor=request.user).order_by('-created_at')
        role = 'Distributor'
        
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )
    date_range_error = None
    if start_date and end_date:
        try:
            d_start = datetime.strptime(start_date, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date, '%Y-%m-%d').date()
            if d_start > d_end:
                date_range_error = f"Invalid date range: From Date ({start_date}) cannot be after To Date ({end_date})."
                messages.error(request, date_range_error)
            else:
                invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            date_range_error = "Invalid date format. Please use YYYY-MM-DD."
            messages.error(request, date_range_error)
    elif start_date and not end_date:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            invoices = invoices.filter(created_at__date__gte=start_date)
        except Exception:
            pass
    elif end_date and not start_date:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            invoices = invoices.filter(created_at__date__lte=end_date)
        except Exception:
            pass
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    # Compute metrics for the selected range
    total_invoices_count = invoices.count()
    total_amount_collected = invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_amount_billed = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_pending_amount = invoices.filter(payment_status='PENDING').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
        
    if per_page_param in ('all', '0', 'none'):
        page_obj = invoices
        is_paginated = False
    else:
        try:
            limit = int(per_page_param)
            if limit <= 0:
                limit = 10
        except ValueError:
            limit = 10
        paginator = Paginator(invoices, limit)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        is_paginated = page_obj.has_other_pages()
    
    has_filters = bool(query or start_date or end_date or status_filter)
    
    context = {
        'invoices': page_obj,
        'is_paginated': is_paginated,
        'per_page': per_page_param,
        'total_invoices_count': total_invoices_count,
        'total_amount_collected': total_amount_collected,
        'total_amount_billed': total_amount_billed,
        'total_pending_amount': total_pending_amount,
        'query': query,
        'start_date': start_date,
        'end_date': end_date,
        'status_filter': status_filter,
        'has_filters': has_filters,
        'date_range_error': date_range_error,
        'role': role,
        'bootstrap_table_mode': True,
    }
    return render(request, 'billing/invoice_list.html', context)


@login_required
def invoice_bootstrap_table_view(request):
    """
    Dedicated view to fetch all invoice records from the database
    and display them in a modern Bootstrap-styled responsive table.
    """
    initialize_default_users()
    query = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '').strip()
    per_page_param = request.GET.get('per_page', 'all').strip().lower()

    if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN') or request.GET.get('all') in ('1', 'true'):
        invoices = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').all().order_by('-created_at')
        role = 'Admin'
    else:
        invoices = Invoice.objects.select_related('customer', 'distributor').prefetch_related('items').filter(distributor=request.user).order_by('-created_at')
        role = 'Distributor'

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    total_invoices_count = invoices.count()
    total_amount_collected = invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_amount_billed = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_pending_amount = invoices.filter(payment_status='PENDING').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    if per_page_param in ('all', '0', 'none'):
        page_obj = invoices
        is_paginated = False
    else:
        try:
            limit = int(per_page_param)
            if limit <= 0:
                limit = 15
        except ValueError:
            limit = 15
        paginator = Paginator(invoices, limit)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)
        is_paginated = page_obj.has_other_pages()

    context = {
        'invoices': page_obj,
        'is_paginated': is_paginated,
        'per_page': per_page_param,
        'total_invoices_count': total_invoices_count,
        'total_amount_collected': total_amount_collected,
        'total_amount_billed': total_amount_billed,
        'total_pending_amount': total_pending_amount,
        'query': query,
        'status_filter': status_filter,
        'has_filters': bool(query or status_filter),
        'role': role,
        'bootstrap_table_mode': True,
    }
    return render(request, 'billing/invoice_list.html', context)


# =========================================================================
# DEDICATED INVOICE REPORT GENERATION & DATE RANGE FILTERING ENGINE
# =========================================================================

@login_required
def invoice_report_view(request):
    """
    Dedicated Report Generation View for filtering invoices by date range,
    payment status, payment method, distributor, customer query, and amount range.
    Includes aggregated metrics and export to CSV/print.
    """
    initialize_default_users()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_method_filter = request.GET.get('payment_method', '').strip()
    query = request.GET.get('q', '').strip()
    distributor_id = request.GET.get('distributor_id', '').strip()
    min_amount = request.GET.get('min_amount', '').strip()
    max_amount = request.GET.get('max_amount', '').strip()
    preset = request.GET.get('preset', '').strip()

    # Automatic preset date calculation if preset provided and dates omitted
    today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
    if preset and not start_date_str and not end_date_str:
        if preset == 'today':
            start_date_str = today.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date_str = yesterday.strftime('%Y-%m-%d')
            end_date_str = yesterday.strftime('%Y-%m-%d')
        elif preset == '7days':
            start_date_str = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == '30days':
            start_date_str = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'this_month':
            start_date_str = today.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'last_month':
            first_this_month = today.replace(day=1)
            last_day_last_month = first_this_month - timedelta(days=1)
            start_date_str = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = last_day_last_month.strftime('%Y-%m-%d')
        elif preset == 'this_year':
            start_date_str = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')

    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')

    if is_admin:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile', 'customer').prefetch_related('items').all()
        role = 'Admin'
    else:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile', 'customer').prefetch_related('items').filter(distributor=request.user)
        role = 'Distributor'

    # Filter by Distributor (Admin only)
    if is_admin and distributor_id:
        invoices = invoices.filter(distributor_id=distributor_id)

    # Filter by Date Range
    date_range_error = None
    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if d_start > d_end:
                date_range_error = f"Invalid date range: From Date ({start_date_str}) cannot be after To Date ({end_date_str})."
                messages.error(request, date_range_error)
            else:
                invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            date_range_error = "Invalid date format provided. Please use YYYY-MM-DD."
            messages.error(request, date_range_error)
    elif start_date_str and not end_date_str:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__gte=start_date_str)
        except (ValueError, TypeError):
            pass
    elif end_date_str and not start_date_str:
        messages.warning(request, "Please provide both From Date and To Date for complete date filtering.")
        try:
            datetime.strptime(end_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__lte=end_date_str)
        except (ValueError, TypeError):
            pass

    # Filter by Payment Status
    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    # Filter by Payment Method
    if payment_method_filter:
        invoices = invoices.filter(payment_method__iexact=payment_method_filter)

    # Min and Max Amount
    if min_amount:
        try:
            invoices = invoices.filter(grand_total__gte=Decimal(min_amount))
        except (InvalidOperation, ValueError):
            pass

    if max_amount:
        try:
            invoices = invoices.filter(grand_total__lte=Decimal(max_amount))
        except (InvalidOperation, ValueError):
            pass

    # Search Query
    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    # Calculate Aggregated Financial Metrics
    total_invoices_count = invoices.count()
    total_billed_val = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_tax_collected = invoices.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
    total_subtotal = invoices.aggregate(Sum('subtotal'))['subtotal__sum'] or Decimal('0.00')
    total_discount = invoices.aggregate(Sum('discount'))['discount__sum'] or Decimal('0.00')

    paid_qs = invoices.filter(payment_status='PAID')
    total_paid_val = paid_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    pending_qs = invoices.filter(payment_status='PENDING')
    total_pending_val = pending_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    failed_qs = invoices.filter(payment_status='FAILED')
    total_failed_val = failed_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    avg_ticket_size = round(float(total_billed_val) / total_invoices_count, 2) if total_invoices_count > 0 else 0.0

    distributors = User.objects.filter(profile__role='DISTRIBUTOR').select_related('profile') if is_admin else []

    # Order before pagination
    invoices = invoices.order_by('-created_at')

    # Pagination: 25 items per page
    paginator = Paginator(invoices, 25)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    available_payment_methods = ['UPI QR Code', 'Cash', 'Credit Card', 'Debit Card', 'Net Banking']
    has_filters = bool(start_date_str or end_date_str or status_filter or payment_method_filter or query or distributor_id or min_amount or max_amount)

    context = {
        'invoices': page_obj,
        'all_filtered_invoices': invoices[:200],  # for printable audit record
        'total_invoices_count': total_invoices_count,
        'total_amount_collected': total_paid_val,
        'total_billed_val': total_billed_val,
        'total_paid_val': total_paid_val,
        'total_pending_val': total_pending_val,
        'total_failed_val': total_failed_val,
        'total_tax_collected': total_tax_collected,
        'total_subtotal': total_subtotal,
        'total_discount': total_discount,
        'avg_ticket_size': avg_ticket_size,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'status_filter': status_filter,
        'payment_method_filter': payment_method_filter,
        'query': query,
        'distributor_id': distributor_id,
        'min_amount': min_amount,
        'max_amount': max_amount,
        'preset': preset,
        'distributors': distributors,
        'available_payment_methods': available_payment_methods,
        'has_filters': has_filters,
        'date_range_error': date_range_error,
        'role': role,
        'is_admin': is_admin,
    }
    return render(request, 'billing/invoice_reports.html', context)


@login_required
def invoice_report_export_csv_view(request):
    """
    Exports filtered invoice reports to CSV based on the exact date range,
    payment status, distributor, payment method, amount, and search filters.
    """
    initialize_default_users()
    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_method_filter = request.GET.get('payment_method', '').strip()
    query = request.GET.get('q', '').strip()
    distributor_id = request.GET.get('distributor_id', '').strip()
    min_amount = request.GET.get('min_amount', '').strip()
    max_amount = request.GET.get('max_amount', '').strip()
    preset = request.GET.get('preset', '').strip()

    # Preset logic
    today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
    if preset and not start_date_str and not end_date_str:
        if preset == 'today':
            start_date_str = today.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date_str = yesterday.strftime('%Y-%m-%d')
            end_date_str = yesterday.strftime('%Y-%m-%d')
        elif preset == '7days':
            start_date_str = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == '30days':
            start_date_str = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'this_month':
            start_date_str = today.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'last_month':
            first_this_month = today.replace(day=1)
            last_day_last_month = first_this_month - timedelta(days=1)
            start_date_str = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = last_day_last_month.strftime('%Y-%m-%d')
        elif preset == 'this_year':
            start_date_str = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')

    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')

    if is_admin:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile').prefetch_related('items').all()
    else:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile').prefetch_related('items').filter(distributor=request.user)

    if is_admin and distributor_id:
        invoices = invoices.filter(distributor_id=distributor_id)

    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if d_start > d_end:
                messages.error(request, f"Cannot export CSV: Invalid date range (From Date {start_date_str} is after To Date {end_date_str}).")
                return redirect('invoice_reports')
            invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format for CSV export.")
            return redirect('invoice_reports')
    elif start_date_str:
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__gte=start_date_str)
        except (ValueError, TypeError):
            pass
    elif end_date_str:
        try:
            datetime.strptime(end_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__lte=end_date_str)
        except (ValueError, TypeError):
            pass

    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    if payment_method_filter:
        invoices = invoices.filter(payment_method__iexact=payment_method_filter)

    if min_amount:
        try:
            invoices = invoices.filter(grand_total__gte=Decimal(min_amount))
        except (InvalidOperation, ValueError):
            pass

    if max_amount:
        try:
            invoices = invoices.filter(grand_total__lte=Decimal(max_amount))
        except (InvalidOperation, ValueError):
            pass

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    invoices = invoices.order_by('-created_at')

    # Filename
    date_suffix = ""
    if start_date_str and end_date_str:
        date_suffix = f"_{start_date_str}_to_{end_date_str}"
    elif start_date_str:
        date_suffix = f"_from_{start_date_str}"
    elif end_date_str:
        date_suffix = f"_until_{end_date_str}"
    else:
        date_suffix = f"_{timezone.now().strftime('%Y%m%d')}"

    filename = f"Invoice_Report{date_suffix}.csv"

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    writer = csv.writer(response)
    writer.writerow([
        'Invoice Number',
        'Date',
        'Time',
        'Distributor',
        'Customer Name',
        'Customer Phone',
        'Payment Method',
        'Taxable Subtotal (INR)',
        'GST Tax Amount (INR)',
        'Discount (INR)',
        'Grand Total (INR)',
        'Payment Status',
        'Item Count'
    ])

    total_subtotal_sum = Decimal('0.00')
    total_tax_sum = Decimal('0.00')
    total_discount_sum = Decimal('0.00')
    total_grand_sum = Decimal('0.00')

    for inv in invoices:
        dist_name = inv.distributor.username if inv.distributor else 'Direct / Admin'
        created_time = inv.created_at.strftime('%H:%M:%S') if inv.created_at else ''
        created_date = inv.created_at.strftime('%Y-%m-%d') if inv.created_at else ''
        item_count = inv.items.count()

        total_subtotal_sum += inv.subtotal
        total_tax_sum += inv.tax_amount
        total_discount_sum += inv.discount
        total_grand_sum += inv.grand_total

        writer.writerow([
            inv.invoice_number,
            created_date,
            created_time,
            dist_name,
            inv.customer_name,
            inv.customer_phone,
            inv.payment_method,
            f"{inv.subtotal:.2f}",
            f"{inv.tax_amount:.2f}",
            f"{inv.discount:.2f}",
            f"{inv.grand_total:.2f}",
            inv.payment_status,
            item_count
        ])

    # Summary Row
    writer.writerow([])
    writer.writerow([
        'TOTALS / SUMMARY',
        f'{invoices.count()} invoices',
        '',
        '',
        '',
        '',
        '',
        f"{total_subtotal_sum:.2f}",
        f"{total_tax_sum:.2f}",
        f"{total_discount_sum:.2f}",
        f"{total_grand_sum:.2f}",
        '',
        ''
    ])

    return response


@login_required
def invoice_report_download_pdf_view(request):
    """
    Generates and downloads an official Invoice Report as a PDF using xhtml2pdf.
    Filters invoices by date range, payment status, distributor, payment method, and amount.
    Includes selected range summary KPIs: Total Invoices and Amount Collected.
    """
    initialize_default_users()
    if not pisa:
        messages.error(request, "PDF generation library (xhtml2pdf) is not installed.")
        return redirect('invoice_reports')

    start_date_str = request.GET.get('start_date', '').strip()
    end_date_str = request.GET.get('end_date', '').strip()
    status_filter = request.GET.get('status', '').strip()
    payment_method_filter = request.GET.get('payment_method', '').strip()
    query = request.GET.get('q', '').strip()
    distributor_id = request.GET.get('distributor_id', '').strip()
    min_amount = request.GET.get('min_amount', '').strip()
    max_amount = request.GET.get('max_amount', '').strip()
    preset = request.GET.get('preset', '').strip()

    # Preset logic
    today = timezone.localdate() if hasattr(timezone, 'localdate') else date.today()
    if preset and not start_date_str and not end_date_str:
        if preset == 'today':
            start_date_str = today.strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'yesterday':
            yesterday = today - timedelta(days=1)
            start_date_str = yesterday.strftime('%Y-%m-%d')
            end_date_str = yesterday.strftime('%Y-%m-%d')
        elif preset == '7days':
            start_date_str = (today - timedelta(days=6)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == '30days':
            start_date_str = (today - timedelta(days=29)).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'this_month':
            start_date_str = today.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')
        elif preset == 'last_month':
            first_this_month = today.replace(day=1)
            last_day_last_month = first_this_month - timedelta(days=1)
            start_date_str = last_day_last_month.replace(day=1).strftime('%Y-%m-%d')
            end_date_str = last_day_last_month.strftime('%Y-%m-%d')
        elif preset == 'this_year':
            start_date_str = today.replace(month=1, day=1).strftime('%Y-%m-%d')
            end_date_str = today.strftime('%Y-%m-%d')

    is_admin = request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')

    if is_admin:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile').prefetch_related('items').all()
        role = 'Admin'
    else:
        invoices = Invoice.objects.select_related('distributor', 'distributor__profile').prefetch_related('items').filter(distributor=request.user)
        role = 'Distributor'

    if is_admin and distributor_id:
        invoices = invoices.filter(distributor_id=distributor_id)

    if start_date_str and end_date_str:
        try:
            d_start = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            d_end = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            if d_start > d_end:
                messages.error(request, f"Cannot generate PDF: Invalid date range (From Date {start_date_str} is after To Date {end_date_str}).")
                return redirect('invoice_reports')
            invoices = invoices.filter(created_at__date__gte=d_start, created_at__date__lte=d_end)
        except (ValueError, TypeError):
            messages.error(request, "Invalid date format for PDF report.")
            return redirect('invoice_reports')
    elif start_date_str:
        try:
            datetime.strptime(start_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__gte=start_date_str)
        except (ValueError, TypeError):
            pass
    elif end_date_str:
        try:
            datetime.strptime(end_date_str, '%Y-%m-%d')
            invoices = invoices.filter(created_at__date__lte=end_date_str)
        except (ValueError, TypeError):
            pass

    if status_filter:
        invoices = invoices.filter(payment_status=status_filter)

    if payment_method_filter:
        invoices = invoices.filter(payment_method__iexact=payment_method_filter)

    if min_amount:
        try:
            invoices = invoices.filter(grand_total__gte=Decimal(min_amount))
        except (InvalidOperation, ValueError):
            pass

    if max_amount:
        try:
            invoices = invoices.filter(grand_total__lte=Decimal(max_amount))
        except (InvalidOperation, ValueError):
            pass

    if query:
        invoices = invoices.filter(
            Q(invoice_number__icontains=query) |
            Q(customer_name__icontains=query) |
            Q(customer_phone__icontains=query)
        )

    invoices = invoices.order_by('-created_at')

    # Aggregates for PDF report
    total_invoices_count = invoices.count()
    total_billed_val = invoices.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_tax_collected = invoices.aggregate(Sum('tax_amount'))['tax_amount__sum'] or Decimal('0.00')
    total_subtotal = invoices.aggregate(Sum('subtotal'))['subtotal__sum'] or Decimal('0.00')
    total_discount = invoices.aggregate(Sum('discount'))['discount__sum'] or Decimal('0.00')

    paid_qs = invoices.filter(payment_status='PAID')
    total_amount_collected = paid_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    pending_qs = invoices.filter(payment_status='PENDING')
    total_pending_val = pending_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    now = timezone.now()
    generated_at = now.strftime('%Y-%m-%d %H:%M:%S')

    context = {
        'invoices': invoices[:300],  # safety ceiling for single PDF render
        'total_invoices_count': total_invoices_count,
        'total_amount_collected': total_amount_collected,
        'total_billed_val': total_billed_val,
        'total_pending_val': total_pending_val,
        'total_tax_collected': total_tax_collected,
        'total_subtotal': total_subtotal,
        'total_discount': total_discount,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'status_filter': status_filter,
        'payment_method_filter': payment_method_filter,
        'role': role,
        'is_admin': is_admin,
        'generated_at': generated_at,
        'generated_by': request.user.get_full_name() or request.user.username,
    }

    template = get_template('billing/invoice_report_pdf.html')
    html = template.render(context)

    # Date suffix for download filename
    date_suffix = ""
    if start_date_str and end_date_str:
        date_suffix = f"_{start_date_str}_to_{end_date_str}"
    elif start_date_str:
        date_suffix = f"_from_{start_date_str}"
    elif end_date_str:
        date_suffix = f"_until_{end_date_str}"
    else:
        date_suffix = f"_{now.strftime('%Y%m%d')}"

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Invoice_Report{date_suffix}.pdf"'

    pisa_status = pisa.CreatePDF(html, dest=response)
    if pisa_status.err:
        return HttpResponse('Error generating PDF report with xhtml2pdf', status=500)
    return response


from django.views.decorators.http import require_http_methods
from django.contrib.auth import authenticate

@csrf_exempt
@require_http_methods(["POST"])
def api_login_admin(request):
    """
    API endpoint for Administrator Login.
    Accepts JSON: {"username": "admin", "password": "password"} or {"identity": "...", "password": "..."}
    Allows authentication by username or email.
    Verifies that the user possesses Administrator authorization.
    """
    try:
        initialize_default_users()
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)
        else:
            data = request.POST.dict()

        username = (data.get('username') or data.get('identity') or data.get('email') or '').strip()
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({'success': False, 'message': 'Both username/email and password are required.'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'success': False, 'message': 'Invalid credentials. Please verify your Admin username/email and password.'}, status=401)

        is_admin = user.is_superuser or (hasattr(user, 'profile') and user.profile.role == 'ADMIN')
        if not is_admin:
            return JsonResponse({
                'success': False,
                'message': 'Access Denied: This account is not authorized as an Administrator. Please use Distributor Login.'
            }, status=403)

        if not user.is_active:
            return JsonResponse({'success': False, 'message': 'Account is inactive. Please contact support.'}, status=403)

        auth_login(request, user)
        # Session configuration based on Remember Me
        remember = bool(data.get('remember_me', False))
        if remember:
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            request.session.set_expiry(0)  # Browser close

        profile, _ = UserProfile.objects.get_or_create(user=user)

        return JsonResponse({
            'success': True,
            'message': f'Welcome back, Administrator {user.get_full_name() or user.username}!',
            'redirect_url': '/admin/dashboard/',
            'session_key': request.session.session_key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'role': profile.role,
                'business_name': profile.business_name or 'Admin HQ',
                'phone': profile.phone or ''
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login_distributor(request):
    """
    API endpoint for Distributor Login.
    Accepts JSON: {"username": "distributor", "password": "password"} or {"identity": "...", "password": "..."}
    Allows authentication by username or email.
    """
    try:
        initialize_default_users()
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)
        else:
            data = request.POST.dict()

        username = (data.get('username') or data.get('identity') or data.get('email') or '').strip()
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({'success': False, 'message': 'Both username/email and password are required.'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'success': False, 'message': 'Invalid credentials. Please verify your distributor username/email and password.'}, status=401)

        if not user.is_active:
            return JsonResponse({'success': False, 'message': 'Account is inactive. Please contact support.'}, status=403)

        auth_login(request, user)
        # Session configuration based on Remember Me
        remember = bool(data.get('remember_me', False))
        if remember:
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            request.session.set_expiry(0)  # Browser close

        profile, _ = UserProfile.objects.get_or_create(user=user)

        redirect_url = '/admin/dashboard/' if (user.is_superuser or profile.role == 'ADMIN') else '/distributor/dashboard/'

        return JsonResponse({
            'success': True,
            'message': f'Welcome back, Distributor {user.get_full_name() or user.username}!',
            'redirect_url': redirect_url,
            'session_key': request.session.session_key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'role': profile.role,
                'business_name': profile.business_name or 'Distribution Agency',
                'phone': profile.phone or '',
                'upi_id': profile.upi_id or 'merchant@upi'
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_login_general(request):
    """
    General API endpoint for User Login (auto-detects role and redirects accordingly).
    """
    try:
        initialize_default_users()
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)
        else:
            data = request.POST.dict()

        username = (data.get('username') or data.get('identity') or data.get('email') or '').strip()
        password = data.get('password', '')

        if not username or not password:
            return JsonResponse({'success': False, 'message': 'Both username/email and password are required.'}, status=400)

        user = authenticate(request, username=username, password=password)
        if user is None:
            return JsonResponse({'success': False, 'message': 'Invalid credentials. Please verify your username/email and password.'}, status=401)

        if not user.is_active:
            return JsonResponse({'success': False, 'message': 'Account is inactive.'}, status=403)

        auth_login(request, user)
        # Session configuration based on Remember Me
        remember = bool(data.get('remember_me', False))
        if remember:
            request.session.set_expiry(60 * 60 * 24 * 30)  # 30 days
        else:
            request.session.set_expiry(0)  # Browser close

        profile, _ = UserProfile.objects.get_or_create(user=user)
        is_admin = user.is_superuser or profile.role == 'ADMIN'
        redirect_url = '/admin/dashboard/' if is_admin else '/distributor/dashboard/'

        return JsonResponse({
            'success': True,
            'message': f'Welcome back, {user.get_full_name() or user.username}!',
            'redirect_url': redirect_url,
            'session_key': request.session.session_key,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name() or user.username,
                'role': profile.role,
                'business_name': profile.business_name or '',
                'phone': profile.phone or '',
                'upi_id': getattr(profile, 'upi_id', '')
            }
        }, status=200)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["GET"])
def api_session_status(request):
    """
    Session verification endpoint. Returns current authenticated user session details,
    role, permissions, and session expiry age.
    """
    if request.user.is_authenticated:
        role = 'ADMIN' if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN') else 'DISTRIBUTOR'
        profile = getattr(request.user, 'profile', None)
        return JsonResponse({
            'authenticated': True,
            'session_key': request.session.session_key,
            'session_expiry_age': request.session.get_expiry_age(),
            'user': {
                'id': request.user.id,
                'username': request.user.username,
                'email': request.user.email,
                'full_name': request.user.get_full_name() or request.user.username,
                'role': role,
                'business_name': profile.business_name if profile else '',
                'phone': profile.phone if profile else '',
                'upi_id': getattr(profile, 'upi_id', '') if profile else ''
            }
        }, status=200)
    else:
        return JsonResponse({
            'authenticated': False,
            'message': 'No active authenticated session.'
        }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def api_logout(request):
    """
    API endpoint to securely terminate and flush the current session.
    """
    username = request.user.username if request.user.is_authenticated else ''
    auth_logout(request)
    request.session.flush()
    return JsonResponse({
        'success': True,
        'message': f'Session for {username or "user"} successfully terminated.',
        'redirect_url': '/'
    }, status=200)


@csrf_exempt
@require_http_methods(["POST"])
def api_register_admin(request):
    try:
        data = json.loads(request.body)
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        
        if not username or not email or not password:
            return JsonResponse({'success': False, 'message': 'Username, email, and password are required.'}, status=400)
            
        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'message': 'Username already exists.'}, status=400)
            
        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
            first_name=data.get('first_name', '').strip(),
            last_name=data.get('last_name', '').strip()
        )
        
        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'ADMIN'
        profile.business_name = data.get('business_name', 'Admin HQ').strip()
        profile.phone = data.get('phone', '').strip()
        profile.save()
        
        return JsonResponse({'success': True, 'message': f'Admin user {username} created successfully.'}, status=201)
    except json.JSONDecodeError:
        return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_register_distributor(request):
    """
    API endpoint to register a new Distributor account.
    """
    try:
        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON data.'}, status=400)
        else:
            data = request.POST.dict()

        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        full_name = data.get('full_name', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        business_name = data.get('business_name', '').strip()
        phone = data.get('phone', '').strip()
        upi_id = data.get('upi_id', 'merchant@upi').strip()

        if full_name and not (first_name or last_name):
            parts = full_name.split(' ', 1)
            first_name = parts[0]
            last_name = parts[1] if len(parts) > 1 else ''

        if not username or not email or not password:
            return JsonResponse({'success': False, 'message': 'Username, email, and password are required.'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'success': False, 'message': 'Username already exists.'}, status=400)

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.role = 'DISTRIBUTOR'
        profile.business_name = business_name or f"{first_name or username}'s Distribution"
        profile.phone = phone
        profile.upi_id = upi_id
        profile.save()

        return JsonResponse({
            'success': True,
            'message': f'Distributor {username} registered successfully.',
            'distributor': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.get_full_name(),
                'business_name': profile.business_name,
                'phone': profile.phone,
                'upi_id': profile.upi_id,
                'role': profile.role
            }
        }, status=201)
    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def api_register_customer(request):
    """
    API endpoint for Distributors to register new retail/wholesale customers.
    Accepts JSON or form-data:
    - name: str (required)
    - phone: str (required)
    - email: str (optional)
    - address: str (optional)
    - city: str (optional)
    - gstin: str (optional)
    - distributor_username / distributor_id: str/int (optional, links customer to specific distributor)
    """
    try:
        initialize_default_users()

        if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
            try:
                data = json.loads(request.body)
            except json.JSONDecodeError:
                return JsonResponse({'success': False, 'message': 'Invalid JSON format in request body.'}, status=400)
        else:
            data = request.POST.dict()

        name = data.get('name', '').strip()
        phone = data.get('phone', '').strip()
        email = data.get('email', '').strip()
        address = data.get('address', '').strip()
        city = data.get('city', '').strip()
        gstin = data.get('gstin', '').strip()

        if not name:
            return JsonResponse({'success': False, 'message': 'Customer name is required.'}, status=400)
        if not phone:
            return JsonResponse({'success': False, 'message': 'Customer phone number is required.'}, status=400)

        # Associate with distributor
        distributor_user = None
        if request.user.is_authenticated:
            distributor_user = request.user
        else:
            dist_user_param = data.get('distributor_username') or data.get('distributor')
            dist_id_param = data.get('distributor_id')
            if dist_user_param:
                distributor_user = User.objects.filter(username=dist_user_param).first()
            elif dist_id_param:
                distributor_user = User.objects.filter(id=dist_id_param).first()

            if not distributor_user:
                # Default to system distributor if not specified
                distributor_user = User.objects.filter(profile__role='DISTRIBUTOR').first()

        # Check duplicate customer with same phone for this distributor
        existing = Customer.objects.filter(phone=phone, created_by=distributor_user).first()
        if existing:
            return JsonResponse({
                'success': False,
                'message': f"Customer with phone number '{phone}' already registered under distributor '{distributor_user.username if distributor_user else 'General'}'.",
                'customer': {
                    'id': existing.id,
                    'name': existing.name,
                    'phone': existing.phone,
                    'email': existing.email or '',
                    'address': existing.address or '',
                    'city': existing.city or '',
                    'gstin': existing.gstin or '',
                }
            }, status=409)

        customer = Customer.objects.create(
            name=name,
            phone=phone,
            email=email if email else None,
            address=address if address else None,
            city=city if city else None,
            gstin=gstin if gstin else None,
            created_by=distributor_user
        )

        dist_profile = getattr(distributor_user, 'profile', None) if distributor_user else None

        return JsonResponse({
            'success': True,
            'message': f"Customer '{customer.name}' registered successfully for Distributor.",
            'customer': {
                'id': customer.id,
                'name': customer.name,
                'phone': customer.phone,
                'email': customer.email or '',
                'address': customer.address or '',
                'city': customer.city or '',
                'gstin': customer.gstin or '',
                'distributor': distributor_user.username if distributor_user else None,
                'distributor_business_name': getattr(dist_profile, 'business_name', '') if dist_profile else '',
                'created_at': customer.created_at.strftime('%Y-%m-%d %H:%M:%S')
            }
        }, status=201)

    except Exception as e:
        return JsonResponse({'success': False, 'message': str(e)}, status=500)


def serialize_product(product):
    """Serialize Product model instance into clean JSON-compliant dictionary."""
    return {
        'id': product.id,
        'name': product.name,
        'sku': product.sku or '',
        'category': product.category,
        'price': float(product.price),
        'stock': product.stock,
        'gst_rate': float(product.gst_rate),
        'hsn_code': product.hsn_code or '',
        'unit': product.unit,
        'description': product.description or '',
        'created_by': product.created_by.username if product.created_by else None,
        'created_at': product.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'updated_at': product.updated_at.strftime('%Y-%m-%d %H:%M:%S')
    }


@csrf_exempt
def api_products(request):
    """
    Product API CRUD Endpoint:
    - GET: Read/List all products (with optional 'q' search and 'category' filtering)
    - POST: Create a new product
    """
    initialize_default_users()
    if request.method == 'GET':
        query = request.GET.get('q', '').strip()
        category = request.GET.get('category', '').strip()
        limit = int(request.GET.get('limit', 100))

        products = Product.objects.all().order_by('-id')
        if query:
            products = products.filter(
                Q(name__icontains=query) |
                Q(sku__icontains=query) |
                Q(hsn_code__icontains=query) |
                Q(category__icontains=query)
            )
        if category:
            products = products.filter(category__iexact=category)

        product_list = [serialize_product(p) for p in products[:limit]]
        return JsonResponse({
            'success': True,
            'count': len(product_list),
            'total_count': products.count(),
            'products': product_list
        }, status=200)

    elif request.method == 'POST':
        try:
            if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'success': False, 'message': 'Invalid JSON format in request body.'}, status=400)
            else:
                data = request.POST.dict()

            name = data.get('name', '').strip()
            price_raw = data.get('price')
            sku = data.get('sku', '').strip()
            category = data.get('category', '').strip() or 'General'
            stock_raw = data.get('stock', 100)
            gst_rate_raw = data.get('gst_rate', 18.00)
            hsn_code = data.get('hsn_code', '').strip()
            unit = data.get('unit', '').strip() or 'Pcs'
            description = data.get('description', '').strip()

            if not name:
                return JsonResponse({'success': False, 'message': 'Product name is required.'}, status=400)
            if price_raw is None or str(price_raw).strip() == '':
                return JsonResponse({'success': False, 'message': 'Product price is required.'}, status=400)

            try:
                price = Decimal(str(price_raw))
                if price <= 0:
                    return JsonResponse({'success': False, 'message': 'Product price must be greater than zero.'}, status=400)
            except (InvalidOperation, ValueError):
                return JsonResponse({'success': False, 'message': 'Invalid price format.'}, status=400)

            try:
                stock = int(stock_raw)
                if stock < 0:
                    return JsonResponse({'success': False, 'message': 'Stock cannot be negative.'}, status=400)
            except (ValueError, TypeError):
                stock = 100

            try:
                gst_rate = Decimal(str(gst_rate_raw))
            except (InvalidOperation, ValueError):
                gst_rate = Decimal('18.00')

            # Check SKU uniqueness if provided
            if sku:
                if Product.objects.filter(sku=sku).exists():
                    return JsonResponse({'success': False, 'message': f"Product with SKU '{sku}' already exists."}, status=409)

            creator = request.user if request.user.is_authenticated else User.objects.filter(is_superuser=True).first()

            product = Product.objects.create(
                name=name,
                sku=sku or None,
                category=category,
                price=price,
                stock=stock,
                gst_rate=gst_rate,
                hsn_code=hsn_code or None,
                unit=unit,
                description=description or None,
                created_by=creator
            )

            return JsonResponse({
                'success': True,
                'message': f"Product '{product.name}' created successfully.",
                'product': serialize_product(product)
            }, status=201)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': f"Method '{request.method}' not allowed."}, status=405)


@csrf_exempt
def api_product_detail(request, product_id):
    """
    Product Detail CRUD Endpoint:
    - GET: Read single product details
    - PUT / PATCH / POST: Update product details
    - DELETE: Delete product
    """
    initialize_default_users()
    product = Product.objects.filter(pk=product_id).first()
    if not product:
        return JsonResponse({'success': False, 'message': f"Product with ID #{product_id} not found."}, status=404)

    # 1. READ (GET)
    if request.method == 'GET':
        return JsonResponse({
            'success': True,
            'product': serialize_product(product)
        }, status=200)

    # 2. UPDATE (PUT / PATCH / POST)
    elif request.method in ['PUT', 'PATCH', 'POST']:
        try:
            if request.content_type == 'application/json' or (request.body and request.body.strip().startswith(b'{')):
                try:
                    data = json.loads(request.body)
                except json.JSONDecodeError:
                    return JsonResponse({'success': False, 'message': 'Invalid JSON format in request body.'}, status=400)
            else:
                data = request.POST.dict()

            if 'name' in data and data['name'].strip():
                product.name = data['name'].strip()
            if 'price' in data and str(data['price']).strip():
                try:
                    p = Decimal(str(data['price']))
                    if p > 0:
                        product.price = p
                    else:
                        return JsonResponse({'success': False, 'message': 'Price must be greater than zero.'}, status=400)
                except (InvalidOperation, ValueError):
                    return JsonResponse({'success': False, 'message': 'Invalid price format.'}, status=400)
            if 'stock' in data:
                try:
                    product.stock = max(0, int(data['stock']))
                except (ValueError, TypeError):
                    pass
            if 'gst_rate' in data:
                try:
                    product.gst_rate = Decimal(str(data['gst_rate']))
                except (InvalidOperation, ValueError):
                    pass
            if 'category' in data and data['category'].strip():
                product.category = data['category'].strip()
            if 'unit' in data and data['unit'].strip():
                product.unit = data['unit'].strip()
            if 'hsn_code' in data:
                product.hsn_code = data['hsn_code'].strip() or None
            if 'description' in data:
                product.description = data['description'].strip() or None

            if 'sku' in data:
                new_sku = data['sku'].strip() or None
                if new_sku and new_sku != product.sku:
                    if Product.objects.filter(sku=new_sku).exclude(pk=product.id).exists():
                        return JsonResponse({'success': False, 'message': f"SKU '{new_sku}' already in use by another product."}, status=409)
                product.sku = new_sku

            product.save()

            return JsonResponse({
                'success': True,
                'message': f"Product '{product.name}' updated successfully.",
                'product': serialize_product(product)
            }, status=200)

        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    # 3. DELETE (DELETE)
    elif request.method == 'DELETE':
        name = product.name
        pid = product.id
        product.delete()
        return JsonResponse({
            'success': True,
            'message': f"Product '{name}' (ID: #{pid}) deleted successfully."
        }, status=200)

    return JsonResponse({'success': False, 'message': f"Method '{request.method}' not allowed."}, status=405)


@csrf_exempt
@require_http_methods(["POST"])
def api_product_delete(request, product_id):
    """Convenience POST endpoint for deleting product from clients/tools without native DELETE method."""
    product = Product.objects.filter(pk=product_id).first()
    if not product:
        return JsonResponse({'success': False, 'message': f"Product with ID #{product_id} not found."}, status=404)
    name = product.name
    pid = product.id
    product.delete()
    return JsonResponse({
        'success': True,
        'message': f"Product '{name}' (ID: #{pid}) deleted successfully."
    }, status=200)


# =========================================================================
# QR CODE DECODER STUDIO & UPLOADED IMAGE API ENDPOINTS
# =========================================================================

from .qr_decoder import decode_qr_image, parse_qr_payload, extract_invoice_info


def enrich_result_with_invoice_data(result: dict) -> dict:
    """
    Checks if decoded QR result contains invoice information.
    If so, verifies against Django Invoice model in database.
    Attaches complete DB verification metadata, customer details, and invoice action URLs.
    """
    if not result or not result.get('success'):
        return result

    invoice_info = result.get('invoice_info')
    if not invoice_info:
        raw_text = result.get('data', '')
        fields = result.get('parsed', {})
        invoice_info = extract_invoice_info(raw_text, fields)
        if invoice_info:
            result['invoice_info'] = invoice_info

    if not invoice_info:
        return result

    inv_num = invoice_info.get('invoice_number')
    inv_id = invoice_info.get('invoice_id')
    db_inv = None

    try:
        from .models import Invoice
        if inv_num and inv_num not in ['N/A', 'None']:
            db_inv = Invoice.objects.filter(invoice_number__iexact=inv_num.strip()).first()
        if not db_inv and inv_id:
            db_inv = Invoice.objects.filter(id=inv_id).first()
    except Exception:
        db_inv = None

    if db_inv:
        dist_user = db_inv.distributor
        dist_name = dist_user.get_full_name() or dist_user.username if dist_user else 'Advance Billing Agency'
        profile = getattr(dist_user, 'profile', None) if dist_user else None
        dist_business = profile.business_name if profile else 'Advance Billing Agency'

        db_items = [
            {
                'name': item.product_name,
                'quantity': item.quantity,
                'unit_price': float(item.unit_price),
                'discount': float(item.discount),
                'tax_rate': float(item.tax_rate),
                'total': float(item.total)
            }
            for item in db_inv.items.all()
        ]

        result['db_verified'] = True
        result['db_invoice'] = {
            'id': db_inv.id,
            'invoice_number': db_inv.invoice_number,
            'customer_name': db_inv.customer_name,
            'customer_phone': db_inv.customer_phone,
            'distributor_name': dist_name,
            'business_name': dist_business,
            'subtotal': float(db_inv.subtotal),
            'tax_amount': float(db_inv.tax_amount),
            'discount': float(db_inv.discount),
            'grand_total': float(db_inv.grand_total),
            'payment_status': db_inv.payment_status,
            'payment_method': db_inv.payment_method,
            'notes': db_inv.notes or '',
            'created_at': db_inv.created_at.strftime('%Y-%m-%d %H:%M'),
            'items': db_items,
            'items_count': len(db_items),
            'view_url': f'/invoice/{db_inv.id}/',
            'pdf_url': f'/invoice/{db_inv.id}/pdf/',
        }

        invoice_info['db_verified'] = True
        invoice_info['db_id'] = db_inv.id
        invoice_info['invoice_number'] = db_inv.invoice_number
        invoice_info['customer_name'] = db_inv.customer_name
        invoice_info['customer_phone'] = db_inv.customer_phone
        invoice_info['business_name'] = dist_business
        invoice_info['distributor_name'] = dist_name
        invoice_info['date'] = db_inv.created_at.strftime('%Y-%m-%d %H:%M')
        invoice_info['total_bill'] = float(db_inv.grand_total)
        invoice_info['formatted_total'] = f"₹{float(db_inv.grand_total):,.2f}"
        invoice_info['subtotal'] = float(db_inv.subtotal)
        invoice_info['tax_amount'] = float(db_inv.tax_amount)
        invoice_info['discount'] = float(db_inv.discount)
        invoice_info['payment_status'] = db_inv.payment_status
        invoice_info['payment_method'] = db_inv.payment_method
        invoice_info['view_url'] = f'/invoice/{db_inv.id}/'
        invoice_info['pdf_url'] = f'/invoice/{db_inv.id}/pdf/'
        if db_items and (not invoice_info.get('items') or len(invoice_info.get('items', [])) == 0):
            invoice_info['items'] = db_items
            invoice_info['items_count'] = len(db_items)
    else:
        result['db_verified'] = False
        invoice_info['db_verified'] = False

    result['invoice_info'] = invoice_info
    return result


@csrf_exempt
@require_http_methods(["POST"])
def api_qr_decode(request):
    """
    Dedicated API endpoint for decoding QR codes from uploaded images.
    Accepts:
    - Multipart file upload under 'image', 'file', or 'qr_image'
    - JSON payload with base64 encoded image string under 'image'
    Returns structured JSON with decoded string, version, type, parsed metadata, and invoice_info.
    """
    uploaded_file = (
        request.FILES.get('image') or
        request.FILES.get('file') or
        request.FILES.get('qr_image')
    )

    image_input = None

    if uploaded_file:
        if uploaded_file.size == 0:
            return JsonResponse({
                'success': False,
                'error': 'The uploaded file is empty (0 bytes). Please upload a valid image file.'
            }, status=400)
        image_input = uploaded_file
    elif request.content_type == 'application/json':
        try:
            body_data = json.loads(request.body.decode('utf-8'))
            image_input = body_data.get('image') or body_data.get('file')
            if not image_input or not str(image_input).strip():
                return JsonResponse({
                    'success': False,
                    'error': 'The image field in JSON payload cannot be empty.'
                }, status=400)
        except Exception:
            return JsonResponse({'success': False, 'error': 'Invalid JSON request payload.'}, status=400)
    elif request.POST.get('image_base64'):
        image_input = request.POST.get('image_base64')
        if not image_input or not image_input.strip():
            return JsonResponse({
                'success': False,
                'error': 'The image_base64 field cannot be empty.'
            }, status=400)

    if not image_input:
        return JsonResponse({
            'success': False,
            'error': 'No image provided. Please upload an image file using multipart/form-data or provide a base64 image string.'
        }, status=400)

    result = decode_qr_image(image_input)
    if result.get('success'):
        result = enrich_result_with_invoice_data(result)

    status_code = 200 if result.get('success') else 422
    return JsonResponse(result, status=status_code)


def qr_decoder_view(request):
    """
    Interactive Web Studio for uploading and decoding QR code images.
    Includes instant preview, format breakdown, parsed invoice rendering, and 1-click test samples.
    Handles empty files, invalid images, and corrupted QR codes gracefully.
    """
    initialize_default_users()
    result = None
    uploaded_b64 = None

    if request.method == 'POST':
        uploaded_file = (
            request.FILES.get('image') or
            request.FILES.get('file') or
            request.FILES.get('qr_image')
        )
        base64_data = request.POST.get('image_base64')

        if uploaded_file:
            if uploaded_file.size == 0:
                result = {'success': False, 'error': 'The uploaded file is empty (0 bytes). Please select a valid QR code image.'}
            else:
                try:
                    uploaded_file.seek(0)
                    file_bytes = uploaded_file.read()
                    if not file_bytes:
                        result = {'success': False, 'error': 'The uploaded file contains no data (0 bytes).'}
                    else:
                        uploaded_b64 = f"data:image/png;base64,{base64.b64encode(file_bytes).decode('utf-8')}"
                        result = decode_qr_image(BytesIO(file_bytes))
                except Exception as e:
                    result = {'success': False, 'error': f"Failed to process uploaded file: {str(e)}"}
        elif base64_data and base64_data.strip():
            uploaded_b64 = base64_data
            result = decode_qr_image(base64_data)
        else:
            result = {'success': False, 'error': 'No image provided. Please select an image file to upload.'}

        if result:
            if result.get('success'):
                result = enrich_result_with_invoice_data(result)
                if result.get('invoice_info'):
                    inv_num = result['invoice_info'].get('invoice_number', 'QR Bill')
                    if result.get('db_verified'):
                        messages.success(request, f"QR Code decoded successfully! Invoice #{inv_num} verified in system database.")
                    else:
                        messages.success(request, f"QR Code decoded successfully! Parsed structured invoice details for #{inv_num}.")
                else:
                    messages.success(request, f"QR Code ({result.get('payload_type', 'QR')}) decoded successfully!")
            else:
                messages.error(request, result.get('error', 'Failed to decode QR code from the uploaded image.'))

    # Generate sample QR codes for immediate testing in the UI
    sample_qrs = []
    
    # Try getting an existing system invoice
    existing_inv = None
    try:
        from .models import Invoice
        existing_inv = Invoice.objects.first()
    except Exception:
        existing_inv = None

    sample_payloads = []
    if existing_inv:
        prod_summary = ", ".join([f"{item.product_name} (x{item.quantity})" for item in existing_inv.items.all()][:3])
        sample_payloads.append({
            'title': f'System GST Invoice ({existing_inv.invoice_number})',
            'desc': f'Live database invoice for {existing_inv.customer_name} - ₹{existing_inv.grand_total}',
            'data': (
                f"Invoice No: {existing_inv.invoice_number}\n"
                f"Date: {existing_inv.created_at.strftime('%Y-%m-%d %H:%M')}\n"
                f"Customer: {existing_inv.customer_name}\n"
                f"Products: {prod_summary}\n"
                f"Total Bill: Rs.{existing_inv.grand_total}"
            )
        })

    sample_payloads.extend([
        {
            'title': 'Retail Tax Invoice QR',
            'desc': 'Formal invoice verification ledger data with customer info & items',
            'data': 'Invoice No: INV-2026-8801\nDate: 2026-10-14 10:30\nCustomer: Priya Sharma\nProducts: Premium Billing Software License (x1), Thermal Paper Rolls 50pk (x2)\nTotal Bill: Rs.2499.00\nPayment Method: UPI QR Code'
        },
        {
            'title': 'UPI Payment QR',
            'desc': 'Advance Billing UPI payment string with amount and VPA',
            'data': f"upi://pay?pa=advancebilling@upi&pn=AdvanceBillingAgency&am={float(existing_inv.grand_total) if existing_inv else '2499.00'}&cu=INR&tn={existing_inv.invoice_number if existing_inv else 'INV-2026-8801'}"
        },
        {
            'title': 'Direct Portal Invoice Link',
            'desc': 'Secure direct HTTPS URL to customer billing receipt',
            'data': f"http://127.0.0.1:8000/invoice/{existing_inv.id if existing_inv else 1}/"
        }
    ])

    for sp in sample_payloads:
        try:
            q = qrcode.QRCode(box_size=6, border=2)
            q.add_data(sp['data'])
            q.make(fit=True)
            buf = BytesIO()
            q.make_image(fill_color='black', back_color='white').save(buf, format='PNG')
            b64_str = f"data:image/png;base64,{base64.b64encode(buf.getvalue()).decode('utf-8')}"
            sample_qrs.append({
                'title': sp['title'],
                'desc': sp['desc'],
                'data': sp['data'],
                'b64': b64_str
            })
        except Exception:
            pass

    context = {
        'result': result,
        'uploaded_b64': uploaded_b64,
        'sample_qrs': sample_qrs,
    }
    return render(request, 'billing/qr_decoder.html', context)



