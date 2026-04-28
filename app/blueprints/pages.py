from flask import Blueprint, render_template, make_response
from flask_login import login_required

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def index():
    return render_template("index.html")


@pages_bp.route("/dashboard")
@login_required
def dashboard_page():
    return render_template("dashboard.html")


@pages_bp.route("/booking")
@login_required
def booking_page():
    resp = make_response(render_template("booking.html"))
    resp.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    resp.headers["Pragma"] = "no-cache"
    return resp


@pages_bp.route("/live-queue")
def live_queue_page():
    return render_template("live-queue.html")


@pages_bp.route("/notifications")
@login_required
def notifications_page():
    return render_template("notifications.html")


@pages_bp.route("/history")
@login_required
def history_page():
    return render_template("history.html")
