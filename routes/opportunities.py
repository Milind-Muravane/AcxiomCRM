"""
Opportunity management routes: Pipeline tracking, stages, weighted value, and audit logging.
"""
from datetime import date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Opportunity, Customer, Lead, User
from forms import OpportunityForm
from helpers import can_access_record, log_audit

opportunities_bp = Blueprint('opportunities', __name__, url_prefix='/opportunities')

def populate_opportunity_choices(form):
    """Populate dynamic select fields for customers, leads, and sales reps."""
    customers = Customer.query.order_by(Customer.name.asc()).all()
    form.customer_id.choices = [(c.id, f"{c.name} ({c.customer_code})") for c in customers]

    leads = Lead.query.order_by(Lead.name.asc()).all()
    form.lead_id.choices = [(0, '-- None / Direct Customer --')] + [(l.id, f"{l.name} ({l.lead_code})") for l in leads]

    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    form.assigned_user_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]


@opportunities_bp.route('/')
@login_required
def list_opportunities():
    """List opportunities with stage and status filters."""
    query = Opportunity.query

    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        search_filter = f"%{search}%"
        query = query.join(Customer).filter(
            (Opportunity.name.ilike(search_filter)) |
            (Customer.name.ilike(search_filter))
        )

    # Stage filter
    stage = request.args.get('stage', '').strip()
    if stage and stage != 'All':
        query = query.filter(Opportunity.stage == stage)

    # Status filter
    status = request.args.get('status', '').strip()
    if status and status != 'All':
        query = query.filter(Opportunity.status == status)

    opportunities = query.order_by(Opportunity.expected_close_date.asc()).all()

    # Calculate summary numbers for this filtered view
    total_val = sum(float(o.amount) for o in opportunities)
    weighted_val = sum(o.weighted_value for o in opportunities)

    return render_template(
        'opportunities.html',
        opportunities=opportunities,
        search=search,
        selected_stage=stage,
        selected_status=status,
        total_val=round(total_val, 2),
        weighted_val=round(weighted_val, 2)
    )


@opportunities_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_opportunity():
    """Create a new opportunity."""
    form = OpportunityForm()
    populate_opportunity_choices(form)

    # Check if there are any customers
    if not form.customer_id.choices:
        flash("You must create at least one customer before creating an opportunity.", "warning")
        return redirect(url_for('customers.create_customer'))

    # Default assignee
    if request.method == 'GET' and form.assigned_user_id.data is None:
        form.assigned_user_id.data = current_user.id

    if form.validate_on_submit():
        lead_id = form.lead_id.data if form.lead_id.data != 0 else None
        assigned_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        if current_user.role == 'SalesExecutive':
            assigned_id = current_user.id

        stage = form.stage.data
        # Synchronize status based on stage
        if stage == 'Won':
            status = 'Won'
            probability = 100
        elif stage == 'Lost':
            status = 'Lost'
            probability = 0
        else:
            status = 'Open'
            probability = form.probability.data

        opportunity = Opportunity(
            name=form.name.data.strip(),
            customer_id=form.customer_id.data,
            lead_id=lead_id,
            amount=form.amount.data,
            stage=stage,
            probability=probability,
            expected_close_date=form.expected_close_date.data,
            status=status,
            assigned_user_id=assigned_id
        )

        db.session.add(opportunity)
        db.session.commit()

        log_audit(
            action="OPPORTUNITY_CREATED",
            entity_name="Opportunity",
            record_id=opportunity.id,
            new_values=opportunity.to_dict()
        )

        flash(f"Opportunity '{opportunity.name}' created successfully!", "success")
        return redirect(url_for('opportunities.list_opportunities'))

    return render_template('opportunity_form.html', form=form, title="New Opportunity")


@opportunities_bp.route('/<int:opportunity_id>')
@login_required
def view_opportunity(opportunity_id):
    """View details of a specific deal and linked customer/lead."""
    opp = Opportunity.query.get_or_404(opportunity_id)
    if not can_access_record(opp, current_user):
        flash("You do not have permission to view this opportunity.", "danger")
        return redirect(url_for('opportunities.list_opportunities'))

    return render_template('opportunity_detail.html', opportunity=opp)


@opportunities_bp.route('/<int:opportunity_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_opportunity(opportunity_id):
    """Edit opportunity details, stages, and probabilities."""
    opp = Opportunity.query.get_or_404(opportunity_id)
    if not can_access_record(opp, current_user):
        flash("You do not have permission to edit this opportunity.", "danger")
        return redirect(url_for('opportunities.list_opportunities'))

    form = OpportunityForm(obj=opp)
    populate_opportunity_choices(form)

    if request.method == 'GET':
        form.lead_id.data = opp.lead_id or 0
        form.assigned_user_id.data = opp.assigned_user_id or 0

    if form.validate_on_submit():
        old_data = opp.to_dict()

        stage = form.stage.data
        if stage == 'Won':
            status = 'Won'
            probability = 100
        elif stage == 'Lost':
            status = 'Lost'
            probability = 0
        else:
            status = 'Open'
            probability = form.probability.data

        opp.name = form.name.data.strip()
        opp.customer_id = form.customer_id.data
        opp.lead_id = form.lead_id.data if form.lead_id.data != 0 else None
        opp.amount = form.amount.data
        opp.stage = stage
        opp.probability = probability
        opp.expected_close_date = form.expected_close_date.data
        opp.status = status

        if current_user.role in ['Admin', 'Manager']:
            opp.assigned_user_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        db.session.commit()

        log_audit(
            action="OPPORTUNITY_UPDATED",
            entity_name="Opportunity",
            record_id=opp.id,
            old_values=old_data,
            new_values=opp.to_dict()
        )

        flash(f"Opportunity '{opp.name}' updated successfully.", "success")
        return redirect(url_for('opportunities.list_opportunities'))

    return render_template('opportunity_form.html', form=form, title=f"Edit Opportunity: {opp.name}", opportunity=opp)


@opportunities_bp.route('/<int:opportunity_id>/delete', methods=['POST'])
@login_required
def delete_opportunity(opportunity_id):
    """Delete an opportunity (Managers and Admins only)."""
    opp = Opportunity.query.get_or_404(opportunity_id)
    if not can_access_record(opp, current_user):
        flash("You do not have permission to delete this opportunity.", "danger")
        return redirect(url_for('opportunities.list_opportunities'))

    if current_user.role == 'SalesExecutive':
        flash("Sales Executives cannot delete opportunities. Please consult your manager.", "danger")
        return redirect(url_for('opportunities.list_opportunities'))

    old_data = opp.to_dict()
    name = opp.name
    db.session.delete(opp)
    db.session.commit()

    log_audit("OPPORTUNITY_DELETED", entity_name="Opportunity", record_id=opportunity_id, old_values=old_data)
    flash(f"Opportunity '{name}' deleted.", "info")
    return redirect(url_for('opportunities.list_opportunities'))
