from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from billing_app.models import Product, UserProfile, Customer

class ProductUpdateTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='testuser', password='password123')
        self.client.login(username='testuser', password='password123')
        
        self.product = Product.objects.create(
            name='Test Scanner',
            sku='SCAN-001',
            category='Hardware',
            price=1500.00,
            stock=50,
            gst_rate=18.00,
            hsn_code='8471',
            unit='Pcs',
            description='Original Scanner Description',
            created_by=self.user
        )

    def test_product_list_view(self):
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Test Scanner')
        self.assertContains(response, 'SCAN-001')

    def test_edit_product_prefilled_form_get(self):
        response = self.client.get(reverse('edit_product', args=[self.product.id]))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context['is_edit'])
        self.assertEqual(response.context['product'], self.product)
        # Verify form is pre-filled with existing values
        form = response.context['form']
        self.assertEqual(form.initial.get('name') or form.instance.name, 'Test Scanner')
        self.assertEqual(float(form.initial.get('price') or form.instance.price), 1500.00)

    def test_edit_product_post_success(self):
        updated_data = {
            'name': 'Updated Scanner Pro',
            'sku': 'SCAN-001',
            'category': 'Electronics',
            'price': 1800.50,
            'stock': 75,
            'gst_rate': 18.00,
            'hsn_code': '8471',
            'unit': 'Box',
            'description': 'Updated Description Text'
        }
        response = self.client.post(reverse('edit_product', args=[self.product.id]), updated_data)
        self.assertRedirects(response, reverse('product_list'))
        
        # Verify object updated in DB
        self.product.refresh_from_db()
        self.assertEqual(self.product.name, 'Updated Scanner Pro')
        self.assertEqual(float(self.product.price), 1800.50)
        self.assertEqual(self.product.stock, 75)
        self.assertEqual(self.product.category, 'Electronics')
        self.assertEqual(self.product.unit, 'Box')

    def test_edit_product_duplicate_sku_validation(self):
        # Create second product
        Product.objects.create(
            name='Other Device',
            sku='OTHER-99',
            price=100.00,
            stock=10,
            created_by=self.user
        )
        # Try setting self.product's SKU to OTHER-99
        invalid_data = {
            'name': 'Test Scanner',
            'sku': 'OTHER-99',
            'category': 'Hardware',
            'price': 1500.00,
            'stock': 50,
            'gst_rate': 18.00,
            'unit': 'Pcs'
        }
        response = self.client.post(reverse('edit_product', args=[self.product.id]), invalid_data)
        self.assertEqual(response.status_code, 200) # Re-renders form with error
        self.product.refresh_from_db()
        self.assertEqual(self.product.sku, 'SCAN-001') # Unchanged

    def test_delete_product_with_success_message(self):
        product_id = self.product.id
        product_name = self.product.name
        response = self.client.post(reverse('delete_product', args=[product_id]), follow=True)
        self.assertRedirects(response, reverse('product_list'))
        self.assertFalse(Product.objects.filter(id=product_id).exists())
        # Check success message in response context/content
        self.assertContains(response, f"Product &#x27;{product_name}&#x27; deleted successfully")


from billing_app.models import Customer, Invoice, InvoiceItem
import json

class InvoiceRelationsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='distributor1', password='password123')
        self.client.login(username='distributor1', password='password123')

        self.customer = Customer.objects.create(
            name='Acme Retailers',
            phone='9876543210',
            email='acme@example.com',
            city='Mumbai',
            created_by=self.user
        )

        self.product = Product.objects.create(
            name='Thermal Printer 80mm',
            sku='PRN-80',
            price=3200.00,
            gst_rate=18.00,
            stock=20,
            created_by=self.user
        )

    def test_create_invoice_establishes_fk_relations(self):
        items_payload = json.dumps([{
            'name': 'Thermal Printer 80mm',
            'qty': 2,
            'price': '3200.00',
            'tax': '18.00'
        }])

        post_data = {
            'customer_name': 'Acme Retailers',
            'customer_phone': '9876543210',
            'payment_method': 'UPI QR Code',
            'notes': 'Test invoice generation',
            'items_data': items_payload
        }

        response = self.client.post(reverse('create_invoice'), post_data)
        self.assertEqual(response.status_code, 302)

        invoice = Invoice.objects.first()
        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.customer_ref, self.customer)
        self.assertEqual(invoice.distributor, self.user)

        items = invoice.items.all()
        self.assertEqual(items.count(), 1)
        item = items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.product_name, 'Thermal Printer 80mm')
        self.assertEqual(item.quantity, 2)

        # Verify stock was decremented from 20 to 18
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 18)

    def test_create_invoice_auto_creates_customer(self):
        items_payload = json.dumps([{
            'name': 'Thermal Printer 80mm',
            'qty': 1,
            'price': '3200.00',
            'tax': '18.00'
        }])
        post_data = {
            'customer_name': 'New Dynamic Client',
            'customer_phone': '9123456780',
            'payment_method': 'UPI QR Code',
            'items_data': items_payload
        }
        response = self.client.post(reverse('create_invoice'), post_data)
        self.assertEqual(response.status_code, 302)

        # Verify Customer object was automatically created in DB
        new_customer = Customer.objects.filter(phone='9123456780').first()
        self.assertIsNotNone(new_customer)
        self.assertEqual(new_customer.name, 'New Dynamic Client')
        self.assertEqual(new_customer.created_by, self.user)


class CustomerPermissionTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user1 = User.objects.create_user(username='dist1', password='password123')
        self.user2 = User.objects.create_user(username='dist2', password='password123')
        self.admin = User.objects.create_superuser(username='adminuser', password='password123')
        
        self.customer1 = Customer.objects.create(
            name='User1 Customer',
            phone='9800000001',
            created_by=self.user1
        )

    def test_distributor_cannot_delete_other_customer(self):
        self.client.login(username='dist2', password='password123')
        response = self.client.post(reverse('delete_customer', args=[self.customer1.id]), follow=True)
        self.assertContains(response, 'Access denied')
        self.assertTrue(Customer.objects.filter(id=self.customer1.id).exists())

    def test_distributor_can_delete_own_customer(self):
        self.client.login(username='dist1', password='password123')
        response = self.client.post(reverse('delete_customer', args=[self.customer1.id]), follow=True)
        self.assertContains(response, 'deleted successfully')
        self.assertFalse(Customer.objects.filter(id=self.customer1.id).exists())

    def test_admin_can_delete_any_customer(self):
        self.client.login(username='adminuser', password='password123')
        response = self.client.post(reverse('delete_customer', args=[self.customer1.id]), follow=True)
        self.assertContains(response, 'deleted successfully')
        self.assertFalse(Customer.objects.filter(id=self.customer1.id).exists())


class DistributorRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_distributor_registration_success(self):
        data = {
            'full_name': 'Rajesh Kumar',
            'username': 'newdistributor',
            'email': 'dist@example.com',
            'password': 'SecurePassword123!',
            'confirm_password': 'SecurePassword123!',
            'business_name': 'Super Wholesale Corp',
            'phone': '9876543210',
            'upi_id': 'supercorp@upi'
        }
        response = self.client.post(reverse('distributor_register'), data, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Registration successful')

        # Verify user & profile created properly
        user = User.objects.filter(username='newdistributor').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'dist@example.com')
        self.assertTrue(user.check_password('SecurePassword123!'))

        self.assertEqual(user.profile.role, 'DISTRIBUTOR')
        self.assertEqual(user.profile.business_name, 'Super Wholesale Corp')
        self.assertEqual(user.profile.phone, '9876543210')
        self.assertEqual(user.profile.upi_id, 'supercorp@upi')


from billing_app.forms import InvoiceCreationForm, InvoiceItemForm
from decimal import Decimal

class InvoiceCreationFormTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(username='dist_tester', password='password123')
        self.client.login(username='dist_tester', password='password123')

        self.customer = Customer.objects.create(
            name='Rajesh Traders',
            phone='9811223344',
            city='Delhi',
            created_by=self.user
        )

        self.product = Product.objects.create(
            name='Barcode Terminal',
            sku='BAR-001',
            price=Decimal('2000.00'),
            gst_rate=Decimal('18.00'),
            stock=25,
            unit='Pcs',
            created_by=self.user
        )

    def test_invoice_creation_form_customer_dropdown_queryset(self):
        form = InvoiceCreationForm(user=self.user)
        # Dropdown queryset should include our customer
        customer_qs = form.fields['customer'].queryset
        self.assertIn(self.customer, customer_qs)

    def test_invoice_creation_form_save_with_customer_and_product(self):
        items_payload = json.dumps([
            {
                'product_id': self.product.id,
                'name': self.product.name,
                'price': '2000.00',
                'qty': 2,
                'tax': '18.00'
            }
        ])

        data = {
            'customer': self.customer.id,
            'customer_name': self.customer.name,
            'customer_phone': self.customer.phone,
            'payment_method': 'UPI QR Code',
            'discount': '100.00',
            'notes': 'Test invoice note',
            'items_data': items_payload
        }

        form = InvoiceCreationForm(data=data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        invoice = form.save(distributor=self.user)

        self.assertIsNotNone(invoice)
        self.assertEqual(invoice.customer, self.customer)
        self.assertEqual(invoice.customer_name, 'Rajesh Traders')
        self.assertEqual(invoice.customer_phone, '9811223344')
        self.assertEqual(invoice.subtotal, Decimal('4000.00')) # 2000 * 2
        self.assertEqual(invoice.tax_amount, Decimal('720.00')) # 18% of 4000
        # Grand total = (4000 + 720) - 100 discount = 4620.00
        self.assertEqual(invoice.grand_total, Decimal('4620.00'))

        # Check stock deduction: 25 - 2 = 23
        self.product.refresh_from_db()
        self.assertEqual(self.product.stock, 23)

        # Check invoice item creation
        self.assertEqual(invoice.items.count(), 1)
        item = invoice.items.first()
        self.assertEqual(item.product, self.product)
        self.assertEqual(item.quantity, 2)
        self.assertEqual(item.unit_price, Decimal('2000.00'))

    def test_invoice_create_view_get_and_post(self):
        # Test GET loads the dynamic dropdowns and products catalog
        response = self.client.get(reverse('create_invoice'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Rajesh Traders')
        self.assertContains(response, 'Barcode Terminal')
        self.assertIn('products_catalog_json', response.context)

        # Test POST creates invoice
        items_payload = json.dumps([
            {
                'product_id': self.product.id,
                'name': self.product.name,
                'price': '2000.00',
                'qty': 1,
                'tax': '18.00'
            }
        ])

        post_data = {
            'customer': self.customer.id,
            'customer_name': self.customer.name,
            'customer_phone': self.customer.phone,
            'payment_method': 'UPI QR Code',
            'discount': '0.00',
            'notes': 'Online order',
            'items_data': items_payload
        }

        post_resp = self.client.post(reverse('create_invoice'), post_data)
        self.assertEqual(post_resp.status_code, 302)
        new_inv = Invoice.objects.filter(customer=self.customer).first()
        self.assertIsNotNone(new_inv)
        self.assertRedirects(post_resp, reverse('invoice_detail', args=[new_inv.id]))

    def test_invoice_creation_with_item_discount_and_gst(self):
        # Base: 2000 * 2 = 4000; Item Discount: 200; Taxable: 3800; Tax (18%): 684; Total: 4484
        items_payload = json.dumps([
            {
                'product_id': self.product.id,
                'name': self.product.name,
                'price': '2000.00',
                'qty': 2,
                'discount': '200.00',
                'tax': '18.00'
            }
        ])

        post_data = {
            'customer': self.customer.id,
            'customer_name': self.customer.name,
            'customer_phone': self.customer.phone,
            'payment_method': 'UPI QR Code',
            'discount': '50.00', # Extra overall invoice discount
            'notes': 'Item discount test',
            'items_data': items_payload
        }

        form = InvoiceCreationForm(data=post_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        invoice = form.save(distributor=self.user)

        self.assertEqual(invoice.subtotal, Decimal('4000.00'))
        # Total discount: 200 (item) + 50 (invoice extra) = 250
        self.assertEqual(invoice.discount, Decimal('250.00'))
        self.assertEqual(invoice.tax_amount, Decimal('684.00'))
        # Grand total = (4000 - 250) + 684 = 4434.00
        self.assertEqual(invoice.grand_total, Decimal('4434.00'))

        item = invoice.items.first()
        self.assertEqual(item.discount, Decimal('200.00'))
        self.assertEqual(item.total, Decimal('4484.00'))

    def test_multiple_products_added_to_same_invoice(self):
        # Create second and third products
        prod2 = Product.objects.create(
            name='Thermal Receipt Printer',
            sku='PRN-002',
            price=Decimal('3000.00'),
            gst_rate=Decimal('12.00'),
            stock=15,
            unit='Pcs',
            created_by=self.user
        )
        prod3 = Product.objects.create(
            name='Thermal Paper Rolls',
            sku='ROL-003',
            price=Decimal('500.00'),
            gst_rate=Decimal('5.00'),
            stock=100,
            unit='Box',
            created_by=self.user
        )

        # 3 products in one invoice:
        # Item 1: self.product (price 2000, qty 2, disc 100, gst 18%) -> taxable 3900, tax 702, total 4602
        # Item 2: prod2 (price 3000, qty 1, disc 0, gst 12%) -> taxable 3000, tax 360, total 3360
        # Item 3: prod3 (price 500, qty 4, disc 50, gst 5%) -> taxable 1950, tax 97.50, total 2047.50
        items_payload = json.dumps([
            {
                'product_id': self.product.id,
                'name': self.product.name,
                'price': '2000.00',
                'qty': 2,
                'discount': '100.00',
                'tax': '18.00'
            },
            {
                'product_id': prod2.id,
                'name': prod2.name,
                'price': '3000.00',
                'qty': 1,
                'discount': '0.00',
                'tax': '12.00'
            },
            {
                'product_id': prod3.id,
                'name': prod3.name,
                'price': '500.00',
                'qty': 4,
                'discount': '50.00',
                'tax': '5.00'
            }
        ])

        post_data = {
            'customer': self.customer.id,
            'customer_name': self.customer.name,
            'customer_phone': self.customer.phone,
            'payment_method': 'UPI QR Code',
            'discount': '0.00',
            'notes': 'Multi-product order',
            'items_data': items_payload
        }

        form = InvoiceCreationForm(data=post_data, user=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        invoice = form.save(distributor=self.user)

        # Verify 3 distinct line items saved to invoice
        self.assertEqual(invoice.items.count(), 3)

        # Subtotal: (2000*2) + (3000*1) + (500*4) = 4000 + 3000 + 2000 = 9000
        self.assertEqual(invoice.subtotal, Decimal('9000.00'))

        # Total item discount: 100 + 0 + 50 = 150
        self.assertEqual(invoice.discount, Decimal('150.00'))

        # Tax: 702 + 360 + 97.50 = 1159.50
        self.assertEqual(invoice.tax_amount, Decimal('1159.50'))

        # Grand total = (9000 - 150) + 1159.50 = 10009.50
        self.assertEqual(invoice.grand_total, Decimal('10009.50'))

        # Verify stock was decremented for all 3 products in inventory
        self.product.refresh_from_db()
        prod2.refresh_from_db()
        prod3.refresh_from_db()
        self.assertEqual(self.product.stock, 25 - 2) # 23
        self.assertEqual(prod2.stock, 15 - 1)       # 14
        self.assertEqual(prod3.stock, 100 - 4)      # 96


class AdminRegistrationTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_admin_registration_success(self):
        import json
        data = {
            'first_name': 'Super',
            'last_name': 'Admin',
            'business_name': 'Admin Corp',
            'phone': '1234567890',
            'email': 'admin_new@example.com',
            'username': 'admin_new',
            'password': 'AdminPassword123!',
        }
        response = self.client.post(reverse('api_register_admin'), data=json.dumps(data), content_type='application/json')
        self.assertIn(response.status_code, [200, 201])
        resp_data = response.json()
        self.assertTrue(resp_data.get('success'))

        # Verify user & profile created properly
        user = User.objects.filter(username='admin_new').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.email, 'admin_new@example.com')
        self.assertTrue(user.check_password('AdminPassword123!'))

        self.assertEqual(user.profile.role, 'ADMIN')
        self.assertEqual(user.profile.business_name, 'Admin Corp')
        self.assertEqual(user.profile.phone, '1234567890')


from billing_app.models import OTPToken

class PasswordRecoveryTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_superuser(username='admin', email='admin@example.com', password='password123')
        # Trigger signal/create profile
        from billing_app.models import UserProfile
        profile, _ = UserProfile.objects.get_or_create(user=self.admin)
        profile.role = 'ADMIN'
        profile.save()

    def test_admin_request_otp(self):
        data = {
            'action': 'request_otp',
            'identity': 'admin'
        }
        response = self.client.post(reverse('admin_forgot_password'), data)
        self.assertEqual(response.status_code, 302)
        
        # Verify OTP is created
        token = OTPToken.objects.filter(user=self.admin).first()
        self.assertIsNotNone(token)
        
        # Verify session is updated
        self.assertEqual(self.client.session.get('admin_reset_user_id'), self.admin.id)
        self.assertEqual(self.client.session.get('admin_reset_step'), 2)

    def test_admin_verify_otp(self):
        # 1. Setup session as if step 1 was completed
        token = OTPToken.generate_otp_for_user(self.admin)
        session = self.client.session
        session['admin_reset_user_id'] = self.admin.id
        session['admin_reset_step'] = 2
        session['admin_reset_otp'] = token.otp_code
        session.save()

        # 2. Submit valid OTP
        data = {
            'action': 'verify_otp',
            'otp_code': token.otp_code
        }
        response = self.client.post(reverse('admin_forgot_password'), data)
        self.assertEqual(response.status_code, 302)
        
        # 3. Verify OTP marked as verified and session moves to step 3
        token.refresh_from_db()
        self.assertTrue(token.is_verified)
        self.assertEqual(self.client.session.get('admin_reset_step'), 3)

    def test_admin_reset_password(self):
        # 1. Setup session as if step 2 was completed
        session = self.client.session
        session['admin_reset_user_id'] = self.admin.id
        session['admin_reset_step'] = 3
        session.save()

        # 2. Submit new password
        data = {
            'action': 'reset_password',
            'new_password': 'NewPassword123!',
            'confirm_password': 'NewPassword123!'
        }
        response = self.client.post(reverse('admin_forgot_password'), data)
        self.assertEqual(response.status_code, 302)
        
        # 3. Verify password was updated
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.check_password('NewPassword123!'))


class CustomerRegistrationAPITestCase(TestCase):
    def setUp(self):
        # Create a test distributor
        self.distributor = User.objects.create_user(
            username='api_distributor',
            email='api_dist@test.com',
            password='distpass123'
        )
        self.profile, _ = UserProfile.objects.get_or_create(
            user=self.distributor,
            defaults={
                'role': 'DISTRIBUTOR',
                'business_name': 'API Distribution Ltd',
                'phone': '9876543210'
            }
        )
        self.profile.role = 'DISTRIBUTOR'
        self.profile.save()

    def test_customer_registration_success_json(self):
        import json
        payload = {
            'name': 'Ramesh Patel',
            'phone': '9876500001',
            'email': 'ramesh@example.com',
            'address': '45 MG Road',
            'city': 'Ahmedabad',
            'gstin': '24AAAAA0000A1Z5',
            'distributor_username': 'api_distributor'
        }
        response = self.client.post(
            reverse('api_register_customer'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertTrue(res_data.get('success'))
        self.assertEqual(res_data['customer']['name'], 'Ramesh Patel')
        self.assertEqual(res_data['customer']['phone'], '9876500001')
        self.assertEqual(res_data['customer']['distributor'], 'api_distributor')

        # Verify Customer in database
        customer = Customer.objects.filter(phone='9876500001').first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.name, 'Ramesh Patel')
        self.assertEqual(customer.city, 'Ahmedabad')
        self.assertEqual(customer.created_by, self.distributor)

    def test_customer_registration_with_authenticated_distributor(self):
        import json
        self.client.login(username='api_distributor', password='distpass123')
        payload = {
            'name': 'Suresh Mehta',
            'phone': '9876500002',
            'city': 'Surat'
        }
        response = self.client.post(
            reverse('api_register_customer'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        res_data = response.json()
        self.assertTrue(res_data.get('success'))

        customer = Customer.objects.filter(phone='9876500002').first()
        self.assertIsNotNone(customer)
        self.assertEqual(customer.created_by, self.distributor)

    def test_customer_registration_validation_missing_name(self):
        import json
        payload = {
            'phone': '9876500003'
        }
        response = self.client.post(
            reverse('api_register_customer'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.json().get('success'))

    def test_customer_registration_duplicate_phone_prevention(self):
        import json
        Customer.objects.create(
            name='First Registration',
            phone='9876500004',
            created_by=self.distributor
        )
        payload = {
            'name': 'Duplicate Person',
            'phone': '9876500004',
            'distributor_username': 'api_distributor'
        }
        response = self.client.post(
            reverse('api_register_customer'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.json().get('success'))

    def test_distributor_registration_api(self):
        import json
        payload = {
            'username': 'new_distributor_api',
            'email': 'newdist@test.com',
            'password': 'Password123!',
            'full_name': 'Kavita Verma',
            'business_name': 'Verma Traders',
            'phone': '9876500005',
            'upi_id': 'verma@upi'
        }
        response = self.client.post(
            reverse('api_register_distributor'),
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 201)
        res = response.json()
        self.assertTrue(res.get('success'))
        self.assertEqual(res['distributor']['username'], 'new_distributor_api')

        # Check DB
        user = User.objects.filter(username='new_distributor_api').first()
        self.assertIsNotNone(user)
        self.assertEqual(user.profile.role, 'DISTRIBUTOR')
        self.assertEqual(user.profile.business_name, 'Verma Traders')

