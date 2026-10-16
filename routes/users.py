"""
User and Role Management routes (Restricted strictly to System Administrators).
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, User
from forms import UserEditForm
from helpers import admin_required, log_audit

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
@login_required
@admin_required
def list_users():
    """Admin dashboard for viewing and managing system users and roles."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('users.html', users=users)


@users_bp.route('/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user details, roles, and status with protection against self-deactivation."""
    user = User.query.get_or_404(user_id)
    form = UserEditForm(obj=user)

    if form.validate_on_submit():
        email = form.email.data.strip().lower()

        # Check unique email against others
        existing_email = User.query.filter(User.email == email, User.id != user.id).first()
        if existing_email:
            flash("Another user is already registered with this email.", "danger")
            return render_template('user_form.html', form=form, user=user)

        # Prevent admin from deactivating or demoting themselves
        if user.id == current_user.id:
            if not form.is_active.data:
                flash("Security rule: You cannot deactivate your own administrative account.", "danger")
                return render_template('user_form.html', form=form, user=user)
            if form.role.data != 'Admin':
                flash("Security rule: You cannot remove the Administrator role from yourself.", "danger")
                return render_template('user_form.html', form=form, user=user)

        old_data = user.to_dict()

        user.name = form.name.data.strip()
        user.email = email
        user.role = form.role.data
        user.is_active = form.is_active.data

        # If admin supplied a new password, update hash
        if form.new_password.data:
            user.set_password(form.new_password.data)
            log_audit("USER_PASSWORD_RESET_BY_ADMIN", entity_name="User", record_id=user.id, new_values={"email": user.email})

        db.session.commit()

        log_audit(
            action="USER_UPDATED",
            entity_name="User",
            record_id=user.id,
            old_values=old_data,
            new_values=user.to_dict()
        )

        flash(f"User {user.email} updated successfully.", "success")
        return redirect(url_for('users.list_users'))

    return render_template('user_form.html', form=form, user=user)


@users_bp.route('/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_status(user_id):
    """Toggle active/inactive status of a user."""
    user = User.query.get_or_404(user_id)

    if user.id == current_user.id:
        flash("You cannot deactivate your own account.", "danger")
        return redirect(url_for('users.list_users'))

    old_status = user.is_active
    user.is_active = not user.is_active
    db.session.commit()

    log_audit(
        action="USER_STATUS_TOGGLED",
        entity_name="User",
        record_id=user.id,
        old_values={"is_active": old_status},
        new_values={"is_active": user.is_active}
    )

    action_label = "activated" if user.is_active else "deactivated"
    flash(f"User {user.email} has been {action_label}.", "info")
    return redirect(url_for('users.list_users'))
