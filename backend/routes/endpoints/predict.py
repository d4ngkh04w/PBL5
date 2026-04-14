import logging

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from routes.deps import validate_upload_file, verify_api_key
from database.session import get_db
from services.predict_service import predict_image, save_prediction_result

router = APIRouter()
logger = logging.getLogger("console")


@router.post("/predict")
async def predict(
    _: str = Depends(verify_api_key),
    image_bytes: bytes = Depends(validate_upload_file),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | float]:

    result = await run_in_threadpool(predict_image, image_bytes)
    logger.info(f"Prediction result: {result}")

    await save_prediction_result(db, result)

    return result
