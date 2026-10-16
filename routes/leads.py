"""
Lead management routes: CRUD, conversion workflow, search, and audit logging.
"""
from datetime import date, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Lead, Customer, Opportunity, User
from forms import LeadForm, ConvertLeadForm
from helpers import can_access_record, log_audit, generate_lead_code, generate_customer_code

leads_bp = Blueprint('leads', __name__, url_prefix='/leads')

def populate_assigned_choices(form):
    """Populate assigned_user_id select choices with active users."""
    users = User.query.filter_by(is_active=True).order_by(User.name.asc()).all()
    form.assigned_user_id.choices = [(0, '-- Unassigned --')] + [(u.id, f"{u.name} ({u.role})") for u in users]

@leads_bp.route('/')
@login_required
def list_leads():
    """List leads with search and status filtering."""
    query = Lead.query

    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Lead.name.ilike(search_filter)) |
            (Lead.email.ilike(search_filter)) |
            (Lead.phone.ilike(search_filter)) |
            (Lead.company_name.ilike(search_filter)) |
            (Lead.lead_code.ilike(search_filter))
        )

    # Status filter
    status = request.args.get('status', '').strip()
    if status and status != 'All':
        query = query.filter_by(status=status)

    leads = query.order_by(Lead.created_at.desc()).all()
    return render_template('leads.html', leads=leads, search=search, selected_status=status)


@leads_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_lead():
    """Create a new sales lead."""
    form = LeadForm()
    populate_assigned_choices(form)

    # Set default assignee to current user
    if request.method == 'GET' and form.assigned_user_id.data is None:
        form.assigned_user_id.data = current_user.id

    if form.validate_on_submit():
        lead_code = generate_lead_code()
        assigned_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        # SalesExecutives can only assign to themselves
        if current_user.role == 'SalesExecutive':
            assigned_id = current_user.id

        lead = Lead(
            lead_code=lead_code,
            name=form.name.data.strip(),
            email=form.email.data.strip().lower(),
            phone=form.phone.data.strip(),
            company_name=form.company_name.data.strip() if form.company_name.data else None,
            source=form.source.data,
            status=form.status.data,
            expected_value=form.expected_value.data or 0.00,
            assigned_user_id=assigned_id
        )

        db.session.add(lead)
        db.session.commit()

        log_audit("LEAD_CREATED", entity_name="Lead", record_id=lead.id, new_values=lead.to_dict())
        flash(f"Lead {lead.name} ({lead.lead_code}) created successfully!", "success")
        return redirect(url_for('leads.list_leads'))

    return render_template('lead_form.html', form=form, title="New Lead")


@leads_bp.route('/<int:lead_id>')
@login_required
def view_lead(lead_id):
    """View lead details and interaction timeline."""
    lead = Lead.query.get_or_404(lead_id)
    if not can_access_record(lead, current_user):
        flash("You do not have permission to view this lead.", "danger")
        return redirect(url_for('leads.list_leads'))

    return render_template('lead_detail.html', lead=lead)


@leads_bp.route('/<int:lead_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_lead(lead_id):
    """Edit lead information and pipeline status."""
    lead = Lead.query.get_or_404(lead_id)
    if not can_access_record(lead, current_user):
        flash("You do not have permission to edit this lead.", "danger")
        return redirect(url_for('leads.list_leads'))

    form = LeadForm(obj=lead)
    populate_assigned_choices(form)

    if request.method == 'GET':
        form.assigned_user_id.data = lead.assigned_user_id or 0

    if form.validate_on_submit():
        old_data = lead.to_dict()

        lead.name = form.name.data.strip()
        lead.email = form.email.data.strip().lower()
        lead.phone = form.phone.data.strip()
        lead.company_name = form.company_name.data.strip() if form.company_name.data else None
        lead.source = form.source.data
        lead.status = form.status.data
        lead.expected_value = form.expected_value.data or 0.00

        if current_user.role in ['Admin', 'Manager']:
            lead.assigned_user_id = form.assigned_user_id.data if form.assigned_user_id.data != 0 else None

        db.session.commit()

        log_audit("LEAD_UPDATED", entity_name="Lead", record_id=lead.id, old_values=old_data, new_values=lead.to_dict())
        flash(f"Lead {lead.lead_code} updated successfully.", "success")
        return redirect(url_for('leads.list_leads'))

    return render_template('lead_form.html', form=form, title=f"Edit Lead: {lead.lead_code}", lead=lead)


@leads_bp.route('/<int:lead_id>/convert', methods=['GET', 'POST'])
@login_required
def convert_lead(lead_id):
    """
    Lead conversion workflow:
    Converts lead into an active Customer and optionally creates an Opportunity.
    Prevents duplicate customers if email/phone already exists.
    """
    lead = Lead.query.get_or_404(lead_id)
    if not can_access_record(lead, current_user):
        flash("You do not have permission to convert this lead.", "danger")
        return redirect(url_for('leads.list_leads'))

    if lead.status == 'Converted':
        flash("This lead has already been converted.", "info")
        return redirect(url_for('leads.view_lead', lead_id=lead.id))

    form = ConvertLeadForm()
    # Populate existing customers
    customers = Customer.query.order_by(Customer.name.asc()).all()
    form.existing_customer_id.choices = [(0, '-- Select Customer --')] + [(c.id, f"{c.name} ({c.customer_code})") for c in customers]

    if request.method == 'GET':
        form.opportunity_name.data = f"{lead.company_name or lead.name} - New Opportunity"
        form.opportunity_amount.data = lead.expected_value or 10000.00
        form.expected_close_date.data = date.today() + timedelta(days=30)

    if form.validate_on_submit():
        target_customer = None

        if form.customer_action.data == 'new':
            # Check duplicate email
            existing_c = Customer.query.filter_by(email=lead.email).first()
            if existing_c:
                target_customer = existing_c
                flash(f"Existing customer found with email {lead.email}. Linked to existing customer {existing_c.name}.", "info")
            else:
                # Create new Customer from Lead info
                cust_code = generate_customer_code()
                target_customer = Customer(
                    customer_code=cust_code,
                    name=lead.name,
                    email=lead.email,
                    phone=lead.phone,
                    company_name=lead.company_name,
                    status='Active',
                    created_by_id=current_user.id
                )
                db.session.add(target_customer)
                db.session.flush() # obtain target_customer.id
                log_audit("CUSTOMER_CREATED_FROM_LEAD", entity_name="Customer", record_id=target_customer.id, new_values=target_customer.to_dict())
        else:
            cust_id = form.existing_customer_id.data
            target_customer = Customer.query.get(cust_id)
            if not target_customer:
                flash("Please select a valid existing customer.", "danger")
                return render_template('lead_convert.html', form=form, lead=lead)

        created_opp = None
        if form.create_opportunity.data:
            opp_name = form.opportunity_name.data.strip() if form.opportunity_name.data else f"{lead.name} Opportunity"
            opp_amount = form.opportunity_amount.data or lead.expected_value or 1000.00
            opp_close = form.expected_close_date.data or (date.today() + timedelta(days=30))

            created_opp = Opportunity(
                name=opp_name,
                customer_id=target_customer.id,
                lead_id=lead.id,
                amount=opp_amount,
                stage='Qualification',
                probability=20,
                expected_close_date=opp_close,
                status='Open',
                assigned_user_id=lead.assigned_user_id or current_user.id
            )
            db.session.add(created_opp)
            db.session.flush()
            log_audit("OPPORTUNITY_CREATED_FROM_LEAD", entity_name="Opportunity", record_id=created_opp.id, new_values=created_opp.to_dict())

        # Update Lead status and references
        lead.status = 'Converted'
        lead.converted_customer_id = target_customer.id
        if created_opp:
            lead.converted_opportunity_id = created_opp.id

        db.session.commit()

        log_audit(
            action="LEAD_CONVERTED",
            entity_name="Lead",
            record_id=lead.id,
            new_values={
                "converted_customer_id": target_customer.id,
                "converted_opportunity_id": created_opp.id if created_opp else None
            }
        )

        flash(f"Lead {lead.lead_code} successfully converted into Customer {target_customer.name}!", "success")
        return redirect(url_for('customers.view_customer', customer_id=target_customer.id))

    return render_template('lead_convert.html', form=form, lead=lead)


@leads_bp.route('/<int:lead_id>/delete', methods=['POST'])
@login_required
def delete_lead(lead_id):
    """Delete a lead record (Manager and Admin only)."""
    lead = Lead.query.get_or_404(lead_id)
    if not can_access_record(lead, current_user):
        flash("You do not have permission to delete this lead.", "danger")
        return redirect(url_for('leads.list_leads'))

    if current_user.role == 'SalesExecutive':
        flash("Sales Executives cannot delete lead records. Please contact your manager.", "danger")
        return redirect(url_for('leads.list_leads'))

    old_data = lead.to_dict()
    code = lead.lead_code
    db.session.delete(lead)
    db.session.commit()

    log_audit("LEAD_DELETED", entity_name="Lead", record_id=lead_id, old_values=old_data)
    flash(f"Lead {code} has been deleted.", "info")
    return redirect(url_for('leads.list_leads'))
