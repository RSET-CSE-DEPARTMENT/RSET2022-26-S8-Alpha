# System Architecture Diagrams

## Complete Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            IoT Fall Detection System                         │
└─────────────────────────────────────────────────────────────────────────────┘

                                    ┌──────────────┐
                                    │   ESP32 IoT  │
                                    │   Device     │
                                    └──────┬───────┘
                                           │
                         ┌─────────────────┼─────────────────┐
                         │                 │                 │
                    [ACCEL]          [GYRO]          [TEMP/HUMIDITY]
                    (X,Y,Z)          (X,Y,Z)         (optional)
                         │                 │                 │
                         └─────────────────┼─────────────────┘
                                           │
                    ┌──────────────────────┼──────────────────────┐
                    │   WiFi Connection    │  (encrypted)         │
                    └──────────────────────┼──────────────────────┘
                                           │ HTTP POST (JSON)
                                           ▼
                    ┌─────────────────────────────────────────────┐
                    │        FastAPI Backend (Python)             │
                    │              Port 8000                       │
                    ├─────────────────────────────────────────────┤
                    │  POST /sensor-readings                       │
                    │    └─ Store raw data → Firestore            │
                    │                                              │
                    │  POST /predict-fall                          │
                    │    ├─ Load ML Model                          │
                    │    ├─ Process sensor data                    │
                    │    ├─ Calculate confidence                   │
                    │    ├─ If is_fall=true:                       │
                    │    │  ├─ Create alert in Firestore          │
                    │    │  └─ Send FCM notification              │
                    │    └─ Return prediction                      │
                    └─────────────────────────────────────────────┘
                         │                    │
                    ┌────▼──────┐      ┌──────▼────────┐
                    │ Firestore  │      │ FCM Service    │
                    │ Collections│      │                │
                    ├────────────┤      └──────┬─────────┘
                    │            │             │
                    │ sensor_    │             │ Notification
                    │ readings   │             │ Payload
                    │            │             │
                    │ fall_      │             │
                    │ alerts     │             │
                    │            │             │
                    │ device_    │             │
                    │ registrations          │
                    └────┬───────┘             │
                         │                    │
                         │   Real-time        │
                         │   stream           │
                         └────────┬───────────┘
                                  │
                    ┌─────────────▼─────────────┐
                    │   Flutter App             │
                    │  (iOS/Android)            │
                    ├───────────────────────────┤
                    │ • Receives notification   │
                    │ • Displays alert card     │
                    │ • Real-time list updates  │
                    │ • User acknowledges       │
                    │ • Updates Firestore       │
                    └───────────────────────────┘
```

---

## ML Model Decision Tree

```
                    Sensor Data Received
                            │
                ┌───────────┬┴┬───────────┐
                │           │ │           │
           accelX      accelY Z  gyroX/Y/Z
                │           │ │           │
                └───────────┬┴┬───────────┘
                            ▼
                  Calculate Magnitudes
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
         ▼                  ▼                  ▼
    accel_mag          gyro_mag           gyro_change
         │                  │                  │
         │                  │                  │
         ├─ < 2.0 m/s²?  ├─ > 200 deg/s? ├─ Rapid accel?
         │  └─ FREE FALL  │  └─ ROTATION   │  └─ IMPACT
         │    (0.3x)      │    (0.2x)      │    (0.5x)
         │                │                │
         └────────────────┼────────────────┘
                          │
                    Sum Weighted Scores
                          │
                          ▼
                   Total Confidence
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼ > 0.5                 ▼ ≤ 0.5
         FALL DETECTED            NO FALL
              │                       │
              ├─ Create Alert ────────┼─ Return 0.0
              ├─ Send FCM ────────────┤
              ├─ Store in DB          │
              └─ Return conf. ────────┘
```

---

## Database Schema

```
Firestore
│
├─ sensor_readings/
│  └─ {auto-id}
│     ├─ deviceId: string
│     ├─ userId: string
│     ├─ gyroX: number
│     ├─ gyroY: number
│     ├─ gyroZ: number
│     ├─ accelX: number
│     ├─ accelY: number
│     ├─ accelZ: number
│     └─ timestamp: datetime
│
├─ fall_alerts/
│  └─ {auto-id}
│     ├─ deviceId: string
│     ├─ userId: string
│     ├─ confidence: number (0-1)
│     ├─ isFall: boolean
│     ├─ timestamp: datetime
│     ├─ acknowledged: boolean
│     ├─ acknowledgedAt: datetime (optional)
│     └─ reasoning: array[string]
│
└─ device_registrations/
   └─ {auto-id}
      ├─ userId: string
      ├─ deviceId: string
      ├─ deviceName: string
      ├─ model: string
      ├─ registeredAt: datetime
      └─ isActive: boolean
```

---

## API Request/Response Flow

```
┌────────────────────────────────────────────────────────────────┐
│ REQUEST: POST /predict-fall                                    │
├────────────────────────────────────────────────────────────────┤
│ {                                                              │
│   "deviceId": "esp32_001",                                    │
│   "userId": "user_firebase_uid",                              │
│   "accelX": 30.5,                                             │
│   "accelY": 25.2,                                             │
│   "accelZ": 20.1,                                             │
│   "gyroX": 250.3,                                             │
│   "gyroY": 180.7,                                             │
│   "gyroZ": 200.5                                              │
│ }                                                              │
└────────────────────────────────────────────────────────────────┘
                              │
                    Backend Processing:
                    1. Calculate magnitudes
                    2. Run ML model
                    3. Check thresholds
                    4. Calculate confidence
                    5. If is_fall:
                       - Save to Firestore
                       - Send FCM notification
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│ RESPONSE: 200 OK                                               │
├────────────────────────────────────────────────────────────────┤
│ {                                                              │
│   "status": "success",                                         │
│   "prediction": {                                              │
│     "is_fall": true,                                           │
│     "confidence": 0.87,                                        │
│     "reasoning": [                                             │
│       "Impact detected (accel_mag: 42.50)",                   │
│       "High rotation detected (gyro_mag: 380.20)"             │
│     ],                                                         │
│     "accel_mag": 42.50,                                        │
│     "gyro_mag": 380.20                                         │
│   },                                                           │
│   "alert_id": "firestore_document_id"                          │
│ }                                                              │
└────────────────────────────────────────────────────────────────┘
```

---

## Flutter App Navigation

```
┌─────────────────────┐
│   Home Page         │
├─────────────────────┤
│ • Profile (card)    │
│ • GPS (card)        │
│ • Schedule (card)   │
│ • Fall Alerts (card)│ ← NEW
│                     │
│ • Events section    │
│   - Medications     │
│   - Appointments    │
└──────────┬──────────┘
           │ onTap
           ▼
┌──────────────────────────────────────────┐
│   FallAlertsPage                         │
├──────────────────────────────────────────┤
│ AppBar:                                  │
│  • Title: "Fall Alerts"                  │
│  • Filter button (unacknowledged)        │
│                                          │
│ Body:                                    │
│  • StreamBuilder (real-time updates)     │
│  • FallAlertCard (for each alert)        │
│     ├─ Status icon                       │
│     ├─ Confidence badge                  │
│     ├─ Device ID                         │
│     ├─ Time ago                          │
│     └─ Action button                     │
│        (Acknowledge or Delete)           │
│                                          │
│ Modal (onTap alert):                     │
│  • Full details                          │
│  • Reasoning list                        │
│  • Acknowledge button                    │
└──────────────────────────────────────────┘
```

---

## Deployment Architecture (Optional)

```
                    ┌──────────────────┐
                    │   Google Cloud   │
                    │   Platform       │
                    └────────┬─────────┘
                             │
         ┌───────────────────┼───────────────────┐
         │                   │                   │
         ▼                   ▼                   ▼
    ┌─────────┐          ┌──────────┐      ┌──────────┐
    │Cloud Run│          │Firestore │      │  Cloud   │
    │(Backend)│          │(Database)│      │Messaging │
    └────┬────┘          └─────┬────┘      └────┬─────┘
         │                     │               │
         └─────────────────────┼───────────────┘
                               │
                    ┌──────────▼──────────┐
                    │   Firebase Auth    │
                    │   (User management)│
                    └────────────────────┘
                               │
                ┌──────────────┴──────────────┐
                │                            │
                ▼                            ▼
          ┌──────────┐              ┌──────────┐
          │   iOS    │              │ Android  │
          │   App    │              │   App    │
          └──────────┘              └──────────┘
```

---

## Confidence Score Color Map

```
        Confidence Level Visualization

Confidence Range:    Color:        Icon:         Action:
─────────────────────────────────────────────────────────
0.0 - 0.3           🟡 Yellow      ✓ OK          Dismiss
0.3 - 0.6           🟠 Orange      ⚠️ Warning    Review
0.6 - 0.8           🔴 Red         🚨 Alert      Acknowledge
0.8 - 1.0           🔴 Dark Red    ⚠️ CRITICAL   Immediate
```

---

## File Structure

```
my_app/
├─ lib/
│  ├─ backend/
│  │  ├─ fall_detection_model.py       (NEW - ML Model)
│  │  ├─ main.py                       (UPDATED - Endpoints)
│  │  ├─ notifications.py              (UPDATED - FCM)
│  │  ├─ geofence.py
│  │  └─ requirements.txt              (UPDATED - Dependencies)
│  │
│  ├─ models/
│  │  ├─ fall_alert_model.dart         (NEW - Data Model)
│  │  ├─ device_location.dart
│  │  └─ fall_alert_model.dart
│  │
│  ├─ services/
│  │  ├─ api_service.dart              (UPDATED - API Methods)
│  │  ├─ database_service.dart
│  │  └─ notification_service.dart
│  │
│  ├─ fall_alerts_page.dart            (NEW - UI Page)
│  ├─ home_page.dart                   (UPDATED - Navigation)
│  ├─ main.dart
│  └─ ... other files
│
├─ FIREBASE_FIRESTORE_SETUP.md         (NEW - Config Guide)
├─ IoT_ML_IMPLEMENTATION_GUIDE.md       (NEW - Full Guide)
├─ IOT_ML_CHANGES_SUMMARY.md            (NEW - Summary)
├─ QUICK_START_IOT_ML.md                (NEW - Quick Start)
└─ ARCHITECTURE_DIAGRAMS.md             (THIS FILE)
```

---

**Last Updated**: December 27, 2025  
**System Version**: 1.0  
**Status**: Ready for Development & Testing
