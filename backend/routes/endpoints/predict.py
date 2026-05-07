import logging
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import ESP32_GROUP_CALLBACK_URL
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


def _group_to_id(group_name: str) -> int:
    mapping = {
        "hazardous": 1,
        "organic": 2,
        "recycling": 3,
        "non_recyclable": 4,
    }
    return mapping.get(group_name, 4)


def _notify_esp32(group_id: int, weight: float | None) -> None:
    if not ESP32_GROUP_CALLBACK_URL:
        logger.warning(
            "ESP32 callback URL is not configured; skipping control callback"
        )
        return

    params = {"group": str(group_id)}
    if weight is not None:
        params["weight"] = f"{weight:.2f}"

    separator = "&" if "?" in ESP32_GROUP_CALLBACK_URL else "?"
    url = ESP32_GROUP_CALLBACK_URL + separator + urlencode(params)

    try:
        request = UrlRequest(url)
        with urlopen(request, timeout=10) as response:
            response.read()
        logger.info("ESP32 callback sent: %s", url)
    except Exception:
        logger.exception("Failed to call ESP32 callback URL")


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
    logger.info(f"Prediction result: {result}")

    await save_prediction_result(db, result)

    await run_in_threadpool(save_image, image_bytes, result.class_name)

    group_id = _group_to_id(result.group)
    await run_in_threadpool(_notify_esp32, group_id, weight)

    payload = {
        "type": "result",
        "class_name": result.class_name,
        "group": result.group,
        "group_id": group_id,
        "confidence": result.confidence,
        "weight": weight,
        "weight_unit": "g",
    }

    return payload
