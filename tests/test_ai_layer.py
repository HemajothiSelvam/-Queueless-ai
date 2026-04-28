"""
Tests for the AI layer: Wait_Time_Predictor, Crowd_Analyzer, and RAG_Engine.

Property 5: Estimated wait time is always a non-negative integer
**Validates: Requirements 6.1, 6.2**

Property 6: The top 3 recommended slots are always ordered by ascending crowd score
**Validates: Requirements 6.3**

Unit test: RAG_Engine summary is non-empty for valid branch/service with historical data
**Validates: Requirements 6.5**
"""
import pytest
from datetime import datetime, timedelta

from hypothesis import given, settings
from hypothesis import strategies as st

from app import create_app
from app.extensions import db as _db
from app.models import User, Branch, ServiceType, Token
from werkzeug.security import generate_password_hash


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
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


@pytest.fixture(scope="module")
def seeded(app):
    """Seed branch, service type, user, and 30 days of historical tokens."""
    with app.app_context():
        branch = Branch(name="Central Branch", location="City Center")
        service = ServiceType.__new__(ServiceType)
        _db.session.add(branch)
        _db.session.flush()

        service = ServiceType(name="General Inquiry", branch_id=branch.id)
        _db.session.add(service)
        _db.session.flush()

        user = User(
            name="Test User",
            email="testuser@example.com",
            phone="1234567890",
            password_hash=generate_password_hash("Password1"),
            role="user"
        )
        _db.session.add(user)
        _db.session.flush()

        # Create 30 days of historical tokens across various slots
        slots = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]
        now = datetime.utcnow()
        for day_offset in range(30):
            for i, slot in enumerate(slots):
                booked_at = now - timedelta(days=day_offset + 1, hours=i)
                token = Token(
                    user_id=user.id,
                    branch_id=branch.id,
                    service_type_id=service.id,
                    token_number=f"CTR-{(day_offset * 8 + i):05d}-001",
                    status="Served",
                    preferred_slot=slot,
                    booked_at=booked_at,
                    estimated_wait_minutes=(i + 1) * 3  # 3, 6, 9, ... 24
                )
                _db.session.add(token)

        _db.session.commit()
        return {"branch_id": branch.id, "service_id": service.id, "user_id": user.id}


# ── Property 5: wait time is always a non-negative integer ────────────────────

VALID_SLOTS = ["09:00", "10:00", "11:00", "12:00", "13:00", "14:00", "15:00", "16:00"]

slot_st = st.sampled_from(VALID_SLOTS)
branch_id_st = st.integers(min_value=1, max_value=100)
service_id_st = st.integers(min_value=1, max_value=100)


@given(branch_id=branch_id_st, service_id=service_id_st, slot=slot_st)
@settings(max_examples=200)
def test_estimate_wait_time_always_non_negative_integer(branch_id, service_id, slot):
    """
    Property 5: Estimated wait time is always a non-negative integer.
    **Validates: Requirements 6.1, 6.2**
    """
    from app import create_app
    from config import Config

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SECRET_KEY = "test-secret-key"

    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        from app.services.predictor import estimate_wait_time
        result = estimate_wait_time(branch_id, service_id, slot)
        assert isinstance(result, int), f"Expected int, got {type(result)}: {result}"
        assert result >= 0, f"Expected non-negative, got {result}"


# ── Property 6: best slots ordered by ascending crowd score ───────────────────

@given(branch_id=branch_id_st, service_id=service_id_st)
@settings(max_examples=100)
def test_best_slots_ordered_by_ascending_crowd_score(branch_id, service_id):
    """
    Property 6: The top 3 recommended slots are always ordered by ascending crowd score.
    **Validates: Requirements 6.3**
    """
    from app import create_app
    from config import Config

    class TestConfig(Config):
        TESTING = True
        SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
        SECRET_KEY = "test-secret-key"

    application = create_app(TestConfig)
    with application.app_context():
        _db.create_all()
        from app.services.predictor import get_best_slots
        slots = get_best_slots(branch_id, service_id)

        assert isinstance(slots, list), "get_best_slots must return a list"
        assert len(slots) == 3, f"Expected 3 slots, got {len(slots)}"

        for item in slots:
            assert "slot" in item
            assert "score" in item
            assert "estimated_wait" in item
            assert isinstance(item["score"], int)
            assert item["score"] >= 0

        scores = [s["score"] for s in slots]
        assert scores == sorted(scores), (
            f"Slots not ordered by ascending crowd score: {scores}"
        )


# ── Unit test: RAG_Engine summary ─────────────────────────────────────────────

class TestRAGEngine:
    def test_summary_non_empty_with_historical_data(self, app, seeded):
        """
        RAG_Engine returns a non-empty string when historical data exists.
        **Validates: Requirements 6.5**
        """
        with app.app_context():
            from app.services.rag_engine import get_insights
            summary = get_insights(seeded["branch_id"], seeded["service_id"])
            assert isinstance(summary, str)
            assert len(summary) > 0
            assert summary != "No historical data available for this branch and service yet."

    def test_summary_contains_branch_name(self, app, seeded):
        """Summary mentions the branch name."""
        with app.app_context():
            from app.services.rag_engine import get_insights
            summary = get_insights(seeded["branch_id"], seeded["service_id"])
            assert "Central Branch" in summary

    def test_summary_contains_service_name(self, app, seeded):
        """Summary mentions the service name."""
        with app.app_context():
            from app.services.rag_engine import get_insights
            summary = get_insights(seeded["branch_id"], seeded["service_id"])
            assert "General Inquiry" in summary

    def test_summary_no_data_returns_fallback(self, app):
        """Returns fallback message when no data exists."""
        with app.app_context():
            from app.services.rag_engine import get_insights
            summary = get_insights(99999, 99999)
            assert summary == "No historical data available for this branch and service yet."

    def test_summary_contains_recommendation(self, app, seeded):
        """Summary includes a slot recommendation."""
        with app.app_context():
            from app.services.rag_engine import get_insights
            summary = get_insights(seeded["branch_id"], seeded["service_id"])
            assert "recommend" in summary.lower()
