"""
Unit tests for queue management admin operations.

Tests:
- call-next transitions token statuses correctly
- skip moves token to end and advances queue
- close counter reassigns waiting tokens

Requirements: 10.2, 10.3, 10.4
"""
import pytest
from datetime import datetime
from app import create_app
from app.extensions import db as _db
from app.models import User, Branch, Counter, ServiceType, Token
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
    """Seed admin user, branch, two counters, service type, and tokens."""
    with app.app_context():
        admin = User(
            name="Admin",
            email="admin@example.com",
            phone="0000000000",
            password_hash=generate_password_hash("Password1"),
            role="admin"
        )
        branch = Branch(name="Main Branch", location="HQ")
        _db.session.add_all([admin, branch])
        _db.session.flush()

        counter1 = Counter(name="Counter 1", branch_id=branch.id, status="Active")
        counter2 = Counter(name="Counter 2", branch_id=branch.id, status="Active")
        _db.session.add_all([counter1, counter2])
        _db.session.flush()

        service = ServiceType(name="General", branch_id=branch.id)
        user = User(
            name="Alice",
            email="alice@example.com",
            phone="1111111111",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        _db.session.add_all([service, user])
        _db.session.flush()

        # Token being served at counter1
        t_serving = Token(
            user_id=user.id,
            counter_id=counter1.id,
            branch_id=branch.id,
            service_type_id=service.id,
            token_number="BR1-20250101-001",
            status="Now Serving",
            estimated_wait_minutes=0,
        )
        # Two waiting tokens at counter1
        t_wait1 = Token(
            user_id=user.id,
            counter_id=counter1.id,
            branch_id=branch.id,
            service_type_id=service.id,
            token_number="BR1-20250101-002",
            status="Waiting",
            estimated_wait_minutes=5,
            booked_at=datetime(2025, 1, 1, 10, 0, 0),
        )
        t_wait2 = Token(
            user_id=user.id,
            counter_id=counter1.id,
            branch_id=branch.id,
            service_type_id=service.id,
            token_number="BR1-20250101-003",
            status="Waiting",
            estimated_wait_minutes=10,
            booked_at=datetime(2025, 1, 1, 10, 5, 0),
        )
        _db.session.add_all([t_serving, t_wait1, t_wait2])
        _db.session.commit()

        return {
            "admin_id": admin.id,
            "user_id": user.id,
            "branch_id": branch.id,
            "counter1_id": counter1.id,
            "counter2_id": counter2.id,
            "service_id": service.id,
            "serving_id": t_serving.id,
            "wait1_id": t_wait1.id,
            "wait2_id": t_wait2.id,
        }


def login_admin(client):
    return client.post("/api/auth/login", json={
        "email": "admin@example.com",
        "password": "Password1"
    })


# ── Call Next ─────────────────────────────────────────────────────────────────

class TestCallNext:
    def test_call_next_marks_serving_as_served(self, client, seed, app):
        """Requirement 10.2: current Now Serving token becomes Served."""
        login_admin(client)
        resp = client.post("/api/admin/queue/call-next",
                           json={"counter_id": seed["counter1_id"]})
        assert resp.status_code == 200
        with app.app_context():
            token = Token.query.get(seed["serving_id"])
            assert token.status == "Served"

    def test_call_next_advances_first_waiting_to_now_serving(self, client, seed, app):
        """Requirement 10.2: next Waiting token (oldest) becomes Now Serving."""
        login_admin(client)
        client.post("/api/admin/queue/call-next",
                    json={"counter_id": seed["counter1_id"]})
        with app.app_context():
            token = Token.query.get(seed["wait1_id"])
            assert token.status == "Now Serving"

    def test_call_next_returns_correct_token_numbers(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/call-next",
                           json={"counter_id": seed["counter1_id"]})
        data = resp.get_json()
        assert data["served_token"] == "BR1-20250101-001"
        assert data["next_token"] == "BR1-20250101-002"

    def test_call_next_no_serving_token_returns_null_served(self, client, seed, app):
        """When no token is being served, served_token is null."""
        with app.app_context():
            Token.query.filter_by(id=seed["serving_id"]).update({"status": "Served"})
            _db.session.commit()
        login_admin(client)
        resp = client.post("/api/admin/queue/call-next",
                           json={"counter_id": seed["counter1_id"]})
        data = resp.get_json()
        assert data["served_token"] is None

    def test_call_next_empty_queue_returns_null_next(self, client, seed, app):
        """When no waiting tokens, next_token is null."""
        with app.app_context():
            Token.query.filter_by(counter_id=seed["counter1_id"],
                                  status="Waiting").update({"status": "Served"})
            _db.session.commit()
        login_admin(client)
        resp = client.post("/api/admin/queue/call-next",
                           json={"counter_id": seed["counter1_id"]})
        data = resp.get_json()
        assert data["next_token"] is None

    def test_call_next_missing_counter_id_returns_400(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/call-next", json={})
        assert resp.status_code == 400

    def test_call_next_requires_admin(self, client, seed):
        resp = client.post("/api/admin/queue/call-next",
                           json={"counter_id": seed["counter1_id"]})
        assert resp.status_code == 401


# ── Skip ──────────────────────────────────────────────────────────────────────

class TestSkip:
    def test_skip_marks_serving_as_skipped(self, client, seed, app):
        """Requirement 10.3: current Now Serving token becomes Skipped."""
        login_admin(client)
        client.post("/api/admin/queue/skip",
                    json={"counter_id": seed["counter1_id"]})
        with app.app_context():
            token = Token.query.get(seed["serving_id"])
            assert token.status == "Skipped"

    def test_skip_moves_token_to_end_of_queue(self, client, seed, app):
        """Requirement 10.3: skipped token's booked_at is updated to now (moves to end)."""
        with app.app_context():
            original_booked_at = Token.query.get(seed["serving_id"]).booked_at

        login_admin(client)
        client.post("/api/admin/queue/skip",
                    json={"counter_id": seed["counter1_id"]})

        with app.app_context():
            token = Token.query.get(seed["serving_id"])
            assert token.booked_at > original_booked_at

    def test_skip_advances_next_waiting_to_now_serving(self, client, seed, app):
        """Requirement 10.3: next Waiting token becomes Now Serving after skip."""
        login_admin(client)
        client.post("/api/admin/queue/skip",
                    json={"counter_id": seed["counter1_id"]})
        with app.app_context():
            token = Token.query.get(seed["wait1_id"])
            assert token.status == "Now Serving"

    def test_skip_returns_correct_token_numbers(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/skip",
                           json={"counter_id": seed["counter1_id"]})
        data = resp.get_json()
        assert data["skipped_token"] == "BR1-20250101-001"
        assert data["next_token"] == "BR1-20250101-002"

    def test_skip_missing_counter_id_returns_400(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/skip", json={})
        assert resp.status_code == 400


# ── Close Counter ─────────────────────────────────────────────────────────────

class TestCloseCounter:
    def test_close_counter_sets_status_inactive(self, client, seed, app):
        """Requirement 10.4: closing a counter sets its status to Inactive."""
        login_admin(client)
        resp = client.post(f"/api/admin/counters/{seed['counter1_id']}/close")
        assert resp.status_code == 200
        with app.app_context():
            counter = Counter.query.get(seed["counter1_id"])
            assert counter.status == "Inactive"

    def test_close_counter_reassigns_waiting_tokens(self, client, seed, app):
        """Requirement 10.4: waiting tokens are reassigned to another active counter."""
        login_admin(client)
        client.post(f"/api/admin/counters/{seed['counter1_id']}/close")
        with app.app_context():
            for token_id in [seed["wait1_id"], seed["wait2_id"]]:
                token = Token.query.get(token_id)
                assert token.counter_id == seed["counter2_id"]

    def test_close_counter_returns_reassigned_count(self, client, seed):
        login_admin(client)
        resp = client.post(f"/api/admin/counters/{seed['counter1_id']}/close")
        data = resp.get_json()
        assert data["reassigned"] == 2

    def test_close_counter_no_other_active_sets_counter_id_null(self, client, seed, app):
        """When no other active counter exists, counter_id is set to null."""
        with app.app_context():
            Counter.query.filter_by(id=seed["counter2_id"]).update({"status": "Inactive"})
            _db.session.commit()
        login_admin(client)
        client.post(f"/api/admin/counters/{seed['counter1_id']}/close")
        with app.app_context():
            for token_id in [seed["wait1_id"], seed["wait2_id"]]:
                token = Token.query.get(token_id)
                assert token.counter_id is None

    def test_open_counter_sets_status_active(self, client, seed, app):
        """Opening a counter sets its status to Active."""
        with app.app_context():
            Counter.query.filter_by(id=seed["counter1_id"]).update({"status": "Inactive"})
            _db.session.commit()
        login_admin(client)
        resp = client.post(f"/api/admin/counters/{seed['counter1_id']}/open")
        assert resp.status_code == 200
        with app.app_context():
            counter = Counter.query.get(seed["counter1_id"])
            assert counter.status == "Active"


# ── Delay ─────────────────────────────────────────────────────────────────────

class TestDelay:
    def test_delay_updates_estimated_wait_minutes(self, client, seed, app):
        login_admin(client)
        client.post("/api/admin/queue/delay",
                    json={"counter_id": seed["counter1_id"], "delay_minutes": 5})
        with app.app_context():
            t = Token.query.get(seed["wait1_id"])
            assert t.estimated_wait_minutes == 10  # was 5, +5

    def test_delay_returns_affected_count(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/delay",
                           json={"counter_id": seed["counter1_id"], "delay_minutes": 3})
        data = resp.get_json()
        assert data["affected_tokens"] == 2

    def test_delay_zero_minutes_returns_400(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/delay",
                           json={"counter_id": seed["counter1_id"], "delay_minutes": 0})
        assert resp.status_code == 400

    def test_delay_negative_minutes_returns_400(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/delay",
                           json={"counter_id": seed["counter1_id"], "delay_minutes": -5})
        assert resp.status_code == 400

    def test_delay_missing_counter_id_returns_400(self, client, seed):
        login_admin(client)
        resp = client.post("/api/admin/queue/delay",
                           json={"delay_minutes": 5})
        assert resp.status_code == 400
