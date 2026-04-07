#include <BLEDevice.h>
#include <BLEUtils.h>
#include <BLEScan.h>
#include <BLEAdvertisedDevice.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <vector>
#include <algorithm>

// --- CONFIGURATION ---
// Wi-Fi credentials
const char* ssid     = "eren";
const char* password = "achu1234";

// Django backend endpoint
const char* serverUrl = "http://10.194.203.247:8000/api/location/update/";

// Your App's specific UUID
const std::string targetUUID = "12345678-1234-1234-1234-123456789abc"; 
int scanTime = 2; // 2 seconds gives enough time to catch all 3 phones
BLEScan* pBLEScan;

// A simple structure to hold the data we care about
struct BeaconData {
  int major;
  int minor;
  int rssi;
};

void setup() {
  Serial.begin(115200);
  Serial.println("\n--- SMART CART ESP32 SCANNER ---");

  // --- Wi-Fi Connection ---
  Serial.printf("Connecting to Wi-Fi: %s", ssid);
  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println();
  Serial.println("Connected to Wi-Fi");
  Serial.print("IP Address: ");
  Serial.println(WiFi.localIP());

  // --- BLE Initialization ---
  BLEDevice::init("");
  pBLEScan = BLEDevice::getScan(); 
  pBLEScan->setActiveScan(true); 
  pBLEScan->setInterval(100);
  pBLEScan->setWindow(99); // Full power to Bluetooth antenna
  Serial.println("BLE Scanner initialized. Listening...");
}

void loop() {
  Serial.println("\n[Scan] Listening for 2 seconds...");
  
  // Note: Using pointers (*) for ESP32 Core 3.x compatibility
  BLEScanResults* results = pBLEScan->start(scanTime, false);
  int totalDevices = results->getCount();
  
  std::vector<BeaconData> foundBeacons;

  for (int i = 0; i < totalDevices; i++) {
    BLEAdvertisedDevice device = results->getDevice(i);
    
    if (device.haveManufacturerData()) {
      String data = device.getManufacturerData();
      
      if (data.length() >= 24) {
        bool isIBeacon = ((uint8_t)data[0] == 0x4C && (uint8_t)data[1] == 0x00);
        bool isAltBeacon = ((uint8_t)data[0] == 0x18 && (uint8_t)data[1] == 0x01 && (uint8_t)data[2] == 0xBE && (uint8_t)data[3] == 0xAC);
        
        if (isIBeacon || isAltBeacon) {
          char currentUUID[37];
          sprintf(currentUUID, "%02x%02x%02x%02x-%02x%02x-%02x%02x-%02x%02x-%02x%02x%02x%02x%02x%02x",
            (uint8_t)data[4], (uint8_t)data[5], (uint8_t)data[6], (uint8_t)data[7], 
            (uint8_t)data[8], (uint8_t)data[9], (uint8_t)data[10], (uint8_t)data[11],
            (uint8_t)data[12], (uint8_t)data[13], (uint8_t)data[14], (uint8_t)data[15], 
            (uint8_t)data[16], (uint8_t)data[17], (uint8_t)data[18], (uint8_t)data[19]
          );

          if (std::string(currentUUID) == targetUUID) {
            int major = ((uint8_t)data[20] << 8) | ((uint8_t)data[21]);
            int minor = ((uint8_t)data[22] << 8) | ((uint8_t)data[23]);
            int rssi = device.getRSSI();

            // Check if we already added this specific phone in this 2-second window
            bool exists = false;
            for (auto& b : foundBeacons) {
                if (b.major == major && b.minor == minor) {
                    exists = true;
                    // If the new ping is stronger, update it
                    if (rssi > b.rssi) b.rssi = rssi;
                    break;
                }
            }
            
            // If it's a new phone, add it to our list
            if (!exists) {
                foundBeacons.push_back({major, minor, rssi});
            }
          }
        }
      }
    }
  }

  // --- SORT, BUILD JSON, AND POST TO DJANGO ---
  if (!foundBeacons.empty()) {
    
    // Sort from Strongest (Closest to 0) to Weakest
    std::sort(foundBeacons.begin(), foundBeacons.end(), [](const BeaconData& a, const BeaconData& b) {
      return a.rssi > b.rssi; 
    });

    // Grab up to 3 (or fewer if only 1 or 2 are turned on)
    int limit = std::min((int)foundBeacons.size(), 3);
    Serial.printf("Found %d matching phones. Top %d:\n", foundBeacons.size(), limit);

    // --- Construct JSON payload ---
    String jsonPayload = "{\"target_uuid\": \"" + String(targetUUID.c_str()) + "\", \"beacons\": [";

    for (int i = 0; i < limit; i++) {
      Serial.printf("   #%d | Major-Minor: %d-%d | RSSI: %d dBm\n", 
                    i + 1, foundBeacons[i].major, foundBeacons[i].minor, foundBeacons[i].rssi);

      if (i > 0) jsonPayload += ", ";
      jsonPayload += "{\"major\": " + String(foundBeacons[i].major)
                   + ", \"minor\": " + String(foundBeacons[i].minor)
                   + ", \"rssi\": "  + String(foundBeacons[i].rssi)
                   + "}";
    }

    jsonPayload += "]}";
    Serial.println("[POST] Payload: " + jsonPayload);

    // --- Send HTTP POST ---
    if (WiFi.status() == WL_CONNECTED) {
      HTTPClient http;
      http.begin(serverUrl);
      http.addHeader("Content-Type", "application/json");

      int httpResponseCode = http.POST(jsonPayload);
      Serial.printf("[POST] Response code: %d\n", httpResponseCode);

      if (httpResponseCode > 0) {
        String response = http.getString();
        Serial.println("[POST] Response: " + response);
      } else {
        Serial.printf("[POST] Error: %s\n", http.errorToString(httpResponseCode).c_str());
      }

      http.end();
    } else {
      Serial.println("[WARN] Wi-Fi disconnected! Skipping POST.");
    }

  } else {
    Serial.println("No target phones found.");
  }

  pBLEScan->clearResults(); 
}