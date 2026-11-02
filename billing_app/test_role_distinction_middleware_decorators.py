"""
Test Suite: Custom Middleware and Decorators to Distinguish Between Admin and Distributor Users After Login
Verifies:
1. UserRoleMiddleware accurately distinguishes Admin vs Distributor on request object:
   - request.user_role ('ADMIN' vs 'DISTRIBUTOR' vs 'ANONYMOUS')
   - request.is_admin (True for Admin, False for Distributor)
   - request.is_distributor (True for Distributor, False for Admin)
   - request.user_profile
2. Custom View Decorators:
   - @admin_required enforces Admin role and blocks Distributors with friendly message/redirect or 403 AJAX.
   - @distributor_required enforces Distributor access.
   - @role_required(['ADMIN', 'DISTRIBUTOR']) validates against specific allowed roles.
   - @distinguish_role(admin_func=..., distributor_func=...) automatically dispatches execution based on logged-in role.
3. API Decorators:
   - @api_admin_required returns 401 for unauthenticated, 403 for distributors.
   - @api_distributor_required returns 401 for unauthenticated, 403 for admins.
4. Context Processor:
   - user_role_context exposes is_admin, is_distributor, and user_role to templates.
5. Helper functions:
   - get_user_role(user) correctly distinguishes role strings.
"""

import json
from django.test import TestCase, Client, RequestFactory
from django.contrib.auth.models import User, AnonymousUser
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from billing_app.models import UserProfile
from billing_app.middleware import UserRoleMiddleware
from billing_app.context_processors import user_role_context
from billing_app.decorators import (
    admin_required, distributor_required, role_required,
    distinguish_role, api_admin_required, api_distributor_required,
    get_user_role
)


class RoleDistinctionMiddlewareAndDecoratorsTestCase(TestCase):
    def setUp(self):
        self.client = Client()
        self.factory = RequestFactory()

        # Admin User
        self.admin = User.objects.create_superuser(
            username='role_admin',
            email='admin@billingcorp.com',
            password='AdminPass123!'
        )
        UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': 'ADMIN', 'business_name': 'Central Admin HQ'}
        )

        # Distributor User
        self.distributor = User.objects.create_user(
            username='role_distributor',
            email='dist@agencyhub.com',
            password='DistPass123!'
        )
        UserProfile.objects.get_or_create(
            user=self.distributor,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Agency Hub Wholesale'}
        )

    # -------------------------------------------------------------------------
    # 1. UserRoleMiddleware Tests
    # -------------------------------------------------------------------------
    def test_middleware_anonymous_user_distinction(self):
        """UserRoleMiddleware assigns ANONYMOUS role when unauthenticated."""
        request = self.factory.get('/')
        request.user = AnonymousUser()

        mw = UserRoleMiddleware(lambda req: HttpResponse('OK'))
        response = mw(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_role, 'ANONYMOUS')
        self.assertFalse(request.is_admin)
        self.assertFalse(request.is_distributor)
        self.assertIsNone(request.user_profile)

    def test_middleware_admin_user_distinction(self):
        """UserRoleMiddleware distinguishes Admin user after login."""
        request = self.factory.get('/')
        request.user = self.admin

        mw = UserRoleMiddleware(lambda req: HttpResponse('OK'))
        response = mw(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_role, 'ADMIN')
        self.assertTrue(request.is_admin)
        self.assertFalse(request.is_distributor)
        self.assertIsNotNone(request.user_profile)
        self.assertEqual(request.user_profile.role, 'ADMIN')

    def test_middleware_distributor_user_distinction(self):
        """UserRoleMiddleware distinguishes Distributor user after login."""
        request = self.factory.get('/')
        request.user = self.distributor

        mw = UserRoleMiddleware(lambda req: HttpResponse('OK'))
        response = mw(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(request.user_role, 'DISTRIBUTOR')
        self.assertFalse(request.is_admin)
        self.assertTrue(request.is_distributor)
        self.assertIsNotNone(request.user_profile)
        self.assertEqual(request.user_profile.role, 'DISTRIBUTOR')

    # -------------------------------------------------------------------------
    # 2. View Decorator Tests (@admin_required & @distributor_required)
    # -------------------------------------------------------------------------
    def test_admin_required_allows_admin(self):
        """@admin_required permits Admin user to execute view."""
        @admin_required
        def dummy_admin_view(request):
            return HttpResponse('Welcome Admin')

        request = self.factory.get('/admin/test/')
        request.user = self.admin
        response = dummy_admin_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Welcome Admin')

    def test_admin_required_distinguishes_and_denies_distributor(self):
        """@admin_required recognizes Distributor user, denies access, and redirects."""
        @admin_required
        def dummy_admin_view(request):
            return HttpResponse('Welcome Admin')

        request = self.factory.get('/admin/test/')
        request.user = self.distributor
        request.session = {}
        request._messages = []

        response = dummy_admin_view(request)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/distributor/dashboard/', response.url)

    def test_admin_required_ajax_returns_403_for_distributor(self):
        """@admin_required returns HTTP 403 Forbidden for distributor AJAX call."""
        @admin_required
        def dummy_admin_view(request):
            return HttpResponse('Welcome Admin')

        request = self.factory.get('/admin/test/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        request.user = self.distributor
        response = dummy_admin_view(request)
        self.assertEqual(response.status_code, 403)
        data = json.loads(response.content.decode())
        self.assertIn('Access Denied', data['message'])

    def test_distributor_required_allows_distributor(self):
        """@distributor_required permits Distributor user to execute view."""
        @distributor_required
        def dummy_dist_view(request):
            return HttpResponse('Welcome Distributor')

        request = self.factory.get('/distributor/test/')
        request.user = self.distributor
        response = dummy_dist_view(request)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content.decode(), 'Welcome Distributor')

    # -------------------------------------------------------------------------
    # 3. Role Dispatcher Decorator (@distinguish_role)
    # -------------------------------------------------------------------------
    def test_distinguish_role_decorator_dispatches_cleanly(self):
        """@distinguish_role automatically dispatches execution based on user role."""
        def admin_handler(request):
            return HttpResponse('Executed Admin Handler')

        def dist_handler(request):
            return HttpResponse('Executed Distributor Handler')

        @distinguish_role(admin_func=admin_handler, distributor_func=dist_handler)
        def fallback_view(request):
            return HttpResponse('Fallback')

        # Test Admin invocation
        admin_req = self.factory.get('/role-dispatch/')
        admin_req.user = self.admin
        admin_resp = fallback_view(admin_req)
        self.assertEqual(admin_resp.content.decode(), 'Executed Admin Handler')

        # Test Distributor invocation
        dist_req = self.factory.get('/role-dispatch/')
        dist_req.user = self.distributor
        dist_resp = fallback_view(dist_req)
        self.assertEqual(dist_resp.content.decode(), 'Executed Distributor Handler')

    # -------------------------------------------------------------------------
    # 4. API Decorators (@api_admin_required & @api_distributor_required)
    # -------------------------------------------------------------------------
    def test_api_admin_required_distinguishes_roles(self):
        """@api_admin_required allows admin (200) and rejects distributor (403)."""
        @api_admin_required
        def test_api(request):
            return JsonResponse({'success': True, 'data': 'admin_secret'})

        # Admin
        req_admin = self.factory.get('/api/admin/secret/')
        req_admin.user = self.admin
        resp_admin = test_api(req_admin)
        self.assertEqual(resp_admin.status_code, 200)
        data_admin = json.loads(resp_admin.content.decode())
        self.assertTrue(data_admin['success'])

        # Distributor
        req_dist = self.factory.get('/api/admin/secret/')
        req_dist.user = self.distributor
        resp_dist = test_api(req_dist)
        self.assertEqual(resp_dist.status_code, 403)
        data_dist = json.loads(resp_dist.content.decode())
        self.assertFalse(data_dist['success'])

    def test_api_distributor_required_distinguishes_roles(self):
        """@api_distributor_required allows distributor (200) and rejects admin (403)."""
        @api_distributor_required
        def test_dist_api(request):
            return JsonResponse({'success': True, 'data': 'distributor_billing'})

        # Distributor
        req_dist = self.factory.get('/api/dist/data/')
        req_dist.user = self.distributor
        resp_dist = test_dist_api(req_dist)
        self.assertEqual(resp_dist.status_code, 200)
        data_dist = json.loads(resp_dist.content.decode())
        self.assertTrue(data_dist['success'])

        # Admin
        req_admin = self.factory.get('/api/dist/data/')
        req_admin.user = self.admin
        resp_admin = test_dist_api(req_admin)
        self.assertEqual(resp_admin.status_code, 403)
        data_admin = json.loads(resp_admin.content.decode())
        self.assertFalse(data_admin['success'])

    # -------------------------------------------------------------------------
    # 5. Helper Function & Context Processor Tests
    # -------------------------------------------------------------------------
    def test_get_user_role_helper(self):
        """get_user_role helper correctly distinguishes roles."""
        self.assertEqual(get_user_role(self.admin), 'ADMIN')
        self.assertEqual(get_user_role(self.distributor), 'DISTRIBUTOR')
        self.assertEqual(get_user_role(AnonymousUser()), 'ANONYMOUS')

    def test_user_role_context_processor(self):
        """user_role_context injects role distinction into templates."""
        req = self.factory.get('/')
        req.user = self.admin
        req.user_role = 'ADMIN'
        req.is_admin = True
        req.is_distributor = False
        req.user_profile = self.admin.profile

        ctx = user_role_context(req)
        self.assertEqual(ctx['user_role'], 'ADMIN')
        self.assertTrue(ctx['is_admin'])
        self.assertFalse(ctx['is_distributor'])
        self.assertEqual(ctx['user_profile'], self.admin.profile)
