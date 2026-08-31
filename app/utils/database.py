"""Database abstraction layer — MySQL / PostgreSQL / SQLite fallback.

If DATABASE_URL is set (Render), use PostgreSQL.
If MySQL is available, use it.
Otherwise fall back to SQLite.
"""
import os, sqlite3, datetime, re
from config import Config

_backend = None  # 'mysql' | 'postgresql' | 'sqlite' | None (not yet probed)
_sqlite_conn = None

_SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'voter_portal.db'
)

# ── Query adaptation (MySQL → SQLite) ───────────────────────
def _adapt_query(q):
    """Convert MySQL-style query to SQLite-compatible query."""
    q = q.replace('%s', '?')
    q = q.replace('ON UPDATE CURRENT_TIMESTAMP', '')
    q = re.sub(r"DATE_FORMAT\((\w+),\s*'([^']+)'\)", r"strftime('\2', \1)", q)
    return q

def _adapt_query_pg(q):
    """Convert MySQL-style query to PostgreSQL-compatible query.
    Handles: TIMESTAMPDIFF, CURDATE, DATE_FORMAT, NOW, LIMIT/OFFSET."""
    q = q.replace('ON UPDATE CURRENT_TIMESTAMP', '')
    # TIMESTAMPDIFF(YEAR, col, CURDATE()) → EXTRACT(YEAR FROM AGE(col::date))
    q = re.sub(
        r"TIMESTAMPDIFF\(\s*YEAR\s*,\s*(\w+\.?\w*)\s*,\s*CURDATE\(\s*\)\s*\)",
        r"EXTRACT(YEAR FROM AGE(\1::date))", q
    )
    # CURDATE() → CURRENT_DATE
    q = q.replace('CURDATE()', 'CURRENT_DATE')
    # DATE_FORMAT(col, 'fmt') → to_char(col, 'fmt')
    # PostgreSQL to_char uses different format codes than MySQL
    q = re.sub(
        r"DATE_FORMAT\((\w+\.?\w*),\s*'([^']+)'\)",
        lambda m: f"to_char({m.group(1)}, '{_mysql_datefmt_to_pg(m.group(2))}')",
        q
    )
    # NOW() works in PostgreSQL, no change needed
    return q


def _mysql_datefmt_to_pg(fmt):
    """Convert MySQL DATE_FORMAT codes to PostgreSQL to_char codes."""
    mapping = {
        '%Y': 'YYYY', '%m': 'MM', '%d': 'DD', '%H': 'HH24',
        '%i': 'MI', '%s': 'SS', '%y': 'YY', '%M': 'Month',
        '%b': 'Mon', '%W': 'Day', '%w': 'D',
    }
    for mysql_code, pg_code in mapping.items():
        fmt = fmt.replace(mysql_code, pg_code)
    return fmt


# ── Backend detection ───────────────────────────────────────
def _try_mysql():
    try:
        import pymysql
        conn = pymysql.connect(
            host=Config.DATABASE_HOST, user=Config.DATABASE_USER,
            password=Config.DATABASE_PASSWORD, database=Config.DATABASE_NAME,
            port=Config.DATABASE_PORT, connect_timeout=3
        )
        conn.close()
        return True
    except Exception:
        return False

def _parse_pg_url(db_url):
    """Parse DATABASE_URL into psycopg2 keyword arguments.
    Custom parser that handles brackets and @ in passwords
    (Python 3.12+ urlparse chokes on brackets as IPv6 syntax).
    Uses hostaddr for IPv4 while keeping host for SNI/tenant routing."""
    import socket
    # Strip scheme
    url = db_url.replace('postgresql://', '').replace('postgres://', '')
    # Split off dbname (everything after last /)
    slash_idx = url.rfind('/')
    if slash_idx >= 0:
        dbname = url[slash_idx + 1:]
        authority = url[:slash_idx]
    else:
        dbname = 'postgres'
        authority = url
    # Split user:password@host:port — find LAST @ to handle @ in password
    at_idx = authority.rfind('@')
    if at_idx >= 0:
        userinfo = authority[:at_idx]
        hostport = authority[at_idx + 1:]
    else:
        userinfo = ''
        hostport = authority
    # Split user:password — find FIRST : to get user
    colon_idx = userinfo.find(':')
    if colon_idx >= 0:
        user = userinfo[:colon_idx]
        password = userinfo[colon_idx + 1:]
    else:
        user = userinfo
        password = ''
    # Split host:port
    if hostport.startswith('['):
        bracket_end = hostport.find(']')
        host = hostport[1:bracket_end] if bracket_end > 0 else hostport
        port_str = hostport[bracket_end + 2:] if bracket_end + 1 < len(hostport) and hostport[bracket_end + 1] == ':' else ''
    else:
        colon_idx = hostport.rfind(':')
        if colon_idx >= 0:
            host = hostport[:colon_idx]
            port_str = hostport[colon_idx + 1:]
        else:
            host = hostport
            port_str = ''
    params = {
        'host': host,
        'port': int(port_str) if port_str else 5432,
        'dbname': dbname,
        'user': user,
    }
    if password:
        params['password'] = password
    # Resolve hostname to IPv4 for Vercel serverless (can't do IPv6 outbound)
    # but keep 'host' for SNI/tenant routing — use 'hostaddr' for the actual IP
    try:
        infos = socket.getaddrinfo(host, None, socket.AF_INET)
        if infos:
            params['hostaddr'] = infos[0][4][0]
    except socket.gaierror:
        pass  # keep original hostname, psycopg2 will try
    return params


def _try_postgres():
    """Check if DATABASE_URL is set and PostgreSQL is reachable."""
    db_url = os.environ.get('DATABASE_URL', '')
    if not db_url:
        return False
    try:
        import psycopg2
        params = _parse_pg_url(db_url)
        params['sslmode'] = 'require'
        conn = psycopg2.connect(**params, connect_timeout=10)
        conn.close()
        return True
    except Exception as e:
        print(f"[database] PostgreSQL connection failed: {e}")
        return False

def get_backend():
    global _backend
    if _backend is not None:
        return _backend
    if _try_postgres():
        _backend = 'postgresql'
    elif _try_mysql():
        _backend = 'mysql'
    else:
        _backend = 'sqlite'
    print(f"[database] Using backend: {_backend.upper()}")
    return _backend


# ── PostgreSQL connection ───────────────────────────────────
def _pg_connect():
    import psycopg2
    db_url = os.environ.get('DATABASE_URL', '')
    params = _parse_pg_url(db_url)
    params['sslmode'] = 'require'
    conn = psycopg2.connect(**params)
    conn.autocommit = True
    return conn

# Persistent connection for init (reused across multiple queries)
_pg_init_conn = None

def _pg_init_connect():
    global _pg_init_conn
    if _pg_init_conn is None or _pg_init_conn.closed:
        _pg_init_conn = _pg_connect()
    return _pg_init_conn

def _pg_init_close():
    global _pg_init_conn
    if _pg_init_conn and not _pg_init_conn.closed:
        try:
            _pg_init_conn.close()
        except Exception:
            pass
    _pg_init_conn = None

def _query_pg(query, args, one):
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        cur.execute(_adapt_query_pg(query), args)
        if one:
            row = cur.fetchone()
            if row is None:
                result = None
            else:
                result = dict(zip([d[0] for d in cur.description], row))
        else:
            cols = [d[0] for d in cur.description]
            result = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"PostgreSQL query error: {e}")
        return None

def _execute_pg(query, args):
    try:
        conn = _pg_connect()
        cur = conn.cursor()
        adapted = _adapt_query_pg(query)
        # PostgreSQL INSERT without RETURNING doesn't expose the inserted ID.
        # Append RETURNING id so we can return it (mirrors MySQL's lastrowid).
        q_upper = adapted.strip().upper()
        if q_upper.startswith('INSERT') and 'RETURNING' not in q_upper:
            adapted += ' RETURNING id'
        cur.execute(adapted, args)
        lastrowid = None
        if cur.description:
            row = cur.fetchone()
            if row:
                lastrowid = row[0]
        cur.close()
        conn.close()
        return lastrowid
    except Exception as e:
        print(f"PostgreSQL execute error: {e}")
        return None

def _transaction_pg(operations):
    try:
        conn = _pg_connect()
        conn.autocommit = False
        cur = conn.cursor()
        for q, a in operations:
            cur.execute(_adapt_query_pg(q), a)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"PostgreSQL transaction error: {e}")
        return False


# ── MySQL connection ────────────────────────────────────────
def _mysql_connect():
    import pymysql
    return pymysql.connect(
        host=Config.DATABASE_HOST, user=Config.DATABASE_USER,
        password=Config.DATABASE_PASSWORD, database=Config.DATABASE_NAME,
        port=Config.DATABASE_PORT, cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )

def _query_mysql(query, args, one):
    try:
        conn = _mysql_connect()
        cur = conn.cursor()
        cur.execute(query, args)
        result = cur.fetchone() if one else cur.fetchall()
        cur.close()
        conn.close()
        return result
    except Exception as e:
        print(f"MySQL query error: {e}")
        return None

def _execute_mysql(query, args):
    try:
        conn = _mysql_connect()
        cur = conn.cursor()
        cur.execute(query, args)
        lastrowid = cur.lastrowid
        cur.close()
        conn.close()
        return lastrowid
    except Exception as e:
        print(f"MySQL execute error: {e}")
        return None

def _transaction_mysql(operations):
    try:
        conn = _mysql_connect()
        conn.autocommit(False)
        cur = conn.cursor()
        for q, a in operations:
            cur.execute(q, a)
        conn.commit()
        cur.close()
        conn.close()
        return True
    except Exception as e:
        print(f"MySQL transaction error: {e}")
        return False


# ── SQLite connection ───────────────────────────────────────
def _sqlite_connect():
    global _sqlite_conn
    if _sqlite_conn is None:
        _sqlite_conn = sqlite3.connect(_SQLITE_PATH, check_same_thread=False)
        _sqlite_conn.row_factory = sqlite3.Row
        _sqlite_conn.execute("PRAGMA journal_mode=WAL")
        _sqlite_conn.execute("PRAGMA foreign_keys=ON")
    return _sqlite_conn

def _sqlite_now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

def _query_sqlite(query, args, one):
    try:
        conn = _sqlite_connect()
        cur = conn.cursor()
        q = _adapt_query(query)
        q = q.replace('NOW()', f"'{_sqlite_now()}'").replace('ON UPDATE CURRENT_TIMESTAMP', '')
        cur.execute(q, list(args) if args else [])
        if one:
            row = cur.fetchone()
            result = dict(row) if row else None
        else:
            result = [dict(r) for r in cur.fetchall()]
        cur.close()
        return result
    except Exception as e:
        print(f"SQLite query error: {e}\n  Query: {query[:120]}")
        return None

def _execute_sqlite(query, args):
    try:
        conn = _sqlite_connect()
        cur = conn.cursor()
        q = _adapt_query(query)
        q = q.replace('NOW()', f"'{_sqlite_now()}'").replace('ON UPDATE CURRENT_TIMESTAMP', '')
        cur.execute(q, list(args) if args else [])
        conn.commit()
        lastrowid = cur.lastrowid
        cur.close()
        return lastrowid
    except Exception as e:
        print(f"SQLite execute error: {e}\n  Query: {query[:120]}")
        return None

def _transaction_sqlite(operations):
    try:
        conn = _sqlite_connect()
        cur = conn.cursor()
        for q, a in operations:
            q2 = _adapt_query(q).replace('NOW()', f"'{_sqlite_now()}'")
            cur.execute(q2, list(a) if a else [])
        conn.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"SQLite transaction error: {e}")
        conn.rollback()
        return False


# ── Public API ──────────────────────────────────────────────
def query_db(query, args=None, one=False):
    backend = get_backend()
    if backend == 'postgresql':
        return _query_pg(query, args, one)
    if backend == 'mysql':
        return _query_mysql(query, args, one)
    return _query_sqlite(query, args, one)

def execute_db(query, args=None):
    backend = get_backend()
    if backend == 'postgresql':
        return _execute_pg(query, args)
    if backend == 'mysql':
        return _execute_mysql(query, args)
    return _execute_sqlite(query, args)

def execute_transaction(operations):
    backend = get_backend()
    if backend == 'postgresql':
        return _transaction_pg(operations)
    if backend == 'mysql':
        return _transaction_mysql(operations)
    return _transaction_sqlite(operations)


# ── Auto-initialization (for production deploys) ────────────
def init_database():
    """Create tables and seed demo data if the database is empty."""
    backend = get_backend()
    if backend == 'mysql':
        # MySQL: check if tables exist
        result = query_db("SHOW TABLES", one=True)
        if result is not None:
            return  # Already initialized

    elif backend == 'postgresql':
        # PostgreSQL: check if users table exists
        result = query_db(
            "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'users')",
            one=True
        )
        if result and result.get('exists'):
            return  # Already initialized
        _init_postgres()

    else:  # sqlite
        result = query_db("SELECT name FROM sqlite_master WHERE type='table' AND name='users'", one=True)
        if result:
            return  # Already initialized
        _init_sqlite()

    print("[database] Tables created and seeded successfully")


def _init_postgres():
    """Initialize PostgreSQL with tables and seed data using a single connection."""
    print("[database] Creating PostgreSQL tables...")
    tables = [
        """CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, name VARCHAR(150) NOT NULL, email VARCHAR(200) NOT NULL UNIQUE,
            mobile VARCHAR(15), voter_id VARCHAR(20) UNIQUE, password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL DEFAULT 'VOTER', status VARCHAR(20) NOT NULL DEFAULT 'active',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, last_login TIMESTAMP
        )""",
        "CREATE INDEX IF NOT EXISTS idx_users_email ON users(email)",
        "CREATE INDEX IF NOT EXISTS idx_users_voter_id ON users(voter_id)",
        """CREATE TABLE IF NOT EXISTS voter_profiles (
            id SERIAL PRIMARY KEY, user_id INT NOT NULL UNIQUE, dob DATE, gender VARCHAR(10),
            address TEXT, state VARCHAR(100), district VARCHAR(100), constituency VARCHAR(150),
            pincode VARCHAR(10), photo VARCHAR(255),
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS applications (
            id SERIAL PRIMARY KEY, user_id INT NOT NULL, application_type VARCHAR(30) NOT NULL,
            reference_number VARCHAR(30) NOT NULL UNIQUE, status VARCHAR(30) NOT NULL DEFAULT 'Submitted',
            submitted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, remarks TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS elections (
            id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, description TEXT,
            election_type VARCHAR(100), constituency VARCHAR(150),
            start_time TIMESTAMP NOT NULL, end_time TIMESTAMP NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'Draft',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )""",
        """CREATE TABLE IF NOT EXISTS candidates (
            id SERIAL PRIMARY KEY, election_id INT NOT NULL, name VARCHAR(150) NOT NULL,
            party_name VARCHAR(200), symbol VARCHAR(100), description TEXT, image VARCHAR(255),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS votes (
            id SERIAL PRIMARY KEY, election_id INT NOT NULL, voter_id INT NOT NULL,
            candidate_id INT NOT NULL, voted_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            reference_code VARCHAR(100) NOT NULL UNIQUE,
            FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
            FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
            UNIQUE (voter_id, election_id)
        )""",
        """CREATE TABLE IF NOT EXISTS polling_stations (
            id SERIAL PRIMARY KEY, name VARCHAR(200) NOT NULL, address TEXT NOT NULL,
            state VARCHAR(100), district VARCHAR(100), constituency VARCHAR(150),
            booth_number VARCHAR(50), capacity INT DEFAULT 500,
            accessibility VARCHAR(200), facilities TEXT
        )""",
        """CREATE TABLE IF NOT EXISTS grievances (
            id SERIAL PRIMARY KEY, user_id INT NOT NULL, reference_number VARCHAR(30) NOT NULL UNIQUE,
            category VARCHAR(30) NOT NULL, subject VARCHAR(200) NOT NULL, description TEXT NOT NULL,
            contact_info VARCHAR(200), status VARCHAR(20) NOT NULL DEFAULT 'Submitted',
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS notifications (
            id SERIAL PRIMARY KEY, user_id INT NOT NULL, title VARCHAR(200) NOT NULL,
            message TEXT NOT NULL, is_read BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )""",
        """CREATE TABLE IF NOT EXISTS audit_logs (
            id SERIAL PRIMARY KEY, user_id INT, action VARCHAR(100) NOT NULL,
            entity VARCHAR(100) NOT NULL, entity_id INT, ip_address VARCHAR(45),
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        )""",
    ]
    conn = _pg_connect()
    conn.autocommit = True
    cur = conn.cursor()
    for stmt in tables:
        try:
            cur.execute(stmt)
        except Exception as e:
            if 'already exists' not in str(e).lower():
                print(f"Table creation error: {e}")
    cur.close()
    conn.close()
    print("[database] PostgreSQL tables created")

    _seed_data_pg()


def _init_sqlite():
    """Initialize SQLite with seed data."""
    try:
        import sys
        sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
        from init_sqlite import main as seed_main
        seed_main()
        global _sqlite_conn
        _sqlite_conn = None
    except (OSError, PermissionError):
        print("[database] SQLite init skipped: read-only filesystem")


def _seed_data_pg():
    """Seed demo data into PostgreSQL using a single connection for speed."""
    from werkzeug.security import generate_password_hash

    admin_hash = generate_password_hash('gunu@2567')
    voter_hash = generate_password_hash('Voter@2026')

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    yesterday = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime('%Y-%m-%d %H:%M:%S')
    week_later = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime('%Y-%m-%d %H:%M:%S')

    conn = _pg_connect()
    conn.autocommit = True
    cur = conn.cursor()

    # Check if admin exists
    cur.execute("SELECT id FROM users WHERE email = 'adityagaikwad@2567'")
    if cur.fetchone():
        cur.close()
        conn.close()
        return  # Already seeded

    print("[database] Seeding PostgreSQL demo data...")

    # Users
    users = [
        ('System Administrator', 'adityagaikwad@2567', '9000000000', None, admin_hash, 'ADMIN', 'active'),
        ('Aditya Gaikwad', 'aditya@demo.local', '9100000001', 'DEMO100001', voter_hash, 'VOTER', 'active'),
        ('Aditi Naik', 'aditi@demo.local', '9100000002', 'DEMO100002', voter_hash, 'VOTER', 'active'),
        ('Rahul Sharma', 'rahul@demo.local', '9100000003', 'DEMO100003', voter_hash, 'VOTER', 'active'),
        ('Priya Patil', 'priya@demo.local', '9100000004', 'DEMO100004', voter_hash, 'VOTER', 'active'),
        ('Sneha Deshmukh', 'sneha@demo.local', '9100000005', 'DEMO100005', voter_hash, 'VOTER', 'active'),
        ('Election Officer', 'official@demo.local', '9000000099', None, voter_hash, 'ELECTION_OFFICIAL', 'active'),
    ]
    for u in users:
        cur.execute("INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", u)

    # Voter profiles
    profiles = [
        (2, '2004-05-15', 'Male', '123 Demo Street, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
        (3, '2004-08-22', 'Female', '456 Demo Nagar, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
        (4, '2003-12-10', 'Male', '789 Demo Road, Nagpur', 'Maharashtra', 'Nagpur', 'Demo Constituency North', '440001'),
        (5, '2004-03-08', 'Female', '321 Demo Colony, Pune', 'Maharashtra', 'Pune', 'Demo Constituency Central', '411001'),
        (6, '2004-01-25', 'Female', '654 Demo Lane, Mumbai', 'Maharashtra', 'Mumbai', 'Demo Constituency South', '400001'),
    ]
    for p in profiles:
        cur.execute("INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", p)

    # Polling stations
    stations = [
        ('Demo Government College', 'Example Road, Akola, Maharashtra', 'Maharashtra', 'Akola', 'Demo Constituency', 'Demo Booth 12', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk'),
        ('Demo Community Hall', 'Market Street, Nagpur, Maharashtra', 'Maharashtra', 'Nagpur', 'Demo Constituency North', 'Demo Booth 05', 400, 'Wheelchair Accessible', 'Drinking Water, Toilet'),
        ('Demo Public School', 'Station Road, Pune, Maharashtra', 'Maharashtra', 'Pune', 'Demo Constituency Central', 'Demo Booth 08', 350, 'Ramp Access', 'Drinking Water, Toilet'),
        ('Demo Municipal Building', 'Main Road, Mumbai, Maharashtra', 'Maharashtra', 'Mumbai', 'Demo Constituency South', 'Demo Booth 15', 600, 'Wheelchair Accessible', 'Drinking Water, Toilet, Parking'),
    ]
    for s in stations:
        cur.execute("INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", s)

    # Elections
    cur.execute("INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ('BCA Student Council Election 2026', 'Annual student council election for BCA department', 'Student Council', 'All Constituencies', yesterday, week_later, 'Active', now))
    cur.execute("INSERT INTO elections (name, description, election_type, constituency, start_time, end_time, status, created_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        ('BCA Cultural Committee 2025', 'Cultural committee election (completed)', 'Cultural Committee', 'All Constituencies', '2025-11-01 09:00:00', '2025-11-07 18:00:00', 'Completed', '2025-10-25 09:00:00'))

    # Candidates
    candidates = [
        (1, 'Aarav Mehta', 'BCA United', 'Star', 'Third-year BCA student'),
        (1, 'Sneha Kulkarni', 'Tech Forward', 'Laptop', 'Second-year BCA student'),
        (1, 'Vikram Patil', 'Student Voice', 'Megaphone', 'First-year BCA student'),
        (2, 'Priya Deshmukh', 'Arts Alliance', 'Palette', 'Cultural enthusiast'),
        (2, 'Rohan Gupta', 'Music Club', 'Note', 'Music lover'),
        (2, 'Neha Joshi', 'Drama Society', 'Masks', 'Drama enthusiast'),
    ]
    for c in candidates:
        cur.execute("INSERT INTO candidates (election_id, name, party_name, symbol, description, created_at) VALUES (%s, %s, %s, %s, %s, %s)", (*c, now))

    # Applications
    cur.execute("INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (2, 'correction', 'DEMO-2026-CORR000001', 'Submitted', '2026-08-20 10:00:00', '2026-08-20 10:00:00'))
    cur.execute("INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (3, 'new_registration', 'DEMO-2026-REG000002', 'Approved', '2026-02-01 10:00:00', '2026-02-15 10:00:00'))
    cur.execute("INSERT INTO applications (user_id, application_type, reference_number, status, submitted_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s)",
        (4, 'new_registration', 'DEMO-2026-REG000001', 'Approved', '2026-01-15 10:00:00', '2026-02-01 10:00:00'))

    # Audit logs, grievances, notifications
    for a in [
        (1, 'LOGIN', 'user', 1, '127.0.0.1', now),
        (3, 'LOGIN', 'user', 3, '127.0.0.1', '2026-08-26 09:30:00'),
        (2, 'LOGIN', 'user', 2, '127.0.0.1', '2026-08-26 09:00:00'),
        (1, 'ELECTION_CREATED', 'election', 1, '127.0.0.1', '2026-08-20 09:00:00'),
    ]:
        cur.execute("INSERT INTO audit_logs (user_id, action, entity, entity_id, ip_address, created_at) VALUES (%s, %s, %s, %s, %s, %s)", a)
    for g in [
        (2, 'DEMO-2026-GRV000001', 'voter_registration', 'Name Mismatch', 'My name shows incorrectly', 'aditya@demo.local', 'Submitted', now, now),
        (3, 'DEMO-2026-GRV000002', 'polling_station', 'Accessibility Issue', 'No wheelchair ramp', 'aditi@demo.local', 'Submitted', now, now),
        (4, 'DEMO-2026-GRV000003', 'application', 'Application Delay', 'Pending 2 weeks', 'rahul@demo.local', 'Submitted', now, now),
    ]:
        cur.execute("INSERT INTO grievances (user_id, reference_number, category, subject, description, contact_info, status, created_at, updated_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)", g)
    for n in [
        (2, 'Welcome', 'Account created successfully.', False, now),
        (3, 'Application Approved', 'Your registration is approved.', False, now),
        (1, 'System Update', 'Portal upgraded.', True, now),
    ]:
        cur.execute("INSERT INTO notifications (user_id, title, message, is_read, created_at) VALUES (%s, %s, %s, %s, %s)", n)

    cur.close()
    conn.close()
    print("[database] PostgreSQL seeded with demo data")
