from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError

class AdminLoginForm(AuthenticationForm):
    """Custom Django Authentication form specifically validating Admin privileges."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter admin username',
            'autofocus': True,
            'id': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter admin password',
            'id': 'password'
        })
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise ValidationError(
                    'Invalid credentials. Please verify your Admin username and password.',
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)
                
                # Check for Admin permissions
                is_admin = self.user_cache.is_superuser or (
                    hasattr(self.user_cache, 'profile') and self.user_cache.profile.role == 'ADMIN'
                )
                if not is_admin:
                    raise ValidationError(
                        'Access Denied: This account is not authorized as an Administrator. Please use the Distributor Login portal.',
                        code='not_admin'
                    )

        return self.cleaned_data


class DistributorLoginForm(AuthenticationForm):
    """Custom Django Authentication form for Distributors."""
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter distributor username',
            'autofocus': True,
            'id': 'username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter distributor password',
            'id': 'password'
        })
    )

    def clean(self):
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')

        if username and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                raise ValidationError(
                    'Invalid credentials. Please verify your distributor username and password.',
                    code='invalid_login'
                )
            else:
                self.confirm_login_allowed(self.user_cache)

        return self.cleaned_data
