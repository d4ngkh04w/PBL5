import datetime
import random
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PredictionResult
from core.model import CLASS_NAMES, MAPPED_CLASS_NAMES


async def create_prediction_result(
    db: AsyncSession,
    predicted_class: str,
    predicted_group: str,
    confidence: float,
) -> PredictionResult:
    prediction = PredictionResult(
        predicted_class=predicted_class,
        predicted_group=predicted_group,
        confidence=confidence,
    )

    db.add(prediction)
    await db.commit()

    return prediction


async def get_total_predictions(db: AsyncSession) -> int:
    stmt = select(func.count(PredictionResult.id))
    result = await db.execute(stmt)
    return result.scalar() or 0


async def get_predictions_by_group(db: AsyncSession) -> list[dict]:
    stmt = (
        select(
            PredictionResult.predicted_group,
            func.count(PredictionResult.id).label("count")
        )
        .group_by(PredictionResult.predicted_group)
    )
    result = await db.execute(stmt)
    db_map = {row[0]: row[1] for row in result.all() if row[0] is not None}
    
    groups = ["recycling", "hazardous", "organic", "non_recyclable"]
    return [{"group": g, "count": db_map.get(g, 0)} for g in groups]


async def get_predictions_by_class(db: AsyncSession) -> list[dict]:
    stmt = (
        select(
            PredictionResult.predicted_class,
            func.count(PredictionResult.id).label("count")
        )
        .group_by(PredictionResult.predicted_class)
    )
    result = await db.execute(stmt)
    db_map = {row[0]: row[1] for row in result.all() if row[0] is not None}
    
    return [{"class_name": c, "count": db_map.get(c, 0)} for c in CLASS_NAMES]


async def get_most_common_class(db: AsyncSession) -> dict:
    stmt = (
        select(
            PredictionResult.predicted_class,
            func.count(PredictionResult.id).label("count"),
            func.avg(PredictionResult.confidence).label("avg_confidence")
        )
        .group_by(PredictionResult.predicted_class)
        .order_by(func.count(PredictionResult.id).desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    row = result.first()
    if row:
        return {
            "class": row[0],
            "count": row[1],
            "avg_confidence": float(row[2])
        }
    return {
        "class": "none",
        "count": 0,
        "avg_confidence": 0.0
    }


async def get_predictions_hourly(db: AsyncSession) -> list[dict]:
    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(hours=24)
    
    stmt = (
        select(
            func.date_format(PredictionResult.created_at, "%Y-%m-%d %H").label("date_hour"),
            func.count(PredictionResult.id).label("count")
        )
        .where(PredictionResult.created_at >= start_time)
        .group_by("date_hour")
        .order_by("date_hour")
    )
    result = await db.execute(stmt)
    db_rows = result.all()
    db_map = {row[0]: row[1] for row in db_rows if row[0] is not None}
    
    hourly_data = []
    for i in range(23, -1, -1):
        dt = now - datetime.timedelta(hours=i)
        db_key = dt.strftime("%Y-%m-%d %H")
        label = dt.strftime("%H") + "h"
        hourly_data.append({
            "time": label,
            "count": db_map.get(db_key, 0)
        })
        
    return hourly_data


async def seed_mock_predictions(db: AsyncSession) -> int:
    now = datetime.datetime.now()
    inserted_count = 0
    total_to_seed = random.randint(50, 80)
    
    # Biased weights to make the charts look interesting
    weights = [5, 10, 15, 5, 5, 12, 18, 15, 25, 5]
    
    for _ in range(total_to_seed):
        random_minutes_ago = random.randint(0, 24 * 60)
        created_at = now - datetime.timedelta(minutes=random_minutes_ago)
        
        class_name = random.choices(
            CLASS_NAMES,
            weights=weights,
            k=1
        )[0]
        
        group = MAPPED_CLASS_NAMES.get(class_name, "non_recyclable")
        confidence = round(random.uniform(0.65, 0.98), 4)
        
        prediction = PredictionResult(
            predicted_class=class_name,
            predicted_group=group,
            confidence=confidence,
            created_at=created_at
        )
        db.add(prediction)
        inserted_count += 1

    await db.commit()
    return inserted_count

