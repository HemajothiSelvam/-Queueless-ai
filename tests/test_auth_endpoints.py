"""
Unit tests for auth endpoints.

Tests:
- Duplicate email returns 409
- Invalid credentials return no session
- Logout invalidates session

Requirements: 1.3, 1.5, 1.6
"""
import pytest
from app import create_app
from app.extensions import db as _db


@pytest.fixture
def app():
    """Create a test Flask app with an in-memory SQLite database."""
    from config import Config

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SECRET_KEY = "test-secret-key"
        WTF_CSRF_ENABLED = False

    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


# ── Helpers ───────────────────────────────────────────────────────────────────

def register_user(client, name="Test User", email="test@example.com",
                  phone="1234567890", password="Password1"):
    return client.post("/api/auth/register", json={
        "name": name,
        "email": email,
        "phone": phone,
        "password": password,
    })


def login_user(client, email="test@example.com", password="Password1"):
    return client.post("/api/auth/login", json={
        "email": email,
        "password": password,
    })


# ── Registration tests ────────────────────────────────────────────────────────

class TestRegistration:
    def test_successful_registration_returns_201(self, client):
        resp = register_user(client)
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["user"]["email"] == "test@example.com"
        assert data["user"]["role"] == "user"

    def test_duplicate_email_returns_409(self, client):
        """Requirement 1.3: duplicate email must return 409."""
        register_user(client)
        resp = register_user(client)  # same email again
        assert resp.status_code == 409
        data = resp.get_json()
        assert "error" in data

    def test_missing_name_returns_400(self, client):
        resp = client.post("/api/auth/register", json={
            "email": "a@b.com", "phone": "123", "password": "Password1"
        })
        assert resp.status_code == 400

    def test_missing_email_returns_400(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Alice", "phone": "123", "password": "Password1"
        })
        assert resp.status_code == 400

    def test_invalid_email_format_returns_400(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Alice", "email": "not-an-email",
            "phone": "123", "password": "Password1"
        })
        assert resp.status_code == 400

    def test_short_password_returns_400(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Alice", "email": "a@b.com",
            "phone": "123", "password": "abc"
        })
        assert resp.status_code == 400

    def test_password_without_digit_returns_400(self, client):
        resp = client.post("/api/auth/register", json={
            "name": "Alice", "email": "a@b.com",
            "phone": "123", "password": "NoDigitHere"
        })
        assert resp.status_code == 400


# ── Login tests ───────────────────────────────────────────────────────────────

class TestLogin:
    def test_valid_credentials_return_200(self, client):
        register_user(client)
        resp = login_user(client)
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["email"] == "test@example.com"

    def test_wrong_password_returns_401(self, client):
        """Requirement 1.5: invalid credentials must not grant access."""
        register_user(client)
        resp = login_user(client, password="WrongPass9")
        assert resp.status_code == 401
        data = resp.get_json()
        assert "error" in data

    def test_unknown_email_returns_401(self, client):
        """Requirement 1.5: unknown email must not grant access."""
        resp = login_user(client, email="nobody@example.com")
        assert resp.status_code == 401

    def test_missing_email_returns_400(self, client):
        resp = client.post("/api/auth/login", json={"password": "Password1"})
        assert resp.status_code == 400

    def test_missing_password_returns_400(self, client):
        resp = client.post("/api/auth/login", json={"email": "a@b.com"})
        assert resp.status_code == 400


# ── Logout tests ──────────────────────────────────────────────────────────────

class TestLogout:
    def test_logout_returns_200(self, client):
        register_user(client)
        login_user(client)
        resp = client.post("/api/auth/logout")
        assert resp.status_code == 200

    def test_logout_invalidates_session(self, client):
        """Requirement 1.6: after logout, /api/auth/me must return 401."""
        register_user(client)
        login_user(client)

        # Confirm we are authenticated
        me_resp = client.get("/api/auth/me")
        assert me_resp.status_code == 200

        # Logout
        client.post("/api/auth/logout")

        # Session should now be invalid
        me_resp_after = client.get("/api/auth/me")
        assert me_resp_after.status_code == 401

    def test_me_returns_401_when_not_authenticated(self, client):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401


# ── Role-based access tests ───────────────────────────────────────────────────

class TestRoleAccess:
    def test_me_returns_user_info_when_authenticated(self, client):
        register_user(client)
        login_user(client)
        resp = client.get("/api/auth/me")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["user"]["role"] == "user"
        assert data["user"]["email"] == "test@example.com"
