# AcxiomCRM: Beginner-Friendly Assessment & Modification Guide

This guide is written specifically for you to prepare for, explain, and confidently make modifications during a practical coding assessment.

---

## 1. Core Architecture: How It Works

### 1.1 How the Flask Application Starts
1. When you execute `python app.py`:
2. `create_app()` in `app.py` is invoked.
3. It loads settings from `config.py` (which reads your `.env` file).
4. Extensions are initialized:
   - `db.init_app(app)` sets up SQLAlchemy with MySQL.
   - `login_manager.init_app(app)` configures user session handling.
   - `csrf.init_app(app)` activates CSRF token protection for HTML forms.
5. Blueprints (modular route groups like `auth_bp`, `customers_bp`, `api_bp`) are registered onto the app.
6. Werkzeug dev server starts listening on `http://127.0.0.1:5000`.

### 1.2 How a Browser Request Reaches a Route
1. The user navigates to a URL (e.g., `http://127.0.0.1:5000/customers/`).
2. Flask inspects the URL path (`/customers/`) and HTTP method (`GET`).
3. Flask matches this path to the blueprint route decorator `@customers_bp.route('/')`.
4. Any decorators on the function are executed in order:
   - `@login_required`: Checks if the user is authenticated. If not, redirects to `/login`.
   - `@role_required(...)`: Checks if `current_user.role` matches allowed roles.
5. The view function `list_customers()` runs its Python logic and returns an HTML template rendered with Jinja2.

### 1.3 How a Route Reads & Writes Database Records
- **Reading records**:
  ```python
  # Get all active customers
  customers = Customer.query.filter_by(status='Active').all()

  # Get a single record by Primary Key ID
  customer = db.session.get(Customer, customer_id)
  ```
- **Writing new records**:
  ```python
  new_customer = Customer(name="Acme Corp", email="acme@corp.com", phone="1234567")
  db.session.add(new_customer)
  db.session.commit()
  ```
- **Updating records**:
  ```python
  customer = db.session.get(Customer, customer_id)
  customer.name = "Updated Name"
  db.session.commit()
  ```
- **Deleting records**:
  ```python
  customer = db.session.get(Customer, customer_id)
  db.session.delete(customer)
  db.session.commit()
  ```

### 1.4 How SQLAlchemy Models Work
- In `models.py`, each class inherits from `db.Model`.
- Each attribute maps to a column in MySQL:
  ```python
  class Customer(db.Model):
      __tablename__ = 'customers'
      id = db.Column(db.Integer, primary_key=True)
      name = db.Column(db.String(120), nullable=False)
      email = db.Column(db.String(120), unique=True, nullable=False)
  ```
- Foreign keys establish relational integrity:
  `created_by_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='SET NULL'))`

### 1.5 How HTML Templates Display Records
- Templates are stored in `/templates` and use Jinja2 syntax.
- Variables passed from the route:
  ```python
  return render_template('customers.html', customers=customers)
  ```
- Jinja renders variables using `{{ variable }}` and control flow:
  ```html
  {% for c in customers %}
    <tr>
      <td>{{ c.name }}</td>
      <td>{{ c.email }}</td>
    </tr>
  {% endfor %}
  ```

### 1.6 How Flask-Login Manages Authentication
- When a user logs in: `login_user(user, remember=True)` stores `user.id` in a cryptographically signed browser session cookie.
- On subsequent requests, Flask-Login calls `@login_manager.user_loader`:
  ```python
  @login_manager.user_loader
  def load_user(user_id):
      return db.session.get(User, int(user_id))
  ```
  This makes `current_user` available in every route and Jinja template.

### 1.7 How Password Hashing Works
- We **never store plaintext passwords**.
- `generate_password_hash("MySecretPassword")` creates a salted hash string like `scrypt:32768:8:1$...`.
- When logging in, `check_password_hash(user.password_hash, entered_password)` hashes the entered text with the stored salt and returns `True` or `False`.

### 1.8 How Roles and Authorization Work
- The `User` model has a `role` column (`Admin`, `Manager`, `SalesExecutive`).
- Public registration assigns `SalesExecutive` by default.
- Custom decorators in `helpers.py`:
  ```python
  @admin_required
  def list_users():
      ...
  ```
- Record-level authorization in `helpers.py` ensures sales reps can only see or edit records where `assigned_user_id == current_user.id` or `created_by_id == current_user.id`.

### 1.9 How Input Validation Works
- Handled at two levels:
  1. **Flask-WTF Form validators** (`DataRequired`, `Email`, `Length`, `NumberRange`).
  2. **Server-side database checks** in route handlers to verify unique emails/phones and prevent past close dates on active deals.

### 1.10 How Dashboard Metrics Are Calculated
- Real MySQL queries inside `routes/main.py`:
  - `total_customers = Customer.query.count()`
  - `open_leads = Lead.query.filter(Lead.status.in_(['New', 'Contacted', 'Qualified'])).count()`
  - Weighted Pipeline:
    $$\text{Weighted Value} = \sum (\text{Amount} \times \text{Probability} / 100)$$

### 1.11 How Chart.js Receives Data
1. In `routes/main.py`, Flask groups records and builds standard Python dictionaries:
   `chart1_data = {'labels': ['New', 'Contacted', ...], 'counts': [4, 2, ...]}`
2. Flask converts it to JSON string: `json.dumps(chart1_data)`.
3. In `templates/dashboard.html`, the JSON is passed to JavaScript:
   `<script>window.chart1Data = {{ chart1_json | safe }};</script>`
4. `static/js/dashboard.js` reads `window.chart1Data` and creates the Chart.js canvas instance.

### 1.12 How the REST API Works
- In `routes/api.py`, routes return Python dictionaries wrapped in `jsonify(...)` with HTTP status codes:
  ```python
  @api_bp.route('/customers', methods=['GET'])
  def get_customers():
      customers = Customer.query.all()
      return jsonify({"status": "success", "data": [c.to_dict() for c in customers]}), 200
  ```

### 1.13 How Audit Logs Are Generated
- In `helpers.py`, `log_audit(action, entity_name, record_id, old_values, new_values)` is called after successful state changes.
- It records who did what, when, IP address, and JSON diffs while strictly redacting sensitive fields (passwords, tokens).

---

## 2. Common Practical Assessment Modifications

Here are step-by-step examples of tasks you might be asked to perform:

### Modification 1: Add a New Field to Customer (e.g., `industry`)
1. **In `models.py`**, add the column:
   ```python
   industry = db.Column(db.String(100), nullable=True)
   ```
2. **In `forms.py`**, add the form field:
   ```python
   industry = StringField('Industry Sector', validators=[Optional(), Length(max=100)])
   ```
3. **In `templates/customer_form.html`**, add HTML input:
   ```html
   <div class="col-md-6">
     <label class="form-label fw-semibold">Industry</label>
     {{ form.industry(class="form-control", placeholder="Healthcare, Retail, etc.") }}
   </div>
   ```
4. **In `routes/customers.py`**:
   - In `create_customer()`: `industry=form.industry.data`
   - In `edit_customer()`: `customer.industry = form.industry.data`

---

### Modification 2: Add a Custom Validation Rule
*Example: Require customer phone numbers to have at least 10 digits.*

In `forms.py`:
```python
phone = StringField('Phone Number', validators=[
    DataRequired(message="Phone number is required."),
    Length(min=10, max=15, message="Phone number must be between 10 and 15 digits.")
])
```

---

### Modification 3: Add a Filter to a Listing Page
*Example: Filter opportunities by minimum dollar amount.*

In `routes/opportunities.py`:
```python
min_amount = request.args.get('min_amount', type=float)
if min_amount:
    query = query.filter(Opportunity.amount >= min_amount)
```
In `templates/opportunities.html`, add an input inside the filter form:
```html
<div class="col-md-2">
  <input type="number" name="min_amount" class="form-control" placeholder="Min $" value="{{ request.args.get('min_amount', '') }}">
</div>
```

---

### Modification 4: Restrict a Route to Admins Only
Use the `@admin_required` decorator from `helpers.py`:
```python
from helpers import admin_required

@customers_bp.route('/export-all')
@login_required
@admin_required
def export_all():
    # Only users with role == 'Admin' can reach here
    ...
```

---

### Modification 5: Add a New REST API Endpoint
*Example: Search customers by email via API.*

In `routes/api.py`:
```python
@api_bp.route('/customers/search', methods=['GET'])
@api_auth_required
def search_customer_by_email():
    email = request.args.get('email', '').strip().lower()
    customer = Customer.query.filter_by(email=email).first()
    if not customer:
        return jsonify({"status": "error", "message": "Customer not found"}), 404
    return jsonify({"status": "success", "data": customer.to_dict()}), 200
```

---

### Modification 6: Fix a Database Connection Error
If the app fails to connect to MySQL (`Can't connect to MySQL server on 'localhost'`):
1. Check if the MySQL service is running:
   ```powershell
   Get-Service MySQL*
   Start-Service MySQL80
   ```
2. Verify credentials in `.env`:
   `DATABASE_URL=mysql+pymysql://<user>:<password>@localhost:3306/<database>`
3. Test connection from Python:
   ```python
   import pymysql
   conn = pymysql.connect(host='localhost', user='root', password='root', database='acxiom_crm')
   print("Connected successfully!")
   ```

---

## 3. Likely Assessment Interview Questions & Model Answers

**Q1: Why did you use Werkzeug password hashing instead of storing passwords directly or using MD5?**
> *Answer:* Werkzeug uses secure cryptographic key derivation algorithms (like Scrypt or PBKDF2) with unique automatic salt generation for each password. This protects against rainbow table attacks and brute force cracking. Plaintext or MD5 are completely insecure.

**Q2: What is the purpose of CSRF tokens in Flask-WTF?**
> *Answer:* Cross-Site Request Forgery (CSRF) occurs when an unauthorized malicious site tricks a logged-in user's browser into submitting state-changing POST requests. Flask-WTF injects a unique, secret token into each form (`form.hidden_tag()`) and verifies it on the server, ensuring submissions come only from our genuine application pages.

**Q3: How do you prevent SQL Injection in this application?**
> *Answer:* We use SQLAlchemy ORM, which automatically parameterizes all SQL queries. User input is never concatenated directly into raw SQL strings; instead, it is passed as data parameters, neutralizing SQL injection vectors.

**Q4: How does the application handle account lockout?**
> *Answer:* Each failed login attempt increments `user.failed_login_attempts`. If it reaches 5, `user.locked_until` is set to 15 minutes in the future. The server rejects any login attempts for that account until the time expires, stopping automated brute-force attacks.

**Q5: How does Chart.js get live database data?**
> *Answer:* In the Flask route (`dashboard()`), we query MySQL using SQLAlchemy, compute the counts and totals using Python, format them into dictionary arrays, and pass them as JSON into the template. The client JavaScript (`dashboard.js`) reads this JSON to render dynamic charts.
