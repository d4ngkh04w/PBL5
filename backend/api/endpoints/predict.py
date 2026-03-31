from fastapi import APIRouter, Request, Depends
import logging
import base64

from services.predict_service import predict_image
from exceptions.errors import *
from core.config import ALLOW_FILE_SIZE
from api.deps import verify_api_key

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("")
async def predict(
    request: Request, _: str = Depends(verify_api_key)
) -> dict[str, str | float]:

    # Lấy raw bytes từ request body
    img_bytes = await request.body()

    if not img_bytes:
        raise ValueError("No image data received")

    logger.info(f"📸 Nhận ảnh từ ESP32: {len(img_bytes)} bytes")

    # Kiểm tra kích thước file
    if len(img_bytes) > ALLOW_FILE_SIZE:
        raise FileTooLarge(ALLOW_FILE_SIZE)

    result = predict_image(img_bytes)

    logger.info(f"✅ AI Prediction: {result}")

    # Encode ảnh thành base64 để gửi qua WebSocket
    img_base64 = base64.b64encode(img_bytes).decode("utf-8")

    # --- BẮN LÊN FRONTEND QUA WEBSOCKET ---
    manager = request.app.state.manager
    await manager.broadcast(
        {
            "event": "NEW_TRASH_DETECTED",
            "data": {**result, "image": f"data:image/jpeg;base64,{img_base64}"},
        }
    )
    logger.info(f"📡 Broadcast to {len(manager.active_connections)} frontend(s)")

    return result
