"""
Embeddings Pipeline DAG

This DAG performs the following operations:
1. Fetches training data using fetch_training_data()
2. Generates embeddings using extract_embeddings()
3. Saves the embeddings locally
4. Uploads the embeddings to Google Cloud Storage
"""

from datetime import datetime, timedelta
import os
import logging
import numpy as np
import pandas as pd
import sys
import json

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.email import EmailOperator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/airflow/logs/embeddings_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add necessary paths to import project modules
sys.path.append('/opt/airflow')

# Import project modules
# Import these modules inside the task functions to avoid loading heavy models at DAG definition time
# from scripts.fetch_training_data import fetch_training_data, save_training_data
# from src.data_processing.data_preprocessing import extract_embeddings, clean_text
# from frontend.utils.gcp import upload_to_gcp

# Define default arguments for the DAG
default_args = {
    'owner': 'admin',
    'start_date': datetime(2024, 1, 1),
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
    'email_on_failure': True,
    'email_on_success': True,
    'email': ['mlops.team20@gmail.com'],
}

# Define GCS bucket name from environment variable
GCS_BUCKET_NAME = os.environ.get('GCP_BUCKET_NAME', 'resumatrix-embeddings')

# Define task functions
def fetch_and_save_training_data(**kwargs):
    """
    Fetch training data from the API and save it to a CSV file.
    No fallback to mock data - will fail if API is not available.

    Returns:
        str: Path to the saved CSV file
    """
    try:
        # Import here to avoid loading at DAG definition time
        from scripts.fetch_training_data import save_training_data
        import pandas as pd
        import os
        import socket
        import requests
        from datetime import datetime
        import traceback

        # Get API base URL from environment or use default
        api_base_url = os.getenv("RESUMATRIX_API_URL", "http://host.docker.internal:8000/api")
        logger.info(f"Using API base URL: {api_base_url}")

        # Check if hostname resolves
        try:
            hostname = api_base_url.split("//")[1].split(":")[0].split("/")[0]
            logger.info(f"Checking if hostname '{hostname}' resolves...")
            socket.gethostbyname(hostname)
            logger.info(f"Hostname '{hostname}' resolved successfully")
        except Exception as dns_error:
            logger.error(f"Hostname resolution failed: {str(dns_error)}")
            logger.error("This suggests the API server might not be reachable")

        # Try a basic connection to the API
        try:
            logger.info(f"Testing connection to {api_base_url}...")
            response = requests.get(f"{api_base_url}/health", timeout=5)
            logger.info(f"API health check response: Status {response.status_code}")
            if response.status_code != 200:
                logger.warning(f"API health check returned non-200 status: {response.status_code}")
                logger.warning(f"Response body: {response.text}")
        except requests.exceptions.RequestException as conn_error:
            logger.error(f"API connection test failed: {str(conn_error)}")

        # Fetch the training data using the updated logic
        logger.info("Fetching training data from API...")

        # Import the specific functions we need
        from scripts.fetch_training_data import fetch_existing_training_data, get_joined_resumes_from_api

        # Step 1: Always use the existing training dataset from /api/training/data as the base
        logger.info("Fetching existing training data from /api/training/data endpoint...")
        existing_df = fetch_existing_training_data()
        logger.info(f"Existing training data shape: {existing_df.shape}")

        # Log more details about the existing data
        if not existing_df.empty:
            logger.info(f"Existing data columns: {existing_df.columns.tolist()}")
            logger.info(f"Existing data label distribution: {existing_df['label'].value_counts().to_dict()}")
            if len(existing_df) > 0:
                logger.info(f"Sample of existing data (first row): {existing_df.iloc[0].to_dict()}")
        else:
            logger.warning("Existing training data is empty")

        if existing_df.empty:
            logger.warning("No data found from /api/training/data endpoint.")

        # Step 2: Optionally include feedback-labeled resumes from the joined dataset
        logger.info("Attempting to fetch additional feedback-labeled resumes...")
        try:
            additional_data = get_joined_resumes_from_api()
            logger.info(f"Raw additional data length: {len(additional_data)}")
            additional_df = pd.DataFrame(additional_data) if additional_data else pd.DataFrame()
            logger.info(f"Additional feedback-labeled data shape: {additional_df.shape}")

            # Log more details about the additional data
            if not additional_df.empty:
                logger.info(f"Additional data columns: {additional_df.columns.tolist()}")
                logger.info(f"Additional data label distribution: {additional_df['label'].value_counts().to_dict()}")
                if len(additional_df) > 0:
                    logger.info(f"Sample of additional data (first row): {additional_df.iloc[0].to_dict()}")
            else:
                logger.warning("Additional feedback-labeled data is empty")
        except Exception as e:
            logger.warning(f"Failed to fetch additional feedback-labeled data: {str(e)}")
            logger.warning("Proceeding with only the existing training data.")
            additional_df = pd.DataFrame()

        # Step 3: Combine datasets and deduplicate
        if existing_df.empty and additional_df.empty:
            error_msg = "Both data sources returned empty datasets. No training data available."
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Combine the datasets
        if not additional_df.empty:
            logger.info("Combining existing and additional datasets...")
            df = pd.concat([existing_df, additional_df], ignore_index=True)
            logger.info(f"Combined data shape (before deduplication): {df.shape}")
            logger.info(f"Combined data label distribution: {df['label'].value_counts().to_dict()}")
        else:
            logger.info("Using only existing dataset (no additional data to combine)")
            df = existing_df
            logger.info(f"Using existing data with shape: {df.shape}")

        # Clean and validate data
        df = df.dropna(subset=["job_description_text", "resume_text", "label"])
        logger.info(f"Data after dropping NAs: {df.shape}")

        # Define valid labels
        def is_valid_label(label):
            if isinstance(label, (int, float)):
                return label in [0, 1, -1]  # 0=neutral, 1=fit, -1=no fit
            return str(label).lower() in ["good fit", "no fit", "potential fit", "neutral"]

        df = df[df["label"].apply(is_valid_label)]
        logger.info(f"Data after filtering valid labels: {df.shape}")

        # Deduplicate based on job_description_text and resume_text
        df = df.drop_duplicates(subset=["job_description_text", "resume_text"])
        logger.info(f"Final deduplicated training data shape: {df.shape}")

        if df.empty:
            error_msg = "No valid training data after processing and deduplication."
            logger.error(error_msg)
            raise ValueError(error_msg)

        logger.info(f"Successfully fetched training data from API with shape: {df.shape}")

        # Save the data to a CSV file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        data_dir = '/opt/airflow/data'
        os.makedirs(data_dir, exist_ok=True)
        output_path = f"{data_dir}/training_data_{timestamp}.csv"

        df.to_csv(output_path, index=False)
        logger.info(f"Training data saved to {output_path}")

        # Push the output path to XCom for the next task
        kwargs['ti'].xcom_push(key='training_data_path', value=output_path)

        return output_path

    except Exception as e:
        logger.error(f"Error in fetch_and_save_training_data: {str(e)}")
        logger.error(f"Detailed traceback: {traceback.format_exc()}")
        raise

def generate_and_save_embeddings(**kwargs):
    """
    Generate embeddings from the training data, split into train/test sets, and save them locally.

    Returns:
        dict: Paths to the saved embeddings and metadata files
    """
    try:
        # Import here to avoid loading at DAG definition time
        from src.data_processing.data_preprocessing import extract_embeddings, clean_text
        from sklearn.model_selection import train_test_split

        # Get the training data path from XCom
        ti = kwargs['ti']
        training_data_path = ti.xcom_pull(task_ids='fetch_training_data_task', key='training_data_path')

        logger.info(f"Loading training data from {training_data_path}")
        df = pd.read_csv(training_data_path)

        # Clean the text data if needed
        logger.info("Cleaning text data...")
        if 'resume_text' in df.columns and 'job_description_text' in df.columns:
            df['resume_text'] = df['resume_text'].apply(clean_text)
            df['job_description_text'] = df['job_description_text'].apply(clean_text)

        def is_selected_label(label):
            if isinstance(label, str):
                label = label.lower()
                return label in ['good fit', 'no fit']
            else:  # numeric labels
                return label in [1, -1]  # 1=good fit, -1=no fit

        original_count = len(df)
        df = df[df['label'].apply(is_selected_label)]
        filtered_count = len(df)
        removed_count = original_count - filtered_count

        logger.info(f"Removed {removed_count} rows with other labels. Kept {filtered_count} rows.")

        if df.empty:
            error_msg = "No data remaining after filtering for 'good fit' and 'no fit' labels"
            logger.error(error_msg)
            raise ValueError(error_msg)

        # Split the data into train (80%) and test (20%) sets
        logger.info("Splitting data into train and test sets (80/20 split)...")
        train_df, test_df = train_test_split(df, test_size=0.2, random_state=42)
        logger.info(f"Train set shape: {train_df.shape}, Test set shape: {test_df.shape}")

        # Create directory for embeddings if it doesn't exist
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        embeddings_dir = '/opt/airflow/data/embeddings'
        os.makedirs(embeddings_dir, exist_ok=True)

        # Process train set
        logger.info("Generating embeddings for train set...")
        X_train, y_train = extract_embeddings(train_df, data_type="train")

        # Process test set
        logger.info("Generating embeddings for test set...")
        X_test, y_test = extract_embeddings(test_df, data_type="train")

        # Save train embeddings to a local file
        train_embeddings_path = f"{embeddings_dir}/train_embeddings_{timestamp}.npz"
        np.savez(train_embeddings_path, X=X_train, y=y_train)
        logger.info(f"Train embeddings saved to {train_embeddings_path}")

        # Save test embeddings to a local file
        test_embeddings_path = f"{embeddings_dir}/test_embeddings_{timestamp}.npz"
        np.savez(test_embeddings_path, X=X_test, y=y_test)
        logger.info(f"Test embeddings saved to {test_embeddings_path}")

        # Log the type and values of labels to help with debugging
        logger.info(f"Train labels type: {type(y_train)}, shape: {y_train.shape if hasattr(y_train, 'shape') else 'N/A'}")
        logger.info(f"Train unique labels: {np.unique(y_train)}")
        logger.info(f"Test labels type: {type(y_test)}, shape: {y_test.shape if hasattr(y_test, 'shape') else 'N/A'}")
        logger.info(f"Test unique labels: {np.unique(y_test)}")

        # Convert string labels to numeric if needed (for train set)
        train_numeric_y = np.zeros_like(y_train, dtype=int)
        for i, label in enumerate(y_train):
            if isinstance(label, str):
                if label.lower() == 'good fit':
                    train_numeric_y[i] = 1
                elif label.lower() == 'no fit':
                    train_numeric_y[i] = 0
                # Skip other labels
            else:
                # Assume numeric labels are already correct
                train_numeric_y[i] = int(label)

        # Convert string labels to numeric if needed (for test set)
        test_numeric_y = np.zeros_like(y_test, dtype=int)
        for i, label in enumerate(y_test):
            if isinstance(label, str):
                if label.lower() == 'good fit':
                    test_numeric_y[i] = 1
                elif label.lower() == 'no fit':
                    test_numeric_y[i] = 0
                # Skip other labels
            else:
                # Assume numeric labels are already correct
                test_numeric_y[i] = int(label)

        # Calculate class distribution for train set
        train_fit_count = int(np.sum(train_numeric_y == 1))
        train_no_fit_count = int(np.sum(train_numeric_y == 0))

        # Calculate class distribution for test set
        test_fit_count = int(np.sum(test_numeric_y == 1))
        test_no_fit_count = int(np.sum(test_numeric_y == 0))

        logger.info(f"Train set class distribution: fit={train_fit_count}, no_fit={train_no_fit_count}")
        logger.info(f"Test set class distribution: fit={test_fit_count}, no_fit={test_no_fit_count}")

        # Save metadata
        metadata = {
            'timestamp': timestamp,
            'total_samples': len(df),
            'train_samples': len(train_df),
            'test_samples': len(test_df),
            'embedding_dim': X_train.shape[1],
            'train_class_distribution': {
                'fit': train_fit_count,
                'no_fit': train_no_fit_count
            },
            'test_class_distribution': {
                'fit': test_fit_count,
                'no_fit': test_no_fit_count
            }
        }

        metadata_path = f"{embeddings_dir}/metadata_{timestamp}.json"
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f)

        logger.info(f"Metadata saved to {metadata_path}")

        # Push the paths to XCom for the next task
        ti.xcom_push(key='train_embeddings_path', value=train_embeddings_path)
        ti.xcom_push(key='test_embeddings_path', value=test_embeddings_path)
        ti.xcom_push(key='metadata_path', value=metadata_path)

        return {
            'train_embeddings_path': train_embeddings_path,
            'test_embeddings_path': test_embeddings_path,
            'metadata_path': metadata_path
        }

    except Exception as e:
        logger.error(f"Error in generate_and_save_embeddings: {str(e)}")
        raise

def upload_to_gcs_bucket(**kwargs):
    """
    Upload train/test embeddings and metadata files to Google Cloud Storage.
    If GCS upload fails, save files locally and log the paths.

    Returns:
        dict: GCS paths for the uploaded files or local paths if GCS upload fails
    """
    # Get the file paths from XCom
    ti = kwargs['ti']
    train_embeddings_path = ti.xcom_pull(task_ids='generate_embeddings_task', key='train_embeddings_path')
    test_embeddings_path = ti.xcom_pull(task_ids='generate_embeddings_task', key='test_embeddings_path')
    metadata_path = ti.xcom_pull(task_ids='generate_embeddings_task', key='metadata_path')

    try:
        # Import here to avoid loading at DAG definition time
        from google.cloud import storage

        # Test GCS connection
        try:
            logger.info("Testing GCS connection...")
            client = storage.Client()
            # Try to access the bucket
            bucket = client.bucket(GCS_BUCKET_NAME)
            if not bucket.exists():
                logger.warning(f"Bucket {GCS_BUCKET_NAME} does not exist. Will create it.")
                bucket = client.create_bucket(GCS_BUCKET_NAME)

            # Upload train embeddings file to GCS
            train_blob_name = f"embeddings/{os.path.basename(train_embeddings_path)}"
            logger.info(f"Uploading train embeddings to GCS: {train_blob_name}")

            # Create a blob and upload the file
            train_blob = bucket.blob(train_blob_name)
            with open(train_embeddings_path, 'rb') as f:
                train_blob.upload_from_file(f, content_type="application/octet-stream")

            # Upload test embeddings file to GCS
            test_blob_name = f"embeddings/{os.path.basename(test_embeddings_path)}"
            logger.info(f"Uploading test embeddings to GCS: {test_blob_name}")

            # Create a blob and upload the file
            test_blob = bucket.blob(test_blob_name)
            with open(test_embeddings_path, 'rb') as f:
                test_blob.upload_from_file(f, content_type="application/octet-stream")

            # Upload metadata file to GCS
            metadata_blob_name = f"metadata/{os.path.basename(metadata_path)}"
            logger.info(f"Uploading metadata to GCS: {metadata_blob_name}")

            # Create a blob and upload the file
            metadata_blob = bucket.blob(metadata_blob_name)
            with open(metadata_path, 'rb') as f:
                metadata_blob.upload_from_file(f, content_type="application/json")

            gcs_paths = {
                'train_embeddings_gcs_path': f"gs://{GCS_BUCKET_NAME}/{train_blob_name}",
                'test_embeddings_gcs_path': f"gs://{GCS_BUCKET_NAME}/{test_blob_name}",
                'metadata_gcs_path': f"gs://{GCS_BUCKET_NAME}/{metadata_blob_name}"
            }

            logger.info(f"Files successfully uploaded to GCS: {gcs_paths}")
            return gcs_paths

        except Exception as gcs_error:
            logger.warning(f"GCS upload failed: {str(gcs_error)}")
            raise

    except Exception as e:
        logger.error(f"Error in upload_to_gcs_bucket: {str(e)}")
        logger.info("Falling back to local storage only...")

        # Return local paths instead
        local_paths = {
            'train_embeddings_local_path': train_embeddings_path,
            'test_embeddings_local_path': test_embeddings_path,
            'metadata_local_path': metadata_path
        }

        logger.info(f"Files saved locally: {local_paths}")
        return local_paths

# Define the DAG
with DAG(
    'embeddings_generation_pipeline',
    default_args=default_args,
    description='Pipeline to fetch training data, generate embeddings, and upload to GCS',
    schedule_interval='0 0 */10 * *',  # Run every 10 days
    catchup=False
) as dag:

    # Define tasks
    start_task = EmptyOperator(
        task_id='start',
        dag=dag
    )

    fetch_training_data_task = PythonOperator(
        task_id='fetch_training_data_task',
        python_callable=fetch_and_save_training_data,
        provide_context=True,
        dag=dag
    )

    generate_embeddings_task = PythonOperator(
        task_id='generate_embeddings_task',
        python_callable=generate_and_save_embeddings,
        provide_context=True,
        dag=dag
    )

    upload_to_gcs_task = PythonOperator(
        task_id='upload_to_gcs_task',
        python_callable=upload_to_gcs_bucket,
        provide_context=True,
        dag=dag
    )

    end_task = EmptyOperator(
        task_id='end',
        dag=dag
    )

    # Email notifications
    email_success = EmailOperator(
        task_id='send_email_success',
        to='mlops.team20@gmail.com',
        subject='Embeddings Pipeline Success',
        html_content="""
        <h3>Embeddings Pipeline has completed successfully.</h3>
        <p>DAG: {{ dag.dag_id }}</p>
        <p>Execution Date: {{ ds }}</p>
        <p>Embeddings have been generated and uploaded to GCS.</p>
        """,
        trigger_rule='all_success',
        dag=dag
    )

    email_failure = EmailOperator(
        task_id='send_email_failure',
        to='mlops.team20@gmail.com',
        subject='Embeddings Pipeline Failed',
        html_content="""
        <h3>Embeddings Pipeline has failed.</h3>
        <p>DAG: {{ dag.dag_id }}</p>
        <p>Execution Date: {{ ds }}</p>
        <p>Failed Task: {{ task_instance.task_id }}</p>
        <p>Please check the logs for more information.</p>
        """,
        trigger_rule='one_failed',
        dag=dag
    )

    # Define task dependencies
    start_task >> fetch_training_data_task >> generate_embeddings_task >> upload_to_gcs_task >> end_task
    end_task >> [email_success, email_failure]
