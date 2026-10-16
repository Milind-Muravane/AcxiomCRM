"""
Main application routes: Landing redirect and CRM Dashboard with 8 KPI cards and Chart.js analytics.
"""
import json
from datetime import datetime, timedelta
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from models import db, Customer, Lead, Opportunity, FollowUp, Activity

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Root redirect to dashboard if logged in, else to login page."""
    if current_user.is_authenticated:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))

@main_bp.route('/dashboard')
@login_required
def dashboard():
    """
    CRM Dashboard displaying:
    - 8 Real KPI cards calculated from MySQL
    - 3 Chart.js data streams:
        1. Lead Status Distribution
        2. Opportunity Pipeline Stages
        3. Monthly Sales / Outcomes
    - Recent activities and pending follow-ups
    """
    # Base queries (Admins and Managers see company-wide stats; SalesExecutives see their portfolio)
    is_exec = (current_user.role == 'SalesExecutive')
    
    # 1. Total Customers
    cust_q = Customer.query
    if is_exec:
        cust_q = cust_q.filter_by(created_by_id=current_user.id)
    total_customers = cust_q.count()

    # 2. Total Leads
    lead_q = Lead.query
    if is_exec:
        lead_q = lead_q.filter_by(assigned_user_id=current_user.id)
    total_leads = lead_q.count()

    # 3. Open Leads (New, Contacted, Qualified)
    open_lead_q = Lead.query.filter(Lead.status.in_(['New', 'Contacted', 'Qualified']))
    if is_exec:
        open_lead_q = open_lead_q.filter_by(assigned_user_id=current_user.id)
    open_leads = open_lead_q.count()

    # 4. Total Opportunities
    opp_q = Opportunity.query
    if is_exec:
        opp_q = opp_q.filter_by(assigned_user_id=current_user.id)
    total_opportunities = opp_q.count()

    # 5. Open Opportunities
    open_opp_q = Opportunity.query.filter_by(status='Open')
    if is_exec:
        open_opp_q = open_opp_q.filter_by(assigned_user_id=current_user.id)
    open_opportunities = open_opp_q.count()

    # 6. Won Opportunities
    won_opp_q = Opportunity.query.filter_by(status='Won')
    if is_exec:
        won_opp_q = won_opp_q.filter_by(assigned_user_id=current_user.id)
    won_opportunities = won_opp_q.count()

    # 7. Lost Opportunities
    lost_opp_q = Opportunity.query.filter_by(status='Lost')
    if is_exec:
        lost_opp_q = lost_opp_q.filter_by(assigned_user_id=current_user.id)
    lost_opportunities = lost_opp_q.count()

    # 8. Total Pipeline Value (Weighted Pipeline: Sum(Amount * Probability / 100))
    all_opps = opp_q.all()
    # Calculate weighted value sum for open / active opportunities
    total_pipeline_value = sum(opp.weighted_value for opp in all_opps if opp.status == 'Open')
    total_pipeline_value = round(total_pipeline_value, 2)

    # ==========================================
    # CHART 1: Lead Status Distribution
    # ==========================================
    lead_statuses = ['New', 'Contacted', 'Qualified', 'Unqualified', 'Converted', 'Lost']
    lead_status_counts = []
    for st in lead_statuses:
        q = Lead.query.filter_by(status=st)
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        lead_status_counts.append(q.count())

    chart1_data = {
        'labels': lead_statuses,
        'counts': lead_status_counts
    }

    # ==========================================
    # CHART 2: Opportunity Pipeline Stages
    # ==========================================
    stages = ['Qualification', 'Proposal', 'Negotiation', 'Won', 'Lost']
    stage_counts = []
    stage_values = []
    for stg in stages:
        q = Opportunity.query.filter_by(stage=stg)
        if is_exec:
            q = q.filter_by(assigned_user_id=current_user.id)
        opps_in_stage = q.all()
        stage_counts.append(len(opps_in_stage))
        stage_val = sum(float(o.amount) for o in opps_in_stage)
        stage_values.append(round(stage_val, 2))

    chart2_data = {
        'labels': stages,
        'counts': stage_counts,
        'values': stage_values
    }

    # ==========================================
    # CHART 3: Monthly Sales / Opportunity Outcomes
    # Past 6 calendar months
    # ==========================================
    month_labels = []
    monthly_won = []
    monthly_lost = []
    
    current_date = datetime.now()
    # Build list of previous 6 months
    for i in range(5, -1, -1):
        # Subtract months
        year = current_date.year
        month = current_date.month - i
        while month <= 0:
            month += 12
            year -= 1
        
        month_name = datetime(year, month, 1).strftime('%b %Y')
        month_labels.append(month_name)

        # Query won amount in this month
        q_won = Opportunity.query.filter(
            Opportunity.status == 'Won',
            extract('year', Opportunity.created_at) == year,
            extract('month', Opportunity.created_at) == month
        )
        if is_exec:
            q_won = q_won.filter_by(assigned_user_id=current_user.id)
        won_sum = sum(float(o.amount) for o in q_won.all())
        monthly_won.append(round(won_sum, 2))

        # Query lost amount in this month
        q_lost = Opportunity.query.filter(
            Opportunity.status == 'Lost',
            extract('year', Opportunity.created_at) == year,
            extract('month', Opportunity.created_at) == month
        )
        if is_exec:
            q_lost = q_lost.filter_by(assigned_user_id=current_user.id)
        lost_sum = sum(float(o.amount) for o in q_lost.all())
        monthly_lost.append(round(lost_sum, 2))

    chart3_data = {
        'labels': month_labels,
        'won': monthly_won,
        'lost': monthly_lost
    }

    # Upcoming follow-ups for quick action
    followup_q = FollowUp.query.filter(FollowUp.status.in_(['Planned', 'Pending'])).order_by(FollowUp.followup_date.asc())
    if is_exec:
        followup_q = followup_q.filter_by(assigned_user_id=current_user.id)
    upcoming_followups = followup_q.limit(5).all()

    # Recent activities
    activity_q = Activity.query.order_by(Activity.activity_date.desc())
    if is_exec:
        activity_q = activity_q.filter_by(assigned_user_id=current_user.id)
    recent_activities = activity_q.limit(5).all()

    return render_template(
        'dashboard.html',
        total_customers=total_customers,
        total_leads=total_leads,
        open_leads=open_leads,
        total_opportunities=total_opportunities,
        open_opportunities=open_opportunities,
        won_opportunities=won_opportunities,
        lost_opportunities=lost_opportunities,
        total_pipeline_value=total_pipeline_value,
        chart1_json=json.dumps(chart1_data),
        chart2_json=json.dumps(chart2_data),
        chart3_json=json.dumps(chart3_data),
        upcoming_followups=upcoming_followups,
        recent_activities=recent_activities
    )
