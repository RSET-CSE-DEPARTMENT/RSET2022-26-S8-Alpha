import json
import os
from datetime import datetime
from typing import List, Dict, Optional
import firebase_admin
from firebase_admin import credentials, firestore, db, messaging
from fall_detection_model import FallDetectionModel
from notifications import send_fall_notification

# ============================================
# Firebase Admin SDK Initialization
# ============================================
try:
    # Load Firebase credentials from environment or file
    cred_path = os.getenv('FIREBASE_CREDENTIALS', './firebase_credentials.json')
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        firebase_admin.initialize_app(cred)
    # Otherwise, use Application Default Credentials
except Exception as e:
    print(f"Firebase initialization error: {e}")

db_firestore = firestore.client()
fall_model = FallDetectionModel()

# ============================================
# IoT Sensor Data Endpoints
# ============================================

@app.post("/sensor-readings")
def receive_sensor_readings(data: dict):
    """
    Receive sensor readings from ESP32 device.
    
    Expected payload:
    {
        "deviceId": "esp32_001",
        "userId": "user_uuid",
        "gyroX": float,
        "gyroY": float,
        "gyroZ": float,
        "accelX": float,
        "accelY": float,
        "accelZ": float
    }
    """
    try:
        device_id = data.get("deviceId")
        user_id = data.get("userId")
        
        if not device_id or not user_id:
            return {"error": "Missing deviceId or userId"}, 400
        
        # Store sensor reading in Firestore
        reading_ref = db_firestore.collection("sensor_readings").document()
        reading_ref.set({
            "deviceId": device_id,
            "userId": user_id,
            "gyroX": data.get("gyroX", 0.0),
            "gyroY": data.get("gyroY", 0.0),
            "gyroZ": data.get("gyroZ", 0.0),
            "accelX": data.get("accelX", 0.0),
            "accelY": data.get("accelY", 0.0),
            "accelZ": data.get("accelZ", 0.0),
            "timestamp": datetime.now(),
        })
        
        return {
            "status": "success",
            "reading_id": reading_ref.id,
            "message": "Sensor reading stored"
        }
    
    except Exception as e:
        print(f"Error storing sensor reading: {e}")
        return {"error": str(e)}, 500


@app.post("/predict-fall")
def predict_fall(data: dict):
    """
    Predict if a fall is occurring based on sensor readings.
    Can accept single reading or batch of recent readings.
    
    Expected payload for single:
    {
        "deviceId": "esp32_001",
        "userId": "user_uuid",
        "accelX": float,
        "accelY": float,
        "accelZ": float,
        "gyroX": float,
        "gyroY": float,
        "gyroZ": float
    }
    
    Expected payload for batch:
    {
        "deviceId": "esp32_001",
        "userId": "user_uuid",
        "readings": [
            {"accelX": ..., "accelY": ..., ...},
            ...
        ]
    }
    """
    try:
        device_id = data.get("deviceId")
        user_id = data.get("userId")
        
        if not device_id or not user_id:
            return {"error": "Missing deviceId or userId"}, 400
        
        # Check if batch or single reading
        if "readings" in data:
            # Batch processing
            readings = data.get("readings", [])
            prediction = fall_model.predict_batch(readings)
        else:
            # Single reading
            prediction = fall_model.predict(
                accel_x=data.get("accelX", 0.0),
                accel_y=data.get("accelY", 0.0),
                accel_z=data.get("accelZ", 0.0),
                gyro_x=data.get("gyroX", 0.0),
                gyro_y=data.get("gyroY", 0.0),
                gyro_z=data.get("gyroZ", 0.0)
            )
        
        # Store prediction as fall alert if fall detected
        if prediction["is_fall"]:
            alert_ref = db_firestore.collection("fall_alerts").document()
            alert_ref.set({
                "deviceId": device_id,
                "userId": user_id,
                "confidence": prediction["confidence"],
                "isFall": True,
                "timestamp": datetime.now(),
                "acknowledged": False,
                "reasoning": prediction.get("reasoning", [])
            })
            
            # Send FCM notification
            send_fall_notification(user_id, device_id, prediction["confidence"])
            
            prediction["alert_id"] = alert_ref.id
        
        return {
            "status": "success",
            "prediction": prediction
        }
    
    except Exception as e:
        print(f"Error predicting fall: {e}")
        return {"error": str(e)}, 500


@app.post("/location")
def receive_location(data: dict):
    global LATEST_LOCATION, FENCE_STATES, GEOFENCES

    lat = data["lat"]
    lng = data["lng"]

    LATEST_LOCATION["lat"] = lat
    LATEST_LOCATION["lng"] = lng

    alerts = []

    for fence_id, fence in GEOFENCES.items():
        # Decide which check to use
        if fence["type"] == "circle":
            status = check_circle(lat, lng, fence)
        else:
            status = check_polygon(lat, lng, fence)

        previous = FENCE_STATES.get(fence_id, "OUTSIDE")

        # ENTER
        if previous == "OUTSIDE" and status == "INSIDE":
            send_alert(
                FCM_TOKEN,
                title="Entered Geofence",
                body=f"Entered {fence_id}"
            )
            alerts.append({"fence": fence_id, "event": "ENTER"})

        # EXIT
        if previous == "INSIDE" and status == "OUTSIDE":
            send_alert(
                FCM_TOKEN,
                title="Exited Geofence",
                body=f"Exited {fence_id}"
            )
            alerts.append({"fence": fence_id, "event": "EXIT"})

        # Update state
        FENCE_STATES[fence_id] = status

    return {
        "location": LATEST_LOCATION,
        "alerts": alerts,
        "states": FENCE_STATES
    }
