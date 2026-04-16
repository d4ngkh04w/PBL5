import io
import logging

from PIL import Image, UnidentifiedImageError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from core.model import class_names, model, mapped_class_names
from core.config import CONF_THRESHOLD, MARGIN
from exceptions.errors import DatabaseError, InvalidImage, ModelError
from repositories.prediction_repository import create_prediction_result
from schemas.predict import PredictionResponse

logger = logging.getLogger("prediction")
console = logging.getLogger("console")


def predict_image(img: bytes) -> PredictionResponse:
    try:
        with Image.open(io.BytesIO(img)) as image:
            prepared_image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        console.warning("Invalid image payload: %s", exc)
        raise InvalidImage() from exc

    try:
        results = model(prepared_image, verbose=False)
    except Exception as exc:
        console.exception("Model inference failed")
        raise ModelError() from exc

    if not results or not results[0].probs:
        raise ModelError()

    probabilities = results[0].probs

    top5_indices = probabilities.top5
    top5_confs = probabilities.top5conf

    top1_idx = top5_indices[0]
    top2_idx = top5_indices[1] if len(top5_indices) > 1 else None

    conf_1 = float(top5_confs[0])
    conf_2 = float(top5_confs[1]) if top2_idx is not None else 0.0

    class_1 = class_names[top1_idx]
    class_2 = class_names[top2_idx] if top2_idx is not None else "none"

    logger.info("Top 1: %s (%.4f) | Top 2: %s (%.4f)", class_1, conf_1, class_2, conf_2)

    if conf_1 < CONF_THRESHOLD:
        predicted_class_name = "unknown"
        console.warning(
            "Model confidence %.4f is below threshold for class '%s'", conf_1, class_1
        )
    elif (conf_1 - conf_2) < MARGIN:
        predicted_class_name = "unknown"
        console.warning(
            "Model is uncertain between '%s' and '%s' (conf: %.4f vs %.4f)",
            class_1,
            class_2,
            conf_1,
            conf_2,
        )
    else:
        predicted_class_name = class_1

    predicted_class_group = mapped_class_names.get(
        predicted_class_name, "non_recyclable"
    )

    return PredictionResponse(
        class_name=predicted_class_name,
        group=predicted_class_group,
        confidence=conf_1,
    )


async def save_prediction_result(
    db: AsyncSession,
    prediction: PredictionResponse,
) -> None:
    try:
        await create_prediction_result(
            db=db,
            predicted_class=str(prediction.class_name),
            predicted_group=str(prediction.group),
            confidence=float(prediction.confidence),
        )
    except SQLAlchemyError as exc:
        await db.rollback()
        raise DatabaseError(details=str(exc)) from exc
