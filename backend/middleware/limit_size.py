import logging

from fastapi import Request
from fastapi.responses import JSONResponse

from core.config import ALLOW_FILE_SIZE

logger = logging.getLogger("request")


async def limit_body_size_middleware(request: Request, call_next):
    content_length = request.headers.get("content-length")

    if content_length is None:
        return JSONResponse(
            status_code=411, content={"error": "Content-Length header required"}
        )

    try:
        content_length = int(content_length)
    except ValueError:
        return JSONResponse(
            status_code=400, content={"error": "Invalid Content-Length"}
        )

    if content_length > ALLOW_FILE_SIZE:
        return JSONResponse(
            status_code=413,
            content={
                "error": {
                    "message": "Request too large",
                    "max_size": "{:.2f} MB".format(ALLOW_FILE_SIZE / (1024 * 1024)),
                }
            },
        )

    return await call_next(request)
