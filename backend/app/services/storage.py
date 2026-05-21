import logging
import os
from typing import List
from fastapi import UploadFile
from google.cloud import storage
from app.models import Resume

logger = logging.getLogger(__name__)

BLOB_PREFIX = "resumes"

class StorageService:
    def __init__(self, bucket_name: str):
        self.client: storage.Client = storage.Client(project=os.environ.get("GCP_PROJECT_ID"))
        self.bucket = self.client.bucket(bucket_name)
        
    async def upload_resumes(self, job_id: str, files: List[UploadFile], resume_list: List[Resume]):
        public_urls = []
        for i in range(len(files)):
            await files[i].seek(0)
            contents = await files[i].read()
            blob = self.bucket.blob(f"{BLOB_PREFIX}/{job_id}/{resume_list[i].id}_{files[i].filename}")
            blob.upload_from_string(contents, content_type="application/pdf")
            logger.info(f"File {resume_list[i].id}_{files[i].filename} uploaded successfully, size: {len(contents)} bytes")
            public_urls.append(blob.public_url)
        return public_urls
