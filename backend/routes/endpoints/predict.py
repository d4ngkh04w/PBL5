import logging

from fastapi import APIRouter, Depends, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from core.limiter import limiter
from routes.deps import validate_upload_file
from database.session import get_db
from services.predict_service import (
    predict_image,
    save_prediction_result,
    save_image,
)

router = APIRouter()
logger = logging.getLogger("console")


@router.post("/predict")
@limiter.limit("20/minute")
async def predict(
    request: Request,
    response: Response,
    image_bytes: bytes = Depends(validate_upload_file),
    db: AsyncSession = Depends(get_db),
):

    result = await run_in_threadpool(predict_image, image_bytes)
    logger.info(f"Prediction result: {result}")

    await save_prediction_result(db, result)

    await run_in_threadpool(save_image, image_bytes, result.class_name)

    return result
