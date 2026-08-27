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


