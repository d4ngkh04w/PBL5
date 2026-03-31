#include "esp_camera.h"
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"
#include "config.h"

WebServer server(STREAM_PORT);
unsigned long lastPredictTime = 0;
bool streamEnabled = true;

void predictAndSend();
void sendFrameToBackend(const uint8_t* frameBuf, size_t frameLen);
void handleStreamControl();

#define PWDN_GPIO_NUM     32
#define RESET_GPIO_NUM    -1
#define XCLK_GPIO_NUM      0
#define SIOD_GPIO_NUM     26
#define SIOC_GPIO_NUM     27
#define Y9_GPIO_NUM       35
#define Y8_GPIO_NUM       34
#define Y7_GPIO_NUM       39
#define Y6_GPIO_NUM       36
#define Y5_GPIO_NUM       21
#define Y4_GPIO_NUM       19
#define Y3_GPIO_NUM       18
#define Y2_GPIO_NUM        5
#define VSYNC_GPIO_NUM    25
#define HREF_GPIO_NUM     23
#define PCLK_GPIO_NUM     22

// --- MJPEG Stream Handler ---
void handleMjpegStream() {
  if (!streamEnabled) {
    server.send(503, "text/plain", "Stream is disabled");
    return;
  }

  server.setContentLength(CONTENT_LENGTH_UNKNOWN);
  server.sendHeader("Content-Type", "multipart/x-mixed-replace; boundary=jpgboundary");
  server.sendHeader("Connection", "keep-alive");
  server.sendHeader("Cache-Control", "no-cache");
  server.send(200);

  unsigned long lastFrameTime = millis();
  
  while (millis() - lastFrameTime < STREAM_TIMEOUT) {
    camera_fb_t* fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println(LOG_STREAM_CAPTURE_FAILED);
      delay(100);
      continue;
    }

    server.sendContent("--jpgboundary\r\nContent-Type: image/jpeg\r\n");
    server.sendContent("Content-Length: " + String(fb->len) + "\r\n\r\n");
    server.sendContent((const char*)fb->buf, fb->len);
    server.sendContent("\r\n");

    // Keep AI prediction alive even when stream handler is active.
    if (millis() - lastPredictTime >= PREDICT_INTERVAL) {
      lastPredictTime = millis();
      sendFrameToBackend(fb->buf, fb->len);
    }
    
    esp_camera_fb_return(fb);
    lastFrameTime = millis();
    delay(1000 / STREAM_FPS);
  }
}

void handleStreamControl() {
  if (!server.hasArg("enabled")) {
    server.send(400, "text/plain", "Missing query param: enabled=0|1");
    return;
  }

  const String enabled = server.arg("enabled");
  streamEnabled = (enabled == "1" || enabled == "true" || enabled == "on");

  server.send(200, "application/json", String("{\"stream_enabled\":") + (streamEnabled ? "true" : "false") + "}");
  Serial.println(streamEnabled ? "[STREAM] Enabled" : "[STREAM] Disabled");
}

void handleRoot() {
  server.sendHeader("Content-Type", "text/html");
  server.send(200, "text/plain", LOG_STREAM_INIT);
}

void setup() {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
  
  Serial.begin(115200);
  Serial.println("\n" + String(LOG_SYSTEM_START));

  // --- Camera Configuration ---
  camera_config_t config;
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = CAMERA_QUALITY;
  config.fb_count = CAMERA_FB_COUNT;

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf(LOG_CAMERA_INIT_FAILED, err);
    return;
  }

  // --- WiFi Connection ---
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.print(LOG_WIFI_CONNECTING);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\n" + String(LOG_WIFI_CONNECTED));
  Serial.print("IP: ");
  Serial.println(WiFi.localIP());

  // --- Start MJPEG Stream Server ---
  server.on("/", handleRoot);
  server.on("/stream", handleMjpegStream);
  server.on("/control/stream", handleStreamControl);
  server.begin();
  Serial.println(LOG_STREAM_STARTED);
}

void loop() {
  server.handleClient();
  if (millis() - lastPredictTime >= PREDICT_INTERVAL) {
    lastPredictTime = millis();
    predictAndSend();
  }
}

void predictAndSend() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(LOG_WIFI_LOST);
    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    return;
  }

  Serial.println(LOG_CAPTURE_START);
  
  camera_fb_t* fb = esp_camera_fb_get();
  if (!fb) {
    Serial.println(LOG_CAPTURE_FAILED);
    return;
  }

  sendFrameToBackend(fb->buf, fb->len);
  esp_camera_fb_return(fb);
}

void sendFrameToBackend(const uint8_t* frameBuf, size_t frameLen) {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println(LOG_WIFI_LOST);
    return;
  }

  Serial.println(LOG_SENDING);
  HTTPClient http;
  http.begin(API_URL);
  http.addHeader("x-api-key", API_KEY);
  http.addHeader("Content-Type", "image/jpeg");
  
  int httpResponseCode = http.POST((uint8_t*)frameBuf, frameLen);
  
  if (httpResponseCode > 0) {
    Serial.printf(LOG_SEND_SUCCESS, httpResponseCode);
  } else {
    Serial.printf(LOG_SEND_FAILED, http.errorToString(httpResponseCode).c_str());
  }
  
  http.end();
}