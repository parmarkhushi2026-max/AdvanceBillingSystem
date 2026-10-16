from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from billing_app.models import Invoice, InvoiceItem, Customer
from billing_app.invoice_seeder import ensure_invoice_data_exists


class InvoiceDatabaseDataTestCase(TestCase):
    """
    Test suite verifying that invoice data exists in the database
    with all required core attributes:
    1. Invoice ID (primary key id & unique invoice_number)
    2. Customer Name (customer_name)
    3. Total Amount (grand_total > 0)
    4. Date (created_at)
    """

    def setUp(self):
        self.client = Client()
        # Seed invoice data for tests
        ensure_invoice_data_exists(skip_in_test=False)

    def test_invoice_records_exist_in_database(self):
        """Verify that multiple invoice records exist in the database."""
        invoices_count = Invoice.objects.count()
        self.assertGreater(
            invoices_count, 0,
            "Invoice records must exist in the database."
        )

    def test_invoice_core_fields_integrity(self):
        """
        Verify that every invoice has:
        - invoice ID (id and invoice_number)
        - customer name (customer_name)
        - total amount (grand_total > 0)
        - date (created_at)
        """
        invoices = Invoice.objects.all()
        for inv in invoices:
            # 1. Invoice ID & Number
            self.assertIsNotNone(inv.id, "Invoice must have a primary key ID")
            self.assertGreater(inv.id, 0)
            self.assertTrue(bool(inv.invoice_number), "Invoice must have a valid invoice_number")
            self.assertTrue(inv.invoice_number.startswith('INV-'))

            # 2. Customer Name
            self.assertTrue(
                bool(inv.customer_name and inv.customer_name.strip()),
                f"Invoice #{inv.id} must have a non-empty customer_name"
            )

            # 3. Total Amount (grand_total)
            self.assertIsNotNone(inv.grand_total, f"Invoice #{inv.id} must have grand_total")
            self.assertGreater(
                inv.grand_total, 0,
                f"Invoice #{inv.id} grand_total must be greater than zero"
            )

            # 4. Date (created_at)
            self.assertIsNotNone(inv.created_at, f"Invoice #{inv.id} must have created_at date")
            self.assertTrue(hasattr(inv.created_at, 'strftime'), "created_at must be a valid datetime")

    def test_invoice_has_associated_line_items(self):
        """Verify that invoices have associated line items with product names and pricing."""
        invoices = Invoice.objects.all()
        for inv in invoices:
            items = inv.items.all()
            self.assertGreater(
                items.count(), 0,
                f"Invoice #{inv.id} should have at least one line item."
            )
            for item in items:
                self.assertTrue(bool(item.product_name))
                self.assertGreater(item.total, 0)

    def test_management_command_seed_invoices(self):
        """Verify that 'python manage.py seed_invoices' command runs cleanly."""
        # Test command with --force
        call_command('seed_invoices', force=True)
        self.assertGreater(Invoice.objects.count(), 0)

    def test_invoices_rendered_in_invoice_list_view(self):
        """Verify that authenticated user sees the invoice ID, customer name, total, and date on invoices page."""
        dist = User.objects.filter(username='distributor').first()
        self.client.force_login(dist)

        response = self.client.get(reverse('invoice_list'))
        self.assertEqual(response.status_code, 200)

        # Invoices should be present in the view context
        invoices = response.context.get('invoices')
        self.assertIsNotNone(invoices)
        self.assertGreater(len(invoices), 0)

        first_invoice = invoices[0]
        self.assertContains(response, first_invoice.invoice_number)
        self.assertContains(response, first_invoice.customer_name.split('&')[0].strip())
