"""
Property test for queue status consistency.

**Property 4: People-ahead count is always ≥ 0 and ≤ total waiting tokens for the counter**
**Validates: Requirements 5.1**
"""
import pytest
from hypothesis import given, settings, assume
from hypothesis import strategies as st

from app import create_app
from app.extensions import db as _db
from app.models import User, Branch, ServiceType, Token, Counter
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
    """Seed branch, counter, service type, and a user for tests."""
    with app.app_context():
        branch = Branch(name="Queue Branch", location="Test City")
        _db.session.add(branch)
        _db.session.flush()

        counter = Counter(name="Counter 1", branch_id=branch.id, status="Active")
        service = ServiceType(name="General", branch_id=branch.id)
        _db.session.add_all([counter, service])
        _db.session.flush()

        user = User(
            name="Queue Tester",
            email="queuetest@example.com",
            phone="0000000000",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        _db.session.add(user)
        _db.session.commit()

        return {
            "branch_id": branch.id,
            "counter_id": counter.id,
            "service_id": service.id,
            "user_id": user.id,
        }


def _clear_tokens(app, branch_id):
    """Remove all tokens for the branch to start fresh."""
    with app.app_context():
        Token.query.filter_by(branch_id=branch_id).delete()
        _db.session.commit()


def _create_tokens(app, branch_id, counter_id, service_id, user_id,
                   waiting=0, now_serving=0, served=0):
    """Insert tokens with given statuses directly into the DB."""
    with app.app_context():
        seq = 1
        for _ in range(waiting):
            t = Token(
                user_id=user_id,
                branch_id=branch_id,
                counter_id=counter_id,
                service_type_id=service_id,
                token_number=f"QBR-20990101-{seq:03d}",
                status="Waiting",
            )
            _db.session.add(t)
            seq += 1
        for _ in range(now_serving):
            t = Token(
                user_id=user_id,
                branch_id=branch_id,
                counter_id=counter_id,
                service_type_id=service_id,
                token_number=f"QBR-20990101-{seq:03d}",
                status="Now Serving",
            )
            _db.session.add(t)
            seq += 1
        for _ in range(served):
            t = Token(
                user_id=user_id,
                branch_id=branch_id,
                counter_id=counter_id,
                service_type_id=service_id,
                token_number=f"QBR-20990101-{seq:03d}",
                status="Served",
            )
            _db.session.add(t)
            seq += 1
        _db.session.commit()


# ── Unit tests ────────────────────────────────────────────────────────────────

class TestQueueStatusEndpoint:
    def test_missing_branch_id_returns_400(self, client):
        resp = client.get("/api/queue/status")
        assert resp.status_code == 400
        assert "error" in resp.get_json()

    def test_invalid_branch_returns_404(self, client):
        resp = client.get("/api/queue/status?branch_id=99999")
        assert resp.status_code == 404

    def test_empty_queue_returns_zero_counts(self, client, seed_data, app):
        _clear_tokens(app, seed_data["branch_id"])
        resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["current_token"] is None
        assert data["people_ahead"] == 0
        assert data["progress_percent"] == 0

    def test_now_serving_token_appears_in_current_token(self, client, seed_data, app):
        _clear_tokens(app, seed_data["branch_id"])
        _create_tokens(app, seed_data["branch_id"], seed_data["counter_id"],
                       seed_data["service_id"], seed_data["user_id"],
                       now_serving=1)
        resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["current_token"] is not None

    def test_people_ahead_equals_waiting_count(self, client, seed_data, app):
        _clear_tokens(app, seed_data["branch_id"])
        _create_tokens(app, seed_data["branch_id"], seed_data["counter_id"],
                       seed_data["service_id"], seed_data["user_id"],
                       waiting=3, now_serving=1)
        resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["people_ahead"] == 3

    def test_progress_percent_calculation(self, client, seed_data, app):
        _clear_tokens(app, seed_data["branch_id"])
        # 3 served out of 4 total (3 served + 1 waiting) → 75%
        _create_tokens(app, seed_data["branch_id"], seed_data["counter_id"],
                       seed_data["service_id"], seed_data["user_id"],
                       waiting=1, served=3)
        resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["progress_percent"] == 75

    def test_response_includes_all_required_fields(self, client, seed_data, app):
        _clear_tokens(app, seed_data["branch_id"])
        resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
        assert resp.status_code == 200
        data = resp.get_json()
        for field in ("current_token", "people_ahead", "total_today",
                      "served_today", "progress_percent", "branch_id", "counter_id"):
            assert field in data, f"Missing field: {field}"


# ── Property test ─────────────────────────────────────────────────────────────

@given(
    waiting=st.integers(min_value=0, max_value=10),
    now_serving=st.integers(min_value=0, max_value=1),
    served=st.integers(min_value=0, max_value=10),
)
@settings(max_examples=50, deadline=None)
def test_property_people_ahead_within_bounds(waiting, now_serving, served, app, client, seed_data):
    """
    Property 4: People-ahead count is always ≥ 0 and ≤ total waiting tokens for the counter.

    For any combination of token statuses, the people_ahead value returned by
    /api/queue/status must satisfy: 0 ≤ people_ahead ≤ total_waiting_tokens.
    **Validates: Requirements 5.1**
    """
    _clear_tokens(app, seed_data["branch_id"])
    _create_tokens(
        app,
        seed_data["branch_id"],
        seed_data["counter_id"],
        seed_data["service_id"],
        seed_data["user_id"],
        waiting=waiting,
        now_serving=now_serving,
        served=served,
    )

    resp = client.get(f"/api/queue/status?branch_id={seed_data['branch_id']}")
    assert resp.status_code == 200
    data = resp.get_json()

    people_ahead = data["people_ahead"]

    # Property: people_ahead is always non-negative
    assert people_ahead >= 0, (
        f"people_ahead={people_ahead} is negative (waiting={waiting})"
    )

    # Property: people_ahead never exceeds the number of waiting tokens
    assert people_ahead <= waiting, (
        f"people_ahead={people_ahead} exceeds waiting count={waiting}"
    )
