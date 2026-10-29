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
    sku = models.CharField(max_length=50, blank=True, null=True, unique=True, help_text='Stock Keeping Unit / Product Barcode')
    category = models.CharField(max_length=100, default='General')
    price = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField(default=100)
    gst_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00, help_text='GST Rate % (e.g. 0, 5, 12, 18, 28)')
    hsn_code = models.CharField(max_length=20, blank=True, null=True, help_text='HSN / SAC Code')
    unit = models.CharField(max_length=20, default='Pcs', help_text='Measurement unit (Pcs, Kg, Box, Mtr, Ltr, set)')
    description = models.TextField(blank=True, null=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def tax_rate(self):
        return self.gst_rate

    @tax_rate.setter
    def tax_rate(self, value):
        self.gst_rate = value

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
    customer = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoices')
    customer_ref = models.ForeignKey(Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='legacy_invoices')
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=20)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='PAID')
    payment_method = models.CharField(max_length=50, default='UPI QR Code')
    notes = models.TextField(blank=True, null=True)
    qr_code_image = models.ImageField(upload_to='invoice_qrs/', blank=True, null=True, help_text='QR code image generated on invoice save')
    qr_code_payload = models.TextField(blank=True, null=True, help_text='Structured payload encoded inside the QR')
    created_at = models.DateTimeField(auto_now_add=True)

    def __init__(self, *args, **kwargs):
        total_amount = kwargs.pop('total_amount', None)
        date = kwargs.pop('date', None)
        super().__init__(*args, **kwargs)
        if total_amount is not None:
            self.grand_total = total_amount
        if date is not None:
            self.created_at = date

    @property
    def invoice_id(self):
        """Returns invoice primary key ID."""
        return self.id

    @property
    def total_amount(self):
        """Alias property for grand_total total amount."""
        return self.grand_total

    @total_amount.setter
    def total_amount(self, value):
        self.grand_total = value

    @property
    def date(self):
        """Alias property for invoice date (created_at)."""
        return self.created_at

    @date.setter
    def date(self, value):
        self.created_at = value

    def save(self, *args, **kwargs):
        if self.customer:
            if not self.customer_name:
                self.customer_name = self.customer.name
            if not self.customer_phone:
                self.customer_phone = self.customer.phone
            if not self.customer_ref:
                self.customer_ref = self.customer
        elif self.customer_ref and not self.customer:
            self.customer = self.customer_ref
            if not self.customer_name:
                self.customer_name = self.customer_ref.name
            if not self.customer_phone:
                self.customer_phone = self.customer_ref.phone

        # Support skipping automatic QR code generation if explicitly requested
        skip_qr = kwargs.pop('skip_qr_generation', False)

        super().save(*args, **kwargs)

        # Handle QR generation during invoice save using libraries like qrcode or segno
        if not skip_qr:
            try:
                self.generate_and_save_qr()
            except Exception:
                # Keep invoice save resilient even if external image library fails
                pass

    def __str__(self):
        return f"Invoice #{self.invoice_number} - ₹{self.grand_total}"

    def generate_and_save_qr(self, engine='auto', payload_format='text', box_size=6, border=2):
        """
        Generate a QR code using libraries like 'qrcode' or 'segno' during invoice save,
        storing the image in `qr_code_image` and the text payload in `qr_code_payload`.
        """
        from .invoice_qr import generate_invoice_qr, build_invoice_qr_payload, fetch_invoice_data
        from django.core.files.base import ContentFile

        data = fetch_invoice_data(self)
        payload_text = build_invoice_qr_payload(data, payload_format=payload_format)

        raw_bytes = generate_invoice_qr(
            self,
            engine=engine,
            payload_format=payload_format,
            box_size=box_size,
            border=border,
            as_base64=False
        )

        filename = f"qr_{self.invoice_number or self.id}.png"
        self.qr_code_image.save(filename, ContentFile(raw_bytes), save=False)
        self.qr_code_payload = payload_text

        # Update fields in DB without recursive save
        Invoice.objects.filter(pk=self.pk).update(
            qr_code_image=self.qr_code_image.name,
            qr_code_payload=self.qr_code_payload
        )
        return self.qr_code_image

    def get_complete_details(self):
        """
        Fetch complete invoice details directly from this saved database model:
        - ID: Database primary key ID (id) and unique Invoice Number (invoice_number)
        - Customer Name: customer_name and customer_phone
        - Total: grand_total, subtotal, and tax_amount
        - Date: formatted string and datetime
        - Line items and QR payload
        """
        from .invoice_qr import fetch_invoice_data
        data = fetch_invoice_data(self)
        return {
            'id': self.id,
            'invoice_id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone or '',
            'total': float(self.grand_total) if self.grand_total is not None else 0.0,
            'total_amount': float(self.grand_total) if self.grand_total is not None else 0.0,
            'subtotal': float(self.subtotal) if self.subtotal is not None else 0.0,
            'tax_amount': float(self.tax_amount) if self.tax_amount is not None else 0.0,
            'discount': float(self.discount) if self.discount is not None else 0.0,
            'date': data.get('date'),
            'iso_date': data.get('iso_date'),
            'created_at': self.created_at,
            'payment_method': self.payment_method,
            'payment_status': self.payment_status,
            'items': data.get('items', []),
            'qr_payload': self.qr_code_payload or data.get('qr_payload'),
            'qr_code_base64': self.qr_code_base64,
        }

    def get_qr_data(self):
        """
        Fetch core data from this saved invoice model:
        - Invoice ID (id & invoice_number)
        - Customer Name (customer_name)
        - Total Amount (grand_total)
        - Date (created_at)
        """
        from .invoice_qr import fetch_invoice_data
        return fetch_invoice_data(self)

    def get_qr_text_payload(self):
        """Build structured text payload encoding the saved invoice values."""
        from .invoice_qr import build_invoice_qr_payload
        return build_invoice_qr_payload(self.get_qr_data(), payload_format='text')

    def get_qr_json_payload(self):
        """Build JSON payload encoding the saved invoice values."""
        from .invoice_qr import build_invoice_qr_payload
        return build_invoice_qr_payload(self.get_qr_data(), payload_format='json')

    def generate_qr_code(self, as_base64=True, engine='auto', payload_format='text', box_size=6, border=2):
        """
        Fetch values from this saved invoice model and generate a QR code image encoding them
        using 'qrcode' or 'segno'.
        """
        from .invoice_qr import generate_invoice_qr
        return generate_invoice_qr(
            self,
            engine=engine,
            payload_format=payload_format,
            box_size=box_size,
            border=border,
            as_base64=as_base64
        )

    @property
    def qr_code_base64(self):
        """
        Convenience property returning base64 Data URI for HTML template rendering.
        Reads directly from saved qr_code_image if available, or generates dynamically.
        """
        if self.qr_code_image:
            try:
                import base64
                with self.qr_code_image.open('rb') as f:
                    content = f.read()
                    if content:
                        b64 = base64.b64encode(content).decode('utf-8')
                        return f"data:image/png;base64,{b64}"
            except Exception:
                pass
        return self.generate_qr_code(as_base64=True)



class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True, related_name='invoice_items')
    product_name = models.CharField(max_length=150)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, help_text='Discount on item in INR')
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=18.00)
    total = models.DecimalField(max_digits=10, decimal_places=2)

    def __init__(self, *args, **kwargs):
        total_amount = kwargs.pop('total_amount', None)
        super().__init__(*args, **kwargs)
        if total_amount is not None:
            self.total = total_amount

    @property
    def total_amount(self):
        """Alias property for total."""
        return self.total

    @total_amount.setter
    def total_amount(self, value):
        self.total = value

    def save(self, *args, **kwargs):
        if self.total is None:
            from decimal import Decimal
            qty = Decimal(str(self.quantity or 1))
            price = Decimal(str(self.unit_price or '0.00'))
            disc = Decimal(str(self.discount or '0.00'))
            tax = Decimal(str(self.tax_rate or '0.00'))
            base = (price * qty) - disc
            self.total = (base + (base * (tax / Decimal('100.00')))).quantize(Decimal('0.01'))
        super().save(*args, **kwargs)

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
        from django.core.mail import send_mail
        
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
        
        # Send OTP email
        if user.email:
            try:
                subject = "Your Password Recovery OTP"
                message = f"Hello {user.get_full_name() or user.username},\n\nYour OTP for password recovery is: {random_code}\n\nThis OTP is valid for {validity_minutes} minutes.\n\nThank you,\nAdvance Billing System"
                send_mail(
                    subject,
                    message,
                    'noreply@advancebilling.com',
                    [user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Failed to send email to {user.email}: {e}")
                
        return token

    def __str__(self):
        status = "Verified" if self.is_verified else ("Valid" if self.is_valid() else "Expired")
        return f"OTP {self.otp_code} for {self.user.username} ({status})"


from django.db.models.signals import post_save
from django.dispatch import receiver

@receiver(post_save, sender=User)
def ensure_user_profile_exists(sender, instance, created, **kwargs):
    """Ensure every User has a matching UserProfile."""
    if created:
        UserProfile.objects.get_or_create(
            user=instance,
            defaults={
                'role': 'ADMIN' if instance.is_superuser else 'DISTRIBUTOR',
                'business_name': instance.get_full_name() or instance.username,
                'upi_id': 'merchant@upi'
            }
        )


