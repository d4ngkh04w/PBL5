from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import CORS_ALLOW_ORIGINS
from router.api import router as api_router
from core.logger import setup_logger
from database.db import close_db, init_db
from exceptions.base import APIError
from middleware import logging, limit_size

setup_logger(debug=False)


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router)

app.middleware("http")(limit_size.limit_body_size_middleware)
app.middleware("http")(logging.logging_middleware)


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


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5762)
