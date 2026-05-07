import os


def count_images_in_classes(dataset_path):
    # Các định dạng ảnh phổ biến
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")

    print(f"{'Class Name':<20} | {'Image Count':<12}")
    print("-" * 35)

    total_images = 0
    # Lấy danh sách các folder con
    classes = sorted(
        [
            d
            for d in os.listdir(dataset_path)
            if os.path.isdir(os.path.join(dataset_path, d))
        ]
    )

    for class_name in classes:
        class_dir = os.path.join(dataset_path, class_name)
        # Đếm số lượng tệp có đuôi là ảnh
        count = len(
            [f for f in os.listdir(class_dir) if f.lower().endswith(valid_extensions)]
        )

        print(f"{class_name:<20} | {count:<12}")
        total_images += count

    print("-" * 35)
    print(f"{'Total':<20} | {total_images:<12}")


dataset_path = "./dataset/output/train"

count_images_in_classes(dataset_path)
