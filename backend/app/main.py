from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.api.main import api_router
import logging


LOG = logging.getLogger('uvicorn.error')

@asynccontextmanager
async def lifespan(app: FastAPI):
    # One time
    from app import google_genai_service
    google_genai_service.setup()

    yield
    
app = FastAPI(title="ResuMatrix", lifespan=lifespan)

app.add_middleware(
        CORSMiddleware, 
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"])

app.include_router(api_router, prefix=settings.API_V1_STR)

