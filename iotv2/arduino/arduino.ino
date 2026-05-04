#include <AccelStepper.h>
#include <Servo.h>
#include <SoftwareSerial.h>

SoftwareSerial espSerial(A0, A1); 

#define EN_PIN    8
#define DIR_PIN   5
#define STEP_PIN  2
#define SERVO_PIN 11 

// --- PHẦN CHỈNH GÓC SERVO TẠI ĐÂY ---
#define CLOSE_ANGLE 40
#define OPEN_ANGLE  0
// ------------------------------------

AccelStepper stepper(1, STEP_PIN, DIR_PIN);
Servo myServo; 

void setup() {
  Serial.begin(9600);    
  espSerial.begin(9600); 
  
  pinMode(EN_PIN, OUTPUT);
  digitalWrite(EN_PIN, LOW); 
  
  // Ban đầu cho servo về vị trí đóng rồi ngắt luôn
  myServo.attach(SERVO_PIN);
  myServo.write(CLOSE_ANGLE);
  delay(1000); // Đợi 1 giây để chắc chắn servo đã về đúng vị trí
  myServo.detach();
  
  stepper.setMaxSpeed(150.0);      
  stepper.setAcceleration(80.0);  
  stepper.setCurrentPosition(0);
  
  Serial.println("He thong san sang!");
}

void loop() {
  if (espSerial.available() > 0) {
    char command = espSerial.read();
    while(espSerial.available() > 0) { espSerial.read(); }

    long targetPosition = -1; 
    if (command == '0') targetPosition = 0;   
    else if (command == '1') targetPosition = 50;  
    else if (command == '2') targetPosition = 100; 
    else if (command == '3') targetPosition = 150; 
    else if (command == '4') targetPosition = 200;

    if (targetPosition >= 0) {
      // 1. Quay đến ngăn rác
      stepper.moveTo(targetPosition);
      while (stepper.distanceToGo() != 0) {
        stepper.run();
      }

      // 2. Mở nắp
      Serial.println("Dang mo nap...");
      myServo.attach(SERVO_PIN); // Cấp lại xung điều khiển
      myServo.write(OPEN_ANGLE); 
      delay(1000);               // Đợi servo quay đến góc mở (tầm 1s là đủ)
      myServo.detach();          // Ngắt xung để servo nghỉ, không bị rè khi đang mở
      
      delay(2000);               // Giữ nắp mở trong 2 giây để bỏ rác
      
      // 3. Đóng nắp
      Serial.println("Dang dong nap...");
      myServo.attach(SERVO_PIN); // Cấp lại xung để đóng
      myServo.write(CLOSE_ANGLE); 
      delay(1000);               // Đợi servo quay về góc đóng
      myServo.detach();          // Ngắt xung để nắp không bị ép mạnh vào thành thùng
      
      Serial.print("Da xu ly xong ngan: "); Serial.println(command);
    }
  }
}