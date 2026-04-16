from fastapi import APIRouter, Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: AsyncSession = Depends(get_db)) -> dict[str, str]:
    await db.execute(text("SELECT 1"))
    return {"status": "ok"}
