"""
Reports and analytics routes: Tabular reports, filtering, and CSV export.
"""
import io
import csv
from datetime import datetime
from flask import Blueprint, render_template, request, Response, flash, redirect, url_for
from flask_login import login_required, current_user
from models import Customer, Lead, Opportunity, FollowUp, Activity, User
from helpers import role_required

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')

@reports_bp.route('/')
@login_required
def index():
    """Main reporting center with multiple business report tabs."""
    report_type = request.args.get('type', 'opportunities')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    user_id = request.args.get('user_id', type=int)

    is_exec = (current_user.role == 'SalesExecutive')
    users = User.query.filter_by(is_active=True).all()

    data = []
    headers = []

    if report_type == 'opportunities':
        q = Opportunity.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        elif user_id:
            q = q.filter_by(assigned_user_id=user_id)

        data = q.order_by(Opportunity.expected_close_date.asc()).all()
        headers = ['Deal Name', 'Customer', 'Amount ($)', 'Stage', 'Probability (%)', 'Weighted Value ($)', 'Close Date', 'Status', 'Sales Rep']

    elif report_type == 'leads':
        q = Lead.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        elif user_id:
            q = q.filter_by(assigned_user_id=user_id)

        data = q.order_by(Lead.created_at.desc()).all()
        headers = ['Lead Code', 'Name', 'Email', 'Company', 'Source', 'Status', 'Expected Value ($)', 'Created Date', 'Assigned To']

    elif report_type == 'customers':
        q = Customer.query
        if is_exec:
            q = q.filter_by(created_by_id=current_user.id)

        data = q.order_by(Customer.created_at.desc()).all()
        headers = ['Customer Code', 'Name', 'Email', 'Phone', 'Company', 'City', 'Status', 'Created Date']

    elif report_type == 'followups':
        q = FollowUp.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        elif user_id:
            q = q.filter_by(assigned_user_id=user_id)

        data = q.order_by(FollowUp.followup_date.desc()).all()
        headers = ['Type', 'Target', 'Scheduled Date', 'Status', 'Assigned Rep', 'Remarks']

    elif report_type == 'activities':
        q = Activity.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        elif user_id:
            q = q.filter_by(assigned_user_id=user_id)

        data = q.order_by(Activity.activity_date.desc()).all()
        headers = ['Type', 'Subject', 'Date', 'Target', 'Status', 'Logged By']

    return render_template(
        'reports.html',
        report_type=report_type,
        data=data,
        headers=headers,
        users=users,
        selected_user=user_id
    )


@reports_bp.route('/export/<report_type>')
@login_required
def export_csv(report_type):
    """Export the requested report dataset to a CSV file."""
    is_exec = (current_user.role == 'SalesExecutive')
    output = io.StringIO()
    writer = csv.writer(output)

    if report_type == 'opportunities':
        writer.writerow(['ID', 'Name', 'Customer', 'Amount', 'Stage', 'Probability', 'Weighted Value', 'Close Date', 'Status', 'Assigned User'])
        q = Opportunity.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        for o in q.all():
            writer.writerow([
                o.id, o.name, o.customer.name if o.customer else '',
                o.amount, o.stage, o.probability, o.weighted_value,
                o.expected_close_date, o.status,
                o.assigned_user.name if o.assigned_user else 'Unassigned'
            ])

    elif report_type == 'leads':
        writer.writerow(['ID', 'Code', 'Name', 'Email', 'Phone', 'Company', 'Source', 'Status', 'Expected Value', 'Assigned User'])
        q = Lead.query
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        for l in q.all():
            writer.writerow([
                l.id, l.lead_code, l.name, l.email, l.phone,
                l.company_name or '', l.source, l.status, l.expected_value,
                l.assigned_user.name if l.assigned_user else 'Unassigned'
            ])

    elif report_type == 'customers':
        writer.writerow(['ID', 'Code', 'Name', 'Email', 'Phone', 'Company', 'City', 'State', 'Status', 'Created Date'])
        q = Customer.query
        if is_exec:
            q = q.filter_by(created_by_id=current_user.id)
        for c in q.all():
            writer.writerow([
                c.id, c.customer_code, c.name, c.email, c.phone,
                c.company_name or '', c.city or '', c.state or '', c.status,
                c.created_at.strftime('%Y-%m-%d') if c.created_at else ''
            ])
    else:
        flash("Invalid report export requested.", "danger")
        return redirect(url_for('reports.index'))

    output.seek(0)
    filename = f"acxiom_crm_{report_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={filename}"}
    )
