from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from .models import UserProfile

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


import re
from django.core.validators import validate_email

class ResetPasswordForm(forms.Form):
    """Form to reset account password with strength validation."""
    new_password = forms.CharField(
        label="New Password",
        min_length=6,
        widget=forms.PasswordInput(attrs={
            'class': 'form-input',
            'placeholder': 'Min 6 chars (must include letters & numbers)',
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

    def clean_new_password(self):
        pwd = self.cleaned_data.get('new_password', '')
        if len(pwd) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        if not re.search(r'[a-zA-Z]', pwd):
            raise ValidationError("Password must contain at least one letter (a-z, A-Z).")
        if not re.search(r'[0-9]', pwd):
            raise ValidationError("Password must contain at least one digit (0-9).")
        return pwd

    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("new_password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please enter matching passwords.")
        return cleaned_data


from django.contrib.auth.models import User

class DistributorRegistrationForm(forms.Form):
    """Frontend registration form for new Distributors with strict input validation."""
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
            'placeholder': 'Min 6 chars (letters & numbers)',
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

    # 1. Full Name Validation
    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Full Name must be at least 2 characters long.")
        if not re.match(r"^[a-zA-Z\s\.\']+$", name):
            raise ValidationError("Full Name can only contain letters, spaces, dots, and apostrophes.")
        return name

    # 2. Email Format & Uniqueness Validation
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Please enter a valid email address (e.g. user@domain.com).")
        
        domain = email.split('@')[-1]
        if '.' not in domain or len(domain.split('.')[-1]) < 2:
            raise ValidationError("Please provide an email with a valid domain (e.g. .com, .org, .in).")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("An account with this email address already exists. Please login or use a different email.")
        return email

    # 3. Phone Number Format Validation
    def clean_phone(self):
        phone_raw = self.cleaned_data.get('phone', '').strip()
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone_raw)
        
        if not re.match(r"^\+?[0-9]{10,15}$", phone_clean):
            raise ValidationError("Please enter a valid phone number (10 to 15 digits, optional + country code).")
        return phone_raw

    # 4. UPI ID Format Validation
    def clean_upi_id(self):
        upi = self.cleaned_data.get('upi_id', '').strip().lower()
        if upi:
            if not re.match(r"^[a-zA-Z0-9\.\-_]{2,100}@[a-zA-Z]{2,30}$", upi):
                raise ValidationError("Please enter a valid UPI handle (e.g. name@upi, store@okicici, 9876543210@paytm).")
        return upi

    # 5. Username Format, Length & Uniqueness Validation
    def clean_username(self):
        username = self.cleaned_data.get('username', '').strip()
        if len(username) < 3:
            raise ValidationError("Username must be at least 3 characters long.")
        if not re.match(r"^[a-zA-Z][a-zA-Z0-9_\-]*$", username):
            raise ValidationError("Username must start with a letter and contain only letters, numbers, underscores, or hyphens.")
        
        if User.objects.filter(username__iexact=username).exists():
            raise ValidationError("This username is already taken. Please choose another username.")
        return username

    # 6. Password Strength Validation
    def clean_password(self):
        pwd = self.cleaned_data.get('password', '')
        if len(pwd) < 6:
            raise ValidationError("Password must be at least 6 characters long.")
        if not re.search(r'[a-zA-Z]', pwd):
            raise ValidationError("Password must contain at least one letter (a-z, A-Z).")
        if not re.search(r'[0-9]', pwd):
            raise ValidationError("Password must contain at least one number (0-9).")
        return pwd

    # 7. Password Match Validation
    def clean(self):
        cleaned_data = super().clean()
        p1 = cleaned_data.get("password")
        p2 = cleaned_data.get("confirm_password")
        if p1 and p2 and p1 != p2:
            raise ValidationError("Passwords do not match. Please ensure both password fields match.")
        return cleaned_data


class UserProfileUpdateForm(forms.Form):
    """Form to update User & UserProfile details with validation and DB save method."""
    full_name = forms.CharField(
        label="Full Name",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'full_name'})
    )
    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={'class': 'form-input', 'id': 'email'})
    )
    business_name = forms.CharField(
        label="Business / Store Name",
        max_length=150,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'business_name'})
    )
    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'phone'})
    )
    upi_id = forms.CharField(
        label="UPI ID (For Dynamic QR Billing)",
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-input', 'id': 'upi_id'})
    )

    # Optional Password Change Fields
    current_password = forms.CharField(
        label="Current Password",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Leave blank if not changing', 'id': 'current_password'})
    )
    new_password = forms.CharField(
        label="New Password",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Min 6 chars (letters & numbers)', 'id': 'new_password'})
    )
    confirm_new_password = forms.CharField(
        label="Confirm New Password",
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-input', 'placeholder': 'Re-enter new password', 'id': 'confirm_new_password'})
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

    def clean_full_name(self):
        name = self.cleaned_data.get('full_name', '').strip()
        if len(name) < 2:
            raise ValidationError("Full Name must be at least 2 characters long.")
        if not re.match(r"^[a-zA-Z\s\.\']+$", name):
            raise ValidationError("Full Name can only contain letters, spaces, dots, and apostrophes.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        try:
            validate_email(email)
        except ValidationError:
            raise ValidationError("Please enter a valid email address.")
        
        domain = email.split('@')[-1]
        if '.' not in domain or len(domain.split('.')[-1]) < 2:
            raise ValidationError("Please enter an email with a valid domain (e.g. .com, .in).")

        if self.user and User.objects.filter(email__iexact=email).exclude(pk=self.user.pk).exists():
            raise ValidationError("An account with this email address already exists.")
        return email

    def clean_phone(self):
        phone_raw = self.cleaned_data.get('phone', '').strip()
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone_raw)
        if not re.match(r"^\+?[0-9]{10,15}$", phone_clean):
            raise ValidationError("Please enter a valid phone number (10 to 15 digits, optional + country code).")
        return phone_raw

    def clean_upi_id(self):
        upi = self.cleaned_data.get('upi_id', '').strip().lower()
        if upi and not re.match(r"^[a-zA-Z0-9\.\-_]{2,100}@[a-zA-Z]{2,30}$", upi):
            raise ValidationError("Please enter a valid UPI handle (e.g. name@upi, store@okicici).")
        return upi

    def clean(self):
        cleaned_data = super().clean()
        curr_pwd = cleaned_data.get('current_password')
        new_pwd = cleaned_data.get('new_password')
        confirm_pwd = cleaned_data.get('confirm_new_password')

        if curr_pwd or new_pwd or confirm_pwd:
            if not curr_pwd:
                self.add_error('current_password', "Please enter your current password to set a new password.")
            elif self.user and not self.user.check_password(curr_pwd):
                self.add_error('current_password', "Current password is incorrect.")

            if not new_pwd:
                self.add_error('new_password', "Please enter a new password.")
            else:
                if len(new_pwd) < 6:
                    self.add_error('new_password', "New password must be at least 6 characters long.")
                if not re.search(r'[a-zA-Z]', new_pwd):
                    self.add_error('new_password', "New password must contain at least one letter.")
                if not re.search(r'[0-9]', new_pwd):
                    self.add_error('new_password', "New password must contain at least one number.")

            if new_pwd and confirm_pwd and new_pwd != confirm_pwd:
                self.add_error('confirm_new_password', "New passwords do not match.")

        return cleaned_data

    def save_profile(self, user):
        """Save updated profile data and optional new password directly to Database."""
        full_name = self.cleaned_data['full_name'].strip()
        name_parts = full_name.split(' ', 1)
        user.first_name = name_parts[0]
        user.last_name = name_parts[1] if len(name_parts) > 1 else ''
        user.email = self.cleaned_data['email']

        new_pwd = self.cleaned_data.get('new_password')
        if new_pwd:
            user.set_password(new_pwd)

        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        profile.business_name = self.cleaned_data.get('business_name', '').strip()
        profile.phone = self.cleaned_data.get('phone', '').strip()
        profile.upi_id = self.cleaned_data.get('upi_id', '').strip()
        profile.save()

        return user, profile


# Alias for backward compatibility
DistributorProfileForm = UserProfileUpdateForm


from .models import Customer

class CustomerForm(forms.Form):
    """Form to add a new Customer with strict validations."""
    name = forms.CharField(
        label="Customer Name",
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Acme Corporation or Anish Patel', 'autofocus': True, 'id': 'name'})
    )
    email = forms.EmailField(
        label="Email Address",
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'customer@example.com', 'id': 'email'})
    )
    phone = forms.CharField(
        label="Phone Number",
        max_length=20,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '+91 98765 43210', 'id': 'phone'})
    )
    address = forms.CharField(
        label="Street Address",
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': '123 Business Way, Suite 400', 'id': 'address'})
    )
    city = forms.CharField(
        label="City / Location",
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Mumbai', 'id': 'city'})
    )
    gstin = forms.CharField(
        label="GSTIN (Optional)",
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': '27AAAAA0000A1Z5', 'id': 'gstin'})
    )

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("Customer Name must be at least 2 characters long.")
        return name

    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()
        if email:
            try:
                validate_email(email)
            except ValidationError:
                raise ValidationError("Please enter a valid email address.")
        return email

    def clean_phone(self):
        phone_raw = self.cleaned_data.get('phone', '').strip()
        phone_clean = re.sub(r'[\s\-\(\)]', '', phone_raw)
        if not re.match(r"^\+?[0-9]{10,15}$", phone_clean):
            raise ValidationError("Please enter a valid phone number (10 to 15 digits, optional + country code).")
        return phone_raw

    def clean_gstin(self):
        gstin = self.cleaned_data.get('gstin', '').strip().upper()
        if gstin:
            if not re.match(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$", gstin):
                raise ValidationError("Please enter a valid 15-character GSTIN (e.g. 27AAAAA0000A1Z5).")
        return gstin

    def save_customer(self, created_by=None):
        """Save new Customer to database."""
        customer = Customer.objects.create(
            name=self.cleaned_data['name'].strip(),
            email=self.cleaned_data.get('email', '').strip() or None,
            phone=self.cleaned_data['phone'].strip(),
            address=self.cleaned_data.get('address', '').strip() or None,
            city=self.cleaned_data.get('city', '').strip() or None,
            gstin=self.cleaned_data.get('gstin', '').strip() or None,
            created_by=created_by
        )
        return customer

    def update_customer(self, customer):
        """Update existing Customer instance in database."""
        customer.name = self.cleaned_data['name'].strip()
        customer.email = self.cleaned_data.get('email', '').strip() or None
        customer.phone = self.cleaned_data['phone'].strip()
        customer.address = self.cleaned_data.get('address', '').strip() or None
        customer.city = self.cleaned_data.get('city', '').strip() or None
        customer.gstin = self.cleaned_data.get('gstin', '').strip() or None
        customer.save()
        return customer

from .models import Product

class ProductForm(forms.ModelForm):
    """Form to add or update a Product."""
    class Meta:
        model = Product
        fields = ['name', 'sku', 'category', 'price', 'gst_rate', 'hsn_code', 'stock', 'unit', 'description']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Wireless Barcode Scanner Pro', 'autofocus': True}),
            'sku': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'SKU / Barcode (Optional)'}),
            'category': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Hardware, Software, etc.'}),
            'price': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.01'}),
            'gst_rate': forms.NumberInput(attrs={'class': 'form-input', 'step': '0.01', 'min': '0.00'}),
            'hsn_code': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'HSN / SAC Code'}),
            'stock': forms.NumberInput(attrs={'class': 'form-input', 'min': '0', 'step': '1'}),
            'unit': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Pcs, Kg, Box'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Product description...'}),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name', '').strip()
        if len(name) < 2:
            raise ValidationError("Product Name must be at least 2 characters long.")
        return name

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price is not None and price <= 0:
            raise ValidationError("Price must be greater than 0.")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock is not None and stock < 0:
            raise ValidationError("Stock cannot be negative.")
        return stock



