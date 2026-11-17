from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile, Distributor, Customer, Product


class PaginationAndSearchTestCase(TestCase):
    """
    Comprehensive test suite verifying pagination and search functionality
    for both Customer List and Product List views:
    - Customer search by name, phone, email, city, GSTIN, and ID.
    - Product search by name, SKU, HSN, category, unit, description, and ID.
    - Stock status filtering: in_stock, low_stock, out_of_stock.
    - Configurable pagination (per_page=5, 10, 25, 50, all).
    - Query parameter preservation across pagination links.
    - Multi-tenant data isolation under search and pagination filters.
    - Unauthenticated request redirects.
    """

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='admin_ps_tester',
            email='admin@pstest.com',
            password='AdminPass@123'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.save()

        # Distributor 1 (Alpha Logistics)
        self.dist1_user = User.objects.create_user(
            username='alpha_distributor',
            email='alpha@dist.com',
            password='AlphaPass@123'
        )
        self.dist1_profile, _ = UserProfile.objects.get_or_create(user=self.dist1_user)
        self.dist1_profile.role = 'DISTRIBUTOR'
        self.dist1_profile.save()

        self.dist1 = Distributor.objects.create(
            user=self.dist1_user,
            name='Alpha Agency Head',
            business_name='Alpha Logistics Co',
            phone='9111111111',
            email='alpha@dist.com',
            city='Ahmedabad',
            state='Gujarat',
            upi_id='alpha@upi',
            is_active=True
        )

        # Distributor 2 (Beta Traders)
        self.dist2_user = User.objects.create_user(
            username='beta_distributor',
            email='beta@dist.com',
            password='BetaPass@123'
        )
        self.dist2_profile, _ = UserProfile.objects.get_or_create(user=self.dist2_user)
        self.dist2_profile.role = 'DISTRIBUTOR'
        self.dist2_profile.save()

        self.dist2 = Distributor.objects.create(
            user=self.dist2_user,
            name='Beta Merchant Head',
            business_name='Beta Retail Mart',
            phone='9222222222',
            email='beta@dist.com',
            city='Surat',
            state='Gujarat',
            upi_id='beta@upi',
            is_active=True
        )

        # Populate 15 customers for Distributor 1 (to test pagination at limit=5 or 10)
        self.dist1_customers = []
        for i in range(1, 16):
            c = Customer.objects.create(
                name=f'Alpha Customer {i:02d}',
                phone=f'98000000{i:02d}',
                email=f'cust{i}@alpha.com',
                city='Ahmedabad' if i % 2 == 0 else 'Vadodara',
                address=f'Sector {i}, Alpha Industrial Zone',
                gstin=f'24ALPHA000{i:02d}Z1' if i % 3 == 0 else '',
                created_by=self.dist1_user,
                distributor_ref=self.dist1
            )
            self.dist1_customers.append(c)

        # Populate 5 customers for Distributor 2
        self.dist2_customers = []
        for i in range(1, 6):
            c = Customer.objects.create(
                name=f'Beta Shopper {i:02d}',
                phone=f'99000000{i:02d}',
                email=f'shopper{i}@beta.com',
                city='Surat',
                address=f'Ring Road Market {i}',
                gstin=f'24BETA000{i:02d}Z2',
                created_by=self.dist2_user,
                distributor_ref=self.dist2
            )
            self.dist2_customers.append(c)

        # Populate 15 products for Distributor 1 with varying categories, prices, and stock
        self.dist1_products = []
        categories = ['Electronics', 'Stationery', 'Hardware']
        stocks = [30, 8, 0]  # in_stock, low_stock, out_of_stock
        for i in range(1, 16):
            cat = categories[i % len(categories)]
            stk = stocks[i % len(stocks)]
            p = Product.objects.create(
                name=f'Alpha Gadget {i:02d}',
                sku=f'ALP-SKU-{i:03d}',
                hsn_code=f'8471{i:02d}',
                category=cat,
                price=Decimal(f'{100 * i}.50'),
                gst_rate=18.00,
                unit='Pcs',
                stock=stk,
                description=f'High performance Alpha product item {i}',
                created_by=self.dist1_user,
                distributor_ref=self.dist1
            )
            self.dist1_products.append(p)

        # Populate 5 products for Distributor 2
        self.dist2_products = []
        for i in range(1, 6):
            p = Product.objects.create(
                name=f'Beta Widget {i:02d}',
                sku=f'BET-SKU-{i:03d}',
                hsn_code=f'9000{i:02d}',
                category='Accessories',
                price=Decimal(f'{50 * i}.00'),
                gst_rate=12.00,
                unit='Box',
                stock=25,
                created_by=self.dist2_user,
                distributor_ref=self.dist2
            )
            self.dist2_products.append(p)

    # -------------------------------------------------------------
    # CUSTOMER SEARCH & PAGINATION TESTS
    # -------------------------------------------------------------
    def test_customer_list_unauthenticated_redirect(self):
        """Unauthenticated requests to customer list must redirect to login/landing."""
        response = self.client.get(reverse('customer_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/') or 'login' in response.url)

    def test_customer_list_default_pagination(self):
        """Distributor 1 has 15 customers; default limit 10 returns 10 items on page 1."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 15)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['customers']), 10)
        self.assertEqual(response.context['per_page'], '10')
        self.assertContains(response, 'Showing <strong>1</strong> to <strong>10</strong> of <strong>15</strong> customers')

    def test_customer_list_pagination_page_two(self):
        """Page 2 returns remaining 5 customers with preserved navigation."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['customers']), 5)
        self.assertContains(response, 'Showing <strong>11</strong> to <strong>15</strong> of <strong>15</strong> customers')
        # Check that page 1 and previous links exist
        self.assertContains(response, 'page=1')

    def test_customer_list_custom_per_page(self):
        """Custom per_page=5 results in 3 pages with 5 items per page."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?per_page=5')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['customers']), 5)
        self.assertEqual(response.context['paginator'].num_pages, 3)

    def test_customer_list_show_all(self):
        """per_page=all disables pagination and renders all 15 records."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?per_page=all')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_paginated'])
        self.assertEqual(len(response.context['customers']), 15)
        self.assertContains(response, 'Showing all <strong>15</strong> customers')

    def test_customer_search_by_name(self):
        """Search query 'Alpha Customer 05' returns exactly one matching client."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?q=Alpha Customer 05')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 1)
        self.assertContains(response, 'Alpha Customer 05')
        self.assertNotContains(response, 'Alpha Customer 01')

    def test_customer_search_by_phone(self):
        """Search by phone number returns matching customer."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_customers[2]
        response = self.client.get(reverse('customer_list') + f'?q={target.phone}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, target.name)

    def test_customer_search_by_email(self):
        """Search by email returns matching customer."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_customers[3]
        response = self.client.get(reverse('customer_list') + f'?q={target.email}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, target.name)

    def test_customer_search_by_gstin(self):
        """Search by GSTIN returns the tax registered customer."""
        self.client.force_login(self.dist1_user)
        target = [c for c in self.dist1_customers if c.gstin][0]
        response = self.client.get(reverse('customer_list') + f'?q={target.gstin}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, target.name)

    def test_customer_search_by_hash_id(self):
        """Search by hash id (e.g. #123 urlencoded as %23123) correctly matches the customer PK."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_customers[0]
        response = self.client.get(reverse('customer_list') + f'?q=%23{target.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 1)
        self.assertContains(response, target.name)

    def test_customer_city_filter(self):
        """Filtering by city returns only customers residing in that city."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?city=Vadodara')
        self.assertEqual(response.status_code, 200)
        for cust in response.context['customers']:
            self.assertEqual(cust.city, 'Vadodara')

    def test_customer_pagination_preserves_query_params(self):
        """Pagination links preserve the search query and city filter."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?q=Alpha&per_page=5')
        self.assertEqual(response.status_code, 200)
        # Verify page links contain 'q=Alpha' and 'per_page=5'
        self.assertContains(response, 'page=2')
        self.assertContains(response, 'q=Alpha')
        self.assertContains(response, 'per_page=5')

    def test_customer_multi_tenant_isolation_under_search(self):
        """Distributor 1 searching for 'Beta' returns 0 results (multi-tenant boundary intact)."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('customer_list') + '?q=Beta')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertContains(response, 'No customer profiles found')

    def test_customer_admin_global_access_and_distributor_search(self):
        """Admin sees all 20 customers and can search by distributor name."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('customer_list') + '?per_page=all')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 20)
        
        # Admin search by distributor name
        search_res = self.client.get(reverse('customer_list') + '?q=Beta Retail Mart')
        self.assertEqual(search_res.status_code, 200)
        self.assertEqual(search_res.context['total_count'], 5)

    # -------------------------------------------------------------
    # PRODUCT SEARCH & PAGINATION TESTS
    # -------------------------------------------------------------
    def test_product_list_unauthenticated_redirect(self):
        """Unauthenticated requests to product list must redirect to login/landing."""
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith('/') or 'login' in response.url)

    def test_product_list_default_pagination(self):
        """Distributor 1 has 15 products; default 10 per page renders 10 products on page 1."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 15)
        self.assertTrue(response.context['is_paginated'])
        self.assertEqual(len(response.context['products']), 10)
        self.assertContains(response, 'Showing <strong>1</strong> to <strong>10</strong> of <strong>15</strong> products')

    def test_product_list_page_two(self):
        """Page 2 renders remaining 5 products."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?page=2')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context['products']), 5)
        self.assertContains(response, 'Showing <strong>11</strong> to <strong>15</strong> of <strong>15</strong> products')

    def test_product_list_show_all(self):
        """per_page=all disables pagination and renders all products."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?per_page=all')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.context['is_paginated'])
        self.assertEqual(len(response.context['products']), 15)
        self.assertContains(response, 'Showing all <strong>15</strong> products')

    def test_product_search_by_sku(self):
        """Search by SKU correctly finds the specific product."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_products[4]
        response = self.client.get(reverse('product_list') + f'?q={target.sku}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 1)
        self.assertContains(response, target.name)

    def test_product_search_by_hsn_code(self):
        """Search by HSN code returns the matching product."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_products[1]
        response = self.client.get(reverse('product_list') + f'?q={target.hsn_code}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, target.name)

    def test_product_search_by_hash_id(self):
        """Search by #ID matches product ID."""
        self.client.force_login(self.dist1_user)
        target = self.dist1_products[0]
        response = self.client.get(reverse('product_list') + f'?q=%23{target.id}')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 1)
        self.assertContains(response, target.name)

    def test_product_filter_by_category(self):
        """Category filter returns only products in that category."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?category=Electronics')
        self.assertEqual(response.status_code, 200)
        for p in response.context['products']:
            self.assertEqual(p.category, 'Electronics')

    def test_product_stock_status_in_stock(self):
        """stock_status=in_stock returns products with stock > 15."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?stock_status=in_stock')
        self.assertEqual(response.status_code, 200)
        for p in response.context['products']:
            self.assertGreater(p.stock, 15)

    def test_product_stock_status_low_stock(self):
        """stock_status=low_stock returns products with stock between 1 and 15."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?stock_status=low_stock')
        self.assertEqual(response.status_code, 200)
        for p in response.context['products']:
            self.assertTrue(0 < p.stock <= 15)

    def test_product_stock_status_out_of_stock(self):
        """stock_status=out_of_stock returns products with stock == 0."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?stock_status=out_of_stock')
        self.assertEqual(response.status_code, 200)
        for p in response.context['products']:
            self.assertEqual(p.stock, 0)

    def test_product_pagination_preserves_filters(self):
        """Pagination links in product list preserve search and filter params."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?category=Electronics&per_page=2')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'category=Electronics')
        self.assertContains(response, 'per_page=2')

    def test_product_multi_tenant_isolation(self):
        """Distributor 1 cannot find or view Distributor 2 products via search or list."""
        self.client.force_login(self.dist1_user)
        response = self.client.get(reverse('product_list') + '?q=BET-SKU')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 0)
        self.assertContains(response, 'No products found in catalog')

    def test_product_admin_global_access(self):
        """Admin sees all products (15 dist1 + 5 dist2 = 20) and can search across distributor names."""
        self.client.force_login(self.admin)
        response = self.client.get(reverse('product_list') + '?per_page=all')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['total_count'], 20)

        # Search for Beta products
        res_beta = self.client.get(reverse('product_list') + '?q=Beta Retail Mart')
        self.assertEqual(res_beta.status_code, 200)
        self.assertEqual(res_beta.context['total_count'], 5)

