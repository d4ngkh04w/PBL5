import logging
import requests

from core.config import ESP32_GROUP_CALLBACK_URL

logger = logging.getLogger("console")


def notify_esp32(group: str, weight: float | None) -> None:
    if not ESP32_GROUP_CALLBACK_URL:
        logger.warning(
            "ESP32 callback URL is not configured; skipping control callback"
        )
        return

    mapping = {
        "hazardous": 1,
        "organic": 2,
        "recycling": 3,
        "non_recyclable": 4,
    }

    group_id = mapping.get(group, 0)

    params = {"group": str(group_id)}
    if weight is not None:
        params["weight"] = f"{weight:.2f}"

    try:
        response = requests.get(ESP32_GROUP_CALLBACK_URL, params=params, timeout=10)
        response.raise_for_status()
        logger.info("ESP32 callback sent: %s", response.url)
    except Exception:
        logger.exception("Failed to call ESP32 callback URL")
