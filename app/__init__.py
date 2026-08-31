from flask import Flask, request, session
from flask_wtf.csrf import CSRFProtect
from config import Config
import os
import datetime


csrf = CSRFProtect()


def create_app():
    app = Flask(__name__, template_folder='../templates', static_folder='../static')
    app.config.from_object(Config)

    # Initialize CSRF
    csrf.init_app(app)

    # Ensure upload folder exists
    try:
        os.makedirs(app.config.get('UPLOAD_FOLDER', 'static/uploads'), exist_ok=True)
    except OSError:
        pass

    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.voter import voter_bp
    from app.routes.elections import elections_bp
    from app.routes.voting import voting_bp
    from app.routes.grievances import grievances_bp
    from app.routes.info import info_bp
    from app.routes.admin import admin_bp
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(voter_bp, url_prefix='/voter')
    app.register_blueprint(elections_bp, url_prefix='/elections')
    app.register_blueprint(voting_bp, url_prefix='/voting')
    app.register_blueprint(grievances_bp, url_prefix='/grievances')
    app.register_blueprint(info_bp, url_prefix='/info')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    from app.routes.errors import register_error_handlers
    register_error_handlers(app)

    from app.services.db_operations import get_unread_notification_count
    from flask_login import current_user

    @app.context_processor
    def inject_globals():
        notif_count = 0
        try:
            if current_user.is_authenticated:
                notif_count = get_unread_notification_count(current_user.id)
        except:
            pass
        return {
            'academic_disclaimer': Config.ACADEMIC_DISCLAIMER,
            'unread_notifications': notif_count
        }

    from app.utils.translations import get_translation
    app.jinja_env.globals.update(get_translation=get_translation)

    def format_date(value, fmt='%d %b %Y'):
        if value is None:
            return 'N/A'
        if isinstance(value, str):
            for pattern in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M', '%Y-%m-%d %H:%M', '%Y-%m-%d'):
                try:
                    value = datetime.datetime.strptime(value, pattern)
                    break
                except ValueError:
                    continue
            else:
                return value
        if isinstance(value, datetime.datetime):
            return value.strftime(fmt)
        if isinstance(value, datetime.date):
            return value.strftime(fmt)
        return str(value)

    app.jinja_env.filters['format_date'] = format_date

    return app


def _seed_demo_data():
    """Seed database with demo data if not already present."""
    from app.utils.database import query_db, execute_db, get_backend
    from werkzeug.security import generate_password_hash

    admin = query_db("SELECT id FROM users WHERE email = 'adityagaikwad@2567'", one=True)
    if admin:
        return

    print("Seeding demo data...")
    backend = get_backend()
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    admin_pw = generate_password_hash('gunu@2567')
    voter_pw = generate_password_hash('Voter@2026')
    off_pw = generate_password_hash('Official@2026')

    users = [
        ('System Administrator', 'adityagaikwad@2567', '9000000000', None, admin_pw, 'ADMIN', 'active'),
        ('Aditya Gaikwad', 'aditya@demo.local', '9100000001', 'DEMO100001', voter_pw, 'VOTER', 'active'),
        ('Aditi Naik', 'aditi@demo.local', '9100000002', 'DEMO100002', voter_pw, 'VOTER', 'active'),
        ('Rahul Sharma', 'rahul@demo.local', '9100000003', 'DEMO100003', voter_pw, 'VOTER', 'active'),
        ('Priya Patil', 'priya@demo.local', '9100000004', 'DEMO100004', voter_pw, 'VOTER', 'active'),
        ('Sneha Deshmukh', 'sneha@demo.local', '9100000005', 'DEMO100005', voter_pw, 'VOTER', 'active'),
        ('Election Officer', 'official@demo.local', '9000000099', None, off_pw, 'ELECTION_OFFICIAL', 'active'),
    ]
    for u in users:
        execute_db(
            "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)", u
        )

    profiles = [
        (2, '2004-05-15', 'Male', '123 Demo Street, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
        (3, '2004-08-22', 'Female', '456 Demo Nagar, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
        (4, '2003-12-10', 'Male', '789 Demo Road, Nagpur', 'Maharashtra', 'Nagpur', 'Demo Constituency North', '440001'),
        (5, '2004-03-08', 'Female', '321 Demo Colony, Pune', 'Maharashtra', 'Pune', 'Demo Constituency Central', '411001'),
        (6, '2004-01-25', 'Female', '654 Demo Lane, Mumbai', 'Maharashtra', 'Mumbai', 'Demo Constituency South', '400001'),
    ]
    for p in profiles:
        execute_db(
            "INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", p
        )

    stations = [
        ('Demo Government College', 'Example Road, Akola, Maharashtra', 'Maharashtra', 'Akola', 'Demo Constituency', 'Demo Booth 12', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk'),
        ('Demo Community Hall', 'Market Street, Nagpur, Maharashtra', 'Maharashtra', 'Nagpur', 'Demo Constituency North', 'Demo Booth 05', 400, 'Wheelchair Accessible', 'Drinking Water, Toilet'),
        ('Demo Public School', 'Station Road, Pune, Maharashtra', 'Maharashtra', 'Pune', 'Demo Constituency Central', 'Demo Booth 08', 350, 'Ramp Access', 'Drinking Water, Toilet'),
        ('Demo Municipal Building', 'Main Road, Mumbai, Maharashtra', 'Maharashtra', 'Mumbai', 'Demo Constituency South', 'Demo Booth 15', 600, 'Wheelchair Accessible', 'Drinking Water, Toilet, Parking'),
    ]
    for s in stations:
        execute_db(
            "INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", s
        )

    yesterday = (datetime.datetime.now() - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    week_later = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    execute_db(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ('BCA Student Council Election 2026', 'Annual student council election for BCA department',
         'Student Council', 'All Constituencies', yesterday, week_later, 'Active', now)
    )
    past_start = (datetime.datetime.now() - datetime.timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
    past_end = (datetime.datetime.now() - datetime.timedelta(days=53)).strftime('%Y-%m-%d %H:%M:%S')
    execute_db(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ('BCA Cultural Committee 2025', 'Cultural committee election (completed)',
         'Cultural Committee', 'All Constituencies', past_start, past_end, 'Completed', '2025-10-25 09:00:00')
    )

    candidates = [
        (1, 'Aarav Mehta', 'BCA United', 'Star', 'Third-year BCA student'),
        (1, 'Sneha Kulkarni', 'Tech Forward', 'Laptop', 'Second-year BCA student'),
        (1, 'Vikram Patil', 'Student Voice', 'Megaphone', 'First-year BCA student'),
        (2, 'Priya Deshmukh', 'Arts Alliance', 'Palette', 'Cultural enthusiast'),
        (2, 'Rohan Gupta', 'Music Club', 'Note', 'Music lover'),
        (2, 'Neha Joshi', 'Drama Society', 'Masks', 'Drama enthusiast'),
    ]
    for c in candidates:
        execute_db(
            "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) "
            "VALUES (%s, %s, %s, %s, %s, %s)", (*c, now)
        )

    execute_db(
        "INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (2, 'correction', 'DEMO-2026-CORR000001', 'Submitted', '2026-08-20 10:00:00', '2026-08-20 10:00:00')
    )
    execute_db(
        "INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (3, 'new_registration', 'DEMO-2026-REG000002', 'Approved', '2026-02-01 10:00:00', '2026-02-15 10:00:00')
    )
    execute_db(
        "INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) "
        "VALUES (%s, %s, %s, %s, %s, %s)",
        (4, 'new_registration', 'DEMO-2026-REG000001', 'Approved', '2026-01-15 10:00:00', '2026-02-01 10:00:00')
    )

    for a in [
        (1, 'LOGIN', 'user', 1, '127.0.0.1', now),
        (3, 'LOGIN', 'user', 3, '127.0.0.1', '2026-08-26 09:30:00'),
        (2, 'LOGIN', 'user', 2, '127.0.0.1', '2026-08-26 09:00:00'),
        (1, 'ELECTION_CREATED', 'election', 1, '127.0.0.1', '2026-08-20 09:00:00'),
    ]:
        execute_db("INSERT INTO audit_logs (user_id, action, entity, entity_id, ip_address, created_at) VALUES (%s, %s, %s, %s, %s, %s)", a)
    for g in [
        (2, 'DEMO-2026-GRV000001', 'voter_registration', 'Name Mismatch', 'My name shows incorrectly', 'aditya@demo.local', 'Submitted', now, now),
        (3, 'DEMO-2026-GRV000002', 'polling_station', 'Accessibility Issue', 'No wheelchair ramp', 'aditi@demo.local', 'Submitted', now, now),
        (4, 'DEMO-2026-GRV000003', 'application', 'Application Delay', 'Pending 2 weeks', 'rahul@demo.local', 'Submitted', now, now),
    ]:
        execute_db("INSERT INTO grievances (user_id, reference_number, category, subject, description, contact_info, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", g)
    for n in [
        (2, 'Welcome', 'Account created successfully.', False, now),
        (3, 'Application Approved', 'Your registration is approved.', False, now),
        (1, 'System Update', 'Portal upgraded.', True, now),
    ]:
        execute_db("INSERT INTO notifications (user_id, title, message, is_read, created_at) VALUES (%s, %s, %s, %s, %s)", n)

    print("Demo data seeded successfully!")


# Create app instance at module level so gunicorn can find it via 'app:app'
app = create_app()

# Initialize login manager
from app.routes.auth import init_login_manager
init_login_manager(app)

# Lazy database initialization
_db_initialized = False

@app.before_request
def _lazy_db_init():
    global _db_initialized
    if _db_initialized:
        return
    _db_initialized = True
    with app.app_context():
        from app.utils.database import init_database
        try:
            init_database()
        except Exception as e:
            print(f"Database init note: {e}")
        try:
            _seed_demo_data()
        except Exception as e:
            print(f"Seed note: {e}")
