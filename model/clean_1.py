import os
from PIL import Image
import imagehash


def clean_dataset(input_path):
    valid_extensions = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
    stats = {
        "non_image": 0,
        "corrupt": 0,
        "duplicate": 0,
        "converted_rgb": 0,
        "renamed": 0,
    }

    seen_hashes = set()

    print("--- Đang bắt đầu làm sạch dataset ---")

    for root, _, files in os.walk(input_path):
        for file in files:
            file_path = os.path.join(root, file)
            base_name, ext = os.path.splitext(file)
            ext_lower = ext.lower()

            # 1. Xóa file không phải định dạng ảnh
            if ext_lower not in valid_extensions:
                try:
                    os.remove(file_path)
                    stats["non_image"] += 1
                    continue
                except:
                    continue

            try:
                # Mở ảnh bằng Pillow
                with Image.open(file_path) as img:
                    # Kiểm tra lỗi cấu trúc
                    img.verify()

                # Mở lại để xử lý nội dung
                with Image.open(file_path) as img:
                    img = img.convert("RGB")  # Chuẩn hóa để hash chính xác

                    # 2. Kiểm tra trùng lặp bằng Perceptual Hash (dhash)
                    # dhash hiệu quả với ảnh chụp, tránh bị lừa bởi metadata/format
                    f_hash = str(imagehash.dhash(img))

                    if f_hash in seen_hashes:
                        os.remove(file_path)
                        stats["duplicate"] += 1
                        continue
                    else:
                        seen_hashes.add(f_hash)

                    # 3. Chuyển đổi và lưu nếu không phải RGB
                    # (Lưu ý: Chỉ lưu lại nếu mode gốc không phải RGB để tránh ghi đè liên tục)
                    original_mode = Image.open(file_path).mode
                    if original_mode != "RGB":
                        img.save(file_path)
                        stats["converted_rgb"] += 1

            except Exception as e:
                try:
                    os.remove(file_path)
                    stats["corrupt"] += 1
                except:
                    pass
                continue

            # 4. Chuẩn hóa đuôi file
            if ext != ext_lower:
                new_path = os.path.join(root, base_name + ext_lower)
                try:
                    if not os.path.exists(new_path):
                        os.rename(file_path, new_path)
                        stats["renamed"] += 1
                    else:
                        os.remove(file_path)
                except:
                    pass

    print("-" * 40)
    print(f"KẾT QUẢ LÀM SẠCH VÀ CHUẨN HÓA:")
    print(f"  - Đã xóa {stats['non_image']} file không phải ảnh.")
    print(f"  - Đã xóa {stats['corrupt']} ảnh bị lỗi (corrupt).")
    print(f"  - Đã xóa {stats['duplicate']} ảnh trùng lặp hoàn toàn.")
    print(f"  - Đã chuyển {stats['converted_rgb']} ảnh sang hệ màu RGB chuẩn.")
    print(f"  - Đã chuẩn hóa đuôi {stats['renamed']} file ảnh.")
    print("-" * 40)


clean_dataset("./dataset/input")
