import os
import shutil
from collections import Counter

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import classification_report, confusion_matrix
from torchvision import datasets, models, transforms
from torch.utils.data import DataLoader
from tqdm.auto import tqdm

# ── Paths ─────────────────────────────────────────────────────────────────────
dataset_root = r"./dataset/output"
BEST_MODEL_PATH = "best.pt"
ERROR_DIR = "misclassified_images"  # Thư mục lưu ảnh đoán sai

# ── Config ────────────────────────────────────────────────────────────────────
IMGSZ = 384
BATCH = 32
RESNET_VARIANT = "resnet50"
RESNET_DROPOUT_CONFIG = {
    "resnet18": 0.25,
    "resnet34": 0.30,
    "resnet50": 0.35,
    "resnet101": 0.45,
    "resnet152": 0.50,
}
DROPOUT = RESNET_DROPOUT_CONFIG.get(RESNET_VARIANT, 0.3)
NUM_WORKERS = 0
DEVICE = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")

# ── Transform ─────────────────────────────────────────────────────────────────
eval_transform = transforms.Compose(
    [
        transforms.Resize(IMGSZ + 32),
        transforms.CenterCrop(IMGSZ),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ]
)


# ── Model ─────────────────────────────────────────────────────────────────────
def build_model(
    num_classes: int, dropout: float = 0.3, variant: str = "resnet101"
) -> nn.Module:
    builder_map = {
        "resnet18": models.resnet18,
        "resnet34": models.resnet34,
        "resnet50": models.resnet50,
        "resnet101": models.resnet101,
        "resnet152": models.resnet152,
    }
    assert variant in builder_map, f"Variant không hợp lệ: {variant}"
    model = builder_map[variant](weights=None)
    in_features = model.fc.in_features
    model.fc = nn.Sequential(
        nn.Dropout(p=dropout),
        nn.Linear(in_features, num_classes),
    )
    return model


# ── Inference ─────────────────────────────────────────────────────────────────
@torch.no_grad()
def predict_all(model, loader, device):
    model.eval()
    all_preds, all_labels = [], []

    pbar = tqdm(loader, total=len(loader), desc="🔍 Testing", dynamic_ncols=True)
    for imgs, labels in pbar:
        imgs = imgs.to(device)
        logits = model(imgs)
        preds = logits.argmax(1).cpu().tolist()
        all_preds.extend(preds)
        all_labels.extend(labels.tolist())

    return all_labels, all_preds


# ── Plots & Analysis ──────────────────────────────────────────────────────────
def plot_classification_report(y_true, y_pred, class_names):
    report_dict = classification_report(
        y_true,
        y_pred,
        target_names=class_names,
        output_dict=True,
        zero_division=0,
    )
    report_df = pd.DataFrame(report_dict).transpose()
    plot_df = report_df.drop(columns=["support"]).iloc[:-3, :]

    plt.figure(figsize=(10, 6))
    sns.heatmap(plot_df, annot=True, cmap="RdYlGn", fmt=".2f", cbar=True)
    plt.title(f"Classification Report — {RESNET_VARIANT}")
    plt.tight_layout()
    plt.savefig("classification.png", dpi=300, bbox_inches="tight")
    plt.show()
    print("✅ Saved: classification.png")


def plot_confusion_matrix(y_true, y_pred, class_names):
    cm = confusion_matrix(y_true, y_pred)
    plt.figure(figsize=(10, 8))
    sns.heatmap(
        cm,
        annot=True,
        fmt="d",
        cmap="Blues",
        xticklabels=class_names,
        yticklabels=class_names,
    )
    plt.xlabel("Dự đoán (Predicted)")
    plt.ylabel("Thực tế (Actual)")
    plt.title(f"Confusion Matrix — {RESNET_VARIANT}")
    plt.tight_layout()
    plt.savefig("confusion_matrix.png", dpi=300, bbox_inches="tight")
    plt.show()
    print("✅ Saved: confusion_matrix.png")


def analyze_misclassified(y_true, y_pred, dataset, class_names):
    """Phân tích, lưu CSV, lưu ảnh lưới và copy ảnh đoán sai ra thư mục riêng"""
    print("\n🔍 Đang xử lý các ảnh dự đoán sai...")

    errors = []
    # dataset.samples chứa danh sách tuples: (file_path, class_index)
    image_paths = [path for path, label in dataset.samples]

    for i in range(len(y_true)):
        if y_true[i] != y_pred[i]:
            errors.append(
                {
                    "image_path": image_paths[i],
                    "true_class": class_names[y_true[i]],
                    "pred_class": class_names[y_pred[i]],
                }
            )

    print(f"Tổng số ảnh đoán sai: {len(errors)} / {len(y_true)} ảnh.")

    if len(errors) == 0:
        print("Tuyệt vời! Không có ảnh nào đoán sai.")
        return

    num_to_plot = min(16, len(errors))
    cols = 4
    rows = (num_to_plot + cols - 1) // cols

    fig, axes = plt.subplots(rows, cols, figsize=(15, 4 * rows))
    axes = axes.flatten()

    for i in range(num_to_plot):
        err = errors[i]
        img = Image.open(err["image_path"])
        axes[i].imshow(img)
        axes[i].axis("off")
        # Tiêu đề đỏ nếu sai
        title = f"True: {err['true_class']}\nPred: {err['pred_class']}"
        axes[i].set_title(title, color="red", fontsize=12, fontweight="bold")

    # Tắt các ô thừa nếu có
    for j in range(num_to_plot, len(axes)):
        axes[j].axis("off")

    plt.tight_layout()
    plt.savefig("misclassified_grid_sample.png", dpi=300)
    print("✅ Saved sample grid: misclassified_grid_sample.png")

    # 4. Copy ảnh ra thư mục để duyệt bằng tay
    if os.path.exists(ERROR_DIR):
        shutil.rmtree(ERROR_DIR)  # Xóa thư mục cũ nếu chạy lại
    os.makedirs(ERROR_DIR, exist_ok=True)

    for err in tqdm(errors, desc="Copying error images", leave=False):
        src_path = err["image_path"]
        filename = os.path.basename(src_path)
        true_c = err["true_class"]
        pred_c = err["pred_class"]

        # Tạo thư mục theo True Class (Ví dụ: misclassified_images/True_Cardboard/)
        class_dir = os.path.join(ERROR_DIR, f"True_{true_c}")
        os.makedirs(class_dir, exist_ok=True)

        # Đổi tên ảnh để ghi rõ dự đoán thành gì
        new_filename = f"Pred_{pred_c}_{filename}"
        dst_path = os.path.join(class_dir, new_filename)

        shutil.copy(src_path, dst_path)

    print(f"✅ Đã copy toàn bộ {len(errors)} ảnh lỗi vào thư mục: '{ERROR_DIR}'")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # Dataset
    test_path = os.path.join(dataset_root, "test")
    assert os.path.exists(test_path), f"❌ Không tìm thấy: {test_path}"

    test_dataset = datasets.ImageFolder(test_path, transform=eval_transform)
    test_loader = DataLoader(
        test_dataset,
        batch_size=BATCH,
        shuffle=False,  # CHÚ Ý: Bắt buộc False để map được index ảnh
        num_workers=NUM_WORKERS,
        pin_memory=(DEVICE.type == "cuda"),
        persistent_workers=False if NUM_WORKERS == 0 else True,
    )

    class_names = test_dataset.classes
    num_classes = len(class_names)
    print(f"Classes ({num_classes}): {class_names}")
    print(f"Test size: {len(test_dataset)} ảnh")
    print(f"Device: {DEVICE} | Variant: {RESNET_VARIANT}")

    # Load model
    assert os.path.exists(BEST_MODEL_PATH), f"❌ Không tìm thấy: {BEST_MODEL_PATH}"

    model = build_model(num_classes, dropout=DROPOUT, variant=RESNET_VARIANT).to(DEVICE)
    state_dict = torch.load(BEST_MODEL_PATH, map_location=DEVICE, weights_only=False)
    model.load_state_dict(state_dict)
    print(f"✅ Loaded: {BEST_MODEL_PATH}")

    # Predict
    y_true, y_pred = predict_all(model, test_loader, DEVICE)

    # Prediction distribution
    pred_dist = Counter(class_names[p] for p in y_pred)
    print(f"\n📊 Prediction distribution:")
    for name in class_names:
        print(f"  {name:15s}: {pred_dist.get(name, 0):5d}")

    # Report
    print("\n📄 CLASSIFICATION REPORT:")
    print(
        classification_report(
            y_true,
            y_pred,
            target_names=class_names,
            zero_division=0,
        )
    )

    # Plots (Đã comment plt.show() để chạy trơn tru lưu ra file)
    plot_classification_report(y_true, y_pred, class_names)
    plot_confusion_matrix(y_true, y_pred, class_names)

    # ERROR ANALYSIS
    analyze_misclassified(y_true, y_pred, test_dataset, class_names)
