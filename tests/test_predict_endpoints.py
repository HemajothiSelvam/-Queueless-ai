"""
Integration tests for prediction and RAG endpoints.
"""
import pytest
from datetime import datetime, timedelta
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
    """Seed branch, service, user, and historical tokens."""
    with app.app_context():
        branch = Branch(name="Main Branch", location="Downtown")
        _db.session.add(branch)
        _db.session.flush()

        service = ServiceType(name="Customer Service", branch_id=branch.id)
        _db.session.add(service)
        _db.session.flush()

        user = User(
            name="Test User",
            email="test@example.com",
            phone="1234567890",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        _db.session.add(user)
        _db.session.flush()

        # Add historical tokens
        slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        now = datetime.utcnow()
        for day in range(30):
            for i, slot in enumerate(slots):
                token = Token(
                    user_id=user.id,
                    branch_id=branch.id,
                    service_type_id=service.id,
                    token_number=f"MAI-{day:02d}{i:02d}-001",
                    status="Served",
                    preferred_slot=slot,
                    booked_at=now - timedelta(days=day + 1),
                    estimated_wait_minutes=(i + 1) * 5
                )
                _db.session.add(token)

        _db.session.commit()
        return {"branch_id": branch.id, "service_id": service.id}


class TestWaitTimeEndpoint:
    def test_wait_time_returns_200(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}&slot=10:00"
        )
        assert resp.status_code == 200

    def test_wait_time_returns_estimated_minutes(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}&slot=10:00"
        )
        data = resp.get_json()
        assert "estimated_wait_minutes" in data
        assert isinstance(data["estimated_wait_minutes"], int)
        assert data["estimated_wait_minutes"] >= 0

    def test_wait_time_missing_branch_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?service_type_id={seed['service_id']}&slot=10:00"
        )
        assert resp.status_code == 400

    def test_wait_time_missing_service_type_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?branch_id={seed['branch_id']}&slot=10:00"
        )
        assert resp.status_code == 400

    def test_wait_time_missing_slot_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        assert resp.status_code == 400

    def test_wait_time_invalid_branch_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/wait-time?branch_id=invalid"
            f"&service_type_id={seed['service_id']}&slot=10:00"
        )
        assert resp.status_code == 400


class TestBestSlotsEndpoint:
    def test_best_slots_returns_200(self, client, seed):
        resp = client.get(
            f"/api/predict/best-slots?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        assert resp.status_code == 200

    def test_best_slots_returns_three_slots(self, client, seed):
        resp = client.get(
            f"/api/predict/best-slots?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        data = resp.get_json()
        assert "slots" in data
        assert len(data["slots"]) == 3

    def test_best_slots_each_has_required_fields(self, client, seed):
        resp = client.get(
            f"/api/predict/best-slots?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        data = resp.get_json()
        for slot in data["slots"]:
            assert "slot" in slot
            assert "score" in slot
            assert "estimated_wait" in slot

    def test_best_slots_missing_branch_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/best-slots?service_type_id={seed['service_id']}"
        )
        assert resp.status_code == 400

    def test_best_slots_missing_service_type_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/predict/best-slots?branch_id={seed['branch_id']}"
        )
        assert resp.status_code == 400


class TestRAGInsightsEndpoint:
    def test_insights_returns_200(self, client, seed):
        resp = client.get(
            f"/api/rag/insights?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        assert resp.status_code == 200

    def test_insights_returns_summary(self, client, seed):
        resp = client.get(
            f"/api/rag/insights?branch_id={seed['branch_id']}"
            f"&service_type_id={seed['service_id']}"
        )
        data = resp.get_json()
        assert "summary" in data
        assert isinstance(data["summary"], str)
        assert len(data["summary"]) > 0

    def test_insights_missing_branch_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/rag/insights?service_type_id={seed['service_id']}"
        )
        assert resp.status_code == 400

    def test_insights_missing_service_type_id_returns_400(self, client, seed):
        resp = client.get(
            f"/api/rag/insights?branch_id={seed['branch_id']}"
        )
        assert resp.status_code == 400

    def test_insights_nonexistent_branch_returns_fallback(self, client):
        resp = client.get(
            "/api/rag/insights?branch_id=99999&service_type_id=99999"
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert "No historical data available" in data["summary"]
