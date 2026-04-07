from firebase_admin import messaging, firestore
from datetime import datetime
from typing import Optional


def send_alert(token, title="Alert", body="Notification"):
    """Send FCM notification for geofence alerts."""
    try:
        message = messaging.Message(
            notification=messaging.Notification(
                title=title,
                body=body,
            ),
            token=token,
        )
        messaging.send(message)
        return True
    except Exception as e:
        print(f"Error sending notification: {e}")
        return False


def send_fall_notification(user_id: str, device_id: str, confidence: float):
    """
    Send FCM notification when fall is detected.
    Gets FCM tokens from Firestore and sends notification to all devices.
    """
    try:
        db = firestore.client()
        
        # Query user's devices to get FCM tokens
        user_doc = db.collection("users").document(user_id).get()
        if not user_doc.exists:
            print(f"User {user_id} not found")
            return False
        
        fcm_tokens = user_doc.get("fcmTokens", [])
        if not fcm_tokens:
            print(f"No FCM tokens found for user {user_id}")
            return False
        
        # Send notification to all user devices
        success_count = 0
        for token in fcm_tokens:
            try:
                message = messaging.Message(
                    notification=messaging.Notification(
                        title="⚠️ FALL DETECTED",
                        body=f"Fall detected on {device_id} (Confidence: {confidence*100:.1f}%)",
                    ),
                    data={
                        "type": "fall_alert",
                        "device_id": device_id,
                        "confidence": str(confidence),
                        "timestamp": datetime.now().isoformat()
                    },
                    token=token,
                )
                messaging.send(message)
                success_count += 1
            except Exception as e:
                print(f"Error sending to token {token}: {e}")
        
        print(f"Fall notification sent to {success_count}/{len(fcm_tokens)} devices")
        return success_count > 0
    
    except Exception as e:
        print(f"Error in send_fall_notification: {e}")
        return False
