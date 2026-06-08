import base64
import io

import cv2
import numpy as np
import torch
import torch.nn as nn
from flask import Flask, redirect, render_template, request
from PIL import Image
from torchvision import models, transforms

IMG_SIZE = 384

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

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "jfif"}

# ── Model ───────────────────────────────────────────────────────────────────
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")


def load_model(weights_path: str = "best.pt") -> nn.Module:
    model = models.resnet50(weights=None)
    model.fc = nn.Sequential(
        nn.Dropout(p=0.35),  # → fc.0
        nn.Linear(model.fc.in_features, 10),  # → fc.1.weight / fc.1.bias
    )
    state = torch.load(weights_path, map_location=device)
    # Support bare state-dict or checkpoint dict with key "model_state_dict"
    if isinstance(state, dict) and "model_state_dict" in state:
        state = state["model_state_dict"]
    model.load_state_dict(state)
    model.to(device)
    model.eval()
    return model


model = load_model("best.pt")

# ── Transforms ──────────────────────────────────────────────────────────────
infer_transform = transforms.Compose(
    [
        transforms.Resize((IMG_SIZE, IMG_SIZE)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
    ]
)

# ── Preprocessing ────────────────────────────────────────────────────────────


def preprocess_image(img_pil: Image.Image) -> Image.Image:
    img_np = np.array(img_pil)

    # DENOISE – ESP32-CAM có sensor noise cao, đặc biệt ở điều kiện ánh sáng yếu
    img_np = cv2.fastNlMeansDenoisingColored(
        img_np, None, h=6, hColor=6, templateWindowSize=7, searchWindowSize=21
    )

    # AUTO WHITE BALANCE (Gray World) – cân bằng màu bị lệch do đèn LED / môi trường
    img_float = img_np.astype(np.float32)
    mean_r = img_float[:, :, 0].mean()
    mean_g = img_float[:, :, 1].mean()
    mean_b = img_float[:, :, 2].mean()
    mean_gray = (mean_r + mean_g + mean_b) / 3
    img_float[:, :, 0] = np.clip(
        img_float[:, :, 0] * (mean_gray / (mean_r + 1e-6)), 0, 255
    )
    img_float[:, :, 1] = np.clip(
        img_float[:, :, 1] * (mean_gray / (mean_g + 1e-6)), 0, 255
    )
    img_float[:, :, 2] = np.clip(
        img_float[:, :, 2] * (mean_gray / (mean_b + 1e-6)), 0, 255
    )
    img_np = img_float.astype(np.uint8)

    # CLAHE – tăng độ tương phản cục bộ khi lighting không đều
    lab = cv2.cvtColor(img_np, cv2.COLOR_RGB2LAB)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    lab[:, :, 0] = clahe.apply(lab[:, :, 0])
    img_np = cv2.cvtColor(lab, cv2.COLOR_LAB2RGB)

    # UNSHARP MASK – ESP32-CAM thường cho ảnh hơi mờ (lens chất lượng thấp)
    gaussian = cv2.GaussianBlur(img_np, (0, 0), sigmaX=2.0)
    img_np = cv2.addWeighted(img_np, 1.5, gaussian, -0.5, 0)

    return Image.fromarray(img_np)


# ── Helpers ──────────────────────────────────────────────────────────────────


def pil_to_b64(img: Image.Image, fmt: str = "JPEG") -> str:
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def predict_from_pil(img_pil: Image.Image):
    """Return (class_index, confidence) for a PIL image."""
    tensor = infer_transform(img_pil).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
    pred_idx = int(probs.argmax())
    confidence = float(probs[pred_idx])
    return pred_idx, confidence


# ── Flask app ─────────────────────────────────────────────────────────────────
app = Flask(__name__)


@app.route("/predict", methods=["POST", "GET"])
def predict():
    if request.method == "GET":
        return redirect("/")

    file = request.files.get("image")
    if not (file and file.filename):
        return render_template("index.html", error="No file uploaded")

    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        return render_template(
            "index.html",
            error=f"Invalid file type (allowed: {', '.join(ALLOWED_EXTENSIONS)})",
        )

    img_bytes = file.read()
    img_original = Image.open(io.BytesIO(img_bytes)).convert("RGB")

    # Preprocess
    img_preprocessed = preprocess_image(img_original)

    # Inference on preprocessed image
    pred_idx, confidence = predict_from_pil(img_preprocessed)
    pred_class = class_names[pred_idx]
    bin_class = mapped_class_names[pred_class]

    # Encode both images for display
    original_b64 = pil_to_b64(img_original)
    preprocessed_b64 = pil_to_b64(img_preprocessed)

    return render_template(
        "index.html",
        klass=pred_class,
        bin=bin_class,
        confidence=confidence,
        original_image=original_b64,
        preprocessed_image=preprocessed_b64,
    )


@app.route("/")
def home():
    return render_template("index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
