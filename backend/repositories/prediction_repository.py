from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PredictionResult


async def create_prediction_result(
    db: AsyncSession,
    predicted_class: str,
    confidence: float,
) -> PredictionResult:
    prediction = PredictionResult(
        predicted_class=predicted_class,
        confidence=confidence,
    )

    db.add(prediction)
    await db.commit()

    return prediction
