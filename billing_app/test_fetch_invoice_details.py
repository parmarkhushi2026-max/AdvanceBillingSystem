import json
from io import StringIO
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from billing_app.models import Invoice
from billing_app.invoice_qr import fetch_invoice_details, fetch_invoice_data
from billing_app.invoice_seeder import ensure_invoice_data_exists


class FetchInvoiceDetailsTestCase(TestCase):
    """
    Test suite verifying complete invoice details fetching from the database:
    1. ID (database primary key ID & invoice_number)
    2. Customer Name (customer_name & phone)
    3. Total (grand_total, subtotal, tax_amount)
    4. Date (created_at & formatted string)
    5. REST API endpoints & Management command
    """

    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)
        self.invoice = Invoice.objects.first()
        self.assertIsNotNone(self.invoice, "An invoice must exist in database.")

    def test_model_get_complete_details(self):
        """Verify Invoice.get_complete_details() returns ID, customer name, total, and date."""
        details = self.invoice.get_complete_details()

        # 1. Invoice ID
        self.assertEqual(details['id'], self.invoice.id)
        self.assertEqual(details['invoice_id'], self.invoice.id)
        self.assertEqual(details['invoice_number'], self.invoice.invoice_number)

        # 2. Customer Name
        self.assertEqual(details['customer_name'], self.invoice.customer_name)
        self.assertTrue(len(details['customer_name']) > 0)

        # 3. Total
        self.assertEqual(details['total'], float(self.invoice.grand_total))
        self.assertEqual(details['total_amount'], float(self.invoice.grand_total))
        self.assertGreater(details['total'], 0)

        # 4. Date
        self.assertTrue(bool(details['date']))
        self.assertEqual(details['date'], self.invoice.created_at.strftime('%Y-%m-%d %H:%M'))

    def test_fetch_invoice_details_by_id_and_number(self):
        """Verify fetch_invoice_details() function works with integer ID and invoice number."""
        data_by_id = fetch_invoice_details(self.invoice.id)
        self.assertEqual(data_by_id['invoice_id'], self.invoice.id)
        self.assertEqual(data_by_id['customer_name'], self.invoice.customer_name)
        self.assertEqual(data_by_id['total_amount'], float(self.invoice.grand_total))
        self.assertEqual(data_by_id['date'], self.invoice.created_at.strftime('%Y-%m-%d %H:%M'))

        data_by_num = fetch_invoice_details(self.invoice.invoice_number)
        self.assertEqual(data_by_num['invoice_id'], self.invoice.id)

    def test_api_invoice_details_endpoint(self):
        """Verify GET /api/invoice/<id>/details/ returns complete details JSON."""
        url = reverse('api_invoice_details', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data.get('success'))

        inv = json_data.get('invoice', {})
        self.assertEqual(inv['id'], self.invoice.id)
        self.assertEqual(inv['customer_name'], self.invoice.customer_name)
        self.assertEqual(inv['total'], float(self.invoice.grand_total))
        self.assertEqual(inv['date'], self.invoice.created_at.strftime('%Y-%m-%d %H:%M'))

    def test_api_all_invoices_details_endpoint(self):
        """Verify GET /api/invoices/details/ returns list with all invoices."""
        url = reverse('api_all_invoices_details')
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        json_data = resp.json()
        self.assertTrue(json_data.get('success'))
        self.assertGreater(json_data.get('total_count', 0), 0)

        first = json_data['invoices'][0]
        self.assertIn('id', first)
        self.assertIn('customer_name', first)
        self.assertIn('total', first)
        self.assertIn('date', first)

    def test_management_command_fetch_invoice_details(self):
        """Verify management command prints details cleanly."""
        out = StringIO()
        call_command('fetch_invoice_details', str(self.invoice.id), stdout=out)
        output = out.getvalue()

        self.assertIn(str(self.invoice.id), output)
        self.assertIn(self.invoice.customer_name, output)
        self.assertIn(f"Rs. {self.invoice.grand_total:.2f}", output)
        self.assertIn(self.invoice.created_at.strftime('%Y-%m-%d %H:%M'), output)

    def test_management_command_fetch_all_invoices(self):
        """Verify management command with --all option."""
        out = StringIO()
        call_command('fetch_invoice_details', all=True, stdout=out)
        output = out.getvalue()

        self.assertIn("Fetching complete details", output)
        self.assertIn("INVOICE NO", output)
        self.assertIn("CUSTOMER NAME", output)
        self.assertIn("TOTAL (Rs.)", output)
        self.assertIn("DATE", output)
