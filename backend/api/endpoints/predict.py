from fastapi import APIRouter, UploadFile, File, Depends

from services.predict_service import predict_image
from exceptions.errors import *
from core.config import ALLOWED_EXTENSIONS, ALLOWED_CONTENT_TYPES, ALLOW_FILE_SIZE
from api.deps import verify_api_key

router = APIRouter()


@router.post("/predict")
async def predict(
    file: UploadFile = File(...), _: str = Depends(verify_api_key)
) -> dict[str, str | float]:

    if not (file and file.filename):
        raise ValueError("No file uploaded")

    if file.filename.split(".")[-1].lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileType()

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaType()

    img_bytes = await file.read()

    if len(img_bytes) > ALLOW_FILE_SIZE:
        raise FileTooLarge(ALLOW_FILE_SIZE)

    result = predict_image(img_bytes)

    return result
