#!/usr/bin/env python3
"""
Fetch a DataFrame of embeddings from GCS, run inference with a joblib-loaded model,
and emit JSON results keyed by job_id and resume_id.
"""

import os
import json
import logging
import sys

import numpy as np
import pandas as pd
from joblib import load as joblib_load
from airflow.providers.google.cloud.hooks.gcs import GCSHook
from pandas.api.types import is_list_like

# ─── CONFIG ────────────────────────────────────────────────────────────────────
MODEL_PATH     = '/app/model/model.joblib'
BUCKET_NAME    = "us-east1-mlops-dev-8ad13d78-bucket"
OBJECT_NAME    = os.getenv('EMBEDDINGS_FILE_PATH')      # or .csv
LOCAL_FILE     = '/tmp/embeddings.csv'    # or '/tmp/embeddings.csv'
OUTPUT_PATH    = '/data/output.json'
# ------------------------------------------------------------------------------

logging.basicConfig(stream=sys.stdout, level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def download_embeddings():
    logger.info(f"Downloading embeddings from gs://{BUCKET_NAME}/{OBJECT_NAME}")
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    hook.download(bucket_name=BUCKET_NAME,
                  object_name=OBJECT_NAME,
                  filename=LOCAL_FILE)

def load_dataframe():
    if LOCAL_FILE.endswith('.parquet'):
        return pd.read_parquet(LOCAL_FILE)
    else:
        return pd.read_csv(LOCAL_FILE)

def prepare_embeddings(df):
    # Ensure list-like
    assert is_list_like(df.loc[0, 'resume_embeddings'])
    assert is_list_like(df.loc[0, 'job_embeddings'])

    # Convert to 2D arrays
    X = np.array([np.concatenate([r, j]) for r, j in zip(df['resume_embeddings'], df['job_embeddings'])])
    return X

def run_inference():
    # 1) Fetch embeddings file
    download_embeddings()

    # 2) Load DataFrame
    df = load_dataframe()

    # 3) Prepare arrays
    X = prepare_embeddings(df)

    # 4) Load model and predict
    logger.info("Loading model and running predictions")
    model = joblib_load(MODEL_PATH)
    # X = np.hstack([resume_arr, job_arr])
    preds = model.predict(X).tolist()

    # 5) Emit JSON
    output = []
    for _, row in df.iterrows():
        output.append({
            'job_id': row['job_id'],
            'resume_id': row['resume_id'],
            'prediction': preds[row.name]
        })
    with open(OUTPUT_PATH, 'w') as f:
        json.dump(output, f)
    hook = GCSHook(gcp_conn_id='google_cloud_default')
    hook.upload(
        bucket_name=BUCKET_NAME,
        object_name=os.path.join(os.path.dirname(OBJECT_NAME), "output.json"),
        filename='/data/output.json'
    )
    logger.info(f"Wrote inference results to {OUTPUT_PATH}")

if __name__ == '__main__':
    run_inference()
