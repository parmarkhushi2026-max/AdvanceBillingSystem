import os
import tempfile
from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.core.management import call_command
from django.contrib.auth.models import User
from billing_app.models import Customer, Invoice, InvoiceItem, Product, UserProfile
from billing_app.pdf_generator import (
    render_invoice_to_pdf_xhtml2pdf,
    render_invoice_to_pdf_reportlab,
    generate_invoice_pdf_bytes,
    pisa,
    REPORTLAB_AVAILABLE
)


class PDFIntegrationTestCase(TestCase):
    """
    Test suite verifying integration of xhtml2pdf and ReportLab:
    1. xhtml2pdf HTML/CSS template to PDF generation.
    2. ReportLab direct canvas / Flowable document PDF generation.
    3. Unified entrypoint generate_invoice_pdf_bytes() with 'auto', 'xhtml2pdf', 'reportlab'.
    4. HTTP view endpoint with ?engine= parameter.
    5. Management command CLI execution for both engines.
    """

    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_superuser('admin_pdf_int', 'admin@int.com', 'adminpass123')
        UserProfile.objects.get_or_create(
            user=self.user,
            defaults={
                'role': 'ADMIN',
                'business_name': 'Integrator Solutions Ltd',
                'phone': '+91 91234 56789',
                'upi_id': 'integrator@upi'
            }
        )
        self.client.force_login(self.user)

        self.customer = Customer.objects.create(
            name='Precision Tech Hub',
            phone='9811002233',
            email='precision@hub.com',
            address='12 Tech Zone, Phase 1',
            city='Pune',
            gstin='27AAACP9999F1Z0',
            created_by=self.user
        )

        self.product = Product.objects.create(
            name='Advance POS Touch Terminal',
            sku='HW-POS-T1',
            price=Decimal('18500.00'),
            gst_rate=Decimal('18.00'),
            stock=25
        )

        self.invoice = Invoice.objects.create(
            invoice_number='INV-INT-2026-001',
            customer=self.customer,
            distributor=self.user,
            subtotal=Decimal('18500.00'),
            tax_amount=Decimal('3330.00'),
            grand_total=Decimal('21830.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        InvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product,
            product_name=self.product.name,
            quantity=1,
            unit_price=self.product.price,
            tax_rate=self.product.gst_rate,
            total=Decimal('21830.00')
        )

    def test_xhtml2pdf_engine_integration(self):
        """Verify xhtml2pdf renders valid binary PDF starting with %PDF-."""
        self.assertTrue(pisa is not None, "xhtml2pdf must be installed.")
        pdf_bytes = render_invoice_to_pdf_xhtml2pdf(self.invoice)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_reportlab_engine_integration(self):
        """Verify ReportLab renders valid binary PDF starting with %PDF-."""
        self.assertTrue(REPORTLAB_AVAILABLE, "ReportLab must be installed.")
        pdf_bytes = render_invoice_to_pdf_reportlab(self.invoice)

        self.assertIsInstance(pdf_bytes, bytes)
        self.assertTrue(pdf_bytes.startswith(b'%PDF-'))
        self.assertGreater(len(pdf_bytes), 2000)

    def test_unified_generator_auto_and_explicit_engines(self):
        """Verify generate_invoice_pdf_bytes with auto, xhtml2pdf, and reportlab."""
        auto_pdf = generate_invoice_pdf_bytes(self.invoice, engine='auto')
        self.assertTrue(auto_pdf.startswith(b'%PDF-'))

        xhtml_pdf = generate_invoice_pdf_bytes(self.invoice, engine='xhtml2pdf')
        self.assertTrue(xhtml_pdf.startswith(b'%PDF-'))

        rl_pdf = generate_invoice_pdf_bytes(self.invoice, engine='reportlab')
        self.assertTrue(rl_pdf.startswith(b'%PDF-'))

    def test_view_endpoint_with_engine_query_parameters(self):
        """Verify GET /invoice/<id>/pdf/?engine=xhtml2pdf and ?engine=reportlab."""
        # xhtml2pdf engine
        url_xhtml = reverse('invoice_pdf', args=[self.invoice.id]) + '?engine=xhtml2pdf'
        resp_xhtml = self.client.get(url_xhtml)
        self.assertEqual(resp_xhtml.status_code, 200)
        self.assertEqual(resp_xhtml.get('Content-Type'), 'application/pdf')
        self.assertTrue(resp_xhtml.content.startswith(b'%PDF-'))

        # reportlab engine
        url_rl = reverse('invoice_pdf', args=[self.invoice.id]) + '?engine=reportlab'
        resp_rl = self.client.get(url_rl)
        self.assertEqual(resp_rl.status_code, 200)
        self.assertEqual(resp_rl.get('Content-Type'), 'application/pdf')
        self.assertTrue(resp_rl.content.startswith(b'%PDF-'))

    def test_management_command_generate_invoice_pdf(self):
        """Verify management command generate_invoice_pdf for both engines."""
        with tempfile.TemporaryDirectory() as tmpdir:
            out_xhtml = os.path.join(tmpdir, 'out_xhtml.pdf')
            call_command('generate_invoice_pdf', str(self.invoice.id), engine='xhtml2pdf', output=out_xhtml)
            self.assertTrue(os.path.exists(out_xhtml))
            self.assertGreater(os.path.getsize(out_xhtml), 2000)

            out_rl = os.path.join(tmpdir, 'out_rl.pdf')
            call_command('generate_invoice_pdf', str(self.invoice.id), engine='reportlab', output=out_rl)
            self.assertTrue(os.path.exists(out_rl))
            self.assertGreater(os.path.getsize(out_rl), 2000)

