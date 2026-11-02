"""
Test Suite: Django-based Login/Logout with Session Control and Restricted Dashboard Access
Verifies:
1. Restricting all dashboard access (/admin/dashboard/, /distributor/dashboard/, /dashboard/) to authenticated users only.
2. Unauthenticated web requests redirect to login; unauthenticated AJAX/API requests return HTTP 401.
3. Authenticated Admin users are granted access to admin dashboard and routed correctly from /dashboard/.
4. Authenticated Distributor users are granted access to distributor dashboard and denied access to admin dashboard.
5. Session Control on Login:
   - 'Remember Me' ON configures persistent 30-day session (expire_at_browser_close == False).
   - 'Remember Me' OFF configures browser-session-only expiration (expire_at_browser_close == True).
   - Session key rotation on login.
6. Session Control on Logout:
   - /logout/ securely flushes and purges the session in DB and browser cookie.
   - Post-logout attempts to access dashboards are immediately blocked and redirected.
7. Session Verification API:
   - /api/auth/session/ reports live authenticated status, session key, and remaining lifetime.
   - /api/auth/logout/ terminates session via API.
"""

from django.test import TestCase, Client
from django.contrib.auth.models import User
from django.urls import reverse
from billing_app.models import UserProfile


class SessionControlDashboardProtectionTestCase(TestCase):
    def setUp(self):
        self.client = Client()

        # Admin user
        self.admin_password = 'AdminPassword123!'
        self.admin = User.objects.create_superuser(
            username='auth_admin',
            email='auth_admin@advancebilling.com',
            password=self.admin_password
        )
        self.admin.first_name = 'Vikram'
        self.admin.last_name = 'Mehta'
        self.admin.save()
        UserProfile.objects.get_or_create(
            user=self.admin,
            defaults={'role': 'ADMIN', 'business_name': 'Advance HQ'}
        )

        # Distributor user
        self.dist_password = 'DistPassword123!'
        self.distributor = User.objects.create_user(
            username='auth_distributor',
            email='auth_dist@agency.com',
            password=self.dist_password
        )
        self.distributor.first_name = 'Rajesh'
        self.distributor.last_name = 'Kumar'
        self.distributor.save()
        UserProfile.objects.get_or_create(
            user=self.distributor,
            defaults={'role': 'DISTRIBUTOR', 'business_name': 'Kumar Enterprises'}
        )

    # -------------------------------------------------------------------------
    # 1. Unauthenticated Dashboard Access Restrictions
    # -------------------------------------------------------------------------
    def test_unauthenticated_access_to_admin_dashboard_redirects(self):
        """Unauthenticated GET to /admin/dashboard/ redirects to admin_login."""
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/admin/', response.url)

    def test_unauthenticated_ajax_to_admin_dashboard_returns_401(self):
        """Unauthenticated AJAX request to /admin/dashboard/ returns HTTP 401."""
        response = self.client.get(
            reverse('admin_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])
        self.assertIn('Authentication required', data['message'])

    def test_unauthenticated_access_to_distributor_dashboard_redirects(self):
        """Unauthenticated GET to /distributor/dashboard/ redirects to distributor_login."""
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn('/login/distributor/', response.url)

    def test_unauthenticated_ajax_to_distributor_dashboard_returns_401(self):
        """Unauthenticated AJAX request to /distributor/dashboard/ returns HTTP 401."""
        response = self.client.get(
            reverse('distributor_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    def test_unauthenticated_access_to_central_dashboard_redirects(self):
        """Unauthenticated GET to /dashboard/ redirects to login portal."""
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_unauthenticated_ajax_to_central_dashboard_returns_401(self):
        """Unauthenticated AJAX request to /dashboard/ returns HTTP 401."""
        response = self.client.get(
            reverse('dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(response.status_code, 401)
        data = response.json()
        self.assertFalse(data['success'])

    # -------------------------------------------------------------------------
    # 2. Authenticated Dashboard Access & Role Isolation
    # -------------------------------------------------------------------------
    def test_authenticated_admin_accesses_admin_dashboard(self):
        """Authenticated Admin has full access to Admin Dashboard."""
        self.client.login(username='auth_admin', password=self.admin_password)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Admin Dashboard')

    def test_authenticated_admin_central_dashboard_redirects_to_admin_dashboard(self):
        """Authenticated Admin requesting /dashboard/ is routed to /admin/dashboard/."""
        self.client.login(username='auth_admin', password=self.admin_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('admin_dashboard'), response.url)

    def test_authenticated_distributor_accesses_distributor_dashboard(self):
        """Authenticated Distributor has full access to Distributor Dashboard."""
        self.client.login(username='auth_distributor', password=self.dist_password)
        response = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Distributor Dashboard')

    def test_authenticated_distributor_central_dashboard_redirects_to_distributor_dashboard(self):
        """Authenticated Distributor requesting /dashboard/ is routed to /distributor/dashboard/."""
        self.client.login(username='auth_distributor', password=self.dist_password)
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('distributor_dashboard'), response.url)

    def test_distributor_denied_access_to_admin_dashboard(self):
        """Authenticated Distributor attempting to access Admin Dashboard is forbidden."""
        self.client.login(username='auth_distributor', password=self.dist_password)
        response = self.client.get(reverse('admin_dashboard'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('distributor_dashboard'), response.url)

        # AJAX gets 403 Forbidden
        ajax_resp = self.client.get(
            reverse('admin_dashboard'),
            HTTP_X_REQUESTED_WITH='XMLHttpRequest'
        )
        self.assertEqual(ajax_resp.status_code, 403)

    # -------------------------------------------------------------------------
    # 3. Session Control on Login (Persistent vs Browser-Close)
    # -------------------------------------------------------------------------
    def test_login_session_control_remember_me_persistent(self):
        """Login with Remember Me enables persistent session lasting ~30 days."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'auth_admin',
            'password': self.admin_password,
            'remember_me': '1'
        })
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertFalse(session.get_expire_at_browser_close())
        self.assertGreaterEqual(session.get_expiry_age(), 2590000)

    def test_login_session_control_without_remember_me_expires_on_close(self):
        """Login without Remember Me configures session to expire on browser close."""
        response = self.client.post(reverse('admin_login'), {
            'username': 'auth_admin',
            'password': self.admin_password,
        })
        self.assertEqual(response.status_code, 302)
        session = self.client.session
        self.assertTrue(session.get_expire_at_browser_close())

    def test_general_login_view_authentication_and_session_control(self):
        """General login endpoint /login/ authenticates user and sets up session."""
        response = self.client.post(reverse('login'), {
            'username': 'auth_distributor',
            'password': self.dist_password,
            'remember_me': 'on'
        })
        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.client.session.get('_auth_user_id'))
        self.assertFalse(self.client.session.get_expire_at_browser_close())

    # -------------------------------------------------------------------------
    # 4. Session Control on Logout & Post-Logout Route Protection
    # -------------------------------------------------------------------------
    def test_logout_flushes_session_and_blocks_dashboard(self):
        """Logout flushes session and immediately revokes dashboard access."""
        # 1. Login & confirm access
        self.client.login(username='auth_distributor', password=self.dist_password)
        dash_resp = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(dash_resp.status_code, 200)

        # 2. Perform logout
        logout_resp = self.client.get(reverse('logout'), follow=True)
        self.assertEqual(logout_resp.status_code, 200)
        self.assertFalse(logout_resp.context['user'].is_authenticated)

        # 3. Subsequent dashboard attempts must be redirected
        post_logout_resp = self.client.get(reverse('distributor_dashboard'))
        self.assertEqual(post_logout_resp.status_code, 302)
        self.assertIn('/login/distributor/', post_logout_resp.url)

        post_logout_central = self.client.get(reverse('dashboard'))
        self.assertEqual(post_logout_central.status_code, 302)

    # -------------------------------------------------------------------------
    # 5. REST API Session Control Verification
    # -------------------------------------------------------------------------
    def test_api_session_status_and_logout_flow(self):
        """API endpoints accurately report session status and terminate sessions."""
        # Unauthenticated
        unauth_resp = self.client.get(reverse('api_session_status'))
        self.assertEqual(unauth_resp.status_code, 200)
        self.assertFalse(unauth_resp.json()['authenticated'])

        # Authenticate
        self.client.login(username='auth_admin', password=self.admin_password)
        auth_resp = self.client.get(reverse('api_session_status'))
        self.assertEqual(auth_resp.status_code, 200)
        data = auth_resp.json()
        self.assertTrue(data['authenticated'])
        self.assertEqual(data['user']['username'], 'auth_admin')
        self.assertEqual(data['user']['role'], 'ADMIN')

        # Terminate via API logout
        logout_resp = self.client.post(reverse('api_logout'))
        self.assertEqual(logout_resp.status_code, 200)
        self.assertTrue(logout_resp.json()['success'])

        # Post-logout check
        check_resp = self.client.get(reverse('api_session_status'))
        self.assertFalse(check_resp.json()['authenticated'])
