from datetime import datetime, date
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Token, Branch, ServiceType, Counter

tokens_bp = Blueprint("tokens", __name__)


def _generate_token_number(branch, today_str):
    """Generate token number as {BRANCH_CODE}-{YYYYMMDD}-{SEQ:03d}."""
    branch_code = branch.name[:3].upper()
    count = Token.query.filter(
        Token.branch_id == branch.id,
        Token.token_number.like(f"{branch_code}-{today_str}-%")
    ).count()
    return f"{branch_code}-{today_str}-{count + 1:03d}"


@tokens_bp.route("/api/tokens/book", methods=["POST"])
@login_required
def book_token():
    """Book a new queue token."""
    data = request.get_json()
    if not data:
        return jsonify({"error": "Request body is required"}), 400

    branch_id = data.get("branch_id")
    service_type_id = data.get("service_type_id")
    preferred_slot = data.get("preferred_slot")
    booking_date = data.get("date")

    if not all([branch_id, service_type_id, preferred_slot, booking_date]):
        return jsonify({"error": "All fields are required: branch_id, service_type_id, preferred_slot, date"}), 400

    # Check branch exists
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "Branch not found"}), 404

    # Check service type exists
    service_type = ServiceType.query.get(service_type_id)
    if not service_type:
        return jsonify({"error": "Service type not found"}), 404

    # Check user doesn't already have an active token at this branch
    existing = Token.query.filter(
        Token.user_id == current_user.id,
        Token.branch_id == branch_id,
        Token.status.in_(["Waiting", "Now Serving"])
    ).first()
    if existing:
        return jsonify({"error": "You already have an active token at this branch"}), 409

    today_str = date.today().strftime("%Y%m%d")

    # Count waiting tokens for estimated wait
    waiting_count = Token.query.filter(
        Token.branch_id == branch_id,
        Token.status == "Waiting"
    ).count()

    # Generate token number (retry once on collision)
    token_number = _generate_token_number(branch, today_str)
    token = Token(
        user_id=current_user.id,
        branch_id=branch_id,
        service_type_id=service_type_id,
        token_number=token_number,
        status="Waiting",
        preferred_slot=preferred_slot,
        estimated_wait_minutes=waiting_count * 8
    )
    db.session.add(token)
    try:
        db.session.commit()
    except Exception:
        db.session.rollback()
        # Retry once with incremented sequence
        token_number = _generate_token_number(branch, today_str)
        token.token_number = token_number
        db.session.add(token)
        db.session.commit()

    return jsonify({
        "token_number": token.token_number,
        "estimated_wait_minutes": token.estimated_wait_minutes,
        "token_id": token.id
    }), 201


@tokens_bp.route("/api/tokens/active", methods=["GET"])
@login_required
def get_active_token():
    """Get the current user's active token."""
    token = Token.query.filter(
        Token.user_id == current_user.id,
        Token.status.in_(["Waiting", "Now Serving"])
    ).first()

    if not token:
        return jsonify({"token": None}), 200

    branch = Branch.query.get(token.branch_id)
    service_type = ServiceType.query.get(token.service_type_id)
    counter = Counter.query.get(token.counter_id) if token.counter_id else None

    return jsonify({
        "token": {
            "id": token.id,
            "token_number": token.token_number,
            "status": token.status,
            "preferred_slot": token.preferred_slot,
            "estimated_wait_minutes": token.estimated_wait_minutes,
            "booked_at": token.booked_at.isoformat() if token.booked_at else None,
            "branch_id": token.branch_id,
            "branch_name": branch.name if branch else None,
            "service_type_name": service_type.name if service_type else None,
            "counter_name": counter.name if counter else None
        }
    }), 200


@tokens_bp.route("/api/tokens/<int:token_id>/cancel", methods=["POST"])
@login_required
def cancel_token(token_id):
    """Cancel a token belonging to the current user."""
    token = Token.query.get(token_id)
    if not token:
        return jsonify({"error": "Token not found"}), 404
    if token.user_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    token.status = "Cancelled"
    db.session.commit()
    return jsonify({"message": "Token cancelled"}), 200


@tokens_bp.route("/api/tokens/history", methods=["GET"])
@login_required
def token_history():
    """Return paginated token history for the current user."""
    page = request.args.get("page", 1, type=int)
    per_page = 20

    pagination = Token.query.filter_by(user_id=current_user.id)\
        .order_by(Token.booked_at.desc())\
        .paginate(page=page, per_page=per_page, error_out=False)

    tokens = []
    for t in pagination.items:
        branch = Branch.query.get(t.branch_id)
        service_type = ServiceType.query.get(t.service_type_id)
        tokens.append({
            "id": t.id,
            "token_number": t.token_number,
            "status": t.status,
            "branch_name": branch.name if branch else None,
            "service_type_name": service_type.name if service_type else None,
            "estimated_wait_minutes": t.estimated_wait_minutes,
            "booked_at": t.booked_at.isoformat() if t.booked_at else None
        })

    return jsonify({
        "tokens": tokens,
        "total": pagination.total,
        "page": pagination.page,
        "pages": pagination.pages
    }), 200
