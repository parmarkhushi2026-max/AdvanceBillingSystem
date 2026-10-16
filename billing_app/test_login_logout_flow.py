from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile
import json


class LoginLogoutFlowTestCase(TestCase):
    """
    Comprehensive test suite for Login and Logout flows.
    Tests Web Form flows, JSON API flows, Session management,
    'Remember Me' options, Email vs Username auth, and Post-logout Route Protection.
    """

    def setUp(self):
        self.client = Client()

        # Admin User
        self.admin_password = 'AdminPassword123!'
        self.admin = User.objects.create_superuser(
            username='flow_admin',
            email='flow_admin@advancebilling.com',
            password=self.admin_password
        )
        self.admin.first_name = 'Vikram'
        self.admin.last_name = 'Mehta'
        self.admin.save()
        UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': 'ADMIN', 'business_name': 'Advance HQ'}
        )

        # Distributor User
        self.dist_password = 'DistPassword123!'
        self.distributor = User.objects.create_user(
            username='flow_distributor',
            email='flow_dist@agency.com',
            password=self.dist_password
        )
        self.distributor.first_name = 'Sanjay'
        self.distributor.last_name = 'Patel'
        self.distributor.save()
        UserProfile.objects.get_or_create(
            user=self.distributor,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Patel Distributions'}
        )

    # -------------------------------------------------------------
    # 1. Admin Web Login Flow Tests
    # -------------------------------------------------------------
    def test_admin_web_login_success_with_username(self):
        """Valid admin username and password logs in and redirects to admin dashboard."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'flow_admin',
            'password': self.admin_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_dashboard'), response.url)

        # Follow redirect and verify dashboard access
        dash_response = self.client.get(response.url)
        self.assertEqual(dash_response.status_code, 200)
        self.assertTrue(dash_response.context['user'].is_authenticated)
        self.assertEqual(dash_response.context['user'].username, 'flow_admin')

    def test_admin_web_login_success_with_email(self):
        """Admin can log in using their email address via EmailOrUsernameBackend."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'flow_admin@advancebilling.com',
            'password': self.admin_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_dashboard'), response.url)

    def test_admin_web_login_invalid_password(self):
        """Invalid credentials stay on login page with error and do not authenticate."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'flow_admin',
            'password': 'WrongPassword999',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login_admin.html')
        self.assertFalse(response.context['user'].is_authenticated)

    def test_admin_login_remember_me_persistent_session(self):
        """Enabling 'remember_me' configures a 30-day persistent session."""
        self.client.post(reverse('admin_login'), {
            'username': 'flow_admin',
            'password': self.admin_password,
            'remember_me': 'on'
        })
        session = self.client.session
        self.assertFalse(session.get_expire_at_browser_close())
        # Age should be approx 30 days (2,592,000s)
        self.assertGreaterEqual(session.get_expiry_age(), 2590000)

    def test_admin_login_without_remember_me_session_expires_on_close(self):
        """Without 'remember_me', session expires on browser close."""
        self.client.post(reverse('admin_login'), {
            'username': 'flow_admin',
            'password': self.admin_password,
        })
        session = self.client.session
        self.assertTrue(session.get_expire_at_browser_close())

    def test_admin_login_next_parameter_redirect(self):
        """When ?next= is provided, successful login redirects to the requested URL."""
        response = self.client.post(f"{reverse('admin_login')}?next={reverse('admin_reports')}", {
            'username': 'flow_admin',
            'password': self.admin_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_reports'), response.url)

    def test_authenticated_admin_visiting_login_redirects_to_dashboard(self):
        """Already authenticated admin visiting login page is redirected to dashboard."""
        self.client.login(username='flow_admin', password=self.admin_password)
        response = self.client.get(reverse('admin_login'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_dashboard'), response.url)

    # -------------------------------------------------------------
    # 2. Distributor Web Login Flow Tests
    # -------------------------------------------------------------
    def test_distributor_web_login_success_with_username(self):
        """Valid distributor username logs in and redirects to distributor dashboard."""
        response = self.client.post(reverse('distributor_login'), {
            'username': 'flow_distributor',
            'password': self.dist_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('distributor_dashboard'), response.url)

        # Follow redirect and verify dashboard loads
        dash_response = self.client.get(response.url)
        self.assertEqual(dash_response.status_code, 200)
        self.assertTrue(dash_response.context['user'].is_authenticated)
        self.assertEqual(dash_response.context['user'].username, 'flow_distributor')

    def test_distributor_web_login_success_with_email(self):
        """Distributor can log in using their email address."""
        response = self.client.post(reverse('distributor_login'), {
            'username': 'flow_dist@agency.com',
            'password': self.dist_password,
        })
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('distributor_dashboard'), response.url)

    def test_distributor_web_login_invalid_password(self):
        """Invalid distributor credentials remain on login page with error."""
        response = self.client.post(reverse('distributor_login'), {
            'username': 'flow_distributor',
            'password': 'WrongPassword123',
        })
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'auth/login_distributor.html')
        self.assertFalse(response.context['user'].is_authenticated)

    def test_authenticated_distributor_visiting_login_redirects(self):
        """Already authenticated distributor visiting login page is redirected to dashboard."""
        self.client.login(username='flow_distributor', password=self.dist_password)
        response = self.client.get(reverse('distributor_login'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('distributor_dashboard'), response.url)

    # -------------------------------------------------------------
    # 3. Web Logout Flow & Post-Logout Protection Tests
    # -------------------------------------------------------------
    def test_admin_web_logout_and_post_logout_route_protection(self):
        """Logging out flushes session, revokes access, and blocks protected routes."""
        # 1. Login
        self.client.login(username='flow_admin', password=self.admin_password)
        dash_res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(dash_res.status_code, 200)

        # 2. Logout
        logout_res = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(logout_res.status_code, 200)
        self.assertFalse(logout_res.context['user'].is_authenticated)

        # 3. Verify protected route is now blocked
        blocked_res = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(blocked_res.status_code, 302)
        self.assertIn(reverse('admin_login'), blocked_res.url)

    def test_distributor_web_logout_and_post_logout_protection(self):
        """Distributor logout clears session and prevents accessing distributor billing."""
        # 1. Login
        self.client.login(username='flow_distributor', password=self.dist_password)
        dash_res = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(dash_res.status_code, 200)

        # 2. Logout
        logout_res = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(logout_res.status_code, 200)

        # 3. Verify distributor billing is now blocked
        blocked_billing = self.client.get(reverse('create_invoice'))
        self.assertEqual(blocked_billing.status_code, 302)
        self.assertIn(reverse('distributor_login'), blocked_billing.url)

    # -------------------------------------------------------------
    # 4. JSON API Login & Logout Flows
    # -------------------------------------------------------------
    def test_api_login_admin_success(self):
        """POST to /api/login/admin/ with JSON credentials returns 200 and user profile."""
        payload = json.dumps({
            'username': 'flow_admin',
            'password': self.admin_password
        })
        response = self.client.post(
            reverse('api_login_admin'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'ADMIN')
        self.assertIn('/admin/dashboard/', data['redirect_url'])

    def test_api_login_distributor_success(self):
        """POST to /api/login/distributor/ with JSON returns 200 and distributor payload."""
        payload = json.dumps({
            'username': 'flow_distributor',
            'password': self.dist_password
        })
        response = self.client.post(
            reverse('api_login_distributor'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertEqual(data['user']['role'], 'DISTRIBUTOR')
        self.assertIn('/distributor/dashboard/', data['redirect_url'])

    def test_api_login_invalid_password_returns_401(self):
        """POST invalid credentials to API returns 401 Unauthorized JSON."""
        payload = json.dumps({
            'username': 'flow_admin',
            'password': 'InvalidPassword'
        })
        response = self.client.post(
            reverse('api_login_admin'),
            data=payload,
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    def test_api_session_status_and_api_logout_flow(self):
        """Complete cycle: API Login -> Session Status Check -> API Logout -> Session Status Revoked."""
        # 1. API Login
        self.client.login(username='flow_admin', password=self.admin_password)

        # 2. Check Session Status
        status_resp = self.client.get(reverse('api_session_status'))
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.json()
        self.assertTrue(status_data['authenticated'])
        self.assertEqual(status_data['user']['username'], 'flow_admin')

        # 3. Call API Logout
        logout_resp = self.client.post(reverse('api_logout'))
        self.assertEqual(logout_resp.status_code, 200)
        self.assertTrue(logout_resp.json()['success'])

        # 4. Verify Session Status is now Unauthenticated
        post_logout_status = self.client.get(reverse('api_session_status'))
        self.assertEqual(post_logout_status.status_code, 200)
        self.assertFalse(post_logout_status.json()['authenticated'])
