from flask import Blueprint, jsonify
from app.models import Branch, ServiceType

branches_bp = Blueprint("branches", __name__)

@branches_bp.route("/api/branches")
def get_branches():
    branches = Branch.query.all()
    return jsonify([
        {"id": b.id, "name": b.name, "location": b.location,
         "latitude": b.latitude, "longitude": b.longitude}
        for b in branches
    ])

@branches_bp.route("/api/branches/<int:branch_id>/services")
def get_branch_services(branch_id):
    branch = Branch.query.get(branch_id)
    if not branch:
        return jsonify({"error": "Not found"}), 404
    services = ServiceType.query.filter_by(branch_id=branch_id).all()
    return jsonify([{"id": s.id, "name": s.name} for s in services])
