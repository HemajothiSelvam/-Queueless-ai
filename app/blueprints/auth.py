from flask import Blueprint, request, jsonify, render_template, redirect, url_for
from flask_login import login_user, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db
from app.models import User

auth_bp = Blueprint("auth", __name__)


# Page routes
@auth_bp.route("/login")
def login_page():
    """Serve the login page."""
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard_page"))
        return redirect(url_for("pages.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/register")
def register_page():
    """Serve the registration page."""
    if current_user.is_authenticated:
        if current_user.role == "admin":
            return redirect(url_for("admin.admin_dashboard_page"))
        return redirect(url_for("pages.dashboard_page"))
    return render_template("register.html")


# API routes
@auth_bp.route("/api/auth/register", methods=["POST"])
def register():
    """
    Register a new user.
    Returns HTTP 409 if email already exists.
    """
    data = request.get_json()
    
    # Validate required fields
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    name = data.get("name", "").strip()
    email = data.get("email", "").strip()
    phone = data.get("phone", "").strip()
    password = data.get("password", "")
    role = data.get("role", "user")
    
    # Validate non-empty fields
    if not name or not email or not phone or not password:
        return jsonify({"error": "All fields are required"}), 400
    
    # Validate email format (basic check)
    if "@" not in email or "." not in email:
        return jsonify({"error": "Invalid email format"}), 400
    
    # Validate password strength (min 8 chars + 1 ASCII digit)
    if len(password) < 8:
        return jsonify({"error": "Password must be at least 8 characters"}), 400
    if not any(char in "0123456789" for char in password):
        return jsonify({"error": "Password must contain at least one number"}), 400
    
    # Check for duplicate email
    existing_user = User.query.filter_by(email=email).first()
    if existing_user:
        return jsonify({"error": "Email already registered"}), 409
    
    # Create new user
    password_hash = generate_password_hash(password)
    new_user = User(
        name=name,
        email=email,
        phone=phone,
        password_hash=password_hash,
        role=role
    )
    
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({
        "message": "Registration successful",
        "user": {
            "id": new_user.id,
            "name": new_user.name,
            "email": new_user.email,
            "role": new_user.role
        }
    }), 201


@auth_bp.route("/api/auth/login", methods=["POST"])
def login():
    """
    Authenticate user and create session.
    Returns error if credentials are invalid.
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "Request body is required"}), 400
    
    email = data.get("email", "").strip()
    password = data.get("password", "")
    
    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    
    # Find user by email
    user = User.query.filter_by(email=email).first()
    
    # Validate credentials
    if not user or not check_password_hash(user.password_hash, password):
        return jsonify({"error": "Invalid email or password"}), 401
    
    # Create session
    login_user(user)
    
    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "role": user.role
        }
    }), 200


@auth_bp.route("/api/auth/logout", methods=["POST"])
def logout():
    """
    Invalidate the current session.
    """
    logout_user()
    return jsonify({"message": "Logout successful"}), 200


@auth_bp.route("/api/auth/me", methods=["GET"])
def me():
    """
    Return current session user info.
    Returns HTTP 401 if not authenticated.
    """
    if not current_user.is_authenticated:
        return jsonify({"error": "Unauthenticated"}), 401
    
    return jsonify({
        "user": {
            "id": current_user.id,
            "name": current_user.name,
            "email": current_user.email,
            "phone": current_user.phone,
            "role": current_user.role
        }
    }), 200
