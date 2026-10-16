from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from billing_app.models import UserProfile
from billing_app.decorators import (
    admin_required, distributor_required, role_required,
    api_login_required, api_admin_required
)


class RouteProtectionMiddlewareTestCase(TestCase):
    """
    Comprehensive test suite for RouteProtectionMiddleware.
    Validates route guarding for Admin, Distributor, and Core Management paths,
    as well as API/AJAX 401/403 responses and public route accessibility.
    """

    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin = User.objects.create_superuser(
            username='guard_admin',
            email='guard_admin@example.com',
            password='Password123!'
        )
        UserProfile.objects.get_or_create(user=self.admin, defaults={'role': 'ADMIN'})

        # Distributor user
        self.distributor = User.objects.create_user(
            username='guard_distributor',
            email='guard_dist@example.com',
            password='Password123!'
        )
        UserProfile.objects.get_or_create(user=self.distributor, defaults={'role': 'DISTRIBUTOR'})

    def test_public_routes_accessible_without_auth(self):
        """Verify public landing, auth, and onboarding pages are accessible."""
        public_urls = [
            'portal_select',
            'admin_login',
            'distributor_login',
            'admin_register',
            'distributor_register',
            'forgot_password',
            'admin_forgot_password',
        ]
        for url_name in public_urls:
            response = self.client.get(reverse(url_name))
            self.assertEqual(
                response.status_code, 200,
                f"Expected 200 for public url '{url_name}', got {response.status_code}"
            )

    def test_admin_dashboard_unauthenticated_redirects_to_login(self):
        """Unauthenticated GET to /admin/dashboard/ redirects to admin_login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/admin/', response.url)

    def test_admin_reports_unauthenticated_redirects_to_login(self):
        """Unauthenticated GET to /admin/reports/ redirects to admin_login."""
        response = self.client.get(reverse('admin_reports'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/admin/', response.url)

    def test_admin_route_ajax_unauthenticated_returns_401(self):
        """Unauthenticated AJAX GET to admin route returns HTTP 401 JSON."""
        response = self.client.get(
            reverse('admin_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Authentication required', data['message'])

    def test_admin_dashboard_distributor_denied_access(self):
        """Distributor user attempting to access admin route is redirected with Access Denied."""
        self.client.login(username='guard_distributor', password='Password123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/distributor/dashboard/', response.url)

    def test_admin_dashboard_distributor_ajax_returns_403(self):
        """Distributor user making AJAX request to admin route gets HTTP 403 Forbidden."""
        self.client.login(username='guard_distributor', password='Password123!')
        response = self.client.get(
            reverse('admin_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 403)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Access Denied', data['message'])

    def test_admin_dashboard_admin_allowed(self):
        """Admin user has full access to admin dashboard."""
        self.client.login(username='guard_admin', password='Password123!')
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_distributor_dashboard_unauthenticated_redirects(self):
        """Unauthenticated GET to distributor dashboard redirects to distributor_login."""
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/distributor/', response.url)

    def test_distributor_dashboard_ajax_unauthenticated_returns_401(self):
        """Unauthenticated AJAX GET to distributor route returns HTTP 401 JSON."""
        response = self.client.get(
            reverse('distributor_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    def test_distributor_dashboard_distributor_allowed(self):
        """Distributor user has full access to distributor dashboard."""
        self.client.login(username='guard_distributor', password='Password123!')
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 200)

    def test_invoices_unauthenticated_redirects(self):
        """Unauthenticated GET to invoice list redirects."""
        response = self.client.get(reverse('invoice_list'))
        self.assertEqual(response.status_code, 302)

    def test_customers_unauthenticated_redirects(self):
        """Unauthenticated GET to customer list redirects."""
        response = self.client.get(reverse('customer_list'))
        self.assertEqual(response.status_code, 302)

    def test_products_unauthenticated_redirects(self):
        """Unauthenticated GET to product list redirects."""
        response = self.client.get(reverse('product_list'))
        self.assertEqual(response.status_code, 302)


class RouteDecoratorsTestCase(TestCase):
    """
    Unit test suite verifying custom decorators directly:
    - @admin_required
    - @distributor_required
    - @role_required
    - @api_login_required
    - @api_admin_required
    """

    def setUp(self):
        self.factory = RequestFactory()
        self.admin = User.objects.create_superuser(
            username='dec_admin',
            email='dec_admin@example.com',
            password='Password123!'
        )
        UserProfile.objects.get_or_create(user=self.admin, defaults={'role': 'ADMIN'})

        self.distributor = User.objects.create_user(
            username='dec_distributor',
            email='dec_dist@example.com',
            password='Password123!'
        )
        UserProfile.objects.get_or_create(user=self.distributor, defaults={'role': 'DISTRIBUTOR'})

    def test_api_login_required_unauthenticated(self):
        @api_login_required
        def dummy_api(request):
            return JsonResponse({'success': True})

        req = self.factory.get('/api/sample/')
        req.user = AnonymousUser()
        res = dummy_api(req)
        self.assertEqual(res.status_code, 401)

    def test_api_login_required_authenticated(self):
        @api_login_required
        def dummy_api(request):
            return JsonResponse({'success': True})

        req = self.factory.get('/api/sample/')
        req.user = self.distributor
        res = dummy_api(req)
        self.assertEqual(res.status_code, 200)

    def test_api_admin_required_distributor_rejected(self):
        @api_admin_required
        def dummy_admin_api(request):
            return JsonResponse({'success': True})

        req = self.factory.get('/api/admin/dummy/')
        req.user = self.distributor
        res = dummy_admin_api(req)
        self.assertEqual(res.status_code, 403)

    def test_api_admin_required_admin_allowed(self):
        @api_admin_required
        def dummy_admin_api(request):
            return JsonResponse({'success': True})

        req = self.factory.get('/api/admin/dummy/')
        req.user = self.admin
        res = dummy_admin_api(req)
        self.assertEqual(res.status_code, 200)

    def test_role_required_decorator(self):
        @role_required(['ADMIN'])
        def admin_only_view(request):
            return HttpResponse("OK")

        req = self.factory.get('/some-route/')
        req.user = self.distributor
        res = admin_only_view(req)
        self.assertEqual(res.status_code, 302)

        req.user = self.admin
        res2 = admin_only_view(req)
        self.assertEqual(res2.status_code, 200)
        self.assertEqual(res2.content.decode(), "OK")
