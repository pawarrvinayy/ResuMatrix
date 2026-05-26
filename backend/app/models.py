from typing import List
import uuid
from datetime import datetime
from pydantic import BaseModel


class Job(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    job_text: str
    status: int
    job_title: str | None = None

class JobList(BaseModel):
    job_list: List[Job]

class Resume(BaseModel):
    id: uuid.UUID
    job_id: uuid.UUID
    created_at: datetime
    resume_text: str
    status: int
    fit_probability: float
    feedback_label: int
    section_scores: str | None = None
    filename: str | None = None
    candidate_name: str | None = None
    reasoning: str | None = None
    summary: str | None = None
    missing_keywords: str | None = None

class ResumeList(BaseModel):
    resume_list: List[Resume]


class TrainingData(BaseModel):
    id:uuid.UUID
    resume_text: str
    job_description_text: str
    label: str
    created_at: datetime


class TrainingDataList(BaseModel):
    training_data_list: List[TrainingData]
