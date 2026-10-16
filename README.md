# AcxiomCRM

A full-stack, enterprise-grade Customer Relationship Management (CRM) web application built with **Python Flask**, **MySQL**, **SQLAlchemy**, **Bootstrap 5**, and **Chart.js**.

Designed with clean, readable, beginner-friendly Python code that is easy to understand, explain, debug, and modify during practical coding assessments.

---

## Key Features & Implemented Modules

1. **Authentication & Account Security**
   - User Registration, Login, and Session Management using `Flask-Login`
   - Secure password hashing using Werkzeug (`generate_password_hash` / `check_password_hash`)
   - 8-character minimum password policy enforced server-side
   - Automated temporary account lockout after 5 consecutive failed login attempts (15-minute cooldown)
   - CSRF protection across state-changing forms using `Flask-WTF`
   - Secure session cookie configuration (`HttpOnly`, `SameSite=Lax`)

2. **Role-Based Access Control (RBAC)**
   - **Admin**: Full access across all CRM records, reporting, user management, and audit logs
   - **Manager**: Team-wide access across business records, pipeline, and reporting
   - **SalesExecutive**: Access restricted to assigned leads, opportunities, follow-ups, and created customers
   - Server-side role verification decorators (`@admin_required`, `@manager_or_admin_required`, `@role_required`)
   - Record-level permission checks preventing URL manipulation or unauthorized ID tampering

3. **Customer Management Module**
   - Full CRUD: Create, view details, update, delete
   - Search by name, company, email, phone, or customer code (`CUST-XXXX`)
   - Status filtering (Active, Inactive, Lead)
   - Server-side email and phone format and uniqueness validation
   - Associated opportunity, follow-up, and activity interaction history

4. **Lead Management & Conversion Workflow**
   - Full CRUD with lead statuses: `New`, `Contacted`, `Qualified`, `Unqualified`, `Converted`, `Lost`
   - Sequential lead codes (`LEAD-XXXX`)
   - 1-Click Lead Conversion workflow: converts a qualified lead into an active Customer and optionally creates a sales pipeline Opportunity without duplicate accounts
   - Assignment to sales representatives

5. **Opportunity & Sales Pipeline Module**
   - Stages: `Qualification`, `Proposal`, `Negotiation`, `Won`, `Lost`
   - Real-time calculation of **Weighted Pipeline Value**:
     $$\text{Weighted Value} = \frac{\text{Amount} \times \text{Probability}}{100}$$
   - Synchronized stage/status handling (Won = 100%, Lost = 0%)
   - Strict validation: amount must be positive; probability must be 0–100%; expected close date cannot be in the past for active deals

6. **Follow-up & Activity Tracking Modules**
   - Scheduled client calls, meetings, emails, and demos
   - Automatic identification and visual highlighting of **Overdue** follow-ups
   - Quick one-click status transitions (Planned $\to$ Completed $\to$ Cancelled)
   - Activity audit trail logging detailed meeting notes and client interaction minutes

7. **Executive Dashboard with 8 Real KPI Cards & 3 Chart.js Visualizations**
   - **8 Real Database KPIs**:
     1. Total Customers
     2. Total Leads
     3. Open Leads
     4. Total Opportunities
     5. Open Opportunities
     6. Won Opportunities
     7. Lost Opportunities
     8. Total Weighted Pipeline Value ($)
   - **Chart 1: Lead Status Distribution** (Doughnut chart with percentages)
   - **Chart 2: Opportunity Pipeline Stages** (Dual-axis bar chart showing deal volume & total dollar value)
   - **Chart 3: Monthly Sales / Opportunity Outcomes** (Historical comparison of Won vs. Lost revenues)
   - Real data calculated directly in Flask via SQLAlchemy and passed to Chart.js

8. **User & Role Administration (Admin Only)**
   - View all system users, registration dates, and security statuses
   - Edit user profile details and role assignments
   - Activate / deactivate accounts with self-deactivation protection
   - Administrative password reset capability

9. **Reporting & CSV Export Center**
   - Interactive report views for Opportunities, Leads, Customers, Follow-ups, and Activities
   - Sales representative filters for managers and administrators
   - One-click CSV dataset export

10. **Immutable Audit Logging**
    - Automatic recording of security events (login success, login failed, account locked) and business operations (created, updated, deleted)
    - Captures timestamp, user email, action, entity name, record ID, IP address, and JSON diffs of old vs. new values
    - Sensitive credentials (passwords, tokens, hashes) are strictly redacted
    - Read-only interface with search and entity filters; no modification or deletion endpoints

11. **REST API**
    - Full JSON endpoints with standard HTTP status codes (`200 OK`, `201 Created`, `400 Bad Request`, `401 Unauthorized`, `403 Forbidden`, `404 Not Found`):
      - `GET /api/customers`, `GET /api/customers/<id>`, `POST /api/customers`, `PUT /api/customers/<id>`, `DELETE /api/customers/<id>`
      - `GET /api/leads`, `GET /api/leads/<id>`, `POST /api/leads`, `PUT /api/leads/<id>`, `DELETE /api/leads/<id>`
      - `GET /api/opportunities`, `GET /api/opportunities/<id>`, `POST /api/opportunities`, `PUT /api/opportunities/<id>`, `DELETE /api/opportunities/<id>`
      - `GET /api/dashboard/stats`

---

## Technology Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12 / 3.13 |
| Framework | Flask 3.x |
| Database | MySQL 8.0 |
| ORM | Flask-SQLAlchemy / SQLAlchemy 2.x |
| Driver | PyMySQL + Cryptography |
| Authentication | Flask-Login |
| Form Validation & CSRF | Flask-WTF / WTForms |
| UI Framework | Bootstrap 5.3 + Bootstrap Icons |
| Dashboard Charts | Chart.js 4.4 |
| Environment Config | python-dotenv |
| Testing | pytest |

---

## Directory Structure

```text
AcxiomCRM/
├── app.py                  # Application factory, blueprint registrations, error handlers
├── config.py               # Config classes loading from .env
├── models.py               # SQLAlchemy models (User, Customer, Lead, Opportunity, FollowUp, Activity, AuditLog)
├── forms.py                # Flask-WTF form classes with server-side validators
├── helpers.py              # RBAC decorators, record ownership check, audit logging helper
├── requirements.txt        # Python dependency manifest
├── pytest.ini              # Pytest configuration
├── .env                    # Local environment variables
├── .env.example            # Environment configuration template
├── .gitignore              # Git ignore rules
├── README.md               # Setup and project documentation
├── ASSESSMENT_GUIDE.md     # Beginner-friendly exam and modification guide
├── routes/
│   ├── auth.py             # Login, logout, register, lockout logic
│   ├── main.py             # Dashboard KPIs, chart analytics aggregation
│   ├── customers.py        # Customer CRUD and search
│   ├── leads.py            # Lead CRUD and conversion workflow
│   ├── opportunities.py    # Opportunity pipeline and weighted value
│   ├── followups.py        # Follow-up scheduling and overdue tracking
│   ├── activities.py       # Activity logging and interaction history
│   ├── users.py            # Admin user and role management
│   ├── reports.py          # Tabular business reports and CSV exports
│   ├── audit.py            # Audit log inspection
│   └── api.py              # REST API JSON endpoints
├── templates/
│   ├── base.html           # Master layout with responsive navbar and footer
│   ├── login.html          # Login card
│   ├── register.html       # Self-registration
│   ├── dashboard.html      # 8 KPI cards, 3 Chart.js charts
│   ├── customers.html      # Customer directory
│   ├── customer_form.html  # Create/edit customer
│   ├── customer_detail.html# Customer profile and linked deals
│   ├── leads.html          # Leads directory
│   ├── lead_form.html      # Create/edit lead
│   ├── lead_detail.html    # Lead detail view
│   ├── lead_convert.html   # Lead conversion wizard
│   ├── opportunities.html  # Pipeline list
│   ├── opportunity_form.html # Create/edit deal
│   ├── opportunity_detail.html # Opportunity financials
│   ├── followups.html      # Follow-up tracking
│   ├── followup_form.html  # Schedule follow-up
│   ├── activities.html     # Activity history
│   ├── activity_form.html  # Log activity
│   ├── users.html          # User administration
│   ├── user_form.html      # Edit user profile and role
│   ├── reports.html        # Reporting tabs & CSV export
│   ├── audit_logs.html     # Audit logs table & payload viewer
│   └── errors/             # 403, 404, 500 error pages
├── static/
│   ├── css/
│   │   └── style.css       # Custom styling, KPI cards, badges
│   └── js/
│       └── dashboard.js    # Chart.js initialization script
├── scripts/
│   └── init_db.py          # Database creation, admin setup, sample data seeding
└── tests/
    └── test_app.py         # Automated pytest suite
```

---

## Installation & Setup Instructions

### 1. Prerequisites
- Python 3.10+ installed
- MySQL 8.0 running locally on port 3306

### 2. Configure Environment (`.env`)
Create a `.env` file in the root folder (or copy from `.env.example`):

```bash
FLASK_ENV=development
FLASK_DEBUG=1
SECRET_KEY=your_secure_random_flask_secret_key

# MySQL Connection String
DATABASE_URL=mysql+pymysql://root:root@localhost:3306/acxiom_crm

MAX_LOGIN_ATTEMPTS=5
LOCKOUT_MINUTES=15
```

### 3. Set Up Virtual Environment & Dependencies

In Windows PowerShell:
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install requirements
pip install -r requirements.txt
```

### 4. Initialize MySQL Database & Seed Accounts

Make sure MySQL service is running, then run the initialization script:
```powershell
python scripts/init_db.py
```
This script will:
1. Connect to MySQL and create all required tables.
2. Create default administrative and testing accounts:
   - **Admin**: `admin@acxiom.com` / `AdminPassword123!`
   - **Manager**: `manager@acxiom.com` / `ManagerPassword123!`
   - **Sales Executive**: `sales@acxiom.com` / `SalesPassword123!`
3. Seed realistic customer, lead, deal, follow-up, and activity data.

*(To initialize tables without seeding sample data, run `python scripts/init_db.py --no-seed`)*

### 5. Run the Application

```powershell
python app.py
```
Open your browser and navigate to:
```text
http://127.0.0.1:5000
```

---

## Running Automated Tests

Run the full automated test suite using `pytest`:

```powershell
pytest -v
```

All 10 tests verify:
- Werkzeug password hashing
- Self-registration with default `SalesExecutive` role
- Minimum 8-character password enforcement
- Login, session protection, and logout
- 5-attempt automated account lockout
- Customer CRUD and duplicate prevention
- Lead conversion into customer and deal
- Opportunity weighted value calculation ($Amount \times Probability / 100$)
- REST API customer endpoints (GET, POST, PUT, DELETE)
- Audit log entry creation and credential redaction
