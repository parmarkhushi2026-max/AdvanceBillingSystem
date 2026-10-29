from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from decimal import Decimal
from .models import UserProfile, Product, Invoice, InvoiceItem, OTPToken, Customer

admin.site.site_header = "Advance Billing System - Administration"
admin.site.site_title = "Advance Billing Admin Portal"
admin.site.index_title = "Billing & Financial Operations Management"


class InvoiceItemInline(admin.TabularInline):
    """Inline editor for Invoice Items within the Invoice Admin view."""
    model = InvoiceItem
    extra = 1
    fields = ('product', 'product_name', 'quantity', 'unit_price', 'tax_rate', 'discount', 'total')


class CustomerInvoiceInline(admin.TabularInline):
    """Inline view of customer invoices within Customer Admin."""
    model = Invoice
    fk_name = 'customer'
    extra = 0
    fields = ('invoice_number', 'grand_total', 'payment_status', 'payment_method', 'created_at')
    readonly_fields = ('invoice_number', 'grand_total', 'payment_status', 'payment_method', 'created_at')
    can_delete = False
    show_change_link = True


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'city', 'gstin', 'created_by', 'invoices_count', 'created_at')
    list_filter = ('created_at', 'city')
    search_fields = ('name', 'phone', 'email', 'gstin')
    ordering = ('-created_at',)
    inlines = [CustomerInvoiceInline]

    def invoices_count(self, obj):
        count = obj.invoices.count()
        return format_html('<b>{}</b> invoice(s)', count)
    invoices_count.short_description = "Invoices"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'invoice_number',
        'customer_link',
        'customer_name',
        'grand_total',
        'payment_status',
        'payment_method',
        'distributor',
        'has_qr',
        'created_at'
    )
    list_filter = ('payment_status', 'payment_method', 'created_at')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone', 'customer__name')
    readonly_fields = ('qr_code_image_preview', 'qr_code_payload', 'created_at')
    inlines = [InvoiceItemInline]
    ordering = ('-created_at',)

    fieldsets = (
        ('Invoice Identification', {
            'fields': ('invoice_number', 'distributor')
        }),
        ('Customer Association (FK)', {
            'fields': ('customer', 'customer_name', 'customer_phone'),
            'description': 'Select a registered customer. Customer Name and Phone will auto-fill from the selected Customer if left blank.'
        }),
        ('Financial Breakdown', {
            'fields': ('subtotal', 'tax_amount', 'discount', 'grand_total'),
            'description': 'Enter amounts directly or let inline items auto-calculate the total.'
        }),
        ('Payment & Status', {
            'fields': ('payment_status', 'payment_method', 'notes')
        }),
        ('Verified Dynamic QR Artifacts', {
            'classes': ('collapse',),
            'fields': ('qr_code_image_preview', 'qr_code_payload', 'created_at')
        }),
    )

    def customer_link(self, obj):
        if obj.customer:
            return format_html('<a href="/django-admin/billing_app/customer/{}/change/">{}</a>', obj.customer.id, obj.customer.name)
        return obj.customer_name or "—"
    customer_link.short_description = "Customer (FK)"

    def has_qr(self, obj):
        if obj.qr_code_image or obj.qr_code_payload:
            return mark_safe('<span style="color: #10b981; font-weight: bold;">✔ Active</span>')
        return mark_safe('<span style="color: #94a3b8;">—</span>')
    has_qr.short_description = "QR Code"

    def qr_code_image_preview(self, obj):
        if obj.qr_code_base64:
            return format_html('<img src="{}" style="max-width: 180px; height: auto; border: 1px solid #cbd5e1; border-radius: 8px; padding: 4px; background: #fff;" />', obj.qr_code_base64)
        return "No QR code generated yet."
    qr_code_image_preview.short_description = "QR Code Preview"

    def save_model(self, request, obj, form, change):
        # Auto-fill customer details from selected Customer model
        if obj.customer:
            if not obj.customer_name:
                obj.customer_name = obj.customer.name
            if not obj.customer_phone:
                obj.customer_phone = obj.customer.phone
        if not obj.distributor and request.user.is_authenticated:
            obj.distributor = request.user
        super().save_model(request, obj, form, change)

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        # Recalculate invoice totals from saved inline items if items exist
        invoice = form.instance
        items = invoice.items.all()
        if items.exists():
            computed_subtotal = Decimal('0.00')
            computed_tax = Decimal('0.00')
            computed_grand_total = Decimal('0.00')

            for item in items:
                qty = Decimal(str(item.quantity or 1))
                price = Decimal(str(item.unit_price or '0.00'))
                disc = Decimal(str(item.discount or '0.00'))
                tax_rate = Decimal(str(item.tax_rate or '0.00'))
                line_base = (price * qty) - disc
                line_tax = line_base * (tax_rate / Decimal('100.00'))
                line_total = line_base + line_tax

                computed_subtotal += line_base
                computed_tax += line_tax
                computed_grand_total += line_total

            # Update invoice totals if not manually overridden
            invoice.subtotal = computed_subtotal.quantize(Decimal('0.01'))
            invoice.tax_amount = computed_tax.quantize(Decimal('0.01'))
            invoice.grand_total = computed_grand_total.quantize(Decimal('0.01'))
            invoice.save(skip_qr_generation=False)


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'product_name', 'quantity', 'unit_price', 'tax_rate', 'discount', 'total')
    list_filter = ('tax_rate', 'invoice__payment_status')
    search_fields = ('invoice__invoice_number', 'product_name')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'business_name', 'phone', 'upi_id')
    list_filter = ('role',)
    search_fields = ('user__username', 'business_name', 'upi_id')


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'sku', 'category', 'price', 'gst_rate', 'hsn_code', 'stock', 'unit', 'created_by')
    list_filter = ('category', 'gst_rate', 'created_at')
    search_fields = ('name', 'sku', 'hsn_code')


@admin.register(OTPToken)
class OTPTokenAdmin(admin.ModelAdmin):
    list_display = ('otp_code', 'user', 'is_verified', 'created_at', 'expires_at')
    list_filter = ('is_verified', 'created_at')
    search_fields = ('otp_code', 'user__username')



