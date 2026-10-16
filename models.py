import json
from datetime import datetime, date, timezone
from decimal import Decimal
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

def utc_now():
    """Return timezone-naive UTC datetime for database compatibility."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

db = SQLAlchemy()

class User(UserMixin, db.Model):
    """User model for authentication and role-based access control."""
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='SalesExecutive')  # Admin, Manager, SalesExecutive
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    failed_login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    def set_password(self, password):
        """Securely hash and store the user password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Verify the password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def is_locked(self):
        """Check if the account is currently locked due to failed login attempts."""
        if self.locked_until and self.locked_until > utc_now():
            return True
        return False

    def to_dict(self):
        """Return safe user profile dictionary (excluding credentials)."""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'is_active': self.is_active,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<User {self.email} ({self.role})>'


class Customer(db.Model):
    """Customer entity representing established clients."""
    __tablename__ = 'customers'

    id = db.Column(db.Integer, primary_key=True)
    customer_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(30), unique=True, nullable=False, index=True)
    company_name = db.Column(db.String(150), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    city = db.Column(db.String(100), nullable=True)
    state = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Active')  # Active, Inactive, Lead
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    created_by = db.relationship('User', foreign_keys=[created_by_id], backref='created_customers')
    opportunities = db.relationship('Opportunity', backref='customer', cascade='all, delete-orphan', lazy=True)
    followups = db.relationship('FollowUp', backref='customer', cascade='all, delete-orphan', lazy=True)
    activities = db.relationship('Activity', backref='customer', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_code': self.customer_code,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'created_by': self.created_by.name if self.created_by else 'System'
        }

    def __repr__(self):
        return f'<Customer {self.customer_code} - {self.name}>'


class Lead(db.Model):
    """Lead entity representing potential sales opportunities."""
    __tablename__ = 'leads'

    id = db.Column(db.Integer, primary_key=True)
    lead_code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    phone = db.Column(db.String(30), nullable=False)
    company_name = db.Column(db.String(150), nullable=True)
    source = db.Column(db.String(50), nullable=False, default='Website')  # Website, Referral, Cold Call, Social Media, Advertisement, Partner, Other
    status = db.Column(db.String(30), nullable=False, default='New')  # New, Contacted, Qualified, Unqualified, Converted, Lost
    expected_value = db.Column(db.Numeric(12, 2), default=0.00, nullable=False)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    converted_customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='SET NULL'), nullable=True)
    converted_opportunity_id = db.Column(db.Integer, db.ForeignKey('opportunities.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id], backref='assigned_leads')
    converted_customer = db.relationship('Customer', foreign_keys=[converted_customer_id])
    followups = db.relationship('FollowUp', backref='lead', cascade='all, delete-orphan', lazy=True)
    activities = db.relationship('Activity', backref='lead', cascade='all, delete-orphan', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'lead_code': self.lead_code,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'company_name': self.company_name,
            'source': self.source,
            'status': self.status,
            'expected_value': float(self.expected_value) if self.expected_value is not None else 0.0,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'assigned_user': self.assigned_user.name if self.assigned_user else 'Unassigned',
            'converted_customer_id': self.converted_customer_id
        }

    def __repr__(self):
        return f'<Lead {self.lead_code} - {self.name}>'


class Opportunity(db.Model):
    """Opportunity entity representing an active deal in the sales pipeline."""
    __tablename__ = 'opportunities'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=False)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id', ondelete='SET NULL'), nullable=True)
    amount = db.Column(db.Numeric(12, 2), nullable=False, default=0.00)
    stage = db.Column(db.String(30), nullable=False, default='Qualification')  # Qualification, Proposal, Negotiation, Won, Lost
    probability = db.Column(db.Integer, nullable=False, default=10)  # 0 to 100
    expected_close_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Open')  # Open, Won, Lost
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)

    # Relationships
    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id], backref='assigned_opportunities')
    lead = db.relationship('Lead', foreign_keys=[lead_id], backref=db.backref('opportunities', lazy=True))

    @property
    def weighted_value(self):
        """Calculate Weighted Pipeline Value: Amount * Probability / 100"""
        amt = float(self.amount) if self.amount is not None else 0.0
        prob = float(self.probability) if self.probability is not None else 0.0
        return round((amt * prob) / 100.0, 2)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'lead_id': self.lead_id,
            'amount': float(self.amount) if self.amount is not None else 0.0,
            'stage': self.stage,
            'probability': self.probability,
            'weighted_value': self.weighted_value,
            'expected_close_date': self.expected_close_date.strftime('%Y-%m-%d') if self.expected_close_date else None,
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None,
            'assigned_user': self.assigned_user.name if self.assigned_user else 'Unassigned'
        }

    def __repr__(self):
        return f'<Opportunity {self.name} - ${self.amount}>'


class FollowUp(db.Model):
    """Follow-up action entity scheduled for leads or customers."""
    __tablename__ = 'followups'

    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id', ondelete='CASCADE'), nullable=True)
    followup_date = db.Column(db.DateTime, nullable=False)
    followup_type = db.Column(db.String(50), nullable=False, default='Call')  # Call, Email, Meeting, Demo
    remarks = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Planned')  # Planned, Pending, Completed, Overdue, Cancelled, Rescheduled
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id], backref='assigned_followups')

    @property
    def is_overdue(self):
        """Check if follow-up is past due and still incomplete."""
        if self.status in ['Planned', 'Pending'] and self.followup_date < utc_now():
            return True
        return False

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'lead_id': self.lead_id,
            'lead_name': self.lead.name if self.lead else None,
            'followup_date': self.followup_date.strftime('%Y-%m-%d %H:%M') if self.followup_date else None,
            'followup_type': self.followup_type,
            'remarks': self.remarks,
            'status': self.status,
            'is_overdue': self.is_overdue,
            'assigned_user': self.assigned_user.name if self.assigned_user else 'Unassigned',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<FollowUp {self.followup_type} on {self.followup_date}>'


class Activity(db.Model):
    """Activity tracking entity for logging calls, meetings, emails, and tasks."""
    __tablename__ = 'activities'

    id = db.Column(db.Integer, primary_key=True)
    activity_type = db.Column(db.String(50), nullable=False, default='Task')  # Call, Meeting, Email, Task
    subject = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    activity_date = db.Column(db.DateTime, nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id', ondelete='CASCADE'), nullable=True)
    lead_id = db.Column(db.Integer, db.ForeignKey('leads.id', ondelete='CASCADE'), nullable=True)
    assigned_user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    status = db.Column(db.String(30), nullable=False, default='Planned')  # Planned, In Progress, Completed, Cancelled
    created_at = db.Column(db.DateTime, default=utc_now, nullable=False)

    assigned_user = db.relationship('User', foreign_keys=[assigned_user_id], backref='assigned_activities')

    def to_dict(self):
        return {
            'id': self.id,
            'activity_type': self.activity_type,
            'subject': self.subject,
            'description': self.description,
            'activity_date': self.activity_date.strftime('%Y-%m-%d %H:%M') if self.activity_date else None,
            'customer_id': self.customer_id,
            'customer_name': self.customer.name if self.customer else None,
            'lead_id': self.lead_id,
            'lead_name': self.lead.name if self.lead else None,
            'status': self.status,
            'assigned_user': self.assigned_user.name if self.assigned_user else 'Unassigned',
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else None
        }

    def __repr__(self):
        return f'<Activity {self.activity_type}: {self.subject}>'


class AuditLog(db.Model):
    """Immutable audit trail for business and security operations."""
    __tablename__ = 'audit_logs'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'), nullable=True)
    user_email = db.Column(db.String(120), nullable=True)
    action = db.Column(db.String(100), nullable=False)  # e.g., CUSTOMER_CREATED, LOGIN_SUCCESS
    entity_name = db.Column(db.String(50), nullable=True)  # Customer, Lead, Opportunity, User, Auth
    record_id = db.Column(db.String(50), nullable=True)
    old_values = db.Column(db.Text, nullable=True)  # JSON string
    new_values = db.Column(db.Text, nullable=True)  # JSON string
    ip_address = db.Column(db.String(45), nullable=True)
    timestamp = db.Column(db.DateTime, default=utc_now, nullable=False)

    user = db.relationship('User', foreign_keys=[user_id])

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'user_email': self.user_email or (self.user.email if self.user else 'System'),
            'action': self.action,
            'entity_name': self.entity_name,
            'record_id': self.record_id,
            'old_values': json.loads(self.old_values) if self.old_values else None,
            'new_values': json.loads(self.new_values) if self.new_values else None,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else None
        }

    def __repr__(self):
        return f'<AuditLog {self.action} on {self.entity_name} ({self.record_id})>'
