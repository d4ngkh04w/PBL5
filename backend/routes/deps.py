from typing import Optional

from fastapi import HTTPException, Security, UploadFile
from fastapi.security import APIKeyHeader

from core.config import (
    ALLOW_FILE_SIZE,
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    API_KEY,
)
from exceptions.errors import (
    FileTooLarge,
    InvalidFileType,
    InvalidImage,
    UnsupportedMediaType,
)

CHUNK_SIZE = 1024 * 1024

api_key_header = APIKeyHeader(name="x-api-key", auto_error=False)


async def verify_api_key(api_key: Optional[str] = Security(api_key_header)) -> str:
    if not api_key or api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key")

    return api_key


async def validate_upload_file(file: UploadFile) -> bytes:
    if not file or not file.filename:
        raise InvalidImage()

    filename_parts = file.filename.rsplit(".", maxsplit=1)
    if len(filename_parts) != 2 or filename_parts[1].lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileType()

    content_type = (file.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaType()

    total_size = 0
    img_buffer = bytearray()

    while chunk := await file.read(CHUNK_SIZE):
        total_size += len(chunk)
        if total_size > ALLOW_FILE_SIZE:
            raise FileTooLarge(ALLOW_FILE_SIZE)
        img_buffer.extend(chunk)

    if not img_buffer:
        raise InvalidImage()

    return bytes(img_buffer)
