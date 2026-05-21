# Model Retraining Pipeline

This directory contains the code and configuration for the automated model retraining pipeline.

## Directory Structure

- `docker/`: Contains Docker configuration for the unified Jenkins + MLflow environment
  - `Dockerfile`: Defines the Docker image with Jenkins and MLflow
  - `start-services.sh`: Script to start both Jenkins and MLflow services
  - `init-container.sh`: Script to initialize and run the Docker container
  - `setup_docker_permissions.sh`: Script to set up Docker permissions for Jenkins
  - `DOCKER_PERMISSIONS.md`: Documentation for Docker permissions setup
  - `README.md`: Documentation for the Docker setup

- `Jenkinsfile`: Defines the Jenkins pipeline for model retraining
- `download_from_gcs.py`: Script to download embeddings and metadata from Google Cloud Storage
- `run_retraining.py`: Script to run the model retraining process
- `push_to_artifactory.py`: Script to build and push the Docker image to Google Artifact Registry
- `requirements.txt`: Python dependencies for the retraining pipeline

## Getting Started

1. Set up the Docker environment:
   ```bash
   cd docker
   chmod +x init-container.sh
   ./init-container.sh
   ```
   This script will build and start the Docker container with Jenkins and MLflow.

2. Set up Docker permissions for Jenkins (required for the pipeline to build and push Docker images):
   ```bash
   cd docker
   chmod +x setup_docker_permissions.sh
   sudo ./setup_docker_permissions.sh
   ```
   See `docker/DOCKER_PERMISSIONS.md` for more details on Docker permissions.

3. Access Jenkins at http://localhost:8080 and set up the necessary credentials.

4. Access MLflow at http://localhost:5001 to view experiment results.

5. Create and run the model retraining pipeline in Jenkins.

## GitHub Webhook Integration

The Jenkins pipeline is configured to automatically trigger when changes are pushed to specific paths in the GitHub repository. This is implemented using the GitHub webhook functionality.

### Setting up the GitHub Webhook

#### Option 1: Public Jenkins Server

If your Jenkins server is publicly accessible:

1. In your GitHub repository, go to **Settings** > **Webhooks** > **Add webhook**

2. Configure the webhook:
   - **Payload URL**: `http://<your-jenkins-url>/github-webhook/`
   - **Content type**: `application/json`
   - **Secret**: (Optional) Create a secret token for added security
   - **Which events would you like to trigger this webhook?**: Select "Just the push event"
   - **Active**: Check this box

3. Click **Add webhook** to save

#### Option 2: Local Jenkins with Serveo

If you're running Jenkins locally and need to expose it to GitHub, you can use Serveo:

1. Generate an SSH key if you don't have one:
   ```bash
   ssh-keygen -t rsa -b 4096 -C "your-email@example.com"
   ```

2. Register your key with Serveo by visiting the verification link provided when you first try to connect:
   ```bash
   ssh -R yoursubdomain:80:localhost:8080 serveo.net
   ```
   Follow the Google or GitHub verification link that appears.

3. After verification, connect again to get a persistent URL:
   ```bash
   ssh -R yoursubdomain:80:localhost:8080 serveo.net
   ```
   This will forward traffic from `https://yoursubdomain.serveo.net` to your local Jenkins server.

4. In your GitHub repository, go to **Settings** > **Webhooks** > **Add webhook**

5. Configure the webhook:
   - **Payload URL**: `https://yoursubdomain.serveo.net/github-webhook/`
   - **Content type**: `application/json`
   - **Which events would you like to trigger this webhook?**: Select "Just the push event"
   - **Active**: Check this box

6. Click **Add webhook** to save

7. Keep the Serveo connection running in your terminal while you want the webhook to be active

### Webhook Configuration

The pipeline is configured with a smart filtering mechanism that only runs when:
1. Changes are pushed to the main/master branch
2. The changed files match specific patterns
3. there are new files in the GCP embeddings bucket

The webhook will be triggered for any push to the repository, but the pipeline will first check the branch name and then which files were changed before proceeding.

#### Allowed Branches

The pipeline will only run when changes are pushed to these branches:
- `main`
- `master`
- `origin/main`
- `origin/master`

You can modify the allowed branches in the `Check Branch and Changed Files` stage of the Jenkinsfile.

#### Monitored Files

The pipeline will only run when changes are detected in these specific files:
- `src/model_training/similarity_with_xgboost.py`: The XGBoost similarity model implementation
- `src/data_processing/data_preprocessing.py`: The data preprocessing implementation

You can modify the list of monitored files in the `Check Branch and Changed Files` stage of the Jenkinsfile.

## Pipeline Stages

1. **Check Branch and Changed Files**: Determines if the pipeline should run based on the branch and which files were changed
2. **Setup Python Environment**: Creates a virtual environment and installs dependencies
3. **Download Data from GCS**: Downloads the latest embeddings and metadata from Google Cloud Storage
4. **Train Model**: Trains an XGBoost model and logs metrics to MLflow
5. **Build and Push Docker Image**: Builds a Docker image with the trained model and pushes it to Google Artifact Registry
