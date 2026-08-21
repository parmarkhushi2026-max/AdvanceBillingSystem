from django.contrib import admin
from .models import UserProfile, Product, Invoice, InvoiceItem

class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 0

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
    list_display = ('name', 'category', 'price', 'tax_rate', 'stock')
    list_filter = ('category',)
    search_fields = ('name',)
