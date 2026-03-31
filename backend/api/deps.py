from fastapi import Header

from core.config import API_KEY
from exceptions.errors import Unauthorized


def verify_api_key(x_api_key: str = Header(...)):
    if x_api_key != API_KEY:
        raise Unauthorized("Invalid API key")
