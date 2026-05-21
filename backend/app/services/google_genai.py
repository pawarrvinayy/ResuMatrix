import logging
import asyncio
from google import genai
from google.genai.types import EmbedContentConfig, EmbedContentResponse
from typing import Dict, List, Optional, Union
from asyncio import Semaphore
from aiolimiter import AsyncLimiter
from app.core.config import settings
from app.services.utils import ResumeExtractionBatch, RetryManager
from app.services.prompts import ResumePromptTemplates
from app.services.models import Resume

SECTION_NAMES = ["education", "workexp", "personal_projects", "misc"]

MAX_ATTEMPTS = 3

logger = logging.getLogger('uvicorn.error')

class GoogleGenAIService:
    """Manages interactions with Google's GenAI services."""
    
    def __init__(self, gemini_key: str, rate_limit_per_min: int = 100): 

        """
        Initialize the GenAI client 
        Ensure gcloud auth is setup with all the necessary env 
        variables such as GOOGLE_CLOUD_PROJECT, credentials json
        """
        self.client = genai.Client(api_key=gemini_key)
        self.rate_limit_per_min = rate_limit_per_min
        self.embedding_model_name = "models/text-embedding-004"

        # These values are initialized only once during startup using the setup function
        self.semaphore: Optional[Semaphore] = None
        self.rate_limiter: Optional[AsyncLimiter] = None
        logger.info(f"Initialized GenAI client")

    def setup(self):
        """Setup semaphore and rate limiter"""
        concurrency_limit = max(1, min(int(self.rate_limit_per_min * 0.9 / 60), 20))
        self.semaphore = Semaphore(concurrency_limit)
        self.rate_limiter = AsyncLimiter(self.rate_limit_per_min, 60)


    # Process batches for each section
    async def process_batch(self, inputs, metadata, section_name, batch_id, job_id):
        async with self.rate_limiter:
            async with self.semaphore:
                try:
                    logger.info(f"Processing {section_name} batch {batch_id} with {len(inputs)} inputs")
                    embedding_config = EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        output_dimensionality=768,
                        title=f"Resume: {section_name.capitalize()}"
                    )
                    response = await self.client.aio.models.embed_content(
                        model=self.embedding_model_name,
                        contents=inputs,
                        config=embedding_config)
                    
                    batch_results = []
                    for (resume_id, section), embedding_data in zip(metadata, response.embeddings):
                        embedding_id = '_'.join([job_id, str(resume_id), section])
                        embedding_dict = {
                            "id": embedding_id,
                            "values": embedding_data.values,
                            "metadata": {"job_id": job_id}
                        }

                        batch_results.append(embedding_dict)
                    
                    logger.info(f"Successfully processed {section_name} batch {batch_id}")
                    return batch_results, section_name
                except Exception as e:

                    logger.error(f"Error processing {section_name} batch {batch_id}: {str(e)}")
                    return [], section_name


    async def fetch_resumes_embeddings(
            self,
            resumes_dict: Dict[int, Dict[str, str]],
            job_id: str,
            batch_size: int = 10) -> Dict[str, List[Dict]]:
        """
        Fetches embeddings of multiple resumes, section-wise in batches with ratelimiting.

        Args:
            resumes_dict: Dictionary with resume ids as keys and dictionaries of resume sections
            job_id: Identifier for the current job
            batch_size: Maximum number of inputs per API call
        
        Returns:
            A dictionary mapping section names to lists of embedding dictionaries
        """
        section_queues = {name: [] for name in SECTION_NAMES}
        section_metadata = {name: [] for name in SECTION_NAMES}
        results = {name: [] for name in SECTION_NAMES}

        for resume_id, sections in resumes_dict.items():
            for section_name, section_text in sections.items():
                if section_name in section_queues:
                    section_queues[section_name].append(section_text)
                    section_metadata[section_name].append(resume_id)
        
        # Create tasks for processing each section in batches
        tasks = []

        token_limit = 19000
        
        for section_name in SECTION_NAMES:
            queue = section_queues[section_name]
            metadata = section_metadata[section_name]

            batch_count = 0
            
            for i in range(0,len(queue),batch_size):
                # Take a chunk of batch_size
                chunk_inputs = queue[i:i + batch_size]
                chunk_meta = [(metadata[j], section_name) for j in range(i, min(i + batch_size, len(metadata)))]
                
                # If adding this chunk would exceed the token limit, process current batch
                task = self.process_batch(chunk_inputs, chunk_meta, section_name, batch_count, job_id)
                tasks.append(task)
                batch_count += 1
        
        # Wait for all tasks to complete
        logger.info(f"Waiting for {len(tasks)} batches to complete")
        batch_results = await asyncio.gather(*tasks)
        
        # Combine results from all batches
        for batch_result, section_name in batch_results:
            results[section_name].extend(batch_result)

            logger.info(f"Added {len(batch_result)} results to {section_name}")
        
        return results
    

    async def fetch_job_text_embeddings(self, job_text: str, output_dim: int = 768) -> Optional[List[float]]:
        """
        Generate embedding vector for a job posting.
        
        Args:

            job_post_text: The text of the job posting
            output_dim: Dimensionality of output embeddings
        
        Returns:
            The embedding, List[float]
        """
        try:
            logger.info("Generating embedding for job posting")

            embedding_config = EmbedContentConfig(
                        task_type="RETRIEVAL_DOCUMENT",
                        output_dimensionality=output_dim,
                        title=f"Job Posting"
                    ) 

            response = await self.client.aio.models.embed_content(
                    model=self.embedding_model_name,
                    contents=job_text,
                    config=embedding_config)
            logger.info("Successfully generated job posting embedding")
            return response.embeddings[0].values if response.embeddings is not None else []
        except Exception as e:
            logger.error(f"Error generating job posting embedding: {str(e)}")
            raise


    @RetryManager.retry_decorator(pydantic_model=Resume, max_attempts=MAX_ATTEMPTS)
    async def generate_resume_json(self, resume_text: str, links_str: str = '', 
                                   model: str = settings.LLM_DEFAULT) -> str:
        """Generate structured JSON from resume text using LLM."""

        # Construct prompt
        prompt = ResumePromptTemplates.get_resume_prompt_template() + resume_text + links_str
        
        # Call LLM

        response = await self.client.aio.models.generate_content(
            model=model,
            contents=prompt,
            config={
                'response_mime_type': 'application/json',
                'response_schema': Resume,
                'temperature': settings.LLM_TEMPERATURE,
                'top_p': settings.LLM_TOP_P,
                'stop_sequences': settings.LLM_STOP_SEQUENCES
            }

        )
        return response.text 


    async def process_single_resume(self, candidate_id: Union[int, str], resume_text: str, 

                                   batch: ResumeExtractionBatch):
        """Process a single resume and handle errors."""
        try:
            result = await self.generate_resume_json(resume_text)
            
            if isinstance(result, dict):
                batch.structured_data[candidate_id] = result

            elif isinstance(result, str):
                batch.errors[candidate_id] = result
                logger.error(f'Failed to process candidate {candidate_id}')
                
            return candidate_id, result
            

        except Exception as e:
            error_msg = f"Error processing resume {candidate_id}: {str(e)}"
            logger.error(error_msg)
            batch.errors[candidate_id] = error_msg
            return candidate_id, None

    
    async def extract_resume_data(self, batch: ResumeExtractionBatch):
        """Extract structured data from resumes with LLM with concurrency control."""
        # Create a rate limiter and semaphore to control concurrency
        
        async def bounded_process(candidate_id, resume_text):
            """Process a resume with concurrency control."""
            async with self.rate_limiter, self.semaphore:
                return await self.process_single_resume(candidate_id, resume_text, batch)
        
        # Create tasks for all resumes
        tasks = [
            bounded_process(candidate_id, resume_text) 
            for candidate_id, resume_text in batch.candidate_data.items()
        ]
        
        # Run tasks concurrently with the semaphore limiting concurrency
        await asyncio.gather(*tasks)
        
        return batch


    async def retry_failed_extractions(self, batch: ResumeExtractionBatch):
        """Retry failed resume extractions individually."""
        if not batch.errors:
            return batch
            

        logger.info(f"Retrying {len(batch.errors)} failed extractions...")

        retry_success = []
        
        for candidate_id in list(batch.errors.keys()):

            logger.info(f"Retrying candidate {candidate_id}...")
            try:
                retry_result = await self.generate_resume_json(
                    batch.candidate_data[candidate_id])
                
                if isinstance(retry_result, dict):
                    batch.structured_data[candidate_id] = retry_result
                    retry_success.append(candidate_id)
                    logger.info(f"Retry successful for candidate {candidate_id}")
                else:
                    logger.error(f"Retry failed again for candidate {candidate_id}")
                    
            except Exception as e:
                logger.error(f"Error during retry for candidate {candidate_id}: {str(e)}")
        
        # Remove successful retries from errors
        for candidate_id in retry_success:
            batch.errors.pop(candidate_id)
            
        logger.info(f"Retry results: {len(retry_success)} succeeded, {len(batch.errors)} still failed")
        
        return batch
    

    async def process_resumes(self, job_id, resumes_data):

        """Process a batch of resumes with error handling and retries."""
        logger.info(f"Starting resume processing for job {job_id}")
        logger.info(f"Processing {len(resumes_data)} resumes")
        

        # Create batch from database output

        extraction_batch = ResumeExtractionBatch(job_id, resumes_data)
        
        # Process the batch
        processed_batch = await self.extract_resume_data(extraction_batch)
        
        # Add a cooldown period before retries
        logger.info("Waiting before retry attempts...")
        await asyncio.sleep(10)
        
        # Retry failed extractions
        if processed_batch.errors:

            processed_batch = await self.retry_failed_extractions(processed_batch)
        
        # Print summary
        logger.info(f"Processing complete. Success: {processed_batch.get_success_count()}, "

              f"Failed: {processed_batch.get_error_count()}, "
              f"Total: {processed_batch.get_total_count()}")
        logger.info(processed_batch.get_summary())

        return processed_batch

