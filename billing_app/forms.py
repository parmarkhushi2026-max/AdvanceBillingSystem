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


from django.contrib.auth.models import User

class DistributorRegistrationForm(forms.Form):
    """Frontend registration form for new Distributors."""
    full_name = forms.CharField(
        label="Full Name",
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Rajesh Kumar',
            'autofocus': True,
            'id': 'full_name'
        })
    )
    business_name = forms.CharField(
        label="Business / Store Name",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'e.g. Kumar Retail & Trading Co.',
            'id': 'business_name'
        })
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'rajesh@example.com',
            'id': 'email'
        })
    )
    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '+91 98765 43210',
            'id': 'phone'
        })
    )
    upi_id = forms.CharField(
        label="UPI ID (For QR Payments)",
        max_length=100,
        initial='merchant@upi',
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'rajesh@upi',
            'id': 'upi_id'
        })
    )
    username = forms.CharField(
        label="Account Username",
        max_length=50,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'rajesh123',
            'id': 'username'
        })
    )
    password = forms.CharField(
        label="Password",
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Minimum 6 characters',
            'id': 'password'
        })
    )
    confirm_password = forms.CharField(
        label="Confirm Password",
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Re-enter password',
            'id': 'confirm_password'
        })
    )

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another.")
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please ensure both password fields match.")
        return cleaned_data


