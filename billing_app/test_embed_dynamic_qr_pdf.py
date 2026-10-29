"""
Test Suite: Dynamically Generated QR Code Embedded into PDF Layout
Verifies:
1. Dynamic QR generation encoding live model values (Invoice ID, Customer, Total Amount, Date).
2. Embedded QR in xhtml2pdf HTML/CSS template layout.
3. Embedded QR in ReportLab canvas Flowable layout.
4. Payload modes ('text', 'upi', 'json') and engine selection ('auto', 'qrcode', 'segno').
5. HTTP view download endpoint with qr_mode query params.
6. CLI management command execution.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.core.management import call_command
from django.utils import timezone
import io

from billing_app.models import Invoice, InvoiceItem, Customer, UserProfile
from billing_app.pdf_generator import (
    get_invoice_pdf_context,
    render_invoice_to_pdf_xhtml2pdf,
    render_invoice_to_pdf_reportlab,
    generate_invoice_pdf_bytes,
    pisa,
    REPORTLAB_AVAILABLE,
)
from billing_app.invoice_qr import (
    fetch_invoice_data,
    build_invoice_qr_payload,
    generate_invoice_qr_bundle,
)


class EmbedDynamicQRPDFTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='distributor_qr_test',
            password='testpassword123',
            email='dist_qr@example.com'
        )
        self.profile = self.user.profile
        self.profile.role = 'DISTRIBUTOR'
        self.profile.business_name = 'Test Apex Dynamics'
        self.profile.phone = '+91 99887 76655'
        self.profile.upi_id = 'apexdistributor@upi'
        self.profile.save()

        self.customer = Customer.objects.create(
            name='Vikramaditya Singhania',
            phone='9876543210',
            email='vikram@singhania.com',
            address='Skyline Towers, Nariman Point, Mumbai',
            gstin='27ABCDE1234F1Z5'
        )

        self.invoice = Invoice.objects.create(
            invoice_number='INV-2026-QR-999',
            distributor=self.user,
            customer=self.customer,
            customer_name='Vikramaditya Singhania',
            customer_phone='9876543210',
            subtotal=Decimal('2000.00'),
            tax_amount=Decimal('360.00'),
            discount=Decimal('50.00'),
            grand_total=Decimal('2310.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        InvoiceItem.objects.create(
            invoice=self.invoice,
            product_name='Enterprise Server Blade X1',
            quantity=2,
            unit_price=Decimal('1000.00'),
            tax_rate=Decimal('18.00'),
            total=Decimal('2360.00')
        )

        self.client = Client()
        self.client.login(username='distributor_qr_test', password='testpassword123')

    def test_dynamic_qr_payload_encoding(self):
        """Verify dynamic QR payloads contain accurate live model values."""
        data = fetch_invoice_data(self.invoice)
        self.assertEqual(data['invoice_id'], self.invoice.id)
        self.assertEqual(data['invoice_number'], 'INV-2026-QR-999')
        self.assertEqual(data['customer_name'], 'Vikramaditya Singhania')
        self.assertEqual(data['total_amount'], 2310.00)

        # 1. Text payload
        text_payload = build_invoice_qr_payload(data, payload_format='text')
        self.assertIn('INV-2026-QR-999', text_payload)
        self.assertIn('Vikramaditya Singhania', text_payload)
        self.assertIn('2310.00', text_payload)

        # 2. UPI payload
        upi_payload = build_invoice_qr_payload(data, payload_format='upi')
        self.assertTrue(upi_payload.startswith('upi://pay?'))
        self.assertIn('pa=apexdistributor@upi', upi_payload)
        self.assertIn('am=2310.00', upi_payload)
        self.assertIn('cu=INR', upi_payload)

        # 3. JSON payload
        json_payload = build_invoice_qr_payload(data, payload_format='json')
        self.assertIn('"invoice_number": "INV-2026-QR-999"', json_payload)
        self.assertIn('"customer_name": "Vikramaditya Singhania"', json_payload)

    def test_pdf_context_has_dynamic_qr_bundle(self):
        """Ensure get_invoice_pdf_context dynamically embeds QR data and captions."""
        context_text = get_invoice_pdf_context(self.invoice, qr_mode='text')
        self.assertIn('qr_base64', context_text)
        self.assertIn('qr_bytes', context_text)
        self.assertTrue(len(context_text['qr_bytes']) > 100)
        self.assertEqual(context_text['qr_mode'], 'text')
        self.assertEqual(context_text['qr_caption'], '[ DIGITALLY VERIFIED QR INVOICE ]')

        context_upi = get_invoice_pdf_context(self.invoice, qr_mode='upi')
        self.assertIn('qr_base64', context_upi)
        self.assertEqual(context_upi['qr_mode'], 'upi')
        self.assertEqual(context_upi['qr_caption'], '[ INSTANT UPI PAYMENT QR ]')
        self.assertTrue(context_upi['active_payload'].startswith('upi://pay?'))

    def test_xhtml2pdf_embeds_dynamic_qr(self):
        """Ensure xhtml2pdf compiles invoice HTML template with embedded QR code into valid PDF."""
        if not pisa:
            self.skipTest("xhtml2pdf is not installed.")

        # Test both text and upi mode
        pdf_bytes_text = render_invoice_to_pdf_xhtml2pdf(self.invoice, qr_mode='text')
        self.assertTrue(pdf_bytes_text.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes_text), 1000)

        pdf_bytes_upi = render_invoice_to_pdf_xhtml2pdf(self.invoice, qr_mode='upi')
        self.assertTrue(pdf_bytes_upi.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes_upi), 1000)

    def test_reportlab_embeds_dynamic_qr(self):
        """Ensure ReportLab Flowable canvas compiles with dynamic QR Image Flowable."""
        if not REPORTLAB_AVAILABLE:
            self.skipTest("ReportLab is not installed.")

        pdf_bytes_text = render_invoice_to_pdf_reportlab(self.invoice, qr_mode='text')
        self.assertTrue(pdf_bytes_text.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes_text), 1000)

        pdf_bytes_upi = render_invoice_to_pdf_reportlab(self.invoice, qr_mode='upi')
        self.assertTrue(pdf_bytes_upi.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes_upi), 1000)

    def test_generate_invoice_pdf_bytes_unified_entrypoint(self):
        """Test unified entrypoint generate_invoice_pdf_bytes with various engines and qr_modes."""
        # auto engine
        pdf_auto = generate_invoice_pdf_bytes(self.invoice, engine='auto', qr_mode='upi')
        self.assertTrue(pdf_auto.startswith(b'%PDF-'))

        # xhtml2pdf engine
        if pisa:
            pdf_xhtml = generate_invoice_pdf_bytes(self.invoice, engine='xhtml2pdf', qr_mode='text')
            self.assertTrue(pdf_xhtml.startswith(b'%PDF-'))

        # reportlab engine
        if REPORTLAB_AVAILABLE:
            pdf_rl = generate_invoice_pdf_bytes(self.invoice, engine='reportlab', qr_mode='upi')
            self.assertTrue(pdf_rl.startswith(b'%PDF-'))

    def test_http_view_pdf_download_with_qr_mode(self):
        """Test GET /invoice/<id>/pdf/?qr_mode=upi returns valid PDF with attachment headers."""
        url = f"/invoice/{self.invoice.id}/pdf/?qr_mode=upi&engine=auto"
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'filename="Invoice_{self.invoice.invoice_number}.pdf"', response['Content-Disposition'])
        self.assertTrue(response.content.startswith(b'%PDF-'))

    def test_cli_management_command_qr_mode(self):
        """Test python manage.py generate_invoice_pdf <id> --qr-mode upi."""
        out = io.StringIO()
        call_command('generate_invoice_pdf', str(self.invoice.id), '--qr-mode', 'upi', '--engine', 'auto', stdout=out)
        output_str = out.getvalue()
        self.assertIn("Generated valid PDF", output_str)
        self.assertIn("QR Mode: 'upi'", output_str)
