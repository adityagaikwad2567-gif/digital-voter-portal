"""Shared test fixtures for the Digital Voter Services Portal.

Uses per-test SQLite files via pytest's tmp_path to avoid Windows file-locking.
"""
import os
import sys
import sqlite3
import datetime
import pytest

# Ensure the project root is on the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

# Force SQLite backend for tests
os.environ['DATABASE_HOST'] = 'localhost'
os.environ['DATABASE_PORT'] = '9999'

from werkzeug.security import generate_password_hash


# ── Schema ─────────────────────────────────────────────────
SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    mobile VARCHAR(15),
    voter_id VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'VOTER',
    status VARCHAR(20) NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME
);
CREATE TABLE voter_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL UNIQUE,
    dob DATE, gender VARCHAR(10), address TEXT,
    state VARCHAR(100), district VARCHAR(100),
    constituency VARCHAR(150), pincode VARCHAR(10), photo VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    application_type VARCHAR(30) NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    status VARCHAR(30) NOT NULL DEFAULT 'Submitted',
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    remarks TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE elections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    election_type VARCHAR(100),
    constituency VARCHAR(150),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'Draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE candidates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    name VARCHAR(150) NOT NULL,
    party_name VARCHAR(200),
    symbol VARCHAR(100),
    description TEXT,
    image VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
);
CREATE TABLE votes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    election_id INTEGER NOT NULL,
    voter_id INTEGER NOT NULL,
    candidate_id INTEGER NOT NULL,
    voted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_code VARCHAR(100) NOT NULL UNIQUE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE(voter_id, election_id)
);
CREATE TABLE polling_stations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    state VARCHAR(100), district VARCHAR(100),
    constituency VARCHAR(150), booth_number VARCHAR(50),
    capacity INTEGER DEFAULT 500,
    accessibility VARCHAR(200), facilities TEXT
);
CREATE TABLE grievances (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    category VARCHAR(30) NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    contact_info VARCHAR(200),
    status VARCHAR(20) NOT NULL DEFAULT 'Submitted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read INTEGER NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);
CREATE TABLE audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    entity_id INTEGER,
    ip_address VARCHAR(45),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);
"""


def _seed_database(conn):
    """Insert minimal seed data for tests."""
    cur = conn.cursor()
    admin_pw = generate_password_hash('Admin@12345')
    voter_pw = generate_password_hash('Demo@12345')

    cur.execute(
        "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('Test Admin', 'admin@demo.local', '9000000000', None, admin_pw, 'ADMIN', 'active',
         '2026-01-01 00:00:00')
    )
    cur.execute(
        "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('Test Voter', 'voter@demo.local', '9100000001', 'DEMO100001', voter_pw, 'VOTER', 'active',
         '2026-01-15 10:00:00')
    )
    cur.execute(
        "INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('Second Voter', 'voter2@demo.local', '9100000002', 'DEMO100002', voter_pw, 'VOTER', 'active',
         '2026-02-01 11:00:00')
    )

    cur.execute(
        "INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (2, '2004-05-15', 'Male', '123 Test Street', 'Maharashtra', 'Akola', 'Test Constituency', '444001')
    )
    cur.execute(
        "INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (3, '2004-08-22', 'Female', '456 Test Nagar', 'Maharashtra', 'Akola', 'Test Constituency', '444001')
    )

    now = datetime.datetime.now()
    active_start = (now - datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
    active_end = (now + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')
    completed_start = (now - datetime.timedelta(days=60)).strftime('%Y-%m-%d %H:%M:%S')
    completed_end = (now - datetime.timedelta(days=53)).strftime('%Y-%m-%d %H:%M:%S')

    cur.execute(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('Test Election Active', 'Active test election', 'Test', 'All', active_start, active_end, 'Active',
         '2026-08-20 09:00:00')
    )
    cur.execute(
        "INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        ('Test Election Completed', 'Completed test election', 'Test', 'All', completed_start, completed_end,
         'Completed', '2026-06-20 09:00:00')
    )

    cur.execute(
        "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, 'Candidate Alpha', 'Party A', 'Star', 'Alpha candidate', '2026-08-20 09:00:00')
    )
    cur.execute(
        "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (1, 'Candidate Beta', 'Party B', 'Moon', 'Beta candidate', '2026-08-20 09:00:00')
    )
    cur.execute(
        "INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (2, 'Candidate Gamma', 'Party G', 'Sun', 'Gamma candidate', '2026-06-20 09:00:00')
    )

    cur.execute(
        "INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ('Test Polling Station', 'Test Address', 'Maharashtra', 'Akola', 'Test Constituency',
         '01', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet')
    )

    cur.execute(
        "INSERT INTO grievances (user_id, reference_number, category, subject, description, status) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (2, 'GRV-2026-TEST01', 'voter_registration', 'Test grievance', 'Test description', 'Submitted')
    )

    conn.commit()


@pytest.fixture
def app(tmp_path):
    """Create a fresh app with a per-test SQLite DB.

    Uses tmp_path for automatic cleanup (no file-locking issues).
    Closes the module-level connection between tests properly.
    """
    from app import create_app
    from app.routes.auth import init_login_manager
    import app.utils.database as db_module

    # Close any lingering connection from a previous test
    if db_module._sqlite_conn is not None:
        try:
            db_module._sqlite_conn.close()
        except Exception:
            pass
        db_module._sqlite_conn = None
    db_module._backend = None

    # Each test gets its own DB file in tmp_path
    test_db = str(tmp_path / 'voter_portal.db')
    db_module._SQLITE_PATH = test_db

    # Initialize schema + seed data via direct connection
    init_conn = sqlite3.connect(test_db, check_same_thread=False)
    init_conn.row_factory = sqlite3.Row
    init_conn.execute("PRAGMA journal_mode=WAL")
    init_conn.execute("PRAGMA foreign_keys=ON")
    init_conn.executescript(SCHEMA)
    _seed_database(init_conn)
    # Keep this connection alive and hand it to the database module
    db_module._sqlite_conn = init_conn

    application = create_app()
    application.config['TESTING'] = True
    application.config['WTF_CSRF_ENABLED'] = False
    application.config['SERVER_NAME'] = 'localhost'

    init_login_manager(application)

    yield application

    # Teardown: close module-level connection
    if db_module._sqlite_conn is not None:
        try:
            db_module._sqlite_conn.close()
        except Exception:
            pass
        db_module._sqlite_conn = None
    db_module._backend = None
    # tmp_path handles file cleanup automatically


@pytest.fixture
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture
def app_context(app):
    """Provide a push/pop'd app context."""
    with app.app_context():
        yield


# ── Login helpers ──────────────────────────────────────────

def login_admin(client):
    """Log in as the test admin."""
    return client.post('/auth/login', data={
        'email': 'admin@demo.local',
        'password': 'Admin@12345',
    }, follow_redirects=False)


def login_voter(client):
    """Log in as the first test voter."""
    return client.post('/auth/login', data={
        'email': 'voter@demo.local',
        'password': 'Demo@12345',
    }, follow_redirects=False)


def login_voter2(client):
    """Log in as the second test voter."""
    return client.post('/auth/login', data={
        'email': 'voter2@demo.local',
        'password': 'Demo@12345',
    }, follow_redirects=False)


def logout(client):
    """Log out."""
    return client.get('/auth/logout', follow_redirects=False)
