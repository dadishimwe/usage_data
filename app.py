# app.py
from flask import Flask, render_template, jsonify, Response, request
from flask_sqlalchemy import SQLAlchemy
from config import Config
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io
from weasyprint import HTML
from sklearn.linear_model import LinearRegression
import numpy as np

# Initialize the Flask app and configure it
app = Flask(__name__)
app.config.from_object(Config)
db = SQLAlchemy(app)

# --- Helper Function for Billing Cycles ---
def get_billing_cycle(target_date=None):
    if target_date is None:
        target_date = date.today()
    if target_date.day < 13:
        start_date = (target_date - relativedelta(months=1)).replace(day=13)
        end_date = target_date.replace(day=12)
    else:
        start_date = target_date.replace(day=13)
        end_date = (target_date + relativedelta(months=1)).replace(day=12)
    return start_date, end_date

def forecast_current_cycle_usage(client_id):
    """Forecasts the total usage for the current billing cycle."""
    cycle_start, cycle_end = get_billing_cycle()
    
    usage_records = DataUsage.query.filter(
        DataUsage.client_id == client_id,
        DataUsage.date >= cycle_start,
        DataUsage.date <= cycle_end
    ).order_by(DataUsage.date.asc()).all()

    if not usage_records:
        return 0.0

    days_so_far = np.array([(record.date - cycle_start).days + 1 for record in usage_records]).reshape(-1, 1)
    cumulative_usage = np.cumsum([record.usage_gb for record in usage_records])

    if len(days_so_far) < 2: # Not enough data to forecast
        return cumulative_usage[-1]

    model = LinearRegression()
    model.fit(days_so_far, cumulative_usage)

    total_days_in_cycle = (cycle_end - cycle_start).days + 1
    predicted_usage = model.predict(np.array([[total_days_in_cycle]]))[0]
    
    return max(predicted_usage, cumulative_usage[-1]) # Forecast can't be less than current usage

# --- Database Models ---
class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    monthly_limit_gb = db.Column(db.Float, nullable=False, default=1000.0)

class DataUsage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    usage_gb = db.Column(db.Float, nullable=False)
    client = db.relationship('Client', backref=db.backref('data_usages', lazy=True))

# --- HTML Page Routes ---
@app.route('/')
def dashboard():
    return render_template('index.html')

@app.route('/client/<int:client_id>')
def client_detail_page(client_id):
    client = Client.query.get_or_404(client_id)
    return render_template('client_detail.html', client=client)

# --- API Routes ---
@app.route('/api/clients')
def get_clients():
    clients = Client.query.all()
    client_data = []
    cycle_start_date, _ = get_billing_cycle()

    for client in clients:
        total_usage = db.session.query(db.func.sum(DataUsage.usage_gb)).filter(
            DataUsage.client_id == client.id,
            DataUsage.date >= cycle_start_date,
            DataUsage.date <= date.today()
        ).scalar() or 0.0
        
        usage_percentage = (total_usage / client.monthly_limit_gb) * 100 if client.monthly_limit_gb > 0 else 0
        
        client_data.append({
            'id': client.id,
            'name': client.name,
            'total_usage_gb': round(total_usage, 2),
            'monthly_limit_gb': client.monthly_limit_gb,
            'usage_percentage': round(usage_percentage, 2)
        })
    return jsonify(client_data)

@app.route('/api/client/<int:client_id>/usage/current')
def get_client_current_usage(client_id):
    cycle_start, cycle_end = get_billing_cycle()
    usage_records = DataUsage.query.filter(
        DataUsage.client_id == client_id,
        DataUsage.date >= cycle_start,
        DataUsage.date <= cycle_end
    ).order_by(DataUsage.date.asc()).all()
    
    labels = [record.date.strftime('%b %d') for record in usage_records]
    data = [record.usage_gb for record in usage_records]
    forecast = forecast_current_cycle_usage(client_id)
    
    return jsonify({
        'labels': labels, 
        'data': data, 
        'cycle_label': f"{cycle_start.strftime('%b %d')} - {cycle_end.strftime('%b %d, %Y')}",
        'forecast': round(forecast, 2)
    })

@app.route('/api/client/<int:client_id>/usage/historical')
def get_client_historical_usage(client_id):
    """API endpoint for a client's historical monthly usage data, now with daily details."""
    first_record = DataUsage.query.order_by(DataUsage.date.asc()).first()
    if not first_record: return jsonify([])

    historical_data = []
    # Start from the cycle of the first record, but don't go back more than a few years to be safe
    current_date = max(first_record.date, date.today() - relativedelta(years=5))
    today = date.today()

    while True:
        cycle_start, cycle_end = get_billing_cycle(current_date)
        # Stop if the cycle start is in the future
        if cycle_start > today: break
        
        usage_records = DataUsage.query.filter(
            DataUsage.client_id == client_id,
            DataUsage.date >= cycle_start,
            DataUsage.date <= cycle_end
        ).order_by(DataUsage.date.asc()).all()

        if usage_records:
            labels = [record.date.strftime('%b %d') for record in usage_records]
            data = [record.usage_gb for record in usage_records]
            total_usage = sum(data)
            
            historical_data.append({
                'cycle_label': f"{cycle_start.strftime('%b %d')} - {cycle_end.strftime('%b %d, %Y')}",
                'labels': labels,
                'data': data,
                'total_usage': round(total_usage, 2)
            })
        
        # Move to the next cycle
        current_date = cycle_end + relativedelta(days=1)

    return jsonify(historical_data)

@app.route('/api/client/<int:client_id>/report/pdf')
def generate_pdf_report(client_id):
    client = Client.query.get_or_404(client_id)
    num_cycles = request.args.get('cycles', default=3, type=int)
    report_type = request.args.get('type', default='standard') # 'standard' or 'upgrade'

    historical_data = []
    total_usage = 0
    today = date.today()

    for i in range(num_cycles):
        target_date = today - relativedelta(months=i)
        cycle_start, cycle_end = get_billing_cycle(target_date)
        
        usage_records = DataUsage.query.filter(
            DataUsage.client_id == client.id,
            DataUsage.date >= cycle_start,
            DataUsage.date <= cycle_end
        ).all()

        if usage_records:
            cycle_total = sum(record.usage_gb for record in usage_records)
            total_usage += cycle_total
            historical_data.append({
                'cycle_label': f"{cycle_start.strftime('%b %d, %Y')} - {cycle_end.strftime('%b %d, %Y')}",
                'total_usage': cycle_total
            })

    average_usage = total_usage / num_cycles if num_cycles > 0 else 0
    recommendation = None
    if report_type == 'upgrade' and average_usage > client.monthly_limit_gb * 0.8:
        recommendation = f"The client's average usage of {average_usage:.2f} GB is approaching the cap of {client.monthly_limit_gb} GB. Consider recommending an upgrade."

    report_start = (today - relativedelta(months=num_cycles-1)).replace(day=13)
    report_end = today.replace(day=12)
    
    rendered_html = render_template(
        'report_template.html',
        client=client,
        historical_data=historical_data,
        total_usage=total_usage,
        average_usage=average_usage,
        recommendation=recommendation,
        report_period=f"{report_start.strftime('%B %d, %Y')} to {report_end.strftime('%B %d, %Y')}",
        generation_date=datetime.now().strftime('%B %d, %Y')
    )
    
    pdf = HTML(string=rendered_html).write_pdf()
    
    return Response(pdf, mimetype='application/pdf', headers={
        'Content-Disposition': f'attachment;filename={client.name}_report.pdf'
    })

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
