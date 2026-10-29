from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from billing_app.models import Customer, Invoice, InvoiceItem, Product


class ModelsStructureTestCase(TestCase):
    """
    Test suite verifying the necessary models and fields requested:
    - Customer: name, email, phone, address, city, gstin, created_at
    - Invoice: invoice ID, customer (FK), total amount, date, line items
    - InvoiceItem: invoice (FK), product (FK), quantity, unit price, total amount
    """

    def setUp(self):
        self.user = User.objects.create_user(username='dist_user', password='password123')
        
        # 1. Create Customer
        self.customer = Customer.objects.create(
            name='Ramesh Sharma & Sons',
            email='ramesh@example.com',
            phone='9876543210',
            address='102 Market Lane',
            city='Ahmedabad',
            gstin='24AAACR1234M1Z5',
            created_by=self.user
        )

        # 2. Create Product
        self.product = Product.objects.create(
            name='POS Thermal Printer',
            price=Decimal('4500.00'),
            stock=50,
            gst_rate=Decimal('18.00'),
            created_by=self.user
        )

    def test_customer_model_fields(self):
        """Verify Customer model exists and possesses all necessary customer fields."""
        self.assertEqual(self.customer.name, 'Ramesh Sharma & Sons')
        self.assertEqual(self.customer.email, 'ramesh@example.com')
        self.assertEqual(self.customer.phone, '9876543210')
        self.assertEqual(self.customer.address, '102 Market Lane')
        self.assertEqual(self.customer.city, 'Ahmedabad')
        self.assertEqual(self.customer.gstin, '24AAACR1234M1Z5')
        self.assertIsNotNone(self.customer.created_at)
        self.assertIn('Ramesh Sharma & Sons', str(self.customer))

    def test_invoice_model_fields_and_customer_foreign_key(self):
        """
        Verify Invoice model possesses:
        - invoice ID (id, invoice_id, invoice_number)
        - customer (ForeignKey to Customer model)
        - total amount (grand_total, total_amount)
        - date (created_at, date)
        """
        invoice = Invoice.objects.create(
            invoice_number='INV-TEST-2026-001',
            customer=self.customer,
            distributor=self.user,
            total_amount=Decimal('5310.00'),
            subtotal=Decimal('4500.00'),
            tax_amount=Decimal('810.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        # 1. Invoice ID
        self.assertIsNotNone(invoice.id)
        self.assertEqual(invoice.invoice_id, invoice.id)
        self.assertEqual(invoice.invoice_number, 'INV-TEST-2026-001')

        # 2. Customer Foreign Key (FK)
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.customer.id, self.customer.id)
        self.assertEqual(invoice.customer_name, 'Ramesh Sharma & Sons')
        self.assertEqual(invoice.customer_phone, '9876543210')

        # Reverse relation: Customer -> Invoices
        self.assertIn(invoice, self.customer.invoices.all())

        # 3. Total Amount
        self.assertEqual(invoice.total_amount, Decimal('5310.00'))
        self.assertEqual(invoice.grand_total, Decimal('5310.00'))

        # 4. Date
        self.assertIsNotNone(invoice.date)
        self.assertEqual(invoice.date, invoice.created_at)

    def test_invoice_item_model_fields_and_foreign_keys(self):
        """
        Verify InvoiceItem model possesses:
        - invoice (ForeignKey to Invoice model)
        - product (ForeignKey to Product model)
        - quantity, unit_price, total / total_amount
        """
        invoice = Invoice.objects.create(
            invoice_number='INV-TEST-2026-002',
            customer=self.customer,
            distributor=self.user,
            grand_total=Decimal('9000.00')
        )

        item = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            product_name=self.product.name,
            quantity=2,
            unit_price=self.product.price,
            tax_rate=Decimal('18.00'),
            total_amount=Decimal('10620.00')
        )

        # 1. Invoice Foreign Key
        self.assertEqual(item.invoice, invoice)
        self.assertIn(item, invoice.items.all())

        # 2. Product Foreign Key
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.product_name, 'POS Thermal Printer')

        # 3. Item numeric attributes
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal('4500.00'))
        self.assertEqual(item.total_amount, Decimal('10620.00'))
        self.assertEqual(item.total, Decimal('10620.00'))

    def test_auto_calculation_and_reverse_queries(self):
        """Verify adding multiple InvoiceItems and querying from customer through invoice."""
        invoice = Invoice.objects.create(
            invoice_number='INV-TEST-2026-003',
            customer=self.customer,
            distributor=self.user
        )

        item1 = InvoiceItem.objects.create(
            invoice=invoice,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=Decimal('100.00'),
            tax_rate=Decimal('18.00')
        )
        # Auto-calculated: 100 + 18% = 118.00
        self.assertEqual(item1.total, Decimal('118.00'))

        # Fetch customer invoices and their line items
        customer_invoices = self.customer.invoices.all()
        self.assertIn(invoice, customer_invoices)
        self.assertEqual(invoice.items.count(), 1)

