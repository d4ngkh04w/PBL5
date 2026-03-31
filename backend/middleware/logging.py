import logging

from fastapi import Request

logger = logging.getLogger("request")


async def logging_middleware(request: Request, call_next):
    method = request.method
    path = request.url.path
    if "health" in path:
        return await call_next(request)

    client = request.client.host if request.client else "unknown"
    status_code = 200
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception:
        status_code = 500
        raise
    finally:
        logger.info(f"{client} - {method} {path} - {status_code}")

    return response
