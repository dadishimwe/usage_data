# app.py
from flask import Flask, render_template, jsonify, Response
from flask_sqlalchemy import SQLAlchemy
from config import Config
import pandas as pd
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import io

# Initialize the Flask app and configure it from the Config object
app = Flask(__name__)
app.config.from_object(Config)

# Initialize the database extension
db = SQLAlchemy(app)

# --- Helper Function for Billing Cycles ---
def get_billing_cycle(target_date=None):
    """Calculates the start and end date of a billing cycle based on a target date."""
    if target_date is None:
        target_date = date.today()
    
    if target_date.day < 13:
        # Cycle is from 13th of last month to 12th of this month
        start_date = (target_date - relativedelta(months=1)).replace(day=13)
        end_date = target_date.replace(day=12)
    else:
        # Cycle is from 13th of this month to 12th of next month
        start_date = target_date.replace(day=13)
        end_date = (target_date + relativedelta(months=1)).replace(day=12)
    return start_date, end_date

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
    """Renders the main dashboard page."""
    return render_template('index.html')

@app.route('/client/<int:client_id>')
def client_detail_page(client_id):
    """Renders the detailed page for a single client."""
    client = Client.query.get_or_404(client_id)
    return render_template('client_detail.html', client=client)

# --- API Routes ---
@app.route('/api/clients')
def get_clients():
    """API endpoint for the main dashboard client list."""
    clients = Client.query.all()
    client_data = []
    cycle_start_date, cycle_end_date = get_billing_cycle()

    for client in clients:
        total_usage = db.session.query(db.func.sum(DataUsage.usage_gb)).filter(
            DataUsage.client_id == client.id,
            DataUsage.date >= cycle_start_date,
            DataUsage.date <= cycle_end_date
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
    """API endpoint for a client's usage in the CURRENT billing cycle."""
    cycle_start, cycle_end = get_billing_cycle()
    usage_records = DataUsage.query.filter(
        DataUsage.client_id == client_id,
        DataUsage.date >= cycle_start,
        DataUsage.date <= cycle_end
    ).order_by(DataUsage.date.asc()).all()
    
    labels = [record.date.strftime('%b %d') for record in usage_records]
    data = [record.usage_gb for record in usage_records]
    
    return jsonify({'labels': labels, 'data': data, 'cycle_label': f"{cycle_start.strftime('%b %d')} - {cycle_end.strftime('%b %d, %Y')}"})

@app.route('/api/client/<int:client_id>/usage/historical')
def get_client_historical_usage(client_id):
    """API endpoint for a client's historical monthly usage data."""
    first_record = DataUsage.query.order_by(DataUsage.date.asc()).first()
    if not first_record:
        return jsonify([])

    historical_data = []
    # Start from the cycle of the first record
    current_date = first_record.date 
    today = date.today()

    while True:
        cycle_start, cycle_end = get_billing_cycle(current_date)
        # Stop if the cycle start is in the future
        if cycle_start > today:
            break
        
        usage_records = DataUsage.query.filter(
            DataUsage.client_id == client_id,
            DataUsage.date >= cycle_start,
            DataUsage.date <= cycle_end
        ).order_by(DataUsage.date.asc()).all()

        if usage_records: # Only add cycles with data
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

@app.route('/api/client/<int:client_id>/report/csv')
def generate_csv_report(client_id):
    """Generates and streams a CSV report for a client."""
    client = Client.query.get_or_404(client_id)
    usage_records = DataUsage.query.filter_by(client_id=client_id).order_by(DataUsage.date.asc()).all()
    
    # Create a Pandas DataFrame
    data = {
        'Date': [record.date.strftime('%Y-%m-%d') for record in usage_records],
        'Usage (GB)': [record.usage_gb for record in usage_records]
    }
    df = pd.DataFrame(data)
    
    # Create an in-memory text stream
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return Response(
        output,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment;filename={client.name}_usage_report.csv"}
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)