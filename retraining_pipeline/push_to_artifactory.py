#!/usr/bin/env python3
"""
Push the trained model to Google Artifact Registry.
This script:
1. Checks if a new model has been saved
2. Builds a Docker image with the model
3. Pushes the image to Google Artifact Registry
"""

import os
import sys
import logging
import subprocess
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_for_new_model(model_registry_dir="model_registry"):
    """Check if a new model has been saved."""
    indicator_file = os.path.join(model_registry_dir, "new_model_saved.txt")

    if not os.path.exists(indicator_file):
        logger.info("No new model found.")
        return None

    # Read the indicator file to get the model path
    with open(indicator_file, "r") as f:
        content = f.read()

    # Extract the model path from the content
    import re
    match = re.search(r"New model saved at (.*) with timestamp", content)
    if not match:
        logger.error("Could not extract model path from indicator file.")
        return None

    model_path = match.group(1)
    if not os.path.exists(model_path):
        logger.error(f"Model file {model_path} does not exist.")
        return None

    return model_path

def build_and_push_docker_image(model_path):
    """Build a Docker image with the model and push it to Google Artifact Registry."""
    try:
        # Get environment variables
        gcp_project_id = os.environ.get("GCP_PROJECT_ID")
        artifact_registry_repo = os.environ.get("ARTIFACT_REGISTRY_REPO")
        gcp_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

        # Check if sudo is available
        use_sudo = False
        try:
            sudo_check = subprocess.run("sudo -n true", shell=True, capture_output=True, text=True)
            use_sudo = sudo_check.returncode == 0
            if use_sudo:
                logger.info("Using sudo for Docker commands")
            else:
                logger.info("Sudo not available, using Docker commands directly")
        except Exception as e:
            logger.warning(f"Error checking sudo availability: {str(e)}")
            logger.info("Proceeding without sudo")

        # Validate required environment variables
        if not gcp_project_id:
            logger.error("GCP_PROJECT_ID environment variable not set.")
            return False

        if not artifact_registry_repo:
            logger.error("ARTIFACT_REGISTRY_REPO environment variable not set.")
            return False

        if not gcp_credentials:
            logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
            return False

        # Check if the credentials file exists
        if not os.path.exists(gcp_credentials):
            logger.error(f"GCP credentials file not found at: {gcp_credentials}")
            return False

        # Create a timestamp for the image tag
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        image_tag = f"{artifact_registry_repo}:{timestamp}"
        logger.info(f"Generated image tag: {image_tag}")

        # 1. Copy the model file to the current directory
        logger.info(f"Copying model file: {model_path}")
        model_filename = os.path.basename(model_path)
        copy_command = f"cp {model_path} ."
        process = subprocess.run(copy_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Error copying model file: {process.stderr}")
            return False
        logger.info(f"Successfully copied model file to current directory")

        # 2. Create a Dockerfile
        logger.info("Creating Dockerfile")
        with open("ModelDockerfile", "w") as f:
            f.write(f"""FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy the model file
COPY {model_filename} /app/model.joblib

# Install dependencies
RUN pip install --no-cache-dir joblib scikit-learn xgboost numpy

# Create an entrypoint script
RUN echo '#!/bin/bash\\necho "Model container is running. Use this container as a base for inference."' > /app/entrypoint.sh && \\
    chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
""")
        logger.info("Successfully created Dockerfile")

        # 3. Authenticate with Google Cloud
        logger.info("Authenticating with Google Cloud")
        auth_command = f"gcloud auth activate-service-account --key-file={gcp_credentials}"
        process = subprocess.run(auth_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Error authenticating with Google Cloud: {process.stderr}")
            return False
        logger.info("Successfully authenticated with Google Cloud")

        # 4. Configure Docker for Google Artifact Registry
        logger.info("Configuring Docker for Google Artifact Registry")
        # Extract the registry host from the artifact_registry_repo
        registry_host = artifact_registry_repo.split('/')[0]  # e.g., us-east1-docker.pkg.dev
        configure_command = f"gcloud auth configure-docker {registry_host} --quiet"
        process = subprocess.run(configure_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Error configuring Docker for Google Artifact Registry: {process.stderr}")
            return False
        logger.info("Successfully configured Docker for Google Artifact Registry")

        # 5. Build the Docker image
        logger.info(f"Building Docker image: {image_tag}")
        # Use sudo if available, otherwise try without sudo
        docker_cmd_prefix = "sudo " if use_sudo else ""
        build_command = f"{docker_cmd_prefix}docker build -f ModelDockerfile -t {image_tag} ."
        process = subprocess.run(build_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Error building Docker image: {process.stderr}")
            # If we didn't use sudo and it failed, try with sudo as a fallback
            if not use_sudo:
                logger.info("Trying with sudo as fallback")
                build_command = f"sudo docker build -f ModelDockerfile -t {image_tag} ."
                process = subprocess.run(build_command, shell=True, capture_output=True, text=True)
                if process.returncode != 0:
                    logger.error(f"Error building Docker image with sudo fallback: {process.stderr}")
                    return False
                else:
                    use_sudo = True  # Use sudo for subsequent commands
                    logger.info("Successfully built Docker image with sudo fallback")
            else:
                return False
        else:
            logger.info("Successfully built Docker image")

        # 6. Push the Docker image to Google Artifact Registry
        logger.info(f"Pushing Docker image to Google Artifact Registry: {image_tag}")
        # Use sudo if available, otherwise try without sudo
        docker_cmd_prefix = "sudo " if use_sudo else ""
        push_command = f"{docker_cmd_prefix}docker push {image_tag}"
        process = subprocess.run(push_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.error(f"Error pushing Docker image to Google Artifact Registry: {process.stderr}")
            # If we didn't use sudo and it failed, try with sudo as a fallback
            if not use_sudo:
                logger.info("Trying with sudo as fallback")
                push_command = f"sudo docker push {image_tag}"
                process = subprocess.run(push_command, shell=True, capture_output=True, text=True)
                if process.returncode != 0:
                    logger.error(f"Error pushing Docker image with sudo fallback: {process.stderr}")
                    return False
                else:
                    logger.info("Successfully pushed Docker image with sudo fallback")
            else:
                return False
        logger.info("Successfully pushed Docker image to Google Artifact Registry")

        # 7. Save the image tag for reference
        with open(os.path.join("model_registry", "latest_image.txt"), "w") as f:
            f.write(image_tag)
        logger.info(f"Saved image tag to model_registry/latest_image.txt")

        # 8. Clean up temporary files
        logger.info("Cleaning up temporary files")
        cleanup_command = f"rm ModelDockerfile {model_filename}"
        process = subprocess.run(cleanup_command, shell=True, capture_output=True, text=True)
        if process.returncode != 0:
            logger.warning(f"Error cleaning up temporary files: {process.stderr}")
            # Continue anyway, this is not critical
        else:
            logger.info("Successfully cleaned up temporary files")

        # 9. Remove the indicator file
        try:
            os.remove(os.path.join("model_registry", "new_model_saved.txt"))
            logger.info("Removed indicator file")
        except Exception as e:
            logger.warning(f"Error removing indicator file: {str(e)}")
            # Continue anyway, this is not critical

        logger.info(f"Successfully pushed model to Google Artifact Registry: {image_tag}")
        return True

    except Exception as e:
        logger.error(f"Error building and pushing Docker image: {str(e)}")
        return False

def main():
    """Main function to push the model to Google Artifact Registry."""
    # Get environment variables
    gcp_project_id = os.environ.get("GCP_PROJECT_ID")
    gcp_credentials = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    artifact_registry_repo = os.environ.get("ARTIFACT_REGISTRY_REPO")

    # Log essential information

    # Validate required environment variables
    if not gcp_credentials:
        logger.error("GOOGLE_APPLICATION_CREDENTIALS environment variable not set.")
        sys.exit(1)
    else:
        logger.info(f"Using GCP credentials from: {gcp_credentials}")
        # Check if the file exists
        if not os.path.exists(gcp_credentials):
            logger.error(f"GCP credentials file not found at: {gcp_credentials}")
            sys.exit(1)
        logger.info("GCP credentials file exists.")

    if not gcp_project_id:
        logger.error("GCP_PROJECT_ID environment variable not set.")
        sys.exit(1)
    else:
        logger.info(f"Using GCP project ID: {gcp_project_id}")

    if not artifact_registry_repo:
        logger.error("ARTIFACT_REGISTRY_REPO environment variable not set.")
        sys.exit(1)
    else:
        logger.info(f"Using Artifact Registry repo: {artifact_registry_repo}")

    # Check if a new model has been saved
    model_path = check_for_new_model()
    if not model_path:
        logger.info("No new model to push to Google Artifact Registry.")
        sys.exit(0)

    logger.info(f"Found new model at: {model_path}")

    # Build and push the Docker image
    success = build_and_push_docker_image(model_path)
    if not success:
        logger.error("Failed to push model to Google Artifact Registry.")
        sys.exit(1)

    logger.info("Successfully pushed model to Google Artifact Registry.")
    sys.exit(0)

if __name__ == "__main__":
    main()
