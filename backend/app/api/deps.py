from fastapi import Depends
from app.services.database import DatabaseService
from app.services.google_genai import GoogleGenAIService
from app.services.ranking import ResumeRankingService
from app.services.resume_processing import ResumeProcessingService
from app.services.storage import StorageService
from app.services.pinecone import PineconeService
from app import google_genai_service
from app.core.config import settings

def get_db_service() -> DatabaseService:
    """
    Inject DatabaseService dependency with Supabase settings

    """

    return DatabaseService(settings.SUPABASE_URL, settings.SUPABASE_API_KEY)

def get_storage_service() -> StorageService:
    """
    Inject StorageService dependency with GCP settings
    """

    return StorageService(settings.GCP_BUCKET_NAME)

def get_genai_service() -> GoogleGenAIService:
    """
    Inject GoogleGenAIService dependency with GCP settings
    """
    return google_genai_service

def get_pinecone_service() -> PineconeService:
    """
    Inject PineconeService dependency
    """
    return PineconeService(settings.PINECONE_API_KEY)

def get_resume_ranking_service(
        pinecone_service: PineconeService = Depends(get_pinecone_service),
        genai_service: GoogleGenAIService = Depends(get_genai_service)
        ) -> ResumeRankingService:
    """
    Inject ResumeRankingService dependency
    """
    return ResumeRankingService(pinecone_service, genai_service)

def get_resume_processing_service(
        pinecone_service: PineconeService = Depends(get_pinecone_service),
        genai_service: GoogleGenAIService = Depends(get_genai_service),
        ranking_service: ResumeRankingService = Depends(get_resume_ranking_service),
        db_service: DatabaseService = Depends(get_db_service)):
    """
    Inject ResumeProcessingService dependency
    """
    return ResumeProcessingService(pinecone_service, genai_service, ranking_service, db_service)
