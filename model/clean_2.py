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

    # --- CHẾ ĐỘ 2: XỬ LÝ ẢNH TRÙNG LẶP (GIỮ LẠI 1, XÓA CÁC BẢN SAO) ---
    if "is_near_duplicates_issue" in df.columns:
        # Lấy danh sách các nhóm ảnh trùng lặp từ Imagelab
        # Cleanvision lưu thông tin các cụm (clusters) ảnh giống nhau ở đây
        duplicate_sets = imagelab.info["near_duplicates"]["sets"]

        dupe_delete_count = 0
        for dupe_set in duplicate_sets:
            # dupe_set là một danh sách các đường dẫn ảnh giống nhau
            # Ví dụ: ['path/to/img1.jpg', 'path/to/img2.jpg']

            if len(dupe_set) > 1:
                # GIỮ LẠI ảnh đầu tiên (hoặc bạn có thể chọn ảnh có score cao nhất)
                # XÓA từ ảnh thứ 2 trở đi
                to_remove = dupe_set[1:]
                files_to_delete.update(to_remove)
                dupe_delete_count += len(to_remove)

        print(
            f" > Phát hiện {len(duplicate_sets)} nhóm trùng lặp. Sẽ xóa {dupe_delete_count} bản sao, giữ lại {len(duplicate_sets)} ảnh gốc."
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
