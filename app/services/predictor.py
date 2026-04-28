"""
Wait_Time_Predictor and Crowd_Analyzer for hospital queues.
Uses past 30 days of appointment data to estimate wait times.
"""
from datetime import datetime, timedelta
from app.models import Token

# 10-minute interval slots from 09:00 to 17:00
AVAILABLE_SLOTS = [
    f"{h:02d}:{m:02d}"
    for h in range(9, 17)
    for m in range(0, 60, 10)
]


def estimate_wait_time(branch_id: int, service_type_id: int, slot: str) -> int:
    """
    Estimate wait time in minutes for a given slot.
    Uses 30-day historical average. Falls back to queue length * 10 min.
    """
    from app.extensions import db

    cutoff = datetime.utcnow() - timedelta(days=30)

    try:
        target_hour = int(slot.split(":")[0])
        target_min = int(slot.split(":")[1])
    except (ValueError, AttributeError, IndexError):
        target_hour, target_min = 9, 0

    tokens = (
        db.session.query(Token)
        .filter(
            Token.branch_id == branch_id,
            Token.service_type_id == service_type_id,
            Token.booked_at >= cutoff,
            Token.status.in_(["Served", "Now Serving", "Waiting"]),
        )
        .all()
    )

    if not tokens:
        waiting = (
            db.session.query(Token)
            .filter(
                Token.branch_id == branch_id,
                Token.service_type_id == service_type_id,
                Token.status == "Waiting",
            )
            .count()
        )
        return max(0, waiting * 10)

    # Group by slot hour
    hour_waits: dict[int, list[int]] = {}
    for t in tokens:
        if t.preferred_slot and t.estimated_wait_minutes is not None:
            try:
                h = int(t.preferred_slot.split(":")[0])
                hour_waits.setdefault(h, []).append(t.estimated_wait_minutes)
            except (ValueError, AttributeError):
                pass

    if target_hour in hour_waits:
        return max(0, int(sum(hour_waits[target_hour]) / len(hour_waits[target_hour])))

    waiting = (
        db.session.query(Token)
        .filter(
            Token.branch_id == branch_id,
            Token.service_type_id == service_type_id,
            Token.status == "Waiting",
        )
        .count()
    )
    return max(0, waiting * 10)


def get_best_slots(branch_id: int, service_type_id: int) -> list[dict]:
    """
    Return top 3 least-crowded slots using Crowd_Analyzer.
    """
    from app.extensions import db

    cutoff = datetime.utcnow() - timedelta(days=30)

    tokens = (
        db.session.query(Token)
        .filter(Token.branch_id == branch_id, Token.booked_at >= cutoff)
        .all()
    )

    slot_counts = {slot: 0 for slot in AVAILABLE_SLOTS}
    for t in tokens:
        if t.preferred_slot and t.preferred_slot in slot_counts:
            slot_counts[t.preferred_slot] += 1

    results = [
        {
            "slot": slot,
            "score": slot_counts[slot],
            "estimated_wait": estimate_wait_time(branch_id, service_type_id, slot),
        }
        for slot in AVAILABLE_SLOTS
    ]
    results.sort(key=lambda x: x["score"])
    return results[:3]
