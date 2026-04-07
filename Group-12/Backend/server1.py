import firebase_admin
from firebase_admin import credentials, messaging, firestore
from flask import Flask, request, jsonify
import joblib
import numpy as np
import math
import os
from threading import Thread

# ================= FIREBASE =================
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

app = Flask(__name__)
db = firestore.client()

# ================= FALL DETECTION (UNCHANGED) =================
model = joblib.load("fall_model (1).pkl")
scaler = joblib.load("scaler (1).pkl")
THRESHOLD = 0.35

FCM_TOKENS = set()
FCM_TOKENS_BY_USER = {}
ACTIVE_USER_ID = None
TOKEN_COLLECTION = "fcm_tokens"


def _remember_token(user_id, token):
    FCM_TOKENS.add(token)
    if user_id not in FCM_TOKENS_BY_USER:
        FCM_TOKENS_BY_USER[user_id] = set()
    FCM_TOKENS_BY_USER[user_id].add(token)


def _persist_token(user_id, token, platform):
    try:
        db.collection(TOKEN_COLLECTION).document(token).set({
            "token": token,
            "userId": user_id,
            "platform": platform,
            "updatedAt": firestore.SERVER_TIMESTAMP,
        }, merge=True)
        print(f"📲 Token persisted for user={user_id}", flush=True)
    except Exception as e:
        print(f"❌ Failed to persist token for user={user_id}: {e}", flush=True)


def list_known_speakers():
    embed_dir = "data/embeddings"
    if not os.path.isdir(embed_dir):
        return []

    names = []
    for file_name in os.listdir(embed_dir):
        if file_name.endswith(".npy"):
            names.append(file_name.replace(".npy", ""))
    return sorted(names)

# ================== FCM ==============cd====


@app.route("/register_token", methods=["POST"])
def register_token():
    payload = request.get_json(silent=True) or {}
    token = payload.get("token")
    user_id = payload.get("userId")
    platform = payload.get("platform", "unknown")
    if not token or not user_id:
        return jsonify({"error": "token and userId are required"}), 400

    token_preview = f"{token[:12]}...{token[-8:]}" if len(token) > 20 else token
    print(
        f"📥 /register_token received for user={user_id} "
        f"platform={platform} token={token_preview}",
        flush=True,
    )

    _remember_token(user_id, token)
    Thread(
        target=_persist_token,
        args=(user_id, token, platform),
        daemon=True,
    ).start()

    print(f"📡 Token accepted for user={user_id}", flush=True)
    return jsonify({"status": "ok", "userId": user_id}), 200


@app.route("/known-speakers", methods=["GET"])
def known_speakers():
    return jsonify({"speakers": list_known_speakers()})


def _get_tokens_for_user(user_id):
    tokens = set(FCM_TOKENS_BY_USER.get(user_id, set()))

    try:
        docs = db.collection(TOKEN_COLLECTION).where(
            "userId", "==", user_id).stream()
        tokens.update(doc.id for doc in docs)
    except Exception as e:
        print(f"⚠️ Firestore token lookup failed for user={user_id}: {e}", flush=True)

    return list(tokens)


def send_push_notification(title, body, alert_type=None, extra_data=None, user_id=None):
    if user_id:
        target_tokens = _get_tokens_for_user(user_id)
    else:
        # Safe fallback to previous behavior when user context is missing.
        target_tokens = list(FCM_TOKENS)

    if not target_tokens:
        print(f"⚠️ No FCM tokens registered for user={user_id}", flush=True)
        return

    payload = {}
    if alert_type:
        payload["alertType"] = str(alert_type)
    if user_id:
        payload["userId"] = str(user_id)
    if extra_data:
        for key, value in extra_data.items():
            if value is not None:
                payload[str(key)] = str(value)

    for token in target_tokens:
        try:
            msg = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=payload if payload else None,
                token=token,
            )
            messaging.send(msg)
            print("📤 Push sent:", title, flush=True)
        except Exception as e:
            print("❌ FCM ERROR:", e, flush=True)

# ================= FALL API =================


@app.route("/predict", methods=["POST"])
def predict():
    data = request.json
    user_id = data.get("userId")

    acc_mean = data.get("acc_mean")
    acc_std = data.get("acc_std")
    gyro_mean = data.get("gyro_mean")
    gyro_std = data.get("gyro_std")

    if None in (acc_mean, acc_std, gyro_mean, gyro_std):
        return jsonify({"error": "Invalid input"}), 400

    X = np.array([[acc_mean, acc_std, gyro_mean, gyro_std]])
    X_scaled = scaler.transform(X)

    prob = model.predict_proba(X_scaled)[0][1]
    prediction = "FALL" if prob > THRESHOLD else "NO_FALL"

    print(f"🧠 Fall check → {prediction} ({prob:.2f})", flush=True)

    if prediction == "FALL":
        send_push_notification(
            "🚨 Fall Detected",
            "Possible fall detected. Please check immediately.",
            alert_type="fall",
            user_id=user_id,
        )

    return jsonify({
        "prediction": prediction,
        "probability": float(prob)
    })

# =================================================================
# ================= GPS + GEOFENCE ===============================
# =================================================================


GEOFENCES = []
FENCE_STATUS = {}
LATEST_LOCATION = None


def distance_meters(lat1, lon1, lat2, lon2):
    R = 6371000
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(lat1)) *
         math.cos(math.radians(lat2)) *
         math.sin(dlon/2)**2)
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def point_in_polygon(lat, lon, polygon):
    x, y = lon, lat
    inside = False
    n = len(polygon)

    p1x, p1y = polygon[0]["lng"], polygon[0]["lat"]

    for i in range(n + 1):
        p2x, p2y = polygon[i % n]["lng"], polygon[i % n]["lat"]

        if min(p1y, p2y) < y <= max(p1y, p2y):
            if x <= max(p1x, p2x):
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y + 1e-9) + p1x
                if p1x == p2x or x <= xinters:
                    inside = not inside

        p1x, p1y = p2x, p2y

    return inside

# ================== GEOFENCE CRUD ==================


@app.route("/geofences", methods=["POST"])
def save_geofence():
    GEOFENCES.clear()
    GEOFENCES.append(request.json)
    print("🟢 Geofence saved:", request.json, flush=True)
    return jsonify({"status": "ok"})


@app.route("/geofences", methods=["GET"])
def get_geofences():
    return jsonify(GEOFENCES)

# ================== GPS ==================


@app.route("/gps", methods=["POST"])
def receive_gps():
    global LATEST_LOCATION, ACTIVE_USER_ID

    data = request.json
    lat = data.get("lat")
    lon = data.get("lon")
    user_id = data.get("userId")
    if user_id:
        ACTIVE_USER_ID = user_id

    if lat is None or lon is None:
        return jsonify({"error": "Invalid GPS"}), 400

    LATEST_LOCATION = {"lat": lat, "lng": lon}
    print(f"📍 GPS received → {lat}, {lon}", flush=True)

    check_geofence(lat, lon)
    return jsonify({"status": "ok"})


@app.route("/gps/latest", methods=["GET"])
def get_latest_gps():
    if LATEST_LOCATION is None:
        return jsonify({"status": "no_data"}), 200

    return jsonify({
        "lat": LATEST_LOCATION["lat"],
        "lon": LATEST_LOCATION["lng"]
    }), 200

# ================== GEOFENCE CHECK ==================


def check_geofence(lat, lon):
    # 🔁 ALWAYS print ESP values
    print(
        f"📡 ESP UPDATE → lat={lat}, lon={lon}",
        flush=True
    )

    if not GEOFENCES:
        print("⚠️ No geofence defined yet", flush=True)
        return

    for idx, fence in enumerate(GEOFENCES):
        inside = True

        # ---------- CIRCLE ----------
        if fence["type"] == "circle":
            d = distance_meters(
                lat, lon,
                fence["lat"], fence["lng"]
            )
            inside = d <= fence["radius"]

            print(
                f"🟢 Fence Check → Distance={d:.2f}m | "
                f"Radius={fence['radius']}m | "
                f"Status={'INSIDE' if inside else 'OUTSIDE'}",
                flush=True
            )

        # ---------- POLYGON ----------
        elif fence["type"] == "polygon":
            inside = point_in_polygon(lat, lon, fence["points"])

            print(
                f"🟢 Fence Check → Polygon | "
                f"Status={'INSIDE' if inside else 'OUTSIDE'}",
                flush=True
            )

        prev = FENCE_STATUS.get(idx)
        FENCE_STATUS[idx] = inside

        # 🚨 Notify ONLY when crossing
        if prev is not None and prev != inside:
            if not inside:
                send_push_notification(
                    "📍 Geofence Alert",
                    "Patient exited safe zone",
                    alert_type="geofence",
                    extra_data={"status": "outside"},
                    user_id=ACTIVE_USER_ID,
                )
            else:
                send_push_notification(
                    "✅ Geofence Update",
                    "Patient returned inside safe zone",
                    alert_type="geofence",
                    extra_data={"status": "inside"},
                    user_id=ACTIVE_USER_ID,
                )


# ================= MAIN =================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
