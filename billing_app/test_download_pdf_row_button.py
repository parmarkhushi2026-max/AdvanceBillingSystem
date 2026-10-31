"""
Test Suite: "Download PDF" Button Beside Each Row in Invoices Table
Verifies:
1. Every invoice row in the Bootstrap table includes a prominent "Download PDF" button
   with class 'download-pdf-btn', icon 'fa-file-pdf', and link '/invoice/<id>/pdf/'.
2. The endpoint fetches the exact invoice ID and its related Customer entry from the database.
3. Customer attributes from DB (name, phone, address, gstin) are passed to the PDF generator.
4. The response returns HTTP 200, Content-Type 'application/pdf', and valid attachment headers.
5. The generated binary begins with '%PDF-' for both xhtml2pdf and ReportLab engines.
6. Error handling for non-existent invoice IDs.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Invoice, InvoiceItem, Customer, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists
from billing_app.pdf_generator import get_invoice_pdf_context, generate_invoice_pdf_bytes, pisa, REPORTLAB_AVAILABLE


class DownloadPDFRowButtonTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)

        self.distributor = User.objects.filter(username='distributor').first()
        self.assertIsNotNone(self.distributor)

        self.admin = User.objects.filter(username='admin').first()
        if not self.admin:
            self.admin = User.objects.create_superuser('admin_pdf', 'admin_pdf@example.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=self.admin,
                defaults={'role': 'ADMIN', 'business_name': 'Admin HQ'}
            )

        # Create a specific customer entry in the database with complete details
        self.customer = Customer.objects.create(
            name='Radheshyam Enterprises Pvt Ltd',
            phone='+91 91234 56789',
            email='accounts@radheshyam.com',
            address='Unit 402, Apex Business Square, Andheri East',
            city='Mumbai',
            gstin='27ABCDE5678F1Z9',
            created_by=self.distributor
        )

        # Create a corresponding invoice linked to this customer
        self.invoice = Invoice.objects.create(
            invoice_number='INV-2026-PDF-001',
            distributor=self.distributor,
            customer=self.customer,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
            subtotal=Decimal('10000.00'),
            tax_amount=Decimal('1800.00'),
            discount=Decimal('200.00'),
            grand_total=Decimal('11600.00'),
            payment_status='PAID',
            payment_method='UPI QR Code'
        )

        InvoiceItem.objects.create(
            invoice=self.invoice,
            product_name='Billing Software Annual License',
            quantity=1,
            unit_price=Decimal('10000.00'),
            tax_rate=Decimal('18.00'),
            total=Decimal('11800.00')
        )

    def test_download_pdf_button_rendered_beside_each_row(self):
        """Verify that 'Download PDF' button is present beside each row in the table."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        # Check for Download PDF button class and text
        self.assertContains(response, 'download-pdf-btn')
        self.assertContains(response, 'Download PDF')
        self.assertContains(response, 'fa-file-pdf')

        # Check button links directly to /invoice/<id>/pdf/
        expected_url = reverse('invoice_pdf', args=[self.invoice.id])
        self.assertContains(response, f'href="{expected_url}"')
        self.assertContains(response, f'data-invoice-id="{self.invoice.id}"')

    def test_download_pdf_fetches_correct_data_and_customer_entry_from_db(self):
        """Verify GET /invoice/<id>/pdf/ fetches corresponding customer and invoice data from DB."""
        self.client.force_login(self.distributor)

        # 1. Verify get_invoice_pdf_context fetches the DB customer record
        context = get_invoice_pdf_context(self.invoice)
        self.assertEqual(context['invoice'].id, self.invoice.id)
        self.assertEqual(context['customer'], self.customer)
        self.assertEqual(context['customer_name'], 'Radheshyam Enterprises Pvt Ltd')
        self.assertEqual(context['customer_phone'], '+91 91234 56789')
        self.assertEqual(context['customer_email'], 'accounts@radheshyam.com')
        self.assertEqual(context['customer_address'], 'Unit 402, Apex Business Square, Andheri East')
        self.assertEqual(context['customer_gstin'], '27ABCDE5678F1Z9')

        # 2. Verify HTTP response
        url = reverse('invoice_pdf', args=[self.invoice.id])
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertIn(f'filename="Invoice_{self.invoice.invoice_number}.pdf"', response['Content-Disposition'])

        # Verify valid PDF binary stream
        self.assertTrue(response.content.startswith(b'%PDF-'))
        self.assertGreater(len(response.content), 1000)

    def test_pdf_generated_via_xhtml2pdf_and_reportlab(self):
        """Verify both rendering engines compile PDFs with DB customer data."""
        if pisa:
            pdf_xhtml = generate_invoice_pdf_bytes(self.invoice, engine='xhtml2pdf')
            self.assertTrue(pdf_xhtml.startswith(b'%PDF-'))

        if REPORTLAB_AVAILABLE:
            pdf_rl = generate_invoice_pdf_bytes(self.invoice, engine='reportlab')
            self.assertTrue(pdf_rl.startswith(b'%PDF-'))

    def test_download_pdf_ajax_error_handling_for_invalid_id(self):
        """Verify requesting non-existent invoice ID handles failure cleanly."""
        self.client.force_login(self.admin)
        url = reverse('invoice_pdf', args=[999999])
        response = self.client.get(url, HTTP_X_REQUESTED_WITH='XMLHttpRequest')

        self.assertEqual(response.status_code, 404)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('not found', data['error'].lower())

    def test_distributor_download_pdf_button_access(self):
        """Verify distributor can see the Download PDF button and download their own invoice."""
        self.client.force_login(self.distributor)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'download-pdf-btn')
        self.assertContains(response, reverse('invoice_pdf', args=[self.invoice.id]))
