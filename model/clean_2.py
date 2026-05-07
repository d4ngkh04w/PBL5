import os
from cleanvision import Imagelab


def main():
    dataset_path = r"D:\WorkSpace\PBL5\model\dataset\input"

    print("--- 1. Đang khởi tạo và quét lỗi bằng Imagelab ---")
    imagelab = Imagelab(data_path=dataset_path)
    imagelab.find_issues()

    print("\n--- Báo cáo tổng quan ---")
    imagelab.report()

    # Lấy DataFrame kết quả
    df = imagelab.issues
    files_to_delete = set()

    # --- CHẾ ĐỘ 1: XÓA CÁC LỖI CHẤT LƯỢNG (Xóa sạch nếu là True) ---
    quality_issues = [
        "is_low_information_issue",
        "is_dark_issue",
        "is_light_issue",
        "is_blurry_issue",
        "is_odd_aspect_ratio_issue",
    ]

    for issue in quality_issues:
        if issue in df.columns:
            bad_paths = df[df[issue] == True].index.tolist()
            files_to_delete.update(bad_paths)
            print(f" > Phát hiện {len(bad_paths)} ảnh lỗi chất lượng ({issue})")

    # --- CHẾ ĐỘ 2: XỬ LÝ ẢNH TRÙNG LẶP GẦN GIỐNG (NEAR DUPLICATES) ---
    if "is_near_duplicates_issue" in df.columns:
        near_duplicate_sets = imagelab.info["near_duplicates"]["sets"]
        near_dupe_delete_count = 0
        for dupe_set in near_duplicate_sets:
            if len(dupe_set) > 1:
                # Giữ lại 1, xóa các bản sao còn lại
                to_remove = dupe_set[1:]
                files_to_delete.update(to_remove)
                near_dupe_delete_count += len(to_remove)
        print(
            f" > Phát hiện {len(near_duplicate_sets)} nhóm trùng gần giống. Sẽ xóa {near_dupe_delete_count} bản sao."
        )

    # --- CHẾ ĐỘ 3: XỬ LÝ ẢNH TRÙNG LẶP TUYỆT ĐỐI (EXACT DUPLICATES) ---
    if "is_exact_duplicates_issue" in df.columns:
        exact_duplicate_sets = imagelab.info["exact_duplicates"]["sets"]
        exact_dupe_delete_count = 0
        for dupe_set in exact_duplicate_sets:
            if len(dupe_set) > 1:
                # Giữ lại ảnh đầu tiên, đánh dấu các ảnh còn lại để xóa
                to_remove = dupe_set[1:]
                files_to_delete.update(to_remove)
                exact_dupe_delete_count += len(to_remove)
        print(
            f" > Phát hiện {len(exact_duplicate_sets)} nhóm trùng tuyệt đối. Sẽ xóa {exact_dupe_delete_count} bản sao."
        )

    # --- THỰC HIỆN XÓA VẬT LÝ ---
    print(f"\n--- 2. Đang thực hiện xóa file ---")
    final_delete_list = list(files_to_delete)
    actual_deleted = 0

    for path in final_delete_list:
        try:
            if os.path.exists(path):
                os.remove(path)
                actual_deleted += 1
        except Exception as e:
            print(f" ! Lỗi khi xóa {path}: {e}")

    print(f"\n=> HOÀN THÀNH: Đã dọn dẹp tổng cộng {actual_deleted} ảnh lỗi/trùng lặp.")


if __name__ == "__main__":
    main()
