"""
Activity logging routes: Log calls, meetings, emails, and tasks with customer/lead associations.
"""
from datetime import datetime
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Activity, Customer, Lead, User
from forms import ActivityForm
from helpers import can_access_record, log_audit

activities_bp = Blueprint('activities', __name__, url_prefix='/activities')

def populate_activity_choices(form):
    """Populate customers, leads, and users."""
    customers = Customer.query.order_by(Customer.name.asc()).all()
    form.customer_id.choices = [(0, '-- None / Lead Only --')] + [(c.id, f"{c.name} ({c.customer_code})") for c in customers]

    leads = Lead.query.order_by(Lead.name.asc()).all()
    form.lead_id.choices = [(0, '-- None / Customer Only --')] + [(l.id, f"{l.name} ({l.lead_code})") for l in leads]

    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    form.assigned_user_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]


@activities_bp.route('/')
@login_required
def list_activities():
    """List activities with activity type and status filters."""
    query = Activity.query

    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    activity_type = request.args.get('type', 'All').strip()
    if activity_type != 'All' and activity_type:
        query = query.filter_by(activity_type=activity_type)

    status = request.args.get('status', 'All').strip()
    if status != 'All' and status:
        query = query.filter_by(status=status)

    activities = query.order_by(Activity.activity_date.desc()).all()
    return render_template(
        'activities.html',
        activities=activities,
        selected_type=activity_type,
        selected_status=status
    )


@activities_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_activity():
    """Log a new sales activity."""
    form = ActivityForm()
    populate_activity_choices(form)

    # Pre-select customer or lead if specified
    if request.method == 'GET':
        c_id = request.args.get('customer_id', type=int)
        l_id = request.args.get('lead_id', type=int)
        if c_id:
            form.customer_id.data = c_id
        if l_id:
            form.lead_id.data = l_id
        form.activity_date.data = datetime.now()
        form.assigned_user_id.data = current_user.id

    if form.validate_on_submit():
        c_id = form.customer_id.data if form.customer_id.data != 0 else None
        l_id = form.lead_id.data if form.lead_id.data != 0 else None

        if not c_id and not l_id:
            flash("Please associate this activity with either a Customer or a Lead.", "danger")
            return render_template('activity_form.html', form=form, title="Log Activity")

        assigned_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else current_user.id
        if current_user.role == 'SalesExecutive':
            assigned_id = current_user.id

        activity = Activity(
            activity_type=form.activity_type.data,
            subject=form.subject.data.strip(),
            description=form.description.data.strip() if form.description.data else None,
            activity_date=form.activity_date.data,
            customer_id=c_id,
            lead_id=l_id,
            assigned_user_id=assigned_id,
            status=form.status.data
        )

        db.session.add(activity)
        db.session.commit()

        log_audit("ACTIVITY_CREATED", entity_name="Activity", record_id=activity.id, new_values=activity.to_dict())
        flash(f"Activity '{activity.subject}' logged successfully!", "success")
        return redirect(url_for('activities.list_activities'))

    return render_template('activity_form.html', form=form, title="Log Activity")


@activities_bp.route('/<int:activity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_activity(activity_id):
    """Edit activity details."""
    activity = Activity.query.get_or_404(activity_id)
    if not can_access_record(activity, current_user):
        flash("You do not have permission to edit this activity.", "danger")
        return redirect(url_for('activities.list_activities'))

    form = ActivityForm(obj=activity)
    populate_activity_choices(form)

    if request.method == 'GET':
        form.customer_id.data = activity.customer_id or 0
        form.lead_id.data = activity.lead_id or 0
        form.assigned_user_id.data = activity.assigned_user_id or 0

    if form.validate_on_submit():
        c_id = form.customer_id.data if form.customer_id.data != 0 else None
        l_id = form.lead_id.data if form.lead_id.data != 0 else None

        if not c_id and not l_id:
            flash("Please associate this activity with either a Customer or a Lead.", "danger")
            return render_template('activity_form.html', form=form, title="Edit Activity")

        old_data = activity.to_dict()

        activity.activity_type = form.activity_type.data
        activity.subject = form.subject.data.strip()
        activity.description = form.description.data.strip() if form.description.data else None
        activity.activity_date = form.activity_date.data
        activity.customer_id = c_id
        activity.lead_id = l_id
        activity.status = form.status.data

        if current_user.role in ['Admin', 'Manager']:
            activity.assigned_user_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        db.session.commit()

        log_audit("ACTIVITY_UPDATED", entity_name="Activity", record_id=activity.id, old_values=old_data, new_values=activity.to_dict())
        flash("Activity updated successfully.", "success")
        return redirect(url_for('activities.list_activities'))

    return render_template('activity_form.html', form=form, title="Edit Activity", activity=activity)


@activities_bp.route('/<int:activity_id>/delete', methods=['POST'])
@login_required
def delete_activity(activity_id):
    """Delete an activity record."""
    activity = Activity.query.get_or_404(activity_id)
    if not can_access_record(activity, current_user):
        flash("You do not have permission to delete this activity.", "danger")
        return redirect(url_for('activities.list_activities'))

    old_data = activity.to_dict()
    db.session.delete(activity)
    db.session.commit()

    log_audit("ACTIVITY_DELETED", entity_name="Activity", record_id=activity_id, old_values=old_data)
    flash("Activity deleted.", "info")
    return redirect(url_for('activities.list_activities'))
