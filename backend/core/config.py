import os

import dotenv

dotenv.load_dotenv()


def _get_required_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"{name} environment variable is required")
    return value


def _get_cors_allow_origins() -> list[str]:
    origins = os.getenv("CORS_ALLOW_ORIGINS", "http://localhost:5173")
    return [origin.strip() for origin in origins.split(",") if origin.strip()]


# -- File Upload Configurations ---
ALLOW_FILE_SIZE = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "jfif"}
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/jfif",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

# -- API Configurations ---
API_KEY = _get_required_env("API_KEY")
DB_URL = os.getenv("DB_URL", "mysql+aiomysql://user:password@127.0.0.1:3306/dbname")
CORS_ALLOW_ORIGINS = _get_cors_allow_origins()

# -- Logging Configurations ---
DEBUG_MODE = False
LOG_DIR = "logs"
LOG_FORMAT = "[%(levelname)s] [%(asctime)s] - %(message)s"
DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# -- Model Configurations ---
CONF_THRESHOLD = 0.70  # Ngưỡng tin cậy tối thiểu
MARGIN = 0.15  # Khoảng cách giữa top 1 và top 2 để phân biệt rõ ràng
