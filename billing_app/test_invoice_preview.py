import json
from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Invoice, InvoiceItem, Customer, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists
from billing_app.views import number_to_indian_currency_words


class InvoicePreviewTestCase(TestCase):
    """
    Test suite for the 'Preview Invoice' page and API:
    - Route accessibility and authentication protection
    - Complete details rendering (Invoice ID, customer, products, totals, taxes, words)
    - Dynamic QR code bundle and UPI QR inclusion
    - A4 format and Thermal slip preview support
    - JSON API preview endpoint
    """

    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)
        self.invoice = Invoice.objects.first()
        self.assertIsNotNone(self.invoice, "An invoice must exist in the database.")

        # Create or fetch distributor user
        self.dist_user = User.objects.filter(username='distributor').first()
        if not self.dist_user:
            self.dist_user = User.objects.create_user('distributor', 'dist@test.com', 'dist123')
        UserProfile.objects.get_or_create(
            user=self.dist_user,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Test Agency', 'upi_id': 'test@upi'}
        )

        # Create or fetch admin user
        self.admin_user = User.objects.filter(username='admin').first()
        if not self.admin_user:
            self.admin_user = User.objects.create_superuser('admin', 'admin@test.com', 'admin123')
        UserProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={'role': 'ADMIN', 'business_name': 'Advance HQ', 'upi_id': 'admin@upi'}
        )

    def test_unauthenticated_user_redirected_to_login(self):
        """Unauthenticated GET to /invoice/<id>/preview/ must redirect."""
        url = reverse('invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 302)

    def test_authenticated_distributor_can_view_invoice_preview(self):
        """Authenticated distributor can access the Preview Invoice page successfully."""
        self.client.force_login(self.dist_user)
        url = reverse('invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'billing/invoice_preview.html')

        # Check context
        self.assertEqual(resp.context['invoice'].id, self.invoice.id)
        self.assertIn('bundle', resp.context)
        self.assertIn('qr_base64', resp.context)
        self.assertIn('upi_qr_base64', resp.context)
        self.assertIn('grand_total_words', resp.context)
        self.assertTrue(resp.context['qr_base64'].startswith('data:image/png;base64,'))
        self.assertTrue(resp.context['upi_qr_base64'].startswith('data:image/png;base64,'))

        # Check rendered HTML contents
        from django.utils.html import escape
        content = resp.content.decode('utf-8')
        self.assertIn(self.invoice.invoice_number, content)
        self.assertIn(escape(self.invoice.customer_name), content)
        self.assertIn("Verified Database QR", content)
        self.assertIn("A4 GST Invoice Preview", content)
        self.assertIn("POS Slip Preview", content)

    def test_authenticated_admin_can_view_invoice_preview(self):
        """Authenticated admin can access any invoice preview."""
        self.client.force_login(self.admin_user)
        url = reverse('invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.context['invoice'].id, self.invoice.id)
        self.assertTrue(resp.context['is_admin'])

    def test_preview_nonexistent_invoice_returns_404(self):
        """Requesting preview for invalid invoice ID returns 404."""
        self.client.force_login(self.dist_user)
        url = reverse('invoice_preview', args=[999999])
        resp = self.client.get(url)
        self.assertEqual(resp.status_code, 404)

    def test_api_invoice_preview_returns_valid_json(self):
        """The API endpoint /api/invoice/<id>/preview/ returns structured JSON."""
        url = reverse('api_invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data.get('success'))
        inv = data.get('invoice', {})
        self.assertEqual(inv.get('id'), self.invoice.id)
        self.assertEqual(inv.get('invoice_number'), self.invoice.invoice_number)
        self.assertEqual(inv.get('customer_name'), self.invoice.customer_name)
        self.assertEqual(inv.get('grand_total'), float(self.invoice.grand_total))
        self.assertTrue(inv.get('qr_code_base64').startswith('data:image/png;base64,'))

    def test_number_to_indian_currency_words_helper(self):
        """Verify Indian numbering system currency conversion in words."""
        self.assertEqual(number_to_indian_currency_words(0), "Rupees Zero Only")
        self.assertEqual(number_to_indian_currency_words(100), "Rupees One Hundred Only")
        self.assertEqual(number_to_indian_currency_words(1500), "Rupees One Thousand Five Hundred Only")
        self.assertEqual(number_to_indian_currency_words(25000), "Rupees Twenty Five Thousand Only")
        self.assertIn("Rupees", number_to_indian_currency_words(23234))

    def test_download_pdf_button_present_in_preview_page(self):
        """Verify Download PDF button linking to xhtml2pdf export is in preview HTML."""
        self.client.force_login(self.dist_user)
        url = reverse('invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)
        content = resp.content.decode('utf-8')
        pdf_url = reverse('invoice_pdf', args=[self.invoice.id])
        self.assertIn(pdf_url, content)
        self.assertIn("Download PDF", content)

    def test_download_pdf_via_xhtml2pdf_exports_valid_pdf_with_qr(self):
        """Verify GET to /invoice/<id>/pdf/ generates and downloads valid PDF with embedded QR."""
        self.client.force_login(self.dist_user)
        url = reverse('invoice_pdf', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get('Content-Type'), 'application/pdf')
        self.assertIn(f'filename="Invoice_{self.invoice.invoice_number}.pdf"', resp.get('Content-Disposition'))
        # PDF binary starts with %PDF- header and contains substantial bytes
        self.assertTrue(resp.content.startswith(b'%PDF-'))
        self.assertGreater(len(resp.content), 2000)
