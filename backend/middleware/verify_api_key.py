from fastapi import Request

from fastapi.responses import JSONResponse
from core.config import API_KEY

PUBLIC_PATHS = ["/api/health"]


async def verify_api_key_middleware(request: Request, call_next):
    if request.url.path in PUBLIC_PATHS:
        return await call_next(request)

    api_key = request.headers.get("x-api-key")

    if api_key != API_KEY:
        return JSONResponse(
            status_code=401, content={"error": "Unauthorized: Invalid API Key"}
        )

    return await call_next(request)
