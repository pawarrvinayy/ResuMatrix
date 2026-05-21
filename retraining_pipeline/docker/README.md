# Unified MLOps Environment: Jenkins + MLflow

This directory contains a Docker setup that runs both Jenkins and MLflow in a single container for model retraining automation.

## Features

- Jenkins LTS with CI/CD plugins
- MLflow tracking server (port 5001)
- Automated model retraining pipeline
- Google Cloud integration

## Prerequisites

- Docker installed
- Google Cloud Platform account with:
  - GCS bucket for embeddings
  - Artifact Registry repository
  - Service account with permissions

## Quick Start

1. Build and run the container:
   ```bash
   cd retraining_pipeline/docker
   chmod +x init-container.sh
   ./init-container.sh
   ```

   The script will:
   - Create Docker volumes
   - Build and run the container
   - Display the Jenkins admin password

2. Set up Docker permissions for Jenkins (required for the pipeline to build and push Docker images):
   ```bash
   chmod +x setup_docker_permissions.sh
   sudo ./setup_docker_permissions.sh
   ```
   See `DOCKER_PERMISSIONS.md` for more details on Docker permissions.

## Manual Setup

```bash
# Build image
docker build -t unified-mlops .

# Create volumes
docker volume create jenkins_home
docker volume create mlflow_data

# Run container
docker run -d --name unified-mlops \
  --restart unless-stopped \
  -p 8080:8080 -p 50000:50000 -p 5001:5001 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v jenkins_home:/var/jenkins_home \
  -v mlflow_data:/mlflow \
  unified-mlops
```

## Jenkins Setup

### Using env_variables.json (Recommended)

1. Ensure your `env_variables.json` file contains the following variables:
   ```json
   {
     "MLFLOW_TRACKING_URI": "http://localhost:5001",
     "GCP_PROJECT_ID": "your-gcp-project-id",
     "GCP_BUCKET_NAME": "your-gcs-bucket-name",
     "GOOGLE_APPLICATION_CREDENTIALS": "path/to/service-account-key.json",
     "EMAIL_ADDRESS": "your-email@example.com",
     "ARTIFACT_REGISTRY_REPO": "region-docker.pkg.dev/project-id/repository-name/image-name"
   }
   ```

2. Upload the `env_variables.json` file to Jenkins:
   - Go to Jenkins dashboard
   - Navigate to Manage Jenkins > Script Console
   - Use the following script to create credentials from your JSON file:

```groovy
import jenkins.model.*
import com.cloudbees.plugins.credentials.*
import com.cloudbees.plugins.credentials.domains.*
import com.cloudbees.plugins.credentials.impl.*
import org.jenkinsci.plugins.plaincredentials.impl.*
import hudson.util.Secret
import groovy.json.JsonSlurper

// Path to the uploaded JSON file (update this path)
def jsonContent = '''PASTE_YOUR_JSON_CONTENT_HERE'''

try {
    // Parse the JSON content
    def jsonSlurper = new JsonSlurper()
    def credentials = jsonSlurper.parseText(jsonContent)

    // Get Jenkins instance
    def jenkins = Jenkins.getInstance()
    def domain = Domain.global()
    def store = jenkins.getExtensionList('com.cloudbees.plugins.credentials.SystemCredentialsProvider')[0].getStore()

    // Add each credential
    credentials.each { key, value ->
        println "Adding credential: ${key}"

        // Create a string credential
        def credential = new StringCredentialsImpl(
            CredentialsScope.GLOBAL,
            key,
            key,
            Secret.fromString(value.toString())
        )

        // Add the credential to the store
        store.addCredentials(domain, credential)
    }

    println "All credentials loaded successfully!"
} catch (Exception e) {
    println "ERROR: ${e.message}"
    e.printStackTrace()
}
```

3. Replace `PASTE_YOUR_JSON_CONTENT_HERE` with the contents of your `env_variables.json` file
4. Click "Run" to execute the script

### Manual Setup (Alternative)

Alternatively, add these credentials manually in Jenkins (Manage Jenkins > Credentials > Add):
- `MLFLOW_TRACKING_URI`: MLflow tracking server URI (http://localhost:5001)
- `GCP_PROJECT_ID`: Your GCP project ID
- `GCP_BUCKET_NAME`: Your GCS bucket name
- `GOOGLE_APPLICATION_CREDENTIALS`: GCP service account key file
- `EMAIL_ADDRESS`: Notification email
- `ARTIFACT_REGISTRY_REPO`: Full path to your Artifact Registry repository (region-docker.pkg.dev/project-id/repository-name/image-name)

## GitHub Webhook Integration

The Jenkins pipeline can be configured to automatically trigger when changes are pushed to specific paths in the GitHub repository.

### Setting up the GitHub Webhook

1. In Jenkins, ensure the GitHub plugin is installed (it's included in the Docker image by default)

#### Option 1: Public Jenkins Server

If your Jenkins server is publicly accessible:

1. Configure your GitHub repository:
   - Go to your GitHub repository > **Settings** > **Webhooks** > **Add webhook**
   - Set **Payload URL** to `http://<your-jenkins-url>/github-webhook/`
   - Set **Content type** to `application/json`
   - Select **Just the push event** for the trigger
   - Click **Add webhook**

#### Option 2: Local Jenkins with Serveo

If your Jenkins server is running locally and not publicly accessible, you can use Serveo to expose it:

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

4. Configure your GitHub repository:
   - Go to your GitHub repository > **Settings** > **Webhooks** > **Add webhook**
   - Set **Payload URL** to `https://yoursubdomain.serveo.net/github-webhook/`
   - Set **Content type** to `application/json`
   - Select **Just the push event** for the trigger
   - Click **Add webhook**

5. Keep the Serveo connection running in your terminal while you want the webhook to be active

#### Other Options

Alternative methods for exposing your local Jenkins server:
- [ngrok](https://ngrok.com/) - Another popular tunneling service
- [localtunnel](https://github.com/localtunnel/localtunnel) - A simpler alternative to ngrok
- GitHub Actions - Consider using GitHub Actions instead of webhooks if tunneling is not feasible

### GitHub Webhook Configuration

The Jenkinsfile includes a `triggers` section that enables GitHub webhook integration:

```groovy
triggers {
    githubPush()
}
```

While this trigger responds to all repository pushes, the pipeline includes a smart filtering mechanism in the first stage that:

1. Checks if the current branch is in the allowed list (main/master)
2. Checks if any of the specific monitored files were changed

```groovy
stage('Check Branch and Changed Files') {
    steps {
        script {
            // Get the current branch name
            def branchName = sh(script: 'git rev-parse --abbrev-ref HEAD', returnStdout: true).trim()

            // Define allowed branches
            def allowedBranches = ['main', 'master', 'origin/main', 'origin/master']

            // Check if current branch is allowed
            if (!allowedBranches.contains(branchName)) {
                currentBuild.result = 'SUCCESS'
                error("Skipping pipeline execution as branch ${branchName} is not in the allowed list.")
            }

            // Get the list of changed files
            def changedFiles = sh(script: 'git diff --name-only HEAD^ HEAD || git diff --name-only origin/main...HEAD', returnStdout: true).trim()

            // Define specific files that should trigger the pipeline
            def relevantFiles = [
                'src/model_training/similarity_with_xgboost.py',
                'src/data_processing/data_preprocessing.py'
            ]

            // Check if any changed file is in our list of relevant files
            def shouldRun = false
            for (def file in changedFiles.split("\n")) {
                if (relevantFiles.contains(file)) {
                    echo "Relevant file changed: ${file}"
                    shouldRun = true
                    break
                }
            }

            // Skip the pipeline if no relevant files were changed
            if (!shouldRun) {
                currentBuild.result = 'SUCCESS'
                error("Skipping pipeline execution as no relevant files were changed.")
            }
        }
    }
}
```

This approach provides efficient branch and path-specific filtering without requiring complex webhook configurations.

## Pipeline Stages

1. **Check Branch and Changed Files**: Determine if the pipeline should run based on branch and changed files
2. **Setup**: Install dependencies
3. **Download**: Get embeddings from GCS
4. **Train**: Train XGBoost model with MLflow tracking
5. **Deploy**: Push model to Google Artifact Registry

## Accessing Services

- Jenkins: http://localhost:8080
- MLflow: http://localhost:5001

## Troubleshooting

- Check logs: `docker logs unified-mlops`
- Ensure Docker socket is properly mounted
