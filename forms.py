"""
WTForms definitions for server-side validation and CSRF protection.
"""
from datetime import date, datetime
from flask_wtf import FlaskForm
from wtforms import (
    StringField, PasswordField, BooleanField, SelectField, 
    DecimalField, IntegerField, DateField, DateTimeLocalField, 
    TextAreaField, SubmitField
)
from wtforms.validators import (
    DataRequired, Email, Length, EqualTo, NumberRange, 
    Optional, ValidationError
)

class LoginForm(FlaskForm):
    """User login form."""
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required.")
    ])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    """New user self-registration form (safe default role: SalesExecutive)."""
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100, message="Name must be between 2 and 100 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    password = PasswordField('Password', validators=[
        DataRequired(message="Password is required."),
        Length(min=8, message="Password must be at least 8 characters long.")
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(message="Please confirm your password."),
        EqualTo('password', message="Passwords must match.")
    ])
    submit = SubmitField('Create Account')


class CustomerForm(FlaskForm):
    """Customer creation and edit form."""
    name = StringField('Customer / Contact Name', validators=[
        DataRequired(message="Customer name is required."),
        Length(min=2, max=120, message="Name must be between 2 and 120 characters.")
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=7, max=30, message="Phone number must be at least 7 digits.")
    ])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=150)])
    address = StringField('Street Address', validators=[Optional(), Length(max=255)])
    city = StringField('City', validators=[Optional(), Length(max=100)])
    state = StringField('State / Province', validators=[Optional(), Length(max=100)])
    status = SelectField('Status', choices=[
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
        ('Lead', 'Lead')
    ], default='Active')
    submit = SubmitField('Save Customer')


class LeadForm(FlaskForm):
    """Lead creation and edit form."""
    name = StringField('Lead Name', validators=[
        DataRequired(message="Lead name is required."),
        Length(min=2, max=120)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    phone = StringField('Phone Number', validators=[
        DataRequired(message="Phone number is required."),
        Length(min=7, max=30)
    ])
    company_name = StringField('Company Name', validators=[Optional(), Length(max=150)])
    source = SelectField('Lead Source', choices=[
        ('Website', 'Website'),
        ('Referral', 'Referral'),
        ('Cold Call', 'Cold Call'),
        ('Social Media', 'Social Media'),
        ('Advertisement', 'Advertisement'),
        ('Partner', 'Partner'),
        ('Other', 'Other')
    ], default='Website')
    status = SelectField('Lead Status', choices=[
        ('New', 'New'),
        ('Contacted', 'Contacted'),
        ('Qualified', 'Qualified'),
        ('Unqualified', 'Unqualified'),
        ('Converted', 'Converted'),
        ('Lost', 'Lost')
    ], default='New')
    expected_value = DecimalField('Expected Value ($)', validators=[
        Optional(),
        NumberRange(min=0, message="Expected value cannot be negative.")
    ], default=0.00)
    assigned_user_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Lead')


class OpportunityForm(FlaskForm):
    """Sales Opportunity creation and edit form."""
    name = StringField('Opportunity Name', validators=[
        DataRequired(message="Opportunity name is required."),
        Length(min=2, max=150)
    ])
    customer_id = SelectField('Associated Customer', coerce=int, validators=[
        DataRequired(message="Customer association is required.")
    ])
    lead_id = SelectField('Originating Lead (Optional)', coerce=int, validators=[Optional()])
    amount = DecimalField('Amount ($)', validators=[
        DataRequired(message="Amount is required."),
        NumberRange(min=0.01, message="Active opportunity amount must be greater than zero.")
    ])
    stage = SelectField('Stage', choices=[
        ('Qualification', 'Qualification'),
        ('Proposal', 'Proposal'),
        ('Negotiation', 'Negotiation'),
        ('Won', 'Won'),
        ('Lost', 'Lost')
    ], default='Qualification')
    probability = IntegerField('Probability (%)', validators=[
        DataRequired(message="Probability is required."),
        NumberRange(min=0, max=100, message="Probability must be between 0% and 100%.")
    ], default=10)
    expected_close_date = DateField('Expected Close Date', validators=[
        DataRequired(message="Expected close date is required.")
    ])
    assigned_user_id = SelectField('Assigned Sales Rep', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Opportunity')

    def validate_expected_close_date(self, field):
        """Active opportunities must not have an invalid past expected close date upon creation/edit."""
        # Only enforce on active stages (not Won or Lost historical records)
        if self.stage.data in ['Qualification', 'Proposal', 'Negotiation']:
            if field.data and field.data < date.today():
                raise ValidationError("Expected close date cannot be in the past for active opportunities.")


class FollowUpForm(FlaskForm):
    """Follow-up scheduling form."""
    customer_id = SelectField('Customer (Optional)', coerce=int, validators=[Optional()])
    lead_id = SelectField('Lead (Optional)', coerce=int, validators=[Optional()])
    followup_date = DateTimeLocalField('Scheduled Date & Time', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="Follow-up date and time is required.")
    ])
    followup_type = SelectField('Follow-up Type', choices=[
        ('Call', 'Call'),
        ('Email', 'Email'),
        ('Meeting', 'Meeting'),
        ('Demo', 'Demo')
    ], default='Call')
    remarks = TextAreaField('Remarks / Agenda', validators=[Optional(), Length(max=500)])
    status = SelectField('Status', choices=[
        ('Planned', 'Planned'),
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
        ('Rescheduled', 'Rescheduled')
    ], default='Planned')
    assigned_user_id = SelectField('Assigned To', coerce=int, validators=[Optional()])
    submit = SubmitField('Save Follow-up')

    def validate_followup_date(self, field):
        """Newly planned follow-ups must be scheduled for today or in the future."""
        if self.status.data in ['Planned', 'Pending']:
            if field.data and field.data < datetime.now().replace(second=0, microsecond=0):
                # Allow a small 5 minute grace period for form filling
                diff = datetime.now() - field.data
                if diff.total_seconds() > 300:
                    raise ValidationError("Scheduled follow-up date and time cannot be in the past.")


class ActivityForm(FlaskForm):
    """Activity log form."""
    activity_type = SelectField('Activity Type', choices=[
        ('Call', 'Call'),
        ('Meeting', 'Meeting'),
        ('Email', 'Email'),
        ('Task', 'Task')
    ], default='Task')
    subject = StringField('Subject', validators=[
        DataRequired(message="Subject is required."),
        Length(min=2, max=150)
    ])
    description = TextAreaField('Description / Notes', validators=[Optional()])
    activity_date = DateTimeLocalField('Activity Date & Time', format='%Y-%m-%dT%H:%M', validators=[
        DataRequired(message="Activity date and time is required.")
    ])
    customer_id = SelectField('Customer (Optional)', coerce=int, validators=[Optional()])
    lead_id = SelectField('Lead (Optional)', coerce=int, validators=[Optional()])
    status = SelectField('Status', choices=[
        ('Planned', 'Planned'),
        ('In Progress', 'In Progress'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled')
    ], default='Completed')
    assigned_user_id = SelectField('Assigned User', coerce=int, validators=[Optional()])
    submit = SubmitField('Log Activity')


class UserEditForm(FlaskForm):
    """Admin user profile & role management form."""
    name = StringField('Full Name', validators=[
        DataRequired(message="Name is required."),
        Length(min=2, max=100)
    ])
    email = StringField('Email Address', validators=[
        DataRequired(message="Email is required."),
        Email(message="Please enter a valid email address.")
    ])
    role = SelectField('System Role', choices=[
        ('Admin', 'Administrator'),
        ('Manager', 'Manager'),
        ('SalesExecutive', 'Sales Executive')
    ], default='SalesExecutive')
    is_active = BooleanField('Account Active')
    new_password = PasswordField('Reset Password (leave blank to keep current)', validators=[
        Optional(),
        Length(min=8, message="New password must be at least 8 characters long.")
    ])
    submit = SubmitField('Update User')


class ConvertLeadForm(FlaskForm):
    """Lead conversion modal form."""
    customer_action = SelectField('Customer Destination', choices=[
        ('new', 'Create New Customer from Lead details'),
        ('existing', 'Link to an Existing Customer')
    ], default='new')
    existing_customer_id = SelectField('Select Existing Customer', coerce=int, validators=[Optional()])
    create_opportunity = BooleanField('Also Create an Opportunity in Pipeline', default=True)
    opportunity_name = StringField('Opportunity Name', validators=[Optional(), Length(max=150)])
    opportunity_amount = DecimalField('Deal Amount ($)', validators=[Optional(), NumberRange(min=0.01)])
    expected_close_date = DateField('Expected Close Date', validators=[Optional()])
    submit = SubmitField('Confirm Conversion')
