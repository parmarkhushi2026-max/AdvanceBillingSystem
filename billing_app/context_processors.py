"""
Context processors to expose user role distinction variables to all templates.
"""
from .models import UserProfile


def user_role_context(request):
    """
    Exposes user role distinction information to all templates:
      - is_admin: True if user is superuser or ADMIN role
      - is_distributor: True if user has DISTRIBUTOR role
      - user_role: 'ADMIN', 'DISTRIBUTOR', or 'ANONYMOUS'
      - user_profile: UserProfile instance if available
    """
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        if hasattr(request, 'user_role'):
            return {
                'user_role': request.user_role,
                'is_admin': request.is_admin,
                'is_distributor': request.is_distributor,
                'user_profile': getattr(request, 'user_profile', None),
            }

        profile = getattr(user, 'profile', None)
        if not profile:
            profile = UserProfile.objects.filter(user=user).first()

        is_admin = user.is_superuser or (profile and profile.role == 'ADMIN')
        return {
            'user_role': 'ADMIN' if is_admin else 'DISTRIBUTOR',
            'is_admin': is_admin,
            'is_distributor': not is_admin,
            'user_profile': profile,
        }

    return {
        'user_role': 'ANONYMOUS',
        'is_admin': False,
        'is_distributor': False,
        'user_profile': None,
    }
