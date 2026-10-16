"""
Follow-up management routes: Scheduling, pending, overdue tracking, and status updates.
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, FollowUp, Customer, Lead, User
from forms import FollowUpForm
from helpers import can_access_record, log_audit

followups_bp = Blueprint('followups', __name__, url_prefix='/followups')

def populate_followup_choices(form):
    """Populate customers, leads, and users."""
    customers = Customer.query.order_by(Customer.name.asc()).all()
    form.customer_id.choices = [(0, '-- None / Lead Only --')] + [(c.id, f"{c.name} ({c.customer_code})") for c in customers]

    leads = Lead.query.order_by(Lead.name.asc()).all()
    form.lead_id.choices = [(0, '-- None / Customer Only --')] + [(l.id, f"{l.name} ({l.lead_code})") for l in leads]

    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    form.assigned_user_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]


@followups_bp.route('/')
@login_required
def list_followups():
    """List follow-ups with overdue and status filters."""
    query = FollowUp.query

    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    status_filter = request.args.get('status', 'All').strip()
    now = datetime.utcnow()

    if status_filter == 'Overdue':
        query = query.filter(
            FollowUp.status.in_(['Planned', 'Pending']),
            FollowUp.followup_date < now
        )
    elif status_filter == 'Pending':
        query = query.filter(FollowUp.status.in_(['Planned', 'Pending']))
    elif status_filter != 'All' and status_filter:
        query = query.filter_by(status=status_filter)

    followups = query.order_by(FollowUp.followup_date.asc()).all()
    return render_template('followups.html', followups=followups, selected_status=status_filter, now=now)


@followups_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_followup():
    """Schedule a new follow-up interaction."""
    form = FollowUpForm()
    populate_followup_choices(form)

    # Pre-select customer or lead if passed via query params
    if request.method == 'GET':
        c_id = request.args.get('customer_id', type=int)
        l_id = request.args.get('lead_id', type=int)
        if c_id:
            form.customer_id.data = c_id
        if l_id:
            form.lead_id.data = l_id
        form.assigned_user_id.data = current_user.id

    if form.validate_on_submit():
        c_id = form.customer_id.data if form.customer_id.data != 0 else None
        l_id = form.lead_id.data if form.lead_id.data != 0 else None

        if not c_id and not l_id:
            flash("Please associate this follow-up with either a Customer or a Lead.", "danger")
            return render_template('followup_form.html', form=form, title="Schedule Follow-up")

        assigned_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else current_user.id
        if current_user.role == 'SalesExecutive':
            assigned_id = current_user.id

        followup = FollowUp(
            customer_id=c_id,
            lead_id=l_id,
            followup_date=form.followup_date.data,
            followup_type=form.followup_type.data,
            remarks=form.remarks.data.strip() if form.remarks.data else None,
            status=form.status.data,
            assigned_user_id=assigned_id
        )

        db.session.add(followup)
        db.session.commit()

        log_audit("FOLLOWUP_CREATED", entity_name="FollowUp", record_id=followup.id, new_values=followup.to_dict())
        flash("Follow-up scheduled successfully!", "success")
        return redirect(url_for('followups.list_followups'))

    return render_template('followup_form.html', form=form, title="Schedule Follow-up")


@followups_bp.route('/<int:followup_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_followup(followup_id):
    """Edit or reschedule a follow-up."""
    followup = FollowUp.query.get_or_404(followup_id)
    if not can_access_record(followup, current_user):
        flash("You do not have permission to edit this follow-up.", "danger")
        return redirect(url_for('followups.list_followups'))

    form = FollowUpForm(obj=followup)
    populate_followup_choices(form)

    if request.method == 'GET':
        form.customer_id.data = followup.customer_id or 0
        form.lead_id.data = followup.lead_id or 0
        form.assigned_user_id.data = followup.assigned_user_id or 0

    if form.validate_on_submit():
        c_id = form.customer_id.data if form.customer_id.data != 0 else None
        l_id = form.lead_id.data if form.lead_id.data != 0 else None

        if not c_id and not l_id:
            flash("Please associate this follow-up with either a Customer or a Lead.", "danger")
            return render_template('followup_form.html', form=form, title="Edit Follow-up")

        old_data = followup.to_dict()

        followup.customer_id = c_id
        followup.lead_id = l_id
        followup.followup_date = form.followup_date.data
        followup.followup_type = form.followup_type.data
        followup.remarks = form.remarks.data.strip() if form.remarks.data else None
        followup.status = form.status.data

        if current_user.role in ['Admin', 'Manager']:
            followup.assigned_user_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        db.session.commit()

        log_audit("FOLLOWUP_UPDATED", entity_name="FollowUp", record_id=followup.id, old_values=old_data, new_values=followup.to_dict())
        flash("Follow-up updated successfully.", "success")
        return redirect(url_for('followups.list_followups'))

    return render_template('followup_form.html', form=form, title="Edit Follow-up", followup=followup)


@followups_bp.route('/<int:followup_id>/status/<new_status>', methods=['POST'])
@login_required
def update_status(followup_id, new_status):
    """Quickly update status (e.g. Completed, Cancelled) from the listing table."""
    followup = FollowUp.query.get_or_404(followup_id)
    if not can_access_record(followup, current_user):
        flash("You do not have permission to update this follow-up.", "danger")
        return redirect(url_for('followups.list_followups'))

    if new_status in ['Completed', 'Cancelled', 'Pending', 'Rescheduled']:
        old_data = followup.to_dict()
        followup.status = new_status
        db.session.commit()
        log_audit("FOLLOWUP_STATUS_CHANGED", entity_name="FollowUp", record_id=followup.id, old_values=old_data, new_values=followup.to_dict())
        flash(f"Follow-up marked as {new_status}.", "success")

    return redirect(url_for('followups.list_followups'))


@followups_bp.route('/<int:followup_id>/delete', methods=['POST'])
@login_required
def delete_followup(followup_id):
    """Delete a follow-up record."""
    followup = FollowUp.query.get_or_404(followup_id)
    if not can_access_record(followup, current_user):
        flash("You do not have permission to delete this follow-up.", "danger")
        return redirect(url_for('followups.list_followups'))

    old_data = followup.to_dict()
    db.session.delete(followup)
    db.session.commit()

    log_audit("FOLLOWUP_DELETED", entity_name="FollowUp", record_id=followup_id, old_values=old_data)
    flash("Follow-up deleted.", "info")
    return redirect(url_for('followups.list_followups'))
