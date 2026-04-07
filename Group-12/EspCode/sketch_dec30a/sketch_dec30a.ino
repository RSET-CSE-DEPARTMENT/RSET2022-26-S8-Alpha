#include <WiFi.h>
#include <HTTPClient.h>
#include <Wire.h>
#include <math.h>
#include <TinyGPS++.h>
#include <HardwareSerial.h>

#include <Adafruit_MPU6050.h>
#include <Adafruit_Sensor.h>

/* ================= MPU6050 ================= */
Adafruit_MPU6050 mpu;

/* FALL THRESHOLDS */
const float FALL_ACCEL_THRESHOLD = 18.0;
const float FALL_GYRO_THRESHOLD  = 2.0;

/* FALL COOLDOWN */
unsigned long lastFallTime = 0;
const unsigned long FALL_COOLDOWN_MS = 15000;

/* ================= GPS ================= */
TinyGPSPlus gps;
HardwareSerial gpsSerial(1);

unsigned long lastGPSCheck = 0;
const unsigned long GPS_INTERVAL_MS = 3000;

/* ================= WIFI ================= */
const char* WIFI_SSID = "Angeline";
const char* WIFI_PASSWORD = "hellohibyeeeee";

const char* GPS_URL = "http://172.20.10.3:5000/gps";
const char* FALL_URL = "http://172.20.10.3:5000/predict";
// Set this to the Firebase Auth UID of the current user for this device.
const char* USER_ID = "REPLACE_WITH_FIREBASE_UID";


/* ================= SEND GPS ================= */
void sendGPS(double lat, double lon) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(GPS_URL);
  http.addHeader("Content-Type", "application/json");

  String payload =
    "{"
    "\"userId\":\"" + String(USER_ID) + "\","
    "\"lat\":" + String(lat, 6) + ","
    "\"lon\":" + String(lon, 6) +
    "}";

  http.POST(payload);
  http.end();

  Serial.println("📡 GPS SENT TO FLASK");
}


void sendFall(float accMag, float gyroMag) {
  if (WiFi.status() != WL_CONNECTED) return;

  HTTPClient http;
  http.begin(FALL_URL);
  http.addHeader("Content-Type", "application/json");

  // Simple features (Flask already expects this format)
  float acc_std  = abs(accMag - 9.8);
  float gyro_std = gyroMag * 0.3;

  String payload =
    "{"
    "\"userId\":\"" + String(USER_ID) + "\","
    "\"acc_mean\":" + String(accMag, 2) + ","
    "\"acc_std\":" + String(acc_std, 2) + ","
    "\"gyro_mean\":" + String(gyroMag, 2) + ","
    "\"gyro_std\":" + String(gyro_std, 2) +
    "}";

  http.POST(payload);
  http.end();

  Serial.println("🚨 FALL DATA SENT TO FLASK");
}

/* ================= SETUP ================= */
void setup() {
  Serial.begin(115200);
  delay(2000);

  WiFi.mode(WIFI_STA);
WiFi.disconnect(true);
delay(1000);

WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
Serial.print("Connecting to WiFi");

unsigned long startAttempt = millis();

while (WiFi.status() != WL_CONNECTED && millis() - startAttempt < 20000) {
  delay(500);
  Serial.print(".");
}

Serial.println();

if (WiFi.status() == WL_CONNECTED) {
  Serial.println("✅ WiFi connected");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());
} else {
  Serial.println("❌ WiFi FAILED");
  Serial.print("Status code: ");
  Serial.println(WiFi.status());
}

  
  Wire.begin(21, 22);
  if (!mpu.begin()) {
    Serial.println("❌ MPU6050 not found");
    while (1) delay(1000);
  }
  Serial.println("✅ MPU6050 Found");
  

  gpsSerial.begin(9600, SERIAL_8N1, 16, 17);
  Serial.println("🚀 GPS DEBUG MODE (MPU COMMENTED)");
}

/* ================= LOOP ================= */
void loop() {

  
  sensors_event_t a, g, temp;
  mpu.getEvent(&a, &g, &temp);

  float ax = a.acceleration.x;
  float ay = a.acceleration.y;
  float az = a.acceleration.z;
  float gx = g.gyro.x;
  float gy = g.gyro.y;
  float gz = g.gyro.z;

  float accMag  = sqrt(ax*ax + ay*ay + az*az);
  float gyroMag = sqrt(gx*gx + gy*gy + gz*gz);

  Serial.print("Acc=");
  Serial.print(accMag, 2);
  Serial.print(" | Gyro=");
  Serial.print(gyroMag, 2);

  

    /* --------- FALL DETECTION --------- */
  if (accMag > FALL_ACCEL_THRESHOLD &&
      gyroMag > FALL_GYRO_THRESHOLD &&
      millis() - lastFallTime > FALL_COOLDOWN_MS) {

    Serial.println("  🚨 FALL DETECTED!");
    sendFall(accMag, gyroMag);
    lastFallTime = millis();

  } else {
    Serial.println("  ✅ No Fall");
  }

  if (millis() - lastGPSCheck >= GPS_INTERVAL_MS) {
    lastGPSCheck = millis();

    while (gpsSerial.available()) {
      gps.encode(gpsSerial.read());
    }

    if (gps.location.isValid()) {
      double lat = gps.location.lat();
      double lon = gps.location.lng();

      Serial.print("📍 GPS → ");
      Serial.print(lat, 6);
      Serial.print(", ");
      Serial.println(lon, 6);

      sendGPS(lat, lon);
    } else {
      Serial.println("❌ GPS not fixed yet");
    }
  }

  delay(200);
}
