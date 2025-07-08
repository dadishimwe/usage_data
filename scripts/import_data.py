# scripts/import_data.py
import os
import sys
import pandas as pd
from datetime import datetime

# Add the root project directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app import app, db, Client, DataUsage

def import_data(caps_filepath, usage_filepath):
    """
    Imports client data caps and daily usage from two separate CSV files.
    """
    # Use the application context to interact with the database
    with app.app_context():
        # Ensure all tables are created
        db.create_all()
        
        # --- Step 1: Import Client Caps ---
        print(f"Reading client caps from {caps_filepath}...")
        try:
            caps_df = pd.read_csv(caps_filepath)
            print(f"Found caps for {len(caps_df)} clients.")
        except FileNotFoundError:
            print(f"--- ERROR: Caps file not found at {caps_filepath} ---")
            print("Please create this file with 'ClientName' and 'DataCapGB' columns.")
            return
        
        # Clear existing data
        print("Clearing existing data from tables...")
        db.session.query(DataUsage).delete()
        db.session.query(Client).delete()
        db.session.commit()

        # Create or update clients from the caps file
        for _, row in caps_df.iterrows():
            client = Client(name=row['ClientName'], monthly_limit_gb=row['DataCapGB'])
            db.session.add(client)
        db.session.commit()
        print("Client caps imported successfully.")

        # --- Step 2: Import Daily Usage Data ---
        print(f"\nReading daily usage data from {usage_filepath}...")
        try:
            usage_df_wide = pd.read_csv(usage_filepath)
            
            # Transform data from wide to long format
            usage_df_long = pd.melt(usage_df_wide, id_vars=['Date'], var_name='ClientName', value_name='UsageGB')
            usage_df_long.dropna(subset=['UsageGB'], inplace=True)
            
            # Parse dates, handling ambiguous formats
            def parse_date(date_str):
                try: return pd.to_datetime(date_str)
                except pd.errors.OutOfBoundsDatetime:
                    current_year = datetime.now().year
                    return pd.to_datetime(f"{date_str}-{current_year}", format='%d-%b-%Y')
                except Exception: return pd.NaT
            
            usage_df_long['Date'] = usage_df_long['Date'].apply(parse_date)
            usage_df_long.dropna(subset=['Date'], inplace=True)
            print("Usage data transformed successfully.")

        except FileNotFoundError:
            print(f"--- ERROR: Usage file not found at {usage_filepath} ---")
            return
        except Exception as e:
            print(f"An error occurred during usage data processing: {e}")
            return

        # Add usage data to the corresponding clients
        client_map = {client.name: client.id for client in Client.query.all()}
        
        for _, row in usage_df_long.iterrows():
            client_name = row['ClientName']
            client_id = client_map.get(client_name)

            if client_id:
                data_usage_entry = DataUsage(
                    client_id=client_id,
                    date=row['Date'].date(),
                    usage_gb=row['UsageGB']
                )
                db.session.add(data_usage_entry)
            else:
                print(f"Warning: Skipping usage data for '{client_name}' as they are not in the client caps file.")
        
        db.session.commit()
        print("Daily usage data imported successfully!")


if __name__ == '__main__':
    # Define file paths
    caps_csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'client_caps.csv')
    usage_csv_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'WEEKLY_REPORTS(Sheet1).csv')
    
    import_data(caps_csv_path, usage_csv_path)
