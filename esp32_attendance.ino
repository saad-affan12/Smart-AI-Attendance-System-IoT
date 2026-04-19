/*
  esp32_attendance.ino
  - Streams MJPEG on port 81
  - Controls built-in flash LED and an external LED on GPIO 4
  - REST endpoints: /present (turn LED steady), /late (blink), /off
  - Returns JSON status on /status

  Configure WiFi SSID and PASSWORD below before upload.
*/

#include "esp_camera.h"
#include <WiFi.h>
#include <WebServer.h>

// ====== User WiFi credentials - set before upload ======
const char* ssid = "YOUR_SSID";
const char* password = "YOUR_PASSWORD";
// ======================================================

// Camera module pins for AI Thinker
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

// LED pin (external or on-board depending on module)
const int LED_PIN = 4; // safe choice for many AI Thinker boards

WebServer server(81);

// simple state for LED
enum LedMode {LED_OFF, LED_ON, LED_BLINK};
volatile LedMode ledMode = LED_OFF;
portMUX_TYPE mux = portMUX_INITIALIZER_UNLOCKED;

void setupCamera(){
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
  config.pin_sscb_sda = SIOD_GPIO_NUM;
  config.pin_sscb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  // Prioritize low latency and stable FPS over image detail.
  if(psramFound()){
    config.frame_size = FRAMESIZE_QVGA;   // 320x240
    config.jpeg_quality = 24;             // balanced compression for streaming
    config.fb_count = 2;                  // double buffer for smoother MJPEG
  } else {
    config.frame_size = FRAMESIZE_QVGA;
    config.jpeg_quality = 28;
    config.fb_count = 1;
    config.fb_location = CAMERA_FB_IN_DRAM;
  }

  esp_err_t err = esp_camera_init(&config);
  if (err != ESP_OK) {
    Serial.printf("Camera init failed with error 0x%x\n", err);
    while(true) delay(1000);
  }

  sensor_t * s = esp_camera_sensor_get();
  if (s != nullptr) {
    // Keep exposure auto, but reduce extra image processing that costs cycles.
    s->set_framesize(s, FRAMESIZE_QVGA);
    s->set_quality(s, psramFound() ? 24 : 28);
    s->set_brightness(s, 0);
    s->set_contrast(s, 0);
    s->set_saturation(s, -2);
    s->set_special_effect(s, 0);
    s->set_whitebal(s, 1);
    s->set_awb_gain(s, 1);
    s->set_wb_mode(s, 0);
    s->set_exposure_ctrl(s, 1);
    s->set_aec2(s, 0);
    s->set_ae_level(s, 0);
    s->set_gain_ctrl(s, 1);
    s->set_agc_gain(s, 0);
    s->set_gainceiling(s, (gainceiling_t)0);
    s->set_bpc(s, 0);
    s->set_wpc(s, 0);
    s->set_raw_gma(s, 0);
    s->set_lenc(s, 0);
    s->set_dcw(s, 1);
    s->set_colorbar(s, 0);
  }
}

// Stream handler (MJPEG)
void handleStream(){
  WiFiClient client = server.client();
  client.setNoDelay(true);
  String response = "HTTP/1.1 200 OK\r\nContent-Type: multipart/x-mixed-replace; boundary=frame\r\n\r\n";
  server.sendContent(response);

  while (true) {
    if(!client.connected()){
      break;
    }

    camera_fb_t * fb = esp_camera_fb_get();
    if(!fb) {
      Serial.println("Camera capture failed");
      break;
    }

    String head = "--frame\r\nContent-Type: image/jpeg\r\nContent-Length: " + String(fb->len) + "\r\n\r\n";
    server.sendContent(head);
    client.write(fb->buf, fb->len);
    server.sendContent("\r\n");

    esp_camera_fb_return(fb);

    delay(1);
  }
}

void setLedMode(LedMode m){
  portENTER_CRITICAL(&mux);
  ledMode = m;
  portEXIT_CRITICAL(&mux);
}

void handlePresent(){
  setLedMode(LED_ON);
  server.send(200, "application/json", "{\"status\":\"present\"}");
}

void handleLate(){
  setLedMode(LED_BLINK);
  server.send(200, "application/json", "{\"status\":\"late\"}");
}

void handleOff(){
  setLedMode(LED_OFF);
  server.send(200, "application/json", "{\"status\":\"off\"}");
}

void handleStatus(){
  const char* s = "off";
  portENTER_CRITICAL(&mux);
  if(ledMode==LED_ON) s = "on";
  else if(ledMode==LED_BLINK) s = "blink";
  portEXIT_CRITICAL(&mux);
  String body = String("{\"led\":\"") + s + String("\"}");
  server.send(200, "application/json", body);
}

void ledTask(void* arg){
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);
  while(true){
    LedMode m;
    portENTER_CRITICAL(&mux);
    m = ledMode;
    portEXIT_CRITICAL(&mux);

    if(m==LED_ON){
      digitalWrite(LED_PIN, HIGH);
      vTaskDelay(100 / portTICK_PERIOD_MS);
    } else if(m==LED_BLINK){
      digitalWrite(LED_PIN, HIGH);
      vTaskDelay(200 / portTICK_PERIOD_MS);
      digitalWrite(LED_PIN, LOW);
      vTaskDelay(200 / portTICK_PERIOD_MS);
    } else {
      digitalWrite(LED_PIN, LOW);
      vTaskDelay(200 / portTICK_PERIOD_MS);
    }
  }
}

void setup(){
  Serial.begin(115200);
  pinMode(LED_PIN, OUTPUT);
  digitalWrite(LED_PIN, LOW);

  WiFi.begin(ssid, password);
  WiFi.setSleep(false);
  Serial.printf("Connecting to %s\n", ssid);
  int retries = 0;
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
    if(++retries > 60){
      Serial.println("\nFailed to connect to WiFi");
      break;
    }
  }
  Serial.println();
  Serial.print("IP address: ");
  Serial.println(WiFi.localIP());

  setupCamera();

  server.on("/stream", HTTP_GET, handleStream);
  server.on("/present", HTTP_GET, handlePresent);
  server.on("/late", HTTP_GET, handleLate);
  server.on("/off", HTTP_GET, handleOff);
  server.on("/status", HTTP_GET, handleStatus);

  server.begin();

  xTaskCreatePinnedToCore(ledTask, "ledTask", 2048, NULL, 1, NULL, 1);
}

void loop(){
  server.handleClient();
}
