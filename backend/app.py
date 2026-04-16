from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from core.config import CORS_ALLOW_ORIGINS
from core.limiter import limiter
from routes.api import router as api_router
from core.logger import get_logger_config
from database.db import close_db, init_db
from exceptions.base import APIError
from middleware import limit_size, verify_api_key


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


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


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(api_router)

app.middleware("http")(limit_size.limit_body_size_middleware)
app.middleware("http")(verify_api_key.verify_api_key_middleware)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5762, log_config=get_logger_config())
