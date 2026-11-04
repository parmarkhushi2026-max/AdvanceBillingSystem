from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from decimal import Decimal
from billing_app.models import UserProfile, Distributor, Customer, Product, Invoice


class BootstrapStylingLoginDashboardTestCase(TestCase):
    """
    Test suite verifying Bootstrap 5 styling integration for:
    - Base layout (Bootstrap 5.3 CDN CSS & JS Bundle)
    - Admin Login page (clean cards, input groups, badges, pills)
    - Distributor Login page (clean cards, input groups, badges, POS theme)
    - Admin Welcome Dashboard (Bootstrap grid, stat cards, hover-lift, responsive tables)
    - Distributor Dashboard (Bootstrap grid, collection cards, responsive tables)
    """

    def setUp(self):
        self.client = Client()

        # Admin User & Profile
        self.admin_pass = 'AdminPass123!'
        self.admin = User.objects.create_superuser(
            username='bootstrap_admin',
            email='admin@advancebilling.com',
            password=self.admin_pass
        )
        self.admin.first_name = 'Rajesh'
        self.admin.last_name = 'Sharma'
        self.admin.save()
        UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': 'ADMIN', 'business_name': 'Advance HQ Admin'}
        )

        # Distributor User & Profile
        self.dist_pass = 'DistPass123!'
        self.dist_user = User.objects.create_user(
            username='bootstrap_distributor',
            email='dist@agency.com',
            password=self.dist_pass
        )
        UserProfile.objects.get_or_create(
            user=self.dist_user,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Apex Wholesale Agency', 'upi_id': 'apexwholesale@okaxis'}
        )

        # Distributor Master Model Record
        self.distributor = Distributor.objects.create(
            user=self.dist_user,
            name='Apex Wholesale Agency',
            business_name='Apex Wholesale Agency',
            phone='9876543210',
            email='apex@wholesale.com',
            city='Ahmedabad',
            state='Gujarat',
            upi_id='apexwholesale@okaxis',
            gstin='24AAACA1234A1Z5',
            is_active=True
        )

        # Sample Customer, Product & Invoice for Admin & Distributor
        self.customer = Customer.objects.create(
            name='Mahesh Enterprises',
            phone='9988776655',
            city='Surat',
            gstin='24AABCM9988Z1',
            created_by=self.dist_user
        )
        self.product = Product.objects.create(
            name='Thermal Receipt Paper Rolls',
            category='Consumables',
            sku='BT-ROLL-01',
            price=Decimal('250.00'),
            stock=150,
            unit='Rolls',
            created_by=self.dist_user
        )
        self.invoice = Invoice.objects.create(
            invoice_number='INV-2026-BT-001',
            customer=self.customer,
            distributor=self.dist_user,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
            subtotal=Decimal('500.00'),
            grand_total=Decimal('590.00'),
            payment_status='PAID',
            payment_method='UPI'
        )

    # -------------------------------------------------------------
    # 1. Base Layout Bootstrap CDN Integration Tests
    # -------------------------------------------------------------
    def test_base_layout_includes_bootstrap_5_cdn_assets(self):
        """Verify rendered login page includes Bootstrap 5.3 CSS and JS bundle from CDN."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        content = response.content.decode('utf-8')
        self.assertIn('bootstrap@5.3.3/dist/css/bootstrap.min.css', content)
        self.assertIn('bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js', content)

    # -------------------------------------------------------------
    # 2. Admin Login Page Bootstrap Styling Tests
    # -------------------------------------------------------------
    def test_admin_login_renders_bootstrap_components(self):
        """Admin login renders with clean Bootstrap container, card, pills, and input groups."""
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login_admin.html')
        content = response.content.decode('utf-8')

        # Core Bootstrap utility & component classes
        self.assertIn('container', content)
        self.assertIn('card', content)
        self.assertIn('shadow-lg', content)
        self.assertIn('rounded-4', content)
        self.assertIn('row g-0', content)
        self.assertIn('nav nav-pills', content)
        self.assertIn('input-group', content)
        self.assertIn('form-control', content)
        self.assertIn('form-check', content)
        self.assertIn('btn btn-primary', content)

        # Essential functional elements
        self.assertIn('id="username"', content)
        self.assertIn('id="password"', content)
        self.assertIn('id="togglePasswordBtn"', content)
        self.assertIn('id="capsWarningAlert"', content)
        self.assertIn('id="rememberMe"', content)
        self.assertIn('id="btnAdminSubmit"', content)
        self.assertIn('btn-quick-fill', content)

    # -------------------------------------------------------------
    # 3. Distributor Login Page Bootstrap Styling Tests
    # -------------------------------------------------------------
    def test_distributor_login_renders_bootstrap_components(self):
        """Distributor login renders with clean Bootstrap container, card, pills, and green button."""
        response = self.client.get(reverse('distributor_login'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login_distributor.html')
        content = response.content.decode('utf-8')

        # Core Bootstrap utility & component classes
        self.assertIn('container', content)
        self.assertIn('card', content)
        self.assertIn('shadow-lg', content)
        self.assertIn('rounded-4', content)
        self.assertIn('row g-0', content)
        self.assertIn('nav nav-pills', content)
        self.assertIn('input-group', content)
        self.assertIn('form-control', content)
        self.assertIn('form-check', content)
        self.assertIn('btn btn-success', content)

        # Essential functional elements
        self.assertIn('id="username"', content)
        self.assertIn('id="password"', content)
        self.assertIn('id="togglePasswordBtn"', content)
        self.assertIn('id="capsWarningAlert"', content)
        self.assertIn('id="rememberMe"', content)
        self.assertIn('id="btnDistributorSubmit"', content)
        self.assertIn('btn-quick-fill', content)

    # -------------------------------------------------------------
    # 4. Admin Welcome Dashboard Bootstrap Styling Tests
    # -------------------------------------------------------------
    def test_admin_dashboard_renders_bootstrap_grid_and_components(self):
        """Admin dashboard displays Bootstrap hero card, metrics row, tables, badges, and hover-lift."""
        self.client.login(username='bootstrap_admin', password=self.admin_pass)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/admin_dashboard.html')
        content = response.content.decode('utf-8')

        # Hero Banner with Bootstrap card
        self.assertIn('card border-0 rounded-4 shadow-sm', content)
        self.assertIn('Welcome,', content)
        self.assertIn('Live DB Connected', content)

        # 5 Metrics row with Bootstrap classes
        self.assertIn('row g-3 mb-4', content)
        self.assertIn('hover-lift', content)
        self.assertIn('Total Customers', content)
        self.assertIn('Total Products', content)
        self.assertIn('Total Invoices', content)
        self.assertIn('Settled Revenue', content)
        self.assertIn('Distributor Master', content)

        # Live Database Tables overview
        self.assertIn('Customer Database Table', content)
        self.assertIn('Product Database Table', content)
        self.assertIn('Registered Distributors Master Table', content)
        self.assertIn('table table-hover align-middle mb-0', content)

        # Recent Invoices Table & Action Buttons
        self.assertIn('Recent System Invoices', content)
        self.assertIn('btn-group btn-group-sm', content)
        self.assertIn('btn btn-outline-primary', content)
        self.assertIn('btn btn-outline-danger', content)

        # Chart.js Canvases preserved
        self.assertIn('id="fintechDualFlowCanvas"', content)
        self.assertIn('id="fintechStatusCanvas"', content)

    # -------------------------------------------------------------
    # 5. Distributor Dashboard Bootstrap Styling Tests
    # -------------------------------------------------------------
    def test_distributor_dashboard_renders_bootstrap_grid_and_components(self):
        """Distributor dashboard displays Bootstrap hero card, 4 metric cards, and recent table."""
        self.client.login(username='bootstrap_distributor', password=self.dist_pass)
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'dashboard/distributor_dashboard.html')
        content = response.content.decode('utf-8')

        # Hero Banner with Bootstrap card
        self.assertIn('card border-0 rounded-4 shadow-sm', content)
        self.assertIn('Apex Wholesale Agency', content)
        self.assertIn('apexwholesale@okaxis', content)

        # 4 Metric Cards in Bootstrap grid
        self.assertIn('row g-3 mb-4', content)
        self.assertIn('My Collections', content)
        self.assertIn('Invoices Issued', content)
        self.assertIn('Catalog Products', content)
        self.assertIn('My Customers', content)

        # Table & Action Buttons
        self.assertIn('My Recent Bills & Invoices', content)
        self.assertIn('table table-hover align-middle mb-0', content)
        self.assertIn('btn-group btn-group-sm', content)
        self.assertIn('btn btn-outline-primary', content)

        # Chart.js Canvases preserved
        self.assertIn('id="fintechDualFlowCanvas"', content)
        self.assertIn('id="fintechStatusCanvas"', content)
