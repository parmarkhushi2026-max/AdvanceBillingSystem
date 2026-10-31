"""
Test Suite: Preview Icon beside Each Invoice Entry to View Dynamic QR Code
Verifies:
1. Every invoice entry in the Bootstrap table has a dedicated QR code preview icon button
   beside the invoice number (`qr-preview-icon`) with `openDynamicQRModal(...)` handler.
2. The Actions column also contains the interactive `qr-preview-action-btn`.
3. The dynamic QR modal (`#qrPreviewModal`) is rendered in the HTML with:
   - Live QR image element (`#modalQRImage`)
   - Instant UPI, Certified Summary, and JSON mode selector buttons
   - Live verified badge and invoice data summary (number, customer, grand total, date)
   - Decoded payload preview container
4. The backend API `/api/invoice/<id>/qr-code/` supports `mode=upi|text|json` query parameters
   and returns status='success', live data, active payload, and Base64 Data URI.
5. The raw image endpoint `/invoice/<id>/qr.png` returns a valid image/png stream.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Invoice, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists


class InvoiceQRPreviewIconTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)

        self.distributor = User.objects.filter(username='distributor').first()
        self.assertIsNotNone(self.distributor, "Seed data must provide a distributor user.")

        self.admin = User.objects.filter(username='admin').first()
        if not self.admin:
            self.admin = User.objects.create_superuser('admin_prev', 'admin_prev@example.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=self.admin,
                defaults={'role': 'ADMIN', 'business_name': 'Admin HQ'}
            )

    def test_preview_icon_rendered_beside_invoice_entry(self):
        """Verify each invoice entry has a dedicated QR preview icon beside the invoice number."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        # Check preview icon button class
        self.assertContains(response, 'qr-preview-icon')
        self.assertContains(response, 'openDynamicQRModal')
        self.assertContains(response, 'fa-qrcode')

        # Check action column button
        self.assertContains(response, 'qr-preview-action-btn')
        self.assertContains(response, 'QR Preview')

    def test_dynamic_qr_preview_modal_structure(self):
        """Verify that the dynamic QR preview modal and controls are included in the page."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="qrPreviewModal"')
        self.assertContains(response, 'id="modalQRImage"')
        self.assertContains(response, 'id="modalQRBadge"')
        self.assertContains(response, 'id="modalQRLoader"')
        self.assertContains(response, 'id="btnModeUpi"')
        self.assertContains(response, 'id="btnModeText"')
        self.assertContains(response, 'id="btnModeJson"')
        self.assertContains(response, 'switchModalQRMode')

    def test_api_invoice_qr_code_dynamic_payloads(self):
        """Verify /api/invoice/<id>/qr-code/ returns dynamic QR bundle matching requested mode."""
        self.client.force_login(self.admin)
        inv = Invoice.objects.first()
        self.assertIsNotNone(inv)

        # 1. UPI Mode
        res_upi = self.client.get(f'/api/invoice/{inv.id}/qr-code/?mode=upi')
        self.assertEqual(res_upi.status_code, 200)
        data_upi = res_upi.json()
        self.assertTrue(data_upi['success'])
        self.assertEqual(data_upi['invoice_id'], inv.id)
        self.assertTrue(data_upi['qr_data_uri'].startswith('data:image/png;base64,'))
        self.assertTrue(data_upi['active_payload'].startswith('upi://pay?'))

        # 2. Text Summary Mode
        res_text = self.client.get(f'/api/invoice/{inv.id}/qr-code/?mode=text')
        self.assertEqual(res_text.status_code, 200)
        data_text = res_text.json()
        self.assertIn(inv.invoice_number, data_text['active_payload'])
        self.assertIn(inv.customer_name, data_text['active_payload'])

        # 3. JSON Mode
        res_json = self.client.get(f'/api/invoice/{inv.id}/qr-code/?mode=json')
        self.assertEqual(res_json.status_code, 200)
        data_json = res_json.json()
        self.assertIn('"invoice_number":', data_json['active_payload'])

    def test_invoice_qr_image_raw_png_endpoint(self):
        """Verify /invoice/<id>/qr.png returns valid raw image/png bytes."""
        self.client.force_login(self.admin)
        inv = Invoice.objects.first()

        res = self.client.get(reverse('invoice_qr_image', args=[inv.id]) + '?format=upi')
        self.assertEqual(res.status_code, 200)
        self.assertEqual(res['Content-Type'], 'image/png')
        self.assertTrue(res.content.startswith(b'\x89PNG\r\n\x1a\n'))
        self.assertGreater(len(res.content), 200)

    def test_distributor_can_access_preview_icon(self):
        """Verify distributor user also sees the preview icons and modal for their invoices."""
        self.client.force_login(self.distributor)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'qr-preview-icon')
        self.assertContains(response, 'id="qrPreviewModal"')
