from app.core.config import settings
from app.services.google_genai import GoogleGenAIService

# Single instance for semaphore and rate limiter
google_genai_service = GoogleGenAIService(settings.GOOGLE_API_KEY, 25)


