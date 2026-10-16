"""
Database initialization and seeding script for AcxiomCRM.
Creates all required MySQL tables and safely seeds the initial Admin account
and demonstrative records for testing and assessment.
"""
import sys
import os
from datetime import datetime, timedelta, date

# Add parent directory to path so models and config can be imported
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import create_app
from models import db, User, Customer, Lead, Opportunity, FollowUp, Activity, AuditLog

def init_db(seed=True):
    app = create_app()
    with app.app_context():
        print("Connecting to database and creating tables...")
        db.create_all()
        print("Tables created successfully.")

        # Check if an Admin user already exists
        admin = User.query.filter_by(role='Admin').first()
        if not admin:
            print("Creating default administrative accounts...")
            
            # 1. Admin
            admin = User(
                name="System Administrator",
                email="admin@acxiom.com",
                role="Admin",
                is_active=True
            )
            admin.set_password("AdminPassword123!")
            db.session.add(admin)

            # 2. Manager
            manager = User(
                name="Sarah Jenkins",
                email="manager@acxiom.com",
                role="Manager",
                is_active=True
            )
            manager.set_password("ManagerPassword123!")
            db.session.add(manager)

            # 3. Sales Executive
            sales = User(
                name="Alex Rivera",
                email="sales@acxiom.com",
                role="SalesExecutive",
                is_active=True
            )
            sales.set_password("SalesPassword123!")
            db.session.add(sales)

            db.session.commit()
            print("Admin (admin@acxiom.com / AdminPassword123!) created.")
            print("Manager (manager@acxiom.com / ManagerPassword123!) created.")
            print("Sales Executive (sales@acxiom.com / SalesPassword123!) created.")

            # Record initial audit entry
            log = AuditLog(
                user_id=admin.id,
                user_email=admin.email,
                action="SYSTEM_INIT",
                entity_name="Database",
                record_id="0",
                new_values='{"info": "Initial database created and seeded"}',
                ip_address="127.0.0.1"
            )
            db.session.add(log)
            db.session.commit()

        if seed and Customer.query.count() == 0:
            print("Seeding sample business data for dashboard metrics and charts...")
            admin = User.query.filter_by(email="admin@acxiom.com").first()
            sales = User.query.filter_by(email="sales@acxiom.com").first()
            manager = User.query.filter_by(email="manager@acxiom.com").first()

            # Seed Customers
            c1 = Customer(
                customer_code="CUST-1001",
                name="Apex Global Technologies",
                email="contact@apextech.com",
                phone="+1-555-0101",
                company_name="Apex Global Tech Ltd.",
                address="100 Silicon Way",
                city="San Jose",
                state="California",
                status="Active",
                created_by_id=sales.id
            )
            c2 = Customer(
                customer_code="CUST-1002",
                name="Horizon Financial Group",
                email="accounts@horizonfin.com",
                phone="+1-555-0102",
                company_name="Horizon Capital Corp",
                address="45 Wall Street",
                city="New York",
                state="New York",
                status="Active",
                created_by_id=sales.id
            )
            c3 = Customer(
                customer_code="CUST-1003",
                name="Vanguard Logistics",
                email="info@vanguardlog.com",
                phone="+1-555-0103",
                company_name="Vanguard Logistics Services",
                address="88 Harbor Blvd",
                city="Chicago",
                state="Illinois",
                status="Active",
                created_by_id=manager.id
            )
            db.session.add_all([c1, c2, c3])
            db.session.commit()

            # Seed Leads
            l1 = Lead(
                lead_code="LEAD-2001",
                name="David Miller",
                email="david@nexussoftware.io",
                phone="+1-555-0201",
                company_name="Nexus Software",
                source="Website",
                status="New",
                expected_value=15000.00,
                assigned_user_id=sales.id
            )
            l2 = Lead(
                lead_code="LEAD-2002",
                name="Elena Rostova",
                email="elena@stellarbiotech.com",
                phone="+1-555-0202",
                company_name="Stellar Biotech",
                source="Referral",
                status="Qualified",
                expected_value=45000.00,
                assigned_user_id=sales.id
            )
            l3 = Lead(
                lead_code="LEAD-2003",
                name="Marcus Vance",
                email="marcus@orbitconsulting.org",
                phone="+1-555-0203",
                company_name="Orbit Consulting",
                source="Social Media",
                status="Contacted",
                expected_value=12000.00,
                assigned_user_id=manager.id
            )
            l4 = Lead(
                lead_code="LEAD-2004",
                name="Clara Oswald",
                email="clara@tardisenterprises.uk",
                phone="+1-555-0204",
                company_name="Tardis Enterprises",
                source="Cold Call",
                status="Lost",
                expected_value=8000.00,
                assigned_user_id=sales.id
            )
            db.session.add_all([l1, l2, l3, l4])
            db.session.commit()

            # Seed Opportunities
            today = date.today()
            o1 = Opportunity(
                name="Enterprise Cloud Migration",
                customer_id=c1.id,
                amount=75000.00,
                stage="Negotiation",
                probability=80,
                expected_close_date=today + timedelta(days=25),
                status="Open",
                assigned_user_id=sales.id
            )
            o2 = Opportunity(
                name="Security Audit & Compliance Retainer",
                customer_id=c2.id,
                amount=35000.00,
                stage="Proposal",
                probability=50,
                expected_close_date=today + timedelta(days=40),
                status="Open",
                assigned_user_id=sales.id
            )
            o3 = Opportunity(
                name="Automated Supply Chain Integration",
                customer_id=c3.id,
                amount=120000.00,
                stage="Won",
                probability=100,
                expected_close_date=today - timedelta(days=10),
                status="Won",
                assigned_user_id=manager.id
            )
            o4 = Opportunity(
                name="Legacy ERP Modernization",
                customer_id=c1.id,
                amount=50000.00,
                stage="Lost",
                probability=0,
                expected_close_date=today - timedelta(days=15),
                status="Lost",
                assigned_user_id=sales.id
            )
            o5 = Opportunity(
                name="Data Analytics Platform License",
                customer_id=c2.id,
                amount=28000.00,
                stage="Qualification",
                probability=20,
                expected_close_date=today + timedelta(days=60),
                status="Open",
                assigned_user_id=sales.id
            )
            db.session.add_all([o1, o2, o3, o4, o5])
            db.session.commit()

            # Seed FollowUps
            now = datetime.utcnow()
            f1 = FollowUp(
                customer_id=c1.id,
                followup_date=now + timedelta(days=2),
                followup_type="Call",
                remarks="Review contract amendments and discount terms with procurement",
                status="Planned",
                assigned_user_id=sales.id
            )
            f2 = FollowUp(
                lead_id=l2.id,
                followup_date=now + timedelta(days=1),
                followup_type="Meeting",
                remarks="Technical demo of CRM analytics for VP of Operations",
                status="Planned",
                assigned_user_id=sales.id
            )
            f3 = FollowUp(
                customer_id=c2.id,
                followup_date=now - timedelta(days=1),
                followup_type="Email",
                remarks="Send compliance security whitepaper",
                status="Pending",  # Overdue
                assigned_user_id=sales.id
            )
            db.session.add_all([f1, f2, f3])

            # Seed Activities
            a1 = Activity(
                activity_type="Call",
                subject="Introductory Discovery Call",
                description="Discussed current pain points in legacy CRM and requirements for API integration.",
                activity_date=now - timedelta(days=3),
                customer_id=c1.id,
                assigned_user_id=sales.id,
                status="Completed"
            )
            a2 = Activity(
                activity_type="Meeting",
                subject="Architecture & Security Review",
                description="Addressed data residency and SSO questions with IT Director.",
                activity_date=now - timedelta(days=2),
                customer_id=c2.id,
                assigned_user_id=manager.id,
                status="Completed"
            )
            a3 = Activity(
                activity_type="Task",
                subject="Prepare Custom Proposal Deck",
                description="Draft customized quote covering 100 enterprise user seats.",
                activity_date=now + timedelta(days=1),
                lead_id=l2.id,
                assigned_user_id=sales.id,
                status="In Progress"
            )
            db.session.add_all([a1, a2, a3])
            db.session.commit()
            print("Sample business data seeded successfully.")

if __name__ == '__main__':
    seed_arg = '--no-seed' not in sys.argv
    init_db(seed=seed_arg)
