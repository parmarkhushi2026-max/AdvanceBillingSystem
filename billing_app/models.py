from django.db import models
from django.contrib.auth.models import User

class UserProfile(models.Model):
    ROLE_CHOICES = (
        ('ADMIN', 'System Admin'),
        ('DISTRIBUTOR', 'Distributor'),
    )
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='DISTRIBUTOR')
    business_name = models.CharField(max_length=150, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    upi_id = models.CharField(max_length=100, default='merchant@upi', help_text='UPI ID for dynamic QR payments')

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"

class Product(models.Model):
    name = models.CharField(max_length=150)
    category = models.CharField(max_length=100, default='General')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, help_text='Tax % (GST/VAT)')
    stock = models.PositiveIntegerField(default=100)

    def __str__(self):
        return f"{self.name} - ₹{self.price}"

class Customer(models.Model):
    """Model representing retail/wholesale customers of distributors."""
    name = models.CharField(max_length=150)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=20)
    address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    gstin = models.CharField(max_length=20, blank=True, null=True, help_text='GST Identification Number')
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='customers')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Invoice(models.Model):
    PAYMENT_CHOICES = (
        ('PAID', 'Paid via QR/Cash'),
        ('PENDING', 'Pending'),
        ('FAILED', 'Failed'),
    )
    invoice_number = models.CharField(max_length=50, unique=True)
    distributor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer_ref = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='PAID')
    payment_method = models.CharField(max_length=50, default='UPI QR Code')
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Invoice #{self.invoice_number} - ₹{self.grand_total}"


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.product_name} x {self.quantity}"


import random
from django.utils import timezone
from datetime import timedelta

class OTPToken(models.Model):
    """Temporary database model for storing randomly generated OTP codes."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='otp_tokens')
    otp_code = models.CharField(max_length=6)
    is_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    class Meta:
        ordering = ['-created_at']

    def is_valid(self):
        """Check if OTP is not verified yet and has not expired."""
        return not self.is_verified and timezone.now() <= self.expires_at

    @classmethod
    def generate_otp_for_user(cls, user, validity_minutes=10):
        """Generate a random 6-digit OTP code, store in DB, and invalidate older active OTPs."""
        # Invalidate old unverified OTPs
        cls.objects.filter(user=user, is_verified=False).update(is_verified=True)
        
        # Generate random 6-digit OTP code
        random_code = f"{random.randint(100000, 999999)}"
        expiration = timezone.now() + timedelta(minutes=validity_minutes)

        token = cls.objects.create(
            user=user,
            otp_code=random_code,
            expires_at=expiration
        )
        return token

    def __str__(self):
        status = "Verified" if self.is_verified else ("Valid" if self.is_valid() else "Expired")
        return f"OTP {self.otp_code} for {self.user.username} ({status})"

