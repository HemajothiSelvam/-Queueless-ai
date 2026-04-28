"""
Prediction and RAG blueprint — public endpoints (no login required).
"""
from flask import Blueprint, request, jsonify

predict_bp = Blueprint("predict", __name__)


@predict_bp.get("/api/predict/wait-time")
def wait_time():
    branch_id = request.args.get("branch_id")
    service_type_id = request.args.get("service_type_id")
    slot = request.args.get("slot")

    if not branch_id or not service_type_id or not slot:
        return jsonify({"error": "branch_id, service_type_id, and slot are required"}), 400

    try:
        branch_id = int(branch_id)
        service_type_id = int(service_type_id)
    except ValueError:
        return jsonify({"error": "branch_id and service_type_id must be integers"}), 400

    from app.services.predictor import estimate_wait_time
    minutes = estimate_wait_time(branch_id, service_type_id, slot)
    return jsonify({"estimated_wait_minutes": minutes})


@predict_bp.get("/api/predict/best-slots")
def best_slots():
    branch_id = request.args.get("branch_id")
    service_type_id = request.args.get("service_type_id")

    if not branch_id or not service_type_id:
        return jsonify({"error": "branch_id and service_type_id are required"}), 400

    try:
        branch_id = int(branch_id)
        service_type_id = int(service_type_id)
    except ValueError:
        return jsonify({"error": "branch_id and service_type_id must be integers"}), 400

    from app.services.predictor import get_best_slots
    slots = get_best_slots(branch_id, service_type_id)
    return jsonify({"slots": slots})


@predict_bp.get("/api/rag/insights")
def rag_insights():
    branch_id = request.args.get("branch_id")
    service_type_id = request.args.get("service_type_id")

    if not branch_id or not service_type_id:
        return jsonify({"error": "branch_id and service_type_id are required"}), 400

    try:
        branch_id = int(branch_id)
        service_type_id = int(service_type_id)
    except ValueError:
        return jsonify({"error": "branch_id and service_type_id must be integers"}), 400

    from app.services.rag_engine import get_insights
    summary = get_insights(branch_id, service_type_id)
    return jsonify({"summary": summary})
