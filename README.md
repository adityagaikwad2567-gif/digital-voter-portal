# Digital Voter Services & Online Voting Portal

> **Academic Demonstration Project — Not an Official Government Website**

A complete, functional, responsive full-stack Indian Voter Services and Controlled Online Voting Portal built as an academic BCA 2nd Year project using the Waterfall Model.

## Project Information

| Field | Detail |
|-------|--------|
| **Project Name** | Digital Voter Services & Online Voting Portal |
| **Students** | Aditya Gaikwad & Aditi Naik |
| **Course** | Bachelor of Computer Applications (BCA) |
| **Year** | Second Year |
| **Development Model** | Waterfall Model |

## Features

### Voter Services
- New Voter Registration (Multi-step form)
- Search Electoral Roll
- Find Polling Station
- Digital Voter Card (Demo)
- Update / Correction Requests
- Address Transfer
- Application Tracking
- Eligibility Checker

### Elections
- Election Listing (Active / Upcoming / Completed)
- Election Schedule Timeline
- Candidate Directory with Details
- Election Results with Charts (Chart.js)

### Online Voting
- Secure Voter Login
- Active Election Viewing
- Cast Vote (Step-by-step)
- Vote Confirmation
- Duplicate Vote Prevention
- Voting History

### Grievances
- Submit Grievance
- Track Grievance Status

### Information Pages
- How to Vote Guide
- Eligibility Information
- Documents Required
- FAQ
- Contact / Help
- About the Project
- Privacy Policy
- Terms of Use

### Administration
- Admin Dashboard with Charts
- Voter Management (Add / Edit / Deactivate)
- Application Management (Approve / Reject / Request Info)
- Election Management (Create / Edit / Activate / Close)
- Candidate Management
- Polling Station Management
- Grievance Management
- Notification System
- Audit Logs
- CSV Report Export
- System Settings

### Security
- Werkzeug Password Hashing
- Flask-Login Session Management
- Flask-WTF CSRF Protection
- Role-based Authorization (Admin / Election Official / Voter)
- Server-side Input Validation
- SQL Injection Prevention (Parameterized Queries)
- Duplicate Vote Prevention (Application + DB Level)

## Technology Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | HTML5, CSS3, Bootstrap 5, JavaScript, Bootstrap Icons, Chart.js |
| **Backend** | Python 3, Flask |
| **Database** | MySQL |
| **Security** | Werkzeug, Flask-Login, Flask-WTF |

## Project Structure

```
digital-voter-portal/
│
├── app.py                      # Application entry point + demo data seeder
├── config.py                   # Configuration settings
├── requirements.txt            # Python dependencies
├── .env.example                # Environment variables template
├── README.md
│
├── database/
│   └── schema.sql              # MySQL database schema
│
├── app/
│   ├── __init__.py             # Flask app factory
│   ├── models/
│   │   └── user.py             # User model (Flask-Login)
│   ├── routes/
│   │   ├── main.py             # Homepage
│   │   ├── auth.py             # Login / Register / Logout
│   │   ├── voter.py            # Voter services
│   │   ├── elections.py        # Election pages
│   │   ├── voting.py           # Online voting
│   │   ├── grievances.py       # Grievance submission
│   │   ├── info.py             # Information pages
│   │   ├── admin.py            # Admin dashboard
│   │   └── errors.py           # Error handlers
│   ├── services/
│   │   └── db_operations.py    # Database operations
│   └── utils/
│       ├── database.py         # MySQL connection helper
│       ├── helpers.py          # Utility functions
│       └── translations.py     # Multi-language framework
│
├── templates/
│   ├── base.html               # Base template with navigation
│   ├── index.html              # Homepage
│   ├── auth/                   # Login, Register
│   ├── voter/                  # Dashboard, Registration, Search, etc.
│   ├── elections/              # Election list, Detail, Candidates, Results
│   ├── voting/                 # Cast vote, Confirm, History
│   ├── grievances/             # Submit, Track
│   ├── info/                   # How to vote, FAQ, About, etc.
│   ├── admin/                  # Admin dashboard and management
│   └── errors/                 # 400, 401, 403, 404, 429, 500
│
└── static/
    ├── css/style.css           # Custom styles
    └── js/main.js              # JavaScript utilities
```

## Installation

### Prerequisites
- Python 3.8+
- MySQL 5.7+ or MariaDB 10.3+
- pip (Python package manager)

### Steps

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd digital-voter-portal
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   ```

3. **Activate virtual environment**
   ```bash
   # Windows
   venv\Scripts\activate

   # macOS/Linux
   source venv/bin/activate
   ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Create MySQL database**
   ```sql
   CREATE DATABASE digital_voter_portal;
   ```

6. **Import schema**
   ```bash
   mysql -u root -p digital_voter_portal < database/schema.sql
   ```

7. **Configure environment**
   ```bash
   cp .env.example .env
   ```
   Edit `.env` with your MySQL credentials and a secure Flask secret key.

8. **Run the application**
   ```bash
   python app.py
   ```

9. **Open in browser**
   ```
   http://127.0.0.1:5000
   ```

## Demo Credentials

| Role | Email | Password |
|------|-------|----------|
| **Admin** | admin@demo.local | Admin@12345 |
| **Voter** | aditya@demo.local | Demo@12345 |
| **Voter** | aditi@demo.local | Demo@12345 |
| **Voter** | rahul@demo.local | Demo@12345 |
| **Voter** | priya@demo.local | Demo@12345 |
| **Voter** | sneha@demo.local | Demo@12345 |
| **Election Official** | official@demo.local | Official@12345 |

## Database Schema

### Tables
- **users** — User accounts with roles
- **voter_profiles** — Voter personal and address details
- **applications** — Registration, correction, and transfer applications
- **elections** — Election definitions
- **candidates** — Candidates for each election
- **votes** — Cast votes (with unique voter+election constraint)
- **polling_stations** — Demo polling station data
- **grievances** — User grievances
- **notifications** — System notifications
- **audit_logs** — Action audit trail

## Security Features

- Passwords hashed with Werkzeug (pbkdf2:sha256)
- CSRF tokens on all forms
- Parameterized SQL queries (no string interpolation)
- Role-based access control (Admin / Election Official / Voter)
- Session cookies: HttpOnly, SameSite=Lax
- Server-side input validation
- Duplicate vote prevention (application + UNIQUE constraint)
- Audit logging of sensitive actions

## Waterfall Model

This project follows the Waterfall methodology:

1. **Requirement Analysis** — Documented functional and non-functional requirements
2. **System Design** — Database ER diagram, system architecture, UI wireframes
3. **Implementation** — Flask backend, MySQL database, Bootstrap frontend
4. **Testing** — Unit tests, integration tests, security tests, UAT
5. **Deployment** — Local development server, documentation
6. **Maintenance** — Bug fixes, feature enhancements

## Academic Disclaimer

This application is an **academic demonstration project** developed for educational purposes. It is:

- ❌ NOT an official Election Commission of India website
- ❌ NOT connected to any government database
- ❌ NOT a legally valid voting system
- ❌ NOT using real citizen data
- ✅ Using fictional demo data only
- ✅ Original design (not copied from ECI)
- ✅ Clearly labeled as academic project

## Limitations

- Uses SQLite/MySQL with demo data (not production-grade)
- Online voting is for demonstration only
- No real OTP verification
- No real document upload validation
- Single-server deployment only

## Future Scope

- Real OTP integration (Twilio / MSG91)
- Aadhaar-based verification (demo/simulation)
- PDF voter card generation
- Email notifications
- Real-time election monitoring
- Multi-language support (Hindi, Marathi)
- Mobile responsive PWA
- Docker deployment
- CI/CD pipeline

## Team Members

| Name | Role |
|------|------|
| **Aditya Gaikwad** | BCA 2nd Year — Developer |
| **Aditi Naik** | BCA 2nd Year — Developer |

## License

This is an academic project. For educational use only.

---

*Built with ❤️ using Python, Flask, MySQL, Bootstrap, and JavaScript*
