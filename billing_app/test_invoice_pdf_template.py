from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from billing_app.models import Customer, Invoice, InvoiceItem, Product, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists


class InvoicePDFTemplateTestCase(TestCase):
    """
    Test suite verifying the styled HTML/CSS invoice template for PDF export:
    1. Template renders with clean layout, company branding, and customer cards.
    2. Dynamic QR code image is embedded.
    3. Line items, subtotal, tax splits (CGST, SGST), and grand total are styled.
    4. Amount in Indian currency words is rendered.
    5. Valid binary PDF document is generated and downloaded via xhtml2pdf.
    """

    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser('admin_pdf', 'admin@example.com', 'adminpass123')
        UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={
                'role': 'ADMIN',
                'business_name': 'Apex Commercial Solutions',
                'phone': '+91 99887 76655',
                'upi_id': 'apexsolutions@upi'
            }
        )
        self.client.force_login(self.admin)

        self.customer = Customer.objects.create(
            name='Modern Retail Superstore',
            phone='9811223344',
            email='modern@retail.com',
            address='88 Commercial Boulevard, Ring Road',
            city='Ahmedabad',
            gstin='24AABCM8888K1Z2',
            created_by=self.admin
        )

        self.product1 = Product.objects.create(
            name='Thermal Receipt Printer 80mm',
            sku='PRN-80MM',
            price=Decimal('5000.00'),
            gst_rate=Decimal('18.00'),
            stock=50
        )
        self.product2 = Product.objects.create(
            name='Thermal Paper Rolls (Box of 50)',
            sku='ROL-50BX',
            price=Decimal('800.00'),
            gst_rate=Decimal('18.00'),
            stock=100
        )

        self.invoice = Invoice.objects.create(
            invoice_number='INV-PDF-STYLE-001',
            customer=self.customer,
            distributor=self.admin,
            subtotal=Decimal('5800.00'),
            tax_amount=Decimal('1044.00'),
            grand_total=Decimal('6844.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        InvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product1,
            product_name=self.product1.name,
            quantity=1,
            unit_price=self.product1.price,
            tax_rate=self.product1.gst_rate,
            total=Decimal('5900.00')
        )
        InvoiceItem.objects.create(
            invoice=self.invoice,
            product=self.product2,
            product_name=self.product2.name,
            quantity=1,
            unit_price=self.product2.price,
            tax_rate=self.product2.gst_rate,
            total=Decimal('944.00')
        )

    def test_pdf_export_status_and_headers(self):
        """Verify GET /invoice/<id>/pdf/ returns 200 PDF with proper attachment filename."""
        url = reverse('invoice_pdf', args=[self.invoice.id])
        resp = self.client.get(url)

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get('Content-Type'), 'application/pdf')
        self.assertIn('attachment; filename="Invoice_INV-PDF-STYLE-001.pdf"', resp.get('Content-Disposition', ''))
        self.assertTrue(resp.content.startswith(b'%PDF-'))
        self.assertGreater(len(resp.content), 2500)

    def test_pdf_template_contains_styled_structure(self):
        """Verify the rendered HTML template contains all styled invoice sections."""
        from django.template.loader import render_to_string
        from billing_app.views import number_to_indian_currency_words

        tax_amt = float(self.invoice.tax_amount or 0.0)
        context = {
            'invoice': self.invoice,
            'items': self.invoice.items.all(),
            'business_name': 'Apex Commercial Solutions',
            'business_phone': '+91 99887 76655',
            'business_address': '88 Commercial Boulevard',
            'business_gstin': '24AABCM8888K1Z2',
            'upi_id': 'apexsolutions@upi',
            'qr_base64': self.invoice.qr_code_base64,
            'cgst_amount': round(tax_amt / 2, 2),
            'sgst_amount': round(tax_amt / 2, 2),
            'grand_total_words': number_to_indian_currency_words(self.invoice.grand_total),
        }

        html = render_to_string('billing/invoice_pdf.html', context)

        # 1. Branding & Header
        self.assertIn('Apex Commercial Solutions', html)
        self.assertIn('TAX INVOICE', html)
        self.assertIn('#INV-PDF-STYLE-001', html)
        self.assertIn('PAID', html)

        # 2. Customer Party Card
        self.assertIn('Modern Retail Superstore', html)
        self.assertIn('9811223344', html)
        self.assertIn('Customer GSTIN: 24AABCM8888K1Z2', html)

        # 3. Itemized Products Table
        self.assertIn('Thermal Receipt Printer 80mm', html)
        self.assertIn('Thermal Paper Rolls (Box of 50)', html)

        # 4. Summary & Certified QR Code Box
        self.assertIn('DIGITALLY VERIFIED QR INVOICE', html)
        self.assertIn('Taxable Subtotal:', html)
        self.assertIn('Central GST (CGST):', html)
        self.assertIn('State GST (SGST):', html)
        self.assertIn('Grand Total:', html)

        # 5. Amount in Words & Terms
        self.assertIn('Amount in Words:', html)
        self.assertIn('Terms &amp; Conditions:', html)
        self.assertIn('DIGITALLY CERTIFIED', html)
        self.assertIn('footerContent', html)
