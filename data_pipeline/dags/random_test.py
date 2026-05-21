from google.cloud import storage
import os, shutil

BUCKET_NAME = "us-east1-mlops-dev-8ad13d78-bucket"


def load_resumes(source_dir):
    print("Loading dataset for resume classification.")
    """
        Prerequisites:
        Python library needed: google-cloud-storage
        Download JSON key file from google cloud console.
            Go to "IAM & Admin / Service Accounts".
            Click on the "awesome-nimbus" service account.
            Click on the "Keys" tab. Click on Add key -> Create new key -> Key type: JSON.
            The JSON file of the private key will be downloaded to your local.
        Set an environment variable to point to the key file:
            export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
        Have Google Cloud CLI installed. Enter the command "gcloud init".
            Re-initialize configuration. Option 1.
            Choose your account that is associated with the GCP project.
            Pick our cloud project to use, namely, awesome-nimbus.
            Do not configure region and zone.
        Run the command "gcloud auth application-default login".
            This opens a new tab in your browser. Allow permissions for the account you had selected initially.
            Credentials will be set and this python function should run.
    """
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.bucket(BUCKET_NAME)

    # Get the blob
    blobs = bucket.list_blobs(prefix=source_dir)

    current_file_path = os.path.abspath(__file__)

    parent_dir = current_file_path[:current_file_path.index("ResuMatrix") + 10]
    data_dir = os.path.join(parent_dir, "temp_data_store")

    # Cleaning temporary data store before loading in new resumes
    if os.path.isdir(data_dir):
        for filename in os.listdir(data_dir):
            file_path = os.path.join(data_dir, filename)
            try:
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print('Failed to delete %s. Reason: %s' % (file_path, e))

    os.makedirs(data_dir, exist_ok=True)

    for blob in blobs:
        # Skip any "directory" blobs.
        if blob.name.endswith('/'):
            continue

        # Remove the prefix from the blob name to get the relative file path.
        relative_path = os.path.relpath(blob.name, source_dir)
        local_file_path = os.path.join(data_dir, relative_path)

        # Create local directories if they don't exist.
        local_dir = os.path.dirname(local_file_path)
        if not os.path.exists(local_dir):
            os.makedirs(local_dir)

        # Download the blob to the local file.
        blob.download_to_filename(local_file_path)
        print(f"Downloaded {blob.name} to {local_file_path}")
    print("Successfully loaded resume classification dataset!")

load_resumes("random_resumes")
