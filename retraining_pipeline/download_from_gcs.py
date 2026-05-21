#!/usr/bin/env python3
"""
Download embeddings and metadata from Google Cloud Storage.
This script downloads the latest train/test embeddings and metadata from GCS.
"""

import os
import json
import logging
from datetime import datetime
from google.cloud import storage
from dotenv import load_dotenv

# Load the .env file from the parent directory
dotenv_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '.env'))
load_dotenv(dotenv_path)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_blob(bucket_name, source_blob_name, destination_file_name):
    """Downloads a blob from the bucket."""
    try:
        logger.info(f"Attempting to download {source_blob_name} from bucket {bucket_name}")
        # Initialize the GCS client
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(source_blob_name)

        # Create directory if it doesn't exist
        dest_dir = os.path.dirname(destination_file_name)
        os.makedirs(dest_dir, exist_ok=True)
        logger.info(f"Created directory: {os.path.abspath(dest_dir)}")

        # Download the blob
        blob.download_to_filename(destination_file_name)
        logger.info(f"Downloaded {source_blob_name} to {destination_file_name}")

        # Verify the file exists
        if os.path.exists(destination_file_name):
            logger.info(f"Verified file exists at: {os.path.abspath(destination_file_name)}")
            return True
        else:
            logger.error(f"File was not created at: {os.path.abspath(destination_file_name)}")
            return False
    except Exception as e:
        logger.error(f"Error downloading {source_blob_name}: {str(e)}")
        return False

def list_blobs_with_prefix(bucket_name, prefix):
    """Lists all the blobs in the bucket with the given prefix."""
    try:
        storage_client = storage.Client()
        blobs = storage_client.list_blobs(bucket_name, prefix=prefix)
        blob_list = list(blobs)
        logger.info(f"Found {len(blob_list)} blobs with prefix '{prefix}' in bucket '{bucket_name}'")
        return blob_list
    except Exception as e:
        logger.error(f"Error listing blobs with prefix '{prefix}': {str(e)}")
        return []

def download_latest_embeddings(bucket_name, output_dir="data"):
    """
    Downloads the latest train and test embeddings and metadata from GCS.

    Args:
        bucket_name: Name of the GCS bucket
        output_dir: Local directory to save the downloaded files

    Returns:
        dict: Paths to the downloaded files
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)

    # Get the latest train embeddings
    train_blobs = list_blobs_with_prefix(bucket_name, "embeddings/train_embeddings_")
    if not train_blobs:
        logger.error("No train embeddings found in the bucket")
        return None

    # Sort by creation time (newest first)
    train_blobs.sort(key=lambda x: x.time_created, reverse=True)
    latest_train_blob = train_blobs[0]

    # Get the latest test embeddings
    test_blobs = list_blobs_with_prefix(bucket_name, "embeddings/test_embeddings_")
    if not test_blobs:
        logger.error("No test embeddings found in the bucket")
        return None

    # Sort by creation time (newest first)
    test_blobs.sort(key=lambda x: x.time_created, reverse=True)
    latest_test_blob = test_blobs[0]

    # Get the latest metadata
    metadata_blobs = list_blobs_with_prefix(bucket_name, "metadata/metadata_")
    if not metadata_blobs:
        logger.error("No metadata found in the bucket")
        return None

    # Sort by creation time (newest first)
    metadata_blobs.sort(key=lambda x: x.time_created, reverse=True)
    latest_metadata_blob = metadata_blobs[0]

    # Download the latest files
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    train_path = os.path.join(output_dir, f"train_embeddings_{timestamp}.npz")
    test_path = os.path.join(output_dir, f"test_embeddings_{timestamp}.npz")
    metadata_path = os.path.join(output_dir, f"metadata_{timestamp}.json")

    success_train = download_blob(bucket_name, latest_train_blob.name, train_path)
    success_test = download_blob(bucket_name, latest_test_blob.name, test_path)
    success_metadata = download_blob(bucket_name, latest_metadata_blob.name, metadata_path)

    if not (success_train and success_test and success_metadata):
        logger.error("Failed to download one or more files")
        return None

    return {
        "train_embeddings_path": train_path,
        "test_embeddings_path": test_path,
        "metadata_path": metadata_path
    }

def main():
    """Main function to download embeddings from GCS."""
    # Set up environment variables
    bucket_name = os.environ.get("GCP_BUCKET_NAME", "resumatrix-embeddings")
    output_dir = os.environ.get("DATA_DIR", "data")
    gcp_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    # Log essential information
    logger.info(f"Using GCP bucket: {bucket_name}")
    logger.info(f"Saving to output directory: {output_dir}")

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    logger.info(f"Created output directory at: {os.path.abspath(output_dir)}")

    # Ensure GCP credentials are properly set
    if gcp_credentials:
        # If the path is relative, convert it to absolute
        if not os.path.isabs(gcp_credentials):
            gcp_credentials = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', gcp_credentials))
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = gcp_credentials
        logger.info(f"Using GCP credentials from: {gcp_credentials}")

        # Check if the file exists
        if os.path.exists(gcp_credentials):
            logger.info("GCP credentials file exists.")
        else:
            logger.error(f"GCP credentials file does not exist at: {gcp_credentials}")
    else:
        logger.warning("GOOGLE_APPLICATION_CREDENTIALS not set. Using default credentials.")

    logger.info(f"Downloading embeddings from bucket: {bucket_name}")
    result = download_latest_embeddings(bucket_name, output_dir)

    if result:
        logger.info("Successfully downloaded embeddings and metadata")
        # Save paths to a file for the next step
        file_paths_json = os.path.join(output_dir, "file_paths.json")
        logger.info(f"Saving file paths to: {os.path.abspath(file_paths_json)}")
        try:
            with open(file_paths_json, "w") as f:
                json.dump(result, f)
            logger.info(f"Successfully saved file paths to: {os.path.abspath(file_paths_json)}")
            # Verify the file exists
            if os.path.exists(file_paths_json):
                logger.info(f"Verified file_paths.json exists at: {os.path.abspath(file_paths_json)}")
            else:
                logger.error(f"file_paths.json was not created at: {os.path.abspath(file_paths_json)}")
        except Exception as e:
            logger.error(f"Error saving file paths: {str(e)}")
            exit(1)
    else:
        logger.error("Failed to download embeddings and metadata")
        exit(1)

if __name__ == "__main__":
    main()
