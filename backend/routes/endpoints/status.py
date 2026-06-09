from fastapi import APIRouter
from services.system_state import system_state

router = APIRouter()

@router.get("/status")
async def get_status():
    return {
        "trayPosition": system_state.tray_position,
        "targetTray": system_state.target_tray,
        "doorOpen": system_state.door_open,
        "binWeights": system_state.bin_weights,
        "logs": system_state.logs,
        "latestAi": system_state.latest_ai
    }
