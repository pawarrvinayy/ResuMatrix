import secrets
from pathlib import Path
from pydantic_settings import BaseSettings 

class Settings(BaseSettings):
    # model_config =SettingsConfigDict(
    #         # root of backend
    #         env_file="../.env",
    #         env_ignore_empty=True,
    #         extra="ignore"
    #         )
    API_V1_STR: str = "/api"
    SECRET_KEY:str = secrets.token_urlsafe(32)
    PROJECT_NAME: str = "ResuMatrix"
    
    HF_TOKEN: str
    GCP_BUCKET_NAME: str
    SUPABASE_URL: str
    SUPABASE_KEY: str
    
    # Gemini
    GEMINI_API_KEY: str
    GOOGLE_API_KEY: str
    OPENAI_API_KEY: str
    GROQ_API_KEY: str

    # Backend api base url
    RESUMATRIX_API_URL: str
    GCP_SECRET_JSON_PATH: str
    GCP_PROJECT_ID: str
    class Config:
        env_file = str(Path(__file__).resolve().parent.parent.parent / ".env")
        env_file_encoding = 'utf-8'

settings = Settings() 
