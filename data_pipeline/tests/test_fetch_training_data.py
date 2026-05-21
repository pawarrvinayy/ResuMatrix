import os
import sys
import pandas as pd
from dotenv import load_dotenv
import unittest

# Add the scripts directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

# Load environment variables from .env file in the parent directory
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Import the updated API-based data fetching function
from fetch_training_data import get_joined_resumes_from_api

class TestFetchTrainingDataFromAPI(unittest.TestCase):
    """
    Test case for fetching training data using the ResuMatrix API.
    """

    def test_get_joined_resumes_from_api(self):
        """
        Test the get_joined_resumes_from_api function.
        """
        print("Testing get_joined_resumes_from_api function...")

        # Fetch the data using the API
        data = get_joined_resumes_from_api()

        # Verify that the result is a non-empty list
        self.assertIsInstance(data, list)
        self.assertGreater(len(data), 0)

        # Convert to DataFrame for better analysis and display
        df = pd.DataFrame(data)

        # Verify that required columns exist
        expected_columns = ['job_description_text', 'resume_text', 'label']
        for col in expected_columns:
            self.assertIn(col, df.columns)

        # Print basic stats
        print(f"\nFetched {len(df)} records from the API.")

        print("\nColumns:")
        for col in df.columns:
            print(f"  - {col}")

        # Truncate and print sample rows
        print("\nSample data (first 5 rows):")
        sample_df = df.copy()
        for col in ['job_description_text', 'resume_text']:
            if col in sample_df.columns:
                sample_df[col] = sample_df[col].apply(lambda x: x[:100] + '...' if isinstance(x, str) and len(x) > 100 else x)
        print(sample_df.head().to_string())

        # Print label distribution
        print("\nLabel distribution:")
        print(df['label'].value_counts())

        # Save a sample CSV
        output_path = os.path.join(os.path.dirname(__file__), "training_data_test.csv")
        df.to_csv(output_path, index=False)
        print(f"\nSaved training data to {output_path}")

        self.assertTrue(os.path.exists(output_path))
        print("\nTest completed successfully!")

def run_test():
    """
    Run the test case.
    """
    # Check for API base URL
    if not os.getenv("RESUMATRIX_API_URL"):
        print("WARNING: RESUMATRIX_API_URL not found in environment variables.")
        print("Please add it to your .env file.")

    unittest.main()

if __name__ == "__main__":
    run_test()
