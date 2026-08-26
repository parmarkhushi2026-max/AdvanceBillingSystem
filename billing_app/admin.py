from django.contrib import admin
from .models import UserProfile, Product, Invoice, InvoiceItem, OTPToken, Customer

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone', 'email', 'city', 'gstin', 'created_by', 'created_at')
    list_filter = ('created_at', 'city')
    search_fields = ('name', 'phone', 'email', 'gstin')

@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('invoice_number', 'distributor', 'customer_name', 'grand_total', 'payment_status', 'created_at')
    list_filter = ('payment_status', 'created_at')
    search_fields = ('invoice_number', 'customer_name', 'customer_phone')
    inlines = [InvoiceItemInline]

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


