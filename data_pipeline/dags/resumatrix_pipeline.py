from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.empty import EmptyOperator
from airflow.operators.email import EmailOperator
import logging
import os

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('/opt/airflow/logs/resumatrix_pipeline.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

default_args = {
        'owner': 'admin',
        'start_date': datetime(2025, 2, 28),
        'retries': 1,
        'retry_delay': timedelta(minutes=3),
        'email_on_failure': True,
        'email_on_success': True,
        'email': ['mlops.team20@gmail.com'],
        }

DATA_DIR = '/opt/airflow/data'  # Use absolute path consistent with Docker setup

os.makedirs(DATA_DIR, exist_ok=True)


# Pipeline

def load_resumes():
    logger.info("Loading dataset for resume classification.")
    # ... rest of the function


def extract_text_from_pdf():
    logger.info("Extracting text from pdf.")
    # ... rest of the function


def data_cleaning():
    logger.info("Cleaning data and removing personal information.")
    # ... rest of the function


def generate_embeddings():
    logger.info("Generating Embeddings.")
    # ... rest of the function


def parsing_text_json_schema():
    logger.info("Parsing text for LLM in JSON schema.")
    # ... rest of the function

def data_transform():
    logger.info("Transforming data into necessary format.")
    # ... rest of the function


with (DAG(
        'resumatrix_data_pipeline_dag',
        default_args=default_args,
        description="A pipeline for extracting text from resumes and creating embeddings"
        ) as dag):

    start_task = EmptyOperator(task_id='start')

    load_task = PythonOperator(
        task_id="load_resumes_task",
        python_callable=load_resumes,
        dag=dag
    )

    extract_task = PythonOperator(
        task_id="sample_extract_text_task",
        python_callable=extract_text_from_pdf,
        dag=dag
    )

    data_cleaning_task = PythonOperator(
        task_id="data_cleaning_task",
        python_callable=data_cleaning,
        dag=dag
    )

    embed_task = PythonOperator(
        task_id="embedding_generation_task",
        python_callable=generate_embeddings,
        dag=dag
    )

    parse_text_json_task = PythonOperator(
        task_id="parse_text_json_task",
        python_callable=parsing_text_json_schema,
        dag=dag
    )

    data_transformation_task = PythonOperator(
        task_id="data_transformation_task",
        python_callable=data_transform,
        dag=dag
    )

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
    start_task >> load_task >> extract_task >> data_cleaning_task >> [embed_task, parse_text_json_task] >> data_transformation_task >> end_task >> [email_success, email_failure]

