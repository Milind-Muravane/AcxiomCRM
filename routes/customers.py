"""
Customer management routes: CRUD, search, filter, and audit logging.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from models import db, Customer, User
from forms import CustomerForm
from helpers import can_access_record, log_audit, generate_customer_code

customers_bp = Blueprint('customers', __name__, url_prefix='/customers')

@customers_bp.route('/')
@login_required
def list_customers():
    """List customers with search and status filtering."""
    query = Customer.query

    # Record-level filtering for SalesExecutives
    if current_user.role == 'SalesExecutive':
        query = query.filter_by(created_by_id=current_user.id)

    # Search filter
    search = request.args.get('search', '').strip()
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Customer.name.ilike(search_filter)) |
            (Customer.email.ilike(search_filter)) |
            (Customer.phone.ilike(search_filter)) |
            (Customer.company_name.ilike(search_filter)) |
            (Customer.customer_code.ilike(search_filter))
        )

    # Status filter
    status = request.args.get('status', '').strip()
    if status and status != 'All':
        query = query.filter_by(status=status)

    customers = query.order_by(Customer.created_at.desc()).all()
    return render_template('customers.html', customers=customers, search=search, selected_status=status)


@customers_bp.route('/new', methods=['GET', 'POST'])
@login_required
def create_customer():
    """Create a new customer with server-side validation and duplicate checking."""
    form = CustomerForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        phone = form.phone.data.strip()

        # Check duplicate email
        if Customer.query.filter_by(email=email).first():
            flash("A customer with this email address already exists.", "danger")
            return render_template('customer_form.html', form=form, title="New Customer")

        # Check duplicate phone
        if Customer.query.filter_by(phone=phone).first():
            flash("A customer with this phone number already exists.", "danger")
            return render_template('customer_form.html', form=form, title="New Customer")

        customer_code = generate_customer_code()
        customer = Customer(
            customer_code=customer_code,
            name=form.name.data.strip(),
            email=email,
            phone=phone,
            company_name=form.company_name.data.strip() if form.company_name.data else None,
            address=form.address.data.strip() if form.address.data else None,
            city=form.city.data.strip() if form.city.data else None,
            state=form.state.data.strip() if form.state.data else None,
            status=form.status.data,
            created_by_id=current_user.id
        )

        db.session.add(customer)
        db.session.commit()

        log_audit(
            action="CUSTOMER_CREATED",
            entity_name="Customer",
            record_id=customer.id,
            new_values=customer.to_dict()
        )

        flash(f"Customer {customer.name} ({customer.customer_code}) created successfully!", "success")
        return redirect(url_for('customers.list_customers'))

    return render_template('customer_form.html', form=form, title="New Customer")


@customers_bp.route('/<int:customer_id>')
@login_required
def view_customer(customer_id):
    """View customer details along with associated opportunities, follow-ups, and activities."""
    customer = Customer.query.get_or_404(customer_id)
    if not can_access_record(customer, current_user):
        flash("You do not have permission to view this customer record.", "danger")
        return redirect(url_for('customers.list_customers'))

    return render_template('customer_detail.html', customer=customer)


@customers_bp.route('/<int:customer_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_customer(customer_id):
    """Edit existing customer details."""
    customer = Customer.query.get_or_404(customer_id)
    if not can_access_record(customer, current_user):
        flash("You do not have permission to edit this customer record.", "danger")
        return redirect(url_for('customers.list_customers'))

    form = CustomerForm(obj=customer)
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        phone = form.phone.data.strip()

        # Check uniqueness against other customers
        existing_email = Customer.query.filter(Customer.email == email, Customer.id != customer.id).first()
        if existing_email:
            flash("Another customer is already registered with this email address.", "danger")
            return render_template('customer_form.html', form=form, title=f"Edit Customer: {customer.customer_code}")

        existing_phone = Customer.query.filter(Customer.phone == phone, Customer.id != customer.id).first()
        if existing_phone:
            flash("Another customer is already registered with this phone number.", "danger")
            return render_template('customer_form.html', form=form, title=f"Edit Customer: {customer.customer_code}")

        old_values = customer.to_dict()

        customer.name = form.name.data.strip()
        customer.email = email
        customer.phone = phone
        customer.company_name = form.company_name.data.strip() if form.company_name.data else None
        customer.address = form.address.data.strip() if form.address.data else None
        customer.city = form.city.data.strip() if form.city.data else None
        customer.state = form.state.data.strip() if form.state.data else None
        customer.status = form.status.data

        db.session.commit()

        log_audit(
            action="CUSTOMER_UPDATED",
            entity_name="Customer",
            record_id=customer.id,
            old_values=old_values,
            new_values=customer.to_dict()
        )

        flash(f"Customer {customer.customer_code} updated successfully.", "success")
        return redirect(url_for('customers.list_customers'))

    return render_template('customer_form.html', form=form, title=f"Edit Customer: {customer.customer_code}", customer=customer)


@customers_bp.route('/<int:customer_id>/delete', methods=['POST'])
@login_required
def delete_customer(customer_id):
    """Delete a customer record with audit logging."""
    customer = Customer.query.get_or_404(customer_id)
    if not can_access_record(customer, current_user):
        flash("You do not have permission to delete this customer record.", "danger")
        return redirect(url_for('customers.list_customers'))

    # Restrict deletion to Admin or Manager for safety
    if current_user.role == 'SalesExecutive':
        flash("Sales Executives cannot delete customer records. Please contact a Manager or Admin.", "danger")
        return redirect(url_for('customers.list_customers'))

    old_data = customer.to_dict()
    code = customer.customer_code
    name = customer.name

    db.session.delete(customer)
    db.session.commit()

    log_audit(
        action="CUSTOMER_DELETED",
        entity_name="Customer",
        record_id=customer_id,
        old_values=old_data
    )

    flash(f"Customer {name} ({code}) and associated records deleted.", "info")
    return redirect(url_for('customers.list_customers'))
