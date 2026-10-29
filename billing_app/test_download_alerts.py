import json
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from billing_app.models import Invoice, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists


class DownloadButtonAndAlertsTestCase(TestCase):
    """
    Test suite verifying:
    1. Download button presence across preview, detail, list, and QR views
    2. Server-side PDF download generation and headers
    3. JSON invoice details download endpoint (?download=1)
    4. Success & failure error handling for download endpoints
    5. JavaScript download and alert engine presence in static assets
    """

    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)
        self.invoice = Invoice.objects.first()
        self.assertIsNotNone(self.invoice, "An invoice must exist in database for testing.")

        # Authenticated user for tests
        self.user = User.objects.filter(is_superuser=True).first()
        if not self.user:
            self.user = User.objects.create_superuser('admin_test', 'admin@example.com', 'adminpass123')
            UserProfile.objects.get_or_create(user=self.user, defaults={'role': 'ADMIN', 'business_name': 'Test Corp'})

    def test_download_pdf_success_returns_attachment(self):
        """Verify GET /invoice/<id>/pdf/ returns 200 with PDF content and attachment disposition."""
        self.client.force_login(self.user)
        url = reverse('invoice_pdf', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get('Content-Type'), 'application/pdf')
        self.assertIn(f'filename="Invoice_{self.invoice.invoice_number}.pdf"', resp.get('Content-Disposition', ''))
        self.assertTrue(resp.content.startswith(b'%PDF-'))

    def test_download_pdf_ajax_failure_returns_json_error(self):
        """Verify AJAX download for non-existent invoice returns JSON 404 failure alert data."""
        self.client.force_login(self.user)
        url = reverse('invoice_pdf', args=[999999])
        resp = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('not found', data.get('error', '').lower())

    def test_download_pdf_non_ajax_failure_redirects_with_message(self):
        """Verify direct browser navigation for non-existent invoice redirects with error message."""
        self.client.force_login(self.user)
        url = reverse('invoice_pdf', args=[999999])
        resp = self.client.get(url, follow=True)

        self.assertEqual(resp.status_code, 200)
        # Should redirect to invoice_list and flash error
        messages = [m.message for m in resp.context.get('messages', [])]
        self.assertTrue(any('not found' in m.lower() for m in messages))

    def test_download_invoice_json_details_success(self):
        """Verify /api/invoice/<id>/details/?download=1 returns JSON attachment file."""
        url = reverse('api_invoice_details', args=[self.invoice.id])
        resp = self.client.get(url, {'download': '1'})

        self.assertEqual(resp.status_code, 200)
        self.assertIn(f'filename="Invoice_{self.invoice.invoice_number}_Details.json"', resp.get('Content-Disposition', ''))
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertEqual(data['invoice']['id'], self.invoice.id)
        self.assertEqual(data['invoice']['customer_name'], self.invoice.customer_name)

    def test_download_invoice_json_details_failure_404(self):
        """Verify /api/invoice/999999/details/ returns 404 JSON error."""
        url = reverse('api_invoice_details', args=[999999])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 404)
        data = resp.json()
        self.assertFalse(data.get('success'))
        self.assertIn('error', data)

    def test_download_all_invoices_json_details_success(self):
        """Verify /api/invoices/details/?download=1 returns All_Invoices_Details.json attachment."""
        url = reverse('api_all_invoices_details')
        resp = self.client.get(url, {'download': '1'})

        self.assertEqual(resp.status_code, 200)
        self.assertIn('filename="All_Invoices_Details.json"', resp.get('Content-Disposition', ''))
        data = resp.json()
        self.assertTrue(data.get('success'))
        self.assertGreater(data.get('total_count', 0), 0)

    def test_download_buttons_and_alerts_in_preview_page(self):
        """Verify preview template contains download buttons and alert handlers."""
        self.client.force_login(self.user)
        url = reverse('invoice_preview', args=[self.invoice.id])
        resp = self.client.get(url)
        content = resp.content.decode('utf-8')

        # Download buttons
        self.assertIn('id="btn-server-pdf"', content)
        self.assertIn('downloadServerPDF', content)
        self.assertIn('id="btn-json-download"', content)
        self.assertIn('downloadInvoiceJSON', content)
        self.assertIn('id="btn-pdf-export"', content)
        self.assertIn('downloadInvoicePDF', content)
        self.assertIn('download="Invoice_', content)

        # Alerts handling
        self.assertIn('download-alert-container', content)
        self.assertIn('showAppAlert', content)

    def test_download_buttons_and_alerts_in_detail_page(self):
        """Verify detail template contains download buttons and alert handlers."""
        self.client.force_login(self.user)
        url = reverse('invoice_detail', args=[self.invoice.id])
        resp = self.client.get(url)
        content = resp.content.decode('utf-8')

        self.assertIn('downloadServerPDF', content)
        self.assertIn('Download PDF (Server)', content)
        self.assertIn('Download PDF (Client)', content)
        self.assertIn('Download JSON', content)
        self.assertIn('downloadInvoiceJSON', content)
        self.assertIn('download-alert-container', content)

    def test_download_buttons_in_list_and_qr_pages(self):
        """Verify invoice list and QR showcase contain download buttons and alert handlers."""
        self.client.force_login(self.user)

        # List page
        resp_list = self.client.get(reverse('invoice_list'))
        list_html = resp_list.content.decode('utf-8')
        self.assertIn('downloadServerPDF', list_html)
        self.assertIn('Export JSON', list_html)
        self.assertIn('downloadAllInvoicesJSON', list_html)

        # QR page
        resp_qr = self.client.get(reverse('invoice_qr', args=[self.invoice.id]))
        qr_html = resp_qr.content.decode('utf-8')
        self.assertIn('downloadServerPDF', qr_html)
        self.assertIn('Download PDF', qr_html)
        self.assertIn('Download JSON', qr_html)
        self.assertIn('downloadInvoiceJSON', qr_html)
        self.assertIn('download-alert-container', qr_html)

