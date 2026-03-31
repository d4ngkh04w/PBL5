from fastapi import Header, UploadFile

from core.config import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    ALLOW_FILE_SIZE,
    API_KEY,
)
from exceptions.errors import (
    FileTooLarge,
    InvalidFileType,
    InvalidImage,
    Unauthorized,
    UnsupportedMediaType,
)


def verify_api_key(x_api_key: str = Header(default="")) -> str:
    if x_api_key != API_KEY:
        raise Unauthorized("Invalid API key")
    return x_api_key


async def validate_upload_file(file: UploadFile) -> bytes:
    if not file or not file.filename:
        raise InvalidImage()

    filename_parts = file.filename.rsplit(".", maxsplit=1)
    if len(filename_parts) != 2 or filename_parts[1].lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileType()

    content_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaType()

    img_bytes = await file.read()
    if not img_bytes:
        raise InvalidImage()

    if len(img_bytes) > ALLOW_FILE_SIZE:
        raise FileTooLarge(ALLOW_FILE_SIZE)

    return img_bytes
