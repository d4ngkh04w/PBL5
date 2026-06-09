#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <AccelStepper.h>
#include <ESP32Servo.h>
#include <HX711.h>

// ========== CẤU HÌNH WIFI & BACKEND ==========
const char* WIFI_SSID     = "Nguyen";
const char* WIFI_PASSWORD = "13456789";
const char* CAM_TRIGGER_ENDPOINT = "http://192.168.1.25:82/trigger/capture";

// ========== CẤU HÌNH PIN ==========
#define STEP_PIN        26
#define DIR_PIN         27
#define EN_PIN          25
#define SERVO_PIN       21
#define ULTRASONIC_TRIG  4
#define ULTRASONIC_ECHO  5
#define HX711_DT        32
#define HX711_SCK       33

// ========== THÔNG SỐ CƠ KHÍ ==========
#define CLOSE_ANGLE           90
#define OPEN_ANGLE            20
#define TRIGGER_DIST          10.0
#define CALIB_FACTOR         -411.11
#define MEASUREMENT_DELAY    2000
#define CLASSIFICATION_TIMEOUT 60000

// ========== ĐỐI TƯỢNG & BIẾN TOÀN CỤC ==========
AccelStepper stepper(1, STEP_PIN, DIR_PIN);
Servo myServo;
HX711 scale;
WebServer server(80);

enum State { IDLE, DETECTED, WAITING_AI, PROCESSING };
State currentState = IDLE;

bool waitingForClassification = false;
float currentWeight = 0;
unsigned long detectionStartTime = 0;

// ========== CÁC HÀM ĐIỀU KHIỂN CƠ CẤU ==========

float getDistance() {
  digitalWrite(ULTRASONIC_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);
  long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000);
  return (duration == 0) ? -1 : (duration / 2.0) / 29.1;
}

float getWeight() {
  // --- Kiểm tra HX711 có sẵn sàng không ---
  if (!scale.is_ready()) {
    Serial.println("[SCALE] ⚠️  HX711 không sẵn sàng! Kiểm tra dây DT/SCK");
    return 0.0;
  }

  // --- Đọc các giá trị nội bộ để debug ---
  long rawValue  = scale.read_average(10);
  long offset    = (long)scale.get_offset();
  float scaleFactor = scale.get_scale();
  float weight   = scale.get_units(10);

  Serial.println("[SCALE DEBUG] ----------------------------------------");
  Serial.printf("  raw_avg       = %ld\n",   rawValue);
  Serial.printf("  offset (tare) = %ld\n",   offset);
  Serial.printf("  raw - offset  = %ld\n",   rawValue - offset);
  Serial.printf("  scale_factor  = %.4f\n",  scaleFactor);
  Serial.printf("  weight (calc) = %.2f g\n", weight);
  if (weight < 0.5 && weight > -0.5) {
    Serial.println("  → Sau ngưỡng 0.5g → trả về 0.0g");
  }
  Serial.println("[SCALE DEBUG] ----------------------------------------");

  return (weight < 0.5) ? 0.0 : weight;
}

void moveTrash(int groupId) {
  const char* groupNames[] = {"Không xác định", "Độc hại (Hazardous)", "Hữu cơ (Organic)", "Tái chế (Recycling)", "Khác/Không tái chế"};
  String name = (groupId >= 1 && groupId <= 4) ? groupNames[groupId] : groupNames[0];
  Serial.printf("[ACTION] Di chuyển đến ngăn %d (%s)\n", groupId, name.c_str());

  long positions[] = {0, 400, 800, 1200, 1600};

  digitalWrite(EN_PIN, LOW);  // LOW = bật driver (TB6600 của bạn)
  stepper.moveTo(positions[groupId]);

  unsigned long moveStart = millis();
  while (stepper.distanceToGo() != 0 && millis() - moveStart < 10000) {
    stepper.run();
    server.handleClient();
  }
  stepper.stop();
  delay(1000);

  myServo.write(OPEN_ANGLE);
  delay(2000);
  myServo.write(CLOSE_ANGLE);
  delay(1000);

  // LOW = giữ lực (driver vẫn bật)
  // KHÔNG đổi EN_PIN → giữ nguyên LOW
  Serial.println("[ACTION] Hoàn tất.");
}

// ========== CÁC HÀM XỬ LÝ MẠNG & AI ==========

bool triggerCamera(float weight) {
  if (WiFi.status() != WL_CONNECTED) return false;
  HTTPClient http;
  http.setTimeout(15000);
  String url = String(CAM_TRIGGER_ENDPOINT) + "?weight=" + String(weight, 1);
  http.begin(url);
  int httpCode = http.GET();
  http.end();
  return httpCode == 200;
}

void handleClassificationResult() {
  if (!waitingForClassification) {
    server.send(400, "text/plain", "No pending request");
    return;
  }

  int groupId = server.arg("group").toInt();
  server.send(200, "application/json", "{\"status\":\"received\"}");

  if (groupId >= 1 && groupId <= 4) {
    currentState = PROCESSING;
    moveTrash(groupId);

    waitingForClassification = false;
    currentState = IDLE;
  }
}

void handleRotate() {
  if (server.hasArg("tray")) {
    int trayId = server.arg("tray").toInt();
    if (trayId >= 1 && trayId <= 4) {
      server.send(200, "application/json", "{\"status\":\"success\", \"message\":\"Rotating tray\"}");
      Serial.printf("[MANUAL] Xoay mam toi ngan %d\n", trayId);
      
      // Đảm bảo cửa đóng an toàn trước khi xoay
      Serial.println("[MANUAL] Đóng cửa an toàn trước khi xoay");
      myServo.write(CLOSE_ANGLE);
      delay(1000); // Chờ servo đóng xong
      
      long positions[] = {0, 400, 800, 1200, 1600};
      digitalWrite(EN_PIN, LOW);
      stepper.moveTo(positions[trayId]);
      
      unsigned long moveStart = millis();
      while (stepper.distanceToGo() != 0 && millis() - moveStart < 10000) {
        stepper.run();
      }
      stepper.stop();
      return;
    }
  }
  server.send(400, "application/json", "{\"status\":\"error\", \"message\":\"Invalid tray\"}");
}

void handleDoor() {
  if (server.hasArg("action")) {
    String action = server.arg("action");
    if (action == "open") {
      server.send(200, "application/json", "{\"status\":\"success\", \"message\":\"Opening door\"}");
      Serial.println("[MANUAL] Mo cua");
      myServo.write(OPEN_ANGLE);
      return;
    } else if (action == "close") {
      server.send(200, "application/json", "{\"status\":\"success\", \"message\":\"Closing door\"}");
      Serial.println("[MANUAL] Dong cua");
      myServo.write(CLOSE_ANGLE);
      return;
    }
  }
  server.send(400, "application/json", "{\"status\":\"error\", \"message\":\"Invalid action\"}");
}

// ========== SETUP ==========

void setup() {
  Serial.begin(115200);
  delay(200); // Đợi Serial ổn định

  // --- Pins ---
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW);  // Bật driver → có lực giữ

  // --- Stepper ---
  stepper.setMaxSpeed(800.0);
  stepper.setAcceleration(500.0);

  // --- Servo ---
  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 500, 2400);
  myServo.write(CLOSE_ANGLE);

  // --- HX711 ---
  Serial.println("[SCALE] Đang khởi động HX711...");
  scale.begin(HX711_DT, HX711_SCK);
  delay(500); // Đợi HX711 ổn định

  if (scale.is_ready()) {
    // Đọc raw TRƯỚC khi tare để xác nhận có tín hiệu
    long rawBefore = scale.read_average(5);
    Serial.printf("[SCALE] Raw trước tare: %ld\n", rawBefore);

    scale.set_scale(CALIB_FACTOR);
    scale.tare(20);

    // Xác nhận sau tare
    long rawAfter = scale.read_average(5);
    long savedOffset = (long)scale.get_offset();
    Serial.printf("[SCALE] Raw sau tare:      %ld\n", rawAfter);
    Serial.printf("[SCALE] Offset đã lưu:     %ld\n", savedOffset);
    Serial.printf("[SCALE] CALIB_FACTOR:      %.4f\n", (float)CALIB_FACTOR);
    Serial.println("[SCALE] ✅ Tare hoàn tất");
  } else {
    Serial.println("[SCALE] ❌ HX711 KHÔNG phản hồi! Kiểm tra:");
    Serial.println("         - Dây DT  → GPIO 13");
    Serial.println("         - Dây SCK → GPIO 14");
    Serial.println("         - Nguồn 3.3V/5V cho HX711");
  }

  // --- WiFi ---
  Serial.print("[WIFI] Đang kết nối");
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.printf("\n[WIFI] ✅ Đã kết nối. IP: %s\n", WiFi.localIP().toString().c_str());

  // --- Web Server ---
  server.on("/api/classify", HTTP_GET, handleClassificationResult);
  server.on("/api/control/rotate", HTTP_GET, handleRotate);
  server.on("/api/control/door", HTTP_GET, handleDoor);
  server.begin();

  Serial.println("✅ Hệ thống ESP32 đã sẵn sàng");
}

// ========== LOOP ==========

void loop() {
  server.handleClient();

  // Kiểm tra timeout AI
  if (waitingForClassification && millis() - detectionStartTime > CLASSIFICATION_TIMEOUT) {
    Serial.println("[TIMEOUT] Không nhận được phản hồi từ AI. Reset về IDLE.");
    waitingForClassification = false;
    currentState = IDLE;
  }

  // Luồng xử lý chính
  if (currentState == IDLE) {
    float dist = getDistance();
    if (dist > 0 && dist < TRIGGER_DIST) {
      Serial.printf("[DETECT] Vật thể tại %.1f cm. Đợi ổn định %d ms...\n",
                    dist, MEASUREMENT_DELAY);
      detectionStartTime = millis();
      currentState = DETECTED;
    }
  }

  if (currentState == DETECTED) {
    if (millis() - detectionStartTime >= MEASUREMENT_DELAY) {
      Serial.println("[MEAS] Bắt đầu đo cân...");
      currentWeight = getWeight();
      Serial.printf("[WEIGHT] Kết quả cuối: %.1f g\n", currentWeight);

      if (triggerCamera(currentWeight)) {
        currentState = WAITING_AI;
        waitingForClassification = true;
        detectionStartTime = millis();
        Serial.println("[WAIT] Đã kích hoạt camera. Đang chờ kết quả AI...");
      } else {
        Serial.println("[ERR] Không thể gọi Camera. Reset về IDLE.");
        currentState = IDLE;
      }
    }
  }

  delay(50);
}
