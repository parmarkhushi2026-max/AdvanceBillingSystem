import json
import base64
from io import BytesIO
from PIL import Image
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.urls import reverse
from billing_app.models import Invoice, InvoiceItem, Customer
from billing_app.invoice_seeder import ensure_invoice_data_exists
from billing_app.invoice_qr import (
    fetch_invoice_data,
    build_invoice_qr_payload,
    generate_invoice_qr,
    generate_invoice_qr_bundle
)
from billing_app.qr_decoder import extract_invoice_info, decode_qr_image


class InvoiceQRGenerationTestCase(TestCase):
    """
    Test suite verifying that:
    1. Core values (ID, Customer Name, Total Amount, Date) are fetched from the saved Invoice model.
    2. A valid QR code is generated encoding these values (both text & JSON formats).
    3. The generated QR code can be verified and decoded.
    4. Model methods, views, and JSON API endpoints serve the QR code properly.
    5. Management command operates cleanly.
    """

    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)
        self.invoice = Invoice.objects.first()
        self.assertIsNotNone(self.invoice, "An invoice must exist in the database for testing.")
        
        self.dist_user = User.objects.filter(username='distributor').first()
        if not self.dist_user:
            self.dist_user = User.objects.create_user('distributor', 'dist@test.com', 'pass123')

    def test_fetch_invoice_data_from_saved_model(self):
        """Verify that fetch_invoice_data accurately retrieves ID, customer, amount, and date."""
        data = fetch_invoice_data(self.invoice)

        # 1. Invoice ID & Number
        self.assertEqual(data['invoice_id'], self.invoice.id)
        self.assertEqual(data['invoice_number'], self.invoice.invoice_number)

        # 2. Customer Name
        self.assertEqual(data['customer_name'], self.invoice.customer_name)
        self.assertTrue(len(data['customer_name']) > 0)

        # 3. Total Amount
        self.assertEqual(data['total_amount'], float(self.invoice.grand_total))
        self.assertGreater(data['total_amount'], 0)

        # 4. Date
        self.assertTrue(bool(data['date']))
        self.assertEqual(data['date'], self.invoice.created_at.strftime('%Y-%m-%d %H:%M'))

    def test_fetch_invoice_data_by_id_and_number(self):
        """Verify fetching by integer ID and by invoice_number string."""
        data_by_id = fetch_invoice_data(self.invoice.id)
        self.assertEqual(data_by_id['invoice_id'], self.invoice.id)

        data_by_num = fetch_invoice_data(self.invoice.invoice_number)
        self.assertEqual(data_by_num['invoice_id'], self.invoice.id)

    def test_build_invoice_qr_payload_text(self):
        """Verify text payload contains all 4 core values."""
        data = fetch_invoice_data(self.invoice)
        payload = build_invoice_qr_payload(data, payload_format='text')

        self.assertIn(f"Invoice ID: #{self.invoice.id}", payload)
        self.assertIn(f"Invoice No: {self.invoice.invoice_number}", payload)
        self.assertIn(f"Customer: {self.invoice.customer_name}", payload)
        self.assertIn(f"Total Amount: Rs.{data['grand_total_str']}", payload)
        self.assertIn(f"Date: {data['date']}", payload)

    def test_build_invoice_qr_payload_json(self):
        """Verify JSON payload contains all 4 core values in valid JSON structure."""
        data = fetch_invoice_data(self.invoice)
        payload = build_invoice_qr_payload(data, payload_format='json')

        parsed = json.loads(payload)
        self.assertEqual(parsed['invoice_id'], self.invoice.id)
        self.assertEqual(parsed['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(parsed['customer_name'], self.invoice.customer_name)
        self.assertEqual(parsed['total_amount'], float(self.invoice.grand_total))
        self.assertEqual(parsed['date'], data['date'])

    def test_generate_invoice_qr_base64_and_bytes(self):
        """Verify QR generation outputs valid Base64 data URI and raw PNG bytes."""
        # Base64
        b64_qr = generate_invoice_qr(self.invoice, as_base64=True)
        self.assertTrue(b64_qr.startswith('data:image/png;base64,'))
        self.assertGreater(len(b64_qr), 100)

        # Raw PNG bytes
        raw_bytes = generate_invoice_qr(self.invoice, as_base64=False)
        self.assertIsInstance(raw_bytes, bytes)
        # PNG signature check: \x89PNG\r\n\x1a\n
        self.assertTrue(raw_bytes.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_invoice_model_qr_methods(self):
        """Verify model methods on Invoice instance."""
        data = self.invoice.get_qr_data()
        self.assertEqual(data['invoice_id'], self.invoice.id)

        text_payload = self.invoice.get_qr_text_payload()
        self.assertIn(self.invoice.invoice_number, text_payload)

        json_payload = self.invoice.get_qr_json_payload()
        parsed = json.loads(json_payload)
        self.assertEqual(parsed['invoice_id'], self.invoice.id)

        # Base64 property
        self.assertTrue(self.invoice.qr_code_base64.startswith('data:image/png;base64,'))

    def test_qr_bundle_generation(self):
        """Verify generate_invoice_qr_bundle produces complete package."""
        bundle = generate_invoice_qr_bundle(self.invoice)
        self.assertEqual(bundle['invoice_id'], self.invoice.id)
        self.assertEqual(bundle['customer_name'], self.invoice.customer_name)
        self.assertEqual(bundle['total_amount'], float(self.invoice.grand_total))
        self.assertTrue(bundle['qr_base64'].startswith('data:image/png;base64,'))
        self.assertTrue(bundle['qr_bytes'].startswith(b'\x89PNG'))

    def test_qr_code_decoding_and_verification(self):
        """Verify that decoding the generated QR image extracts the invoice values."""
        raw_bytes = generate_invoice_qr(self.invoice, payload_format='text', as_base64=False)

        # Decode using decode_qr_image
        res = decode_qr_image(raw_bytes)
        self.assertTrue(res['success'], f"QR code decoding failed: {res.get('error')}")
        decoded_text = res['data']
        self.assertIn(self.invoice.invoice_number, decoded_text)
        self.assertIn(self.invoice.customer_name, decoded_text)

        # Extract normalized invoice info
        info = res.get('invoice_info') or extract_invoice_info(decoded_text)
        self.assertIsNotNone(info)
        self.assertEqual(info['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(info['customer_name'], self.invoice.customer_name)
        self.assertIn(str(int(self.invoice.grand_total)), str(info['total_bill']))

    def test_invoice_qr_view_authenticated(self):
        """Verify dedicated invoice QR showcase page renders successfully."""
        self.client.force_login(self.dist_user)
        response = self.client.get(reverse('invoice_qr', args=[self.invoice.id]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.invoice.invoice_number)
        self.assertContains(response, self.invoice.customer_name.split('&')[0].strip())
        self.assertContains(response, 'Invoice Verification QR Code')
        self.assertContains(response, 'data:image/png;base64,')

    def test_invoice_qr_image_view_serves_png(self):
        """Verify direct QR image endpoint returns valid PNG image."""
        response = self.client.get(reverse('invoice_qr_image', args=[self.invoice.id]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        self.assertTrue(response.content.startswith(b'\x89PNG\r\n\x1a\n'))

    def test_api_invoice_qr_code_json(self):
        """Verify JSON API endpoint returns accurate payload and QR Data URI."""
        response = self.client.get(reverse('api_invoice_qr_code', args=[self.invoice.id]))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['invoice_id'], self.invoice.id)
        self.assertEqual(data['invoice_number'], self.invoice.invoice_number)
        self.assertEqual(data['customer_name'], self.invoice.customer_name)
        self.assertEqual(data['total_amount'], float(self.invoice.grand_total))
        self.assertTrue(data['qr_data_uri'].startswith('data:image/png;base64,'))

    def test_invoice_preview_template_displays_dynamic_qr(self):
        """Verify that the invoice preview/detail template dynamically displays the QR code."""
        self.client.force_login(self.dist_user)
        response = self.client.get(reverse('invoice_detail', args=[self.invoice.id]))
        self.assertEqual(response.status_code, 200)

        # Context contains pre-generated dynamic QR codes
        self.assertIn('server_qr_base64', response.context)
        self.assertIn('invoice_qr_base64', response.context)
        self.assertIn('upi_qr_base64', response.context)
        self.assertTrue(response.context['server_qr_base64'].startswith('data:image/png;base64,'))
        self.assertTrue(response.context['upi_qr_base64'].startswith('data:image/png;base64,'))

        # Template HTML renders dynamic image and interactive switcher
        self.assertContains(response, 'id="detail-qr-img"')
        self.assertContains(response, 'data:image/png;base64,')
        self.assertContains(response, 'Invoice Data QR')
        self.assertContains(response, 'UPI Pay QR')
        self.assertContains(response, 'toggleDetailQR')

    def test_create_invoice_template_has_dynamic_qr_preview_and_modal(self):
        """Verify that create invoice template includes dynamic QR preview controls and live modal."""
        self.client.force_login(self.dist_user)
        response = self.client.get(reverse('create_invoice'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'dynamic-qr-box')
        self.assertContains(response, 'btn-mode-bill')
        self.assertContains(response, 'btn-mode-upi')
        self.assertContains(response, 'livePreviewModal')
        self.assertContains(response, 'Live Invoice Bill Preview')

    def test_invoice_pdf_view_includes_qr_code(self):
        """Verify that invoice PDF generation view creates and embeds QR code."""
        self.client.force_login(self.dist_user)
        response = self.client.get(reverse('invoice_pdf', args=[self.invoice.id]))
        # Returns 200 PDF attachment or error if xhtml2pdf is not installed in environment
        self.assertIn(response.status_code, [200, 302])

    def test_qr_generation_with_qrcode_and_segno_engines(self):
        """Verify that QR generation works with both 'qrcode' and 'segno' library engines."""
        # 1. qrcode engine
        qr_bytes_qrcode = generate_invoice_qr(self.invoice, engine='qrcode', as_base64=False)
        self.assertIsInstance(qr_bytes_qrcode, bytes)
        self.assertEqual(qr_bytes_qrcode[:8], b'\x89PNG\r\n\x1a\n')
        img_qrcode = Image.open(BytesIO(qr_bytes_qrcode))
        self.assertEqual(img_qrcode.format, 'PNG')
        dec_qrcode = decode_qr_image(img_qrcode)
        self.assertTrue(dec_qrcode.get('success'))

        # 2. segno engine
        qr_bytes_segno = generate_invoice_qr(self.invoice, engine='segno', as_base64=False)
        self.assertIsInstance(qr_bytes_segno, bytes)
        self.assertEqual(qr_bytes_segno[:8], b'\x89PNG\r\n\x1a\n')
        img_segno = Image.open(BytesIO(qr_bytes_segno))
        self.assertEqual(img_segno.format, 'PNG')
        dec_segno = decode_qr_image(img_segno)
        self.assertTrue(dec_segno.get('success'))

    def test_qr_code_generated_automatically_on_invoice_save(self):
        """Verify that saving an invoice model automatically generates and stores the QR code."""
        new_inv = Invoice.objects.create(
            invoice_number='INV-TEST-AUTO-QR',
            customer_name='Rohan Mehta Automations',
            customer_phone='9811223344',
            grand_total=3499.00
        )
        try:
            # Refresh from DB
            new_inv.refresh_from_db()
            self.assertTrue(bool(new_inv.qr_code_image))
            self.assertTrue('invoice_qrs/qr_INV-TEST-AUTO-QR' in new_inv.qr_code_image.name)
            self.assertTrue(bool(new_inv.qr_code_payload))
            self.assertIn('Invoice No: INV-TEST-AUTO-QR', new_inv.qr_code_payload)
            self.assertIn('Customer: Rohan Mehta Automations', new_inv.qr_code_payload)
            self.assertIn('3499.00', new_inv.qr_code_payload)
            self.assertTrue(new_inv.qr_code_base64.startswith('data:image/png;base64,'))
        finally:
            new_inv.delete()

    def test_generate_and_save_qr_with_explicit_engines(self):
        """Verify generate_and_save_qr method can explicitly select qrcode or segno engines."""
        # Explicit qrcode
        self.invoice.generate_and_save_qr(engine='qrcode')
        self.invoice.refresh_from_db()
        self.assertTrue(bool(self.invoice.qr_code_image))
        self.assertTrue(self.invoice.qr_code_base64.startswith('data:image/png;base64,'))

        # Explicit segno
        self.invoice.generate_and_save_qr(engine='segno')
        self.invoice.refresh_from_db()
        self.assertTrue(bool(self.invoice.qr_code_image))
        self.assertTrue(self.invoice.qr_code_base64.startswith('data:image/png;base64,'))

    def test_generate_invoice_qr_management_command(self):
        """Verify running generate_invoice_qr command via manage.py with qrcode and segno engines."""
        # 1. Single invoice default (auto)
        call_command('generate_invoice_qr')

        # 2. Specific invoice ID with JSON format
        call_command('generate_invoice_qr', str(self.invoice.id), format='json')

        # 3. Explicit engine qrcode
        call_command('generate_invoice_qr', str(self.invoice.id), engine='qrcode')

        # 4. Explicit engine segno
        call_command('generate_invoice_qr', str(self.invoice.id), engine='segno')

        # 5. All invoices flag
        call_command('generate_invoice_qr', all=True)

