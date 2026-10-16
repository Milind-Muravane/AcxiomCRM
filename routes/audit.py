"""
Audit log viewer routes (Restricted to Administrators and Managers, Read-Only).
"""
from flask import Blueprint, render_template, request
from flask_login import login_required
from models import AuditLog
from helpers import manager_or_admin_required

audit_bp = Blueprint('audit', __name__, url_prefix='/audit-logs')

@audit_bp.route('/')
@login_required
@manager_or_admin_required
def list_logs():
    """Display immutable audit logs with search and entity filters."""
    query = AuditLog.query

    action = request.args.get('action', '').strip()
    entity = request.args.get('entity', '').strip()
    search = request.args.get('search', '').strip()

    if action:
        query = query.filter(AuditLog.action.ilike(f"%{action}%"))

    if entity and entity != 'All':
        query = query.filter_by(entity_name=entity)

    if search:
        query = query.filter(
            (AuditLog.user_email.ilike(f"%{search}%")) |
            (AuditLog.record_id.ilike(f"%{search}%")) |
            (AuditLog.old_values.ilike(f"%{search}%")) |
            (AuditLog.new_values.ilike(f"%{search}%"))
        )

    # Order by newest first
    logs = query.order_by(AuditLog.timestamp.desc()).limit(200).all()

    # Collect distinct entity names for the filter dropdown
    entities = ['Customer', 'Lead', 'Opportunity', 'FollowUp', 'Activity', 'User', 'Database']

    return render_template(
        'audit_logs.html',
        logs=logs,
        action=action,
        entity=entity,
        search=search,
        entities=entities
    )
