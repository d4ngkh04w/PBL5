import io
import logging

from PIL import Image

from core.model import model, class_names
from exceptions.errors import ModelError

logger = logging.getLogger(__name__)


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
