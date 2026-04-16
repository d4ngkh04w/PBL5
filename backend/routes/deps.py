from fastapi import UploadFile

from core.config import (
    ALLOWED_CONTENT_TYPES,
    ALLOWED_EXTENSIONS,
    ALLOW_FILE_SIZE,
)
from exceptions.errors import (
    FileTooLarge,
    InvalidFileType,
    InvalidImage,
    UnsupportedMediaType,
)


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
    while True:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break

        total_size += len(chunk)
        if total_size > ALLOW_FILE_SIZE:
            raise FileTooLarge(ALLOW_FILE_SIZE)

        img_buffer.extend(chunk)

    if not img_buffer:
        raise InvalidImage()

    return bytes(img_buffer)
