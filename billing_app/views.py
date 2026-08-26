import json
import uuid
import random
import time
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Q
from django.core.paginator import Paginator
from .models import UserProfile, Product, Invoice, InvoiceItem, OTPToken, Customer
from .forms import AdminLoginForm, DistributorLoginForm, ForgotPasswordForm, VerifyOTPForm, ResetPasswordForm, DistributorRegistrationForm, DistributorProfileForm, CustomerForm, ProductForm
from .decorators import admin_required, distributor_required


def initialize_default_users():
    """Ensure default admin, distributor and demo products exist in the database."""
    # Admin Account
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

    # Distributor Account
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

# 2. Admin Login View (Django Auth Backend)
def admin_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        if request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN'):
            return redirect('admin_dashboard')

    if request.method == 'POST':
        form = AdminLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back, Administrator {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or 'admin_dashboard'
            return redirect(next_url)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = AdminLoginForm(request)

    return render(request, 'auth/login_admin.html', {'form': form})

# 3. Distributor Login View (Django Auth Backend)
def distributor_login_view(request):
    initialize_default_users()
    if request.user.is_authenticated:
        return redirect('distributor_dashboard')

    if request.method == 'POST':
        form = DistributorLoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, f'Welcome back, Distributor {user.get_full_name() or user.username}!')
            next_url = request.GET.get('next') or 'distributor_dashboard'
            return redirect(next_url)
        else:
            for error in form.non_field_errors():
                messages.error(request, error)
    else:
        form = DistributorLoginForm(request)

    return render(request, 'auth/login_distributor.html', {'form': form})

# 4. Logout View
def user_logout(request):
    username = request.user.username if request.user.is_authenticated else ''
    auth_logout(request)
    if username:
        messages.info(request, f'Goodbye {username}, you have been securely logged out.')
    else:
        messages.info(request, 'You have been securely logged out.')
    return redirect('portal_select')

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

# 7. Create QR Bill & Invoice View (Protected by @distributor_required)
@distributor_required
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
        inv_number = f"INV-{uuid.uuid4().hex[:8].upper()}"

        customer_obj = Customer.objects.filter(
            Q(phone=customer_phone) | Q(name__iexact=customer_name),
            Q(created_by=request.user) | Q(created_by__isnull=True)
        ).first()

        invoice = Invoice.objects.create(
            invoice_number=inv_number,
            distributor=request.user,
            customer_ref=customer_obj,
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
            p_name = str(item.get('name', 'Product')).strip() or 'Product'
            
            try:
                p_qty = max(1, int(item.get('qty', 1)))
            except (ValueError, TypeError):
                p_qty = 1

            try:
                p_price = Decimal(str(item.get('price', 0)))
            except (InvalidOperation, ValueError, TypeError):
                p_price = Decimal('0.00')

            try:
                p_tax_rate = Decimal(str(item.get('tax', 18)))
            except (InvalidOperation, ValueError, TypeError):
                p_tax_rate = Decimal('18.00')
            
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

    # Dynamic UPI Payment format
    upi_payment_url = f"upi://pay?pa={upi_id}&pn={business_name.replace(' ', '%20')}&am={invoice.grand_total}&tn={invoice.invoice_number}&cu=INR"

    context = {
        'invoice': invoice,
        'items': invoice.items.all(),
        'upi_id': upi_id,
        'business_name': business_name,
        'upi_payment_url': upi_payment_url,
    }
    return render(request, 'billing/invoice_detail.html', context)


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

            # Create UserProfile
            UserProfile.objects.create(
                user=user,
                role='DISTRIBUTOR',
                business_name=business_name,
                phone=phone,
                upi_id=upi_id
            )

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
        'role': 'Distributor',
    }
    return render(request, 'dashboard/distributor_profile.html', context)


# 13. Customer Management: Add Customer View
@distributor_required
def add_customer_view(request):
    initialize_default_users()
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
        'role': 'Distributor',
    }
    return render(request, 'billing/add_customer.html', context)


# 14. Customer Management: Customer List View
@distributor_required
def customer_list_view(request):
    initialize_default_users()
    query = request.GET.get('q', '').strip()
    
    customers = Customer.objects.all()
    if not request.user.is_superuser:
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
        'role': 'Distributor',
    }
    return render(request, 'billing/customer_list.html', context)


# 15. Edit Customer View
@distributor_required
def edit_customer_view(request, customer_id):
    initialize_default_users()
    customer = get_object_or_404(Customer, pk=customer_id)

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
        'role': 'Distributor',
    }
    return render(request, 'billing/add_customer.html', context)


# 16. Delete Customer View
@distributor_required
def delete_customer_view(request, customer_id):
    initialize_default_users()
    customer = get_object_or_404(Customer, pk=customer_id)
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
        'role': 'Admin' if (request.user.is_superuser or (hasattr(request.user, 'profile') and request.user.profile.role == 'ADMIN')) else 'Distributor',
    }
    return render(request, 'billing/add_product.html', context)


# 21. Product Management: Delete Product
@login_required
def delete_product_view(request, product_id):
    initialize_default_users()
    product = get_object_or_404(Product, pk=product_id)
    name = product.name
    product.delete()
    messages.success(request, f"🗑️ Product '{name}' deleted successfully from inventory.")
    return redirect('product_list')


