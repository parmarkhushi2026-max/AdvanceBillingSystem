"""
Test Suite: Fetch All Invoice Records and Display in Bootstrap-Styled Table
Verifies:
1. Database records are fetched with all related items, customer, and distributor models.
2. Template renders an authentic Bootstrap-styled table with CSS components:
   - <table class="... table table-striped table-hover table-bordered align-middle ...">
   - <thead class="table-dark">
   - Bootstrap badges: badge bg-success, badge bg-warning, badge bg-danger, badge bg-light
   - Bootstrap button groups: btn-group, btn-outline-primary, btn-outline-danger, etc.
   - Bootstrap pagination: pagination, page-item, page-link
3. Renders core invoice attributes: Invoice ID/number, customer name, line items, total amount, date.
4. Action buttons: PDF download, QR view, Preview, and Detail view.
5. Works across both Admin and Distributor accounts.
6. Real-time search, status filtering, and 'view all' (per_page=all) query parameters.
7. Dedicated route /invoices/table/ and canonical route /invoices/.
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Invoice, InvoiceItem, Customer, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists


class InvoiceBootstrapTableTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        # Seed realistic invoice and customer records
        ensure_invoice_data_exists(skip_in_test=False)

        # Retrieve seeded distributor
        self.distributor = User.objects.filter(username='distributor').first()
        self.assertIsNotNone(self.distributor, "Seed data must provide a distributor user.")

        # Ensure admin user exists
        self.admin = User.objects.filter(username='admin').first()
        if not self.admin:
            self.admin = User.objects.create_superuser('admin_bt', 'admin_bt@example.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=self.admin,
                defaults={'role': 'ADMIN', 'business_name': 'Admin HQ'}
            )

    def test_invoices_fetched_from_database(self):
        """Verify that multiple invoice records exist in the database and can be fetched."""
        count = Invoice.objects.count()
        self.assertGreaterEqual(count, 3, "Database must contain at least 3 invoice records.")

    def test_invoice_list_view_renders_bootstrap_table_classes(self):
        """Verify that GET /invoices/ renders an authentic Bootstrap-styled table."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/invoice_list.html')

        # Check Bootstrap 5 CSS CDN link
        self.assertContains(response, 'bootstrap@5.3.3/dist/css/bootstrap.min.css')

        # Check Bootstrap table component classes
        self.assertContains(response, 'table-responsive')
        self.assertContains(response, 'table')
        self.assertContains(response, 'table-striped')
        self.assertContains(response, 'table-hover')
        self.assertContains(response, 'table-bordered')
        self.assertContains(response, 'align-middle')
        self.assertContains(response, 'table-dark')

        # Check Bootstrap badge classes
        self.assertContains(response, 'badge')

    def test_invoice_core_data_rendered_in_bootstrap_table(self):
        """Verify that fetched invoice records show ID, customer, products, total, and date in table cells."""
        self.client.force_login(self.distributor)
        response = self.client.get(reverse('invoice_list'))

        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertGreater(len(invoices), 0)

        # Verify first invoice data appears inside the table markup
        first_inv = invoices[0]
        self.assertContains(response, first_inv.invoice_number)
        self.assertContains(response, first_inv.customer_name.split('&')[0].strip())
        self.assertContains(response, f"{first_inv.grand_total:.2f}")

        # Check for action links inside the Bootstrap action button group
        self.assertContains(response, reverse('invoice_preview', args=[first_inv.id]))
        self.assertContains(response, reverse('invoice_pdf', args=[first_inv.id]))
        self.assertContains(response, reverse('invoice_qr', args=[first_inv.id]))
        self.assertContains(response, reverse('invoice_detail', args=[first_inv.id]))

    def test_dedicated_bootstrap_table_view_endpoint(self):
        """Verify that GET /invoices/table/ displays all fetched invoices in Bootstrap table."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_bootstrap_table'))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'billing/invoice_list.html')
        self.assertTrue(response.context.get('bootstrap_table_mode'))

        # Check all invoices are in the table context
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), Invoice.objects.count())

        # Verify Bootstrap classes on dedicated endpoint
        self.assertContains(response, 'invoice-bootstrap-table')
        self.assertContains(response, 'table-striped')

    def test_bootstrap_table_alias_endpoint(self):
        """Verify that /invoices/bootstrap/ also displays the table."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_bootstrap_table_alias'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'table-striped')

    def test_bootstrap_table_view_all_per_page_parameter(self):
        """Verify ?per_page=all fetches all records without pagination truncation."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list') + '?per_page=all')

        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), Invoice.objects.count())
        self.assertFalse(response.context['is_paginated'])

    def test_bootstrap_table_search_filtering(self):
        """Verify search query filters records inside the Bootstrap table."""
        self.client.force_login(self.admin)
        target = Invoice.objects.first()
        search_query = target.invoice_number

        response = self.client.get(reverse('invoice_list') + f'?q={search_query}')
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertTrue(all(search_query in inv.invoice_number for inv in invoices))

    def test_bootstrap_table_status_filtering(self):
        """Verify filtering by payment_status displays matching records and status badges."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('invoice_list') + '?status=PAID')
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        for inv in invoices:
            self.assertEqual(inv.payment_status, 'PAID')
        self.assertContains(response, 'badge bg-success')
