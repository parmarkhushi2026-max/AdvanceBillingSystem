import json
import uuid
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Sum, Count
from .models import UserProfile, Product, Invoice, InvoiceItem

def initialize_default_users():
    """Ensure default admin, distributor and demo products exist for instant demonstration."""
    # Admin
    if not User.objects.filter(username='admin').exists():
        admin_user = User.objects.create_superuser('admin', 'admin@advancebilling.com', 'admin123')
        admin_user.first_name = 'Super'
        admin_user.last_name = 'Admin'
        admin_user.save()
        UserProfile.objects.create(
            user=admin_user,
            role='ADMIN',
            business_name='Advance Billing HQ',
            phone='+91 98765 43210',
            upi_id='advancebilling@upi'
        )

    # Distributor
    if not User.objects.filter(username='distributor').exists():
        dist_user = User.objects.create_user('distributor', 'distributor@agency.com', 'dist123')
        dist_user.first_name = 'Rahul'
        dist_user.last_name = 'Sharma'
        dist_user.save()
        UserProfile.objects.create(
            user=dist_user,
            role='DISTRIBUTOR',
            business_name='Sharma Tech & Retail Distribution',
            phone='+91 98123 45678',
            upi_id='sharmadist@upi'
        )

    # Sample Products if none exist
    if Product.objects.count() == 0:
        Product.objects.bulk_create([
            Product(name='Wireless Barcode Scanner Pro', category='Hardware', price=Decimal('2499.00'), tax_rate=18.00, stock=45),
            Product(name='Thermal Receipt Printer 80mm', category='Hardware', price=Decimal('4890.00'), tax_rate=18.00, stock=30),
            Product(name='Advance POS Touch Terminal', category='Hardware', price=Decimal('18500.00'), tax_rate=18.00, stock=12),
            Product(name='Billing Software Annual License', category='Software', price=Decimal('5999.00'), tax_rate=18.00, stock=999),
            Product(name='Thermal Paper Rolls (Box of 50)', category='Supplies', price=Decimal('850.00'), tax_rate=12.00, stock=150),
            Product(name='QR Payment Display Stand', category='Accessories', price=Decimal('450.00'), tax_rate=18.00, stock=80),
        ])

# 1. Landing Page / Portal Selector
def portal_select(request):
    initialize_default_users()
    if request.user.is_authenticated:
        try:
            if request.user.profile.role == 'ADMIN' or request.user.is_superuser:
                return redirect('admin_dashboard')
            return redirect('distributor_dashboard')
        except Exception:
            return redirect('distributor_dashboard')
    return render(request, 'home.html')

# 2. Admin Login View
def admin_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        return redirect('admin_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            # Verify admin role
            is_admin = user.is_superuser
            if hasattr(user, 'profile') and user.profile.role == 'ADMIN':
                is_admin = True
            
            if is_admin:
                login(request, user)
                messages.success(request, f'Welcome back, System Admin {user.username}!')
                return redirect('admin_dashboard')
            else:
                messages.error(request, 'Access Denied: This account is not registered with Admin privileges. Please use Distributor Login.')
        else:
            messages.error(request, 'Invalid Admin username or password.')

    return render(request, 'auth/login_admin.html')

# 3. Distributor Login View
def distributor_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        return redirect('distributor_dashboard')

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            messages.success(request, f'Welcome back, Distributor {user.username}!')
            return redirect('distributor_dashboard')
        else:
            messages.error(request, 'Invalid Distributor username or password.')

    return render(request, 'auth/login_distributor.html')

# 4. Logout
def user_logout(request):
    logout(request)
    messages.info(request, 'You have been securely logged out.')
    return redirect('portal_select')

# 5. Admin Dashboard
@login_required(login_url='admin_login')
def admin_dashboard_view(request):
    initialize_default_users()
    # Ensure only admin can access
    if hasattr(request.user, 'profile') and request.user.profile.role != 'ADMIN' and not request.user.is_superuser:
        messages.error(request, 'Unauthorized: Admin privileges required.')
        return redirect('distributor_dashboard')

    total_invoices = Invoice.objects.count()
    total_revenue = Invoice.objects.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_distributors = UserProfile.objects.filter(role='DISTRIBUTOR').count()
    total_products = Product.objects.count()

    recent_invoices = Invoice.objects.all().order_by('-created_at')[:10]
    distributors = UserProfile.objects.filter(role='DISTRIBUTOR').select_related('user')

    context = {
        'total_invoices': total_invoices,
        'total_revenue': total_revenue,
        'total_distributors': total_distributors,
        'total_products': total_products,
        'recent_invoices': recent_invoices,
        'distributors': distributors,
        'role': 'Admin',
    }
    return render(request, 'dashboard/admin_dashboard.html', context)

# 6. Distributor Dashboard
@login_required(login_url='distributor_login')
def distributor_dashboard_view(request):
    initialize_default_users()
    distributor = request.user
    
    # Get user profile or fallback
    profile = getattr(distributor, 'profile', None)
    upi_id = profile.upi_id if profile else 'merchant@upi'
    business_name = profile.business_name if profile else 'Distributor Agency'

    my_invoices = Invoice.objects.filter(distributor=distributor).order_by('-created_at')
    if not my_invoices.exists() and request.user.is_superuser:
        my_invoices = Invoice.objects.all().order_by('-created_at')

    my_revenue = my_invoices.filter(payment_status='PAID').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    my_invoice_count = my_invoices.count()
    products = Product.objects.all()

    context = {
        'invoices': my_invoices[:8],
        'total_revenue': my_revenue,
        'invoice_count': my_invoice_count,
        'products_count': products.count(),
        'upi_id': upi_id,
        'business_name': business_name,
        'products': products,
        'role': 'Distributor',
    }
    return render(request, 'dashboard/distributor_dashboard.html', context)

# 7. Create QR Bill & Invoice View
@login_required(login_url='distributor_login')
def create_invoice_view(request):
    initialize_default_users()
    products = Product.objects.all()
    profile = getattr(request.user, 'profile', None)
    upi_id = profile.upi_id if profile else 'advancebilling@upi'
    business_name = profile.business_name if profile else 'Advance Billing Agency'

    if request.method == 'POST':
        customer_name = request.POST.get('customer_name', 'Walk-in Customer')
        customer_phone = request.POST.get('customer_phone', '9999999999')
        payment_method = request.POST.get('payment_method', 'UPI QR Code')
        notes = request.POST.get('notes', '')
        
        items_json = request.POST.get('items_data', '[]')
        try:
            items_data = json.loads(items_json)
        except Exception:
            items_data = []

        if not items_data:
            messages.error(request, 'Please add at least one product item to create the bill.')
            return redirect('create_invoice')

        # Calculate totals
        subtotal = Decimal('0.00')
        tax_total = Decimal('0.00')
        
        # Generate unique invoice number
        inv_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

        invoice = Invoice.objects.create(
            invoice_number=inv_number,
            distributor=request.user,
            customer_name=customer_name,
            customer_phone=customer_phone,
            payment_status='PAID',
            payment_method=payment_method,
            notes=notes,
            subtotal=subtotal,
            tax_amount=tax_total,
            grand_total=Decimal('0.00')
        )

        for item in items_data:
            p_name = item.get('name', 'Product')
            p_qty = int(item.get('qty', 1))
            p_price = Decimal(str(item.get('price', 0)))
            p_tax_rate = Decimal(str(item.get('tax', 18)))
            
            line_subtotal = p_price * p_qty
            line_tax = line_subtotal * (p_tax_rate / Decimal('100'))
            line_total = line_subtotal + line_tax

            subtotal += line_subtotal
            tax_total += line_tax

            InvoiceItem.objects.create(
                invoice=invoice,
                product_name=p_name,
                quantity=p_qty,
                unit_price=p_price,
                tax_rate=p_tax_rate,
                total=line_total
            )

        invoice.subtotal = subtotal
        invoice.tax_amount = tax_total
        invoice.grand_total = subtotal + tax_total
        invoice.save()

        messages.success(request, f'Invoice #{inv_number} created with QR Code successfully!')
        return redirect('invoice_detail', invoice_id=invoice.id)

    context = {
        'products': products,
        'upi_id': upi_id,
        'business_name': business_name,
    }
    return render(request, 'billing/create_invoice.html', context)

# 8. Invoice Detail & Printable QR Receipt
@login_required
def invoice_detail_view(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id)
    profile = getattr(invoice.distributor, 'profile', None) if invoice.distributor else None
    upi_id = profile.upi_id if profile else 'advancebilling@upi'
    business_name = profile.business_name if profile else 'Advance Billing Agency'

    # UPI Dynamic Payment URL format
    # upi://pay?pa=UPI_ID&pn=NAME&am=AMOUNT&tn=INVOICE_NO&cu=INR
    upi_payment_url = f"upi://pay?pa={upi_id}&pn={business_name.replace(' ', '%20')}&am={invoice.grand_total}&tn={invoice.invoice_number}&cu=INR"

    context = {
        'invoice': invoice,
        'items': invoice.items.all(),
        'upi_id': upi_id,
        'business_name': business_name,
        'upi_payment_url': upi_payment_url,
    }
    return render(request, 'billing/invoice_detail.html', context)
