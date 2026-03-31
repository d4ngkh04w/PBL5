import io
import logging

from PIL import Image
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.model import class_names, model
from exceptions.errors import DatabaseError, ModelError
from repositories.prediction_repository import create_prediction_result

logger = logging.getLogger("prediction")


def predict_image(img: bytes) -> dict[str, str | float]:
    image = Image.open(io.BytesIO(img))

    results = model(image)

    if not results or not results[0].probs:
        raise ModelError()

    pred_class = results[0].probs.top1
    confidence = results[0].probs.top1conf

    logger.info(
        f"Predicted class: {class_names[pred_class]}, Confidence: {confidence:.4f}"
    )

    return {
        "class": class_names[pred_class],
        "confidence": float(confidence),
    }


async def save_prediction_result(
    db: AsyncSession,
    prediction: dict[str, str | float],
) -> None:
    try:
        await create_prediction_result(
            db=db,
            predicted_class=str(prediction["class"]),
            confidence=float(prediction["confidence"]),
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        raise DatabaseError(details=str(exc)) from exc
