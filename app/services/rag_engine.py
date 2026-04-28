"""
RAG Engine — Retrieval-Augmented Generation for hospital queue insights.

RAG Pipeline:
1. RETRIEVE: Query SQLite for historical patient/token data (past 30 days)
2. AUGMENT: Compute statistics (avg wait, peak hour, best slot, crowd scores)
3. GENERATE: Use MCP client to call GPT-4o with the retrieved context

This demonstrates the full RAG pattern:
- The "retrieval" is from our own database (not a vector store, but same concept)
- The "augmentation" enriches the raw data with computed insights
- The "generation" uses an LLM via MCP to produce natural language
"""
import logging
from datetime import datetime, timedelta
from app.models import Token, Branch, ServiceType
from app.services.mcp_client import mcp_client
from app.services.predictor import AVAILABLE_SLOTS

logger = logging.getLogger(__name__)


def get_insights(branch_id: int, service_type_id: int) -> str:
    """
    Full RAG pipeline for hospital queue insights.

    Returns a natural-language string describing queue patterns
    and recommendations for the given hospital department.
    """
    from app.extensions import db

    # ── STEP 1: RETRIEVE ──────────────────────────────────────
    # Fetch historical data from our database (the "knowledge base")
    cutoff = datetime.utcnow() - timedelta(days=30)

    branch = db.session.get(Branch, branch_id)
    service = db.session.get(ServiceType, service_type_id)

    if not branch or not service:
        return "No data available for this hospital department."

    tokens = (
        db.session.query(Token)
        .filter(
            Token.branch_id == branch_id,
            Token.service_type_id == service_type_id,
            Token.booked_at >= cutoff,
        )
        .all()
    )

    if not tokens:
        return f"No historical data available for {service.name} at {branch.name} yet. Be the first to book!"

    # ── STEP 2: AUGMENT ───────────────────────────────────────
    # Compute statistics from retrieved data
    total_tokens = len(tokens)

    wait_times = [t.estimated_wait_minutes for t in tokens if t.estimated_wait_minutes is not None]
    avg_wait = int(sum(wait_times) / len(wait_times)) if wait_times else 0

    # Find peak hour
    hour_counts: dict[int, int] = {}
    for t in tokens:
        if t.preferred_slot:
            try:
                hour = int(t.preferred_slot.split(":")[0])
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
            except (ValueError, AttributeError):
                pass

    peak_hour = f"{max(hour_counts, key=hour_counts.get):02d}:00" if hour_counts else "10:00"

    # Find best (least crowded) slot
    slot_counts = {slot: 0 for slot in AVAILABLE_SLOTS}
    for t in tokens:
        if t.preferred_slot and t.preferred_slot in slot_counts:
            slot_counts[t.preferred_slot] += 1
    best_slot = min(slot_counts, key=slot_counts.get)

    logger.info(f"RAG: Retrieved {total_tokens} tokens for {branch.name}/{service.name}")
    logger.info(f"RAG: Computed avg_wait={avg_wait}, peak={peak_hour}, best_slot={best_slot}")

    # ── STEP 3: GENERATE via MCP ──────────────────────────────
    # Pass retrieved + augmented context to LLM via MCP tool call
    mcp_result = mcp_client.call_tool("queue_insights", {
        "hospital_name": branch.name,
        "department": service.name,
        "avg_wait_minutes": avg_wait,
        "peak_hour": peak_hour,
        "best_slot": best_slot,
        "total_patients_30d": total_tokens
    })

    if mcp_result.get("success"):
        return mcp_result["result"]

    return f"Queue insights unavailable. Average wait for {service.name}: {avg_wait} minutes."
