-- Digital Voter Services & Online Voting Portal
-- Academic Demonstration Project - MySQL Schema
-- Students: Aditya Gaikwad & Aditi Naik

CREATE DATABASE IF NOT EXISTS digital_voter_portal
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE digital_voter_portal;

-- ─── Users Table ────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(150) NOT NULL,
    email VARCHAR(200) NOT NULL UNIQUE,
    mobile VARCHAR(15),
    voter_id VARCHAR(20) UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('VOTER', 'ADMIN', 'ELECTION_OFFICIAL') NOT NULL DEFAULT 'VOTER',
    status ENUM('active', 'inactive', 'suspended') NOT NULL DEFAULT 'active',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    INDEX idx_users_email (email),
    INDEX idx_users_voter_id (voter_id),
    INDEX idx_users_role (role)
) ENGINE=InnoDB;

-- ─── Voter Profiles ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS voter_profiles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL UNIQUE,
    dob DATE,
    gender ENUM('Male', 'Female', 'Other'),
    address TEXT,
    state VARCHAR(100),
    district VARCHAR(100),
    constituency VARCHAR(150),
    pincode VARCHAR(10),
    photo VARCHAR(255),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_vp_district (district),
    INDEX idx_vp_state (state),
    INDEX idx_vp_constituency (constituency)
) ENGINE=InnoDB;

-- ─── Applications ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS applications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    application_type ENUM('new_registration', 'correction', 'address_transfer') NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    status ENUM('Submitted', 'Documents Received', 'Under Review', 'Verification', 'Approved', 'Rejected', 'More Information Required') NOT NULL DEFAULT 'Submitted',
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    remarks TEXT,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_app_ref (reference_number),
    INDEX idx_app_status (status),
    INDEX idx_app_type (application_type)
) ENGINE=InnoDB;

-- ─── Elections ──────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS elections (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    description TEXT,
    election_type VARCHAR(100),
    constituency VARCHAR(150),
    start_time DATETIME NOT NULL,
    end_time DATETIME NOT NULL,
    status ENUM('Draft', 'Upcoming', 'Active', 'Completed', 'Cancelled') NOT NULL DEFAULT 'Draft',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_election_status (status),
    INDEX idx_election_dates (start_time, end_time)
) ENGINE=InnoDB;

-- ─── Candidates ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS candidates (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    name VARCHAR(150) NOT NULL,
    party_name VARCHAR(200),
    symbol VARCHAR(100),
    description TEXT,
    image VARCHAR(255),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    INDEX idx_candidate_election (election_id)
) ENGINE=InnoDB;

-- ─── Votes ──────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS votes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    election_id INT NOT NULL,
    voter_id INT NOT NULL,
    candidate_id INT NOT NULL,
    voted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    reference_code VARCHAR(100) NOT NULL UNIQUE,
    FOREIGN KEY (election_id) REFERENCES elections(id) ON DELETE CASCADE,
    FOREIGN KEY (voter_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (candidate_id) REFERENCES candidates(id) ON DELETE CASCADE,
    UNIQUE KEY unique_voter_election (voter_id, election_id),
    INDEX idx_votes_election (election_id),
    INDEX idx_votes_candidate (candidate_id)
) ENGINE=InnoDB;

-- ─── Polling Stations ───────────────────────────────────────
CREATE TABLE IF NOT EXISTS polling_stations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    address TEXT NOT NULL,
    state VARCHAR(100),
    district VARCHAR(100),
    constituency VARCHAR(150),
    booth_number VARCHAR(50),
    capacity INT DEFAULT 500,
    accessibility VARCHAR(200),
    facilities TEXT,
    INDEX idx_ps_district (district),
    INDEX idx_ps_constituency (constituency)
) ENGINE=InnoDB;

-- ─── Grievances ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS grievances (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    reference_number VARCHAR(30) NOT NULL UNIQUE,
    category ENUM('voter_registration', 'application', 'voter_information', 'polling_station', 'digital_card', 'election', 'technical_issue', 'other') NOT NULL,
    subject VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    contact_info VARCHAR(200),
    status ENUM('Submitted', 'In Progress', 'Resolved', 'Closed') NOT NULL DEFAULT 'Submitted',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_grv_ref (reference_number),
    INDEX idx_grv_status (status)
) ENGINE=InnoDB;

-- ─── Notifications ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    message TEXT NOT NULL,
    is_read TINYINT(1) NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_notif_user (user_id),
    INDEX idx_notif_read (is_read)
) ENGINE=InnoDB;

-- ─── Audit Logs ─────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS audit_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    action VARCHAR(100) NOT NULL,
    entity VARCHAR(100) NOT NULL,
    entity_id INT,
    ip_address VARCHAR(45),
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL,
    INDEX idx_audit_user (user_id),
    INDEX idx_audit_action (action),
    INDEX idx_audit_entity (entity),
    INDEX idx_audit_date (created_at)
) ENGINE=InnoDB;

-- ─── Demo Data ──────────────────────────────────────────────

-- Admin user (password: Admin@12345)
INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status)
VALUES ('System Administrator', 'admin@demo.local', '9000000000', NULL,
        'scrypt:32768:8:1$dummy$placeholder', 'ADMIN', 'active');

-- Demo voters (password: Demo@12345)
INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status)
VALUES
('Aditya Gaikwad', 'aditya@demo.local', '9100000001', 'DEMO100001',
 'scrypt:32768:8:1$dummy$placeholder', 'VOTER', 'active'),
('Aditi Naik', 'aditi@demo.local', '9100000002', 'DEMO100002',
 'scrypt:32768:8:1$dummy$placeholder', 'VOTER', 'active'),
('Rahul Sharma', 'rahul@demo.local', '9100000003', 'DEMO100003',
 'scrypt:32768:8:1$dummy$placeholder', 'VOTER', 'active'),
('Priya Patil', 'priya@demo.local', '9100000004', 'DEMO100004',
 'scrypt:32768:8:1$dummy$placeholder', 'VOTER', 'active'),
('Sneha Deshmukh', 'sneha@demo.local', '9100000005', 'DEMO100005',
 'scrypt:32768:8:1$dummy$placeholder', 'VOTER', 'active');

-- Demo voter profiles
INSERT INTO voter_profiles (user_id, dob, gender, address, state, district, constituency, pincode)
VALUES
(2, '2004-05-15', 'Male', '123 Demo Street, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
(3, '2004-08-22', 'Female', '456 Demo Nagar, Akola', 'Maharashtra', 'Akola', 'Demo Constituency', '444001'),
(4, '2003-12-10', 'Male', '789 Demo Road, Nagpur', 'Maharashtra', 'Nagpur', 'Demo Constituency North', '440001'),
(5, '2004-03-08', 'Female', '321 Demo Colony, Pune', 'Maharashtra', 'Pune', 'Demo Constituency Central', '411001'),
(6, '2004-01-25', 'Female', '654 Demo Lane, Mumbai', 'Maharashtra', 'Mumbai', 'Demo Constituency South', '400001');

-- Election official
INSERT INTO users (name, email, mobile, voter_id, password_hash, role, status)
VALUES ('Election Officer', 'official@demo.local', '9000000099', NULL,
        'scrypt:32768:8:1$dummy$placeholder', 'ELECTION_OFFICIAL', 'active');

-- Demo polling stations
INSERT INTO polling_stations (name, address, state, district, constituency, booth_number, capacity, accessibility, facilities)
VALUES
('Demo Government College', 'Example Road, Akola, Maharashtra', 'Maharashtra', 'Akola', 'Demo Constituency', 'Demo Booth 12', 500, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area'),
('Demo Community Hall', 'Market Street, Nagpur, Maharashtra', 'Maharashtra', 'Nagpur', 'Demo Constituency North', 'Demo Booth 05', 400, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk'),
('Demo Public School', 'Station Road, Pune, Maharashtra', 'Maharashtra', 'Pune', 'Demo Constituency Central', 'Demo Booth 08', 350, 'Ramp Access', 'Drinking Water, Toilet, Waiting Area'),
('Demo Municipal Building', 'Main Road, Mumbai, Maharashtra', 'Maharashtra', 'Mumbai', 'Demo Constituency South', 'Demo Booth 15', 600, 'Wheelchair Accessible', 'Drinking Water, Toilet, Help Desk, Waiting Area, Parking');
