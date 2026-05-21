import os
import logging
from huggingface_hub import hf_hub_download
import pandas as pd
from datetime import datetime

# Configure your Hugging Face dataset details here
DATASET_OWNER = "yifiyifan"  # Dataset owner/organization
DATASET_NAME = "synthetic-resume-fit-labelled"    # Dataset name
DATASET_FILE = "train.csv"            # The file to download from the dataset

def fetch_huggingface_data():
    try:
        # Construct the full repository name
        repo_id = f"{DATASET_OWNER}/{DATASET_NAME}"
        
        # Download the dataset
        file_path = hf_hub_download(
            repo_id=repo_id,
            filename=DATASET_FILE,
            repo_type="dataset"
        )
        
        # Read the CSV file to verify its structure
        df = pd.read_csv(file_path)
        
        # Verify the required columns exist
        required_columns = ['resume_text', 'job_description_text', 'label']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        # Create a timestamp for the filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save to the Airflow data directory with timestamp
        output_path = f"/opt/airflow/data/train_data_{timestamp}.csv"
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        
        return output_path
    except Exception as e:
        print(f"Error fetching data from Hugging Face: {str(e)}")
        raise

if __name__ == "__main__":
    fetch_huggingface_data() 
