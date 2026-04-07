const functions = require("firebase-functions");
const admin = require("firebase-admin");

admin.initializeApp();

exports.sendAlertNotification = functions.database
  .ref("/alerts/{alertId}")
  .onCreate(async (snapshot, context) => {

    const alert = snapshot.val();

    if (!alert || !alert.type || !alert.message) {
      console.log("⚠️ Invalid alert payload");
      return null;
    }

    const payload = {
      notification: {
        title: alert.type === "FALL"
          ? "🚨 Fall Detected"
          : "📍 Geofence Alert",
        body: alert.message,
      },
      topic: "alerts",
    };

    await admin.messaging().send(payload);

    console.log("✅ Notification sent for:", alert.type);
    return null;
  });
