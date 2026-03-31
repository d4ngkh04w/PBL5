import base64
import logging

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from router.deps import validate_upload_file, verify_api_key
from database.session import get_db
from services.predict_service import predict_image, save_prediction_result

router = APIRouter()
logger = logging.getLogger("console")


@router.post("/predict")
async def predict(
    request: Request,
    _: str = Depends(verify_api_key),
    image_bytes: bytes = Depends(validate_upload_file),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | float]:

    img_base64 = base64.b64encode(image_bytes).decode("utf-8")

    result = predict_image(image_bytes)
    logger.info(f"Prediction result: {result}")
    manager = request.app.state.manager

    await save_prediction_result(db, result)
    await manager.broadcast(
        {
            "event": "NEW_TRASH_DETECTED",
            "data": {**result, "image": f"data:image/jpeg;base64,{img_base64}"},
        }
    )

    return result
