from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from exceptions.base import APIError


def register_exception_handlers(app: FastAPI):
    @app.exception_handler(RateLimitExceeded)
    async def rate_limit_handler(request: Request, _: RateLimitExceeded):
        response = JSONResponse(
            status_code=429,
            content={"message": "Too many requests", "code": 429},
        )
        if hasattr(request.state, "view_rate_limit"):
            response = request.app.state.limiter._inject_headers(
                response, request.state.view_rate_limit
            )
        return response

    @app.exception_handler(APIError)
    async def app_exception_handler(_: Request, exc: APIError):
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "message": exc.message,
                "code": exc.status_code,
                "details": exc.details,
            },
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal Server Error",
                "code": 500,
                "details": str(exc),
            },
        )
