# IoT Fall Detection - Implementation Checklist

## Phase 1: Setup & Configuration ✅

### Firebase Console (Day 1)
- [ ] Go to Firebase Console: https://console.firebase.google.com
- [ ] Select project: `fiftypercent-e0f71`
- [ ] Create Firestore Collection: `sensor_readings`
  - [ ] deviceId (string)
  - [ ] userId (string)
  - [ ] gyroX, gyroY, gyroZ (number)
  - [ ] accelX, accelY, accelZ (number)
  - [ ] timestamp (timestamp)
- [ ] Create Firestore Collection: `fall_alerts`
  - [ ] deviceId (string)
  - [ ] userId (string)
  - [ ] confidence (number)
  - [ ] isFall (boolean)
  - [ ] timestamp (timestamp)
  - [ ] acknowledged (boolean)
  - [ ] reasoning (array)
- [ ] Copy security rules from `FIREBASE_FIRESTORE_SETUP.md`
- [ ] Paste into Firestore → Rules
- [ ] Create collection: `device_registrations` (optional)
- [ ] Download service account JSON:
  - [ ] Project Settings → Service Accounts
  - [ ] Generate Private Key
  - [ ] Save as `lib/backend/firebase_credentials.json`
  - [ ] Add to `.gitignore`
- [ ] Enable Cloud Messaging:
  - [ ] Cloud Messaging tab
  - [ ] Note Server Key for later

### Backend Environment (Day 1)
- [ ] Navigate to `lib/backend/`
- [ ] Create `.env` file:
  ```
  FIREBASE_CREDENTIALS=./firebase_credentials.json
  API_HOST=0.0.0.0
  API_PORT=8000
  ```
- [ ] Install Python dependencies:
  ```bash
  pip install -r requirements.txt
  ```
- [ ] Verify all packages installed:
  ```bash
  pip list | grep firebase
  pip list | grep numpy
  ```

### Flutter Configuration (Day 1)
- [ ] Open `lib/services/api_service.dart`
- [ ] Update baseUrl:
  ```dart
  static const String baseUrl = 'http://YOUR_BACKEND_IP:8000';
  ```
- [ ] Verify `cloud_firestore` in `pubspec.yaml`
- [ ] Run `flutter pub get`

---

## Phase 2: Backend Testing 🔧

### Test Backend Startup (Day 1)
- [ ] Navigate to `lib/backend/`
- [ ] Start backend:
  ```bash
  python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
  ```
- [ ] Verify startup message in console
- [ ] Open browser to http://localhost:8000/docs
- [ ] See Swagger API documentation

### Test Sensor Reading Endpoint (Day 2)
- [ ] Open terminal/Postman/curl
- [ ] Send test data:
  ```bash
  curl -X POST http://localhost:8000/sensor-readings \
    -H "Content-Type: application/json" \
    -d '{
      "deviceId": "esp32_test_001",
      "userId": "test_user_123",
      "gyroX": 10.5,
      "gyroY": 5.2,
      "gyroZ": 3.1,
      "accelX": 9.81,
      "accelY": 0.1,
      "accelZ": -0.05
    }'
  ```
- [ ] Check response status: 200 OK
- [ ] Go to Firestore Console → sensor_readings
- [ ] Verify document was created with test data

### Test Fall Prediction Endpoint (Day 2)
- [ ] Send test data (low confidence):
  ```bash
  curl -X POST http://localhost:8000/predict-fall \
    -H "Content-Type: application/json" \
    -d '{
      "deviceId": "esp32_test_001",
      "userId": "test_user_123",
      "accelX": 9.81,
      "accelY": 0.1,
      "accelZ": 0.0,
      "gyroX": 5,
      "gyroY": 3,
      "gyroZ": 2
    }'
  ```
- [ ] Verify response: `"is_fall": false`, low confidence
- [ ] Send test data (high confidence):
  ```bash
  curl -X POST http://localhost:8000/predict-fall \
    -H "Content-Type: application/json" \
    -d '{
      "deviceId": "esp32_test_001",
      "userId": "test_user_123",
      "accelX": 35.0,
      "accelY": 28.0,
      "accelZ": 22.0,
      "gyroX": 280.0,
      "gyroY": 200.0,
      "gyroZ": 220.0
    }'
  ```
- [ ] Verify response: `"is_fall": true`, high confidence
- [ ] Go to Firestore → fall_alerts
- [ ] Verify alert document was created

### Test Firestore Integration (Day 2)
- [ ] Open Firebase Console
- [ ] Collections → sensor_readings
- [ ] See test documents
- [ ] Collections → fall_alerts
- [ ] See test alert documents
- [ ] Verify all fields match API response

---

## Phase 3: Flutter Testing 📱

### Test App Compilation (Day 2)
- [ ] Open project in VS Code/Android Studio
- [ ] Run `flutter pub get`
- [ ] Run `flutter analyze` - no critical errors
- [ ] Run `flutter build` - builds successfully
  ```bash
  flutter build apk    # For Android
  flutter build ios    # For iOS
  ```

### Test Flutter App (Day 2-3)
- [ ] Run app on emulator/device:
  ```bash
  flutter run
  ```
- [ ] No compilation errors
- [ ] App starts without crashes
- [ ] Home page loads
- [ ] See "Fall Alerts" card in overview

### Test Fall Alerts Page (Day 3)
- [ ] Tap "Fall Alerts" card
- [ ] Page opens without errors
- [ ] See empty state message (if no alerts)
- [ ] Firestore connection is working

### Test Real-time Updates (Day 3)
- [ ] Keep Fall Alerts page open
- [ ] Send test fall prediction from backend:
  ```bash
  curl -X POST http://localhost:8000/predict-fall \
    -H "Content-Type: application/json" \
    -d '{
      "deviceId": "esp32_test",
      "userId": "YOUR_USER_ID",
      "accelX": 35, "accelY": 28, "accelZ": 22,
      "gyroX": 280, "gyroY": 200, "gyroZ": 220
    }'
  ```
- [ ] Page updates in real-time with new alert
- [ ] Alert shows confidence and device info
- [ ] Alert has correct status color

### Test Alert Interactions (Day 3)
- [ ] Tap on alert card
- [ ] Details modal opens
- [ ] Shows full information
- [ ] "Acknowledge Alert" button visible
- [ ] Click Acknowledge
- [ ] Button changes state
- [ ] Close modal
- [ ] Alert status updated in list

### Test Filter Functionality (Day 3)
- [ ] Click filter icon
- [ ] List shows only unacknowledged alerts
- [ ] Click filter again
- [ ] Show all alerts

---

## Phase 4: ESP32 Configuration 🧬

### Prepare ESP32 Code (Day 3-4)
- [ ] Get ESP32 development board
- [ ] Install Arduino IDE
- [ ] Add ESP32 board to Arduino IDE
- [ ] Install required libraries:
  - [ ] WiFi.h (built-in)
  - [ ] HTTPClient.h (built-in)
  - [ ] ArduinoJson.h (install via Library Manager)
  - [ ] MPU6050.h (install for sensor)
- [ ] Open Arduino sketch

### Configure WiFi & Backend (Day 4)
- [ ] Update WiFi credentials in code:
  ```cpp
  const char* SSID = "YOUR_WIFI_SSID";
  const char* PASSWORD = "YOUR_WIFI_PASSWORD";
  ```
- [ ] Get backend server IP:
  ```bash
  ifconfig           # macOS/Linux
  ipconfig          # Windows
  ```
- [ ] Update server URL:
  ```cpp
  const char* SERVER_URL = "http://192.168.1.X:8000";
  ```
- [ ] Get user ID from Firebase:
  - [ ] Run Flutter app
  - [ ] Authenticate with Firebase
  - [ ] Get UID from Firebase Console
  - [ ] Update in ESP32 code:
    ```cpp
    const String USER_ID = "YOUR_FIREBASE_UID";
    ```
- [ ] Update device ID (unique for each ESP32):
  ```cpp
  const char* DEVICE_ID = "esp32_bedroom";
  ```

### Setup IMU Sensor (Day 4)
- [ ] Connect MPU6050 to ESP32:
  - [ ] VCC → 3V3
  - [ ] GND → GND
  - [ ] SCL → GPIO 22
  - [ ] SDA → GPIO 21
- [ ] Verify sensor connection:
  ```cpp
  mpu.testConnection()  // Should return true
  ```
- [ ] Calibrate sensor if needed

### Upload & Test (Day 4)
- [ ] Connect ESP32 via USB
- [ ] Select correct board and COM port
- [ ] Compile and upload code:
  - [ ] Arduino IDE: Sketch → Upload
  - [ ] VS Code: Click Upload
- [ ] Open Serial Monitor (115200 baud)
- [ ] See "WiFi connected" message
- [ ] See "MPU6050 initialized" message
- [ ] See sensor readings printing

### Test Data Transmission (Day 4)
- [ ] Move device around
- [ ] See accelerometer values changing
- [ ] See gyroscope values changing
- [ ] See POST requests in backend logs:
  ```
  192.168.1.X - "POST /predict-fall HTTP/1.1" 200
  ```
- [ ] Check Firestore for new documents
- [ ] See sensor_readings collection updating

### Test Fall Detection (Day 4)
- [ ] Shake ESP32 vigorously
- [ ] Watch serial output
- [ ] See high acceleration/gyro values
- [ ] Check backend logs for fall prediction
- [ ] See fall_alerts document created
- [ ] Check Flutter app for new alert
- [ ] See alert with high confidence

---

## Phase 5: Integration Testing 🔗

### End-to-End Flow (Day 5)
- [ ] ESP32 sends sensor data every 1 second
- [ ] Backend receives and stores in Firestore
- [ ] Backend runs ML prediction
- [ ] Falls detected and alerts created
- [ ] Flutter app shows real-time updates
- [ ] User can acknowledge alerts
- [ ] Alert status updates in Firestore

### Notification Testing (Day 5)
- [ ] Device has FCM enabled
- [ ] `users` collection has `fcmTokens` array
- [ ] Send test notification:
  - [ ] Backend creates fall alert
  - [ ] FCM sends notification to device
  - [ ] Device receives notification
  - [ ] Tap notification
  - [ ] Opens Fall Alerts page

### Performance Testing (Day 5)
- [ ] Measure response time < 200ms
- [ ] Real-time updates < 1 second
- [ ] No memory leaks in app
- [ ] Backend handles multiple devices
- [ ] Firestore queries efficient

### Edge Cases (Day 5)
- [ ] Test with no WiFi connection
- [ ] Test with backend offline
- [ ] Test with invalid sensor data
- [ ] Test with multiple devices
- [ ] Test delete functionality

---

## Phase 6: Optimization & Cleanup 🧹

### Code Cleanup (Day 5-6)
- [ ] Remove debug print statements
- [ ] Remove test data from Firestore
- [ ] Clean up temporary files
- [ ] Review error handling
- [ ] Add logging for debugging

### Security Review (Day 6)
- [ ] Firestore rules are restrictive
- [ ] Credentials not in git
- [ ] API endpoints validate input
- [ ] No sensitive data in logs
- [ ] WiFi uses WPA2 encryption

### Documentation (Day 6)
- [ ] All guides updated
- [ ] Code has comments
- [ ] README files accurate
- [ ] Architecture diagrams current

---

## Phase 7: Production Deployment 🚀

### Backend Deployment
- [ ] Choose platform (Cloud Run recommended)
- [ ] Set up environment variables
- [ ] Deploy backend
- [ ] Update Flutter API URL
- [ ] Test with production backend

### App Deployment
- [ ] Update API URLs
- [ ] Update version number
- [ ] Create signed APK/IPA
- [ ] Submit to stores

### Monitoring (Post-launch)
- [ ] Monitor Firestore usage
- [ ] Check error logs
- [ ] Track user feedback
- [ ] Monitor API performance

---

## Verification Summary

### Backend ✅
- [ ] Endpoints respond correctly
- [ ] Firestore documents created
- [ ] Notifications sent
- [ ] No errors in logs

### Flutter ✅
- [ ] App compiles
- [ ] Page displays alerts
- [ ] Real-time updates work
- [ ] Interactions work

### ESP32 ✅
- [ ] Connects to WiFi
- [ ] Sensor readings taken
- [ ] Data sent to backend
- [ ] Fall detection works

### Integration ✅
- [ ] End-to-end flow works
- [ ] All components connected
- [ ] No data loss
- [ ] Performance acceptable

---

## Timeline

```
Day 1: Setup (4 hours)
├─ Firebase configuration
└─ Backend environment setup

Day 2: Backend Testing (4 hours)
├─ Endpoint testing
└─ Firestore integration

Day 3: Flutter Testing (4 hours)
├─ App compilation
└─ UI testing

Day 4: ESP32 Configuration (4 hours)
├─ WiFi setup
└─ Sensor testing

Day 5: Integration Testing (4 hours)
├─ End-to-end flow
└─ Notification testing

Day 6: Optimization (2 hours)
├─ Code cleanup
└─ Security review
```

**Total: ~6 days (22 hours)**

---

## Sign-Off

When complete, check each box:

- [ ] All phases completed
- [ ] All tests passed
- [ ] Documentation reviewed
- [ ] Security verified
- [ ] Performance acceptable
- [ ] Ready for production

**Implementation Date**: ________________  
**Completed By**: ________________  
**Reviewed By**: ________________  

---

**Last Updated**: December 27, 2025  
**Version**: 1.0
