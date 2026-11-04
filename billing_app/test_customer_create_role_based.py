from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile, Distributor, Customer
from billing_app.forms import CustomerForm, CustomerModelForm


class RoleBasedCustomerCreateTestCase(TestCase):
    """
    Test suite verifying role-based customer creation forms and views:
    - Admin can add customers for all distributors or central admin
    - Distributors can add customers strictly for their own account
    - Input validation, field filtering, multi-tenant isolation, and route protection
    """

    def setUp(self):
        self.client = Client()

        # 1. System Admin User
        self.admin_pass = 'AdminSecure@123'
        self.admin = User.objects.create_superuser(
            username='role_admin',
            email='admin@billingcorp.com',
            password=self.admin_pass
        )
        self.admin.first_name = 'Vikram'
        self.admin.last_name = 'Mehta'
        self.admin.save()
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.business_name = 'Billing Corp Central'
        self.admin_profile.save()

        # 2. Distributor 1 (Rahul - Sharma Agency)
        self.dist1_pass = 'Dist1Pass@123'
        self.dist1_user = User.objects.create_user(
            username='sharma_distributor',
            email='rahul@sharmaagency.in',
            password=self.dist1_pass
        )
        self.dist1_profile, _ = UserProfile.objects.get_or_create(user=self.dist1_user)
        self.dist1_profile.role = 'DISTRIBUTOR'
        self.dist1_profile.business_name = 'Sharma Agency Hub'
        self.dist1_profile.save()

        self.dist1_record = Distributor.objects.create(
            user=self.dist1_user,
            name='Rahul Sharma',
            business_name='Sharma Agency Hub',
            phone='9811122233',
            email='rahul@sharmaagency.in',
            city='Ahmedabad',
            state='Gujarat',
            upi_id='sharma@upi',
            gstin='24AAECS1111F1Z1',
            is_active=True
        )

        # 3. Distributor 2 (Priya - Patel Traders)
        self.dist2_pass = 'Dist2Pass@123'
        self.dist2_user = User.objects.create_user(
            username='patel_distributor',
            email='priya@pateltraders.in',
            password=self.dist2_pass
        )
        self.dist2_profile, _ = UserProfile.objects.get_or_create(user=self.dist2_user)
        self.dist2_profile.role = 'DISTRIBUTOR'
        self.dist2_profile.business_name = 'Patel Traders Ltd'
        self.dist2_profile.save()

        self.dist2_record = Distributor.objects.create(
            user=self.dist2_user,
            name='Priya Patel',
            business_name='Patel Traders Ltd',
            phone='9822233344',
            email='priya@pateltraders.in',
            city='Surat',
            state='Gujarat',
            upi_id='patel@upi',
            gstin='24AABCP2222K1Z2',
            is_active=True
        )

    # -------------------------------------------------------------
    # 1. Form Level Role Differentiation Tests
    # -------------------------------------------------------------
    def test_customer_form_fields_for_admin_vs_distributor(self):
        """Admin has 'distributor' selection field; Distributor does NOT."""
        admin_form = CustomerForm(user=self.admin, is_admin=True)
        self.assertIn('distributor', admin_form.fields)
        self.assertIn('name', admin_form.fields)
        self.assertIn('phone', admin_form.fields)

        dist_form = CustomerForm(user=self.dist1_user, is_admin=False)
        self.assertNotIn('distributor', dist_form.fields)
        self.assertIn('name', dist_form.fields)
        self.assertIn('phone', dist_form.fields)

    def test_customer_model_form_fields_for_admin_vs_distributor(self):
        """CustomerModelForm also omits 'distributor' for distributors."""
        admin_model_form = CustomerModelForm(user=self.admin, is_admin=True)
        self.assertIn('distributor', admin_model_form.fields)

        dist_model_form = CustomerModelForm(user=self.dist1_user, is_admin=False)
        self.assertNotIn('distributor', dist_model_form.fields)

    # -------------------------------------------------------------
    # 2. Admin Adding Customers (Can add for all or any distributor)
    # -------------------------------------------------------------
    def test_admin_can_add_customer_for_specific_distributor(self):
        """Admin can choose a distributor and assign the new customer to that distributor."""
        self.client.force_login(self.admin)

        # GET request renders distributor select
        get_res = self.client.get(reverse('add_customer'))
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('distributor-select', get_res.content.decode('utf-8'))
        self.assertIn('Sharma Agency Hub', get_res.content.decode('utf-8'))

        # POST assigning to Distributor 1
        post_data = {
            'name': 'Gajanan Electricals',
            'phone': '9898011223',
            'email': 'gajanan@elec.com',
            'city': 'Ahmedabad',
            'address': 'Plot 10, GIDC',
            'gstin': '24AABCG1234F1Z1',
            'distributor': self.dist1_record.id
        }
        res = self.client.post(reverse('add_customer'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # Verify customer created in DB
        cust = Customer.objects.filter(phone='9898011223').first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, 'Gajanan Electricals')
        self.assertEqual(cust.distributor_ref, self.dist1_record)
        self.assertEqual(cust.created_by, self.dist1_user)

    def test_admin_can_add_customer_globally_for_central_admin(self):
        """Admin can leave distributor blank to create a central/global customer."""
        self.client.force_login(self.admin)

        post_data = {
            'name': 'Central Apex Wholesaler',
            'phone': '9898099887',
            'email': 'apex@central.com',
            'city': 'Mumbai',
            'distributor': ''  # No distributor selected
        }
        res = self.client.post(reverse('add_customer'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        cust = Customer.objects.filter(phone='9898099887').first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.created_by, self.admin)
        self.assertIsNone(cust.distributor_ref)

    # -------------------------------------------------------------
    # 3. Distributor Adding Customers (Adds ONLY their own)
    # -------------------------------------------------------------
    def test_distributor_adds_customer_strictly_for_their_own_account(self):
        """Distributor adds customer and it is automatically bound to their account."""
        self.client.force_login(self.dist1_user)

        # GET request does not display distributor select
        get_res = self.client.get(reverse('add_customer'))
        self.assertEqual(get_res.status_code, 200)
        self.assertNotIn('distributor-select', get_res.content.decode('utf-8'))
        self.assertIn('Sharma Agency Hub', get_res.content.decode('utf-8'))

        # POST customer data (cannot specify distributor)
        post_data = {
            'name': 'Bhavik Stationery Mart',
            'phone': '9812300001',
            'email': 'bhavik@stationery.com',
            'city': 'Ahmedabad',
            'gstin': '24AABCB1001B1Z2'
        }
        res = self.client.post(reverse('add_customer'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        cust = Customer.objects.filter(phone='9812300001').first()
        self.assertIsNotNone(cust)
        self.assertEqual(cust.name, 'Bhavik Stationery Mart')
        self.assertEqual(cust.created_by, self.dist1_user)
        self.assertEqual(cust.distributor_ref, self.dist1_record)

    def test_distributor_cannot_tamper_distributor_assignment(self):
        """Even if distributor submits a 'distributor' POST param of another agency, it is ignored."""
        self.client.force_login(self.dist1_user)

        post_data = {
            'name': 'Tamper Test Retailer',
            'phone': '9812399999',
            'distributor': self.dist2_record.id  # Attempting to assign to Distributor 2
        }
        res = self.client.post(reverse('add_customer'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        cust = Customer.objects.filter(phone='9812399999').first()
        self.assertIsNotNone(cust)
        # Must be bound to dist1, not dist2!
        self.assertEqual(cust.created_by, self.dist1_user)
        self.assertEqual(cust.distributor_ref, self.dist1_record)
        self.assertNotEqual(cust.distributor_ref, self.dist2_record)

    # -------------------------------------------------------------
    # 4. Multi-Tenant Customer Isolation Verification
    # -------------------------------------------------------------
    def test_multi_tenant_isolation_between_distributors(self):
        """Customers added by Distributor 1 are hidden from Distributor 2, but visible to Admin."""
        # 1. Distributor 1 creates Customer A
        self.client.force_login(self.dist1_user)
        self.client.post(reverse('add_customer'), {
            'name': 'Customer of Sharma',
            'phone': '9800011111'
        }, follow=True)

        # 2. Distributor 2 creates Customer B
        self.client.force_login(self.dist2_user)
        self.client.post(reverse('add_customer'), {
            'name': 'Customer of Patel',
            'phone': '9800022222'
        }, follow=True)

        # Check Distributor 1 customer list: only sees Customer A
        self.client.force_login(self.dist1_user)
        res1 = self.client.get(reverse('customer_list'))
        self.assertEqual(res1.status_code, 200)
        names1 = [c.name for c in res1.context['customers']]
        self.assertIn('Customer of Sharma', names1)
        self.assertNotIn('Customer of Patel', names1)

        # Check Distributor 2 customer list: only sees Customer B
        self.client.force_login(self.dist2_user)
        res2 = self.client.get(reverse('customer_list'))
        self.assertEqual(res2.status_code, 200)
        names2 = [c.name for c in res2.context['customers']]
        self.assertIn('Customer of Patel', names2)
        self.assertNotIn('Customer of Sharma', names2)

        # Check Admin customer list: sees BOTH customers
        self.client.force_login(self.admin)
        res_admin = self.client.get(reverse('customer_list'))
        self.assertEqual(res_admin.status_code, 200)
        names_admin = [c.name for c in res_admin.context['customers']]
        self.assertIn('Customer of Sharma', names_admin)
        self.assertIn('Customer of Patel', names_admin)

    # -------------------------------------------------------------
    # 5. Form Validation & Route Protection
    # -------------------------------------------------------------
    def test_validation_errors_for_invalid_customer_data(self):
        """Required fields, short names, and invalid phone numbers produce validation errors."""
        self.client.force_login(self.admin)

        # Invalid phone and 1-letter name
        res = self.client.post(reverse('add_customer'), {
            'name': 'A',
            'phone': '123'
        })
        self.assertEqual(res.status_code, 200)
        self.assertFalse(Customer.objects.filter(phone='123').exists())

    def test_unauthenticated_user_cannot_access_add_customer(self):
        """Unauthenticated requests are redirected away from protected form."""
        self.client.logout()
        res = self.client.get(reverse('add_customer'))
        self.assertEqual(res.status_code, 302)
        # Login redirect target
        self.assertTrue(res.url.startswith('/') or 'login' in res.url)

    def test_url_alias_customer_create_works_identically(self):
        """URL alias 'customer_create' routes correctly to add customer view."""
        self.client.force_login(self.admin)
        res = self.client.get(reverse('customer_create'))
        self.assertEqual(res.status_code, 200)
        self.assertTemplateUsed(res, 'billing/add_customer.html')
