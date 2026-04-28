from datetime import date
from flask import Blueprint, request, jsonify
from app.models import Token, Branch

queue_bp = Blueprint("queue", __name__)


@queue_bp.route("/api/queue/status", methods=["GET"])
def queue_status():
    """Return live queue status for a branch (and optionally a counter)."""
    branch_id = request.args.get("branch_id", type=int)
    counter_id = request.args.get("counter_id", type=int)

    if not branch_id:
        return jsonify({"error": "branch_id is required"}), 400

    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    today = date.today()

    # Base query filters
    def base_filter(query):
        query = query.filter(Token.branch_id == branch_id)
        if counter_id:
            query = query.filter(Token.counter_id == counter_id)
        return query

    # Current token being served
    now_serving_q = base_filter(
        Token.query.filter(Token.status == "Now Serving")
    ).first()

    current_token = now_serving_q.token_number if now_serving_q else None

    # People ahead = waiting tokens
    people_ahead = base_filter(
        Token.query.filter(Token.status == "Waiting")
    ).count()

    # Total today = Waiting + Now Serving + Served
    total_today = base_filter(
        Token.query.filter(
            Token.status.in_(["Waiting", "Now Serving", "Served"]),
            Token.booked_at >= today
        )
    ).count()

    # Served today
    served_today = base_filter(
        Token.query.filter(
            Token.status == "Served",
            Token.booked_at >= today
        )
    ).count()

    progress_percent = round(served_today / total_today * 100) if total_today > 0 else 0

    return jsonify({
        "current_token": current_token,
        "people_ahead": people_ahead,
        "total_today": total_today,
        "served_today": served_today,
        "progress_percent": progress_percent,
        "branch_id": branch_id,
        "counter_id": counter_id
    }), 200
