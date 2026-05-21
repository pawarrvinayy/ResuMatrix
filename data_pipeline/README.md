# ResuMatrix Data Pipeline

This directory contains the Airflow data pipelines for the ResuMatrix project. These pipelines handle various data processing tasks including resume embeddings generation, model training, and deployment.

## Prerequisites

Before running the data pipeline, ensure you have the following installed:

- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)
- Git (for cloning the repository)

## Setup Instructions

### 1. First-Time Setup

For a fresh computer installation, follow these steps:

1. Clone the repository:

```bash
git clone https://github.com/your-repo/ResuMatrix.git
cd ResuMatrix
```

2. Make sure Docker and Docker Compose are installed and running on your system

3. Create the necessary directories if they don't exist:

```bash
mkdir -p data_pipeline/logs data_pipeline/plugins data_pipeline/config data_pipeline/data
```

### 2. Environment Configuration

1. Make sure the `.env` file exists in the `data_pipeline` directory with the following variables:

```
SUPABASE_URL=your_supabase_url
SUPABASE_API_KEY=your_supabase_api_key
GCP_BUCKET_NAME=your_gcp_bucket_name
HF_TOKEN=your_huggingface_token
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_api_key
GCP_PROJECT_ID=your_gcp_project_id
GCP_JSON_PATH=./your_gcp_credentials.json
MLFLOW_TRACKING_URI=http://localhost:5001/
ARTIFACT_REGISTRY_REPO=your_artifact_registry_repo
```

2. Ensure your GCP credentials JSON file exists at the path specified in `GCP_JSON_PATH`.

### 3. Directory Structure

Ensure the following directories exist in the `data_pipeline` folder:

```
data_pipeline/
├── dags/           # Contains Airflow DAG definitions
├── config/         # Configuration files
├── plugins/        # Airflow plugins
├── scripts/        # Helper scripts
├── data/           # Data storage
└── logs/           # Log files
```

Also, make sure the `src` directory exists one level up from the `data_pipeline` directory.

## Running Airflow

### Starting Airflow

1. Navigate to the `data_pipeline` directory:

```bash
cd path/to/ResuMatrix/data_pipeline
```

2. Build the Docker images first:

```bash
docker-compose build
```

3. Start the Airflow services using Docker Compose:

```bash
docker-compose up -d
```

These commands will:
- Build the custom Airflow Docker image with all required dependencies
- Start the PostgreSQL database
- Initialize the Airflow database
- Start the Airflow webserver, scheduler, and triggerer

4. Access the Airflow web interface at [http://localhost:8085](http://localhost:8085)
   - Username: airflow
   - Password: airflow

### Stopping Airflow

To stop all Airflow services:

```bash
docker-compose down
```

To stop and remove all containers, networks, and volumes:

```bash
docker-compose down -v
```

## Troubleshooting


### Missing GCP Credentials

If Airflow fails to start due to missing GCP credentials:

1. Ensure your GCP credentials JSON file exists at the path specified in the `.env` file
2. Verify the file has the correct permissions
3. Restart the Airflow services

### Checking Logs

To view logs for troubleshooting:

```bash
docker-compose logs
```

To view logs for a specific service:

```bash
docker-compose logs airflow-webserver
docker-compose logs airflow-scheduler
```

## Available DAGs

The following DAGs are available in this data pipeline:

1. **Embeddings Pipeline** (`embeddings_pipeline.py`): Generates embeddings for resumes
2. **Training Data Pipeline** (`train_data_pipeline.py`): Prepares data for model training
3. **Deployment Pipeline** (`deployment_pipeline.py`): Handles model deployment
4. **ResuMatrix Pipeline** (`resumatrix_pipeline.py`): Main pipeline for the ResuMatrix application

## Development

### Adding New DAGs

To add a new DAG:

1. Create a new Python file in the `dags` directory
2. Define your DAG using the Airflow DAG API
3. Restart the Airflow scheduler or wait for it to detect the new DAG

### Updating Dependencies

If you need to add or update dependencies:

1. Update the `requirements.txt` file
2. Rebuild the Docker containers:

```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Additional Resources

- [Apache Airflow Documentation](https://airflow.apache.org/docs/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
