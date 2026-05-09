#include <Arduino.h>
#include <WiFiClient.h>
#include "esp_camera.h"
#include "esp_http_server.h"

#include <cstring>

#include "board_config.h"
#include "config.h"

extern volatile bool streamEnabled;

static httpd_handle_t stream_httpd = NULL;
static httpd_handle_t control_httpd = NULL;

static const char *STREAM_CONTENT_TYPE = "multipart/x-mixed-replace;boundary=frame";
static const char *STREAM_BOUNDARY = "\r\n--frame\r\n";
static const char *STREAM_PART = "Content-Type: image/jpeg\r\nContent-Length: %u\r\n\r\n";

struct ParsedUrl {
  String host;
  uint16_t port;
  String path;
};

static bool parseHttpUrl(const char *url, ParsedUrl &out) {
  if (!url) {
    return false;
  }

  String full(url);
  const String httpPrefix = "http://";
  if (!full.startsWith(httpPrefix)) {
    return false;
  }

  String rest = full.substring(httpPrefix.length());
  int slashIndex = rest.indexOf('/');
  String hostPort = slashIndex >= 0 ? rest.substring(0, slashIndex) : rest;
  out.path = slashIndex >= 0 ? rest.substring(slashIndex) : "/";
  out.port = 80;

  int colonIndex = hostPort.indexOf(':');
  if (colonIndex >= 0) {
    out.host = hostPort.substring(0, colonIndex);
    String portString = hostPort.substring(colonIndex + 1);
    long parsedPort = portString.toInt();
    if (parsedPort <= 0 || parsedPort > 65535) {
      return false;
    }
    out.port = static_cast<uint16_t>(parsedPort);
  } else {
    out.host = hostPort;
  }

  return out.host.length() > 0 && out.path.length() > 0;
}

static bool writeAll(WiFiClient &client, const uint8_t *data, size_t length) {
  size_t sent = 0;
  while (sent < length) {
    int written = client.write(data + sent, length - sent);
    if (written <= 0) {
      return false;
    }
    sent += static_cast<size_t>(written);
  }
  return true;
}

static esp_err_t stream_handler(httpd_req_t *req) {
  if (!streamEnabled) {
    httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
    httpd_resp_set_status(req, "503 Service Unavailable");
    return httpd_resp_send(req, "Stream disabled", HTTPD_RESP_USE_STRLEN);
  }

  esp_err_t res = httpd_resp_set_type(req, STREAM_CONTENT_TYPE);
  if (res != ESP_OK) {
    return res;
  }

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");
  httpd_resp_set_hdr(req, "Cache-Control", "no-cache");

  while (streamEnabled) {
    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      return ESP_FAIL;
    }

    if (httpd_resp_send_chunk(req, STREAM_BOUNDARY, strlen(STREAM_BOUNDARY)) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    char header[64];
    int header_len = snprintf(header, sizeof(header), STREAM_PART, fb->len);
    if (httpd_resp_send_chunk(req, header, header_len) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    if (httpd_resp_send_chunk(req, (const char *)fb->buf, fb->len) != ESP_OK) {
      esp_camera_fb_return(fb);
      break;
    }

    esp_camera_fb_return(fb);
    delay(1);
  }

  return httpd_resp_send_chunk(req, NULL, 0);
}

static esp_err_t control_stream_handler(httpd_req_t *req) {
  char query[32];
  char enabled[8];

  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  size_t query_len = httpd_req_get_url_query_len(req) + 1;
  if (query_len <= 1 || query_len > sizeof(query)) {
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Missing query string");
  }

  if (httpd_req_get_url_query_str(req, query, sizeof(query)) != ESP_OK) {
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Invalid query string");
  }

  if (httpd_query_key_value(query, "enabled", enabled, sizeof(enabled)) != ESP_OK) {
    return httpd_resp_send_err(req, HTTPD_400_BAD_REQUEST, "Missing enabled param");
  }

  streamEnabled = !strcmp(enabled, "1") || !strcmp(enabled, "true") || !strcmp(enabled, "on");

  return httpd_resp_send(req, streamEnabled ? "{\"stream_enabled\":true}" : "{\"stream_enabled\":false}", HTTPD_RESP_USE_STRLEN);
}

static esp_err_t trigger_capture_handler(httpd_req_t *req) {
  httpd_resp_set_hdr(req, "Access-Control-Allow-Origin", "*");

  // Lấy parameter "weight" từ query URL, mặc định là "0"
  String weightValue = "0";
  size_t query_len = httpd_req_get_url_query_len(req) + 1;
  if (query_len > 1 && query_len <= 160) {
    char query[160];
    if (httpd_req_get_url_query_str(req, query, sizeof(query)) == ESP_OK) {
      char weight[32];
      if (httpd_query_key_value(query, "weight", weight, sizeof(weight)) == ESP_OK) {
        weightValue = weight;
      }
    }
  }

  camera_fb_t *fb = esp_camera_fb_get();
  if (!fb) {
    return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Camera capture failed");
  }

  ParsedUrl backend;
  if (!parseHttpUrl(BACKEND_PREDICT_URL, backend)) {
    esp_camera_fb_return(fb);
    return httpd_resp_send_err(req, HTTPD_500_INTERNAL_SERVER_ERROR, "Invalid backend URL");
  }

  WiFiClient httpClient;
  httpClient.setTimeout(12000);

  if (!httpClient.connect(backend.host.c_str(), backend.port)) {
    esp_camera_fb_return(fb);
    httpd_resp_set_status(req, "502 Bad Gateway");
    return httpd_resp_send(req, "Cannot connect to backend", HTTPD_RESP_USE_STRLEN);
  }

  const String boundary = "----ESP32CamBoundary7MA4YWxkTrZu0gW";

  const String weightPart =
      "--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"weight\"\r\n\r\n" +
      weightValue + "\r\n";

  const String filePartHeader =
      "--" + boundary + "\r\n"
      "Content-Disposition: form-data; name=\"file\"; filename=\"capture.jpg\"\r\n"
      "Content-Type: image/jpeg\r\n\r\n";

  const String partFooter = "\r\n--" + boundary + "--\r\n";

  const size_t contentLength = weightPart.length() + filePartHeader.length() + fb->len + partFooter.length();

  String requestHeaders =
      "POST " + backend.path + " HTTP/1.1\r\n"
      "Host: " + backend.host + "\r\n"
      "x-api-key: " + String(BACKEND_API_KEY) + "\r\n"
      "Content-Type: multipart/form-data; boundary=" + boundary + "\r\n"
      "Content-Length: " + String(contentLength) + "\r\n"
      "Connection: close\r\n\r\n";

  bool writeOk = true;
  writeOk = writeOk && writeAll(httpClient, reinterpret_cast<const uint8_t *>(requestHeaders.c_str()), requestHeaders.length());
  writeOk = writeOk && writeAll(httpClient, reinterpret_cast<const uint8_t *>(weightPart.c_str()), weightPart.length());
  writeOk = writeOk && writeAll(httpClient, reinterpret_cast<const uint8_t *>(filePartHeader.c_str()), filePartHeader.length());
  writeOk = writeOk && writeAll(httpClient, fb->buf, fb->len);
  writeOk = writeOk && writeAll(httpClient, reinterpret_cast<const uint8_t *>(partFooter.c_str()), partFooter.length());

  if (!writeOk) {
    httpClient.stop();
    esp_camera_fb_return(fb);
    httpd_resp_set_status(req, "502 Bad Gateway");
    return httpd_resp_send(req, "Failed to send request body", HTTPD_RESP_USE_STRLEN);
  }

  String rawResponse;
  rawResponse.reserve(1024);
  unsigned long startMs = millis();
  while (httpClient.connected() || httpClient.available()) {
    while (httpClient.available()) {
      char c = static_cast<char>(httpClient.read());
      rawResponse += c;
      startMs = millis();
    }
    if (millis() - startMs > 12000) {
      break;
    }
    delay(1);
  }
  httpClient.stop();

  int status = 502;
  String responseBody = rawResponse;
  int statusLineEnd = rawResponse.indexOf("\r\n");
  if (statusLineEnd > 0) {
    String statusLine = rawResponse.substring(0, statusLineEnd);
    int firstSpace = statusLine.indexOf(' ');
    if (firstSpace > 0 && statusLine.length() >= firstSpace + 4) {
      status = statusLine.substring(firstSpace + 1, firstSpace + 4).toInt();
    }
  }

  int bodyStart = rawResponse.indexOf("\r\n\r\n");
  if (bodyStart >= 0) {
    responseBody = rawResponse.substring(bodyStart + 4);
  }

  esp_camera_fb_return(fb);

  if (status <= 0) {
    httpd_resp_set_status(req, "502 Bad Gateway");
    return httpd_resp_send(req, "Backend request failed", HTTPD_RESP_USE_STRLEN);
  }

  if (status == 401) {
    httpd_resp_set_status(req, "401 Unauthorized");
  } else if (status == 400) {
    httpd_resp_set_status(req, "400 Bad Request");
  } else if (status == 413) {
    httpd_resp_set_status(req, "413 Payload Too Large");
  } else if (status == 415) {
    httpd_resp_set_status(req, "415 Unsupported Media Type");
  } else if (status >= 500) {
    httpd_resp_set_status(req, "502 Bad Gateway");
  }

  httpd_resp_set_type(req, "application/json");
  return httpd_resp_send(req, responseBody.c_str(), HTTPD_RESP_USE_STRLEN);
}

void startCameraServer() {
  httpd_config_t stream_config = HTTPD_DEFAULT_CONFIG();
  stream_config.server_port = 81;
  stream_config.ctrl_port = 82;

  httpd_config_t control_config = HTTPD_DEFAULT_CONFIG();
  control_config.server_port = 82;
  control_config.ctrl_port = 83;

  httpd_uri_t stream_uri = {
    .uri = "/stream",
    .method = HTTP_GET,
    .handler = stream_handler,
    .user_ctx = NULL,
  };

  if (httpd_start(&stream_httpd, &stream_config) == ESP_OK) {
    httpd_register_uri_handler(stream_httpd, &stream_uri);
  }

  httpd_uri_t control_uri = {
    .uri = "/control/stream",
    .method = HTTP_GET,
    .handler = control_stream_handler,
    .user_ctx = NULL,
  };

  httpd_uri_t trigger_uri = {
    .uri = "/trigger/capture",
    .method = HTTP_GET,
    .handler = trigger_capture_handler,
    .user_ctx = NULL,
  };

  if (httpd_start(&control_httpd, &control_config) == ESP_OK) {
    httpd_register_uri_handler(control_httpd, &control_uri);
    httpd_register_uri_handler(control_httpd, &trigger_uri);
  }
}

void setupLedFlash() {
}
