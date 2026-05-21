from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.services.database import DatabaseService
from app.api.deps import get_db_service
import logging

LOG = logging.getLogger('uvicorn.error')

router = APIRouter(prefix="/resumes", tags=["resumes"])

@router.get("/", status_code=200)
async def get_all_resumes(db_service: DatabaseService = Depends(get_db_service)):
    try:
        resumes  = await db_service.get_all_resumes()
        if resumes is None:
            LOG.error("No resumes found")
            raise HTTPException(status_code=404, detail="No resumes found")
        else:
            return JSONResponse(content={"resumes": jsonable_encoder(resumes)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

