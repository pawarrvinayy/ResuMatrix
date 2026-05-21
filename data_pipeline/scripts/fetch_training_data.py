import os
import pandas as pd
import requests
import logging
import socket

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_BASE_URL = os.getenv("RESUMATRIX_API_URL", "http://host.docker.internal:8000/api")


def check_api_connection():
    """
    Check if the API is reachable and responding.
    Returns True if the API is reachable, False otherwise.
    """
    # Extract hostname from API_BASE_URL
    try:
        url_parts = API_BASE_URL.split('://')
        if len(url_parts) > 1:
            host_part = url_parts[1].split('/')[0]
            if ':' in host_part:
                hostname, port = host_part.split(':')
                port = int(port)
            else:
                hostname = host_part
                port = 80 if url_parts[0] == 'http' else 443
        else:
            hostname = API_BASE_URL
            port = 80

        logger.info(f"Checking connection to {hostname}:{port}...")

        # Try to resolve the hostname
        try:
            ip_address = socket.gethostbyname(hostname)
            logger.info(f"Hostname {hostname} resolved to {ip_address}")
        except socket.gaierror as e:
            logger.error(f"Failed to resolve hostname {hostname}: {e}")
            return False

        # Try to connect to the host
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((hostname, port))
            sock.close()

            if result == 0:
                logger.info(f"Successfully connected to {hostname}:{port}")
            else:
                logger.error(f"Failed to connect to {hostname}:{port} (error code: {result})")
                return False
        except socket.error as e:
            logger.error(f"Socket error connecting to {hostname}:{port}: {e}")
            return False

        # Try to make a simple HTTP request
        # First try a health endpoint if it exists
        health_endpoints = [
            f"{API_BASE_URL}/health",
            f"{API_BASE_URL.rstrip('/api')}/health",
            f"{API_BASE_URL}/jobs"
        ]

        for endpoint in health_endpoints:
            try:
                logger.info(f"Testing API endpoint: {endpoint}")
                response = requests.get(endpoint, timeout=5)
                if response.status_code < 500:  # Accept any non-server error response
                    logger.info(f"API responded with status code {response.status_code}")
                    return True
            except requests.RequestException as e:
                logger.warning(f"Failed to connect to {endpoint}: {e}")
                continue

        logger.error("All API test endpoints failed")
        return False

    except Exception as e:
        logger.error(f"Error checking API connection: {e}")
        return False


def get_joined_resumes_from_api() -> list[dict]:
    try:
        logger.info(f"Fetching jobs data from API at {API_BASE_URL}...")

        # Get all jobs - no need for user_id to get all jobs
        logger.info(f"Requesting jobs from: {API_BASE_URL}/jobs/")
        jobs_response = requests.get(f"{API_BASE_URL}/jobs/", timeout=10)
        logger.info(f"Jobs response status code: {jobs_response.status_code}")
        try:
            logger.info(f"Jobs response headers: {jobs_response.headers}")
            logger.info(f"Jobs response content (first 500 chars): {jobs_response.text[:500]}...")
        except Exception as e:
            logger.warning(f"Could not log response details: {e}")

        # Handle the specific case where the API returns 500 but the error is "No jobs found"
        if jobs_response.status_code == 500:
            try:
                error_data = jobs_response.json()
                if isinstance(error_data, dict) and "detail" in error_data:
                    error_message = error_data["detail"]
                    if "No jobs found" in error_message:
                        logger.warning("API returned 500 with 'No jobs found' message. Treating as empty jobs list.")
                        return []
            except Exception:
                # If we can't parse the error, just continue with the normal flow
                pass

        # For all other cases, raise for status as usual
        jobs_response.raise_for_status()
        jobs = jobs_response.json()

        # Handle different response formats
        if isinstance(jobs, dict) and "jobs" in jobs:
            jobs = jobs["jobs"]

        logger.info(f"Retrieved {len(jobs)} jobs")
        result = []

        for job in jobs:
            job_id = job.get("id")
            job_text = job.get("job_description", "") or job.get("job_text", "")
            if not job_id or not job_text:
                logger.warning(f"Skipping job with missing id or text: {job}")
                continue

            logger.info(f"Processing job ID: {job_id}")
            resumes_url = f"{API_BASE_URL}/jobs/{job_id}/resumes"
            logger.info(f"Requesting resumes from: {resumes_url}")
            resumes_response = requests.get(resumes_url, timeout=10)
            logger.info(f"Resumes response status code: {resumes_response.status_code}")
            try:
                logger.info(f"Resumes response headers: {resumes_response.headers}")
                logger.info(f"Resumes response content (first 500 chars): {resumes_response.text[:500]}...")
            except Exception as e:
                logger.warning(f"Could not log resumes response details: {e}")

            if resumes_response.status_code == 200:
                resumes = resumes_response.json()
                if isinstance(resumes, dict) and "resumes" in resumes:
                    resumes = resumes["resumes"]

                logger.info(f"Retrieved {len(resumes)} resumes for job {job_id}")

                resume_count = 0
                processed_count = 0
                skipped_count = 0

                for resume in resumes:
                    resume_count += 1
                    # Get the feedback label
                    feedback_label = resume.get("feedback_label")
                    resume_id = resume.get("id", "unknown")

                    logger.info(f"Processing resume {resume_count}/{len(resumes)}, ID: {resume_id}, feedback_label: {feedback_label}")

                    # Skip if no feedback label
                    if feedback_label is None:
                        logger.info(f"Skipping resume {resume_id}: No feedback label")
                        skipped_count += 1
                        continue

                    # Apply the specified logic:
                    # - If feedback_label is 1, it's a fit
                    # - If feedback_label is -1, it's a no fit
                    # - If feedback_label is 0, skip this resume
                    if feedback_label == 1:
                        label = "Good Fit"
                        logger.info(f"Resume {resume_id}: feedback_label=1, labeled as 'fit'")
                        processed_count += 1
                    elif feedback_label == -1:
                        label = "No Fit"
                        logger.info(f"Resume {resume_id}: feedback_label=-1, labeled as 'no fit'")
                        processed_count += 1
                    else:
                        # Skip resumes with feedback_label = 0 or any other value
                        logger.info(f"Skipping resume {resume_id}: feedback_label={feedback_label} (not 1 or -1)")
                        skipped_count += 1
                        continue

                    # Add the resume-job pair to the result list
                    result.append({
                        "job_description_text": job_text,
                        "resume_text": resume.get("resume_text", ""),
                        "label": label
                    })

                # Log summary after processing all resumes for this job
                logger.info(f"Resume processing summary for job {job_id}: Total={resume_count}, Processed={processed_count}, Skipped={skipped_count}")

        logger.info(f"Total feedback records found: {len(result)}")
        return result

    except requests.RequestException as e:
        logger.error(f"API request error: {e}")
        raise


def fetch_existing_training_data() -> pd.DataFrame:
    try:
        logger.info("Fetching existing training data from /api/training/data")
        training_url = f"{API_BASE_URL}/training/data"
        logger.info(f"Requesting training data from: {training_url}")
        response = requests.get(training_url, timeout=10)
        logger.info(f"Training data response status code: {response.status_code}")
        try:
            logger.info(f"Training data response headers: {response.headers}")
            logger.info(f"Training data response content (first 500 chars): {response.text[:500]}...")
        except Exception as e:
            logger.warning(f"Could not log training data response details: {e}")
        response.raise_for_status()

        # Parse the response
        response_data = response.json()

        # Handle different response formats
        if isinstance(response_data, dict):
            # If response is a dict, look for data in common keys
            if "data" in response_data:
                data = response_data["data"]
            elif "training_data" in response_data:
                data = response_data["training_data"]
            else:
                # If no recognized keys, use the whole dict
                data = [response_data]
        elif isinstance(response_data, list):
            # If response is already a list, use it directly
            data = response_data
        else:
            logger.error(f"Unexpected training data response type: {type(response_data)}")
            return pd.DataFrame()

        if not data:
            logger.warning("Training data response is empty.")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        expected_columns = {"job_description_text", "resume_text", "label"}
        if not expected_columns.issubset(df.columns):
            logger.error(f"Training data missing expected columns. Found columns: {df.columns.tolist()}")
            return pd.DataFrame()

        logger.info(f"Fetched {len(df)} existing training records")
        return df

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch existing training data: {e}")
        logger.error(f"Request URL: {API_BASE_URL}/training/data")
        import traceback
        logger.error(f"Detailed traceback: {traceback.format_exc()}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error fetching training data: {e}")
        import traceback
        logger.error(f"Detailed traceback: {traceback.format_exc()}")
        return pd.DataFrame()


def fetch_training_data() -> pd.DataFrame:
    try:
        logger.info("Starting training data fetch process...")

        # First get the existing training data (this should always be available)
        existing_df = fetch_existing_training_data()
        logger.info(f"Existing training data shape: {existing_df.shape}")

        # Then try to get new feedback data (this is optional)
        try:
            if check_api_connection():  # Only try if API is reachable
                new_data = get_joined_resumes_from_api()
                new_df = pd.DataFrame(new_data) if new_data else pd.DataFrame()
                logger.info(f"New feedback data shape: {new_df.shape}")

                # Only proceed with combining if we got new data
                if not new_df.empty:
                    logger.info("New feedback data is not empty, proceeding with combining datasets")
                    logger.info(f"Existing data columns: {existing_df.columns.tolist()}")
                    logger.info(f"New data columns: {new_df.columns.tolist()}")

                    # Log sample of new data
                    if len(new_df) > 0:
                        logger.info(f"Sample of new data (first row): {new_df.iloc[0].to_dict()}")

                    # Combine datasets
                    all_data = pd.concat([existing_df, new_df], ignore_index=True)
                    logger.info(f"Combined data shape: {all_data.shape}")

                    # Clean and validate the combined data
                    valid_data = all_data.dropna(subset=["job_description_text", "resume_text", "label"])
                    logger.info(f"Data after dropping NAs: {valid_data.shape}")

                    # Define valid labels (including numeric values)
                    def is_valid_label(label):
                        if isinstance(label, (int, float)):
                            return label in [0, 1, -1]  # 0=neutral, 1=fit, -1=no fit
                        return str(label).lower() in ["fit", "no fit", "potential fit", "neutral"]

                    valid_data = valid_data[valid_data["label"].apply(is_valid_label)]
                    logger.info(f"Data after filtering valid labels: {valid_data.shape}")

                    # Remove duplicates
                    deduped_data = valid_data.drop_duplicates(subset=["job_description_text", "resume_text"])
                    logger.info(f"Final deduplicated training data shape: {deduped_data.shape}")

                    if not deduped_data.empty:
                        return deduped_data
                    logger.warning("Combined data was empty after validation")
                else:
                    logger.info("New feedback data is empty, skipping combination step")
                    return existing_df

            logger.info("No valid feedback data available, using existing training data only")
            return existing_df

        except Exception as e:
            logger.warning(f"Failed to fetch feedback data: {str(e)}")
            logger.info("Falling back to existing training data only")
            return existing_df

    except Exception as e:
        logger.error(f"Error in fetch_training_data: {str(e)}")
        raise


def save_training_data(df, output_path=None):
    try:
        if output_path is None:
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = f"/opt/airflow/data/training_data_{timestamp}.csv"

        dirname = os.path.dirname(output_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)

        df.to_csv(output_path, index=False)
        logger.info(f"Training data saved to {output_path}")

        return output_path
    except Exception as e:
        logger.error(f"Error saving training data: {str(e)}")
        raise


if __name__ == "__main__":
    df = fetch_training_data()
    save_training_data(df)
