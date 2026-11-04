from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Distributor, UserProfile, Customer, Invoice, InvoiceItem, Product


class AdminWelcomeDashboardAndDistributorIsolationTestCase(TestCase):
    """
    Automated test suite verifying:
    Part 1:
      - Admin Welcome Dashboard displaying total customers, total products, and total invoices from the DB.
      - Hero banner greeting, live DB summary cards, and recent records tables.
      - Access protection (@admin_required).
    Part 2:
      - User role logic enforcing multi-tenant isolation so Distributors see ONLY their customers, products, and invoices.
      - Admin visibility over all records across all distributors.
      - Cross-tenant access prevention on invoice detail and preview endpoints.
      - Dynamic dropdown isolation on invoice creation form.
    """

    def setUp(self):
        self.client = Client()

        # 1. Super Admin
        self.admin_user = User.objects.create_superuser(
            username='super_admin',
            email='admin@billingcorp.com',
            password='AdminPass@123',
            first_name='Super',
            last_name='Admin'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.business_name = 'Advance Billing HQ'
        self.admin_profile.save()

        # 2. Distributor 1 (Rahul Sharma - Sharma Agency)
        self.dist1_user = User.objects.create_user(
            username='distributor1',
            email='rahul@sharmaagency.in',
            password='DistPass@123',
            first_name='Rahul',
            last_name='Sharma'
        )
        self.dist1_profile, _ = UserProfile.objects.get_or_create(user=self.dist1_user)
        self.dist1_profile.role = 'DISTRIBUTOR'
        self.dist1_profile.business_name = 'Sharma Tech Distribution'
        self.dist1_profile.upi_id = 'sharmadist@upi'
        self.dist1_profile.save()

        self.dist1_record = Distributor.objects.create(
            user=self.dist1_user,
            name='Rahul Sharma',
            business_name='Sharma Tech Distribution',
            phone='+91 98111 22233',
            city='Ahmedabad',
            gstin='24AAECS1111F1Z1',
            upi_id='sharmadist@upi'
        )

        # 3. Distributor 2 (Priya Patel - Patel Enterprises)
        self.dist2_user = User.objects.create_user(
            username='distributor2',
            email='priya@patelenterprises.in',
            password='DistPass@123',
            first_name='Priya',
            last_name='Patel'
        )
        self.dist2_profile, _ = UserProfile.objects.get_or_create(user=self.dist2_user)
        self.dist2_profile.role = 'DISTRIBUTOR'
        self.dist2_profile.business_name = 'Patel Enterprises'
        self.dist2_profile.upi_id = 'pateldist@upi'
        self.dist2_profile.save()

        self.dist2_record = Distributor.objects.create(
            user=self.dist2_user,
            name='Priya Patel',
            business_name='Patel Enterprises',
            phone='+91 98222 33344',
            city='Surat',
            gstin='24AABCP2222K1Z2',
            upi_id='pateldist@upi'
        )

        # 4. Customers for Distributor 1
        self.cust1_d1 = Customer.objects.create(
            name='Aarav Retailers',
            phone='9811100001',
            city='Ahmedabad',
            gstin='24AABCA1001A1Z1',
            created_by=self.dist1_user
        )
        self.cust2_d1 = Customer.objects.create(
            name='Bhavik Stationery',
            phone='9811100002',
            city='Gandhinagar',
            created_by=self.dist1_user
        )

        # 5. Customers for Distributor 2
        self.cust1_d2 = Customer.objects.create(
            name='Chirag Supermarket',
            phone='9822200001',
            city='Surat',
            gstin='24AABCC2001C1Z3',
            created_by=self.dist2_user
        )
        self.cust2_d2 = Customer.objects.create(
            name='Deepak Electronics',
            phone='9822200002',
            city='Navsari',
            created_by=self.dist2_user
        )

        # 6. Products for Distributor 1
        self.prod1_d1 = Product.objects.create(
            name='POS Thermal Terminal X1',
            sku='D1-POS-01',
            category='Hardware',
            price=Decimal('15000.00'),
            stock=10,
            created_by=self.dist1_user
        )
        self.prod2_d1 = Product.objects.create(
            name='Paper Rolls 80mm',
            sku='D1-ROLL-01',
            category='Supplies',
            price=Decimal('500.00'),
            stock=100,
            created_by=self.dist1_user
        )

        # 7. Products for Distributor 2
        self.prod1_d2 = Product.objects.create(
            name='Barcode Scanner Wireless',
            sku='D2-SCN-01',
            category='Hardware',
            price=Decimal('3500.00'),
            stock=20,
            created_by=self.dist2_user
        )
        self.prod2_d2 = Product.objects.create(
            name='Receipt Printer Bluetooth',
            sku='D2-PRN-01',
            category='Hardware',
            price=Decimal('6200.00'),
            stock=15,
            created_by=self.dist2_user
        )

        # 8. Invoices for Distributor 1
        self.inv1_d1 = Invoice.objects.create(
            invoice_number='INV-D1-001',
            distributor=self.dist1_user,
            customer=self.cust1_d1,
            customer_name=self.cust1_d1.name,
            customer_phone=self.cust1_d1.phone,
            subtotal=Decimal('15000.00'),
            tax_amount=Decimal('2700.00'),
            grand_total=Decimal('17700.00'),
            payment_status='PAID',
            skip_qr_generation=True
        )
        self.inv2_d1 = Invoice.objects.create(
            invoice_number='INV-D1-002',
            distributor=self.dist1_user,
            customer=self.cust2_d1,
            customer_name=self.cust2_d1.name,
            customer_phone=self.cust2_d1.phone,
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('120.00'),
            grand_total=Decimal('1120.00'),
            payment_status='PENDING',
            skip_qr_generation=True
        )

        # 9. Invoices for Distributor 2
        self.inv1_d2 = Invoice.objects.create(
            invoice_number='INV-D2-001',
            distributor=self.dist2_user,
            customer=self.cust1_d2,
            customer_name=self.cust1_d2.name,
            customer_phone=self.cust1_d2.phone,
            subtotal=Decimal('7000.00'),
            tax_amount=Decimal('1260.00'),
            grand_total=Decimal('8260.00'),
            payment_status='PAID',
            skip_qr_generation=True
        )

    # =========================================================================
    # Part 1: Admin Welcome Dashboard Tests
    # =========================================================================

    def test_01_admin_welcome_dashboard_renders_with_exact_db_counts(self):
        """Verify Admin Welcome Dashboard page fetches and renders total customers, products, and invoices from DB."""
        self.client.login(username='super_admin', password='AdminPass@123')
        url = reverse('admin_dashboard')
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin_dashboard.html')

        # Verify DB counts in context
        self.assertEqual(response.context['total_customers'], Customer.objects.count())
        self.assertEqual(response.context['total_products'], Product.objects.count())
        self.assertEqual(response.context['total_invoices'], Invoice.objects.count())
        self.assertGreaterEqual(response.context['total_customers'], 4)
        self.assertGreaterEqual(response.context['total_products'], 4)
        self.assertGreaterEqual(response.context['total_invoices'], 3)

        # Verify rendered HTML contains Welcome message and metric cards
        self.assertContains(response, 'Welcome')
        self.assertContains(response, 'Total Customers')
        self.assertContains(response, 'Total Products')
        self.assertContains(response, 'Total Invoices')
        self.assertContains(response, 'Customer Database Table')
        self.assertContains(response, 'Product Database Table')

    def test_02_admin_welcome_dashboard_access_protection(self):
        """Verify Admin Welcome Dashboard is strictly protected against unauthenticated and Distributor users."""
        url = reverse('admin_dashboard')

        # Anonymous access redirected to login
        self.client.logout()
        res_anon = self.client.get(url)
        self.assertIn(res_anon.status_code, (302, 403))

        # Distributor access denied and redirected
        self.client.login(username='distributor1', password='DistPass@123')
        res_dist = self.client.get(url)
        self.assertIn(res_dist.status_code, (302, 403))

    def test_03_foreign_keys_associated_on_customers_products_invoices(self):
        """Verify Customer, Product, and Invoice models have all needed foreign keys populated."""
        # Customer Foreign Keys
        self.assertEqual(self.cust1_d1.created_by, self.dist1_user)
        self.assertEqual(self.cust1_d1.distributor_ref, self.dist1_record)
        self.assertEqual(self.cust1_d2.created_by, self.dist2_user)
        self.assertEqual(self.cust1_d2.distributor_ref, self.dist2_record)

        # Product Foreign Keys
        self.assertEqual(self.prod1_d1.created_by, self.dist1_user)
        self.assertEqual(self.prod1_d1.distributor_ref, self.dist1_record)
        self.assertEqual(self.prod1_d2.created_by, self.dist2_user)
        self.assertEqual(self.prod1_d2.distributor_ref, self.dist2_record)

        # Invoice Foreign Keys
        self.assertEqual(self.inv1_d1.distributor, self.dist1_user)
        self.assertEqual(self.inv1_d1.distributor_ref, self.dist1_record)
        self.assertEqual(self.inv1_d1.customer, self.cust1_d1)
        self.assertEqual(self.inv1_d2.distributor, self.dist2_user)
        self.assertEqual(self.inv1_d2.distributor_ref, self.dist2_record)
        self.assertEqual(self.inv1_d2.customer, self.cust1_d2)

    # =========================================================================
    # Part 2: Distributor User Role Logic & Multi-Tenant Data Isolation Tests
    # =========================================================================

    def test_04_distributor_sees_only_their_customers(self):
        """Verify Distributors see ONLY their customers in customer_list_view, while Admin sees all."""
        # Distributor 1 login
        self.client.login(username='distributor1', password='DistPass@123')
        res_d1 = self.client.get(reverse('customer_list'))
        self.assertEqual(res_d1.status_code, 200)

        # D1 must see their own customers
        self.assertContains(res_d1, 'Aarav Retailers')
        self.assertContains(res_d1, 'Bhavik Stationery')
        # D1 must NOT see D2's customers
        self.assertNotContains(res_d1, 'Chirag Supermarket')
        self.assertNotContains(res_d1, 'Deepak Electronics')
        self.assertEqual(res_d1.context['total_count'], 2)

        # Distributor 2 login
        self.client.login(username='distributor2', password='DistPass@123')
        res_d2 = self.client.get(reverse('customer_list'))
        self.assertEqual(res_d2.status_code, 200)

        # D2 must see their own customers
        self.assertContains(res_d2, 'Chirag Supermarket')
        self.assertContains(res_d2, 'Deepak Electronics')
        # D2 must NOT see D1's customers
        self.assertNotContains(res_d2, 'Aarav Retailers')
        self.assertNotContains(res_d2, 'Bhavik Stationery')
        self.assertEqual(res_d2.context['total_count'], 2)

        # Admin login: sees ALL customers
        self.client.login(username='super_admin', password='AdminPass@123')
        res_admin = self.client.get(reverse('customer_list'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'Aarav Retailers')
        self.assertContains(res_admin, 'Chirag Supermarket')
        self.assertGreaterEqual(res_admin.context['total_count'], 4)

    def test_05_distributor_sees_only_their_products(self):
        """Verify Distributors see ONLY their products in product_list_view, while Admin sees all."""
        # Distributor 1 login
        self.client.login(username='distributor1', password='DistPass@123')
        res_d1 = self.client.get(reverse('product_list'))
        self.assertEqual(res_d1.status_code, 200)

        # D1 sees only D1 products
        self.assertContains(res_d1, 'POS Thermal Terminal X1')
        self.assertContains(res_d1, 'Paper Rolls 80mm')
        self.assertNotContains(res_d1, 'Barcode Scanner Wireless')
        self.assertNotContains(res_d1, 'Receipt Printer Bluetooth')
        self.assertEqual(res_d1.context['total_count'], 2)

        # Distributor 2 login
        self.client.login(username='distributor2', password='DistPass@123')
        res_d2 = self.client.get(reverse('product_list'))
        self.assertEqual(res_d2.status_code, 200)

        # D2 sees only D2 products
        self.assertContains(res_d2, 'Barcode Scanner Wireless')
        self.assertContains(res_d2, 'Receipt Printer Bluetooth')
        self.assertNotContains(res_d2, 'POS Thermal Terminal X1')
        self.assertNotContains(res_d2, 'Paper Rolls 80mm')
        self.assertEqual(res_d2.context['total_count'], 2)

        # Admin login sees ALL products
        self.client.login(username='super_admin', password='AdminPass@123')
        res_admin = self.client.get(reverse('product_list'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'POS Thermal Terminal X1')
        self.assertContains(res_admin, 'Barcode Scanner Wireless')
        self.assertGreaterEqual(res_admin.context['total_count'], 4)

    def test_06_distributor_sees_only_their_invoices_in_table(self):
        """Verify Distributors see ONLY their invoices in invoice_list_view and invoice_bootstrap_table_view."""
        # Distributor 1 login
        self.client.login(username='distributor1', password='DistPass@123')
        res_d1 = self.client.get(reverse('invoice_list'))
        self.assertEqual(res_d1.status_code, 200)

        # D1 invoices present
        self.assertContains(res_d1, 'INV-D1-001')
        self.assertContains(res_d1, 'INV-D1-002')
        # D2 invoices absent
        self.assertNotContains(res_d1, 'INV-D2-001')

        # Dedicated Bootstrap table view
        res_d1_tbl = self.client.get(reverse('invoice_bootstrap_table'))
        self.assertEqual(res_d1_tbl.status_code, 200)
        self.assertContains(res_d1_tbl, 'INV-D1-001')
        self.assertNotContains(res_d1_tbl, 'INV-D2-001')

        # Distributor 2 login
        self.client.login(username='distributor2', password='DistPass@123')
        res_d2 = self.client.get(reverse('invoice_list'))
        self.assertEqual(res_d2.status_code, 200)
        self.assertContains(res_d2, 'INV-D2-001')
        self.assertNotContains(res_d2, 'INV-D1-001')
        self.assertNotContains(res_d2, 'INV-D1-002')

        # Admin login sees all invoices across both distributors
        self.client.login(username='super_admin', password='AdminPass@123')
        res_admin = self.client.get(reverse('invoice_list'))
        self.assertEqual(res_admin.status_code, 200)
        self.assertContains(res_admin, 'INV-D1-001')
        self.assertContains(res_admin, 'INV-D1-002')
        self.assertContains(res_admin, 'INV-D2-001')

    def test_07_distributor_cross_tenant_invoice_access_denied(self):
        """Verify a distributor is blocked from viewing another distributor's invoice detail or preview."""
        # Distributor 1 tries to view Distributor 2's invoice
        self.client.login(username='distributor1', password='DistPass@123')

        url_detail = reverse('invoice_detail', args=[self.inv1_d2.id])
        res_detail = self.client.get(url_detail)
        self.assertIn(res_detail.status_code, (302, 403))

        url_preview = reverse('invoice_preview', args=[self.inv1_d2.id])
        res_preview = self.client.get(url_preview)
        self.assertIn(res_preview.status_code, (302, 403))

        # Admin CAN view any distributor's invoice
        self.client.login(username='super_admin', password='AdminPass@123')
        res_admin_view = self.client.get(url_detail)
        self.assertEqual(res_admin_view.status_code, 200)

    def test_08_distributor_dashboard_metrics_isolated(self):
        """Verify distributor dashboard calculates metrics strictly from their own DB data."""
        # Distributor 1 Dashboard
        self.client.login(username='distributor1', password='DistPass@123')
        res_d1 = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(res_d1.status_code, 200)
        self.assertEqual(res_d1.context['invoice_count'], 2)
        self.assertEqual(res_d1.context['total_revenue'], Decimal('17700.00'))
        self.assertEqual(res_d1.context['products_count'], 2)
        self.assertEqual(res_d1.context['customers_count'], 2)

        # Distributor 2 Dashboard
        self.client.login(username='distributor2', password='DistPass@123')
        res_d2 = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(res_d2.status_code, 200)
        self.assertEqual(res_d2.context['invoice_count'], 1)
        self.assertEqual(res_d2.context['total_revenue'], Decimal('8260.00'))
        self.assertEqual(res_d2.context['products_count'], 2)
        self.assertEqual(res_d2.context['customers_count'], 2)

    def test_09_create_invoice_dropdown_filters_distributor_customers(self):
        """Verify that create_invoice_view dropdown contains only the logged-in distributor's customers."""
        self.client.login(username='distributor1', password='DistPass@123')
        res = self.client.get(reverse('create_invoice'))
        self.assertEqual(res.status_code, 200)

        form_customers = res.context['form'].fields['customer'].queryset
        self.assertIn(self.cust1_d1, form_customers)
        self.assertIn(self.cust2_d1, form_customers)
        self.assertNotIn(self.cust1_d2, form_customers)
        self.assertNotIn(self.cust2_d2, form_customers)

    def test_10_api_all_invoices_details_distributor_isolation(self):
        """Verify /api/invoices/details/ enforces tenant isolation for distributor API calls."""
        self.client.login(username='distributor1', password='DistPass@123')
        res_d1 = self.client.get(reverse('api_all_invoices_details'))
        self.assertEqual(res_d1.status_code, 200)
        data_d1 = res_d1.json()

        # D1 must receive only 2 invoices
        numbers_d1 = [inv['invoice_number'] for inv in data_d1['invoices']]
        self.assertIn('INV-D1-001', numbers_d1)
        self.assertIn('INV-D1-002', numbers_d1)
        self.assertNotIn('INV-D2-001', numbers_d1)

