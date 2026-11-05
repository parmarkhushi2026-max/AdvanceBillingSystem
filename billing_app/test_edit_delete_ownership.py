from decimal import Decimal
from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile, Distributor, Customer, Product


class EditDeleteOwnershipTestCase(TestCase):
    """
    Test suite verifying edit and delete functionality for both customers and products
    strictly enforcing user ownership checks:
    - Distributors can edit and delete only their own customers and products.
    - Non-owning distributors are blocked (access denied, database intact).
    - Admins possess universal privileges to edit, reassign, and delete any customer or product.
    - Unauthenticated users are redirected to login.
    """

    def setUp(self):
        self.client = Client()

        # 1. System Admin User
        self.admin = User.objects.create_superuser(
            username='admin_owner_tester',
            email='admin@ownership.corp',
            password='AdminPass@123'
        )
        self.admin_profile, _ = UserProfile.objects.get_or_create(user=self.admin)
        self.admin_profile.role = 'ADMIN'
        self.admin_profile.business_name = 'Ownership Master Corp'
        self.admin_profile.save()

        # 2. Distributor 1 (Alpha Wholesale)
        self.dist1_user = User.objects.create_user(
            username='alpha_distributor',
            email='alpha@wholesalecorp.in',
            password='AlphaPass@123'
        )
        self.dist1_profile, _ = UserProfile.objects.get_or_create(user=self.dist1_user)
        self.dist1_profile.role = 'DISTRIBUTOR'
        self.dist1_profile.business_name = 'Alpha Wholesale Ltd'
        self.dist1_profile.save()

        self.dist1_record = Distributor.objects.create(
            user=self.dist1_user,
            name='Alpha Manager',
            business_name='Alpha Wholesale Ltd',
            phone='9111122222',
            email='alpha@wholesalecorp.in',
            city='Ahmedabad',
            state='Gujarat',
            upi_id='alpha@upi',
            is_active=True
        )

        # 3. Distributor 2 (Beta Retail)
        self.dist2_user = User.objects.create_user(
            username='beta_distributor',
            email='beta@retailcorp.in',
            password='BetaPass@123'
        )
        self.dist2_profile, _ = UserProfile.objects.get_or_create(user=self.dist2_user)
        self.dist2_profile.role = 'DISTRIBUTOR'
        self.dist2_profile.business_name = 'Beta Retail Hub'
        self.dist2_profile.save()

        self.dist2_record = Distributor.objects.create(
            user=self.dist2_user,
            name='Beta Manager',
            business_name='Beta Retail Hub',
            phone='9222233333',
            email='beta@retailcorp.in',
            city='Vadodara',
            state='Gujarat',
            upi_id='beta@upi',
            is_active=True
        )

        # Create Baseline Customer for Alpha
        self.alpha_customer = Customer.objects.create(
            name='Alpha Client One',
            phone='9800011111',
            email='client1@alpha.com',
            city='Ahmedabad',
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

        # Create Baseline Product for Alpha
        self.alpha_product = Product.objects.create(
            name='Alpha Scanner X1',
            sku='ALP-SCN-001',
            category='Hardware',
            price=Decimal('1500.00'),
            stock=40,
            gst_rate=Decimal('18.00'),
            unit='Pcs',
            created_by=self.dist1_user,
            distributor_ref=self.dist1_record
        )

    # =========================================================================
    # 1. Customer Edit Ownership Tests
    # =========================================================================
    def test_distributor_can_edit_own_customer(self):
        """Owner distributor can successfully edit their customer details."""
        self.client.force_login(self.dist1_user)

        edit_url = reverse('edit_customer', args=[self.alpha_customer.id])
        post_data = {
            'name': 'Alpha Client One Updated',
            'phone': '9800011199',
            'email': 'client_updated@alpha.com',
            'city': 'Gandhinagar',
            'address': 'Sector 25, IT City',
            'gstin': '24AAACT1234F1Z9'
        }
        res = self.client.post(edit_url, post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        self.alpha_customer.refresh_from_db()
        self.assertEqual(self.alpha_customer.name, 'Alpha Client One Updated')
        self.assertEqual(self.alpha_customer.phone, '9800011199')
        self.assertEqual(self.alpha_customer.city, 'Gandhinagar')

    def test_distributor_cannot_edit_other_distributors_customer(self):
        """Distributor 2 cannot edit Distributor 1's customer (access denied)."""
        self.client.force_login(self.dist2_user)

        edit_url = reverse('edit_customer', args=[self.alpha_customer.id])
        
        # GET request should redirect with error
        get_res = self.client.get(edit_url, follow=True)
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('Access denied', get_res.content.decode('utf-8'))

        # POST request should also be rejected
        post_data = {
            'name': 'Hacked Customer Name',
            'phone': '9999900000',
            'city': 'Nowhere'
        }
        post_res = self.client.post(edit_url, post_data, follow=True)
        self.assertEqual(post_res.status_code, 200)
        self.assertIn('Access denied', post_res.content.decode('utf-8'))

        # Verify DB remained unchanged
        self.alpha_customer.refresh_from_db()
        self.assertEqual(self.alpha_customer.name, 'Alpha Client One')
        self.assertEqual(self.alpha_customer.phone, '9800011111')

    def test_admin_can_edit_any_customer_and_reassign(self):
        """Admin has universal permission to edit and reassign any customer."""
        self.client.force_login(self.admin)

        edit_url = reverse('edit_customer', args=[self.alpha_customer.id])
        post_data = {
            'name': 'Alpha Customer Reassigned to Beta',
            'phone': '9800011111',
            'email': 'client1@alpha.com',
            'distributor': self.dist2_record.id  # Reassign to Beta
        }
        res = self.client.post(edit_url, post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        self.alpha_customer.refresh_from_db()
        self.assertEqual(self.alpha_customer.name, 'Alpha Customer Reassigned to Beta')
        self.assertEqual(self.alpha_customer.distributor_ref, self.dist2_record)

    # =========================================================================
    # 2. Customer Delete Ownership Tests
    # =========================================================================
    def test_distributor_can_delete_own_customer(self):
        """Owner distributor can successfully delete their own customer."""
        self.client.force_login(self.dist1_user)

        delete_url = reverse('delete_customer', args=[self.alpha_customer.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)

        self.assertFalse(Customer.objects.filter(pk=self.alpha_customer.id).exists())

    def test_distributor_cannot_delete_other_distributors_customer(self):
        """Distributor 2 cannot delete Distributor 1's customer."""
        self.client.force_login(self.dist2_user)

        delete_url = reverse('delete_customer', args=[self.alpha_customer.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Access denied', res.content.decode('utf-8'))

        # Customer must still exist in DB
        self.assertTrue(Customer.objects.filter(pk=self.alpha_customer.id).exists())

    def test_admin_can_delete_any_customer(self):
        """Admin can delete any customer record across all distributors."""
        self.client.force_login(self.admin)

        delete_url = reverse('delete_customer', args=[self.alpha_customer.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)

        self.assertFalse(Customer.objects.filter(pk=self.alpha_customer.id).exists())

    # =========================================================================
    # 3. Product Edit Ownership Tests
    # =========================================================================
    def test_distributor_can_edit_own_product(self):
        """Owner distributor can successfully update their product details."""
        self.client.force_login(self.dist1_user)

        edit_url = reverse('edit_product', args=[self.alpha_product.id])
        post_data = {
            'name': 'Alpha Scanner X1 Pro Updated',
            'sku': 'ALP-SCN-001',
            'category': 'Hardware Electronics',
            'price': '1850.00',
            'stock': '65',
            'gst_rate': '18.00',
            'unit': 'Box',
            'description': 'Updated model with enhanced battery life'
        }
        res = self.client.post(edit_url, post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        self.alpha_product.refresh_from_db()
        self.assertEqual(self.alpha_product.name, 'Alpha Scanner X1 Pro Updated')
        self.assertEqual(self.alpha_product.price, Decimal('1850.00'))
        self.assertEqual(self.alpha_product.stock, 65)

    def test_distributor_cannot_edit_other_distributors_product(self):
        """Distributor 2 cannot edit Distributor 1's product."""
        self.client.force_login(self.dist2_user)

        edit_url = reverse('edit_product', args=[self.alpha_product.id])
        
        # GET access denied
        get_res = self.client.get(edit_url, follow=True)
        self.assertEqual(get_res.status_code, 200)
        self.assertIn('Access denied', get_res.content.decode('utf-8'))

        # POST access denied
        post_res = self.client.post(edit_url, {
            'name': 'Hacked Product Name',
            'price': '1.00',
            'stock': '0',
            'category': 'General',
            'gst_rate': '18.00',
            'unit': 'Pcs'
        }, follow=True)
        self.assertEqual(post_res.status_code, 200)
        self.assertIn('Access denied', post_res.content.decode('utf-8'))

        self.alpha_product.refresh_from_db()
        self.assertEqual(self.alpha_product.name, 'Alpha Scanner X1')
        self.assertEqual(self.alpha_product.price, Decimal('1500.00'))

    def test_admin_can_edit_any_product_and_reassign(self):
        """Admin has universal privileges to edit any product and reassign agency."""
        self.client.force_login(self.admin)

        edit_url = reverse('edit_product', args=[self.alpha_product.id])
        post_data = {
            'name': 'Alpha Scanner Reassigned to Beta Hub',
            'sku': 'ALP-SCN-001',
            'category': 'Hardware',
            'price': '1999.00',
            'stock': '50',
            'gst_rate': '18.00',
            'unit': 'Pcs',
            'distributor': self.dist2_record.id
        }
        res = self.client.post(edit_url, post_data, follow=True)
        self.assertEqual(res.status_code, 200)

        self.alpha_product.refresh_from_db()
        self.assertEqual(self.alpha_product.name, 'Alpha Scanner Reassigned to Beta Hub')
        self.assertEqual(self.alpha_product.distributor_ref, self.dist2_record)

    # =========================================================================
    # 4. Product Delete Ownership Tests
    # =========================================================================
    def test_distributor_can_delete_own_product(self):
        """Owner distributor can successfully delete their own product."""
        self.client.force_login(self.dist1_user)

        delete_url = reverse('delete_product', args=[self.alpha_product.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)

        self.assertFalse(Product.objects.filter(pk=self.alpha_product.id).exists())

    def test_distributor_cannot_delete_other_distributors_product(self):
        """Distributor 2 cannot delete Distributor 1's product."""
        self.client.force_login(self.dist2_user)

        delete_url = reverse('delete_product', args=[self.alpha_product.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)
        self.assertIn('Access denied', res.content.decode('utf-8'))

        # Product must remain in DB
        self.assertTrue(Product.objects.filter(pk=self.alpha_product.id).exists())

    def test_admin_can_delete_any_product(self):
        """Admin can delete any product from catalog."""
        self.client.force_login(self.admin)

        delete_url = reverse('delete_product', args=[self.alpha_product.id])
        res = self.client.post(delete_url, follow=True)
        self.assertEqual(res.status_code, 200)

        self.assertFalse(Product.objects.filter(pk=self.alpha_product.id).exists())

    # =========================================================================
    # 5. Unauthenticated User Route Protection
    # =========================================================================
    def test_unauthenticated_user_cannot_edit_or_delete(self):
        """Unauthenticated requests to edit or delete are redirected to login."""
        endpoints = [
            reverse('edit_customer', args=[self.alpha_customer.id]),
            reverse('delete_customer', args=[self.alpha_customer.id]),
            reverse('edit_product', args=[self.alpha_product.id]),
            reverse('delete_product', args=[self.alpha_product.id]),
        ]
        for url in endpoints:
            res = self.client.get(url)
            self.assertEqual(res.status_code, 302)
            self.assertTrue(res.url.startswith('/') or 'login' in res.url)

