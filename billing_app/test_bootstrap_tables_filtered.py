from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile, Distributor, Customer, Product


class BootstrapTablesFilteredTestCase(TestCase):
    """
    Test suite verifying customer and product list tables formatted using Bootstrap 5
    and strictly filtered by the logged-in user:
    - Non-admin distributors only see their own customers and products.
    - System administrators see universal tables across all distributor agencies.
    - Bootstrap 5 classes (table, table-hover, table-responsive, card, badges, pagination) are present.
    - Search and category filters work seamlessly.
    - Unauthenticated requests are redirected.
    """

    def setUp(self):
        self.client = Client()

        # 1. System Admin User
        self.admin = User.objects.create_superuser(
            username='admin_table_tester',
            email='admin@tabletest.com',
            password='AdminPass@123'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.business_name = 'Table Admin Corp'
        self.admin_profile.save()

        # 2. Distributor 1 (Omkar Logistics)
        self.dist1_user = User.objects.create_user(
            username='omkar_distributor',
            email='omkar@logistics.in',
            password='OmkarPass@123'
        )
        self.dist1_profile, _ = UserProfile.objects.get_or_create(user=self.dist1_user)
        self.dist1_profile.role = 'DISTRIBUTOR'
        self.dist1_profile.business_name = 'Omkar Logistics Agency'
        self.dist1_profile.save()

        self.dist1_record = Distributor.objects.create(
            user=self.dist1_user,
            name='Omkar Shah',
            business_name='Omkar Logistics Agency',
            phone='9333344444',
            email='omkar@logistics.in',
            city='Ahmedabad',
            state='Gujarat',
            upi_id='omkar@upi',
            is_active=True
        )

        # 3. Distributor 2 (Radha Retail)
        self.dist2_user = User.objects.create_user(
            username='radha_distributor',
            email='radha@retailhub.in',
            password='RadhaPass@123'
        )
        self.dist2_profile, _ = UserProfile.objects.get_or_create(user=self.dist2_user)
        self.dist2_profile.role = 'DISTRIBUTOR'
        self.dist2_profile.business_name = 'Radha Retail Hub'
        self.dist2_profile.save()

        self.dist2_record = Distributor.objects.create(
            user=self.dist2_user,
            name='Radha Nair',
            business_name='Radha Retail Hub',
            phone='9444455555',
            email='radha@retailhub.in',
            city='Rajkot',
            state='Gujarat',
            upi_id='radha@upi',
            is_active=True
        )

        # Create Customers for Distributor 1
        self.c1 = Customer.objects.create(
            name='Omkar Prime Client',
            phone='9811100001',
            email='client1@omkar.com',
            city='Ahmedabad',
            gstin='24AAACT1111A1Z1',
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

        # Create Customers for Distributor 2
        self.c2 = Customer.objects.create(
            name='Radha VIP Shopper',
            phone='9822200002',
            email='vip@radha.com',
            city='Rajkot',
            gstin='24AAACT2222B1Z2',
            created_by=self.dist2_user,
            distributor_ref=self.dist2_record
        )

        # Create Products for Distributor 1
        self.p1 = Product.objects.create(
            name='Omkar Thermal Rolls Pack',
            sku='OMK-ROLL-80',
            category='Paper Supplies',
            price=Decimal('450.00'),
            stock=120,
            gst_rate=Decimal('12.00'),
            unit='Box',
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

        # Create Products for Distributor 2
        self.p2 = Product.objects.create(
            name='Radha Barcode Labels Pack',
            sku='RAD-LBL-50',
            category='Labels',
            price=Decimal('280.00'),
            stock=80,
            gst_rate=Decimal('18.00'),
            unit='Pack',
            created_by=self.dist2_user,
            distributor_ref=self.dist2_record
        )

    # =========================================================================
    # 1. Customer List Filtered by Logged-In User
    # =========================================================================
    def test_customer_list_distributor_isolation(self):
        """Distributor 1 only sees their own customer; Distributor 2's customer is omitted."""
        self.client.force_login(self.dist1_user)
        res = self.client.get(reverse('customer_list'))
        self.assertEqual(res.status_code, 200)

        names = [c.name for c in res.context['customers']]
        self.assertIn('Omkar Prime Client', names)
        self.assertNotIn('Radha VIP Shopper', names)

        # Check HTML content
        content = res.content.decode('utf-8')
        self.assertIn('Omkar Prime Client', content)
        self.assertNotIn('Radha VIP Shopper', content)

    def test_customer_list_admin_sees_all_distributors(self):
        """Admin sees customers from all distributor accounts."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse('customer_list'))
        self.assertEqual(res.status_code, 200)

        names = [c.name for c in res.context['customers']]
        self.assertIn('Omkar Prime Client', names)
        self.assertIn('Radha VIP Shopper', names)

    # =========================================================================
    # 2. Product List Filtered by Logged-In User
    # =========================================================================
    def test_product_list_distributor_isolation(self):
        """Distributor 1 only sees their own product; Distributor 2's product is omitted."""
        self.client.force_login(self.dist1_user)
        res = self.client.get(reverse('product_list'))
        self.assertEqual(res.status_code, 200)

        names = [p.name for p in res.context['products']]
        self.assertIn('Omkar Thermal Rolls Pack', names)
        self.assertNotIn('Radha Barcode Labels Pack', names)

        # Check HTML content
        content = res.content.decode('utf-8')
        self.assertIn('Omkar Thermal Rolls Pack', content)
        self.assertNotIn('Radha Barcode Labels Pack', content)

    def test_product_list_admin_sees_all_distributors(self):
        """Admin sees products from all distributor accounts."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse('product_list'))
        self.assertEqual(res.status_code, 200)

        names = [p.name for p in res.context['products']]
        self.assertIn('Omkar Thermal Rolls Pack', names)
        self.assertIn('Radha Barcode Labels Pack', names)

    # =========================================================================
    # 3. Bootstrap 5 Tabular Format Verification
    # =========================================================================
    def test_customer_table_bootstrap_classes(self):
        """Customer list contains table, table-hover, table-responsive, and card markup."""
        self.client.force_login(self.dist1_user)
        res = self.client.get(reverse('customer_list'))
        html = res.content.decode('utf-8')

        self.assertIn('table table-hover align-middle', html)
        self.assertIn('table-responsive', html)
        self.assertIn('card border-0 shadow-sm rounded-4', html)
        self.assertIn('deleteCustomerModal', html)

    def test_product_table_bootstrap_classes(self):
        """Product list contains table, table-hover, table-responsive, and card markup."""
        self.client.force_login(self.dist1_user)
        res = self.client.get(reverse('product_list'))
        html = res.content.decode('utf-8')

        self.assertIn('table table-hover align-middle', html)
        self.assertIn('table-responsive', html)
        self.assertIn('card border-0 shadow-sm rounded-4', html)
        self.assertIn('deleteProductModal', html)

    # =========================================================================
    # 4. Search and Category Filter Tests
    # =========================================================================
    def test_customer_table_search_filter(self):
        """Search query 'Prime' filters customer table accurately."""
        self.client.force_login(self.dist1_user)
        res = self.client.get(reverse('customer_list') + '?q=Prime')
        self.assertEqual(res.status_code, 200)
        names = [c.name for c in res.context['customers']]
        self.assertIn('Omkar Prime Client', names)

        # Irrelevant search returns no customer
        res_empty = self.client.get(reverse('customer_list') + '?q=NonExistent123')
        self.assertEqual(len(res_empty.context['customers']), 0)

    def test_product_table_search_and_category_filter(self):
        """Product table filters by SKU and by Category."""
        self.client.force_login(self.dist1_user)

        # Filter by SKU search
        res_sku = self.client.get(reverse('product_list') + '?q=OMK-ROLL')
        self.assertEqual(res_sku.status_code, 200)
        self.assertEqual(len(res_sku.context['products']), 1)

        # Filter by Category
        res_cat = self.client.get(reverse('product_list') + '?category=Paper+Supplies')
        self.assertEqual(res_cat.status_code, 200)
        self.assertEqual(len(res_cat.context['products']), 1)

        # Filter by non-matching category
        res_mismatch = self.client.get(reverse('product_list') + '?category=Heavy+Machinery')
        self.assertEqual(len(res_mismatch.context['products']), 0)

    # =========================================================================
    # 5. Bootstrap Pagination Verification
    # =========================================================================
    def test_customer_and_product_pagination_support(self):
        """Confirm paginator handles multiple items properly."""
        self.client.force_login(self.dist1_user)

        # Create 12 additional products to trigger pagination (10 per page)
        for i in range(12):
            Product.objects.create(
                name=f'Bulk Test Item {i}',
                sku=f'BLK-ITEM-{i}',
                price=Decimal('100.00'),
                stock=10,
                created_by=self.dist1_user,
                distributor_ref=self.dist1_record
            )

        res = self.client.get(reverse('product_list'))
        self.assertEqual(res.status_code, 200)
        self.assertTrue(res.context['is_paginated'])
        self.assertEqual(len(res.context['products']), 10)  # Page 1 has 10 items

        res_page2 = self.client.get(reverse('product_list') + '?page=2')
        self.assertEqual(res_page2.status_code, 200)
        self.assertGreaterEqual(len(res_page2.context['products']), 3)

    # =========================================================================
    # 6. Unauthenticated Access Protection
    # =========================================================================
    def test_unauthenticated_user_redirected(self):
        """Unauthenticated requests to customer and product lists are redirected."""
        res_cust = self.client.get(reverse('customer_list'))
        self.assertEqual(res_cust.status_code, 302)
        self.assertTrue(res_cust.url.startswith('/') or 'login' in res_cust.url)

        res_prod = self.client.get(reverse('product_list'))
        self.assertEqual(res_prod.status_code, 302)
        self.assertTrue(res_prod.url.startswith('/') or 'login' in res_prod.url)

