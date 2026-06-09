import logging

from fastapi import APIRouter, Depends, Form, Request, Response, BackgroundTasks
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.ext.asyncio import AsyncSession

from core.limiter import limiter
from utils.esp32 import notify_esp32
from routes.deps import validate_upload_file
from database.session import get_db
from services.predict_service import (
    predict_image,
    save_prediction_result,
    save_image,
)
from services.websocket_manager import manager
from services.system_state import system_state

router = APIRouter()
logger = logging.getLogger("console")


@router.post("/predict")
@limiter.limit("20/minute")
async def predict(
    request: Request,
    response: Response,
    background_tasks: BackgroundTasks,
    weight: float = Form(...),
    image_bytes: bytes = Depends(validate_upload_file),
    db: AsyncSession = Depends(get_db),
):

    result = await run_in_threadpool(predict_image, image_bytes)

    await save_prediction_result(db, result)

    await run_in_threadpool(save_image, image_bytes, result.class_name)

    background_tasks.add_task(notify_esp32, group=result.group, weight=weight)

    result.weight = weight

    # Map group to bin index: recycling->1, organic->2, hazardous->3, non_recyclable->4
    group_to_bin = {
        "recycling": 1,
        "organic": 2,
        "hazardous": 3,
        "non_recyclable": 4,
    }
    bin_index = group_to_bin.get(result.group, 1)
    system_state.tray_position = bin_index
    system_state.target_tray = bin_index
    system_state.door_open = False
    system_state.bin_weights[bin_index] = round(
        system_state.bin_weights[bin_index] + weight, 2
    )
    system_state.latest_ai = {
        "type": result.class_name,
        "confidence": float(result.confidence),
        "image": None,
    }
    system_state.add_log("AI Nhận diện rác", result.class_name)
    
    # Broadcast SYSTEM_STATUS
    await manager.broadcast_json({
        "event": "SYSTEM_STATUS",
        "data": {
            "trayPosition": system_state.tray_position,
            "targetTray": system_state.target_tray,
            "doorOpen": system_state.door_open,
            "binWeights": system_state.bin_weights,
            "logs": system_state.logs,
            "latestAi": system_state.latest_ai
        }
    })

    await manager.broadcast_json({"event": "SYSTEM_LOG", "data": system_state.logs})

    await manager.broadcast_json(
        {
            "event": "NEW_TRASH_DETECTED",
            "data": {
                "class": result.group,
                "class_name": result.class_name,
                "group": result.group,
                "confidence": float(result.confidence),
                "weight": weight,
                "image": None,
            },
        }
    )

    return result

