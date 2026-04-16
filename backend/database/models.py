from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base


class PredictionResult(Base):
    __tablename__ = "prediction_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    predicted_class: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    predicted_group: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
