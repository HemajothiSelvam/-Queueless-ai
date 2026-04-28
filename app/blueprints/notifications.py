from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Notification

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.route("/api/notifications", methods=["GET"])
@login_required
def get_notifications():
    """Return all notifications for the current user, newest first."""
    notifications = Notification.query.filter_by(user_id=current_user.id)\
        .order_by(Notification.created_at.desc())\
        .all()

    return jsonify({
        "notifications": [
            {
                "id": n.id,
                "message": n.message,
                "type": n.type,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None
            }
            for n in notifications
        ]
    }), 200


@notifications_bp.route("/api/notifications/mark-read", methods=["POST"])
@login_required
def mark_all_read():
    """Mark all unread notifications for the current user as read."""
    Notification.query.filter_by(user_id=current_user.id, is_read=0)\
        .update({"is_read": 1})
    db.session.commit()
    return jsonify({"message": "All notifications marked as read"}), 200
