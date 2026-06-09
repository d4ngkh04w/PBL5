from datetime import datetime

class SystemState:
    def __init__(self):
        self.tray_position = 1
        self.target_tray = 1
        self.door_open = False
        # Ngăn 1: Nhựa, Ngăn 2: Giấy, Ngăn 3: Kim loại, Ngăn 4: Khác
        self.bin_weights = {
            1: 0.0,
            2: 0.0,
            3: 0.0,
            4: 0.0,
        }
        self.logs = [
            {"action": "Khởi động Server", "result": "Thành công", "time": self._now()},
        ]
        self.latest_ai = {
            "type": "Chưa có",
            "confidence": 0.0,
            "image": None
        }

    def _now(self):
        return datetime.now().strftime("%H:%M:%S")

    def add_log(self, action: str, result: str):
        self.logs.insert(0, {"action": action, "result": result, "time": self._now()})
        self.logs = self.logs[:8]

system_state = SystemState()
