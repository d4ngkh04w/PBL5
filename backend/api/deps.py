from fastapi import File, Header, UploadFile

from core.config import ALLOWED_CONTENT_TYPES, ALLOWED_EXTENSIONS, ALLOW_FILE_SIZE, API_KEY
from exceptions.errors import FileTooLarge, InvalidFileType, Unauthorized, UnsupportedMediaType


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise Unauthorized("Invalid API key")

def validate_file(file: UploadFile = File(...)):
    if not (file and file.filename and file.size):
        raise ValueError("No file uploaded")
    
    if file.filename.split(".")[-1].lower() not in ALLOWED_EXTENSIONS:
        raise InvalidFileType()

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise UnsupportedMediaType()
    
    if file.size > ALLOW_FILE_SIZE:
        raise FileTooLarge(ALLOW_FILE_SIZE)

    return file