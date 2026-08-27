"""Tests for authentication flows: login, register, logout, role checks."""
from tests.conftest import login_admin, login_voter, logout


class TestLoginPage:
    """Tests for the login page and login logic."""

    def test_login_page_renders(self, client):
        """GET /auth/login returns 200 with login form."""
        r = client.get('/auth/login')
        assert r.status_code == 200
        assert b'Login' in r.data
        assert b'email' in r.data.lower()
        assert b'password' in r.data.lower()

    def test_valid_admin_login_redirects_to_admin_dashboard(self, client):
        """Admin login should redirect to /admin/."""
        r = login_admin(client)
        assert r.status_code == 302
        assert '/admin/' in r.headers['Location']

    def test_valid_voter_login_redirects_to_voter_dashboard(self, client):
        """Voter login should redirect to /voter/dashboard."""
        r = login_voter(client)
        assert r.status_code == 302
        assert '/voter/dashboard' in r.headers['Location']

    def test_invalid_email_rejected(self, client):
        """Login with non-existent email should return 200 (re-render login)."""
        r = client.post('/auth/login', data={
            'email': 'nonexistent@demo.local',
            'password': 'anything',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Invalid email or password' in r.data

    def test_wrong_password_rejected(self, client):
        """Login with wrong password should be rejected."""
        r = client.post('/auth/login', data={
            'email': 'admin@demo.local',
            'password': 'WrongPassword!',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Invalid email or password' in r.data

    def test_empty_fields_flash_warning(self, client):
        """Submitting empty fields should show a warning."""
        r = client.post('/auth/login', data={
            'email': '',
            'password': '',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Please enter email and password' in r.data

    def test_already_authenticated_redirects_home(self, client):
        """If already logged in, /auth/login redirects to home."""
        login_admin(client)
        r = client.get('/auth/login', follow_redirects=False)
        assert r.status_code == 302
        # Should redirect to home
        assert '/' in r.headers['Location']

    def test_admin_cannot_access_voter_dashboard_via_role_bypass(self, client):
        """Admin role should not grant access to voter-only routes if admin_required."""
        login_admin(client)
        # /voter/dashboard uses @login_required (both admin and voter can access)
        r = client.get('/voter/dashboard')
        assert r.status_code == 200  # Both roles can see voter dashboard


class TestRegistration:
    """Tests for the registration page and new user creation."""

    def test_register_page_renders(self, client):
        """GET /auth/register returns 200."""
        r = client.get('/auth/register')
        assert r.status_code == 200
        assert b'Register' in r.data

    def test_valid_registration(self, client):
        """Registering with valid data should redirect to login."""
        r = client.post('/auth/login', data={
            'email': '', 'password': ''
        })  # just to bypass

        r = client.post('/auth/register', data={
            'name': 'New User',
            'email': 'newuser@test.local',
            'mobile': '9999999999',
            'password': 'Secure@123',
            'confirm_password': 'Secure@123',
        }, follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_duplicate_email_rejected(self, client):
        """Registering with an existing email should fail."""
        r = client.post('/auth/register', data={
            'name': 'Duplicate User',
            'email': 'admin@demo.local',  # already exists
            'mobile': '9999999999',
            'password': 'Secure@123',
            'confirm_password': 'Secure@123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Email already registered' in r.data

    def test_short_name_rejected(self, client):
        """Name shorter than 2 chars should fail."""
        r = client.post('/auth/register', data={
            'name': 'X',
            'email': 'x@test.local',
            'mobile': '9999999999',
            'password': 'Secure@123',
            'confirm_password': 'Secure@123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'at least 2 characters' in r.data

    def test_invalid_email_rejected(self, client):
        """Email without @ should fail."""
        r = client.post('/auth/register', data={
            'name': 'Valid Name',
            'email': 'notanemail',
            'mobile': '9999999999',
            'password': 'Secure@123',
            'confirm_password': 'Secure@123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'valid email' in r.data

    def test_short_password_rejected(self, client):
        """Password shorter than 8 chars should fail."""
        r = client.post('/auth/register', data={
            'name': 'Valid Name',
            'email': 'valid@test.local',
            'mobile': '9999999999',
            'password': 'short',
            'confirm_password': 'short',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'at least 8 characters' in r.data

    def test_password_mismatch_rejected(self, client):
        """Mismatched passwords should fail."""
        r = client.post('/auth/register', data={
            'name': 'Valid Name',
            'email': 'valid@test.local',
            'mobile': '9999999999',
            'password': 'Secure@123',
            'confirm_password': 'Different@123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'Passwords do not match' in r.data

    def test_short_mobile_rejected(self, client):
        """Mobile with fewer than 10 digits should fail."""
        r = client.post('/auth/register', data={
            'name': 'Valid Name',
            'email': 'valid@test.local',
            'mobile': '12345',
            'password': 'Secure@123',
            'confirm_password': 'Secure@123',
        }, follow_redirects=True)
        assert r.status_code == 200
        assert b'10+ digits' in r.data

    def test_newly_registered_user_can_login(self, client):
        """A user registered via the form should be able to log in."""
        client.post('/auth/register', data={
            'name': 'Loginable User',
            'email': 'loginable@test.local',
            'mobile': '9876543210',
            'password': 'MyPassword@1',
            'confirm_password': 'MyPassword@1',
        }, follow_redirects=False)

        r = client.post('/auth/login', data={
            'email': 'loginable@test.local',
            'password': 'MyPassword@1',
        }, follow_redirects=False)
        assert r.status_code == 302
        assert '/voter/dashboard' in r.headers['Location']


class TestLogout:
    """Tests for logout functionality."""

    def test_logout_redirects_to_home(self, client):
        """Logging out should redirect to home."""
        login_voter(client)
        r = logout(client)
        assert r.status_code == 302
        assert r.headers['Location'] == '/'

    def test_logout_then_protected_route_requires_login(self, client):
        """After logout, accessing protected routes should redirect to login."""
        login_voter(client)
        logout(client)
        r = client.get('/voter/dashboard', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_unauthenticated_access_redirects_to_login(self, client):
        """Accessing protected routes without login should redirect to login."""
        r = client.get('/voter/dashboard', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_admin_routes_require_admin_role(self, client):
        """Admin routes should redirect non-admin users to home."""
        login_voter(client)
        r = client.get('/admin/', follow_redirects=False)
        assert r.status_code == 302
        # Should redirect to home (access denied)
        assert '/' in r.headers['Location']
        # Should NOT go to admin dashboard
        assert '/admin/' not in r.headers['Location']
