"""
Property test for active token constraint.

**Property 3: A user can never have more than one token with status
`Waiting` or `Now Serving` per branch**
**Validates: Requirements 3.5**
"""
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app import create_app
from app.extensions import db as _db
from app.models import User, Branch, ServiceType, Token
from werkzeug.security import generate_password_hash


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def app():
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


@pytest.fixture(scope="module")
def client(app):
    return app.test_client()


@pytest.fixture(scope="module")
def seed_data(app):
    """Seed a user, branch, and service type for tests."""
    with app.app_context():
        user = User(
            name="Test User",
            email="tokentest@example.com",
            phone="1234567890",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        branch = Branch(name="Main Branch", location="City Center")
        _db.session.add_all([user, branch])
        _db.session.flush()

        service = ServiceType(name="General", branch_id=branch.id)
        _db.session.add(service)
        _db.session.commit()

        return {"user_id": user.id, "branch_id": branch.id, "service_id": service.id}


def _login(client, email="tokentest@example.com", password="Password1"):
    client.post("/api/auth/login", json={"email": email, "password": password})


def _book(client, branch_id, service_id, slot="09:00", date="2025-12-01"):
    return client.post("/api/tokens/book", json={
        "branch_id": branch_id,
        "service_type_id": service_id,
        "preferred_slot": slot,
        "date": date
    })


def _cancel_all_active(app, user_id, branch_id):
    """Helper: cancel all active tokens for a user at a branch."""
    with app.app_context():
        tokens = Token.query.filter(
            Token.user_id == user_id,
            Token.branch_id == branch_id,
            Token.status.in_(["Waiting", "Now Serving"])
        ).all()
        for t in tokens:
            t.status = "Cancelled"
        _db.session.commit()


# ── Unit tests for the constraint ─────────────────────────────────────────────

class TestActiveTokenConstraint:
    def test_first_booking_succeeds(self, client, seed_data, app):
        """A user with no active token can book successfully."""
        _cancel_all_active(app, seed_data["user_id"], seed_data["branch_id"])
        _login(client)
        resp = _book(client, seed_data["branch_id"], seed_data["service_id"])
        assert resp.status_code == 201

    def test_second_booking_same_branch_returns_409(self, client, seed_data, app):
        """A user with an active token at a branch cannot book another at the same branch."""
        _cancel_all_active(app, seed_data["user_id"], seed_data["branch_id"])
        _login(client)
        # First booking
        resp1 = _book(client, seed_data["branch_id"], seed_data["service_id"])
        assert resp1.status_code == 201
        # Second booking at same branch
        resp2 = _book(client, seed_data["branch_id"], seed_data["service_id"])
        assert resp2.status_code == 409
        data = resp2.get_json()
        assert "error" in data

    def test_cancel_allows_rebooking(self, client, seed_data, app):
        """After cancelling, the user can book again at the same branch."""
        _cancel_all_active(app, seed_data["user_id"], seed_data["branch_id"])
        _login(client)
        resp1 = _book(client, seed_data["branch_id"], seed_data["service_id"])
        assert resp1.status_code == 201
        token_id = resp1.get_json()["token_id"]

        # Cancel the token
        cancel_resp = client.post(f"/api/tokens/{token_id}/cancel")
        assert cancel_resp.status_code == 200

        # Now can book again
        resp2 = _book(client, seed_data["branch_id"], seed_data["service_id"])
        assert resp2.status_code == 201


# ── Property test ─────────────────────────────────────────────────────────────

@given(
    attempts=st.integers(min_value=2, max_value=5)
)
@settings(max_examples=20, deadline=None)
def test_property_at_most_one_active_token_per_branch(attempts, app, client, seed_data):
    """
    Property 3: A user can never have more than one token with status
    `Waiting` or `Now Serving` per branch.

    For any number of booking attempts, the count of active tokens
    for a user at a branch is always ≤ 1.
    """
    _cancel_all_active(app, seed_data["user_id"], seed_data["branch_id"])
    _login(client)

    success_count = 0
    for _ in range(attempts):
        resp = _book(client, seed_data["branch_id"], seed_data["service_id"])
        if resp.status_code == 201:
            success_count += 1

    # Verify at most one active token exists in the DB
    with app.app_context():
        active_count = Token.query.filter(
            Token.user_id == seed_data["user_id"],
            Token.branch_id == seed_data["branch_id"],
            Token.status.in_(["Waiting", "Now Serving"])
        ).count()

    assert active_count <= 1, (
        f"User has {active_count} active tokens at branch {seed_data['branch_id']}, "
        f"expected at most 1"
    )
    assert success_count <= 1, (
        f"Expected at most 1 successful booking, got {success_count}"
    )
