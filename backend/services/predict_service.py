import io
import logging

from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.model import class_names, model
from exceptions.errors import DatabaseError, InvalidImage, ModelError
from repositories.prediction_repository import create_prediction_result

logger = logging.getLogger("prediction")


def predict_image(img: bytes) -> dict[str, str | float]:
    try:
        with Image.open(io.BytesIO(img)) as image:
            prepared_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        logger.warning("Invalid image payload: %s", exc)
        raise InvalidImage() from exc

    try:
        results = model(prepared_image)
    except Exception as exc:
        logger.exception("Model inference failed")
        raise ModelError() from exc

    if not results or not results[0].probs:
        raise ModelError()

    prediction_result = results[0]
    probabilities = prediction_result.probs
    pred_class = probabilities.top1
    confidence = float(probabilities.top1conf)

    logger.info(
        "Predicted class: %s, Confidence: %.4f",
        class_names[pred_class],
        confidence,
    )

    return {
        "class": class_names[pred_class],
        "confidence": confidence,
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
