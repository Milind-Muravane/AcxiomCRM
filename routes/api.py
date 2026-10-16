"""
REST API endpoints for Customers, Leads, Opportunities, and Dashboard Analytics.
Returns JSON and proper HTTP status codes.
"""
from datetime import datetime, date
from flask import Blueprint, jsonify, request
from flask_login import current_user
from models import db, Customer, Lead, Opportunity, User
from helpers import log_audit, generate_customer_code, generate_lead_code

api_bp = Blueprint('api', __name__, url_prefix='/api')

def api_auth_required(f):
    """Ensure user is logged in before using API routes, returning 401 JSON instead of redirect."""
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({
                "status": "error",
                "message": "Authentication required. Please sign in."
            }), 401
        return f(*args, **kwargs)
    return decorated


# ==============================================================
# CUSTOMER API ENDPOINTS
# ==============================================================

@api_bp.route('/customers', methods=['GET'])
@api_auth_required
def get_customers():
    """GET /api/customers: Retrieve list of customers."""
    query = Customer.query
    if current_user.role == 'SalesExecutive':
        query = query.filter_by(created_by_id=current_user.id)

    customers = query.order_by(Customer.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "count": len(customers),
        "data": [c.to_dict() for c in customers]
    }), 200


@api_bp.route('/customers/<int:id>', methods=['GET'])
@api_auth_required
def get_customer(id):
    """GET /api/customers/<id>: Retrieve single customer details."""
    customer = db.session.get(Customer, id)
    if not customer:
        return jsonify({"status": "error", "message": f"Customer with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and customer.created_by_id != current_user.id:
        return jsonify({"status": "error", "message": "Access forbidden: you do not own this customer record."}), 403

    return jsonify({"status": "success", "data": customer.to_dict()}), 200


@api_bp.route('/customers', methods=['POST'])
@api_auth_required
def create_customer():
    """POST /api/customers: Create a new customer."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON or missing request body."}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()

    if not name or not email or not phone:
        return jsonify({"status": "error", "message": "name, email, and phone are required fields."}), 400

    if Customer.query.filter_by(email=email).first():
        return jsonify({"status": "error", "message": "A customer with this email already exists."}), 400

    if Customer.query.filter_by(phone=phone).first():
        return jsonify({"status": "error", "message": "A customer with this phone already exists."}), 400

    code = generate_customer_code()
    customer = Customer(
        customer_code=code,
        name=name,
        email=email,
        phone=phone,
        company_name=data.get('company_name'),
        address=data.get('address'),
        city=data.get('city'),
        state=data.get('state'),
        status=data.get('status', 'Active'),
        created_by_id=current_user.id
    )
    db.session.add(customer)
    db.session.commit()

    log_audit("API_CUSTOMER_CREATED", entity_name="Customer", record_id=customer.id, new_values=customer.to_dict())
    return jsonify({"status": "success", "message": "Customer created successfully.", "data": customer.to_dict()}), 201


@api_bp.route('/customers/<int:id>', methods=['PUT'])
@api_auth_required
def update_customer(id):
    """PUT /api/customers/<id>: Update an existing customer."""
    customer = db.session.get(Customer, id)
    if not customer:
        return jsonify({"status": "error", "message": f"Customer with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and customer.created_by_id != current_user.id:
        return jsonify({"status": "error", "message": "Access forbidden: you do not own this customer record."}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON or missing request body."}), 400

    old_data = customer.to_dict()

    if 'email' in data:
        new_email = data['email'].strip().lower()
        conflict = Customer.query.filter(Customer.email == new_email, Customer.id != customer.id).first()
        if conflict:
            return jsonify({"status": "error", "message": "Email is already taken by another customer."}), 400
        customer.email = new_email

    if 'phone' in data:
        new_phone = data['phone'].strip()
        conflict = Customer.query.filter(Customer.phone == new_phone, Customer.id != customer.id).first()
        if conflict:
            return jsonify({"status": "error", "message": "Phone number is already taken by another customer."}), 400
        customer.phone = new_phone

    if 'name' in data and data['name'].strip():
        customer.name = data['name'].strip()
    if 'company_name' in data:
        customer.company_name = data['company_name']
    if 'address' in data:
        customer.address = data['address']
    if 'city' in data:
        customer.city = data['city']
    if 'state' in data:
        customer.state = data['state']
    if 'status' in data:
        customer.status = data['status']

    db.session.commit()
    log_audit("API_CUSTOMER_UPDATED", entity_name="Customer", record_id=customer.id, old_values=old_data, new_values=customer.to_dict())

    return jsonify({"status": "success", "message": "Customer updated successfully.", "data": customer.to_dict()}), 200


@api_bp.route('/customers/<int:id>', methods=['DELETE'])
@api_auth_required
def delete_customer(id):
    """DELETE /api/customers/<id>: Delete a customer."""
    customer = db.session.get(Customer, id)
    if not customer:
        return jsonify({"status": "error", "message": f"Customer with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive':
        return jsonify({"status": "error", "message": "Forbidden: Sales Executives cannot delete customer records."}), 403

    old_data = customer.to_dict()
    db.session.delete(customer)
    db.session.commit()

    log_audit("API_CUSTOMER_DELETED", entity_name="Customer", record_id=id, old_values=old_data)
    return jsonify({"status": "success", "message": f"Customer {id} deleted successfully."}), 200


# ==============================================================
# LEAD API ENDPOINTS
# ==============================================================

@api_bp.route('/leads', methods=['GET'])
@api_auth_required
def get_leads():
    """GET /api/leads: Retrieve leads."""
    query = Lead.query
    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    leads = query.order_by(Lead.created_at.desc()).all()
    return jsonify({
        "status": "success",
        "count": len(leads),
        "data": [l.to_dict() for l in leads]
    }), 200


@api_bp.route('/leads/<int:id>', methods=['GET'])
@api_auth_required
def get_lead(id):
    """GET /api/leads/<id>: Retrieve single lead."""
    lead = db.session.get(Lead, id)
    if not lead:
        return jsonify({"status": "error", "message": f"Lead with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and lead.assigned_user_id != current_user.id:
        return jsonify({"status": "error", "message": "Forbidden: record not assigned to you."}), 403

    return jsonify({"status": "success", "data": lead.to_dict()}), 200


@api_bp.route('/leads', methods=['POST'])
@api_auth_required
def create_lead():
    """POST /api/leads: Create a new lead."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON or missing body."}), 400

    name = data.get('name', '').strip()
    email = data.get('email', '').strip().lower()
    phone = data.get('phone', '').strip()

    if not name or not email or not phone:
        return jsonify({"status": "error", "message": "name, email, and phone are required."}), 400

    code = generate_lead_code()
    lead = Lead(
        lead_code=code,
        name=name,
        email=email,
        phone=phone,
        company_name=data.get('company_name'),
        source=data.get('source', 'Website'),
        status=data.get('status', 'New'),
        expected_value=float(data.get('expected_value', 0.0)),
        assigned_user_id=data.get('assigned_user_id') or current_user.id
    )
    db.session.add(lead)
    db.session.commit()

    log_audit("API_LEAD_CREATED", entity_name="Lead", record_id=lead.id, new_values=lead.to_dict())
    return jsonify({"status": "success", "message": "Lead created.", "data": lead.to_dict()}), 201


@api_bp.route('/leads/<int:id>', methods=['PUT'])
@api_auth_required
def update_lead(id):
    """PUT /api/leads/<id>: Update lead details."""
    lead = db.session.get(Lead, id)
    if not lead:
        return jsonify({"status": "error", "message": f"Lead with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and lead.assigned_user_id != current_user.id:
        return jsonify({"status": "error", "message": "Forbidden."}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON."}), 400

    old_data = lead.to_dict()
    if 'name' in data:
        lead.name = data['name'].strip()
    if 'email' in data:
        lead.email = data['email'].strip().lower()
    if 'phone' in data:
        lead.phone = data['phone'].strip()
    if 'company_name' in data:
        lead.company_name = data['company_name']
    if 'source' in data:
        lead.source = data['source']
    if 'status' in data:
        lead.status = data['status']
    if 'expected_value' in data:
        lead.expected_value = float(data['expected_value'])

    db.session.commit()
    log_audit("API_LEAD_UPDATED", entity_name="Lead", record_id=lead.id, old_values=old_data, new_values=lead.to_dict())
    return jsonify({"status": "success", "message": "Lead updated.", "data": lead.to_dict()}), 200


@api_bp.route('/leads/<int:id>', methods=['DELETE'])
@api_auth_required
def delete_lead(id):
    """DELETE /api/leads/<id>: Delete lead."""
    lead = db.session.get(Lead, id)
    if not lead:
        return jsonify({"status": "error", "message": f"Lead with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive':
        return jsonify({"status": "error", "message": "Forbidden."}), 403

    old_data = lead.to_dict()
    db.session.delete(lead)
    db.session.commit()
    log_audit("API_LEAD_DELETED", entity_name="Lead", record_id=id, old_values=old_data)
    return jsonify({"status": "success", "message": f"Lead {id} deleted."}), 200


# ==============================================================
# OPPORTUNITY API ENDPOINTS
# ==============================================================

@api_bp.route('/opportunities', methods=['GET'])
@api_auth_required
def get_opportunities():
    """GET /api/opportunities: Retrieve list of opportunities."""
    query = Opportunity.query
    if current_user.role == 'SalesExecutive':
        query = query.filter_by(assigned_user_id=current_user.id)

    opps = query.order_by(Opportunity.expected_close_date.asc()).all()
    return jsonify({
        "status": "success",
        "count": len(opps),
        "data": [o.to_dict() for o in opps]
    }), 200


@api_bp.route('/opportunities/<int:id>', methods=['GET'])
@api_auth_required
def get_opportunity(id):
    """GET /api/opportunities/<id>: Retrieve single opportunity."""
    opp = db.session.get(Opportunity, id)
    if not opp:
        return jsonify({"status": "error", "message": f"Opportunity with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and opp.assigned_user_id != current_user.id:
        return jsonify({"status": "error", "message": "Forbidden."}), 403

    return jsonify({"status": "success", "data": opp.to_dict()}), 200


@api_bp.route('/opportunities', methods=['POST'])
@api_auth_required
def create_opportunity():
    """POST /api/opportunities: Create new opportunity with validation."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON or missing body."}), 400

    name = data.get('name', '').strip()
    customer_id = data.get('customer_id')
    amount = float(data.get('amount', 0))
    stage = data.get('stage', 'Qualification')
    prob = int(data.get('probability', 10))
    close_str = data.get('expected_close_date')

    if not name or not customer_id or not close_str:
        return jsonify({"status": "error", "message": "name, customer_id, and expected_close_date are required."}), 400

    if amount <= 0:
        return jsonify({"status": "error", "message": "amount must be greater than zero."}), 400

    if prob < 0 or prob > 100:
        return jsonify({"status": "error", "message": "probability must be between 0 and 100."}), 400

    # Verify customer exists
    if not Customer.query.get(customer_id):
        return jsonify({"status": "error", "message": f"Customer {customer_id} does not exist."}), 400

    try:
        close_date = datetime.strptime(close_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"status": "error", "message": "expected_close_date must be in YYYY-MM-DD format."}), 400

    if stage in ['Qualification', 'Proposal', 'Negotiation'] and close_date < date.today():
        return jsonify({"status": "error", "message": "expected_close_date cannot be in the past for active opportunities."}), 400

    status = 'Won' if stage == 'Won' else ('Lost' if stage == 'Lost' else 'Open')
    opp = Opportunity(
        name=name,
        customer_id=customer_id,
        lead_id=data.get('lead_id'),
        amount=amount,
        stage=stage,
        probability=prob,
        expected_close_date=close_date,
        status=status,
        assigned_user_id=data.get('assigned_user_id') or current_user.id
    )
    db.session.add(opp)
    db.session.commit()

    log_audit("API_OPPORTUNITY_CREATED", entity_name="Opportunity", record_id=opp.id, new_values=opp.to_dict())
    return jsonify({"status": "success", "message": "Opportunity created.", "data": opp.to_dict()}), 201


@api_bp.route('/opportunities/<int:id>', methods=['PUT'])
@api_auth_required
def update_opportunity(id):
    """PUT /api/opportunities/<id>: Update opportunity."""
    opp = db.session.get(Opportunity, id)
    if not opp:
        return jsonify({"status": "error", "message": f"Opportunity with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive' and opp.assigned_user_id != current_user.id:
        return jsonify({"status": "error", "message": "Forbidden."}), 403

    data = request.get_json(silent=True)
    if not data:
        return jsonify({"status": "error", "message": "Invalid JSON."}), 400

    old_data = opp.to_dict()

    if 'name' in data:
        opp.name = data['name'].strip()
    if 'amount' in data:
        amt = float(data['amount'])
        if amt <= 0:
            return jsonify({"status": "error", "message": "amount must be greater than zero."}), 400
        opp.amount = amt
    if 'probability' in data:
        p = int(data['probability'])
        if p < 0 or p > 100:
            return jsonify({"status": "error", "message": "probability must be 0-100."}), 400
        opp.probability = p
    if 'stage' in data:
        stg = data['stage']
        opp.stage = stg
        if stg == 'Won':
            opp.status = 'Won'
            opp.probability = 100
        elif stg == 'Lost':
            opp.status = 'Lost'
            opp.probability = 0
        else:
            opp.status = 'Open'

    if 'expected_close_date' in data:
        try:
            close_date = datetime.strptime(data['expected_close_date'], '%Y-%m-%d').date()
            if opp.status == 'Open' and close_date < date.today():
                return jsonify({"status": "error", "message": "expected_close_date cannot be in the past for active deals."}), 400
            opp.expected_close_date = close_date
        except ValueError:
            return jsonify({"status": "error", "message": "expected_close_date must be YYYY-MM-DD."}), 400

    db.session.commit()
    log_audit("API_OPPORTUNITY_UPDATED", entity_name="Opportunity", record_id=opp.id, old_values=old_data, new_values=opp.to_dict())
    return jsonify({"status": "success", "message": "Opportunity updated.", "data": opp.to_dict()}), 200


@api_bp.route('/opportunities/<int:id>', methods=['DELETE'])
@api_auth_required
def delete_opportunity(id):
    """DELETE /api/opportunities/<id>: Delete opportunity."""
    opp = db.session.get(Opportunity, id)
    if not opp:
        return jsonify({"status": "error", "message": f"Opportunity with id {id} not found."}), 404

    if current_user.role == 'SalesExecutive':
        return jsonify({"status": "error", "message": "Forbidden."}), 403

    old_data = opp.to_dict()
    db.session.delete(opp)
    db.session.commit()
    log_audit("API_OPPORTUNITY_DELETED", entity_name="Opportunity", record_id=id, old_values=old_data)
    return jsonify({"status": "success", "message": f"Opportunity {id} deleted."}), 200


# ==============================================================
# DASHBOARD STATS API
# ==============================================================

@api_bp.route('/dashboard/stats', methods=['GET'])
@api_auth_required
def get_dashboard_stats():
    """GET /api/dashboard/stats: Return calculated 8 KPIs for live updates."""
    is_exec = (current_user.role == 'SalesExecutive')

    cust_q = Customer.query
    if is_exec:
        cust_q = cust_q.filter_by(created_by_id=current_user.id)

    lead_q = Lead.query
    if is_exec:
        lead_q = lead_q.filter_by(assigned_user_id=current_user.id)

    opp_q = Opportunity.query
    if is_exec:
        opp_q = opp_q.filter_by(assigned_user_id=current_user.id)

    all_opps = opp_q.all()
    weighted_pipeline = sum(o.weighted_value for o in all_opps if o.status == 'Open')

    return jsonify({
        "status": "success",
        "kpis": {
            "total_customers": cust_q.count(),
            "total_leads": lead_q.count(),
            "open_leads": lead_q.filter(Lead.status.in_(['New', 'Contacted', 'Qualified'])).count(),
            "total_opportunities": opp_q.count(),
            "open_opportunities": opp_q.filter_by(status='Open').count(),
            "won_opportunities": opp_q.filter_by(status='Won').count(),
            "lost_opportunities": opp_q.filter_by(status='Lost').count(),
            "total_pipeline_value": round(weighted_pipeline, 2)
        }
    }), 200
