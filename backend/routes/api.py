from fastapi import APIRouter, Depends

from .deps import verify_api_key
from .endpoints import health, predict

router = APIRouter()

router.include_router(health.router, prefix="/api")
router.include_router(
    predict.router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
)
