import os
import pandas as pd
from supabase import create_client
import time

def load_to_supabase():
    """
    Load the training data into Supabase.
    """
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")

        supabase = create_client(supabase_url, supabase_key)

        # Get the most recent data file
        data_dir = "/opt/airflow/data"
        data_files = [f for f in os.listdir(data_dir) if f.startswith("train_data_")]

        if not data_files:
            raise FileNotFoundError(f"No data files found in {data_dir}")

        latest_file = max(data_files, key=lambda x: os.path.getctime(os.path.join(data_dir, x)))
        file_path = os.path.join(data_dir, latest_file)

        # Read the CSV file
        df = pd.read_csv(file_path)

        # Check if the required columns exist
        required_columns = ['resume_text', 'job_description_text', 'label']
        missing_columns = [col for col in required_columns if col not in df.columns]

        if missing_columns:
            raise ValueError(f"Missing required columns in CSV: {missing_columns}")

        # Convert DataFrame to list of dictionaries
        records = df.to_dict('records')

        # Insert data into Supabase in batches
        batch_size = 100
        total_records = len(records)
        successful_inserts = 0

        try:
            for i in range(0, total_records, batch_size):
                batch = records[i:i + batch_size]
                try:
                    # Insert the batch of records
                    supabase.table('training_data').insert(batch).execute()
                    successful_inserts += len(batch)

                    # Add a small delay between batches to avoid overwhelming the API
                    time.sleep(1)
                except Exception as e:
                    if "relation \"public.training_data\" does not exist" in str(e):
                        print("Table 'training_data' does not exist in Supabase.")
                        print("Please create the table in the Supabase dashboard with the following schema:")
                        print("""
                        CREATE TABLE public.training_data (
                            id SERIAL PRIMARY KEY,
                            resume_text TEXT,
                            job_description_text TEXT,
                            label TEXT,
                            created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                        );
                        """)
                        print("After creating the table, run this DAG again.")
                        return None
                    else:
                        raise

            return successful_inserts

        except Exception:
            print("Error during batch insert. Check table structure and permissions.")
            raise

    except Exception:
        print("Error loading data to Supabase. Check credentials, permissions, and table structure.")
        raise

if __name__ == "__main__":
    load_to_supabase()