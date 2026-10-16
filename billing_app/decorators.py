from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.http import JsonResponse
from .models import UserProfile


def is_ajax_or_api(request):
    """Detect whether request is expecting JSON or is from an API client."""
    return (
        request.path.startswith('/api/') or
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        'application/json' in request.headers.get('accept', '') or
        (getattr(request, 'content_type', '') and 'application/json' in request.content_type)
    )


def _safe_message(request, level, text):
    """Add a flash message safely without failing if MessageMiddleware is absent."""
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


def admin_required(view_func):
    """
    Decorator to ensure only authenticated users with ADMIN role or superuser access can view.
    Redirects unauthenticated users to admin_login, and non-admins to distributor_dashboard.
    Returns 401/403 JsonResponse for API or AJAX calls.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if is_ajax_or_api(request):
                return JsonResponse({
                    'success': False,
                    'message': 'Authentication required. Please log in as an Administrator.'
                }, status=401)
            _safe_message(request, 'warning', 'Please log in as an Administrator to access this page.')
            return redirect('admin_login')
        
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'ADMIN' if request.user.is_superuser else 'DISTRIBUTOR'}
        )
        is_admin = request.user.is_superuser or profile.role == 'ADMIN'
        if not is_admin:
            if is_ajax_or_api(request):
                return JsonResponse({
                    'success': False,
                    'message': 'Access Denied: You do not have Administrator permissions.'
                }, status=403)
            _safe_message(request, 'error', 'Access Denied: You do not have Administrator permissions.')
            return redirect('distributor_dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def distributor_required(view_func):
    """
    Decorator to ensure only authenticated distributors can access.
    Redirects unauthenticated users to distributor_login.
    Returns 401 JsonResponse for API or AJAX calls.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            if is_ajax_or_api(request):
                return JsonResponse({
                    'success': False,
                    'message': 'Authentication required. Please log in as a Distributor.'
                }, status=401)
            _safe_message(request, 'warning', 'Please log in as a Distributor to access the billing register.')
            return redirect('distributor_login')
            
        UserProfile.objects.get_or_create(user=request.user, defaults={'role': 'DISTRIBUTOR'})
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def role_required(allowed_roles):
    """
    Decorator ensuring user is authenticated and possesses one of the specified roles.
    Example: @role_required(['ADMIN', 'DISTRIBUTOR'])
    """
    if isinstance(allowed_roles, str):
        allowed_roles = [allowed_roles]

    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                if is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Authentication required.'
                    }, status=401)
                _safe_message(request, 'warning', 'Please log in to continue.')
                return redirect('portal_select')

            profile, _ = UserProfile.objects.get_or_create(
                user=request.user,
                defaults={'role': 'ADMIN' if request.user.is_superuser else 'DISTRIBUTOR'}
            )
            has_role = request.user.is_superuser or (profile.role in allowed_roles)
            if not has_role:
                if is_ajax_or_api(request):
                    return JsonResponse({
                        'success': False,
                        'message': 'Access denied: Insufficient role permissions.'
                    }, status=403)
                _safe_message(request, 'error', 'Access Denied: You do not have permission to view this page.')
                return redirect('portal_select')

            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def api_login_required(view_func):
    """
    Dedicated decorator for API endpoints requiring authentication.
    Returns JSON 401 Unauthorized if not authenticated.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required. Please log in to continue.'
            }, status=401)
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def api_admin_required(view_func):
    """
    Dedicated decorator for Admin API endpoints requiring ADMIN role or superuser.
    Returns JSON 401 if unauthenticated, 403 if unauthorized.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({
                'success': False,
                'message': 'Authentication required. Please log in as an Administrator.'
            }, status=401)
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'ADMIN' if request.user.is_superuser else 'DISTRIBUTOR'}
        )
        if not (request.user.is_superuser or profile.role == 'ADMIN'):
            return JsonResponse({
                'success': False,
                'message': 'Access Denied: Administrator role required.'
            }, status=403)
        return view_func(request, *args, **kwargs)
    return _wrapped_view
