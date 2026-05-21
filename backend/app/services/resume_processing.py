import json
import asyncio
import logging
from typing import List
from fastapi import Depends
from app.services.database import DatabaseService
from app.services.google_genai import GoogleGenAIService
from app.services.pinecone import PineconeService
from app.services.ranking import ResumeRankingService
from app.models import Resume

logger = logging.getLogger('uvicorn.error')

RANKING_WEIGHTS = {
        'education': 0.2,
        'workexp': 0.6,
        'personal_projects': 0.15,
        'misc': 0.05
    }


class ResumeProcessingService:
    """Manages processing and ranking of resumes"""
    
    def __init__(self, 
                 pinecone_service: PineconeService = Depends(),
                 genai_service: GoogleGenAIService = Depends(),
                 ranking_service: ResumeRankingService = Depends(),
                 db_service: DatabaseService = Depends()):

        """
        Initialize the Resume Processing and Ranking service.
        This service accepts a set of resumes, extracts embeddings, 
        stores them in Pinecone and then calls the Ranker Service to finally rank them
        
        """
        self.pinecone_service = pinecone_service
        self.genai_service = genai_service
        self.ranking_service = ranking_service
        self.db_service = db_service
    

    async def run_ranking(self, job_id, job_text, resume_list: List[Resume]):
        try:
            resume_data = [{"candidate_id": resume.id, "resume_text": resume.resume_text} for resume in resume_list]
            processed_resumes = await self.genai_service.process_resumes(job_id, resume_data)
            resume_embs = await self.genai_service.fetch_resumes_embeddings(processed_resumes.structured_data, job_id)
            self.pinecone_service.upsert_embeddings(resume_embs)
            await asyncio.sleep(10)
            result = await self.ranking_service.weighted_borda_count(job_id, job_text, RANKING_WEIGHTS)
            logger.info(f"Rankings: {result['final_ranking']}")
            logger.info("Ranking complete!")

            rsm_to_update = []
            for i in range(len(result['final_ranking'])):
                resume_id = result['final_ranking'][i]
                scores_json = {
                        "education": result["individual_scores"]["education"][resume_id],
                        "workexp": result["individual_scores"]["workexp"][resume_id],
                        "personal_projects": result["individual_scores"]["personal_projects"][resume_id],
                        "misc": result["individual_scores"]["misc"][resume_id]
                        }
                rsm_to_update.append({"id": result['final_ranking'][i], "status": i+1, "section_scores": json.dumps(scores_json)})

            await self.db_service.update_resumes_with_job_id(job_id, rsm_to_update)
            await self.db_service.update_jobs([{"id": job_id, "status": 1}])

            return rsm_to_update
        except Exception as e:
            logger.warning(
                f"Gemini-based ranking skipped for job_id {job_id} "
                f"(likely billing/quota issue): {e}"
            )
            return []


