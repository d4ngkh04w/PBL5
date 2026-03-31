from flask import Flask, request, render_template, redirect
from PIL import Image
import base64
from ultralytics import YOLO

app = Flask(__name__)
model = YOLO("best.pt")

class_names = [
    "hazardous",
    "non_recyclable",
    "organic",
    "recycling",
]


@app.route("/predict", methods=["POST", "GET"])
def predict():
    if request.method == "GET":
        return redirect("/")
    file = request.files["image"]
    if not (file and file.filename):
        return render_template("index.html", error="No file uploaded")
    allowed_extensions = {"png", "jpg", "jpeg", "webp", "bmp", "tiff", "jfif"}
    if not file.filename.split(".")[-1].lower() in allowed_extensions:
        return render_template(
            "index.html",
            error=f"Invalid file type (allowed: {', '.join(allowed_extensions)})",
        )
    img_bytes = file.read()
    img = Image.open(file.stream)

    results = model(img)
    pred_class = results[0].probs.top1
    confidence = results[0].probs.top1conf

    return render_template(
        "index.html",
        klass=class_names[pred_class],
        confidence=float(confidence),
        image_data=base64.b64encode(img_bytes).decode("utf-8"),
    )


@app.route("/")
def home():
    return render_template("index.html")


app.run(host="0.0.0.0", port=8000)
