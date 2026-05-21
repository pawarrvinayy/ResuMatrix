import logging
import os, sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/airflow/logs/deployment_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.email import EmailOperator
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.utils.log.logging_mixin import LoggingMixin
from airflow.providers.google.cloud.hooks.gcs import GCSHook
import pandas as pd
import io
from docker.types import Mount
from urllib.parse import urlparse

# Using Airflow's built-in logger
log = LoggingMixin().log

default_args = {
        'owner': 'admin',
        'start_date': datetime(2025, 4, 3),
        'retries': 1,
        'retry_delay': timedelta(minutes=3),
        'email_on_failure': True,
        'email_on_success': True,
        'email': ['mlops.team20@gmail.com'],
        }

# DATA_DIR = '~/data/workspace/mlops/ResuMatrix/data'

BUCKET_NAME = os.environ.get("GCP_BUCKET_NAME", "resumatrix-bucket")
SEEN_PATH = "resumes/seen_directories.txt"

# HOST_DATA = os.path.join(os.environ['GCP_JSON_PATH'], 'data')

# os.makedirs(DATA_DIR, exist_ok=True)


# Pipeline

# def load_resumes(**kwargs):
#     log.info("Loading data for resume classification.")
#     """
#         Prerequisites:
#         Python library needed: google-cloud-storage
#         Download JSON key file from google cloud console.
#             Go to "IAM & Admin / Service Accounts".
#             Click on the "awesome-nimbus" service account.
#             Click on the "Keys" tab. Click on Add key -> Create new key -> Key type: JSON.
#             The JSON file of the private key will be downloaded to your local.
#         Set an environment variable to point to the key file:
#             export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
#         Have Google Cloud CLI installed. Enter the command "gcloud init".
#             Re-initialize configuration. Option 1.
#             Choose your account that is associated with the GCP project.
#             Pick our cloud project to use, namely, awesome-nimbus.
#             Do not configure region and zone.
#         Run the command "gcloud auth application-default login".
#             This opens a new tab in your browser. Allow permissions for the account you had selected initially.
#             Credentials will be set and this python function should run.
#     """
#     print("Loading dataset for resume classification.")
#     hook = GCSHook(gcp_conn_id='google_cloud_default')
#     storage_client = hook.get_conn()
#
#     # Get the bucket
#     bucket = storage_client.bucket(BUCKET_NAME)
#
#     dag_run_conf = kwargs.get('dag_run').conf or {}
#     source_dir = dag_run_conf.get('source_dir', 'random_resumes')
#
#     # Get the blob
#     blobs = bucket.list_blobs(prefix=source_dir)
#
#     current_file_path = os.path.abspath(__file__)
#     log.info("Current file path: ")
#     log.info(current_file_path)
#
#     parent_dir = current_file_path[:current_file_path.index("dags") + 4]
#     data_dir = os.path.join(parent_dir, "temp_data_store")
#     log.info("Data directory: ")
#     log.info(data_dir)
#
#     # Cleaning temporary data store before loading in new resumes
#     if os.path.isdir(data_dir):
#         for filename in os.listdir(data_dir):
#             file_path = os.path.join(data_dir, filename)
#             try:
#                 if os.path.isfile(file_path) or os.path.islink(file_path):
#                     os.unlink(file_path)
#                 elif os.path.isdir(file_path):
#                     shutil.rmtree(file_path)
#             except Exception as e:
#                 print('Failed to delete %s. Reason: %s' % (file_path, e))
#
#     os.makedirs(data_dir, exist_ok=True)
#
#     for blob in blobs:
#         # Skip any "directory" blobs.
#         if blob.name.endswith('/'):
#             continue
#
#         # Remove the prefix from the blob name to get the relative file path.
#         relative_path = os.path.relpath(blob.name, source_dir)
#         log.info("Relative path: ")
#         log.info(relative_path)
#         local_file_path = os.path.join(data_dir, relative_path)
#         log.info("Local File Path: ")
#         log.info(local_file_path)
#
#         # Create local directories if they don't exist.
#         local_dir = os.path.dirname(local_file_path)
#         if not os.path.exists(local_dir):
#             os.makedirs(local_dir, exist_ok=True)
#
#         # Download the blob to the local file.
#         blob.download_to_filename(local_file_path)
#         print(f"Downloaded {blob.name} to {local_file_path}")
#     log.info("Successfully loaded resume classification dataset!")
#     print("Successfully loaded resume classification dataset!")

def get_job_id(**kwargs):
    dag_run_conf = kwargs.get('dag_run').conf or {}
    job_id = dag_run_conf.get('job_id')
    if not job_id:
        raise ValueError(“No job_id provided in dag_run conf. Trigger with: {'job_id': '<uuid>'}”)
    log.info(f”Received job_id: {job_id}”)
    gcs_path = f”gs://{BUCKET_NAME}/resumes/{job_id}/{job_id}.csv”
    log.info(f”Constructed GCS path: {gcs_path}”)
    return gcs_path

def load_data_for_fit_pred(ti, **kwargs):
    """
    Assumptions:
        - There is a CSV loaded into "gs://{bucket_name}/{prefix}/{job_id}/" with all the resumes that need fit classification.
        - There is a TXT loaded into "gs://{bucket_name}/{prefix}/{job_id}/" with the corresponding JD that those resumes need to be fit
        against.
        - CSV format: 2 columns, resume_id and resume.
        - Only one CSV file and one TXT file is present in the directory.
    """
    from fetch_training_data import check_api_connection
    import requests
    from pathlib import Path
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    client = hook.get_conn()
    bucket = client.get_bucket(BUCKET_NAME)
    # dag_run_conf = kwargs.get('dag_run').conf or {}
    csv_file_path = ti.xcom_pull(task_ids="get_job_id_task")
    # form: gs://us-east1-mlops-dev-8ad13d78-bucket/resumes/0f54f3e0-5a58-4996-b7ed-abe08f34969c/0f54f3e0-5a58-4996-b7ed-abe08f34969c.csv
    # csv_file_Path = Path(csv_file_path)
    # blob_name = csv_file_Path.parts[3:]
    # blob_name = "/".join(blob_name)
    parts = csv_file_path.split("/")
    i = parts.index("resumes")
    parent_directory = "/".join(parts[i : i + 2])
    blob_name = "/".join(parts[i:])
    log.info(f"Parent directory: {parent_directory}")
    job_id = csv_file_path.rstrip("/").split("/")[-2]
    API_BASE_URL = os.getenv("RESUMATRIX_API_URL", "http://host.docker.internal:8000/api")
    jd_text = ""
    resume_df = pd.DataFrame()
    if check_api_connection():
        log.info(f"Requesting job description from: {API_BASE_URL}/jobs/{job_id}/")
        jd_url = f"{API_BASE_URL}/jobs/{job_id}/"
        jd_response = requests.get(jd_url, timeout=10)
        logger.info(f"JD response status code: {jd_response.status_code}")
        try:
            logger.info(f"JD response headers: {jd_response.headers}")
            logger.info(f"JD response content (first 500 chars): {jd_response.text[:500]}...")
        except Exception as e:
            logger.warning(f"Could not log resumes response details: {e}")
        if jd_response.status_code == 200:
            jd_json = jd_response.json()
            log.info(f"JD JSON keys: {jd_json.keys()}")
            jd_text = jd_json['job']['job_text']
        blob = bucket.blob(blob_name)
        csv_data = blob.download_as_text(encoding='utf-8')
        resume_df = pd.read_csv(io.StringIO(csv_data))
    if len(resume_df.index) == 0:
        raise ValueError("No resume CSV file found in given source directory.")
    if len(jd_text) == 0:
        raise ValueError("No text file found for Job Description or the file is empty.")

    resume_df['job_description_text'] = jd_text
    log.info("Resume DF shape: ")
    log.info(resume_df.shape)

    csv_data = resume_df.to_csv(index=False)

    # Define your GCS bucket and blob name
    destination_blob_name = f"{parent_directory}/resume_jd_data.csv"  # Replace with desired blob path
    log.info(f"Destination blob name: {destination_blob_name}")

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(csv_data, content_type='text/csv')

    # Construct a GCS path that can be used by downstream tasks
    gcs_path = f"{destination_blob_name}"

    ti.xcom_push(key="data_path", value=gcs_path)

def gen_embeddings(ti, **kwargs):
    from data_processing.data_preprocessing import extract_embeddings
    from pathlib import Path
    gcs_path = ti.xcom_pull(key="data_path", task_ids="load_data_for_fit_pred_task")
    # Path of the form: "gs://us-east1-mlops-dev-8ad13d78-bucket/resumes/0f54f3e0-5a58-4996-b7ed-abe08f34969c/resume_jd_data.csv"
    if not gcs_path:
        raise ValueError("No GCS path found in XCom. Check upstream task.")
    log.info("GCS Path from previous task: ")
    log.info(gcs_path)

    # Parse the GCS path to extract bucket and blob names
    parsed = urlparse(gcs_path)
    blob_name = parsed.path.lstrip('/')
    log.info("Blob name: ")
    log.info(blob_name)

    # Initialize GCS client and download the CSV file as string
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    client = hook.get_conn()
    bucket = client.get_bucket(BUCKET_NAME)
    blob = bucket.blob(blob_name)
    csv_data = blob.download_as_string().decode('utf-8')

    # Load the CSV data into a pandas DataFrame
    resume_df = pd.read_csv(io.StringIO(csv_data))
    log.info("Resume DF shape: ")
    log.info(resume_df.shape)
    blob.delete()

    X_test = extract_embeddings(resume_df, data_type="deployment")
    csv_data = X_test.to_csv(index=False)
    csv_file_Path = Path(gcs_path)
    blob_name = csv_file_Path.parts[2:]
    blob_name = "/".join(blob_name)
    parent_directory = os.path.dirname(gcs_path)
    # job_id = gcs_path.rstrip("/").split("/")[-2]
    destination_blob_name = f"{parent_directory}/resume_jd_data.csv"  # Replace with desired blob path

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(csv_data, content_type='text/csv')

    # Construct a GCS path that can be used by downstream tasks
    # gcs_path = f"gs://{BUCKET_NAME}/{destination_blob_name}"

    ti.xcom_push(key="data_path", value=destination_blob_name)
    # buffer = io.BytesIO()
    # np.save(buffer, X_test)
    # buffer.seek(0)
    #
    # destination_blob_name = f"{os.path.dirname(blob_name).split('/', 3)[-1]}/embeddings_np_array.npy"  # Replace with desired blob path
    # log.info(f"Destination_blob_name: {destination_blob_name}")
    #
    # # Initialize GCS client and upload the file from the buffer
    # client = storage.Client()
    # bucket = client.get_bucket(BUCKET_NAME)
    # blob = bucket.blob(destination_blob_name)
    #
    # # Upload the NumPy binary data to GCS
    # blob.upload_from_file(buffer, content_type="application/octet-stream")
    #
    # # Construct the GCS path (URI) to be passed via XCom
    # gcs_path = f"{destination_blob_name}"
    # ti.xcom_push(key="numpy_path", value=gcs_path)

def run_inference(ti, **kwargs):
    import pickle
    import numpy as np
    # form: resumes/0f54f3e0-5a58-4996-b7ed-abe08f34969c/resume_jd_data.csv
    embeddings_csv_blob_name = ti.xcom_pull(key="data_path", task_ids="gen_embeddings_task")
    model_blob_name = "model/xgboost_model_with_similarity_20250420_124918.pkl"

    hook = GCSHook(gcp_conn_id='google_cloud_default')
    client = hook.get_conn()

    # 2. Reference your bucket + blob
    bucket = client.get_bucket(BUCKET_NAME)
    blob = bucket.blob(model_blob_name)

    data_bytes = blob.download_as_bytes()  # or .download_as_string()
    model = pickle.loads(data_bytes)

    blob = bucket.blob(embeddings_csv_blob_name)
    csv_data = blob.download_as_string().decode('utf-8')

    # Load the CSV data into a pandas DataFrame
    resume_df = pd.read_csv(io.StringIO(csv_data))
    resume_df['resume_embeddings'] = resume_df['resume_embeddings'].apply(
        lambda s: np.fromstring(s.strip('[]'), sep=' ').tolist())
    resume_df['job_embeddings'] = resume_df['job_embeddings'].apply(
        lambda s: np.fromstring(s.strip('[]'), sep=' ').tolist())
    X = np.array([np.concatenate([r, j]) for r, j in zip(resume_df['resume_embeddings'], resume_df['job_embeddings'])])
    preds = model.predict(X).tolist()
    resume_df['predictions'] = preds

    csv_data = resume_df.to_csv(index=False)

    # Define your GCS bucket and blob name
    destination_blob_name = f"{os.path.dirname(embeddings_csv_blob_name)}/resume_jd_data.csv"
    log.info(f"Destination blob name: {destination_blob_name}")

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(csv_data, content_type='text/csv')

    # Construct a GCS path that can be used by downstream tasks
    gcs_path = f"{destination_blob_name}"

    ti.xcom_push(key="data_path", value=gcs_path)

def push_results_to_supabase(ti, **kwargs):
    import requests
    import random
    embeddings_csv_blob_name = ti.xcom_pull(key="data_path", task_ids="gen_embeddings_task")
    # form: resumes/0f54f3e0-5a58-4996-b7ed-abe08f34969c/resume_jd_data.csv
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    client = hook.get_conn()

    # 2. Reference your bucket + blob
    bucket = client.get_bucket(BUCKET_NAME)
    blob = bucket.blob(embeddings_csv_blob_name)
    csv_data = blob.download_as_string().decode('utf-8')

    # Load the CSV data into a pandas DataFrame
    resume_df = pd.read_csv(io.StringIO(csv_data))
    resume_df['predictions'] = resume_df['predictions'].astype(int)
    resume_df['predictions'] = resume_df['predictions'].replace({0: -1, 1: 0})
    output = []
    for _, row in resume_df.iterrows():
        output.append({
            'id': row['resume_id'],
            'status': row['predictions']
        })
    put_request_json = {
        "resumes": output
    }
    API_BASE_URL = os.getenv("RESUMATRIX_API_URL", "localhost")
    job_id = embeddings_csv_blob_name.split('/')[1]
    jd_url = f"{API_BASE_URL}/jobs/{job_id}/resumes/"
    requests.put(jd_url, json=put_request_json)
    rank_url = f"{API_BASE_URL}/jobs/{job_id}/rank/"
    requests.post(rank_url)



# def extract_text_from_pdf():
#     log.info("Extracting text from pdf.")
#     print("Extracting text from pdf.")
#
#
# def data_cleaning():
#     log.info("Cleaning data and removing personal information.")
#     print("Cleaning data and removing personal information.")
#
#
# def generate_embeddings():
#     log.info("Generating Embeddings.")
#     print("Generating Embeddings.")
#     log.info("Embeddings generated successfully!")
#     print("Embeddings generated successfully!")
#
#
# def parsing_text_json_schema():
#     log.info("Parsing text for LLM in JSON schema.")
#     print("Parsing text for LLM in JSON schema.")
#     log.info("Parsed data successfully!")
#     print("Parsed data successfully!")
#
# def data_transform():
#     log.info("Transforming data into necessary format.")
#     print("Transforming data into necessary format.")
#
#     log.info("Successfully transformed data!")
#     print("Successfully transformed data!")


with (DAG(
        'resumatrix_deployment_data_pipeline_dag',
        default_args=default_args,
        description="A pipeline for extracting text from resumes and creating embeddings",
        schedule_interval="@once",
        is_paused_upon_creation=False
)
as dag):

    get_job_id_task = PythonOperator(
        task_id='get_job_id_task',
        python_callable=get_job_id,
        provide_context=True,
    )

    load_data_for_fit_pred_task = PythonOperator(
        task_id="load_data_for_fit_pred_task",
        python_callable=load_data_for_fit_pred,
        dag=dag,
        provide_context=True
    )

    gen_embeddings_task = PythonOperator(
        task_id="gen_embeddings_task",
        python_callable=gen_embeddings,
        dag=dag,
        provide_context=True
    )

    run_inference = PythonOperator(
        task_id="run_inference_task",
        python_callable=run_inference,
        dag=dag,
        provide_context=True
    )

    push_results_to_supabase = PythonOperator(
        task_id="push_results_to_supabase_task",
        python_callable=push_results_to_supabase,
        dag=dag,
        provide_context=True
    )

    # run_inference_task = DockerOperator(
    #     task_id='run_inference_task',
    #     image='us-east1-docker.pkg.dev/awesome-nimbus-452221-v2/resume-fit-supervised/xgboost_and_cosine_similarity:20250420_031643',
    #     api_version='auto',
    #     entrypoint='/bin/bash',
    #     command=[
    #     '-c',
    #     'python /app/scripts/inference.py '
    #     '--input /data/input.json '
    #     '--output /data/output.json '
    #     '&& sleep infinity'
    #     ],
    #     auto_remove='never',
    #     tty=True,
    #     docker_url='unix://var/run/docker.sock',
    #     network_mode='bridge',
    #     mounts=[
    #         Mount(source="data_volume",
    #               target='/data',
    #               type='volume'),
    #         Mount(source=os.environ['GCP_JSON_PATH'],
    #               target='/etc/secrets/gcp_key.json',
    #               type='bind',
    #               read_only=True),
    #         # ${AIRFLOW_PROJ_DIR:-.}/scripts:/opt/airflow/scripts
    #         Mount(source="scripts_volume",
    #               target="/app/scripts",
    #               type="volume")
    #     ],
    #     environment={"EMBEDDINGS_FILE_PATH": "{{ ti.xcom_pull(task_ids='gen_embeddings_task', key='data_path') }}/",
    #                  'GOOGLE_APPLICATION_CREDENTIALS': '/etc/secrets/gcp_key.json',
    #                  'GCP_PROJECT_ID': os.environ['GCP_PROJECT_ID']},
    #     dag=dag,
    # )

    # embed_task = PythonOperator(
    #     task_id="embedding_generation_task",
    #     python_callable=generate_embeddings,
    #     dag=dag
    # )
    #
    # parse_text_json_task = PythonOperator(
    #     task_id="parse_text_json_task",
    #     python_callable=parsing_text_json_schema,
    #     dag=dag
    # )
    #
    # data_transformation_task = PythonOperator(
    #     task_id="data_transformation_task",
    #     python_callable=data_transform,
    #     dag=dag
    # )

    end_task = EmptyOperator(task_id='end')

    email_success = EmailOperator(
        task_id='send_email_success',
        to='mlops.team20@gmail.com',
        subject='Airflow Task Success: {{ task_instance.task_id }}',
        html_content="""
        <h3>Task {{ task_instance.task_id }} has completed successfully.</h3>
        <p>DAG: {{ dag.dag_id }}</p>
        """,
        trigger_rule='all_success',
        dag=dag
    )

    email_failure = EmailOperator(
        task_id='send_email_failure',
        to='mlops.team20@gmail.com',
        subject='Airflow Task Failed: {{ task_instance.task_id }}',
        html_content="""
        <h3>Task {{ task_instance.task_id }} has failed.</h3>
        <p>DAG: {{ dag.dag_id }}</p>
        """,
        trigger_rule='one_failed',  # Triggers only if a task fails
        dag=dag
    )

    # set the task dependencies
    get_job_id_task >> load_data_for_fit_pred_task >> gen_embeddings_task >> run_inference >> push_results_to_supabase >> end_task >> [email_success, email_failure]

