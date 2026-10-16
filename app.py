"""
AcxiomCRM: Flask Application Factory and Central Entrypoint.
Initializes database, authentication manager, CSRF protection, blueprints, and error handlers.
"""
from datetime import datetime
from flask import Flask, render_template, jsonify
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from config import Config
from models import db, User

# Initialize extensions
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = "Please sign in to access this page."
login_manager.login_message_category = "warning"
csrf = CSRFProtect()

@login_manager.user_loader
def load_user(user_id):
    """Load user instance by primary key ID for Flask-Login session."""
    return db.session.get(User, int(user_id))


def create_app(config_class=Config):
    """Flask application factory pattern."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions with app
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)

    # Register Blueprints
    from routes.auth import auth_bp
    from routes.main import main_bp
    from routes.customers import customers_bp
    from routes.leads import leads_bp
    from routes.opportunities import opportunities_bp
    from routes.followups import followups_bp
    from routes.activities import activities_bp
    from routes.users import users_bp
    from routes.reports import reports_bp
    from routes.audit import audit_bp
    from routes.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(customers_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(opportunities_bp)
    app.register_blueprint(followups_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(users_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(audit_bp)

    # Keep CSRF protection enabled for the API.
    app.register_blueprint(api_bp)

    # Global context processors for templates
    @app.context_processor
    def inject_globals():
        return {
            'now': datetime.utcnow(),
            'current_year': datetime.now().year,
            'app_name': 'AcxiomCRM'
        }

    # Custom Error Handlers
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True)
