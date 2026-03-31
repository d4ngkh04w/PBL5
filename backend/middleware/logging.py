import logging
from fastapi import Request

logger = logging.getLogger(__name__)


async def logging_middleware(request: Request, call_next):
    method = request.method
    url = str(request.url)
    client = request.client.host if request.client else "unknown"
    status_code = 200
    try:
        response = await call_next(request)
        status_code = response.status_code
    except Exception as e:
        status_code = 500
        raise e
    finally:
        logger.info(f"{client} | {method} {url} | {status_code}")

    return response
