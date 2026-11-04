from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from billing_app.models import (
    UserProfile,
    Distributor,
    Customer,
    Product,
    Invoice,
    InvoiceItem,
    OTPToken
)


class Command(BaseCommand):
    help = "Create and populate all necessary database tables (Distributor, Customer, Product, Invoice, InvoiceItem, UserProfile, OTPToken) required to perform system tasks."

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset and re-populate table data.'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== Setting up Necessary System Database Tables ==="))

        if options.get('reset'):
            self.stdout.write(self.style.WARNING("Reset flag provided. Purging existing transactional records..."))
            InvoiceItem.objects.all().delete()
            Invoice.objects.all().delete()
            Customer.objects.all().delete()
            Product.objects.all().delete()
            Distributor.objects.all().delete()

        # -------------------------------------------------------------
        # 1. System Admin User & UserProfile
        # -------------------------------------------------------------
        admin_user, created_admin = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@advancebilling.com',
                'first_name': 'System',
                'last_name': 'Administrator',
                'is_staff': True,
                'is_superuser': True,
            }
        )
        if created_admin:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(self.style.SUCCESS("✔ Created Superuser 'admin' (password: admin123)"))
        else:
            if not admin_user.is_superuser:
                admin_user.is_superuser = True
                admin_user.is_staff = True
                admin_user.save()

        admin_profile, _ = UserProfile.objects.get_or_create(
            user=admin_user,
            defaults={
                'role': 'ADMIN',
                'business_name': 'Advance Billing Central HQ',
                'phone': '+91 98000 00001',
                'upi_id': 'advancebilling@okaxis'
            }
        )
        if admin_profile.role != 'ADMIN':
            admin_profile.role = 'ADMIN'
            admin_profile.save()

        # -------------------------------------------------------------
        # 2. Distributor User & Distributor Master Records
        # -------------------------------------------------------------
        dist_user, created_dist = User.objects.get_or_create(
            username='distributor',
            defaults={
                'email': 'rahul@distributor.com',
                'first_name': 'Rahul',
                'last_name': 'Sharma',
            }
        )
        if created_dist:
            dist_user.set_password('dist123')
            dist_user.save()
            self.stdout.write(self.style.SUCCESS("✔ Created Distributor User 'distributor' (password: dist123)"))

        dist_profile, _ = UserProfile.objects.get_or_create(
            user=dist_user,
            defaults={
                'role': 'DISTRIBUTOR',
                'business_name': 'Sharma Tech Distribution Hub',
                'phone': '+91 98111 22233',
                'upi_id': 'sharmadist@upi'
            }
        )

        dist1, _ = Distributor.objects.get_or_create(
            business_name='Sharma Tech Distribution Hub',
            defaults={
                'user': dist_user,
                'name': 'Rahul Sharma',
                'phone': '+91 98111 22233',
                'email': 'rahul@sharmaagency.in',
                'address': 'Shop 104, IT Trade Complex, CG Road',
                'city': 'Ahmedabad',
                'state': 'Gujarat',
                'pincode': '380009',
                'gstin': '24AAECS1111F1Z1',
                'upi_id': 'sharmadist@upi',
                'is_active': True
            }
        )
        if dist1.user != dist_user:
            dist1.user = dist_user
            dist1.save()

        # Distributor 2
        dist2_user, _ = User.objects.get_or_create(
            username='patel_distributor',
            defaults={
                'email': 'priya@patelenterprises.in',
                'first_name': 'Priya',
                'last_name': 'Patel'
            }
        )
        if _:
            dist2_user.set_password('dist123')
            dist2_user.save()

        dist2, _ = Distributor.objects.get_or_create(
            business_name='Patel Wholesale & Distribution',
            defaults={
                'user': dist2_user,
                'name': 'Priya Patel',
                'phone': '+91 98222 33344',
                'email': 'priya@patelenterprises.in',
                'address': '201 Diamond World, Ring Road',
                'city': 'Surat',
                'state': 'Gujarat',
                'pincode': '395002',
                'gstin': '24AABCP2222K1Z2',
                'upi_id': 'pateldist@upi',
                'is_active': True
            }
        )

        # -------------------------------------------------------------
        # 3. Product Catalog Table Data
        # -------------------------------------------------------------
        products_data = [
            {
                'name': 'Smart POS Thermal Billing Register X-500',
                'sku': 'POS-TR-500',
                'category': 'Hardware',
                'price': Decimal('16500.00'),
                'stock': 45,
                'unit': 'Pcs',
                'hsn_code': '8470',
                'gst_rate': Decimal('18.00'),
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'High-Speed Wireless 2D QR Barcode Scanner',
                'sku': 'SCN-QR-2D',
                'category': 'Hardware',
                'price': Decimal('3200.00'),
                'stock': 80,
                'unit': 'Pcs',
                'hsn_code': '8471',
                'gst_rate': Decimal('18.00'),
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'Thermal Receipt Paper Rolls 80mm (Pack of 50)',
                'sku': 'ROLL-80MM-50',
                'category': 'Consumables',
                'price': Decimal('850.00'),
                'stock': 250,
                'unit': 'Box',
                'hsn_code': '4811',
                'gst_rate': Decimal('12.00'),
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'Heavy Duty 5-Slot Electronic Cash Drawer',
                'sku': 'CSH-DRW-HD',
                'category': 'Hardware',
                'price': Decimal('2800.00'),
                'stock': 35,
                'unit': 'Pcs',
                'hsn_code': '8303',
                'gst_rate': Decimal('18.00'),
                'created_by': dist2_user,
                'distributor_ref': dist2
            },
            {
                'name': 'Barcode Label Sticker Rolls 50x25mm (1000 Labels)',
                'sku': 'LBL-50X25-1K',
                'category': 'Consumables',
                'price': Decimal('220.00'),
                'stock': 300,
                'unit': 'Rolls',
                'hsn_code': '4821',
                'gst_rate': Decimal('12.00'),
                'created_by': dist2_user,
                'distributor_ref': dist2
            },
        ]

        for pdata in products_data:
            Product.objects.get_or_create(
                sku=pdata['sku'],
                defaults=pdata
            )

        # -------------------------------------------------------------
        # 4. Customer Table Data
        # -------------------------------------------------------------
        customers_data = [
            {
                'name': 'Gajanan Electricals & Electronics',
                'phone': '9822334455',
                'email': 'gajanan.elec@example.com',
                'address': 'Plot 44, GIDC Phase 2',
                'city': 'Surat',
                'gstin': '24AABCG1234F1Z1',
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'Shreeji Mega Mart & Provisions',
                'phone': '9877112233',
                'email': 'shreeji.mart@example.com',
                'address': 'Shop 12, Golden Arcade',
                'city': 'Vadodara',
                'gstin': '24AAECS9876K1Z8',
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'Navkar Healthcare & Surgical Supplies',
                'phone': '9899334411',
                'email': 'navkar.health@example.com',
                'address': '104 Apollo Enclave, Ring Road',
                'city': 'Ahmedabad',
                'gstin': '24AAYPN4567P1ZA',
                'created_by': dist_user,
                'distributor_ref': dist1
            },
            {
                'name': 'Royal Supermarket & Retailers',
                'phone': '9844556677',
                'email': 'royal.super@example.com',
                'address': '78 High Street Market',
                'city': 'Rajkot',
                'gstin': '24AAECR3344J1Z9',
                'created_by': dist2_user,
                'distributor_ref': dist2
            },
        ]

        created_customers = []
        for cdata in customers_data:
            cust, _ = Customer.objects.get_or_create(
                phone=cdata['phone'],
                defaults=cdata
            )
            created_customers.append(cust)

        # -------------------------------------------------------------
        # 5. Invoice & InvoiceItem Table Data
        # -------------------------------------------------------------
        invoices_data = [
            {
                'invoice_number': 'INV-2026-NEC-001',
                'customer': created_customers[0],
                'distributor': dist_user,
                'distributor_ref': dist1,
                'customer_name': created_customers[0].name,
                'customer_phone': created_customers[0].phone,
                'payment_status': 'PAID',
                'payment_method': 'UPI QR Code',
                'subtotal': Decimal('16500.00'),
                'tax_amount': Decimal('2970.00'),
                'discount': Decimal('0.00'),
                'grand_total': Decimal('19470.00'),
                'items': [
                    {
                        'product_name': 'Smart POS Thermal Billing Register X-500',
                        'quantity': 1,
                        'unit_price': Decimal('16500.00'),
                        'tax_rate': Decimal('18.00'),
                        'discount': Decimal('0.00'),
                        'total': Decimal('19470.00')
                    }
                ]
            },
            {
                'invoice_number': 'INV-2026-NEC-002',
                'customer': created_customers[1],
                'distributor': dist_user,
                'distributor_ref': dist1,
                'customer_name': created_customers[1].name,
                'customer_phone': created_customers[1].phone,
                'payment_status': 'PAID',
                'payment_method': 'UPI QR Code',
                'subtotal': Decimal('4900.00'),
                'tax_amount': Decimal('780.00'),
                'discount': Decimal('100.00'),
                'grand_total': Decimal('5580.00'),
                'items': [
                    {
                        'product_name': 'High-Speed Wireless 2D QR Barcode Scanner',
                        'quantity': 1,
                        'unit_price': Decimal('3200.00'),
                        'tax_rate': Decimal('18.00'),
                        'discount': Decimal('100.00'),
                        'total': Decimal('3658.00')
                    },
                    {
                        'product_name': 'Thermal Receipt Paper Rolls 80mm (Pack of 50)',
                        'quantity': 2,
                        'unit_price': Decimal('850.00'),
                        'tax_rate': Decimal('12.00'),
                        'discount': Decimal('0.00'),
                        'total': Decimal('1904.00')
                    }
                ]
            },
            {
                'invoice_number': 'INV-2026-NEC-003',
                'customer': created_customers[2],
                'distributor': dist_user,
                'distributor_ref': dist1,
                'customer_name': created_customers[2].name,
                'customer_phone': created_customers[2].phone,
                'payment_status': 'PENDING',
                'payment_method': 'UPI QR Code',
                'subtotal': Decimal('2550.00'),
                'tax_amount': Decimal('306.00'),
                'discount': Decimal('0.00'),
                'grand_total': Decimal('2856.00'),
                'items': [
                    {
                        'product_name': 'Thermal Receipt Paper Rolls 80mm (Pack of 50)',
                        'quantity': 3,
                        'unit_price': Decimal('850.00'),
                        'tax_rate': Decimal('12.00'),
                        'discount': Decimal('0.00'),
                        'total': Decimal('2856.00')
                    }
                ]
            },
            {
                'invoice_number': 'INV-2026-NEC-004',
                'customer': created_customers[3],
                'distributor': dist2_user,
                'distributor_ref': dist2,
                'customer_name': created_customers[3].name,
                'customer_phone': created_customers[3].phone,
                'payment_status': 'PAID',
                'payment_method': 'UPI QR Code',
                'subtotal': Decimal('3460.00'),
                'tax_amount': Decimal('583.20'),
                'discount': Decimal('0.00'),
                'grand_total': Decimal('4043.20'),
                'items': [
                    {
                        'product_name': 'Heavy Duty 5-Slot Electronic Cash Drawer',
                        'quantity': 1,
                        'unit_price': Decimal('2800.00'),
                        'tax_rate': Decimal('18.00'),
                        'discount': Decimal('0.00'),
                        'total': Decimal('3304.00')
                    },
                    {
                        'product_name': 'Barcode Label Sticker Rolls 50x25mm (1000 Labels)',
                        'quantity': 3,
                        'unit_price': Decimal('220.00'),
                        'tax_rate': Decimal('12.00'),
                        'discount': Decimal('0.00'),
                        'total': Decimal('739.20')
                    }
                ]
            }
        ]

        for inv_data in invoices_data:
            items_list = inv_data.pop('items')
            inv, created_inv = Invoice.objects.get_or_create(
                invoice_number=inv_data['invoice_number'],
                defaults=inv_data
            )
            if created_inv:
                for itm in items_list:
                    prod = Product.objects.filter(name=itm['product_name']).first()
                    InvoiceItem.objects.create(
                        invoice=inv,
                        product=prod,
                        product_name=itm['product_name'],
                        quantity=itm['quantity'],
                        unit_price=itm['unit_price'],
                        tax_rate=itm['tax_rate'],
                        discount=itm['discount'],
                        total=itm['total']
                    )

        # Print Table Summary
        self.stdout.write(self.style.SUCCESS("\n✔ All Necessary Tables Successfully Initialized and Verified:"))
        self.stdout.write(f"  1. User & UserProfile (Total Users: {User.objects.count()}, Total Profiles: {UserProfile.objects.count()})")
        self.stdout.write(f"  2. Distributor Table  (Total Distributors: {Distributor.objects.count()})")
        self.stdout.write(f"  3. Customer Table     (Total Customers: {Customer.objects.count()})")
        self.stdout.write(f"  4. Product Table      (Total Products: {Product.objects.count()})")
        self.stdout.write(f"  5. Invoice Table      (Total Invoices: {Invoice.objects.count()})")
        self.stdout.write(f"  6. InvoiceItem Table  (Total Line Items: {InvoiceItem.objects.count()})")
        self.stdout.write(f"  7. OTPToken Table     (Total OTP Tokens: {OTPToken.objects.count()})")
        self.stdout.write(self.style.SUCCESS("=== Database Setup Completed Successfully ===\n"))

