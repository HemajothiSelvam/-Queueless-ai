from app.models import Notification
from app.extensions import db


def create_notification(user_id, message, notif_type):
    """
    Create and persist a notification for a user.
    notif_type: one of 'turn_approaching', 'queue_delay', 'counter_changed', 'general'
    """
    notification = Notification(
        user_id=user_id,
        message=message,
        type=notif_type,
        is_read=0
    )
    db.session.add(notification)
    db.session.commit()
    return notification
