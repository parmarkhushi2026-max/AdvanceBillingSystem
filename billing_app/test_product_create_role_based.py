from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile, Distributor, Product
from billing_app.forms import ProductForm, ProductModelForm


class RoleBasedProductCreateTestCase(TestCase):
    """
    Test suite verifying role-based product creation forms and views:
    - Admin can add products for all distributors or central inventory
    - Distributors can add products strictly for their own catalog
    - Input validation, field filtering, multi-tenant isolation, and route protection
    """

    def setUp(self):
        self.client = Client()

        # 1. System Admin User
        self.admin_pass = 'AdminSecure@123'
        self.admin = User.objects.create_superuser(
            username='prod_admin',
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
            username='sharma_prod_distributor',
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
            username='patel_prod_distributor',
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
    def test_product_form_fields_for_admin_vs_distributor(self):
        """Admin has 'distributor' selection field; Distributor does NOT."""
        admin_form = ProductForm(user=self.admin, is_admin=True)
        self.assertIn('distributor', admin_form.fields)
        self.assertIn('name', admin_form.fields)
        self.assertIn('price', admin_form.fields)
        self.assertIn('stock', admin_form.fields)

        dist_form = ProductForm(user=self.dist1_user, is_admin=False)
        self.assertNotIn('distributor', dist_form.fields)
        self.assertIn('name', dist_form.fields)
        self.assertIn('price', dist_form.fields)
        self.assertIn('stock', dist_form.fields)

    def test_product_model_form_fields_for_admin_vs_distributor(self):
        """ProductModelForm also omits 'distributor' for distributors."""
        admin_model_form = ProductModelForm(user=self.admin, is_admin=True)
        self.assertIn('distributor', admin_model_form.fields)

        dist_model_form = ProductModelForm(user=self.dist1_user, is_admin=False)
        self.assertNotIn('distributor', dist_model_form.fields)

    # -------------------------------------------------------------
    # 2. Admin Adding Products (Can add for all or any distributor)
    # -------------------------------------------------------------
    def test_admin_can_add_product_for_specific_distributor(self):
        """Admin can choose a distributor and assign the new product to that distributor."""
        self.client.force_login(self.admin)

        # GET request renders distributor select
        get_res = self.client.get(reverse('add_product'))
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('distributor-select', get_res.content.decode('utf-8'))
        self.assertIn('Sharma Agency Hub', get_res.content.decode('utf-8'))

        # POST assigning to Distributor 1
        post_data = {
            'name': 'Thermal Barcode Printer Pro',
            'sku': 'PRT-TH-9001',
            'category': 'Hardware',
            'price': '4500.00',
            'gst_rate': '18.00',
            'hsn_code': '844332',
            'stock': '25',
            'unit': 'Pcs',
            'description': 'High-speed 80mm receipt printer',
            'distributor': self.dist1_record.id
        }
        res = self.client.post(reverse('add_product'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        # Verify product created in DB
        prod = Product.objects.filter(sku='PRT-TH-9001').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.name, 'Thermal Barcode Printer Pro')
        self.assertEqual(prod.distributor_ref, self.dist1_record)
        self.assertEqual(prod.created_by, self.dist1_user)
        self.assertEqual(prod.price, Decimal('4500.00'))

    def test_admin_can_add_product_globally_for_central_admin(self):
        """Admin can leave distributor blank to create a central/global product."""
        self.client.force_login(self.admin)

        post_data = {
            'name': 'Universal Billing Software License',
            'sku': 'SFT-UB-CENTRAL',
            'category': 'Software',
            'price': '12000.00',
            'gst_rate': '18.00',
            'stock': '999',
            'unit': 'License',
            'distributor': ''  # No distributor selected
        }
        res = self.client.post(reverse('add_product'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        prod = Product.objects.filter(sku='SFT-UB-CENTRAL').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.created_by, self.admin)
        self.assertIsNone(prod.distributor_ref)

    # -------------------------------------------------------------
    # 3. Distributor Adding Products (Adds ONLY their own)
    # -------------------------------------------------------------
    def test_distributor_adds_product_strictly_for_their_own_account(self):
        """Distributor adds product and it is automatically bound to their account."""
        self.client.force_login(self.dist1_user)

        # GET request does not display distributor select
        get_res = self.client.get(reverse('add_product'))
        self.assertEqual(get_res.status_code, 200)
        self.assertNotIn('distributor-select', get_res.content.decode('utf-8'))
        self.assertIn('Sharma Agency Hub', get_res.content.decode('utf-8'))

        # POST product data (cannot specify distributor)
        post_data = {
            'name': 'Wireless Laser Scanner',
            'sku': 'WLS-SC-8811',
            'category': 'Hardware',
            'price': '2200.00',
            'gst_rate': '18.00',
            'stock': '50',
            'unit': 'Pcs',
            'description': '2.4GHz handheld wireless scanner'
        }
        res = self.client.post(reverse('add_product'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        prod = Product.objects.filter(sku='WLS-SC-8811').first()
        self.assertIsNotNone(prod)
        self.assertEqual(prod.name, 'Wireless Laser Scanner')
        self.assertEqual(prod.created_by, self.dist1_user)
        self.assertEqual(prod.distributor_ref, self.dist1_record)

    def test_distributor_cannot_tamper_distributor_assignment(self):
        """Even if distributor submits a 'distributor' POST param of another agency, it is ignored."""
        self.client.force_login(self.dist1_user)

        post_data = {
            'name': 'Tampered Product Attempt',
            'sku': 'TMP-SPOOF-99',
            'category': 'General',
            'price': '999.00',
            'gst_rate': '18.00',
            'stock': '10',
            'unit': 'Pcs',
            'distributor': self.dist2_record.id  # Attempting to assign to Distributor 2
        }
        res = self.client.post(reverse('add_product'), post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        prod = Product.objects.filter(sku='TMP-SPOOF-99').first()
        self.assertIsNotNone(prod)
        # MUST still belong to Distributor 1!
        self.assertEqual(prod.distributor_ref, self.dist1_record)
        self.assertEqual(prod.created_by, self.dist1_user)

    # -------------------------------------------------------------
    # 4. Multi-Tenant Isolation between Distributors
    # -------------------------------------------------------------
    def test_multi_tenant_isolation_between_distributors(self):
        """Distributor 1 cannot see Distributor 2's products in inventory list."""
        prod_dist1 = Product.objects.create(
            name='Distributor 1 Exclusive Widget',
            sku='EXCL-D1-01',
            price=Decimal('150.00'),
            stock=100,
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )
        prod_dist2 = Product.objects.create(
            name='Distributor 2 Private Gizmo',
            sku='EXCL-D2-02',
            price=Decimal('250.00'),
            stock=50,
            created_by=self.dist2_user,
            distributor_ref=self.dist2_record
        )

        # Login as Distributor 1
        self.client.force_login(self.dist1_user)
        res1 = self.client.get(reverse('product_list'))
        self.assertEqual(res1.status_code, 200)
        p_names = [p.name for p in res1.context['products']]
        self.assertIn('Distributor 1 Exclusive Widget', p_names)
        self.assertNotIn('Distributor 2 Private Gizmo', p_names)

        # Login as Distributor 2
        self.client.force_login(self.dist2_user)
        res2 = self.client.get(reverse('product_list'))
        self.assertEqual(res2.status_code, 200)
        p_names2 = [p.name for p in res2.context['products']]
        self.assertIn('Distributor 2 Private Gizmo', p_names2)
        self.assertNotIn('Distributor 1 Exclusive Widget', p_names2)

        # Login as Admin (sees both)
        self.client.force_login(self.admin)
        res_admin = self.client.get(reverse('product_list'))
        p_names_admin = [p.name for p in res_admin.context['products']]
        self.assertIn('Distributor 1 Exclusive Widget', p_names_admin)
        self.assertIn('Distributor 2 Private Gizmo', p_names_admin)

    # -------------------------------------------------------------
    # 5. Role-Protected Product Edit & Tamper Prevention
    # -------------------------------------------------------------
    def test_distributor_cannot_edit_other_distributors_product(self):
        """Distributor 2 is blocked from editing Distributor 1's product."""
        prod = Product.objects.create(
            name='Rahul Protected Product',
            sku='PROT-D1-01',
            price=Decimal('500.00'),
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

        # Distributor 2 tries to GET edit page
        self.client.force_login(self.dist2_user)
        get_res = self.client.get(reverse('edit_product', args=[prod.id]))
        self.assertEqual(get_res.status_code, 302)  # Access Denied redirect

        # Distributor 2 tries to POST edit
        post_res = self.client.post(reverse('edit_product', args=[prod.id]), {
            'name': 'Hacked Product Name',
            'price': '10.00',
            'stock': '1',
            'unit': 'Pcs',
            'category': 'General',
            'gst_rate': '18.00'
        })
        self.assertEqual(post_res.status_code, 302)

        prod.refresh_from_db()
        self.assertEqual(prod.name, 'Rahul Protected Product')

    def test_admin_can_edit_any_distributors_product(self):
        """Admin has universal editing privileges and can reassign products."""
        prod = Product.objects.create(
            name='Original Admin Editable Item',
            sku='EDIT-AD-01',
            price=Decimal('100.00'),
            stock=10,
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

        self.client.force_login(self.admin)
        post_res = self.client.post(reverse('edit_product', args=[prod.id]), {
            'name': 'Updated by Admin Item',
            'sku': 'EDIT-AD-01',
            'price': '180.00',
            'stock': '20',
            'unit': 'Box',
            'category': 'Electronics',
            'gst_rate': '12.00',
            'distributor': self.dist2_record.id  # Reassign to Distributor 2
        }, follow=True)
        self.assertEqual(post_res.status_code, 200)

        prod.refresh_from_db()
        self.assertEqual(prod.name, 'Updated by Admin Item')
        self.assertEqual(prod.price, Decimal('180.00'))
        self.assertEqual(prod.distributor_ref, self.dist2_record)

    # -------------------------------------------------------------
    # 6. Unauthenticated Access & Form Validation
    # -------------------------------------------------------------
    def test_unauthenticated_user_cannot_access_add_product(self):
        """Anonymous user is redirected to login."""
        res = self.client.get(reverse('add_product'))
        self.assertEqual(res.status_code, 302)
        self.assertTrue(res.url.startswith('/') or 'login' in res.url)

    def test_product_form_validation_errors(self):
        """Form rejects negative price, negative stock, and invalid GST rate."""
        # 1. Negative price
        form1 = ProductForm(data={
            'name': 'Test Item',
            'price': '-50.00',
            'stock': '10',
            'gst_rate': '18.00',
            'category': 'General',
            'unit': 'Pcs'
        }, user=self.admin, is_admin=True)
        self.assertFalse(form1.is_valid())
        self.assertIn('price', form1.errors)

        # 2. Negative stock
        form2 = ProductForm(data={
            'name': 'Test Item',
            'price': '50.00',
            'stock': '-5',
            'gst_rate': '18.00',
            'category': 'General',
            'unit': 'Pcs'
        }, user=self.admin, is_admin=True)
        self.assertFalse(form2.is_valid())
        self.assertIn('stock', form2.errors)

        # 3. Invalid GST rate (>100)
        form3 = ProductForm(data={
            'name': 'Test Item',
            'price': '50.00',
            'stock': '5',
            'gst_rate': '120.00',
            'category': 'General',
            'unit': 'Pcs'
        }, user=self.admin, is_admin=True)
        self.assertFalse(form3.is_valid())
        self.assertIn('gst_rate', form3.errors)

