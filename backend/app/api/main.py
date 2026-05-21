from fastapi import APIRouter

from app.api.routes import jobs, training

api_router = APIRouter()
api_router.include_router(jobs.router)
api_router.include_router(training.router)

