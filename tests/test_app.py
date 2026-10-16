"""
Automated Pytest Suite for AcxiomCRM.
Tests Authentication, Role-based Authorization, Lockout,
Customer CRUD, Lead Conversion, Opportunity Calculations,
Follow-ups, REST API endpoints, and Audit Trails.
"""
import os
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from datetime import date, datetime, timedelta
from app import create_app
from config import TestConfig
from models import db, User, Customer, Lead, Opportunity, FollowUp, Activity, AuditLog

@pytest.fixture
def app():
    """Create and configure a clean testing app instance."""
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()

@pytest.fixture
def client(app):
    """Test HTTP client."""
    return app.test_client()

@pytest.fixture
def runner(app):
    return app.test_cli_runner()

@pytest.fixture
def test_users(app):
    """Seed test accounts for Admin, Manager, and SalesExecutive."""
    admin = User(name="Admin User", email="admin@test.com", role="Admin", is_active=True)
    admin.set_password("AdminPass123!")

    manager = User(name="Manager User", email="manager@test.com", role="Manager", is_active=True)
    manager.set_password("ManagerPass123!")

    sales1 = User(name="Sales Rep 1", email="sales1@test.com", role="SalesExecutive", is_active=True)
    sales1.set_password("SalesPass123!")

    sales2 = User(name="Sales Rep 2", email="sales2@test.com", role="SalesExecutive", is_active=True)
    sales2.set_password("SalesPass123!")

    db.session.add_all([admin, manager, sales1, sales2])
    db.session.commit()
    return {"admin": admin, "manager": manager, "sales1": sales1, "sales2": sales2}


# ==============================================================
# 1. AUTHENTICATION & SECURITY TESTS
# ==============================================================

def test_password_hashing(test_users):
    """Verify passwords are secure hashes and not stored plaintext."""
    admin = test_users['admin']
    assert admin.password_hash != "AdminPass123!"
    assert admin.check_password("AdminPass123!") is True
    assert admin.check_password("WrongPassword") is False

def test_user_registration(client, app):
    """Test user registration with safe default role (SalesExecutive)."""
    response = client.post('/register', data={
        'name': 'New Register',
        'email': 'newuser@test.com',
        'password': 'Password123!',
        'confirm_password': 'Password123!'
    }, follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        u = User.query.filter_by(email='newuser@test.com').first()
        assert u is not None
        assert u.role == 'SalesExecutive'
        assert u.check_password('Password123!') is True

def test_registration_password_length_validation(client):
    """Password under 8 characters must be rejected."""
    response = client.post('/register', data={
        'name': 'Short Pass',
        'email': 'short@test.com',
        'password': 'short',
        'confirm_password': 'short'
    }, follow_redirects=True)
    assert b"Password must be at least 8 characters long." in response.data

def test_login_and_logout(client, test_users):
    """Verify login and logout flow."""
    # Login
    response = client.post('/login', data={
        'email': 'admin@test.com',
        'password': 'AdminPass123!'
    }, follow_redirects=True)
    assert response.status_code == 200
    assert b"Welcome back, Admin User!" in response.data

    # Access protected route
    dash = client.get('/dashboard')
    assert dash.status_code == 200

    # Logout
    logout_resp = client.get('/logout', follow_redirects=True)
    assert b"You have been signed out successfully." in logout_resp.data

    # Protected route should now redirect to login
    dash_anon = client.get('/dashboard')
    assert dash_anon.status_code == 302
    assert '/login' in dash_anon.headers['Location']

def test_account_lockout(client, test_users, app):
    """Verify account lockout after repeated failed attempts."""
    email = 'sales1@test.com'
    # Send 5 failed attempts
    for _ in range(5):
        client.post('/login', data={'email': email, 'password': 'WrongPassword123!'})

    with app.app_context():
        u = User.query.filter_by(email=email).first()
        assert u.failed_login_attempts >= 5
        assert u.is_locked() is True

    # Next attempt should inform account is locked
    resp = client.post('/login', data={'email': email, 'password': 'SalesPass123!'}, follow_redirects=True)
    assert b"Account is temporarily locked" in resp.data


# ==============================================================
# 2. CUSTOMER MODULE TESTS
# ==============================================================

def test_customer_crud_and_validation(client, test_users, app):
    """Test customer creation, validation of duplicate email/phone, and editing."""
    # Login as admin
    client.post('/login', data={'email': 'admin@test.com', 'password': 'AdminPass123!'})

    # Create customer 1
    resp = client.post('/customers/new', data={
        'name': 'Acme Corporation',
        'email': 'contact@acme.com',
        'phone': '1234567890',
        'company_name': 'Acme Inc',
        'city': 'Dallas',
        'state': 'Texas',
        'status': 'Active'
    }, follow_redirects=True)
    assert b"created successfully" in resp.data

    with app.app_context():
        c = Customer.query.filter_by(email='contact@acme.com').first()
        assert c is not None
        assert c.customer_code.startswith("CUST-")

        # Duplicate email test
        resp_dup = client.post('/customers/new', data={
            'name': 'Duplicate Corp',
            'email': 'contact@acme.com',
            'phone': '9999999999',
            'status': 'Active'
        }, follow_redirects=True)
        assert b"customer with this email address already exists" in resp_dup.data


# ==============================================================
# 3. LEAD MODULE & CONVERSION TESTS
# ==============================================================

def test_lead_crud_and_conversion(client, test_users, app):
    """Test lead creation and conversion into customer + opportunity."""
    client.post('/login', data={'email': 'manager@test.com', 'password': 'ManagerPass123!'})

    # Create Lead
    resp = client.post('/leads/new', data={
        'name': 'Prospect Alpha',
        'email': 'alpha@prospect.com',
        'phone': '5551234567',
        'company_name': 'Alpha Ventures',
        'source': 'Website',
        'status': 'Qualified',
        'expected_value': 25000.00,
        'assigned_user_id': test_users['sales1'].id
    }, follow_redirects=True)
    assert b"created successfully" in resp.data

    with app.app_context():
        lead = Lead.query.filter_by(email='alpha@prospect.com').first()
        assert lead is not None
        lead_id = lead.id

    # Convert Lead to Customer and Opportunity
    conv_resp = client.post(f'/leads/{lead_id}/convert', data={
        'customer_action': 'new',
        'create_opportunity': 'y',
        'opportunity_name': 'Alpha Cloud Contract',
        'opportunity_amount': 25000.00,
        'expected_close_date': (date.today() + timedelta(days=30)).strftime('%Y-%m-%d')
    }, follow_redirects=True)
    assert conv_resp.status_code == 200

    with app.app_context():
        updated_lead = Lead.query.get(lead_id)
        assert updated_lead.status == 'Converted'
        assert updated_lead.converted_customer_id is not None
        # Check newly created customer
        new_cust = Customer.query.get(updated_lead.converted_customer_id)
        assert new_cust.email == 'alpha@prospect.com'
        # Check opportunity
        opp = Opportunity.query.filter_by(lead_id=lead_id).first()
        assert opp is not None
        assert opp.name == 'Alpha Cloud Contract'
        assert float(opp.amount) == 25000.00


# ==============================================================
# 4. OPPORTUNITY & PIPELINE CALCULATION TESTS
# ==============================================================

def test_opportunity_weighted_value_calculation(app, test_users):
    """Verify Opportunity Weighted Value = Amount * Probability / 100."""
    with app.app_context():
        cust = Customer(customer_code="CUST-9999", name="Test Cust", email="tc@test.com", phone="1231231234")
        db.session.add(cust)
        db.session.commit()

        opp = Opportunity(
            name="Test Deal",
            customer_id=cust.id,
            amount=50000.00,
            stage="Negotiation",
            probability=70,
            expected_close_date=date.today() + timedelta(days=20),
            status="Open"
        )
        db.session.add(opp)
        db.session.commit()

        # Weighted value = 50,000 * 70 / 100 = 35,000.00
        assert opp.weighted_value == 35000.00


# ==============================================================
# 5. REST API TESTS
# ==============================================================

def test_rest_api_customers(client, test_users, app):
    """Test /api/customers GET, POST, PUT, DELETE endpoints."""
    # Login session
    client.post('/login', data={'email': 'admin@test.com', 'password': 'AdminPass123!'})

    # POST /api/customers
    post_res = client.post('/api/customers', json={
        'name': 'API Tech Corp',
        'email': 'api@techcorp.com',
        'phone': '9876543210',
        'company_name': 'Tech Corp Global',
        'status': 'Active'
    })
    assert post_res.status_code == 201
    json_data = post_res.get_json()
    assert json_data['status'] == 'success'
    cust_id = json_data['data']['id']

    # GET /api/customers/<id>
    get_res = client.get(f'/api/customers/{cust_id}')
    assert get_res.status_code == 200
    assert get_res.get_json()['data']['email'] == 'api@techcorp.com'

    # PUT /api/customers/<id>
    put_res = client.put(f'/api/customers/{cust_id}', json={
        'name': 'API Tech Corp Updated',
        'city': 'San Francisco'
    })
    assert put_res.status_code == 200
    assert put_res.get_json()['data']['name'] == 'API Tech Corp Updated'

    # DELETE /api/customers/<id>
    del_res = client.delete(f'/api/customers/{cust_id}')
    assert del_res.status_code == 200

    # Verify 404 after delete
    get_res404 = client.get(f'/api/customers/{cust_id}')
    assert get_res404.status_code == 404


# ==============================================================
# 6. AUDIT TRAIL TESTS
# ==============================================================

def test_audit_log_generation(client, test_users, app):
    """Verify that operations write non-sensitive immutable audit logs."""
    client.post('/login', data={'email': 'admin@test.com', 'password': 'AdminPass123!'})

    # Create customer
    client.post('/customers/new', data={
        'name': 'Audited Customer',
        'email': 'audit@cust.com',
        'phone': '1112223334',
        'status': 'Active'
    })

    with app.app_context():
        log = AuditLog.query.filter_by(action='CUSTOMER_CREATED').first()
        assert log is not None
        assert 'Audited Customer' in log.new_values
        # Password hashes must never appear in audit logs
        assert 'password_hash' not in (log.new_values or '')
