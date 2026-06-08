import os
import torch
import torch.nn as nn
from torchvision import models

os.makedirs("model", exist_ok=True)

print("Creating dummy resnet50.pth...")
net = models.resnet50(weights=None)
net.fc = nn.Sequential(
    nn.Dropout(p=0.35),
    nn.Linear(net.fc.in_features, 10),
)
torch.save(net.state_dict(), "model/resnet50.pth")

print("Creating dummy yolov8.pt...")
# Ultralytics will automatically download yolov8n.pt if we try to initialize it
try:
    from ultralytics import YOLO
    model = YOLO("yolov8n.pt")  # this downloads to current dir or cache
    model.save("model/yolov8.pt")
except Exception as e:
    print(f"Could not create YOLOv8 model: {e}")
    # Just create a dummy file to bypass FileNotFoundError
    with open("model/yolov8.pt", "wb") as f:
        f.write(b"dummy")

print("Done!")
