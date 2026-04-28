from flask import Flask
from sqlalchemy import event
from sqlalchemy.engine import Engine
import sqlite3

from config import Config
from app.extensions import db, login_manager


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """Enforce foreign key constraints for every SQLite connection."""
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()


def create_app(config_class=Config):
    app = Flask(__name__, template_folder="../templates", static_folder="../static")
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # User loader for Flask-Login
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Register blueprints (populated in later tasks)
    _register_blueprints(app)

    # Create tables
    with app.app_context():
        db.create_all()

    return app


def _register_blueprints(app):
    """Register all blueprints. Blueprints are added here as they are implemented."""
    try:
        from app.blueprints.auth import auth_bp
        app.register_blueprint(auth_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.tokens import tokens_bp
        app.register_blueprint(tokens_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.queue import queue_bp
        app.register_blueprint(queue_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.predict import predict_bp
        app.register_blueprint(predict_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.notifications import notifications_bp
        app.register_blueprint(notifications_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.admin import admin_bp
        app.register_blueprint(admin_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.pages import pages_bp
        app.register_blueprint(pages_bp)
    except ImportError:
        pass

    try:
        from app.blueprints.branches import branches_bp
        app.register_blueprint(branches_bp)
    except ImportError:
        pass
