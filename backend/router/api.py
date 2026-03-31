from fastapi import APIRouter

from .endpoints import health, predict

router = APIRouter()

router.include_router(health.router, prefix="/api")
router.include_router(predict.router, prefix="/api")
