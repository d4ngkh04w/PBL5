import os

from ultralytics import YOLO

model_path = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "model", "best.pt")
)

if not os.path.exists(model_path):
    raise FileNotFoundError(f"Model file not found at {model_path}")

model = YOLO(model_path)

class_names = [
    "battery",
    "biological",
    "cardboard",
    "clothes",
    "e-waste",
    "glass",
    "metal",
    "paper",
    "plastic",
    "shoes",
]

mapped_class_names = {
    "battery": "hazardous",
    "biological": "organic",
    "cardboard": "recycling",
    "clothes": "non_recyclable",
    "e-waste": "hazardous",
    "glass": "recycling",
    "metal": "recycling",
    "paper": "recycling",
    "plastic": "recycling",
    "shoes": "non_recyclable",
}
