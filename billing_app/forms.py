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


class ForgotPasswordForm(forms.Form):
    """Form to request password reset OTP by username or email."""
    identity = forms.CharField(
        label="Username or Email",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter your username or email',
            'autofocus': True,
            'id': 'identity'
        })
    )


class VerifyOTPForm(forms.Form):
    """Form to verify 6-digit OTP code."""
    otp_code = forms.CharField(
        label="Enter 6-Digit OTP",
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'form-input otp-code-input',
            'placeholder': '123456',
            'maxlength': '6',
            'id': 'otp_code'
        })
    )


class ResetPasswordForm(forms.Form):
    """Form to reset account password."""
    new_password = forms.CharField(
        label="New Password",
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Enter new password (min 6 characters)',
            'id': 'new_password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm New Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Re-enter new password',
            'id': 'confirm_password'
        })
    )

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please enter matching passwords.")
        return cleaned_data

