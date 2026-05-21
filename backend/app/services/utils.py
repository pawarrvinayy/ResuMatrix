from functools import wraps
from typing import Callable, Optional, Union
from datetime import datetime
from pydantic import ValidationError, BaseModel
from app.core.config import settings
import logging
import asyncio
import json


MAX_ATTEMPTS = 3

logger = logging.getLogger(__name__)

class ResumeFormatter:
    """Class for formatting resume data into readable text."""

    
    @staticmethod
    def parse_date(date_str: Optional[str], default: str = "N/A") -> str:
        """Parse date string safely with error handling."""
        if not date_str:
            return default
        
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00')).strftime("%Y-%m")
        except (ValueError, AttributeError):
            return default

    
    @classmethod
    def format_work_experience(cls, work_experiences: list) -> str:
        """Format work experience entries into readable text."""
        if not work_experiences:

            return "No work experience listed"
        
        formatted = []
        for work in work_experiences:
            start_date = cls.parse_date(work.get('startDate'))
            end_date = cls.parse_date(work.get('endDate'), "Present")
            
            date_range = f"{start_date} - {end_date}".strip(" -")

            # Format responsibilities
            responsibilities = '\n\t'.join(work.get('summary', [])) if work.get('summary') else 'No responsibilities listed'
            
            # Format skills
            skills = ', '.join(work.get('skills', [])) if work.get('skills') else 'No skills listed'
            
            # Create formatted string
            entry = (
                f"{work.get('position', 'Unknown Position')} at {work.get('companyName', 'Unknown Company')}"
                + (f" ({date_range})" if date_range else "") + "\n"
                + f"Responsibilities:\n\t{responsibilities}\n"
                + f"Skills: {skills}"
            )
            formatted.append(entry)
        
        return '\n\n'.join(formatted)


    @classmethod
    def format_projects(cls, project_entries: list) -> str:
        """Format project entries into readable text."""
        if not project_entries:
            return "No projects listed."

        
        formatted = []
        for project in project_entries:

            start_date = cls.parse_date(project.get('startDate'))
            end_date = cls.parse_date(project.get('endDate'), "Present")
            
            date_range = f"{start_date} - {end_date}".strip(" -")


            # Format highlights
            highlights = '\n\t'.join(project.get('highlights', [])) if project.get('highlights') else "No highlights provided"

            # Format keywords
            keywords_list = project.get('keywords', [])
            keywords = ', '.join(keywords_list) if keywords_list else "No keywords provided"

            # Create formatted string
            entry = (
                f"Project: {project.get('projectName', 'Unnamed Project')}"

                + (f" ({date_range})" if date_range else "") + "\n"
                + f"Highlights:\n\t{highlights}\n"
                + f"Keywords: {keywords}\n"
                + f"{project.get('project_url', '')}"
            )

            formatted.append(entry)

        
        return '\n\n'.join(formatted)


    @staticmethod
    def format_award(awards: list) -> str:

        """Format award entries into readable text."""

        if not awards:
            return ""
            
        awards_list = []
        for award in awards:
            awards_list.append(
                f"Award: {award.get('title', '')}, "
                f"Date: {award.get('dateReceived', '')}, "

                f"Awarder: {award.get('awarder', '')}, "
                f"Summary: {award.get('summary', '')}"
            )
        return '\n'.join(awards_list)


    @staticmethod

    def format_certificate(certificates: list) -> str:
        """Format certificate entries into readable text."""
        if not certificates:
            return ""
            
        certificates_list = []

        for certificate in certificates:
            certificates_list.append(
                f"Certificate: {certificate.get('certificateName', '')}, "
                f"Date Issued: {certificate.get('dateIssued', '')}, "
                f"Issuer: {certificate.get('issuer', '')}"
            )
        return '\n'.join(certificates_list)


    @staticmethod
    def format_publication(publications: list) -> str:
        """Format publication entries into readable text."""
        if not publications:
            return ""
            
        publications_list = []
        for publication in publications:
            publications_list.append(
                f"Publication: {publication.get('publicationName', '')}, "
                f"Publisher: {publication.get('publisherName', '')}, "
                f"Release Date: {publication.get('releaseDate', '')}, "
                f"Summary: {publication.get('summary', '')}"
            )
        return '\n'.join(publications_list)

    @classmethod
    def format_resume(cls, resume_dict: dict) -> dict:
        """Format a resume dictionary into a structured format with formatted sections."""
        formatted_dict = {}
        
        # Add basics section if available
        if resume_dict.get('basics'):
            formatted_dict['basics'] = resume_dict['basics']
        
        # Format work experience
        if resume_dict.get('workexp'):
            formatted_dict['workexp'] = cls.format_work_experience(resume_dict['workexp'])
        
        # Format projects
        if resume_dict.get('personal_projects'):
            formatted_dict['personal_projects'] = cls.format_projects(resume_dict['personal_projects'])
        
        # Format education
        if resume_dict.get('education'):
            formatted_dict['education'] = ('\n'.join(resume_dict.get('education', [])))
        
        # Combine miscellaneous sections
        misc_sections = []
        
        if resume_dict.get('awards'):
            misc_sections.append(cls.format_award(resume_dict['awards']))
        
        if resume_dict.get('certificates'):
            misc_sections.append(cls.format_certificate(resume_dict['certificates']))
        
        if resume_dict.get('publications'):

            misc_sections.append(cls.format_publication(resume_dict['publications']))
        
        if resume_dict.get('skills'):
            misc_sections.append(f"Skills: {', '.join(resume_dict.get('skills', []))}")
        
        # Add misc section if not empty
        misc_content = '\n'.join(section for section in misc_sections if section)
        if misc_content:
            formatted_dict['misc'] = misc_content

        
        return formatted_dict


class ResumeExtractionBatch:
    """Container for resume extraction batch data and results."""
    
    def __init__(self, job_id, resume_data):
        """
        Initialize batch processing with database output format
        
        Args:
            job_id: The job ID this batch is associated with
            resume_data: A list of dictionaries with keys - candidate_id and resume_text
        """
        self.job_id = job_id
        self.candidate_data = {item["candidate_id"]: item["resume_text"] for item in resume_data}
        self.structured_data = {}
        self.errors = {}
        self.processing_time = {}
        self.start_time = datetime.now()
        
    def get_success_count(self):
        """Return the number of successfully processed resumes."""
        return len(self.structured_data)

        
    def get_error_count(self):
        """Return the number of failed resume extractions."""

        return len(self.errors)
        
    def get_total_count(self):
        """Return the total number of resumes in the batch."""
        return len(self.candidate_data)
    
    def get_completion_percentage(self):
        """Return the percentage of completed resume processing."""
        if self.get_total_count() == 0:
            return 0
        return round((self.get_success_count() + self.get_error_count()) / self.get_total_count() * 100, 2)
    
    def record_processing_time(self, candidate_id, elapsed_time):
        """Record processing time for a candidate."""
        self.processing_time[candidate_id] = elapsed_time
    
    def get_average_processing_time(self):
        """Get average processing time per resume."""
        if not self.processing_time:
            return 0
        return sum(self.processing_time.values()) / len(self.processing_time)
    
    def get_total_elapsed_time(self):
        """Get total elapsed time since batch creation."""
        return (datetime.now() - self.start_time).total_seconds()
    
    def get_summary(self):
        """Get a summary of the batch processing results."""

        return {
            "job_id": self.job_id,
            "total_count": self.get_total_count(),
            "success_count": self.get_success_count(),
            "error_count": self.get_error_count(),
            "completion_percentage": self.get_completion_percentage(),
            "avg_processing_time": self.get_average_processing_time(),
            "total_elapsed_time": self.get_total_elapsed_time()
        }


class RetryManager:
    """Class for managing retry logic with validation."""
    
    @staticmethod
    def retry_decorator(pydantic_model: type[BaseModel], max_attempts: int = MAX_ATTEMPTS):
        """Decorator to retry LLM calls with validation against a Pydantic model."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            async def wrapper(self, resume_text: str, links_str: str = '', model: str = '') -> Union[dict, str]:
                valid_output = False
                last_llm_json = ""
                llm_json = ""
                
                for attempt in range(max_attempts):
                    try:
                        # Use fallback model on second attempt if no model specified
                        if not model:
                            current_model = settings.LLM_FALLBACK if attempt == 1 else settings.LLM_DEFAULT
                        else:

                            current_model = model
                        

                        # Get LLM response
                        llm_json = await func(self, resume_text, links_str, current_model)
                        last_llm_json = llm_json
                        
                        # Validate against the model
                        _ = pydantic_model.model_validate_json(llm_json)
                        valid_output = True
                        break
                        
                    except ValidationError as e:
                        # Log detailed error information
                        error_details = ValidationHelper.extract_validation_errors(e, llm_json)
                        logger.error(f"Attempt {attempt+1} failed. Issues: {error_details}")
                        
                        # Exponential backoff
                        wait = min(2 ** attempt, 60)
                        await asyncio.sleep(wait)
                    except Exception as e:
                        logger.error(f"Unexpected error on attempt {attempt+1}: {str(e)}")
                        wait = min(2 ** attempt, 60)
                        await asyncio.sleep(wait)
                
                if valid_output:
                    parsed_json = json.loads(last_llm_json)
                    return ResumeFormatter.format_resume(parsed_json)

                else:
                    return 'Could not parse resume accurately.'
                    
            return wrapper

        return decorator


class ValidationHelper:
    """Helper class for validation and error handling."""
    

    @staticmethod
    def extract_validation_errors(validation_error: ValidationError, json_str: str) -> str:
        """Extract and format validation errors for better diagnostics."""
        error_fields = []

        
        # Parse JSON to get actual values
        try:
            json_data = json.loads(json_str)

            for err in validation_error.errors():

                # Get the location path as a string (e.g., "workexp.0.startDate")
                field_path = '.'.join(str(loc) for loc in err['loc'])

                
                # Try to extract the actual value that caused the error
                field_value = None
                try:
                    # Navigate to the problematic field
                    current = json_data
                    for loc in err['loc']:
                        current = current[loc]
                    field_value = str(current)

                except (KeyError, IndexError, TypeError):
                    field_value = "N/A"
                    
                error_fields.append(f"{field_path}: {err['msg']} (value: '{field_value}')")
        except json.JSONDecodeError:

            # If JSON parsing fails, just use the basic error info
            for err in validation_error.errors():
                field_path = '.'.join(str(loc) for loc in err['loc'])

                error_fields.append(f"{field_path}: {err['msg']}")

                
        return ', '.join(error_fields)
