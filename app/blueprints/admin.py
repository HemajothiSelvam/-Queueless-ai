from datetime import date, datetime, timedelta
from flask import Blueprint, jsonify, render_template, request
from app.extensions import db
from app.models import User, Token, Counter, Branch, ServiceType, QueueDelay
from app.utils import require_role
from app.services.notification_service import create_notification

admin_bp = Blueprint('admin', __name__)


# ── Page routes ──────────────────────────────────────────────────────────────

@admin_bp.route('/admin/dashboard')
@require_role('admin')
def admin_dashboard_page():
    return render_template('admin/dashboard.html')


@admin_bp.route('/admin/queue')
@require_role('admin')
def admin_queue_page():
    return render_template('admin/queue-management.html')


@admin_bp.route('/admin/reports')
@require_role('admin')
def admin_reports_page():
    return render_template('admin/reports.html')


# ── API routes ────────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/dashboard')
@require_role('admin')
def admin_dashboard_api():
    today = date.today()
    today_start = datetime(today.year, today.month, today.day)
    today_end = today_start + timedelta(days=1)

    # Total users created today
    total_users_today = User.query.filter(
        User.created_at >= today_start,
        User.created_at < today_end
    ).count()

    # All tokens booked today
    tokens_today = Token.query.filter(
        Token.booked_at >= today_start,
        Token.booked_at < today_end
    ).all()

    total_tokens = len(tokens_today)

    # Average wait time today (int, 0 if none)
    wait_times = [t.estimated_wait_minutes for t in tokens_today if t.estimated_wait_minutes is not None]
    avg_wait_time = int(sum(wait_times) / len(wait_times)) if wait_times else 0

    # Active counters
    active_counters = Counter.query.filter_by(status='Active').count()

    # Hourly volume: 24 ints (index = hour 0-23)
    hourly_volume = [0] * 24
    for token in tokens_today:
        if token.booked_at:
            hourly_volume[token.booked_at.hour] += 1

    # Weekly avg wait: past 7 days (index 0 = 6 days ago, index 6 = today)
    weekly_avg_wait = []
    for days_ago in range(6, -1, -1):
        day = today - timedelta(days=days_ago)
        day_start = datetime(day.year, day.month, day.day)
        day_end = day_start + timedelta(days=1)
        day_tokens = Token.query.filter(
            Token.booked_at >= day_start,
            Token.booked_at < day_end
        ).all()
        day_waits = [t.estimated_wait_minutes for t in day_tokens if t.estimated_wait_minutes is not None]
        avg = round(sum(day_waits) / len(day_waits), 2) if day_waits else 0.0
        weekly_avg_wait.append(avg)

    return jsonify({
        'total_users_today': total_users_today,
        'total_tokens': total_tokens,
        'avg_wait_time': avg_wait_time,
        'active_counters': active_counters,
        'hourly_volume': hourly_volume,
        'weekly_avg_wait': weekly_avg_wait,
    })


# ── Counter management ────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/counters')
@require_role('admin')
def list_counters():
    counters = Counter.query.join(Branch).all()
    return jsonify([
        {
            'id': c.id,
            'name': c.name,
            'status': c.status,
            'branch_id': c.branch_id,
            'branch_name': c.branch.name,
        }
        for c in counters
    ])


@admin_bp.route('/api/admin/counters/<int:counter_id>/open', methods=['POST'])
@require_role('admin')
def open_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    counter.status = 'Active'
    db.session.commit()
    return jsonify({'message': 'Counter opened', 'counter_id': counter_id})


@admin_bp.route('/api/admin/counters/<int:counter_id>/close', methods=['POST'])
@require_role('admin')
def close_counter(counter_id):
    counter = Counter.query.get_or_404(counter_id)
    counter.status = 'Inactive'

    # Find another active counter at the same branch
    other_active = Counter.query.filter(
        Counter.branch_id == counter.branch_id,
        Counter.status == 'Active',
        Counter.id != counter_id
    ).first()

    # Reassign waiting tokens
    waiting_tokens = Token.query.filter_by(counter_id=counter_id, status='Waiting').all()
    for token in waiting_tokens:
        token.counter_id = other_active.id if other_active else None

    db.session.commit()
    return jsonify({'message': 'Counter closed', 'reassigned': len(waiting_tokens)})


# ── Queue actions ─────────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/queue/call-next', methods=['POST'])
@require_role('admin')
def call_next():
    data = request.get_json(silent=True) or {}
    counter_id = data.get('counter_id')
    if not counter_id:
        return jsonify({'error': 'counter_id is required'}), 400

    # Mark current "Now Serving" as "Served"
    serving = Token.query.filter_by(counter_id=counter_id, status='Now Serving').first()
    served_number = None
    if serving:
        serving.status = 'Served'
        served_number = serving.token_number

    # Advance next "Waiting" token
    next_token = Token.query.filter_by(counter_id=counter_id, status='Waiting') \
        .order_by(Token.booked_at.asc()).first()
    next_number = None
    if next_token:
        next_token.status = 'Now Serving'
        next_number = next_token.token_number

    db.session.commit()
    return jsonify({'served_token': served_number, 'next_token': next_number})


@admin_bp.route('/api/admin/queue/skip', methods=['POST'])
@require_role('admin')
def skip_token():
    data = request.get_json(silent=True) or {}
    counter_id = data.get('counter_id')
    if not counter_id:
        return jsonify({'error': 'counter_id is required'}), 400

    # Mark current "Now Serving" as "Skipped" and move to end of queue
    serving = Token.query.filter_by(counter_id=counter_id, status='Now Serving').first()
    skipped_number = None
    if serving:
        serving.status = 'Skipped'
        serving.booked_at = datetime.utcnow()
        skipped_number = serving.token_number

    # Advance next "Waiting" token
    next_token = Token.query.filter_by(counter_id=counter_id, status='Waiting') \
        .order_by(Token.booked_at.asc()).first()
    next_number = None
    if next_token:
        next_token.status = 'Now Serving'
        next_number = next_token.token_number

    db.session.commit()
    return jsonify({'skipped_token': skipped_number, 'next_token': next_number})


@admin_bp.route('/api/admin/queue/delay', methods=['POST'])
@require_role('admin')
def apply_delay():
    data = request.get_json(silent=True) or {}
    counter_id = data.get('counter_id')
    delay_minutes = data.get('delay_minutes')

    if not counter_id:
        return jsonify({'error': 'counter_id is required'}), 400
    if delay_minutes is None or int(delay_minutes) <= 0:
        return jsonify({'error': 'delay_minutes must be > 0'}), 400

    delay_minutes = int(delay_minutes)

    # Insert QueueDelay record
    queue_delay = QueueDelay(counter_id=counter_id, delay_minutes=delay_minutes)
    db.session.add(queue_delay)

    # Update all waiting tokens and notify users
    waiting_tokens = Token.query.filter_by(counter_id=counter_id, status='Waiting').all()
    for token in waiting_tokens:
        if token.estimated_wait_minutes is not None:
            token.estimated_wait_minutes += delay_minutes
        else:
            token.estimated_wait_minutes = delay_minutes
        create_notification(
            token.user_id,
            f'Your queue has been delayed by {delay_minutes} minutes.',
            'queue_delay'
        )

    db.session.commit()
    return jsonify({'message': 'Delay applied', 'affected_tokens': len(waiting_tokens)})


# ── Waiting queue list ────────────────────────────────────────────────────────

@admin_bp.route('/api/admin/queue/waiting')
@require_role('admin')
def waiting_tokens():
    counter_id = request.args.get('counter_id', type=int)
    if not counter_id:
        return jsonify({'error': 'counter_id is required'}), 400

    tokens = Token.query.filter_by(counter_id=counter_id, status='Waiting') \
        .order_by(Token.booked_at.asc()).all()
    return jsonify({'tokens': [
        {
            'id': t.id,
            'token_number': t.token_number,
            'status': t.status,
            'estimated_wait_minutes': t.estimated_wait_minutes,
        }
        for t in tokens
    ]})


@admin_bp.route('/api/admin/queue/patient-done', methods=['POST'])
@require_role('admin')
def patient_done():
    """
    Admin marks current patient as done (Served).
    Automatically notifies the next waiting patient.
    """
    data = request.get_json() or {}
    counter_id = data.get('counter_id')

    if not counter_id:
        return jsonify({"error": "counter_id is required"}), 400

    # Find current "Now Serving" token
    current = Token.query.filter_by(
        counter_id=counter_id, status="Now Serving"
    ).first()

    if current:
        current.status = "Served"
        db.session.flush()

    # Find next waiting token (ordered by booked_at)
    next_token = Token.query.filter_by(
        counter_id=counter_id, status="Waiting"
    ).order_by(Token.booked_at.asc()).first()

    # If no counter-specific token, look at branch level
    if not next_token and current:
        counter = Counter.query.get(counter_id)
        if counter:
            next_token = Token.query.filter_by(
                branch_id=counter.branch_id, status="Waiting"
            ).order_by(Token.booked_at.asc()).first()
            if next_token:
                next_token.counter_id = counter_id

    next_info = None
    if next_token:
        next_token.status = "Now Serving"
        next_info = next_token.token_number

        # Auto-notify the next patient
        counter = Counter.query.get(counter_id)
        counter_name = counter.name if counter else f"Counter {counter_id}"
        create_notification(
            next_token.user_id,
            f"🏥 It's your turn! Please proceed to {counter_name}. Your token: {next_token.token_number}",
            "turn_approaching"
        )

    db.session.commit()

    return jsonify({
        "message": "Patient marked as done",
        "served_token": current.token_number if current else None,
        "next_token": next_info,
        "notified": next_info is not None
    }), 200


@admin_bp.route('/api/admin/queue/current')
@require_role('admin')
def queue_current():
    """Get current serving patient + waiting list for a counter."""
    counter_id = request.args.get('counter_id', type=int)
    if not counter_id:
        return jsonify({'error': 'counter_id is required'}), 400

    counter = Counter.query.get(counter_id)
    if not counter:
        return jsonify({'error': 'Counter not found'}), 404

    # Now serving
    serving = Token.query.filter_by(counter_id=counter_id, status='Now Serving').first()
    serving_data = None
    if serving:
        patient = User.query.get(serving.user_id)
        service = ServiceType.query.get(serving.service_type_id)
        serving_data = {
            'id': serving.id,
            'token_number': serving.token_number,
            'patient_name': patient.name if patient else 'Patient',
            'service_name': service.name if service else '',
            'preferred_slot': serving.preferred_slot,
        }

    # Waiting list (branch-wide so all counters' patients are visible)
    waiting_tokens = Token.query.filter_by(
        branch_id=counter.branch_id, status='Waiting'
    ).order_by(Token.booked_at.asc()).all()

    waiting_data = []
    for t in waiting_tokens:
        patient = User.query.get(t.user_id)
        service = ServiceType.query.get(t.service_type_id)
        waiting_data.append({
            'id': t.id,
            'token_number': t.token_number,
            'patient_name': patient.name if patient else 'Patient',
            'service_name': service.name if service else '',
            'preferred_slot': t.preferred_slot,
        })

    # Served today count
    today_start = datetime.combine(date.today(), datetime.min.time())
    served_today = Token.query.filter(
        Token.counter_id == counter_id,
        Token.status == 'Served',
        Token.status_updated_at >= today_start
    ).count()

    return jsonify({
        'now_serving': serving_data,
        'waiting': waiting_data,
        'waiting_count': len(waiting_data),
        'served_today': served_today,
    })
