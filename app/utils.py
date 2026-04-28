from functools import wraps
from flask import jsonify, redirect, url_for, request
from flask_login import current_user


def require_role(role):
    """
    Decorator to enforce role-based access control.
    Returns HTTP 401 for unauthenticated users.
    Returns HTTP 403 for authenticated users with wrong role.
    For page routes, redirects instead of returning JSON.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Unauthenticated"}), 401
                return redirect(url_for('auth.login_page'))
            if current_user.role != role:
                if request.path.startswith('/api/'):
                    return jsonify({"error": "Forbidden"}), 403
                return redirect(url_for('pages.dashboard_page'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
