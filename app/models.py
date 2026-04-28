from datetime import datetime
from flask_login import UserMixin
from sqlalchemy import event
from app.extensions import db


class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False, unique=True)
    phone = db.Column(db.Text, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=False, default="user")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    tokens = db.relationship("Token", backref="user", lazy=True)
    notifications = db.relationship("Notification", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.email}>"


class Branch(db.Model):
    __tablename__ = "branch"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.Text, nullable=False)
    location = db.Column(db.Text, nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)

    counters = db.relationship("Counter", backref="branch", lazy=True)
    service_types = db.relationship("ServiceType", backref="branch", lazy=True)
    tokens = db.relationship("Token", backref="branch", lazy=True)

    def __repr__(self):
        return f"<Branch {self.name}>"


class Counter(db.Model):
    __tablename__ = "counter"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branch.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)
    status = db.Column(db.Text, nullable=False, default="Inactive")

    tokens = db.relationship("Token", backref="counter", lazy=True)
    queue_delays = db.relationship("QueueDelay", backref="counter", lazy=True)

    def __repr__(self):
        return f"<Counter {self.name}>"


class ServiceType(db.Model):
    __tablename__ = "service_type"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branch.id"), nullable=False)
    name = db.Column(db.Text, nullable=False)

    tokens = db.relationship("Token", backref="service_type", lazy=True)

    def __repr__(self):
        return f"<ServiceType {self.name}>"


class Token(db.Model):
    __tablename__ = "token"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    counter_id = db.Column(db.Integer, db.ForeignKey("counter.id"), nullable=True)
    branch_id = db.Column(db.Integer, db.ForeignKey("branch.id"), nullable=False)
    service_type_id = db.Column(db.Integer, db.ForeignKey("service_type.id"), nullable=False)
    token_number = db.Column(db.Text, nullable=False, unique=True)
    status = db.Column(db.Text, nullable=False, default="Waiting")
    preferred_slot = db.Column(db.Text, nullable=True)
    booked_at = db.Column(db.DateTime, default=datetime.utcnow)
    status_updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    estimated_wait_minutes = db.Column(db.Integer, nullable=True)

    def __repr__(self):
        return f"<Token {self.token_number} [{self.status}]>"


@event.listens_for(Token, "before_update")
def token_before_update(mapper, connection, target):
    """Auto-update status_updated_at whenever a Token record is updated."""
    target.status_updated_at = datetime.utcnow()


class Notification(db.Model):
    __tablename__ = "notification"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.Text, nullable=False)
    is_read = db.Column(db.Integer, nullable=False, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Notification {self.type} user={self.user_id}>"


class QueueDelay(db.Model):
    __tablename__ = "queue_delay"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    counter_id = db.Column(db.Integer, db.ForeignKey("counter.id"), nullable=False)
    delay_minutes = db.Column(db.Integer, nullable=False)
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<QueueDelay counter={self.counter_id} delay={self.delay_minutes}m>"
