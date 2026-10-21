import re
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile


def _safe_message(request, level, text):
    """Add flash message safely without failing if MessageMiddleware is absent."""
    try:
        if level == 'warning':
            messages.warning(request, text, fail_silently=True)
        elif level == 'error':
            messages.error(request, text, fail_silently=True)
        elif level == 'success':
            messages.success(request, text, fail_silently=True)
        else:
            messages.info(request, text, fail_silently=True)
    except Exception:
        pass


class RouteProtectionMiddleware:
    """
    Comprehensive Route Protection & Role-Based Access Control (RBAC) Middleware.
    
    Guards routes across the application:
    - Protects Admin routes (/admin/* excluding password recovery).
    - Protects Distributor routes (/distributor/dashboard/, /distributor/profile/, /distributor/billing/).
    - Protects core management routes (/invoices/, /customers/ CRUD, /products/ CRUD).
    - Respects public whitelisted authentication, onboarding, and static asset routes.
    - Gracefully differentiates between Web browser navigation (friendly redirects + messages)
      and API/AJAX requests (standard HTTP 401/403 JSON payloads).
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # Exact public URL paths exempt from auth protection
        self.public_exact_paths = {
            '/',
            '/login/admin/',
            '/register/admin/',
            '/login/distributor/',
            '/register/distributor/',
            '/forgot-password/',
            '/forgot-password/resend-otp/',
            '/admin/forgot-password/',
            '/admin/forgot-password/resend-otp/',
            '/logout/',
            '/api/login/',
            '/api/login/admin/',
            '/api/admin/login/',
            '/api/login/distributor/',
            '/api/distributor/login/',
            '/api/auth/session/',
            '/api/session/',
            '/api/auth/logout/',
            '/api/register/admin/',
            '/api/register/distributor/',
            '/api/customer/register/',
            '/api/register/customer/',
            '/api/distributor/customers/register/',
            '/api/products/',
            '/api/qr/decode/',
            '/api/qr-decode/',
            '/qr-decoder/',
            '/qr/decoder/',
            '/customers/register/',
            '/register/customer/',
            '/distributor/customer/register/',
            '/products/manage/',
            '/manage/products/',
        }

        # Public path prefixes
        self.public_prefixes = (
            '/static/',
            '/media/',
            '/admin/forgot-password/',
            '/django-admin/',
            '/api/products/',
            '/api/invoice/',
        )

        # Admin protected path prefixes
        self.admin_prefixes = (
            '/admin/dashboard/',
            '/admin/reports/',
        )

        # Distributor protected path prefixes
        self.distributor_prefixes = (
            '/distributor/dashboard/',
            '/distributor/profile/',
            '/distributor/billing/',
        )

        # Protected core paths requiring general authenticated user
        self.protected_core_prefixes = (
            '/invoices/',
            '/invoice/',
            '/reports/invoices/',
        )

    def is_ajax_or_api(self, request):
        """Determine whether the request expects a JSON or API response."""
        return (
            request.path.startswith('/api/') or
            request.headers.get('x-requested-with') == 'XMLHttpRequest' or
            'application/json' in request.headers.get('accept', '') or
            (getattr(request, 'content_type', '') and 'application/json' in request.content_type)
        )

    def __call__(self, request):
        path = request.path

        # 1. Check if route is public or explicitly exempt
        if path in self.public_exact_paths or any(path.startswith(prefix) for prefix in self.public_prefixes) or path.endswith('/qr.png') or path.endswith('/qr-image/'):
            return self.get_response(request)

        # 2. Check Admin Protected Routes (/admin/...)
        is_admin_path = any(path.startswith(prefix) for prefix in self.admin_prefixes) or (
            path.startswith('/admin/') and not path.startswith('/admin/forgot-password')
        )

        if is_admin_path:
            if not request.user.is_authenticated:
                if self.is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Authentication required. Please log in as an Administrator.'
                    }, status=401)
                _safe_message(request, 'warning', 'Please log in as an Administrator to access this page.')
                return redirect('admin_login')

            # User is authenticated; verify Admin role
            profile, _ = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'role': 'ADMIN' if request.user.is_superuser else 'DISTRIBUTOR'}
            )
            is_admin = request.user.is_superuser or (profile.role == 'ADMIN')
            if not is_admin:
                if self.is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Access Denied: You do not have Administrator permissions.'
                    }, status=403)
                _safe_message(request, 'error', 'Access Denied: You do not have Administrator permissions.')
                return redirect('distributor_dashboard')

            return self.get_response(request)

        # 3. Check Distributor Protected Routes (/distributor/...)
        if any(path.startswith(prefix) for prefix in self.distributor_prefixes):
            if not request.user.is_authenticated:
                if self.is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Authentication required. Please log in as a Distributor.'
                    }, status=401)
                _safe_message(request, 'warning', 'Please log in as a Distributor to access the billing register.')
                return redirect('distributor_login')

            return self.get_response(request)

        # 4. Check Protected Core Management Routes
        is_protected_core = any(path.startswith(prefix) for prefix in self.protected_core_prefixes)
        
        # Check specific customer & product management routes
        is_customer_mgmt = (
            path == '/customers/' or
            path.startswith('/customers/add/') or
            bool(re.match(r'^/customers/\d+/(edit|delete)/', path))
        )
        is_product_mgmt = (
            path == '/products/' or
            path.startswith('/products/add/') or
            bool(re.match(r'^/products/\d+/(edit|delete)/', path))
        )

        if is_protected_core or is_customer_mgmt or is_product_mgmt:
            if not request.user.is_authenticated:
                if self.is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Authentication required. Please log in to continue.'
                    }, status=401)
                _safe_message(request, 'warning', 'Please log in to continue.')
                return redirect('portal_select')

            return self.get_response(request)

        return self.get_response(request)
