from decimal import Decimal
from django.test import TestCase
from django.contrib import admin
from django.contrib.auth.models import User
from django.core.management import call_command
from django.db import connection
from billing_app.models import (
    UserProfile,
    Distributor,
    Customer,
    Product,
    Invoice,
    InvoiceItem,
    OTPToken
)


class NecessaryTablesTestCase(TestCase):
    """
    Comprehensive test suite verifying that all necessary tables required to perform
    billing, invoice generation, QR code creation, multi-tenant distributor isolation,
    customer directory, and admin management are properly created with robust relational
    foreign keys, constraint enforcement, and admin registration.
    """

    def setUp(self):
        # 1. Admin User
        self.admin_user = User.objects.create_superuser(
            username='tables_admin',
            email='admin@tables.com',
            password='AdminPass@123'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={'role': 'ADMIN', 'business_name': 'Central Billing Admin'}
        )

        # 2. Distributor User & Profile
        self.dist_user = User.objects.create_user(
            username='tables_distributor',
            email='dist@tables.com',
            password='DistPass@123'
        )
        self.dist_profile, _ = UserProfile.objects.get_or_create(
            user=self.dist_user,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Navkar Distributions', 'upi_id': 'navkar@upi'}
        )

        # 3. Distributor Table Record
        self.distributor = Distributor.objects.create(
            user=self.dist_user,
            name='Navkar Distributions',
            business_name='Navkar Distributions Pvt Ltd',
            phone='9812345678',
            email='navkar@dist.com',
            city='Ahmedabad',
            state='Gujarat',
            pincode='380015',
            gstin='24AABCN1234N1Z2',
            upi_id='navkar@upi',
            is_active=True
        )

        # 4. Customer Record
        self.customer = Customer.objects.create(
            name='Arihant Retail Store',
            email='arihant@retail.com',
            phone='9899887766',
            address='Shop 5, Navrang Complex',
            city='Ahmedabad',
            gstin='24AAACA9876K1Z9',
            created_by=self.dist_user,
            distributor_ref=self.distributor
        )

        # 5. Product Record
        self.product = Product.objects.create(
            name='Thermal POS Printer 80mm',
            sku='PRN-80MM-01',
            category='Hardware',
            price=Decimal('5500.00'),
            stock=60,
            unit='Pcs',
            hsn_code='8443',
            gst_rate=Decimal('18.00'),
            created_by=self.dist_user,
            distributor_ref=self.distributor
        )

        # 6. Invoice Record
        self.invoice = Invoice.objects.create(
            invoice_number='INV-TBL-2026-001',
            customer=self.customer,
            distributor=self.dist_user,
            distributor_ref=self.distributor,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
            subtotal=Decimal('5500.00'),
            tax_amount=Decimal('990.00'),
            discount=Decimal('0.00'),
            grand_total=Decimal('6490.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        # 7. InvoiceItem Record
        self.item = InvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=self.product.price,
            tax_rate=Decimal('18.00'),
            discount=Decimal('0.00'),
            total=Decimal('6490.00')
        )

        # 8. OTPToken Record
        self.otp = OTPToken.generate_otp_for_user(self.dist_user, validity_minutes=15)

    # -------------------------------------------------------------
    # 1. Table Existence in Database Schema
    # -------------------------------------------------------------
    def test_all_necessary_tables_exist_in_database_schema(self):
        """Verify all 7 necessary tables physically exist in the database."""
        table_names = connection.introspection.table_names()
        expected_tables = [
            'billing_app_userprofile',
            'billing_app_distributor',
            'billing_app_customer',
            'billing_app_product',
            'billing_app_invoice',
            'billing_app_invoiceitem',
            'billing_app_otptoken'
        ]
        for tbl in expected_tables:
            self.assertIn(
                tbl,
                table_names,
                f"Required database table '{tbl}' was not found in schema."
            )

    # -------------------------------------------------------------
    # 2. Relational Foreign Key Integrity Tests
    # -------------------------------------------------------------
    def test_relational_foreign_keys_and_bidirectional_access(self):
        """
        Verify bidirectional relational links:
        - Invoice <-> Customer
        - Invoice <-> Distributor
        - InvoiceItem <-> Invoice
        - InvoiceItem <-> Product
        - Customer <-> Distributor
        - Product <-> Distributor
        """
        # Invoice -> Customer & reverse
        self.assertEqual(self.invoice.customer, self.customer)
        self.assertIn(self.invoice, self.customer.invoices.all())

        # Invoice -> Distributor & reverse
        self.assertEqual(self.invoice.distributor_ref, self.distributor)
        self.assertIn(self.invoice, self.distributor.invoices.all())

        # InvoiceItem -> Invoice & reverse
        self.assertEqual(self.item.invoice, self.invoice)
        self.assertIn(self.item, self.invoice.items.all())

        # InvoiceItem -> Product
        self.assertEqual(self.item.product, self.product)
        self.assertEqual(self.item.product_name, 'Thermal POS Printer 80mm')

        # Customer -> Distributor & reverse
        self.assertEqual(self.customer.distributor_ref, self.distributor)
        self.assertIn(self.customer, self.distributor.customers.all())

        # Product -> Distributor & reverse
        self.assertEqual(self.product.distributor_ref, self.distributor)
        self.assertIn(self.product, self.distributor.products.all())

    # -------------------------------------------------------------
    # 3. Model Data Integrity & Calculations
    # -------------------------------------------------------------
    def test_distributor_and_invoice_financial_aggregations(self):
        """Distributor model correctly aggregates total invoices and total settled revenue from DB."""
        self.assertEqual(self.distributor.total_invoices, 1)
        self.assertEqual(self.distributor.total_revenue, Decimal('6490.00'))

    def test_invoice_qr_generation_on_necessary_table(self):
        """Invoice model auto-generates QR payload and image attributes."""
        self.assertIsNotNone(self.invoice.qr_code_payload)
        self.assertIn('INV-TBL-2026-001', self.invoice.qr_code_payload)
        self.assertIn('6490.00', self.invoice.qr_code_payload)
        self.assertIsNotNone(self.invoice.qr_code_base64)
        self.assertTrue(self.invoice.qr_code_base64.startswith('data:image/png;base64,'))

    def test_otp_token_table_generation_and_validation(self):
        """OTPToken table successfully stores 6-digit codes and checks validity."""
        self.assertEqual(len(self.otp.otp_code), 6)
        self.assertTrue(self.otp.is_valid())
        self.assertFalse(self.otp.is_verified)

    # -------------------------------------------------------------
    # 4. Django Admin Registration of All Tables
    # -------------------------------------------------------------
    def test_all_necessary_tables_registered_in_django_admin(self):
        """All 7 necessary tables must be registered in the Django Admin site registry."""
        registered_models = [model for model in admin.site._registry.keys()]
        self.assertIn(UserProfile, registered_models)
        self.assertIn(Distributor, registered_models)
        self.assertIn(Customer, registered_models)
        self.assertIn(Product, registered_models)
        self.assertIn(Invoice, registered_models)
        self.assertIn(InvoiceItem, registered_models)
        self.assertIn(OTPToken, registered_models)

    # -------------------------------------------------------------
    # 5. Setup Management Command Test
    # -------------------------------------------------------------
    def test_setup_necessary_tables_management_command(self):
        """Management command executes cleanly and populates necessary tables."""
        call_command('setup_necessary_tables')
        self.assertGreaterEqual(User.objects.count(), 2)
        self.assertGreaterEqual(Distributor.objects.count(), 2)
        self.assertGreaterEqual(Customer.objects.count(), 4)
        self.assertGreaterEqual(Product.objects.count(), 5)
        self.assertGreaterEqual(Invoice.objects.count(), 4)
        self.assertGreaterEqual(InvoiceItem.objects.count(), 4)
