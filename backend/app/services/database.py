from supabase import create_client, Client
from typing import Any, List, Optional, Dict
from app.core.config import settings
from app.models import *
import logging

logger = logging.getLogger('uvicorn.error')

class DatabaseService:
    def __init__(self, url: str, key:str):
        self.client: Client = create_client(url, key)
    
    # Job CRUD functions
    async def create_job(self, job_text: str, user_id: str) -> Optional[Job]:
        """Creates a new job posting in the database"""
        try:
            result = self.client.table("jobs").insert({
                "job_text": job_text,
                "status": 0,
                "user_id": user_id,
                }).execute()
            return Job.model_validate(result.data[0])
        except Exception as e:
            logger.error(f"Error creating job: {str(e)}")
            raise

    
    async def get_job(self, job_id: str) -> Optional[Job]:
        """Returns a job with the given job_id"""
        try:
            result = self.client.table("jobs").select("*").eq("id", job_id).execute()
            if not result.data:
                return None

            return Job.model_validate(result.data[0])
        except Exception as e:
            logger.error(f"Error fetching job: {str(e)}")
            raise


    async def get_jobs_by_user_id(self, user_id: str) -> Optional[List[Job]]:
        """Returns all jobs created by a user given their user_id""" 
        try:
            result = self.client.table("jobs").select("*").eq("user_id", user_id).execute()
            if not result.data:
                return None

            return JobList.model_validate({"job_list": result.data}).job_list
        except Exception as e:
            logger.error(f"Error fetching jobs for user {user_id}: {str(e)}")
            raise

    # Get all jobs for traininig
    async def get_all_jobs(self) -> Optional[List[Job]]:
        """Returns all jobs for data crunching"""
        try:
            result = self.client.table("jobs").select("*").execute()
            if not result.data:
                return None

            return JobList.model_validate({"job_list": result.data}).job_list
        except Exception as e:
            logger.error(f"Error fetching jobs: {str(e)}")
            raise
    
    async def update_jobs(self, jobs: List[Dict[str, Any]]) -> Optional[List[Job]]:
        """update jobs"""
        updated_jobs = []
        try:
            for job in jobs:
                result = self.client.table("jobs").update(job).eq("id", job["id"]).execute()
                updated_jobs.append(result.data[0])
            return JobList.model_validate({"job_list": updated_jobs}).job_list
        except Exception as e:
            logger.error(f"Error updating jobs: {str(e)}")
            raise

    # Resume CRUD functions
    async def create_resume(self, job_id: str, resume_text:str) -> Optional[Resume]:
        """Creates a new resume row in the database"""
        try:
            result = self.client.table("resumes").insert({
                "job_id": job_id,
                "resume_text": resume_text,
                "status": -2,
                "fit_probability": 0,
                }).execute()
            return Resume.model_validate(result.data[0])
        except Exception as e:
            logger.error(f"Error creating resume: {str(e)}")
            raise

    async def create_resumes(self, job_id: str, resume_text_list: List[str]) -> List[Resume]:
        """Creates multiple resumes given a job_id"""
        resume_list = [
                {
                    "job_id": job_id,
                    "resume_text": resume_text,
                    "status": -2,
                    "fit_probability": 0,
                    "feedback_label": 0,
                 } for resume_text in resume_text_list
            ]
        try:
            result = self.client.table("resumes").insert(resume_list).execute()
            return ResumeList.model_validate({"resume_list": result.data}).resume_list
        except Exception as e:
            logger.error(f"Error creating resumes for job_id {job_id}: {str(e)}")
            raise


    async def get_resume(self, resume_id: str) -> Optional[Resume]:
        """Returns a resume with the given resume_id"""
        try:
            result = self.client.table("resumes").select("*").eq("id", resume_id).execute()
            if not result.data:
                return None

            return Resume.model_validate(result.data[0])
        except Exception as e:
            logger.error(f"Error fetching resume with id {resume_id}: {str(e)}")
            raise


    async def get_resumes_with_job_id(self, job_id: str) -> Optional[List[Resume]]:
        """Returns all resumes with the given job_id"""
        try:
            result = self.client.table("resumes").select("*").eq("job_id", job_id).execute()
            if not result.data:
                return None

            return ResumeList.model_validate({"resume_list": result.data}).resume_list
        except Exception as e:
            logger.error(f"Error fetching resume withs job {job_id}: {str(e)}")
            raise


    async def get_all_resumes(self) -> Optional[List[Resume]]:
        """Returns all resumes for data crunching"""
        try:
            result = self.client.table("resumes").select("*").execute()
            if not result.data:
                return None

            return ResumeList.model_validate({"resume_list": result.data}).resume_list
        except Exception as e:
            logger.error(f"Error fetching resumes: {str(e)}")
            raise


    async def update_resumes_with_job_id(self, job_id: str, resumes: List[Dict[str, Any]]) -> Optional[List[Resume]]:
        """update the resumes based on job_id"""
        updated_res = []
        try:
            for resume in resumes:
                result = self.client.table("resumes").update(resume).eq("id", resume["id"]).execute()
                updated_res.append(result.data[0])
            return ResumeList.model_validate({"resume_list": updated_res}).resume_list
        except Exception as e:
            logger.error(f"Error updating resumes: {str(e)}")
            raise

    # TrainingData CRUD
    async def get_training_data(self) -> Optional[List[TrainingData]]:
        """Returns all TrainingData"""
        try:
            result = self.client.table("training_data").select("*").execute()
            if not result.data:
                return None

            return TrainingDataList.model_validate({"training_data_list": result.data}).training_data_list
        except Exception as e:
            logger.error(f"Error fetching training_data: {str(e)}")
            raise

