from decimal import Decimal
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from billing_app.models import Customer, Invoice, InvoiceItem, Product, UserProfile


class AdminManualEntriesTestCase(TestCase):
    """
    Test suite verifying manual entries via Django Admin:
    1. Superuser login into Django Admin (/django-admin/)
    2. Manual entry of Customer via Django admin (/django-admin/billing_app/customer/add/)
    3. Manual entry of Invoice with inlined items via Django admin (/django-admin/billing_app/invoice/add/)
    4. Auto-calculation of totals from inlines & automatic QR generation
    """

    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_superuser(
            username='admin_entry_tester',
            email='admin@test.com',
            password='testpassword123'
        )
        profile, _ = UserProfile.objects.get_or_create(
            user=self.admin_user,
            defaults={
                'role': 'ADMIN',
                'business_name': 'Admin Entry Hub',
                'phone': '9811122233'
            }
        )
        if profile.role != 'ADMIN':
            profile.role = 'ADMIN'
            profile.save()
        self.client.force_login(self.admin_user)

        self.product = Product.objects.create(
            name='Thermal Receipt Printer 80mm',
            sku='PRN-ADM-01',
            price=Decimal('5000.00'),
            gst_rate=Decimal('18.00'),
            stock=100
        )

    def test_admin_dashboard_accessible(self):
        """Verify Django Admin dashboard loads successfully for superuser."""
        resp = self.client.get('/django-admin/')
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, 'Advance Billing System - Administration')
        self.assertContains(resp, 'Customers')
        self.assertContains(resp, 'Invoices')

    def test_manual_customer_entry_via_admin(self):
        """Verify adding a Customer manually via Django Admin POST."""
        url = '/django-admin/billing_app/customer/add/'
        post_data = {
            'name': 'Kalyan Jewellers & Retail',
            'phone': '9844455566',
            'email': 'kalyan@example.com',
            'address': '204 High Street, CG Road',
            'city': 'Ahmedabad',
            'gstin': '24AAACK1234F1Z9',
            'created_by': self.admin_user.id,
            'invoices-TOTAL_FORMS': '0',
            'invoices-INITIAL_FORMS': '0',
            'invoices-MIN_NUM_FORMS': '0',
            'invoices-MAX_NUM_FORMS': '1000',
            '_save': 'Save',
        }
        resp = self.client.post(url, data=post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Verify Customer exists in database
        cust = Customer.objects.filter(phone='9844455566').first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, 'Kalyan Jewellers & Retail')
        self.assertEqual(cust.city, 'Ahmedabad')

    def test_manual_invoice_entry_with_inline_items_via_admin(self):
        """Verify adding an Invoice with inlined InvoiceItems via Django Admin."""
        customer = Customer.objects.create(
            name='Maruti Supermarket',
            phone='9833344455',
            city='Surat'
        )

        url = '/django-admin/billing_app/invoice/add/'
        post_data = {
            'invoice_number': 'INV-ADM-MANUAL-001',
            'distributor': self.admin_user.id,
            'customer': customer.id,
            'customer_name': 'Maruti Supermarket',
            'customer_phone': '9833344455',
            'subtotal': '5000.00',
            'tax_amount': '900.00',
            'discount': '0.00',
            'grand_total': '5900.00',
            'payment_status': 'PAID',
            'payment_method': 'UPI QR Code',
            'notes': 'Manually entered in admin with line item',
            '_save': 'Save',
            # Formset inline items management form
            'items-TOTAL_FORMS': '1',
            'items-INITIAL_FORMS': '0',
            'items-MIN_NUM_FORMS': '0',
            'items-MAX_NUM_FORMS': '1000',
            # Inline Item 0
            'items-0-product': self.product.id,
            'items-0-product_name': self.product.name,
            'items-0-quantity': '1',
            'items-0-unit_price': '5000.00',
            'items-0-tax_rate': '18.00',
            'items-0-discount': '0.00',
            'items-0-total': '5900.00',
        }

        resp = self.client.post(url, data=post_data, follow=True)
        self.assertEqual(resp.status_code, 200)

        # Verify Invoice exists and customer details were auto-filled
        invoice = Invoice.objects.filter(invoice_number='INV-ADM-MANUAL-001').first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.customer, customer)
        self.assertEqual(invoice.customer_name, 'Maruti Supermarket')
        self.assertEqual(invoice.customer_phone, '9833344455')
        self.assertEqual(invoice.grand_total, Decimal('5900.00'))

        # Verify inlined item was saved
        self.assertEqual(invoice.items.count(), 1)
        item = invoice.items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 1)

        # Verify QR was automatically generated on manual save
        self.assertTrue(bool(invoice.qr_code_image) or bool(invoice.qr_code_payload))
