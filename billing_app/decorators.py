from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from .models import UserProfile

def admin_required(view_func):
    """Decorator to ensure only authenticated users with ADMIN role or superuser access can view."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in as an Administrator to access this page.')
            return redirect('admin_login')
        
        profile, _ = UserProfile.objects.get_or_create(
            user=request.user,
            defaults={'role': 'ADMIN' if request.user.is_superuser else 'DISTRIBUTOR'}
        )
        is_admin = request.user.is_superuser or profile.role == 'ADMIN'
        if not is_admin:
            messages.error(request, 'Access Denied: You do not have Administrator permissions.')
            return redirect('distributor_dashboard')
            
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def distributor_required(view_func):
    """Decorator to ensure only authenticated distributors can access."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in as a Distributor to access the billing register.')
            return redirect('distributor_login')
            
        UserProfile.objects.get_or_create(user=request.user, defaults={'role': 'DISTRIBUTOR'})
        return view_func(request, *args, **kwargs)
    return _wrapped_view

