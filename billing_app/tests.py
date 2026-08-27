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
