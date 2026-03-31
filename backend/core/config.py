import os
import dotenv

dotenv.load_dotenv()

ALLOW_FILE_SIZE = int(os.getenv("ALLOW_FILE_SIZE", 5 * 1024 * 1024))
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "jfif"}
ALLOWED_CONTENT_TYPES = {
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/bmp",
    "image/tiff",
}

API_KEY = os.getenv("API_KEY", "default_api_key")
