from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import verify_api_key, validate_file
from database.session import get_db
from services.predict_service import predict_image, save_prediction_result

router = APIRouter()


@router.post("/predict")
async def predict(
    _: str = Depends(verify_api_key),
    validated_file: UploadFile = Depends(validate_file),
    db: AsyncSession = Depends(get_db),
) -> dict[str, str | float]:

    img_bytes = await validated_file.read()

    result = predict_image(img_bytes)
    await save_prediction_result(db, result)

    return result
