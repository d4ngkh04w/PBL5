from fastapi import APIRouter, Depends

from .deps import verify_api_key
from .endpoints import health, predict, status, ws, control, statistics

router = APIRouter()

router.include_router(health.router, prefix="/api")
router.include_router(status.router, prefix="/api")
router.include_router(control.router, prefix="/api/control")
router.include_router(statistics.router, prefix="/api")
router.include_router(ws.router)
router.include_router(
    predict.router,
    prefix="/api",
    dependencies=[Depends(verify_api_key)],
)
