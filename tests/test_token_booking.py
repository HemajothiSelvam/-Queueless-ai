"""
Unit tests for token booking endpoints.

Tests:
- Missing fields return 400
- Successful booking returns token number and estimated wait time
- Cancel updates status and timestamp

Requirements: 3.2, 3.3, 3.4
"""
import pytest
from app import create_app
from app.extensions import db as _db
from app.models import User, Branch, ServiceType, Token
from werkzeug.security import generate_password_hash


@pytest.fixture
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


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def seed(app):
    """Seed a user, branch, and service type."""
    with app.app_context():
        user = User(
            name="Alice",
            email="alice@example.com",
            phone="0000000000",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        branch = Branch(name="Downtown", location="Main St")
        _db.session.add_all([user, branch])
        _db.session.flush()

        service = ServiceType(name="Billing", branch_id=branch.id)
        _db.session.add(service)
        _db.session.commit()

        return {"user_id": user.id, "branch_id": branch.id, "service_id": service.id}


def login(client):
    return client.post("/api/auth/login", json={
        "email": "alice@example.com",
        "password": "Password1"
    })


def book(client, branch_id, service_id, slot="10:00", date="2025-12-15"):
    return client.post("/api/tokens/book", json={
        "branch_id": branch_id,
        "service_type_id": service_id,
        "preferred_slot": slot,
        "date": date
    })


# ── Missing fields ─────────────────────────────────────────────────────────────

class TestBookingValidation:
    def test_missing_branch_id_returns_400(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/book", json={
            "service_type_id": seed["service_id"],
            "preferred_slot": "10:00",
            "date": "2025-12-15"
        })
        assert resp.status_code == 400

    def test_missing_service_type_id_returns_400(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/book", json={
            "branch_id": seed["branch_id"],
            "preferred_slot": "10:00",
            "date": "2025-12-15"
        })
        assert resp.status_code == 400

    def test_missing_slot_returns_400(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/book", json={
            "branch_id": seed["branch_id"],
            "service_type_id": seed["service_id"],
            "date": "2025-12-15"
        })
        assert resp.status_code == 400

    def test_missing_date_returns_400(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/book", json={
            "branch_id": seed["branch_id"],
            "service_type_id": seed["service_id"],
            "preferred_slot": "10:00"
        })
        assert resp.status_code == 400

    def test_empty_body_returns_400(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/book", json={})
        assert resp.status_code == 400

    def test_unauthenticated_returns_401(self, client, seed):
        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 401


# ── Successful booking ─────────────────────────────────────────────────────────

class TestSuccessfulBooking:
    def test_booking_returns_201_with_token_number(self, client, seed):
        """Requirement 3.2: booking returns a token number."""
        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 201
        data = resp.get_json()
        assert "token_number" in data
        assert data["token_number"]  # non-empty

    def test_booking_returns_estimated_wait_minutes(self, client, seed):
        """Requirement 3.3: booking returns estimated wait time."""
        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 201
        data = resp.get_json()
        assert "estimated_wait_minutes" in data
        assert isinstance(data["estimated_wait_minutes"], int)
        assert data["estimated_wait_minutes"] >= 0

    def test_booking_returns_token_id(self, client, seed):
        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 201
        data = resp.get_json()
        assert "token_id" in data
        assert isinstance(data["token_id"], int)

    def test_token_number_format(self, client, seed, app):
        """Token number follows {BRANCH_CODE}-{YYYYMMDD}-{SEQ:03d} format."""
        import re
        login(client)
        # Cancel any existing active tokens first
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 201
        token_number = resp.get_json()["token_number"]
        pattern = re.compile(r"^[A-Z]{3}-\d{8}-\d{3}$")
        assert pattern.match(token_number), f"Token number '{token_number}' has unexpected format"

    def test_first_booking_has_zero_wait_when_no_queue(self, client, seed, app):
        """When no one is waiting, estimated wait is 0."""
        with app.app_context():
            Token.query.filter(
                Token.branch_id == seed["branch_id"],
                Token.status == "Waiting"
            ).update({"status": "Served"})
            _db.session.commit()

        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["estimated_wait_minutes"] == 0


# ── Cancel token ───────────────────────────────────────────────────────────────

class TestCancelToken:
    def test_cancel_returns_200(self, client, seed, app):
        """Requirement 3.4: cancel returns 200."""
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        token_id = resp.get_json()["token_id"]

        cancel_resp = client.post(f"/api/tokens/{token_id}/cancel")
        assert cancel_resp.status_code == 200

    def test_cancel_updates_status_to_cancelled(self, client, seed, app):
        """Requirement 3.4: cancel sets status to Cancelled."""
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        token_id = resp.get_json()["token_id"]

        client.post(f"/api/tokens/{token_id}/cancel")

        with app.app_context():
            token = Token.query.get(token_id)
            assert token.status == "Cancelled"

    def test_cancel_updates_status_updated_at(self, client, seed, app):
        """status_updated_at is updated when token is cancelled."""
        from datetime import datetime, timezone
        import time

        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        token_id = resp.get_json()["token_id"]

        with app.app_context():
            token_before = Token.query.get(token_id)
            original_updated_at = token_before.status_updated_at

        time.sleep(0.05)  # small delay to ensure timestamp changes
        client.post(f"/api/tokens/{token_id}/cancel")

        with app.app_context():
            token_after = Token.query.get(token_id)
            assert token_after.status_updated_at >= original_updated_at

    def test_cancel_other_users_token_returns_403(self, client, seed, app):
        """Cannot cancel another user's token."""
        # Create a second user
        with app.app_context():
            other = User(
                name="Bob",
                email="bob@example.com",
                phone="9999999999",
                password_hash=generate_password_hash("Password1"),
                role="user"
            )
            _db.session.add(other)
            _db.session.commit()
            other_id = other.id

        # Book as alice
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        resp = book(client, seed["branch_id"], seed["service_id"])
        token_id = resp.get_json()["token_id"]

        # Login as bob and try to cancel alice's token
        client.post("/api/auth/logout")
        client.post("/api/auth/login", json={"email": "bob@example.com", "password": "Password1"})
        cancel_resp = client.post(f"/api/tokens/{token_id}/cancel")
        assert cancel_resp.status_code == 403

    def test_cancel_nonexistent_token_returns_404(self, client, seed):
        login(client)
        resp = client.post("/api/tokens/99999/cancel")
        assert resp.status_code == 404


# ── Active token ───────────────────────────────────────────────────────────────

class TestActiveToken:
    def test_active_token_returns_token_info(self, client, seed, app):
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        book(client, seed["branch_id"], seed["service_id"])

        resp = client.get("/api/tokens/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["token"] is not None
        assert "token_number" in data["token"]
        assert "branch_name" in data["token"]
        assert "service_type_name" in data["token"]

    def test_no_active_token_returns_null(self, client, seed, app):
        with app.app_context():
            Token.query.filter(
                Token.user_id == seed["user_id"],
                Token.status.in_(["Waiting", "Now Serving"])
            ).update({"status": "Cancelled"})
            _db.session.commit()

        login(client)
        resp = client.get("/api/tokens/active")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["token"] is None


# ── History ────────────────────────────────────────────────────────────────────

class TestTokenHistory:
    def test_history_returns_paginated_results(self, client, seed):
        login(client)
        resp = client.get("/api/tokens/history")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "tokens" in data
        assert "total" in data
        assert "page" in data
        assert "pages" in data

    def test_history_default_page_is_1(self, client, seed):
        login(client)
        resp = client.get("/api/tokens/history")
        data = resp.get_json()
        assert data["page"] == 1

    def test_history_unauthenticated_returns_401(self, client):
        client.post("/api/auth/logout")
        resp = client.get("/api/tokens/history")
        assert resp.status_code == 401
