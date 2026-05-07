import io
import os
import uuid
import logging

from PIL import Image, UnidentifiedImageError, ImageOps
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
import numpy as np
import cv2

from core.model import class_names, model, mapped_class_names
from core.config import CONF_THRESHOLD, MARGIN, UPLOAD_DIR
from exceptions.errors import DatabaseError, InvalidImage, ModelError
from repositories.prediction_repository import create_prediction_result
from schemas.predict import PredictionResponse

logger = logging.getLogger("prediction")
console = logging.getLogger("console")


def preprocess_image(img_pil: Image.Image) -> Image.Image:
    img_np = np.array(img_pil)

    # DENOISE
    # ESP32-CAM có sensor noise cao, đặc biệt ở điều kiện ánh sáng yếu
    img_np = cv2.fastNlMeansDenoisingColored(
        img_np, None, h=6, hColor=6, templateWindowSize=7, searchWindowSize=21
    )

    # AUTO WHITE BALANCE (Gray World)
    # Cân bằng màu sắc bị lệch do đèn LED / ánh sáng môi trường
    img_float = img_np.astype(np.float32)
    mean_r, mean_g, mean_b = (
        img_float[:, :, 0].mean(),
        img_float[:, :, 1].mean(),
        img_float[:, :, 2].mean(),
    )
    mean_gray = (mean_r + mean_g + mean_b) / 3
    img_float[:, :, 0] = np.clip(
        img_float[:, :, 0] * (mean_gray / (mean_r + 1e-6)), 0, 255
    )
    img_float[:, :, 1] = np.clip(
        img_float[:, :, 1] * (mean_gray / (mean_g + 1e-6)), 0, 255
    )
    img_float[:, :, 2] = np.clip(
        img_float[:, :, 2] * (mean_gray / (mean_b + 1e-6)), 0, 255
    )
    img_np = img_float.astype(np.uint8)

    # CLAHE (Contrast enhancement)
    # Tăng độ tương phản cục bộ, hữu ích khi lighting không đều
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    img_np = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    # UNSHARP MASK (Sharpen)
    # ESP32-CAM thường cho ảnh hơi mờ (lens chất lượng thấp)
    gaussian = cv2.GaussianBlur(img_np, (0, 0), sigmaX=2.0)
    img_np = cv2.addWeighted(img_np, 1.5, gaussian, -0.5, 0)

    return Image.fromarray(img_np)


def predict_image(img: bytes) -> PredictionResponse:
    try:
        with Image.open(io.BytesIO(img)) as image:
            prepared_image = preprocess_image(
                ImageOps.exif_transpose(image).convert("RGB")
            )
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        console.warning("Invalid image payload: %s", exc)
        raise InvalidImage() from exc

    try:
        results = model(prepared_image, imgsz=384, verbose=False)
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


def save_image(img: bytes, class_name: str) -> None:
    try:
        class_dir = os.path.join(UPLOAD_DIR, class_name)
        os.makedirs(class_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.jpg"
        filepath = os.path.join(class_dir, filename)

        with Image.open(io.BytesIO(img)) as image:
            image.convert("RGB").save(filepath, format="JPEG")
    except Exception:
        console.exception("Failed to save image to disk")
