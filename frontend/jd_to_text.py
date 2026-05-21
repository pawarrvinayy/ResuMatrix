from groq import Groq
from pydantic import BaseModel, Field, ValidationError
from typing import List, Optional
# wrapper requirements
from functools import wraps
from typing import Callable, Any, Tuple
import os
import json
import streamlit as st
import re
from app.core.config import settings

client = Groq(api_key=settings.GROQ_API_KEY)

# Nested models and main model for JobPosting
class Qualifications(BaseModel):
    """Represents the qualifications required for the job."""
    education: str
    experience: str
    required_skills: List[str]
    nice_to_have_skills: Optional[List[str]] = None

class Compensation(BaseModel):
    """Represents the compensation details for the job."""
    base_salary: Optional[str]
    benefits: Optional[str]

class JobPosting(BaseModel):
    """Represents a job posting scraped or retrieved from a source."""
    job_title: str
    company_name: str
    location: Optional[str]
    posted_date: Optional[str] = None
    job_description: str
    responsibilities: List[str]
    qualifications: Qualifications
    compensation: Compensation   
    equal_opportunity_employer: Optional[str]

    class Config:
        str_strip_whitespace = True
        validate_by_name = True # Allows using snake_case or camelCase

def retry_decorator(max_attempts: int = 3):
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(resume_text: str, links_str: str = '') -> Tuple[dict, str]:
            valid_output = False
            for attempt in range(max_attempts):
                try:
                    llm_json = func(resume_text, links_str)
                    _ = JobPosting.model_validate_json(llm_json)
                    valid_output = True
                    break
                except (ValidationError, json.JSONDecodeError) as e:
                    print(f"Attempt {attempt+1} failed. Error: {e}")

            if valid_output:
                return llm_json
            else:
                return 'Could not parse job description accurately.'

        return wrapper

    return decorator

@retry_decorator(max_attempts=3)
def jobPosting_pre_processing_llm(jobPosting_text, user_customization:str = '') -> str:
    prompt = """Given the Job Posting text, create a structured JSON representation following these guidelines:

    # CRITICAL INSTRUCTION FOR 
    - Keep all your results very grounded and based on the given information provided.
    - Prioritize client requirements if they dont align with contradicting instructions.

    # INSTRUCTIONS FOR ADDING FURTHER DETAILS
    - If the job posting has explicit mention of the fields use them directly.
    - If the responsibilites are missing, generate a reasonable inference based on the overall requirements mentioned.
    - If the educational qualifications are missing, include education requirements witha requirement for a minimum degree in a relvant field e.g. 'Bachelors in Computer Science or Data Science' or 'Minimum Masters in Accounting' or if the requirements are complex research require a PhD.
    - If there are no work experience requirement, add a work experience requirement relevant years of experience e.g. '4+ years of Java Experience', 'At least 2 years of Healthcare Reporting', KEEP the numbers small.  
    - If there are NO explicit details mentioned in the job posting, infer and generate a list of approximately SEVEN (7) skills that are highly relevant to the job title, description, responsibilities, and qualifications mentioned. 
    - Base these inferences on common industry knowledge for the role.
    - Keep the job description less than 4 lines to summarize what the role entails.

    # Formatting Guidelines
    - Convert any gendered pronouns to gender-neutral alternatives.
    - Format dates in YYYY-MM-DD format when possible.

    The given job description is:

    {jobPosting_text}

    The following are the client requirements. If the client has any requirements that clash with the previous instructions, follow the client instruction.
    {user_customization}

    You MUST respond with a JSON object matching exactly this structure (no extra keys, no wrapping object):
    {{
        "job_title": "string",
        "company_name": "string",
        "location": "string or null",
        "posted_date": "YYYY-MM-DD or null",
        "job_description": "string",
        "responsibilities": ["string", ...],
        "qualifications": {{
            "education": "string",
            "experience": "string",
            "required_skills": ["string", ...],
            "nice_to_have_skills": ["string", ...] or null
        }},
        "compensation": {{
            "base_salary": "string or null",
            "benefits": "string or null"
        }},
        "equal_opportunity_employer": "string or null"
    }}
    """.format(jobPosting_text=jobPosting_text, user_customization=user_customization)
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content


def json_to_str(data:dict) -> str:
    converted_str = ''
    for i in data:
        value = data[i]
        val_type = type(value)
        if val_type==str or val_type == int:
            pass
        elif val_type==list:
            value = ','.join(value)
        elif val_type==dict:
            value = json_to_str(value)
        elif val_type is None:
            continue
        converted_str += f"{i} : {value} \n"
    return converted_str


def jobPosting_pre_processing(init_jobPosting, user_customization = ''):

    jobPosting_text = init_jobPosting[:]
    continue_preprocessing = True

    while continue_preprocessing:
        jobPosting_json = jobPosting_pre_processing_llm(jobPosting_text, user_customization)

        try:
            json_data = json.loads(jobPosting_json)
            jobPosting_text = json_to_str(json_data)
            continue_preprocessing = False
        except json.JSONDecodeError:
            jobPosting_text = "Error: Could not parse job description correctly."
            continue_preprocessing = False

    return jobPosting_json, jobPosting_text