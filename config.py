import os
from dotenv import load_dotenv

# Load variables from .env file if present
load_dotenv()

class Config:
    """Base application configuration loaded from environment variables."""
    SECRET_KEY = os.environ.get('SECRET_KEY', 'default-dev-secret-key-please-change')
    
    # MySQL Database URI via PyMySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL', 
        'mysql+pymysql://root:root@localhost:3306/acxiom_crm'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Engine options for MySQL connection reliability
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Security: Session Cookie Configuration
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    # In production, enable Secure cookie over HTTPS
    SESSION_COOKIE_SECURE = os.environ.get('FLASK_ENV') == 'production'
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    
    # Account Lockout Settings
    MAX_LOGIN_ATTEMPTS = int(os.environ.get('MAX_LOGIN_ATTEMPTS', 5))
    LOCKOUT_MINUTES = int(os.environ.get('LOCKOUT_MINUTES', 15))


class TestConfig(Config):
    """Configuration for automated test suite."""
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Use SQLite in-memory or a test database during pytest to allow fast and isolated tests
    SQLALCHEMY_DATABASE_URI = os.environ.get('TEST_DATABASE_URL', 'sqlite:///:memory:')
