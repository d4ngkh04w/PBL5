import logging
import requests
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel

from core.config import ESP32_GROUP_CALLBACK_URL
from services.websocket_manager import manager
from services.system_state import system_state

router = APIRouter()
logger = logging.getLogger("console")

class RotateRequest(BaseModel):
    tray_id: int

class DoorRequest(BaseModel):
    action: str  # "open" or "close"

def get_base_url():
    if not ESP32_GROUP_CALLBACK_URL:
        return ""
    parsed = urlparse(ESP32_GROUP_CALLBACK_URL)
    return f"{parsed.scheme}://{parsed.netloc}"

@router.post("/rotate")
async def manual_rotate(req: RotateRequest):
    base_url = get_base_url()
    if not base_url:
        raise HTTPException(status_code=500, detail="ESP32 URL not configured")
    
    url = f"{base_url}/api/control/rotate"
    try:
        response = requests.get(url, params={"tray": req.tray_id}, timeout=10)
        response.raise_for_status()
        
        # Log and notify
        system_state.tray_position = req.tray_id
        system_state.target_tray = req.tray_id
        system_state.door_open = False
        system_state.add_log("Xoay mâm (Manual)", f"Thành công (Ngăn {req.tray_id})")
        
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
        
        return {"status": "success", "message": f"Rotated to tray {req.tray_id}"}
    except Exception as e:
        logger.exception("Failed to call ESP32 manual rotate")
        system_state.add_log("Xoay mâm (Manual)", f"Lỗi ESP32")
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
        raise HTTPException(status_code=500, detail="Failed to communicate with ESP32")

@router.post("/door")
async def manual_door(req: DoorRequest):
    base_url = get_base_url()
    if not base_url:
        raise HTTPException(status_code=500, detail="ESP32 URL not configured")
    
    if req.action not in ["open", "close"]:
        raise HTTPException(status_code=400, detail="Action must be 'open' or 'close'")

    url = f"{base_url}/api/control/door"
    try:
        response = requests.get(url, params={"action": req.action}, timeout=10)
        response.raise_for_status()
        
        # Log and notify
        is_open = req.action == "open"
        system_state.door_open = is_open
        action_vn = "Mở cửa" if is_open else "Đóng cửa"
        system_state.add_log(f"{action_vn} (Manual)", "Thành công")
        
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
        
        return {"status": "success", "message": f"Door {req.action} successful"}
    except Exception as e:
        logger.exception(f"Failed to call ESP32 manual door ({req.action})")
        action_vn = "Mở cửa" if req.action == "open" else "Đóng cửa"
        system_state.add_log(f"{action_vn} (Manual)", f"Lỗi ESP32")
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
        raise HTTPException(status_code=500, detail="Failed to communicate with ESP32")

