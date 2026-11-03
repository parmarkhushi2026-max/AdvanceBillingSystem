from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import Distributor, UserProfile, Customer, Invoice, InvoiceItem, Product
from billing_app.forms import DistributorForm


class DistributorModelAndAdminTestCase(TestCase):
    """
    Comprehensive test suite verifying:
    1. Distributor model table creation, fields, relationships, and computed properties.
    2. Adding, updating, and querying distributor records via Django Admin.
    3. Distributor management in Admin Portal (listing, search, filter, and add form).
    4. Two-way synchronization with UserProfile and Invoice linkages.
    """

    def setUp(self):
        self.client = Client()

        # Admin User
        self.admin_user = User.objects.create_superuser(
            username='admin_test',
            email='admin@testcorp.com',
            password='Password@123'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin_user)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.business_name = 'Apex Billing Admin HQ'
        self.admin_profile.phone = '+91 99000 11223'
        self.admin_profile.save()

        # Distributor User
        self.dist_user = User.objects.create_user(
            username='dist_rahul',
            email='rahul@sharmadist.com',
            password='Password@123',
            first_name='Rahul',
            last_name='Sharma'
        )
        self.dist_profile, _ = UserProfile.objects.get_or_create(user=self.dist_user)
        self.dist_profile.role = 'DISTRIBUTOR'
        self.dist_profile.business_name = 'Sharma Tech & Retail Distribution'
        self.dist_profile.phone = '+91 98123 45678'
        self.dist_profile.upi_id = 'sharmadist@upi'
        self.dist_profile.save()

        # Customer & Product for Invoices
        self.customer = Customer.objects.create(
            name='Pooja Electronics',
            phone='9876543210',
            city='Ahmedabad',
            created_by=self.dist_user
        )
        self.product = Product.objects.create(
            name='POS Machine X1',
            price=Decimal('10000.00'),
            gst_rate=Decimal('18.00'),
            stock=50,
            created_by=self.dist_user
        )

    def test_01_distributor_model_creation_and_attributes(self):
        """Verify Distributor table record creation, fields, and string representation."""
        dist = Distributor.objects.create(
            user=self.dist_user,
            name='Rahul Sharma',
            business_name='Sharma Tech & Retail Distribution',
            phone='+91 98123 45678',
            email='rahul@sharmadist.com',
            address='Plot 42, Electronic Zone, GIDC',
            city='Ahmedabad',
            state='Gujarat',
            pincode='382024',
            gstin='24AAECS1234F1Z9',
            upi_id='sharmadist@upi',
            is_active=True
        )

        self.assertIsNotNone(dist.id)
        self.assertEqual(dist.name, 'Rahul Sharma')
        self.assertEqual(dist.business_name, 'Sharma Tech & Retail Distribution')
        self.assertEqual(dist.gstin, '24AAECS1234F1Z9')
        self.assertEqual(dist.upi_id, 'sharmadist@upi')
        self.assertTrue(dist.is_active)
        self.assertEqual(str(dist), 'Sharma Tech & Retail Distribution (Rahul Sharma)')

    def test_02_distributor_save_syncs_with_user_profile(self):
        """Verify saving Distributor updates or verifies associated UserProfile."""
        new_user = User.objects.create_user(
            username='dist_new',
            email='new@agency.com',
            password='PassWord123'
        )
        dist = Distributor.objects.create(
            user=new_user,
            name='Vikram Patel',
            business_name='Patel Wholesale Trading',
            phone='+91 98888 77777',
            upi_id='pateltrade@upi'
        )

        profile = UserProfile.objects.get(user=new_user)
        self.assertEqual(profile.role, 'DISTRIBUTOR')
        self.assertEqual(profile.business_name, 'Patel Wholesale Trading')
        self.assertEqual(profile.phone, '+91 98888 77777')
        self.assertEqual(profile.upi_id, 'pateltrade@upi')

    def test_03_distributor_metrics_properties(self):
        """Verify total_invoices and total_revenue properties on Distributor model."""
        dist = Distributor.objects.create(
            user=self.dist_user,
            name='Rahul Sharma',
            business_name='Sharma Tech & Retail Distribution',
            phone='+91 98123 45678',
            upi_id='sharmadist@upi'
        )

        # Initial zero metrics
        self.assertEqual(dist.total_invoices, 0)
        self.assertEqual(dist.total_revenue, Decimal('0.00'))

        # Create paid invoice
        inv1 = Invoice.objects.create(
            invoice_number='INV-TEST-001',
            distributor=self.dist_user,
            distributor_ref=dist,
            customer=self.customer,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
            subtotal=Decimal('1000.00'),
            tax_amount=Decimal('180.00'),
            grand_total=Decimal('1180.00'),
            payment_status='PAID',
            skip_qr_generation=True
        )

        # Create pending invoice
        inv2 = Invoice.objects.create(
            invoice_number='INV-TEST-002',
            distributor=self.dist_user,
            distributor_ref=dist,
            customer=self.customer,
            customer_name=self.customer.name,
            customer_phone=self.customer.phone,
            subtotal=Decimal('500.00'),
            tax_amount=Decimal('90.00'),
            grand_total=Decimal('590.00'),
            payment_status='PENDING',
            skip_qr_generation=True
        )

        self.assertEqual(dist.total_invoices, 2)
        # Revenue should aggregate PAID invoices only
        self.assertEqual(dist.total_revenue, Decimal('1180.00'))

    def test_04_add_distributor_through_django_admin(self):
        """Verify adding distributor data directly through Django Admin portal."""
        self.client.login(username='admin_test', password='Password@123')

        admin_add_url = '/django-admin/billing_app/distributor/add/'
        response = self.client.get(admin_add_url)
        self.assertEqual(response.status_code, 200)

        # Post new distributor data through Admin
        post_data = {
            'business_name': 'Omkar Enterprise & Logistics',
            'name': 'Omkar Singh',
            'phone': '+91 91234 56789',
            'email': 'omkar@enterprise.com',
            'address': 'Sector 15, Transport Hub',
            'city': 'Surat',
            'state': 'Gujarat',
            'pincode': '395001',
            'gstin': '24AABCO1234P1Z5',
            'upi_id': 'omkarlogistics@upi',
            'is_active': 'on',
            'invoices-TOTAL_FORMS': '0',
            'invoices-INITIAL_FORMS': '0',
            'invoices-MIN_NUM_FORMS': '0',
            'invoices-MAX_NUM_FORMS': '1000',
        }
        res_post = self.client.post(admin_add_url, data=post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

        # Check in DB
        dist = Distributor.objects.filter(business_name='Omkar Enterprise & Logistics').first()
        self.assertIsNotNone(dist)
        self.assertEqual(dist.name, 'Omkar Singh')
        self.assertEqual(dist.city, 'Surat')
        self.assertEqual(dist.gstin, '24AABCO1234P1Z5')

    def test_05_django_admin_distributor_changelist_and_search(self):
        """Verify Django Admin Distributor changelist view and search filter."""
        Distributor.objects.create(
            name='Karan Mehra',
            business_name='Mehra Super Distributors',
            phone='+91 97777 66666',
            city='Vadodara',
            gstin='24AABCM9999K1Z2',
            upi_id='mehra@upi'
        )
        self.client.login(username='admin_test', password='Password@123')

        changelist_url = '/django-admin/billing_app/distributor/'
        response = self.client.get(changelist_url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Mehra Super Distributors')

        # Test search query
        search_res = self.client.get(f"{changelist_url}?q=Vadodara")
        self.assertEqual(search_res.status_code, 200)
        self.assertContains(search_res, 'Mehra Super Distributors')

    def test_06_admin_portal_distributor_list_view_access_control(self):
        """Verify that /admin/distributors/ is restricted to authenticated Admin users only."""
        url = reverse('admin_distributor_list')

        # 1. Anonymous user redirected to login
        res_anon = self.client.get(url)
        self.assertIn(res_anon.status_code, (302, 403))

        # 2. Distributor user is blocked (redirected or forbidden)
        self.client.login(username='dist_rahul', password='Password@123')
        res_dist = self.client.get(url)
        self.assertIn(res_dist.status_code, (302, 403))
        self.client.logout()

        # 3. Admin user can access
        self.client.login(username='admin_test', password='Password@123')
        res_admin = self.client.get(url)
        self.assertEqual(res_admin.status_code, 200)
        self.assertTemplateUsed(res_admin, 'admin/distributor_list.html')
        self.assertContains(res_admin, 'Distributor Directory')
        self.assertContains(res_admin, 'Master Table')

    def test_07_admin_portal_distributor_search_and_filter(self):
        """Verify search by firm name and status filter on admin distributor list view."""
        d1 = Distributor.objects.create(
            name='Mahesh Shah',
            business_name='Shah Infotech Distributors',
            phone='9822233344',
            city='Rajkot',
            is_active=True
        )
        d2 = Distributor.objects.create(
            name='Dinesh Joshi',
            business_name='Joshi Wholesale Supplies',
            phone='9833344455',
            city='Bhavnagar',
            is_active=False
        )

        self.client.login(username='admin_test', password='Password@123')
        url = reverse('admin_distributor_list')

        # Search by keyword
        res_search = self.client.get(f"{url}?q=Infotech")
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, 'Shah Infotech Distributors')
        self.assertNotContains(res_search, 'Joshi Wholesale Supplies')

        # Filter by active status
        res_active = self.client.get(f"{url}?status=active")
        self.assertEqual(res_active.status_code, 200)
        self.assertContains(res_active, 'Shah Infotech Distributors')
        self.assertNotContains(res_active, 'Joshi Wholesale Supplies')

        # Filter by inactive status
        res_inactive = self.client.get(f"{url}?status=inactive")
        self.assertEqual(res_inactive.status_code, 200)
        self.assertContains(res_inactive, 'Joshi Wholesale Supplies')
        self.assertNotContains(res_inactive, 'Shah Infotech Distributors')

    def test_08_admin_portal_distributor_add_view(self):
        """Verify adding distributor through Admin portal form."""
        self.client.login(username='admin_test', password='Password@123')
        url = reverse('admin_distributor_add')

        # GET request renders form
        res_get = self.client.get(url)
        self.assertEqual(res_get.status_code, 200)
        self.assertTemplateUsed(res_get, 'admin/distributor_form.html')

        # POST creates record
        post_data = {
            'business_name': 'Prime Global Distribution',
            'name': 'Girish Kumar',
            'phone': '+91 99887 76655',
            'email': 'girish@primeglobal.in',
            'address': 'Ring Road Warehouse Complex',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'pincode': '380015',
            'gstin': '24AABCP1122D1Z9',
            'upi_id': 'primeglobal@upi',
            'is_active': True,
        }
        res_post = self.client.post(url, data=post_data, follow=True)
        self.assertEqual(res_post.status_code, 200)

        dist = Distributor.objects.filter(business_name='Prime Global Distribution').first()
        self.assertIsNotNone(dist)
        self.assertEqual(dist.name, 'Girish Kumar')
        self.assertEqual(dist.upi_id, 'primeglobal@upi')

    def test_09_distributor_form_validation(self):
        """Verify DistributorForm validation rules."""
        # Missing required business_name and name
        form_invalid = DistributorForm(data={
            'business_name': '',
            'name': '',
            'phone': '',
        })
        self.assertFalse(form_invalid.is_valid())
        self.assertIn('business_name', form_invalid.errors)
        self.assertIn('name', form_invalid.errors)
        self.assertIn('phone', form_invalid.errors)

        # Valid form data
        form_valid = DistributorForm(data={
            'business_name': 'Reliable Trade Links',
            'name': 'Sanjay Mehta',
            'phone': '9898989898',
            'city': 'Ahmedabad',
            'state': 'Gujarat',
            'upi_id': 'reliable@upi',
            'is_active': True
        })
        self.assertTrue(form_valid.is_valid())
        dist = form_valid.save()
        self.assertEqual(dist.business_name, 'Reliable Trade Links')

    def test_10_invoice_save_auto_associates_distributor_ref(self):
        """Verify that Invoice.save auto-links distributor_ref when distributor User is assigned."""
        dist = Distributor.objects.create(
            user=self.dist_user,
            name='Rahul Sharma',
            business_name='Sharma Tech & Retail Distribution',
            phone='+91 98123 45678',
            upi_id='sharmadist@upi'
        )

        inv = Invoice.objects.create(
            invoice_number='INV-AUTO-SYNC-01',
            distributor=self.dist_user,
            customer=self.customer,
            grand_total=Decimal('500.00'),
            skip_qr_generation=True
        )

        self.assertEqual(inv.distributor_ref, dist)
