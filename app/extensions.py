from flask import request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()
login_manager.login_view = "auth.login_page"
login_manager.login_message_category = "info"


@login_manager.unauthorized_handler
def unauthorized():
    """Return 401 JSON for API routes, redirect for page routes."""
    if request.path.startswith("/api/"):
        return jsonify({"error": "Unauthenticated"}), 401
    from flask import redirect, url_for
    return redirect(url_for(login_manager.login_view))
