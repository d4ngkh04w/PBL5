#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <AccelStepper.h>
#include <ESP32Servo.h>
#include <HX711.h>

// ========== CẤU HÌNH WIFI & BACKEND ==========
const char* WIFI_SSID = "Nguyen";
const char* WIFI_PASSWORD = "13456789";
const char* CAM_TRIGGER_ENDPOINT = "http://192.168.1.10:82/trigger/capture";

// ========== CẤU HÌNH PIN ==========
#define STEP_PIN        26    
#define DIR_PIN         27    
#define EN_PIN          25    
#define SERVO_PIN       21    
#define ULTRASONIC_TRIG 4     
#define ULTRASONIC_ECHO 5     
#define HX711_DT        13    
#define HX711_SCK       14    

// ========== THÔNG SỐ CƠ KHÍ ==========
#define CLOSE_ANGLE     90
#define OPEN_ANGLE      20 
#define TRIGGER_DIST    10.0    
#define CALIB_FACTOR    -411.11  
#define MEASUREMENT_DELAY 2000
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
  digitalWrite(ULTRASONIC_TRIG, LOW); delayMicroseconds(2);
  digitalWrite(ULTRASONIC_TRIG, HIGH); delayMicroseconds(10);
  digitalWrite(ULTRASONIC_TRIG, LOW);
  long duration = pulseIn(ULTRASONIC_ECHO, HIGH, 30000);
  return (duration == 0) ? -1 : (duration / 2.0) / 29.1;
}

float getWeight() {
  if (!scale.is_ready()) return 0.0;
  float weight = scale.get_units(10);
  return (weight < 0.5) ? 0.0 : weight;
}

void moveTrash(int groupId) {
  Serial.printf("[ACTION] Di chuyển đến ngăn %d\n", groupId);
  
  // Tọa độ các ngăn (điều chỉnh theo thực tế)
  long positions[] = {0, 400, 800, 1200, 1600}; 
  
  // 1. Kích hoạt Driver và di chuyển đến ngăn mục tiêu
  digitalWrite(EN_PIN, LOW); // Bật Driver (nếu dùng chế độ tiết kiệm điện)
  stepper.moveTo(positions[groupId]);
  
  unsigned long moveStart = millis();
  // Chạy motor cho đến khi tới đích hoặc quá 10 giây (timeout)
  while (stepper.distanceToGo() != 0 && millis() - moveStart < 10000) {
    stepper.run();
  }
  stepper.stop();
  delay(1000); // Đợi ổn định cơ cấu

  // 2. Mở nắp đổ rác (Servo)
  myServo.write(OPEN_ANGLE);  
  delay(2000);  
  myServo.write(CLOSE_ANGLE); 
  delay(1000);  
  
  Serial.println("[ACTION] Hoàn tất và giữ nguyên vị trí.");
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
    
    // Reset trạng thái sau khi xong
    waitingForClassification = false;
    currentState = IDLE;
  }
}

// ========== SETUP & LOOP ==========

void setup() {
  Serial.begin(115200);
  
  // Pins
  pinMode(ULTRASONIC_TRIG, OUTPUT);
  pinMode(ULTRASONIC_ECHO, INPUT);
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, HIGH); // Mặc định tắt driver

  // Stepper config
  stepper.setMaxSpeed(800.0);
  stepper.setAcceleration(500.0);
  
  // Servo config
  ESP32PWM::allocateTimer(0);
  myServo.setPeriodHertz(50);
  myServo.attach(SERVO_PIN, 500, 2400);
  myServo.write(CLOSE_ANGLE);
  
  // HX711 config
  scale.begin(HX711_DT, HX711_SCK);
  scale.set_scale(CALIB_FACTOR);
  scale.tare(20);

  // WiFi
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
  Serial.printf("\nIP: %s\n", WiFi.localIP().toString().c_str());

  // Server API
  server.on("/api/classify", HTTP_GET, handleClassificationResult);
  server.begin();
  
  Serial.println("✅ Hệ thống ESP32-S3 đã sẵn sàng");
}

void loop() {
  server.handleClient();

  // Kiểm tra Timeout AI
  if (waitingForClassification && millis() - detectionStartTime > CLASSIFICATION_TIMEOUT) {
    Serial.println("[TIMEOUT] Không nhận được phản hồi từ AI");
    waitingForClassification = false;
    currentState = IDLE;
  }

  // Luồng xử lý chính
  if (currentState == IDLE) {
    float dist = getDistance();
    if (dist > 0 && dist < TRIGGER_DIST) {
      Serial.printf("[DETECT] Vật thể tại %.1f cm. Đợi ổn định...\n", dist);
      detectionStartTime = millis();
      currentState = DETECTED;
    }
  }

  if (currentState == DETECTED) {
    if (millis() - detectionStartTime >= MEASUREMENT_DELAY) {
      currentWeight = getWeight();
      Serial.printf("[WEIGHT] Cân nặng: %.1f g\n", currentWeight);

      if (triggerCamera(currentWeight)) {
        currentState = WAITING_AI;
        waitingForClassification = true;
        detectionStartTime = millis(); // Reset để tính timeout cho AI
        Serial.println("[WAIT] Đang chờ kết quả từ AI...");
      } else {
        Serial.println("[ERR] Không thể gọi Camera");
        currentState = IDLE;
      }
    }
  }
  
  delay(50); 
}