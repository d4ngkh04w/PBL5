import logging

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from core.limiter import limiter
from utils.esp32 import notify_esp32
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
    weight: float = Form(...),
    image_bytes: bytes = Depends(validate_upload_file),
    db: AsyncSession = Depends(get_db),
):

    result = await run_in_threadpool(predict_image, image_bytes)

    await save_prediction_result(db, result)

    await run_in_threadpool(save_image, image_bytes, result.class_name)

    await run_in_threadpool(notify_esp32, group=result.group, weight=weight)

    result.weight = weight

    return result
