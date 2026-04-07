# Quick Start Guide - IoT Fall Detection

## 🚀 Get Started in 5 Steps

### Step 1: Firebase Setup (5 mins)
```
1. Go to Firebase Console → fiftypercent-e0f71
2. Firestore Database → Create Collections:
   - sensor_readings (for raw sensor data)
   - fall_alerts (for detected falls)
3. Copy Security Rules from FIREBASE_FIRESTORE_SETUP.md
4. Download service account JSON → save as lib/backend/firebase_credentials.json
```

### Step 2: Backend Setup (5 mins)
```bash
cd lib/backend
pip install -r requirements.txt
export FIREBASE_CREDENTIALS=./firebase_credentials.json
python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Step 3: Update Flutter
```dart
// In lib/services/api_service.dart
static const String baseUrl = 'http://192.168.1.X:8000';  // Your IP
```

### Step 4: Configure ESP32
```cpp
// In Arduino code
const char* SSID = "Your WiFi";
const char* PASSWORD = "Your Password";
const String USER_ID = "firebase_uid";  // Get from app
const char* SERVER_URL = "http://192.168.1.X:8000";
```

### Step 5: Test
```bash
# Send sensor data
curl -X POST http://localhost:8000/predict-fall \
  -H "Content-Type: application/json" \
  -d '{"deviceId":"esp32_001","userId":"test","accelX":30,"accelY":25,"accelZ":20,"gyroX":250,"gyroY":180,"gyroZ":200}'

# Check Firestore console for fall_alerts
```

---

## 📊 Architecture at a Glance

```
ESP32 (accel + gyro) 
  ↓ HTTP POST
Backend (FastAPI) 
  ├─ Stores in Firestore
  └─ Runs ML model
  ↓
Firestore (sensor_readings, fall_alerts)
  ↓ FCM
App (Real-time alerts)
```

---

## 🔑 Key Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/sensor-readings` | POST | Store raw sensor data |
| `/predict-fall` | POST | Run ML & create alert |

## 📱 Flutter Methods

| Method | Purpose |
|--------|---------|
| `sendSensorReadings()` | Send to `/sensor-readings` |
| `predictFallSingle()` | Send to `/predict-fall` |
| `getFallAlerts()` | Get from Firestore |
| `acknowledgeFallAlert()` | Mark as acknowledged |
| `streamFallAlerts()` | Real-time updates |

---

## 🎯 ML Model Logic

```
IF accel_magnitude < 2.0 m/s²
  → Free fall detected (0.3x weight)
  
IF accel_magnitude > 20 m/s²
  → Impact detected (0.5x weight)
  
IF gyro_magnitude > 200 deg/s
  → Unusual rotation (0.2x weight)
  
IF total_confidence > 0.5
  → FALL DETECTED ⚠️
  → Create alert in Firestore
  → Send FCM notification
```

---

## 📁 New Files Created

```
lib/
  ├─ backend/
  │  ├─ fall_detection_model.py (NEW)
  │  ├─ main.py (UPDATED)
  │  ├─ notifications.py (UPDATED)
  │  └─ requirements.txt (UPDATED)
  ├─ models/
  │  └─ fall_alert_model.dart (NEW)
  ├─ services/
  │  └─ api_service.dart (UPDATED)
  ├─ fall_alerts_page.dart (NEW)
  └─ home_page.dart (UPDATED)

FIREBASE_FIRESTORE_SETUP.md (NEW)
IoT_ML_IMPLEMENTATION_GUIDE.md (NEW)
IOT_ML_CHANGES_SUMMARY.md (NEW)
```

---

## 🧪 Test Data (High Fall Confidence)

```json
{
  "deviceId": "esp32_test",
  "userId": "test_user",
  "accelX": 35.0,
  "accelY": 28.0,
  "accelZ": 22.0,
  "gyroX": 280.0,
  "gyroY": 200.0,
  "gyroZ": 220.0
}
```

Expected response:
```json
{
  "status": "success",
  "prediction": {
    "is_fall": true,
    "confidence": 0.92,
    "reasoning": ["Impact detected", "High rotation detected"]
  }
}
```

---

## ❌ Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| `firebase_admin not found` | `pip install firebase-admin` |
| Connection refused | Check backend is running on correct port |
| Firestore empty | Check Firebase credentials are valid |
| No notifications | Verify `users` collection has `fcmTokens` array |
| ESP32 won't connect | Check WiFi SSID/password and backend IP |

---

## 📚 Detailed Guides

- **Full Setup**: `IoT_ML_IMPLEMENTATION_GUIDE.md`
- **Firebase Config**: `FIREBASE_FIRESTORE_SETUP.md`
- **All Changes**: `IOT_ML_CHANGES_SUMMARY.md`

---

## ✅ Checklist Before Going Live

- [ ] Firebase collections created
- [ ] Firestore rules set
- [ ] Backend running and tested
- [ ] Flutter API URL updated
- [ ] ESP32 WiFi credentials set
- [ ] Device IDs are unique
- [ ] User IDs from Firebase Auth
- [ ] Notification permissions granted
- [ ] Tested end-to-end flow
- [ ] API credentials in .gitignore

---

**Ready to test?** Start with Step 1 above!
