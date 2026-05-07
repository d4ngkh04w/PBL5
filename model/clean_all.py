import os
import argparse
import uuid
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from cleanvision import Imagelab
from tqdm.auto import tqdm


def process_single_image(file_path):
    """Xử lý đơn lẻ 1 ảnh để dùng với đa luồng."""
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    root, file = os.path.split(file_path)
    base_name, ext = os.path.splitext(file)
    ext_lower = ext.lower()

    # 1. Xóa file không phải định dạng ảnh
    if ext_lower not in valid_extensions:
        try:
            os.remove(file_path)
            return "non_image"
        except:
            return "error"

    # 2. Xóa file lỗi cấu trúc và convert RGB
    try:
        # Mở ảnh kiểm tra bằng verify
        with Image.open(file_path) as img:
            img.verify()

        # Mở lại để xử lý nội dung RGB
        converted = False
        with Image.open(file_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
                img.save(file_path)
                converted = True
    except Exception:
        try:
            os.remove(file_path)
            return "corrupt"
        except:
            return "error"

    # 3. Chuẩn hóa đuôi file
    renamed = False
    if ext != ext_lower:
        new_path = os.path.join(root, base_name + ext_lower)
        try:
            if not os.path.exists(new_path):
                os.rename(file_path, new_path)
                renamed = True
            else:
                os.remove(file_path)
        except:
            pass

    return "converted" if converted else ("renamed" if renamed else "ok")


def step1_prepare_images(input_path):
    print("--- 1. Bắt đầu làm sạch định dạng và chuyển đổi RGB ---")

    tasks = []
    for root, _, files in os.walk(input_path):
        for file in files:
            tasks.append(os.path.join(root, file))

    stats = {
        "non_image": 0,
        "corrupt": 0,
        "converted_rgb": 0,
        "renamed": 0,
        "ok": 0,
        "error": 0,
    }

    with ThreadPoolExecutor(max_workers=(os.cpu_count() or 1) * 2) as executor:
        results = executor.map(process_single_image, tasks)

        for res in tqdm(results, total=len(tasks), desc="Chuẩn hóa & Chuyển RGB"):
            if res == "non_image":
                stats["non_image"] += 1
            elif res == "corrupt":
                stats["corrupt"] += 1
            elif res == "converted":
                stats["converted_rgb"] += 1
            elif res == "renamed":
                stats["renamed"] += 1
            elif res == "ok":
                stats["ok"] += 1

    print(f"KẾT QUẢ BƯỚC 1:")
    print(f"  - Đã xóa {stats['non_image']} file không phải ảnh.")
    print(f"  - Đã xóa {stats['corrupt']} ảnh bị lỗi (corrupt).")
    print(f"  - Đã chuyển {stats['converted_rgb']} ảnh sang chuẩn RGB.")
    print(f"  - Đã chuẩn hóa đuôi {stats['renamed']} file ảnh.\n")


def step2_scan_and_remove(dataset_path):
    print("--- 2. Quét lỗi chất lượng và trùng lặp bằng Imagelab ---")
    imagelab = Imagelab(data_path=dataset_path)
    imagelab.find_issues()

    print("\n--- Báo cáo tổng quan Imagelab ---")
    imagelab.report()

    df = imagelab.issues
    files_to_delete = set()

    # Nhóm lỗi chất lượng
    for issue in [
        "is_low_information_issue",
        "is_dark_issue",
        "is_light_issue",
        "is_blurry_issue",
        "is_odd_aspect_ratio_issue",
    ]:
        if issue in df.columns:
            paths = df[df[issue] == True].index.tolist()
            files_to_delete.update(paths)
            if paths:
                print(f" > Phát hiện {len(paths)} ảnh lỗi ({issue})")

    # Mảng thông tin trùng lặp (tránh KeyError)
    near_dups = imagelab.info.get("near_duplicates", {}).get("sets", [])
    exact_dups = imagelab.info.get("exact_duplicates", {}).get("sets", [])

    for dup_sets, name in [(near_dups, "gần giống"), (exact_dups, "tuyệt đối")]:
        count = 0
        for dupe_set in dup_sets:
            if len(dupe_set) > 1:
                files_to_delete.update(dupe_set[1:])
                count += len(dupe_set[1:])
        if count > 0:
            print(f" > Phát hiện trùng {name}. Sẽ xóa {count} bản sao.")

    print(f"\n--- 3. Thực hiện XÓA file lỗi và trùng lặp ---")
    actual_deleted = 0
    for path in tqdm(files_to_delete, desc="Xóa file lỗi/trùng lặp"):
        try:
            if os.path.exists(path):
                os.remove(path)
                actual_deleted += 1
        except Exception:
            pass

    print(
        f"=> HOÀN THÀNH: Đã dọn dẹp tổng cộng {actual_deleted} ảnh lỗi/trùng lặp bằng Imagelab."
    )


def step3_rename_files(dataset_path):
    print("\n--- 4. Thực hiện đổi tên file (Rename) ---")
    total_renamed = 0

    for class_name in os.listdir(dataset_path):
        class_dir = os.path.join(dataset_path, class_name)
        if not os.path.isdir(class_dir):
            continue

        valid_files = [
            f
            for f in sorted(os.listdir(class_dir))
            if os.path.isfile(os.path.join(class_dir, f))
        ]

        # Tránh lỗi WinError 183 do chia sẻ tên: Đổi tất cả sang tên tạm bằng UUID
        temp_files = []
        for file_name in tqdm(
            valid_files, desc=f"Tạo tên tạm ({class_name})", leave=False
        ):
            old_path = os.path.join(class_dir, file_name)
            ext = os.path.splitext(file_name)[1]
            temp_path = os.path.join(class_dir, f"temp_{uuid.uuid4().hex}{ext}")
            os.rename(old_path, temp_path)
            temp_files.append((temp_path, ext))

        # Đổi hàng loạt từ tên tạm sang tên chuẩn
        for index, (temp_path, ext) in tqdm(
            enumerate(temp_files, start=1),
            total=len(temp_files),
            desc=f"Đổi tên chuẩn ({class_name})",
            leave=False,
        ):
            new_path = os.path.join(class_dir, f"{class_name}_{index}{ext}")
            os.replace(temp_path, new_path)
            total_renamed += 1

    print(f"=> HOÀN THÀNH: Đã đổi tên chuẩn hóa cho {total_renamed} ảnh.\n")


def main():
    parser = argparse.ArgumentParser(description="Clean and rename dataset images.")
    parser.add_argument("--clean", action="store_true", help="Clean dataset")
    parser.add_argument(
        "--rename", action="store_true", help="Rename files in dataset "
    )
    args = parser.parse_args()

    dataset_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "dataset", "input")
    )
    if not os.path.exists(dataset_path):
        print(f"Không tìm thấy thư mục: {dataset_path}")
        return

    print(f"Bắt đầu quy trình tại thư mục: {dataset_path}\n")

    run_all = not args.clean and not args.rename

    if run_all or args.clean:
        step1_prepare_images(dataset_path)
        step2_scan_and_remove(dataset_path)

    if run_all or args.rename:
        step3_rename_files(dataset_path)


if __name__ == "__main__":
    main()
