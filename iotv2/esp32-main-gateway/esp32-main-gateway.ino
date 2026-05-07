#include <WiFi.h>
#include <WebServer.h>

const char* ssid = "Nguyen";
const char* password = "13456789";

WebServer server(80);

#define RXD2 16
#define TXD2 17

void handleRoot() {
  String html = "<html><head><meta charset='UTF-8'><style>";
  html += "button{width:100%;height:60px;margin:10px 0;font-size:25px;border-radius:10px;background:#4CAF50;color:white;}";
  html += "</style></head><body>";
  html += "<h1>Thùng Rác Thông Minh</h1>";
  html += "<button onclick=\"location.href='/cmd?v=1'\">Ngăn 1</button>";
  html += "<button onclick=\"location.href='/cmd?v=2'\">Ngăn 2</button>";
  html += "<button onclick=\"location.href='/cmd?v=3'\">Ngăn 3</button>";
  html += "<button onclick=\"location.href='/cmd?v=4'\">Ngăn 4</button>";
  html += "<button onclick=\"location.href='/cmd?v=0'\" style='background:#f44336'>Về Gốc</button>";
  html += "</body></html>";
  server.send(200, "text/html", html);
}

void handleCommand() {
  if (server.hasArg("v")) {
    String val = server.arg("v");
    Serial2.print(val[0]); // Gửi ký tự đầu tiên sang Arduino
    server.send(200, "text/plain", "OK");
  }
}

void setup() {
  Serial.begin(115200);
  Serial2.begin(9600, SERIAL_8N1, RXD2, TXD2);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) { delay(500); }
  
  Serial.println(WiFi.localIP());
  server.on("/", handleRoot);
  server.on("/cmd", handleCommand);
  server.begin();
}

void loop() {
  server.handleClient();
}