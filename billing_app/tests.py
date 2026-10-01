from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from billing_app.models import Product

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

