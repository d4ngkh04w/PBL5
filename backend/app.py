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
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from typing import List

from core.logger import setup_logger
from exceptions.base import APIError
from middleware.logging import logging_middleware
from api.api import api_router

setup_logger(debug=False)


# --- QUẢN LÝ WEBSOCKET ---
class ConnectionManager:
    def __init__(self):
        # Danh sách các kết nối WebSocket đang hoạt động (Frontend React)
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        # Gửi dữ liệu tới tất cả trình duyệt đang mở Dashboard
        for connection in self.active_connections:
            await connection.send_json(message)


manager = ConnectionManager()
# --------------------------

app = FastAPI()
# Lưu manager vào app.state để các file router ở thư mục api/ có thể truy cập được
app.state.manager = manager

app.include_router(api_router, prefix="/api")
app.middleware("http")(logging_middleware)


# --- ROUTE WEBSOCKET ---
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Giữ kết nối mở, chờ nhận tin (nếu cần) hoặc chỉ để duy trì
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)


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

    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=5762,
        reload=True,
        reload_excludes=["logs/", "*.log"],
    )
