import os
import shutil
import time
import splitfolders
from ultralytics import YOLO
from sklearn.metrics import classification_report, confusion_matrix
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd


dataset_input = r"./dataset/input"
dataset_output = r"./dataset/output"


def clean_dataset(input_path):
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    count_deleted = 0
    count_renamed = 0

    for root, _, files in os.walk(input_path):
        for file in files:
            file_path = os.path.join(root, file)
            # Lấy phần tên và phần đuôi file
            base_name, ext = os.path.splitext(file)
            ext_lower = ext.lower()

            # 1. Kiểm tra nếu không phải file ảnh thì xóa
            if ext_lower not in valid_extensions:
                try:
                    os.remove(file_path)
                    count_deleted += 1
                except Exception as e:
                    print(f"Lỗi khi xóa {file}: {e}")

            # 2. Nếu là ảnh, chuẩn hóa đuôi file thành chữ thường
            else:
                if ext != ext_lower:
                    new_name = base_name + ext_lower
                    new_path = os.path.join(root, new_name)
                    try:
                        # Tránh lỗi nếu file mới đã tồn tại
                        if not os.path.exists(new_path):
                            os.rename(file_path, new_path)
                            count_renamed += 1
                        else:
                            os.remove(
                                file_path
                            )  # Xóa file cũ nếu trùng tên file đã lowercase
                    except Exception as e:
                        print(f"Lỗi khi đổi tên {file}: {e}")

    print(f"Đã xóa {count_deleted} file rác.")
    print(f"Đã chuẩn hóa đuôi {count_renamed} file ảnh.")


def format_duration(total_seconds: float) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


if __name__ == "__main__":
    clean_dataset(dataset_input)

    # Chia tập dữ liệu (75% Train, 15% Val, 10% Test)
    if os.path.exists(dataset_output):
        shutil.rmtree(dataset_output)

    splitfolders.ratio(
        dataset_input, output=dataset_output, seed=1303, ratio=(0.75, 0.15, 0.1)
    )

    # Khởi tạo Model và Huấn luyện
    model = YOLO("yolov8s-cls.pt")
    start_time = time.perf_counter()

    results = model.train(
        data=dataset_output,
        epochs=130,
        imgsz=320,
        batch=32,
        optimizer="AdamW",
        lr0=0.001,
        lrf=0.01,
        cos_lr=True,
        patience=15,
        dropout=0.1,
        fliplr=0.5,
        workers=8,
        project="trash_classification",
        name="optimized_yolov8_exp",
        cache=True,
        device=0,
        deterministic=True,
        pretrained=True,
    )

    val_results = model.val(data=dataset_output, split="val")

    test_results = model.val(data=dataset_output, split="test")

    best_model_path = os.path.join(
        "runs",
        "classify",
        "trash_classification",
        "optimized_yolov8_exp",
        "weights",
        "best.pt",
    )
    model = YOLO(best_model_path)

    test_dir = os.path.join(dataset_output, "test")
    class_names = sorted(os.listdir(test_dir))

    y_true = []
    y_pred = []

    for class_id, class_name in enumerate(class_names):
        class_path = os.path.join(test_dir, class_name)
        for img_name in os.listdir(class_path):
            img_path = os.path.join(class_path, img_name)

            result = model(img_path, verbose=False)
            pred_class = result[0].probs.top1

            y_true.append(class_id)
            y_pred.append(pred_class)

    print("\n📄 CLASSIFICATION REPORT:")
    report_str = classification_report(y_true, y_pred, target_names=class_names)
    print(report_str)

    # 2. Lưu Classification Report thành ảnh (dạng Heatmap)
    report_dict = classification_report(
        y_true, y_pred, target_names=class_names, output_dict=True
    )
    # Chuyển thành DataFrame và loại bỏ các dòng không cần thiết để vẽ biểu đồ đẹp hơn
    report_df = pd.DataFrame(report_dict).transpose()
    # Loại bỏ cột 'support' và dòng 'accuracy' để chỉ tập trung vào Precision, Recall, F1
    plot_df = report_df.drop(columns=["support"]).iloc[:-3, :]

    plt.figure(figsize=(10, 6))
    sns.heatmap(plot_df, annot=True, cmap="RdYlGn", fmt=".2f", cbar=True)
    plt.title("Classification Report Heatmap")
    plt.savefig(
        "classification_report_result.png", dpi=300, bbox_inches="tight"
    )  # Lưu ảnh chất lượng cao
    plt.show()

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
    plt.title("Confusion Matrix - Trash Classification")
    plt.savefig("confusion_matrix_result.png")
    plt.show()

    elapsed_time = time.perf_counter() - start_time
    print(f"⏱️ Tổng thời gian: {format_duration(elapsed_time)}")
