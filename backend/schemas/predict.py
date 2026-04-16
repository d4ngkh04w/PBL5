from pydantic import BaseModel


class PredictionResponse(BaseModel):
    class_name: str
    group: str
    confidence: float
