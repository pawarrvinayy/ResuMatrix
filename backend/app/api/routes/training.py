from fastapi import APIRouter, HTTPException, Depends 
from fastapi.responses import JSONResponse
from fastapi.encoders import jsonable_encoder
from app.services.database import DatabaseService
from app.api.deps import get_db_service
import logging

LOG = logging.getLogger('uvicorn.error')

router = APIRouter(prefix="/training", tags=["training", "train"])


@router.get("/data", status_code=200)
async def get_training_data(db_service: DatabaseService = Depends(get_db_service)):
    try:
        data = await db_service.get_training_data()
        if data is None:
            LOG.error(f"No training data found")
            raise HTTPException(status_code=404, detail=f"No training data found")
        else:
            return JSONResponse(content={"training_data": jsonable_encoder(data)})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

