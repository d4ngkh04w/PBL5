import os
import shutil
import time
from collections import Counter
from PIL import Image

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix
from tqdm.auto import tqdm
from ultralytics import YOLO

# ── Paths ─────────────────────────────────────────────────────────────────────
dataset_root = r"./dataset/output"
BEST_MODEL_PATH = "best.pt"
ERROR_DIR = "misclassified_images_yolo"  # Thư mục lưu ảnh đoán sai


# ── Plots & Analysis ──────────────────────────────────────────────────────────
def plot_classification_report(y_true, y_pred, class_names):
    report_dict = classification_report(
        y_true, y_pred, target_names=class_names, output_dict=True, zero_division=0
    )
    report_df = pd.DataFrame(report_dict).transpose()
    plot_df = report_df.drop(columns=["support"]).iloc[:-3, :]

    plt.figure(figsize=(10, 6))
    sns.heatmap(plot_df, annot=True, cmap="RdYlGn", fmt=".2f", cbar=True)
    plt.title("Classification Report Heatmap - YOLO")
    plt.savefig("classification_report_result_yolo.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("✅ Saved: classification_report_result_yolo.png")


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
    plt.title("Confusion Matrix - Trash Classification - YOLO")
    plt.savefig("confusion_matrix_result_yolo.png", dpi=300, bbox_inches="tight")
    plt.close()
    print("✅ Saved: confusion_matrix_result_yolo.png")


def analyze_misclassified(y_true, y_pred, image_paths, class_names):
    print("\n🔍 Đang xử lý các ảnh dự đoán sai...")
    errors = []

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
        title = f"True: {err['true_class']}\nPred: {err['pred_class']}"
        axes[i].set_title(title, color="red", fontsize=12, fontweight="bold")

    for j in range(num_to_plot, len(axes)):
        axes[j].axis("off")

    plt.tight_layout()
    plt.savefig("misclassified_grid_sample_yolo.png", dpi=300)
    plt.close()
    print("✅ Saved sample grid: misclassified_grid_sample_yolo.png")

    if os.path.exists(ERROR_DIR):
        shutil.rmtree(ERROR_DIR)
    os.makedirs(ERROR_DIR, exist_ok=True)

    for err in tqdm(errors, desc="Copying error images", leave=False):
        src_path = err["image_path"]
        filename = os.path.basename(src_path)
        true_c = err["true_class"]
        pred_c = err["pred_class"]

        class_dir = os.path.join(ERROR_DIR, f"True_{true_c}")
        os.makedirs(class_dir, exist_ok=True)

        new_filename = f"Pred_{pred_c}_{filename}"
        dst_path = os.path.join(class_dir, new_filename)

        shutil.copy(src_path, dst_path)

    print(f"✅ Đã copy toàn bộ {len(errors)} ảnh lỗi vào thư mục: '{ERROR_DIR}'")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    # 1. Load Model
    assert os.path.exists(BEST_MODEL_PATH), f"❌ Không tìm thấy: {BEST_MODEL_PATH}"
    model = YOLO(BEST_MODEL_PATH)

    # 2. Chuẩn bị dữ liệu test
    test_dir = os.path.join(dataset_root, "test")
    assert os.path.exists(test_dir), f"❌ Không tìm thấy: {test_dir}"

    class_names = sorted(os.listdir(test_dir))

    y_true = []
    y_pred = []
    image_paths = []

    print("🚀 Đang bắt đầu dự đoán trên tập Test...")
    start_time = time.perf_counter()

    for class_id, class_name in enumerate(
        tqdm(class_names, desc="Classes", position=0)
    ):
        class_path = os.path.join(test_dir, class_name)
        img_names = os.listdir(class_path)
        for img_name in tqdm(
            img_names, desc=f"Images in {class_name}", position=1, leave=False
        ):
            img_path = os.path.join(class_path, img_name)

            result = model(img_path, verbose=False)
            pred_class = result[0].probs.top1

            y_true.append(class_id)
            y_pred.append(pred_class)
            image_paths.append(img_path)

    print(f"⏱ Hoàn thành dự đoán trong {time.perf_counter() - start_time:.2f}s")

    # Prediction distribution
    pred_dist = Counter(class_names[p] for p in y_pred)
    print(f"\n📊 Prediction distribution:")
    for name in class_names:
        print(f"  {name:15s}: {pred_dist.get(name, 0):5d}")

    # 3. Report
    print("\n📄 CLASSIFICATION REPORT:")
    print(
        classification_report(y_true, y_pred, target_names=class_names, zero_division=0)
    )

    plot_classification_report(y_true, y_pred, class_names)
    plot_confusion_matrix(y_true, y_pred, class_names)
    analyze_misclassified(y_true, y_pred, image_paths, class_names)
