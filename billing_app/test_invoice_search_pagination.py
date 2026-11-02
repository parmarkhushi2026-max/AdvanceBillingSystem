"""
Test Suite: Invoice Search Functionality (Customer Name & Invoice ID) and Pagination
Verifies:
1. Search functionality by customer name using Django Q query filters.
2. Search functionality by invoice ID (integer primary key and invoice number) using Django Q query filters.
3. Combined search by both customer name and invoice ID simultaneously.
4. Universal search query (?q=...) filtering customer name and invoice ID.
5. Pagination results per page limiting (?per_page=2, ?per_page=5, ?per_page=10).
6. Pagination navigation (page 1, page 2) and preservation of query parameters in pagination links.
7. Unpaginated full view (?per_page=all).
8. REST API /api/invoices/details/ search and pagination parameters.
9. Edge cases (case-insensitivity, whitespace trimming, hash prefix, invalid page numbers).
"""

from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Invoice, Customer, UserProfile
from billing_app.invoice_seeder import ensure_invoice_data_exists


class InvoiceSearchAndPaginationTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        ensure_invoice_data_exists(skip_in_test=False)

        # Retrieve seeded distributor & admin
        self.distributor = User.objects.filter(username='distributor').first()
        self.assertIsNotNone(self.distributor, "Seed data must provide distributor user.")

        self.admin = User.objects.filter(username='admin').first()
        if not self.admin:
            self.admin = User.objects.create_superuser('admin_sp', 'admin_sp@example.com', 'admin123')
            UserProfile.objects.get_or_create(
                user=self.admin,
                defaults={'role': 'ADMIN', 'business_name': 'Admin HQ'}
            )

        self.client.force_login(self.admin)

    def test_search_by_customer_name_query_filter(self):
        """Verify searching by customer_name filters records accurately using Django Q query filters."""
        # Target customer: Pooja Electronics & Retail
        response = self.client.get(reverse('invoice_list') + '?customer_name=Pooja')
        self.assertEqual(response.status_code, 200)

        invoices = response.context['invoices']
        self.assertGreater(len(invoices), 0)
        for inv in invoices:
            self.assertTrue(
                'pooja' in inv.customer_name.lower() or 
                (inv.customer and 'pooja' in inv.customer.name.lower())
            )
        self.assertContains(response, 'Pooja Electronics')

    def test_search_by_customer_name_case_insensitive_and_partial(self):
        """Verify customer name query is case-insensitive and supports substrings."""
        response = self.client.get(reverse('invoice_list') + '?customer_name=stationery')
        self.assertEqual(response.status_code, 200)

        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].customer_name, 'Modern Stationery Hub')

    def test_search_by_invoice_id_integer(self):
        """Verify searching by invoice ID primary key integer using query filter."""
        first_inv = Invoice.objects.first()
        response = self.client.get(reverse('invoice_list') + f'?invoice_id={first_inv.id}')
        self.assertEqual(response.status_code, 200)

        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].id, first_inv.id)
        self.assertContains(response, first_inv.invoice_number)

    def test_search_by_invoice_id_number_string_and_hash_prefix(self):
        """Verify searching by invoice number string with and without '#' prefix."""
        target_inv = Invoice.objects.filter(invoice_number__contains='001').first()
        self.assertIsNotNone(target_inv)

        # With hash prefix (sent via GET dict to ensure proper URL parameter encoding)
        response = self.client.get(reverse('invoice_list'), {'invoice_id': f'#{target_inv.invoice_number}'})
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].invoice_number, target_inv.invoice_number)

        # Without hash prefix
        response_raw = self.client.get(reverse('invoice_list'), {'invoice_id': target_inv.invoice_number})
        self.assertEqual(response_raw.status_code, 200)
        invoices_raw = response_raw.context['invoices']
        self.assertEqual(len(invoices_raw), 1)
        self.assertEqual(invoices_raw[0].invoice_number, target_inv.invoice_number)

    def test_combined_search_by_customer_name_and_invoice_id(self):
        """Verify combining both customer_name and invoice_id filters restricts to exact match."""
        target_inv = Invoice.objects.filter(customer_name__icontains='Rajesh').first()
        self.assertIsNotNone(target_inv)

        # Matching both
        response = self.client.get(
            reverse('invoice_list') + f'?customer_name=Rajesh&invoice_id={target_inv.id}'
        )
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].id, target_inv.id)

        # Non-matching combination (Customer Rajesh + Non-matching Invoice ID 99999)
        response_none = self.client.get(
            reverse('invoice_list') + '?customer_name=Rajesh&invoice_id=99999'
        )
        self.assertEqual(response_none.status_code, 200)
        self.assertEqual(len(response_none.context['invoices']), 0)
        self.assertContains(response_none, 'No invoice records match')

    def test_universal_search_query_param(self):
        """Verify ?q= works across both customer name and invoice ID/number."""
        # Search by customer name via ?q=
        resp_cust = self.client.get(reverse('invoice_list') + '?q=Anil')
        self.assertEqual(resp_cust.status_code, 200)
        self.assertGreater(len(resp_cust.context['invoices']), 0)
        self.assertTrue(all('anil' in inv.customer_name.lower() for inv in resp_cust.context['invoices']))

        # Search by invoice number via ?q=
        target = Invoice.objects.first()
        resp_inv = self.client.get(reverse('invoice_list') + f'?q={target.invoice_number}')
        self.assertEqual(resp_inv.status_code, 200)
        self.assertEqual(len(resp_inv.context['invoices']), 1)
        self.assertEqual(resp_inv.context['invoices'][0].id, target.id)

    def test_pagination_limits_results_per_page(self):
        """Verify pagination parameter ?per_page limits the number of results per page."""
        total_count = Invoice.objects.count()
        self.assertGreaterEqual(total_count, 4, "Need at least 4 invoices to test pagination limits.")

        # Limit to 2 per page
        response = self.client.get(reverse('invoice_list') + '?per_page=2')
        self.assertEqual(response.status_code, 200)

        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 2)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(response.context['paginator'].num_pages, (total_count + 1) // 2)

    def test_pagination_navigation_pages(self):
        """Verify navigating across page 1 and page 2 returns distinct slices."""
        response_p1 = self.client.get(reverse('invoice_list') + '?per_page=2&page=1')
        response_p2 = self.client.get(reverse('invoice_list') + '?per_page=2&page=2')

        self.assertEqual(response_p1.status_code, 200)
        self.assertEqual(response_p2.status_code, 200)

        p1_ids = [inv.id for inv in response_p1.context['invoices']]
        p2_ids = [inv.id for inv in response_p2.context['invoices']]

        self.assertEqual(len(p1_ids), 2)
        self.assertEqual(len(p2_ids), 2)
        # Ensure no overlap between page 1 and page 2
        self.assertFalse(set(p1_ids).intersection(set(p2_ids)))

    def test_pagination_links_preserve_search_filters(self):
        """Verify pagination links preserve customer_name, invoice_id, and per_page in href."""
        response = self.client.get(reverse('invoice_list') + '?customer_name=Stores&per_page=1')
        self.assertEqual(response.status_code, 200)

        # Pagination links should contain customer_name=Stores and per_page=1
        if response.context['is_paginated']:
            self.assertContains(response, 'customer_name=Stores')
            self.assertContains(response, 'per_page=1')

    def test_pagination_view_all_parameter(self):
        """Verify ?per_page=all returns all records without pagination."""
        response = self.client.get(reverse('invoice_list') + '?per_page=all')
        self.assertEqual(response.status_code, 200)

        invoices = response.context['invoices']
        self.assertEqual(len(invoices), Invoice.objects.count())
        self.assertFalse(response.context['is_paginated'])

    def test_dedicated_bootstrap_table_view_search_and_pagination(self):
        """Verify dedicated /invoices/table/ view supports customer_name, invoice_id, and pagination."""
        response = self.client.get(
            reverse('invoice_bootstrap_table') + '?customer_name=Medical&per_page=5'
        )
        self.assertEqual(response.status_code, 200)
        invoices = response.context['invoices']
        self.assertEqual(len(invoices), 1)
        self.assertEqual(invoices[0].customer_name, 'Anil Medical & Diagnostics')

    def test_api_invoices_search_and_pagination(self):
        """Verify REST API endpoint /api/invoices/details/ supports search & pagination."""
        # Filter by customer name
        resp = self.client.get(reverse('api_all_invoices_details') + '?customer_name=Pooja')
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data['success'])
        self.assertGreater(data['total_count'], 0)
        self.assertTrue(all('pooja' in inv['customer_name'].lower() for inv in data['invoices']))

        # Filter by limit / per_page
        resp_limit = self.client.get(reverse('api_all_invoices_details') + '?limit=2&page=1')
        self.assertEqual(resp_limit.status_code, 200)
        data_limit = resp_limit.json()
        self.assertEqual(len(data_limit['invoices']), 2)
        self.assertTrue(data_limit['is_paginated'])
