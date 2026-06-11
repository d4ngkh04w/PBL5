from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.session import get_db
from schemas.statistics import (
    StatisticsResponse,
    GroupStat,
    ClassStat,
    HourlyStat,
)
from repositories import prediction_repository

router = APIRouter()


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics(
    seed: bool = Query(False, description="Force seeding of mock data"),
    db: AsyncSession = Depends(get_db),
):
    # Check total predictions
    total_count = await prediction_repository.get_total_predictions(db)

    # If database is empty or seed is requested, perform seed
    if total_count == 0 or seed:
        await prediction_repository.seed_mock_predictions(db)
        total_count = await prediction_repository.get_total_predictions(db)

    # Fetch stats
    most_common = await prediction_repository.get_most_common_class(db)
    group_dist = await prediction_repository.get_predictions_by_group(db)
    class_dist = await prediction_repository.get_predictions_by_class(db)
    hourly_dist = await prediction_repository.get_predictions_hourly(db)

    return StatisticsResponse(
        total_count=total_count,
        most_common_class=most_common["class"],
        most_common_class_count=most_common["count"],
        most_common_class_confidence=most_common["avg_confidence"],
        group_distribution=[
            GroupStat(group=g["group"], count=g["count"]) for g in group_dist
        ],
        class_distribution=[
            ClassStat(class_name=c["class_name"], count=c["count"]) for c in class_dist
        ],
        hourly_distribution=[
            HourlyStat(time=h["time"], count=h["count"]) for h in hourly_dist
        ],
    )
