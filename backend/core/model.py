import os

from ultralytics import YOLO

model = YOLO(os.path.join(os.path.dirname(__file__), "..", "model", "best.pt"))

class_names = [
    "hazardous",
    "non_recyclable",
    "organic",
    "recycling",
]
