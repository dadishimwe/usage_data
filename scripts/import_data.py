# scripts/import_data.py
import os
import sys
import pandas as pd
from datetime import datetime

# --- FIX FOR ModuleNotFoundError ---
# This adds the root project directory to the Python path.
# It allows the script to find and import the 'app' module from the parent directory.
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
# --- END FIX ---

from app import app, db, Client, DataUsage


def import_from_csv(filepath):
    """Imports client data from a CSV file into the database."""
    print(f"Reading data from {filepath}...")
    
    try:
        df_wide = pd.read_csv(filepath)
        print(f"Columns found in CSV: {df_wide.columns.tolist()}")

        # --- FIX FOR WIDE DATA FORMAT ---
        # The CSV is in a "wide" format (each client is a column).
        # We need to "unpivot" or "melt" it into a "long" format.
        # The expected columns are 'Date', 'ClientName', and 'UsageGB'.
        
        if 'Date' not in df_wide.columns:
            print("Error: CSV file must contain a 'Date' column.")
            return

        print("Transforming data from wide to long format...")
        df = pd.melt(df_wide, id_vars=['Date'], var_name='ClientName', value_name='UsageGB')
        
        # Remove rows where usage is not recorded (NaN values)
        df.dropna(subset=['UsageGB'], inplace=True)
        print("Data transformation complete.")
        # --- END FIX ---

        # --- NEW: Filter data to start from March 13th ---
        # First, convert the 'Date' column to datetime objects, handling ambiguous dates
        def parse_date(date_str):
            try:
                return pd.to_datetime(date_str)
            except pd.errors.OutOfBoundsDatetime:
                current_year = datetime.now().year
                return pd.to_datetime(f"{date_str}-{current_year}", format='%d-%b-%Y')
            except Exception:
                return pd.NaT # Return Not a Time for unparseable dates

        df['Date'] = df['Date'].apply(parse_date)
        df.dropna(subset=['Date'], inplace=True) # Drop rows with unparseable dates

        start_date = datetime(datetime.now().year, 3, 13)
        df = df[df['Date'] >= start_date]
        print(f"Data filtered to include records on or after {start_date.date()}.")
        # --- END NEW ---


    except FileNotFoundError:
        print(f"Error: The file was not found at {filepath}")
        return
    except Exception as e:
        print(f"An error occurred during data processing: {e}")
        return

    # Use the application context to interact with the database
    with app.app_context():
        # This ensures that all tables are created in the database before we try to access them.
        db.create_all()
        
        print("Clearing existing data from tables...")
        # Clear existing data to avoid duplicates if run multiple times
        db.session.query(DataUsage).delete()
        db.session.query(Client).delete()
        db.session.commit()
        print("Existing data cleared.")

        # Iterate over each row in the transformed DataFrame
        for index, row in df.iterrows():
            client_name = row['ClientName']
            usage_date = row['Date'].date()
            usage_gb = row['UsageGB']

            # Check if the client already exists in the database
            client = Client.query.filter_by(name=client_name).first()
            if not client:
                # If not, create a new client with a default limit
                print(f"Creating new client: {client_name}")
                client = Client(name=client_name, monthly_limit_gb=1000.0) # Default to 1TB
                db.session.add(client)
                # We commit here to get the new client's ID
                db.session.commit()

            # Add the data usage record for the client
            data_usage_entry = DataUsage(
                client_id=client.id,
                date=usage_date,
                usage_gb=usage_gb
            )
            db.session.add(data_usage_entry)

        # Commit all the new records to the database
        print("Committing new data to the database...")
        db.session.commit()
        print("Data imported successfully!")

if __name__ == '__main__':
    # The filename for the CSV data
    csv_filename = 'WEEKLY_REPORTS(datausage)-2.csv'
    csv_file_path = os.path.join(os.path.dirname(__file__), '..', 'data', csv_filename)
    import_from_csv(csv_file_path)