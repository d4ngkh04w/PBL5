from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.middleware import SlowAPIMiddleware

from core.config import CORS_ALLOW_ORIGINS
from core.limiter import limiter
from routes.api import router as api_router
from core.logger import get_logger_config
from database.db import close_db, init_db
from exceptions.handlers import register_exception_handlers
from middleware import limit_size


@asynccontextmanager
async def lifespan(_: FastAPI):
    await init_db()
    yield
    await close_db()


app = FastAPI(lifespan=lifespan)

register_exception_handlers(app)

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)


app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(api_router)

app.middleware("http")(limit_size.limit_body_size_middleware)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5762, log_config=get_logger_config())
