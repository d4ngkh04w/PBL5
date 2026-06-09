<<<<<<< Updated upstream
# PBL5 - Phân loại rác thải

## 1. Kiến trúc tổng quan

```
ESP32-CAM
   ↓
Backend (FastAPI) ->  ┌ Model (YOLOv8)
                      └ Database (MySQL)
   ↑
Web dashboard
```

Luồng dữ liệu:

1. ESP32-CAM chụp ảnh và gửi đến Backend qua API.
2. Backend nhận ảnh, sử dụng YOLOv8 để phân loại loại rác.
3. Kết quả phân loại được lưu vào MySQL và trả về cho ESP32-CAM.
4. Web dashboard hiển thị kết quả phân loại và thống kê.
=======
# PBL5 - Phân loại rác thải

## 1. Kiến trúc tổng quan

```
ESP32-CAM
   ↓
Backend (FastAPI) ->  ┌ Model (YOLOv8)
                      └ Database (MySQL)
   ↑
Web dashboard
```

Luồng dữ liệu:

1. ESP32-CAM chụp ảnh và gửi đến Backend qua API.
2. Backend nhận ảnh, sử dụng YOLOv8 để phân loại loại rác.
3. Kết quả phân loại được lưu vào MySQL và trả về cho ESP32-CAM.
4. Web dashboard hiển thị kết quả phân loại và thống kê.

> Note:
>
> - Sử dụng websocket để cập nhật kết quả phân loại thời gian thực trên dashboard.


`venv310\Scripts\mineru -p BaoCao.docx -o TTNT -b pipeline`
>>>>>>> Stashed changes
