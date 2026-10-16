"""
Authentication routes: login, registration, logout, lockout handling, and password security.
"""
from datetime import datetime, timedelta, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from models import db, User, utc_now
from forms import LoginForm, RegisterForm
from helpers import log_audit

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Handle user authentication with lockout protection."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()
        password = form.password.data

        user = User.query.filter_by(email=email).first()

        # Check account lockout before verifying credentials
        if user and user.is_locked():
            remaining_minutes = int((user.locked_until - utc_now()).total_seconds() / 60) + 1
            flash(f"Account is temporarily locked due to repeated failed attempts. Please try again in {remaining_minutes} minute(s).", "danger")
            log_audit("LOGIN_LOCKED_ATTEMPT", entity_name="User", record_id=user.id, new_values={"email": email})
            return render_template('login.html', form=form)

        # Verify password
        if user and user.check_password(password):
            if not user.is_active:
                flash("Your account has been deactivated. Please contact an Administrator.", "warning")
                log_audit("LOGIN_INACTIVE_ATTEMPT", entity_name="User", record_id=user.id, new_values={"email": email})
                return render_template('login.html', form=form)

            # Successful login: reset failed counters
            user.failed_login_attempts = 0
            user.locked_until = None
            db.session.commit()

            login_user(user, remember=form.remember.data)
            log_audit("LOGIN_SUCCESS", entity_name="User", record_id=user.id, new_values={"email": email})

            flash(f"Welcome back, {user.name}!", "success")
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('main.dashboard'))
        else:
            # Handle failed login attempt
            if user:
                user.failed_login_attempts += 1
                max_attempts = current_app.config.get('MAX_LOGIN_ATTEMPTS', 5)
                lockout_minutes = current_app.config.get('LOCKOUT_MINUTES', 15)

                if user.failed_login_attempts >= max_attempts:
                    user.locked_until = utc_now() + timedelta(minutes=lockout_minutes)
                    db.session.commit()
                    log_audit("ACCOUNT_LOCKED", entity_name="User", record_id=user.id, new_values={"email": email})
                    flash(f"Account locked due to {max_attempts} failed login attempts. Try again in {lockout_minutes} minutes.", "danger")
                    return render_template('login.html', form=form)
                else:
                    db.session.commit()

            # Generic error message to prevent user enumeration
            log_audit("LOGIN_FAILED", entity_name="User", new_values={"attempted_email": email})
            flash("Invalid email or password.", "danger")

    return render_template('login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Handle new user self-registration with safe default role (SalesExecutive)."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))

    form = RegisterForm()
    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        # Check if email is already taken
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("An account with this email already exists. Please sign in or use another email.", "warning")
            return render_template('register.html', form=form)

        # Create new user with safe default role 'SalesExecutive'
        new_user = User(
            name=form.name.data.strip(),
            email=email,
            role='SalesExecutive',
            is_active=True
        )
        new_user.set_password(form.password.data)

        db.session.add(new_user)
        db.session.commit()

        log_audit("USER_REGISTERED", entity_name="User", record_id=new_user.id, new_values={"email": email, "role": "SalesExecutive"})
        flash("Registration successful! You may now sign in.", "success")
        return redirect(url_for('auth.login'))

    return render_template('register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out current user and end session."""
    user_id = current_user.id
    user_email = current_user.email
    logout_user()
    log_audit("LOGOUT", entity_name="User", record_id=user_id, new_values={"email": user_email})
    flash("You have been signed out successfully.", "info")
    return redirect(url_for('auth.login'))
