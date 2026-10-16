"""
Helper utilities for authorization, record ownership verification,
audit logging, and unique code generation.
"""
import json
from functools import wraps
from flask import request, abort, flash, redirect, url_for
from flask_login import current_user
from models import db, AuditLog, Customer, Lead

def role_required(*allowed_roles):
    """
    Decorator to restrict route access to users with specified roles.
    Example: @role_required('Admin', 'Manager')
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login', next=request.url))
            if current_user.role not in allowed_roles:
                flash("You do not have permission to access this page.", "danger")
                return redirect(url_for('main.dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """Decorator to restrict access strictly to System Administrators."""
    return role_required('Admin')(f)

def manager_or_admin_required(f):
    """Decorator for routes accessible to Managers and Admins."""
    return role_required('Admin', 'Manager')(f)

def can_access_record(record, user):
    """
    Record-level access control:
    - Admins and Managers can access all records.
    - SalesExecutives can only view/modify records assigned to them or created by them.
    """
    if not user.is_authenticated:
        return False
    if user.role in ['Admin', 'Manager']:
        return True
    
    # Check assigned_user_id or created_by_id
    assigned_id = getattr(record, 'assigned_user_id', None)
    if assigned_id is not None and assigned_id == user.id:
        return True
    
    creator_id = getattr(record, 'created_by_id', None)
    if creator_id is not None and creator_id == user.id:
        return True
        
    return False

def log_audit(action, entity_name=None, record_id=None, old_values=None, new_values=None):
    """
    Create an immutable audit log entry.
    Safely strips out sensitive fields like passwords, secrets, or tokens.
    """
    try:
        # Determine current user if available
        user_id = current_user.id if current_user.is_authenticated else None
        user_email = current_user.email if current_user.is_authenticated else "System / Anonymous"

        # Sanitize dictionaries to prevent sensitive information from being logged
        def sanitize(val_dict):
            if not isinstance(val_dict, dict):
                return val_dict
            clean = {}
            for k, v in val_dict.items():
                if any(secret_word in k.lower() for secret_word in ['password', 'secret', 'token', 'hash', 'csrf']):
                    clean[k] = '[REDACTED]'
                else:
                    clean[k] = v
            return clean

        old_json = json.dumps(sanitize(old_values)) if old_values is not None else None
        new_json = json.dumps(sanitize(new_values)) if new_values is not None else None

        ip_addr = request.remote_addr if request else "127.0.0.1"

        log_entry = AuditLog(
            user_id=user_id,
            user_email=user_email,
            action=action,
            entity_name=entity_name,
            record_id=str(record_id) if record_id is not None else None,
            old_values=old_json,
            new_values=new_json,
            ip_address=ip_addr
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        # Never allow audit logging failure to crash an otherwise successful transaction
        db.session.rollback()
        print(f"Warning: Failed to write audit log: {e}")

def generate_customer_code():
    """Generate next sequential customer code like CUST-1004."""
    last_customer = Customer.query.order_by(Customer.id.desc()).first()
    next_id = (last_customer.id + 1) if last_customer else 1001
    return f"CUST-{next_id:04d}"

def generate_lead_code():
    """Generate next sequential lead code like LEAD-2001."""
    last_lead = Lead.query.order_by(Lead.id.desc()).first()
    next_id = (last_lead.id + 1) if last_lead else 2001
    return f"LEAD-{next_id:04d}"
