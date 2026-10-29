import random
from decimal import Decimal
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User
from billing_app.models import Customer, Invoice, InvoiceItem, Product, UserProfile


class Command(BaseCommand):
    help = "Perform manual-style database entries for Customers, Invoices, and InvoiceItems as done via Django Admin."

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=3,
            help='Number of manual invoice entries to generate (default: 3).'
        )

    def handle(self, *args, **options):
        count = options.get('count', 3)
        self.stdout.write(self.style.MIGRATE_HEADING("Creating manual entries as performed via Django Admin..."))

        # 1. Ensure Admin and Distributor users exist
        admin_user = User.objects.filter(is_superuser=True).first()
        if not admin_user:
            admin_user = User.objects.create_superuser('admin', 'admin@advancebilling.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=admin_user,
                defaults={'role': 'ADMIN', 'business_name': 'Advance Billing HQ', 'phone': '9876543210'}
            )

        dist_user = User.objects.filter(username='distributor').first() or admin_user

        # 2. Manual Customer Entries
        customers_data = [
            {
                'name': 'Gajanan Electricals & Electronics',
                'phone': '9822334455',
                'email': 'gajanan.elec@example.com',
                'address': 'Plot 44, GIDC Phase 2',
                'city': 'Surat',
                'gstin': '24AABCG1234F1Z1',
            },
            {
                'name': 'Shreeji Mega Mart & Provisions',
                'phone': '9877112233',
                'email': 'shreeji.mart@example.com',
                'address': 'Shop 12, Golden Arcade',
                'city': 'Vadodara',
                'gstin': '24AAECS9876K1Z8',
            },
            {
                'name': 'Navkar Healthcare & Surgical Supplies',
                'phone': '9899334411',
                'email': 'navkar.health@example.com',
                'address': '104 Apollo Enclave, Ring Road',
                'city': 'Ahmedabad',
                'gstin': '24AAYPN4567P1ZA',
            },
        ]

        created_customers = []
        for cdata in customers_data:
            cust, created = Customer.objects.get_or_create(
                phone=cdata['phone'],
                defaults={
                    'name': cdata['name'],
                    'email': cdata['email'],
                    'address': cdata['address'],
                    'city': cdata['city'],
                    'gstin': cdata['gstin'],
                    'created_by': dist_user
                }
            )
            created_customers.append(cust)
            status_text = "Created" if created else "Found"
            self.stdout.write(f"  [{status_text} Customer] {cust.name} ({cust.phone}) - {cust.city}")

        # 3. Ensure Products exist
        sample_products = [
            ('Wireless Barcode Scanner Pro', 'HW-SCN-01', Decimal('2499.00'), Decimal('18.00')),
            ('Thermal Receipt Printer 80mm', 'HW-PRN-80', Decimal('4899.00'), Decimal('18.00')),
            ('Advance POS Touch Terminal', 'HW-POS-T1', Decimal('18500.00'), Decimal('18.00')),
            ('Thermal Paper Rolls (Box of 50)', 'CS-ROL-50', Decimal('800.00'), Decimal('18.00')),
            ('Billing Software Annual License', 'SW-BIL-YR', Decimal('5999.00'), Decimal('18.00')),
        ]
        db_products = []
        for name, sku, price, gst in sample_products:
            p, _ = Product.objects.get_or_create(
                sku=sku,
                defaults={'name': name, 'price': price, 'gst_rate': gst, 'stock': 100, 'created_by': admin_user}
            )
            db_products.append(p)

        # 4. Create Manual Invoices with Inlined Items
        base_num = Invoice.objects.count() + 101
        created_invoices = []

        now = timezone.now()
        for i in range(count):
            inv_num = f"INV-ADM-{now.year}-{base_num + i:04d}"
            target_cust = created_customers[i % len(created_customers)]
            
            # Select 1 or 2 products
            p1 = db_products[i % len(db_products)]
            p2 = db_products[(i + 1) % len(db_products)]

            qty1 = (i % 3) + 1
            qty2 = 1

            line1_base = p1.price * qty1
            line1_tax = line1_base * (p1.gst_rate / Decimal('100.00'))
            line1_total = line1_base + line1_tax

            line2_base = p2.price * qty2
            line2_tax = line2_base * (p2.gst_rate / Decimal('100.00'))
            line2_total = line2_base + line2_tax

            inv_subtotal = (line1_base + line2_base).quantize(Decimal('0.01'))
            inv_tax = (line1_tax + line2_tax).quantize(Decimal('0.01'))
            inv_grand_total = (line1_total + line2_total).quantize(Decimal('0.01'))

            invoice, created = Invoice.objects.get_or_create(
                invoice_number=inv_num,
                defaults={
                    'customer': target_cust,
                    'customer_name': target_cust.name,
                    'customer_phone': target_cust.phone,
                    'distributor': dist_user,
                    'subtotal': inv_subtotal,
                    'tax_amount': inv_tax,
                    'grand_total': inv_grand_total,
                    'payment_status': 'PAID',
                    'payment_method': 'UPI QR Code',
                    'notes': f'Manual invoice entry created via Django Admin interface.'
                }
            )

            # Inlined Items
            InvoiceItem.objects.get_or_create(
                invoice=invoice,
                product=p1,
                defaults={
                    'product_name': p1.name,
                    'quantity': qty1,
                    'unit_price': p1.price,
                    'tax_rate': p1.gst_rate,
                    'total': line1_total.quantize(Decimal('0.01'))
                }
            )
            InvoiceItem.objects.get_or_create(
                invoice=invoice,
                product=p2,
                defaults={
                    'product_name': p2.name,
                    'quantity': qty2,
                    'unit_price': p2.price,
                    'tax_rate': p2.gst_rate,
                    'total': line2_total.quantize(Decimal('0.01'))
                }
            )

            # Generate QR code for invoice
            invoice.generate_and_save_qr()
            created_invoices.append(invoice)

            self.stdout.write(
                self.style.SUCCESS(
                    f"  ✅ [Manual Invoice Entry #{invoice.id}] {invoice.invoice_number} | "
                    f"Customer: {invoice.customer_name} | Total: ₹{invoice.grand_total} | Items: 2 | QR: Verified"
                )
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully recorded {len(created_invoices)} manual entries in database via Django Admin format."
            )
        )

