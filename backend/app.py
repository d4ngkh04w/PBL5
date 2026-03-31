# from fastapi import FastAPI, File, UploadFile
# from fastapi.responses import JSONResponse
# from ultralytics import YOLO
# from PIL import Image, UnidentifiedImageError
# import io

# app = FastAPI()
# model = YOLO("model/best.pt")

# class_names = [
#     "hazardous",
#     "non_recyclable",
#     "organic",
#     "recycling",
# ]


# class APIError(Exception):
#     def __init__(self, message: str):
#         self.message = message


# @app.post("/api/predict")
# async def predict(file: UploadFile = File(...)):
#     # Validate file
#     if not file.size or file.size > 5 * 1024 * 1024:  # 5MB limit
#         raise APIError("File size exceeds limit of 5MB")

#     allowed_extensions = ["png", "jpg", "jpeg", "webp", "bmp", "tiff", "jfif"]
#     if (
#         not file.filename
#         or file.filename.split(".")[-1].lower() not in allowed_extensions
#     ):
#         raise APIError("Invalid file type")

#     if file.content_type not in [
#         "image/png",
#         "image/jpeg",
#         "image/webp",
#         "image/bmp",
#         "image/tiff",
#     ]:
#         raise APIError("Unsupported media type")

#     img_bytes = await file.read()
#     try:
#         img = Image.open(io.BytesIO(img_bytes))
#     except UnidentifiedImageError:
#         raise APIError("Invalid image file")

#     results = model(img)
#     if not results or not results[0].probs:
#         raise APIError("Model did not return classification result")
#     pred_class = results[0].probs.top1
#     confidence = results[0].probs.top1conf

#     return {"class": class_names[pred_class], "confidence": float(confidence)}


# @app.exception_handler(APIError)
# async def api_error_handler(request, exc):
#     return JSONResponse(status_code=400, content={"error": exc.message})


# if __name__ == "__main__":
#     import uvicorn

#     uvicorn.run("app:app", host="0.0.0.0", port=5762)
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from core.logger import setup_logger
from exceptions.base import APIError
from middleware.logging import logging_middleware
from api.api import api_router

setup_logger(debug=True)

app = FastAPI()
app.include_router(api_router, prefix="/api")

app.middleware("http")(logging_middleware)


@app.exception_handler(APIError)
async def app_exception_handler(request: Request, exc: APIError):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "message": exc.message,
                "code": exc.status_code,
                "details": exc.details,
            }
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app:app", host="0.0.0.0", port=5762)
