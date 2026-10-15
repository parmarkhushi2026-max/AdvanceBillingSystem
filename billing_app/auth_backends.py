from django.contrib.auth.backends import ModelBackend
from django.contrib.auth.models import User
from django.db.models import Q


class EmailOrUsernameBackend(ModelBackend):
    """
    Custom Authentication Backend supporting login via either Username or Email address.
    Applicable for both Admin and Distributor accounts.
    """
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None:
            username = kwargs.get('email')
        
        if not username or not password:
            return None

        username = str(username).strip()
        try:
            # Match username exactly or case-insensitively, or email case-insensitively
            user = User.objects.filter(
                Q(username__iexact=username) | Q(email__iexact=username)
            ).first()
            
            if user and user.check_password(password) and self.user_can_authenticate(user):
                return user
        except Exception:
            return None
        return None
