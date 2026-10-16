import sys
from decimal import Decimal
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from .models import UserProfile, Product, Customer, Invoice, InvoiceItem


def ensure_invoice_data_exists(skip_in_test=False):
    """
    Ensure that representative invoice records exist in the database with:
    - Invoice ID / Unique Invoice Number
    - Customer Name and Phone
    - Grand Total (Total Amount)
    - Invoice Date / Timestamp
    - Associated Line Items and Customer Foreign Keys
    """
    if skip_in_test and ('test' in sys.argv):
        return 0

    if Invoice.objects.exists():
        return Invoice.objects.count()

    # 1. Ensure Distributor exists
    dist_user = User.objects.filter(username='distributor').first()
    if not dist_user:
        dist_user = User.objects.create_user('distributor', 'distributor@agency.com', 'dist123')
        dist_user.first_name = 'Rahul'
        dist_user.last_name = 'Sharma'
        dist_user.save()
    UserProfile.objects.get_or_create(
        user=dist_user,
        defaults={
            'role': 'DISTRIBUTOR',
            'business_name': 'Sharma Tech & Retail Distribution',
            'phone': '+91 98123 45678',
            'upi_id': 'sharmadist@upi'
        }
    )

    # 2. Ensure Sample Customers exist
    cust1, _ = Customer.objects.get_or_create(
        phone='9876543210',
        defaults={'name': 'Pooja Electronics & Retail', 'city': 'Ahmedabad', 'created_by': dist_user}
    )
    cust2, _ = Customer.objects.get_or_create(
        phone='9812345678',
        defaults={'name': 'Rajesh General Stores', 'city': 'Mumbai', 'created_by': dist_user}
    )
    cust3, _ = Customer.objects.get_or_create(
        phone='9899001122',
        defaults={'name': 'Anil Medical & Diagnostics', 'city': 'Surat', 'created_by': dist_user}
    )
    cust4, _ = Customer.objects.get_or_create(
        phone='9888877777',
        defaults={'name': 'Modern Stationery Hub', 'city': 'Vadodara', 'created_by': dist_user}
    )

    # 3. Ensure Sample Products exist
    prod1, _ = Product.objects.get_or_create(
        sku='HW-POS-03',
        defaults={
            'name': 'Advance POS Touch Terminal',
            'category': 'Hardware',
            'price': Decimal('18500.00'),
            'gst_rate': Decimal('18.00'),
            'stock': 25,
            'unit': 'Pcs',
            'created_by': dist_user
        }
    )
    prod2, _ = Product.objects.get_or_create(
        sku='HW-PRN-02',
        defaults={
            'name': 'Thermal Receipt Printer 80mm',
            'category': 'Hardware',
            'price': Decimal('4890.00'),
            'gst_rate': Decimal('18.00'),
            'stock': 40,
            'unit': 'Pcs',
            'created_by': dist_user
        }
    )
    prod3, _ = Product.objects.get_or_create(
        sku='SW-LIC-01',
        defaults={
            'name': 'Billing Software Annual License',
            'category': 'Software',
            'price': Decimal('5999.00'),
            'gst_rate': Decimal('18.00'),
            'stock': 999,
            'unit': 'License',
            'created_by': dist_user
        }
    )
    prod4, _ = Product.objects.get_or_create(
        sku='HW-SCN-01',
        defaults={
            'name': 'Wireless Barcode Scanner Pro',
            'category': 'Hardware',
            'price': Decimal('2499.00'),
            'gst_rate': Decimal('18.00'),
            'stock': 50,
            'unit': 'Pcs',
            'created_by': dist_user
        }
    )
    prod5, _ = Product.objects.get_or_create(
        sku='SUP-PAP-01',
        defaults={
            'name': 'Thermal Paper Rolls (Box of 50)',
            'category': 'Supplies',
            'price': Decimal('850.00'),
            'gst_rate': Decimal('12.00'),
            'stock': 200,
            'unit': 'Box',
            'created_by': dist_user
        }
    )

    now = timezone.now()

    sample_invoices = [
        {
            'number': 'INV-2026-001',
            'customer': cust1,
            'name': 'Pooja Electronics & Retail',
            'phone': '9876543210',
            'items': [
                {'product': prod1, 'name': prod1.name, 'qty': 1, 'price': Decimal('18500.00'), 'tax': Decimal('18.00')},
                {'product': prod5, 'name': prod5.name, 'qty': 2, 'price': Decimal('850.00'), 'tax': Decimal('12.00')}
            ],
            'subtotal': Decimal('20200.00'),
            'tax_amount': Decimal('3534.00'),
            'discount': Decimal('500.00'),
            'grand_total': Decimal('23234.00'),
            'status': 'PAID',
            'method': 'UPI QR Code',
            'notes': 'POS Terminal bundle setup for retail counter',
            'days_ago': 10
        },
        {
            'number': 'INV-2026-002',
            'customer': cust2,
            'name': 'Rajesh General Stores',
            'phone': '9812345678',
            'items': [
                {'product': prod2, 'name': prod2.name, 'qty': 1, 'price': Decimal('4890.00'), 'tax': Decimal('18.00')},
                {'product': prod5, 'name': prod5.name, 'qty': 1, 'price': Decimal('850.00'), 'tax': Decimal('12.00')}
            ],
            'subtotal': Decimal('5740.00'),
            'tax_amount': Decimal('982.20'),
            'discount': Decimal('100.00'),
            'grand_total': Decimal('6622.20'),
            'status': 'PAID',
            'method': 'UPI QR Code',
            'notes': 'Thermal receipt printer and roll supply',
            'days_ago': 7
        },
        {
            'number': 'INV-2026-003',
            'customer': cust3,
            'name': 'Anil Medical & Diagnostics',
            'phone': '9899001122',
            'items': [
                {'product': prod3, 'name': prod3.name, 'qty': 1, 'price': Decimal('5999.00'), 'tax': Decimal('18.00')}
            ],
            'subtotal': Decimal('5999.00'),
            'tax_amount': Decimal('1079.82'),
            'discount': Decimal('200.00'),
            'grand_total': Decimal('6878.82'),
            'status': 'PAID',
            'method': 'Net Banking',
            'notes': 'Advance Billing Software 1-Year License',
            'days_ago': 4
        },
        {
            'number': 'INV-2026-004',
            'customer': cust4,
            'name': 'Modern Stationery Hub',
            'phone': '9888877777',
            'items': [
                {'product': prod4, 'name': prod4.name, 'qty': 2, 'price': Decimal('2499.00'), 'tax': Decimal('18.00')}
            ],
            'subtotal': Decimal('4998.00'),
            'tax_amount': Decimal('899.64'),
            'discount': Decimal('0.00'),
            'grand_total': Decimal('5897.64'),
            'status': 'PAID',
            'method': 'Cash',
            'notes': 'Barcode scanners for inventory checkout',
            'days_ago': 2
        },
        {
            'number': 'INV-2026-005',
            'customer': None,
            'name': 'Walk-in Customer (Apex Mart)',
            'phone': '9800011223',
            'items': [
                {'product': prod5, 'name': prod5.name, 'qty': 5, 'price': Decimal('850.00'), 'tax': Decimal('12.00')}
            ],
            'subtotal': Decimal('4250.00'),
            'tax_amount': Decimal('510.00'),
            'discount': Decimal('0.00'),
            'grand_total': Decimal('4760.00'),
            'status': 'PAID',
            'method': 'UPI QR Code',
            'notes': 'Direct walk-in thermal roll purchase',
            'days_ago': 1
        },
        {
            'number': 'INV-2026-006',
            'customer': cust1,
            'name': 'Pooja Electronics & Retail',
            'phone': '9876543210',
            'items': [
                {'product': prod3, 'name': prod3.name, 'qty': 1, 'price': Decimal('5999.00'), 'tax': Decimal('18.00')},
                {'product': prod2, 'name': prod2.name, 'qty': 1, 'price': Decimal('4890.00'), 'tax': Decimal('18.00')}
            ],
            'subtotal': Decimal('10889.00'),
            'tax_amount': Decimal('1960.02'),
            'discount': Decimal('300.00'),
            'grand_total': Decimal('12549.02'),
            'status': 'PAID',
            'method': 'UPI QR Code',
            'notes': 'Additional counter terminal and software upgrade',
            'days_ago': 0
        }
    ]

    created_count = 0
    for data in sample_invoices:
        inv = Invoice.objects.create(
            invoice_number=data['number'],
            distributor=dist_user,
            customer=data['customer'],
            customer_ref=data['customer'],
            customer_name=data['name'],
            customer_phone=data['phone'],
            subtotal=data['subtotal'],
            tax_amount=data['tax_amount'],
            discount=data['discount'],
            grand_total=data['grand_total'],
            payment_status=data['status'],
            payment_method=data['method'],
            notes=data['notes']
        )
        # Update created_at timestamp to simulate historical dates
        custom_date = now - timedelta(days=data['days_ago'])
        Invoice.objects.filter(id=inv.id).update(created_at=custom_date)

        # Create Line Items
        for item in data['items']:
            item_total = (item['price'] * item['qty']) * Decimal('1.18')
            InvoiceItem.objects.create(
                invoice=inv,
                product=item['product'],
                product_name=item['name'],
                quantity=item['qty'],
                unit_price=item['price'],
                tax_rate=item['tax'],
                discount=Decimal('0.00'),
                total=round(item_total, 2)
            )
        created_count += 1

    return created_count
