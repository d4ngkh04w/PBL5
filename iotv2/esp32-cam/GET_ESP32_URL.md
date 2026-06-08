**Hướng dẫn nhanh — Lấy URL stream của ESP32-CAM khi đổi WiFi**

Mục tiêu: biết được URL MJPEG stream của `ESP32-CAM` sau khi nó kết nối vào mạng Wi‑Fi mới (ví dụ khi dùng iPhone hotspot), rồi dán URL đó vào frontend.

Chuẩn bị:

- Laptop với cổng USB và 1 USB-to-Serial adapter (FTDI, CP2102, v.v.)
- Phần mềm Serial Monitor (Arduino IDE, PuTTY, hoặc `screen` trên Linux)
- Mã nguồn ESP32 trong `iotv2/esp32-cam` hoặc firmware đã nạp có in ra URL lên Serial
- Frontend trong repo: `frontend/.env`

Các bước (ngắn gọn):

1. Tháo ESP32-CAM khỏi mạch nếu cần để dễ kết nối.
2. Kết nối phần cứng Serial:
    - Adapter 5V/GND -> ESP GND và 5V (hoặc 3.3V nếu board yêu cầu). Chú ý điện áp.
    - Adapter TX -> ESP RX, Adapter RX -> ESP TX.
    - Kết nối GND chung.
3. Cắm adapter vào laptop.
4. Mở Serial Monitor (baud 115200) — cài đặt: `115200`, `No line ending` hoặc `Both NL & CR` tùy log của firmware.
    - Arduino IDE: Tools → Port → chọn port → Serial Monitor → chọn `115200`.
    - PuTTY: chọn Serial, port COMx, speed 115200.
5. Bật/khởi động lại ESP32 (nhấn RESET nếu cần). Quan sát log trên Serial.

Ghi chú về Wi‑Fi:

- Nếu firmware đã lưu SSID & password (ví dụ trong `config.h`), hãy bật hotspot (iPhone) hoặc mạng có SSID/password đó để ESP có thể kết nối.
- Nếu bạn cần thay SSID/password trong code: sửa `iotv2/esp32-cam/config.h` (các biến `WIFI_SSID`, `WIFI_PASSWORD`) rồi nạp lại firmware bằng Arduino IDE / PlatformIO.

Tìm URL trên Serial:

- Khi ESP kết nối thành công, firmware thường in ra địa chỉ IP và URL stream. Ví dụ log mẫu:

    Stream URL: http://192.168.1.6:81/stream
    Control URL: http://192.168.1.6:82/control/stream?enabled=1|0

- Trong Serial Monitor, tìm dòng chứa `Stream URL` hoặc `IP:`. Ghi lại URL đầy đủ (bao gồm port và path `/stream`).

Dán vào frontend:

- Mở file `frontend/.env` trong workspace.
- Cập nhật biến `VITE_STREAM_URL` và `VITE_ESP32_STREAM_CONTROL_URL` bằng URL bạn vừa lấy. Ví dụ:

    VITE_STREAM_URL=http://192.168.1.6:81/stream
    VITE_ESP32_STREAM_CONTROL_URL=http://192.168.1.6:82/control/stream

- Lưu file và khởi động lại frontend dev server nếu đang chạy (`npm run dev` trong `frontend`).

Kiểm tra trên máy client (laptop/phone):

- Mở `http://<VITE_STREAM_URL>` trong trình duyệt hoặc qua UI frontend.

Mẹo và lưu ý khi dùng iPhone hotspot:

- iPhone hotspot thường dùng subnet `172.20.10.x` — nếu firmware in IP, dùng IP đó.
- mDNS (`esp32cam.local`) có thể không hoạt động xuyên hotspot; nên dựa vào IP in ra serial.
- Nếu IP thay đổi khi tắt/mở hotspot, lặp các bước trên để lấy IP mới.

Nếu muốn tôi tự động hoá thêm (ví dụ: thêm mDNS code vào firmware, hoặc thêm một input trong UI frontend để thay URL runtime), nói tôi làm tiếp phần đó.

--
File này được tạo để giúp bạn nhanh lấy URL stream khi demo.
