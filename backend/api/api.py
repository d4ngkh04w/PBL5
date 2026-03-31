from fastapi import APIRouter

from .endpoints import predict

api_router = APIRouter()

api_router.include_router(predict.router)
