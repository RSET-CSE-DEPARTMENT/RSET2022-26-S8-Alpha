# Firebase Firestore Setup for IoT Fall Detection

## Collections to Create in Firebase Console

### 1. `sensor_readings` Collection
Store all sensor data from ESP32 devices.

**Fields:**
- `deviceId` (String) - ESP32 device identifier
- `userId` (String) - User ID from Firebase Auth
- `gyroX` (Number) - Gyroscope X axis reading
- `gyroY` (Number) - Gyroscope Y axis reading
- `gyroZ` (Number) - Gyroscope Z axis reading
- `accelX` (Number) - Accelerometer X axis reading
- `accelY` (Number) - Accelerometer Y axis reading
- `accelZ` (Number) - Accelerometer Z axis reading
- `timestamp` (Timestamp) - Reading timestamp

**Index:** Composite index on `userId` + `timestamp` (descending) for efficient queries

### 2. `fall_alerts` Collection
Store fall detection predictions and alerts.

**Fields:**
- `deviceId` (String) - ESP32 device identifier
- `userId` (String) - User ID from Firebase Auth
- `confidence` (Number) - Confidence score (0-1)
- `isFall` (Boolean) - Whether fall was detected
- `sensorDataId` (String) - Reference to sensor_readings document
- `timestamp` (Timestamp) - Alert timestamp
- `acknowledged` (Boolean) - Whether user acknowledged alert
- `acknowledgedAt` (Timestamp, optional) - When alert was acknowledged

**Index:** Composite index on `userId` + `timestamp` (descending) for efficient queries

### 3. `device_registrations` Collection (Optional)
Track registered ESP32 devices per user.

**Fields:**
- `userId` (String) - User ID from Firebase Auth
- `deviceId` (String) - Device identifier
- `deviceName` (String) - Human-readable name
- `model` (String) - Device model (e.g., "ESP32")
- `registeredAt` (Timestamp) - Registration date
- `isActive` (Boolean) - Device active status

### 4. `fall_detection_logs` Collection
Store notification delivery logs for fall alerts when the app receives or opens them.

**Fields:**
- `alertType` (String) - Always `fall`
- `deliveryEvent` (String) - `received_foreground`, `received_background`, `opened_from_background`, `opened_from_terminated`
- `messageId` (String, optional) - FCM message ID
- `title` (String) - Notification title
- `body` (String) - Notification body
- `data` (Map<String, dynamic>) - FCM data payload
- `sentTime` (Timestamp, optional) - FCM sent time
- `receivedAt` (Timestamp) - Server timestamp written at log creation
- `platform` (String) - App source (e.g., `flutter_app`)

**Index:** Single-field index on `receivedAt` (descending). Add `deliveryEvent` + `receivedAt` composite if needed.

### 5. `geofence_logs` Collection
Store notification delivery logs for geofence alerts when the app receives or opens them.

**Fields:**
- `alertType` (String) - Always `geofence`
- `deliveryEvent` (String) - `received_foreground`, `received_background`, `opened_from_background`, `opened_from_terminated`
- `messageId` (String, optional) - FCM message ID
- `title` (String) - Notification title
- `body` (String) - Notification body
- `data` (Map<String, dynamic>) - FCM data payload
- `sentTime` (Timestamp, optional) - FCM sent time
- `receivedAt` (Timestamp) - Server timestamp written at log creation
- `platform` (String) - App source (e.g., `flutter_app`)

**Index:** Single-field index on `receivedAt` (descending). Add `deliveryEvent` + `receivedAt` composite if needed.

## Firestore Security Rules

Add these rules to your Firestore in the Firebase Console:

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // Users can read/write their own sensor readings
    match /sensor_readings/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || request.auth.uid == request.resource.data.userId;
    }
    
    // Users can read/write their own fall alerts
    match /fall_alerts/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || request.auth.uid == request.resource.data.userId;
    }
    
    // Users can read device registrations
    match /device_registrations/{document=**} {
      allow read, write: if request.auth.uid == resource.data.userId || request.auth.uid == request.resource.data.userId;
    }

    // Notification receipt logs for fall alerts
    match /fall_detection_logs/{document=**} {
      allow read, write: if request.auth != null;
    }

    // Notification receipt logs for geofence alerts
    match /geofence_logs/{document=**} {
      allow read, write: if request.auth != null;
    }
  }
}
```

## Backend Configuration

The Python backend needs Firebase Admin SDK credentials:

1. Download service account JSON from Firebase Console (Project Settings → Service Accounts)
2. Save as `lib/backend/firebase_credentials.json` (do NOT commit to git)
3. Initialize Firebase Admin SDK in backend (see main.py updates)

## Environment Setup

Backend requires:
```
fastapi
uvicorn
firebase-admin
numpy
scikit-learn
python-dotenv
```

See updated `requirements.txt` for details.
