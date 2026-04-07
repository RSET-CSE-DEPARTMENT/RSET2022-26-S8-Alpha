# IoT + ML Fall Detection Pipeline Implementation Guide

## Overview
Complete implementation for ESP32 IoT devices to send sensor readings to cloud backend, run ML fall detection, and send notifications to Flutter app.

---

## 📦 What's Been Implemented

### 1. **Backend - Python/FastAPI** (`lib/backend/`)

#### `fall_detection_model.py`
- ML model for fall detection using accelerometer & gyroscope data
- Features:
  - Free fall detection (low acceleration)
  - Impact detection (high acceleration)
  - Unusual rotation patterns detection
  - Batch processing support
  - Configurable thresholds

#### `main.py` - New Endpoints
- **POST `/sensor-readings`** - Store raw sensor data in Firestore
  ```
  Payload: {deviceId, userId, gyroX/Y/Z, accelX/Y/Z}
  ```
- **POST `/predict-fall`** - Run ML prediction and create alerts
  ```
  Payload: Same as above or {deviceId, userId, readings: [...]}
  ```

#### `notifications.py` - Enhanced
- `send_fall_notification()` - Send FCM alerts when fall detected
- Gets FCM tokens from Firestore user documents
- Sends to all user devices with push notification data

#### `requirements.txt`
- Updated with Firebase Admin SDK, numpy, scikit-learn

### 2. **Flutter Frontend** (`lib/`)

#### `models/fall_alert_model.dart`
- `FallAlert` class with:
  - Firestore serialization (fromFirestore, toFirestore)
  - JSON serialization (fromJson, toJson)
  - Helper methods (getConfidencePercentage, getStatus, etc.)

#### `services/api_service.dart` - New Methods
```dart
// Send sensor readings
sendSensorReadings(deviceId, userId, gyro*, accel*)

// Predict fall (single)
predictFallSingle(deviceId, userId, gyro*, accel*)

// Predict fall (batch)
predictFallBatch(deviceId, userId, readings)

// Firestore fall alerts
getFallAlerts(userId)
getUnacknowledgedAlerts(userId)
acknowledgeFallAlert(alertId)
getDeviceFallAlerts(userId, deviceId)
streamFallAlerts(userId)
deleteFallAlert(alertId)
```

#### `fall_alerts_page.dart`
- Complete UI for viewing fall alerts
- Features:
  - Real-time alert updates (Firestore stream)
  - Filter by acknowledged status
  - View alert details with reasoning
  - Acknowledge individual alerts
  - Delete alerts
  - Color-coded confidence levels
  - Formatted timestamps

#### `home_page.dart`
- Added "Fall Alerts" card to overview
- Navigation to fall alerts page

---

## 🔧 Setup Instructions

### Step 1: Firebase Console Setup

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Select your project `fiftypercent-e0f71`
3. Create **Firestore Collections**:

#### Collection: `sensor_readings`
```
Path: /sensor_readings/{documentId}
Fields:
  - deviceId: string
  - userId: string
  - gyroX: number
  - gyroY: number
  - gyroZ: number
  - accelX: number
  - accelY: number
  - accelZ: number
  - timestamp: timestamp
```

#### Collection: `fall_alerts`
```
Path: /fall_alerts/{documentId}
Fields:
  - deviceId: string
  - userId: string
  - confidence: number (0-1)
  - isFall: boolean
  - timestamp: timestamp
  - acknowledged: boolean
  - acknowledgedAt: timestamp (optional)
  - reasoning: array of strings
```

4. **Set Firestore Security Rules** (Firestore → Rules):
```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /sensor_readings/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || 
                            request.auth.uid == request.resource.data.userId;
    }
    
    match /fall_alerts/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || 
                            request.auth.uid == request.resource.data.userId;
    }
    
    match /device_registrations/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || 
                            request.auth.uid == request.resource.data.userId;
    }
  }
}
```

### Step 2: Backend Setup

1. **Get Firebase Credentials**:
   - Firebase Console → Project Settings → Service Accounts
   - Click "Generate New Private Key"
   - Save as `lib/backend/firebase_credentials.json`
   - **⚠️ Add to `.gitignore`** (do NOT commit!)

2. **Install Dependencies**:
   ```bash
   cd lib/backend
   pip install -r requirements.txt
   ```

3. **Set Environment Variables**:
   ```bash
   # .env file in lib/backend/
   FIREBASE_CREDENTIALS=./firebase_credentials.json
   API_HOST=0.0.0.0
   API_PORT=8000
   ```

4. **Run Backend**:
   ```bash
   python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
   ```

### Step 3: Flutter Setup

1. **Update API URL** in `lib/services/api_service.dart`:
   ```dart
   static const String baseUrl = 'http://YOUR_SERVER_IP:8000';
   ```

2. **Add Cloud Firestore Dependency** (already in pubspec.yaml):
   ```yaml
   cloud_firestore: ^4.14.0
   ```

3. **Enable Firestore in Firebase Console**:
   - Firestore Database → Create Database
   - Start in Test Mode (for development)
   - Choose region close to users

### Step 4: ESP32 Configuration

#### ESP32 Sensor Reading Code (Arduino)
```cpp
#include <HTTPClient.h>
#include <ArduinoJson.h>

// Sensor includes for IMU (MPU6050 or similar)
#include <MPU6050.h>

// WiFi credentials
const char* SSID = "YOUR_WIFI";
const char* PASSWORD = "YOUR_PASSWORD";

// Backend server
const char* SERVER_URL = "http://YOUR_SERVER_IP:8000";
const char* DEVICE_ID = "esp32_001";
const String USER_ID = "USER_UID_FROM_FIREBASE";

HTTPClient http;
MPU6050 mpu;

void setup() {
  Serial.begin(115200);
  
  // Connect to WiFi
  WiFi.begin(SSID, PASSWORD);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("\nWiFi connected");
  
  // Initialize MPU6050
  mpu.initialize();
  if (!mpu.testConnection()) {
    Serial.println("MPU6050 connection failed");
  }
}

void loop() {
  // Read sensor data
  int16_t ax, ay, az, gx, gy, gz;
  mpu.getMotion6(&ax, &ay, &az, &gx, &gy, &gz);
  
  // Convert to m/s² and deg/s
  float accelX = ax / 16384.0 * 9.81;
  float accelY = ay / 16384.0 * 9.81;
  float accelZ = az / 16384.0 * 9.81;
  float gyroX = gx / 131.0;
  float gyroY = gy / 131.0;
  float gyroZ = gz / 131.0;
  
  // Create JSON payload
  DynamicJsonDocument doc(256);
  doc["deviceId"] = DEVICE_ID;
  doc["userId"] = USER_ID;
  doc["accelX"] = accelX;
  doc["accelY"] = accelY;
  doc["accelZ"] = accelZ;
  doc["gyroX"] = gyroX;
  doc["gyroY"] = gyroY;
  doc["gyroZ"] = gyroZ;
  
  String payload;
  serializeJson(doc, payload);
  
  // Send to backend
  if (WiFi.connected()) {
    http.begin(String(SERVER_URL) + "/predict-fall");
    http.addHeader("Content-Type", "application/json");
    int httpCode = http.POST(payload);
    
    if (httpCode == 200) {
      String response = http.getString();
      DynamicJsonDocument respDoc(512);
      deserializeJson(respDoc, response);
      
      if (respDoc["prediction"]["is_fall"]) {
        Serial.print("FALL DETECTED! Confidence: ");
        Serial.println(respDoc["prediction"]["confidence"]);
        // Optional: trigger local alarm
      }
    }
    http.end();
  }
  
  delay(1000); // Send every second (adjust as needed)
}
```

---

## 📊 Data Flow Diagram

```
ESP32 (Sensor)
    ↓ (POST /sensor-readings + /predict-fall)
FastAPI Backend
    ↓ (Save + ML Prediction)
Firebase Firestore
    ├─ sensor_readings collection
    └─ fall_alerts collection
         ↓ (Send FCM)
Firebase Cloud Messaging
    ↓
Flutter App
    ├─ Notification received
    ├─ Fall Alerts Page displays alert
    └─ User can acknowledge/delete
```

---

## 🧪 Testing

### Test Backend Endpoints

**1. Send Sensor Reading**:
```bash
curl -X POST http://localhost:8000/sensor-readings \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "esp32_001",
    "userId": "test_user_id",
    "gyroX": 10, "gyroY": 5, "gyroZ": 3,
    "accelX": 9.81, "accelY": 0, "accelZ": 0
  }'
```

**2. Predict Fall**:
```bash
curl -X POST http://localhost:8000/predict-fall \
  -H "Content-Type: application/json" \
  -d '{
    "deviceId": "esp32_001",
    "userId": "test_user_id",
    "gyroX": 250, "gyroY": 180, "gyroZ": 200,
    "accelX": 30, "accelY": 25, "accelZ": 20
  }'
```

### Test Flutter Integration

1. Update `baseUrl` in api_service.dart to your backend
2. Run app in dev mode
3. Check Firestore console for incoming data
4. Check fall alerts page for real-time updates

---

## 🔐 Security Notes

1. **Firebase Credentials**:
   - Keep `firebase_credentials.json` in `.gitignore`
   - Never commit to version control

2. **Firestore Rules**:
   - Current rules allow users to access only their own data
   - In production, consider stricter rules

3. **Backend API**:
   - Add authentication (Firebase tokens verification)
   - Rate limiting on endpoints
   - Input validation

4. **ESP32**:
   - Use HTTPS for production
   - Implement token-based authentication
   - Secure WiFi credentials

---

## 🚀 Production Deployment

### Backend Deployment Options:
- **Google Cloud Run** (recommended for Firebase integration)
- **AWS Lambda** (with API Gateway)
- **Heroku** (simple but less scalable)
- **Self-hosted server**

### Firebase Hosting:
- Deploy backend to Cloud Run
- Use environment variables for secrets
- Set up CI/CD pipeline

### App Distribution:
- Test with TestFlight (iOS)
- Test with Google Play Beta
- Update API URL to production backend

---

## 📝 Configuration Summary

| Component | Configuration |
|-----------|----------------|
| Firebase Project | `fiftypercent-e0f71` |
| Firestore Collections | `sensor_readings`, `fall_alerts` |
| Backend Port | `8000` |
| ML Thresholds | Configurable in `fall_detection_model.py` |
| Notification Type | FCM Push Notifications |
| Flutter Build | Requires cloud_firestore dependency |

---

## 🆘 Troubleshooting

### Backend Won't Connect to Firebase
```bash
# Check credentials file exists and is valid
ls -la lib/backend/firebase_credentials.json

# Check environment variable
echo $FIREBASE_CREDENTIALS
```

### Flutter App Not Receiving Notifications
1. Check Firestore has `users` collection with `fcmTokens` field
2. Verify FCM tokens are properly saved to Firestore
3. Check Firebase Cloud Messaging is enabled in Firebase Console
4. Test with curl to trigger notification manually

### Fall Detection Not Triggering
1. Check threshold values in `fall_detection_model.py`
2. Verify sensor data format is correct
3. Check confidence score (should be > 0.5 for fall)
4. Review ML model reasoning in logs

---

## 📚 Additional Resources

- [Firebase Admin SDK - Python](https://firebase.google.com/docs/database/admin/start)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Flutter Firestore Integration](https://firebase.flutter.dev/)
- [FCM Documentation](https://firebase.google.com/docs/cloud-messaging)
- [ESP32 Documentation](https://docs.espressif.com/projects/esp-idf/en/latest/)

---

## ✅ Next Steps

1. ✅ Create Firestore collections (see Firebase Console Setup)
2. ✅ Download Firebase credentials
3. ✅ Install backend dependencies
4. ✅ Configure ESP32 with your WiFi and User ID
5. ✅ Update Flutter API URL
6. ✅ Test each component individually
7. ✅ Deploy to production

---

**Version**: 1.0  
**Last Updated**: December 27, 2025  
**Status**: Ready for testing and deployment
