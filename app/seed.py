from app.extensions import db
from app.models import Branch, Counter, ServiceType, User, Notification, Token
from werkzeug.security import generate_password_hash
from datetime import datetime


def seed_db():
    """Always clears and re-seeds the database with Puducherry hospital data."""
    Notification.query.delete()
    Token.query.delete()
    ServiceType.query.delete()
    Counter.query.delete()
    Branch.query.delete()
    User.query.delete()
    db.session.flush()

    # Real hospitals near Puducherry/Pondicherry
    hospitals = [
        Branch(name="JIPMER Hospital",
               location="Dhanvantari Nagar, Gorimedu, Puducherry",
               latitude=11.9416, longitude=79.8083),
        Branch(name="PIMS - Pondicherry Institute of Medical Sciences",
               location="Kalapet, Puducherry - 605014",
               latitude=11.9799, longitude=79.8553),
        Branch(name="Mahatma Gandhi Medical College",
               location="Pillaiyarkuppam, Puducherry - 607402",
               latitude=11.8462, longitude=79.7598),
        Branch(name="Aarupadai Veedu Medical College",
               location="Kirumampakkam, Puducherry - 607403",
               latitude=11.8301, longitude=79.7512),
        Branch(name="Sri Manakula Vinayagar Medical College",
               location="Madagadipet, Puducherry - 605107",
               latitude=11.9102, longitude=79.7601),
    ]
    db.session.add_all(hospitals)
    db.session.flush()

    depts = ["General Medicine", "Cardiology", "Orthopedics", "Pediatrics", "Neurology", "Dermatology"]

    for h in hospitals:
        db.session.add_all([
            Counter(branch_id=h.id, name="Doctor Room 1", status="Active"),
            Counter(branch_id=h.id, name="Doctor Room 2", status="Active"),
        ])
        for dept in depts:
            db.session.add(ServiceType(branch_id=h.id, name=dept))

    db.session.flush()

    admin = User(name="Dr. Admin", email="admin@hospital.ai", phone="9876543210",
                 password_hash=generate_password_hash("Admin1234"), role="admin")
    patient = User(name="Demo Patient", email="patient@hospital.ai", phone="9876543211",
                   password_hash=generate_password_hash("Patient123"), role="user")
    db.session.add_all([admin, patient])
    db.session.flush()

    sample_notifications = [
        Notification(user_id=patient.id,
                     message="🏥 Welcome! Book your first appointment from the dashboard.",
                     type="general", is_read=0, created_at=datetime.utcnow()),
        Notification(user_id=patient.id,
                     message="🔔 Your appointment at JIPMER Hospital has been confirmed. Token: JIP-20250427-001",
                     type="general", is_read=0, created_at=datetime.utcnow()),
        Notification(user_id=patient.id,
                     message="⏱️ Queue update: 3 patients ahead of you at JIPMER Hospital.",
                     type="queue_delay", is_read=0, created_at=datetime.utcnow()),
        Notification(user_id=patient.id,
                     message="🏥 It's almost your turn! Please proceed to Doctor Room 1.",
                     type="turn_approaching", is_read=0, created_at=datetime.utcnow()),
        Notification(user_id=patient.id,
                     message="✅ Appointment complete. Thank you for visiting JIPMER Hospital!",
                     type="general", is_read=1, created_at=datetime.utcnow()),
    ]
    db.session.add_all(sample_notifications)
    db.session.commit()

    print("✅ Seeded 5 Puducherry hospitals!")
    print("   Admin:   admin@hospital.ai / Admin1234")
    print("   Patient: patient@hospital.ai / Patient123")


if __name__ == "__main__":
    from app import create_app
    app = create_app()
    with app.app_context():
        seed_db()
