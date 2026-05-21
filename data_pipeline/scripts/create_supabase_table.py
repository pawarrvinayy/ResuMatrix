import os
from supabase import create_client

def create_supabase_table():
    """
    Drop and recreate the training_data table in Supabase.
    """
    try:
        # Initialize Supabase client
        supabase_url = os.getenv("SUPABASE_URL")
        supabase_key = os.getenv("SUPABASE_API_KEY") or os.getenv("SUPABASE_KEY")

        if not supabase_url or not supabase_key:
            raise ValueError("Supabase credentials not found in environment variables")

        supabase = create_client(supabase_url, supabase_key)

        # SQL to drop and recreate the table
        sql = """
        -- First, drop the table if it exists
        DROP TABLE IF EXISTS public.training_data;

        -- Create the extension for UUID generation
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

        -- Recreate the table
        CREATE TABLE public.training_data (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            resume_text TEXT,
            job_description_text TEXT,
            label TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW()
        );
        """

        # Try to delete all records first (in case table exists but we can't drop it)
        try:
            response =supabase.table('training_data').delete().neq("id", "").execute()
            print(f"Deleted {response.data} records from training_data table")
            
        except Exception:
            # Table might not exist yet, which is fine
            pass

        # Execute the SQL to drop and recreate the table
        try:
            # Try to execute SQL directly if the RPC function exists
            supabase.rpc('exec_sql', {"sql": sql}).execute()
        except Exception:
            # If RPC fails, the table will be created when we try to insert data
            pass

        return True

    except Exception:
        print("Error resetting table in Supabase. Check credentials and permissions.")
        return False

if __name__ == "__main__":
    create_supabase_table()