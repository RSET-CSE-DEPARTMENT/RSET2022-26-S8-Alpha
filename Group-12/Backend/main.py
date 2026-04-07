import asyncio
import websockets
import json
import numpy as np
import joblib
import firebase_admin
import os
import tempfile
import shutil
from flask import Flask, request, jsonify
from firebase_admin import credentials, messaging
from resemblyzer import VoiceEncoder, preprocess_wav
from threading import Thread
import concurrent.futures
from datetime import datetime
from firebase_admin import firestore
import soundfile as sf
from voice import DEFAULT_TARGET_WINDOWS as VOICE_ENROLL_TARGET_WINDOWS
from voice import DEFAULT_WINDOW_SECONDS as VOICE_ENROLL_WINDOW_SECONDS

# ================= FIREBASE =================
cred = credentials.Certificate("serviceAccountKey.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

# ================= FLASK =================
app = Flask(__name__)
FCM_TOKENS = set()
FCM_TOKENS_BY_USER = {}
CURRENT_USER_ID = None
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


def _get_tokens_for_user(user_id):
    tokens = set(FCM_TOKENS_BY_USER.get(user_id, set()))

    try:
        docs = db.collection(TOKEN_COLLECTION).where(
            "userId", "==", user_id).stream()
        tokens.update(doc.id for doc in docs)
    except Exception as e:
        print(f"⚠️ Firestore token lookup failed for user={user_id}: {e}")

    return list(tokens)


def send_push(title, body, alert_type=None, extra_data=None, user_id=None):
    if user_id:
        tokens = _get_tokens_for_user(user_id)
    else:
        # Safe fallback to previous behavior when user context is missing.
        tokens = list(FCM_TOKENS)

    if not tokens:
        print(f"⚠️ No FCM tokens found for user={user_id}")
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

    for token in tokens:
        try:
            msg = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                ),
                data=payload if payload else None,
                token=token,
            )
            messaging.send(msg)
            print("📤 Push sent:", title)
        except Exception as e:
            print("❌ FCM ERROR:", e)


# ================= FALL MODEL =================
model = joblib.load("fall_model (1).pkl")
scaler = joblib.load("scaler (1).pkl")
THRESHOLD = 0.35

# ================= VOICE SETTINGS =================
UNKNOWN_THRESHOLD = 0.72
STABLE_REQUIRED = 3

# ================= VOICE ENGINE =================
encoder = VoiceEncoder()
executor = concurrent.futures.ThreadPoolExecutor(max_workers=2)

frame_queue = asyncio.Queue()
audio_buffer = np.array([], dtype=np.int16)
iot_enrollment_audio_buffer = []

WINDOW_SECONDS = 5
STEP_SECONDS = 2
SAMPLE_RATE = 16000
WINDOW_SAMPLES = WINDOW_SECONDS * SAMPLE_RATE
STEP_SAMPLES = STEP_SECONDS * SAMPLE_RATE

EMBED_DIR = "data/embeddings"
ENROLL_DIR = "data/enroll"
ENROLLMENT_WINDOW_SECONDS = VOICE_ENROLL_WINDOW_SECONDS
ENROLLMENT_TARGET_WINDOWS = VOICE_ENROLL_TARGET_WINDOWS
ENROLLMENT_TARGET_SAMPLES = ENROLLMENT_WINDOW_SECONDS * SAMPLE_RATE

# ================= LOAD EMBEDDINGS =================


def _sanitize_member_name(name):
    cleaned = (name or "").strip().replace("/", "_").replace("\\", "_")
    return cleaned


def _normalize_member_key(name):
    lowered = (name or "").strip().lower()
    normalized = []
    previous_was_dash = False

    for char in lowered:
        if char.isalnum():
            normalized.append(char)
            previous_was_dash = False
        elif not previous_was_dash:
            normalized.append("-")
            previous_was_dash = True

    return "".join(normalized).strip("-")


def _user_embed_dir(user_id):
    if not user_id:
        return None
    return os.path.join(EMBED_DIR, user_id)


def _enroll_audio_dir(user_id, member_name):
    if user_id:
        return os.path.join(ENROLL_DIR, user_id, member_name)
    return os.path.join(ENROLL_DIR, member_name)


def _save_embedding_outputs(user_id, member_name, embedding):
    os.makedirs(EMBED_DIR, exist_ok=True)

    saved_paths = []
    shared_path = os.path.join(EMBED_DIR, f"{member_name}.npy")
    np.save(shared_path, embedding)
    saved_paths.append(shared_path)

    user_dir = _user_embed_dir(user_id)
    if user_dir:
        os.makedirs(user_dir, exist_ok=True)
        user_path = os.path.join(user_dir, f"{member_name}.npy")
        np.save(user_path, embedding)
        saved_paths.append(user_path)

    return saved_paths


def _save_member_profile_record(user_id, name, description, source):
    normalized_name = _normalize_member_key(name)
    if not normalized_name:
        raise ValueError("name is invalid")

    document_id = f"{user_id}_{normalized_name}"
    db.collection("members").document(document_id).set({
        "userId": user_id,
        "name": name,
        "normalizedName": normalized_name,
        "description": description,
        "source": source,
        "updatedAt": firestore.SERVER_TIMESTAMP,
        "createdAt": firestore.SERVER_TIMESTAMP,
    }, merge=True)
    return {
        "id": document_id,
        "normalizedName": normalized_name,
    }


def load_embeddings(user_id=None):
    db = {}
    directories = []

    # Keep legacy flat embeddings readable while preferring user-scoped data.
    if os.path.exists(EMBED_DIR):
        directories.append(EMBED_DIR)

    user_dir = _user_embed_dir(user_id)
    if user_dir and os.path.exists(user_dir):
        directories.append(user_dir)

    for directory in directories:
        for file in os.listdir(directory):
            if file.endswith(".npy"):
                name = file.replace(".npy", "")
                db[name] = np.load(os.path.join(directory, file))
    print(f"Loaded {len(db)} enrolled speakers")
    return db


speaker_db = load_embeddings()


@app.route("/known-speakers", methods=["GET"])
def get_known_speakers():
    global speaker_db
    user_id = request.args.get("userId")
    speaker_db = load_embeddings(user_id=user_id)
    names = sorted(speaker_db.keys())
    return jsonify({"speakers": names})


@app.route("/members/enroll", methods=["POST"])
def enroll_member():
    global speaker_db

    audio_file = request.files.get("audio")
    user_id = (request.form.get("userId") or "").strip()
    member_name = _sanitize_member_name(request.form.get("memberName"))
    description = (request.form.get("description") or "").strip()
    source = (request.form.get("source") or "phone").strip()

    if not user_id:
        return jsonify({"error": "userId is required"}), 400
    if not member_name:
        return jsonify({"error": "memberName is required"}), 400
    if audio_file is None or not audio_file.filename:
        return jsonify({"error": "audio file is required"}), 400

    temp_path = None
    try:
        extension = os.path.splitext(audio_file.filename)[1] or ".wav"
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
            temp_path = temp.name

        audio_file.save(temp_path)

        enroll_dir = _enroll_audio_dir(user_id, member_name)
        os.makedirs(enroll_dir, exist_ok=True)
        recorded_audio_path = os.path.join(
            enroll_dir, f"{member_name}{extension}")
        shutil.copyfile(temp_path, recorded_audio_path)

        wav = preprocess_wav(temp_path)
        embedding = encoder.embed_utterance(wav)

        output_paths = _save_embedding_outputs(user_id, member_name, embedding)
        profile = _save_member_profile_record(
            user_id=user_id,
            name=member_name,
            description=description,
            source=source,
        )

        if user_id == CURRENT_USER_ID:
            speaker_db = load_embeddings(user_id=user_id)

        return jsonify({
            "status": "ok",
            "memberName": member_name,
            "path": output_paths[0],
            "paths": output_paths,
            "audioPath": recorded_audio_path,
            "profile": profile,
        })
    except Exception as exc:
        return jsonify({"error": f"Enrollment failed: {exc}"}), 500
    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


@app.route("/members/profile", methods=["POST"])
def save_member_profile():
    payload = request.json or {}
    user_id = (payload.get("userId") or "").strip()
    name = (payload.get("name") or "").strip()
    description = (payload.get("description") or "").strip()
    source = (payload.get("source") or "").strip()

    if not user_id:
        return jsonify({"error": "userId is required"}), 400
    if not name:
        return jsonify({"error": "name is required"}), 400
    if not source:
        return jsonify({"error": "source is required"}), 400

    try:
        profile = _save_member_profile_record(
            user_id=user_id,
            name=name,
            description=description,
            source=source,
        )
        return jsonify({
            "status": "ok",
            **profile,
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to save member profile: {exc}"}), 500


enrollment_state = {
    "active": False,
    "status": "idle",
    "userId": None,
    "memberName": None,
    "collectedWindows": 0,
    "targetWindows": ENROLLMENT_TARGET_WINDOWS,
    "windowSeconds": ENROLLMENT_WINDOW_SECONDS,
    "error": None,
    "path": None,
}
iot_enrollment_embeddings = []


def _set_iot_enrollment_state(**updates):
    enrollment_state.update(updates)


@app.route("/members/enroll/iot/start", methods=["POST"])
def start_iot_member_enrollment():
    global audio_buffer, iot_enrollment_audio_buffer, iot_enrollment_embeddings

    payload = request.json or {}
    user_id = (payload.get("userId") or "").strip()
    member_name = _sanitize_member_name(payload.get("memberName"))

    if not user_id:
        return jsonify({"error": "userId is required"}), 400
    if not member_name:
        return jsonify({"error": "memberName is required"}), 400
    if enrollment_state["active"]:
        return jsonify({"error": "Another IoT enrollment is already in progress"}), 409

    audio_buffer = np.array([], dtype=np.int16)
    iot_enrollment_audio_buffer = []
    iot_enrollment_embeddings = []
    _set_iot_enrollment_state(
        active=True,
        status="recording",
        userId=user_id,
        memberName=member_name,
        collectedWindows=0,
        targetWindows=ENROLLMENT_TARGET_WINDOWS,
        windowSeconds=ENROLLMENT_WINDOW_SECONDS,
        error=None,
        path=None,
    )

    return jsonify({
        "status": "recording",
        "memberName": member_name,
        "targetWindows": ENROLLMENT_TARGET_WINDOWS,
        "windowSeconds": ENROLLMENT_WINDOW_SECONDS,
    }), 202


@app.route("/members/enroll/iot/status", methods=["GET"])
def get_iot_member_enrollment_status():
    user_id = (request.args.get("userId") or "").strip()

    if user_id and enrollment_state["userId"] not in (None, user_id):
        return jsonify({"status": "idle", "active": False})

    return jsonify(enrollment_state)


@app.route("/members/enroll/iot/complete", methods=["POST"])
def complete_iot_member_enrollment():
    payload = request.json or {}
    user_id = (payload.get("userId") or "").strip()
    member_name = _sanitize_member_name(payload.get("memberName"))
    description = (payload.get("description") or "").strip()
    source = (payload.get("source") or "iot").strip()

    if not user_id:
        return jsonify({"error": "userId is required"}), 400
    if not member_name:
        return jsonify({"error": "memberName is required"}), 400

    expected_path = os.path.join(
        _user_embed_dir(user_id), f"{member_name}.npy")
    if not os.path.exists(expected_path):
        return jsonify({"error": "Voice embedding not found for member"}), 409

    try:
        profile = _save_member_profile_record(
            user_id=user_id,
            name=member_name,
            description=description,
            source=source,
        )
        return jsonify({
            "status": "ok",
            "memberName": member_name,
            "path": expected_path,
            "profile": profile,
        })
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as exc:
        return jsonify({"error": f"Failed to finalize IoT enrollment: {exc}"}), 500


# ================= SPEAKER STATE =================
last_confirmed_speaker = None
current_candidate = None
stable_count = 0

# ================= SILENCE TRIM =================


def trim_silence(audio, sr, threshold=0.01):
    frame_len = int(0.025 * sr)
    hop = frame_len

    energies = [
        np.mean(audio[i:i+frame_len]**2)
        for i in range(0, len(audio)-frame_len, hop)
    ]

    if not energies:
        return audio

    energies = np.array(energies)
    max_energy = np.max(energies)

    if max_energy == 0:
        return audio

    mask = energies > (threshold * max_energy)

    if not mask.any():
        return audio

    start = np.argmax(mask) * hop
    end = (len(mask) - np.argmax(mask[::-1])) * hop

    return audio[start:end]

# ================= SPEAKER COMPARISON =================


def compare_embedding(test_emb):
    global last_confirmed_speaker, current_candidate, stable_count

    current_db = load_embeddings(user_id=CURRENT_USER_ID)

    if not current_db:
        print("⚠ No enrolled speakers found!")
        return

    timestamp_str = datetime.now().strftime("%H:%M:%S")

    results = []
    for name, stored_emb in current_db.items():
        score = np.dot(test_emb, stored_emb)
        results.append((name, score))

    results.sort(key=lambda x: x[1], reverse=True)

    best_name, best_score = results[0]

    print(f"\n[{timestamp_str}] Top Matches:")
    for i, (name, score) in enumerate(results[:3]):
        print(f"   {i+1}. {name} → {score:.4f}")

    if best_score < UNKNOWN_THRESHOLD:
        detected = "UNKNOWN"
    else:
        detected = best_name

    print(f"[{timestamp_str}] Detected: {detected} ({best_score:.4f})")

    # ===== Stability Logic =====
    if detected == current_candidate:
        stable_count += 1
    else:
        current_candidate = detected
        stable_count = 1

    if stable_count < STABLE_REQUIRED:
        return

    # ===== Push Only If Changed =====
    if detected != last_confirmed_speaker:

        if detected == "UNKNOWN":
            send_push(
                "⚠ Unknown Speaker",
                "Unrecognized person speaking near patient.",
                alert_type="speaker",
                user_id=CURRENT_USER_ID,
            )
        else:
            send_push(
                "👤 Speaker Identified",
                f"{detected} is speaking.",
                alert_type="speaker",
                extra_data={"detectedSpeaker": detected},
                user_id=CURRENT_USER_ID,
            )

        last_confirmed_speaker = detected


def _complete_iot_enrollment():
    global speaker_db, iot_enrollment_audio_buffer, iot_enrollment_embeddings

    user_id = enrollment_state["userId"]
    member_name = enrollment_state["memberName"]

    averaged_embedding = np.mean(iot_enrollment_embeddings, axis=0)
    output_paths = _save_embedding_outputs(
        user_id, member_name, averaged_embedding)

    if user_id == CURRENT_USER_ID:
        speaker_db = load_embeddings(user_id=user_id)

    _set_iot_enrollment_state(
        active=False,
        status="completed",
        collectedWindows=enrollment_state["targetWindows"],
        path=output_paths[0],
        paths=output_paths,
        error=None,
    )
    iot_enrollment_audio_buffer = []
    iot_enrollment_embeddings = []


async def _process_iot_enrollment_frame(frame, loop):
    global iot_enrollment_audio_buffer, iot_enrollment_embeddings

    iot_enrollment_audio_buffer.append(frame)
    total_samples = sum(len(chunk) for chunk in iot_enrollment_audio_buffer)

    if total_samples < ENROLLMENT_TARGET_SAMPLES:
        return

    audio = np.concatenate(iot_enrollment_audio_buffer)[
        :ENROLLMENT_TARGET_SAMPLES]
    iot_enrollment_audio_buffer = []

    audio_f = audio.astype(np.float32) / 32768.0
    audio_f = trim_silence(audio_f, SAMPLE_RATE)

    collected = enrollment_state["collectedWindows"] + 1
    enroll_dir = _enroll_audio_dir(
        enrollment_state["userId"],
        enrollment_state["memberName"],
    )
    os.makedirs(enroll_dir, exist_ok=True)
    sf.write(
        os.path.join(enroll_dir, f"win_{collected:02d}.wav"),
        audio_f,
        SAMPLE_RATE,
    )

    wav = preprocess_wav(audio_f, SAMPLE_RATE)
    emb = await loop.run_in_executor(
        executor,
        encoder.embed_utterance,
        wav
    )

    iot_enrollment_embeddings.append(emb)
    _set_iot_enrollment_state(collectedWindows=collected)

    if collected >= enrollment_state["targetWindows"]:
        try:
            _complete_iot_enrollment()
        except Exception as exc:
            _set_iot_enrollment_state(
                active=False,
                status="failed",
                error=str(exc),
            )
            iot_enrollment_audio_buffer = []
            iot_enrollment_embeddings = []

# ================= AUDIO PROCESSOR =================


async def processor():
    global audio_buffer
    loop = asyncio.get_running_loop()

    while True:
        msg = await frame_queue.get()

        frame = np.frombuffer(msg, dtype=np.int16)

        if enrollment_state["active"]:
            await _process_iot_enrollment_frame(frame, loop)
            continue

        audio_buffer = np.concatenate([audio_buffer, frame])

        while len(audio_buffer) >= WINDOW_SAMPLES:
            audio = audio_buffer[:WINDOW_SAMPLES]
            audio_buffer = audio_buffer[STEP_SAMPLES:]

            audio_f = audio.astype(np.float32) / 32768.0

            # Silence removal
            audio_f = trim_silence(audio_f, SAMPLE_RATE)

            wav = preprocess_wav(audio_f, SAMPLE_RATE)

            emb = await loop.run_in_executor(
                executor,
                encoder.embed_utterance,
                wav
            )

            compare_embedding(emb)

# ================= WEBSOCKET =================


async def ws_handler(ws):
    global CURRENT_USER_ID
    print("🔌 ESP connected")

    try:
        async for message in ws:

            if isinstance(message, bytes):
                await frame_queue.put(message)
                continue

            data = json.loads(message)
            msg_type = data.get("type")
            incoming_user_id = data.get("userId")
            if incoming_user_id:
                CURRENT_USER_ID = incoming_user_id

            # ===== FALL DETECTION =====
            if msg_type == "fall":
                acc_mean = data["acc_mean"]
                acc_std = data["acc_std"]
                gyro_mean = data["gyro_mean"]
                gyro_std = data["gyro_std"]

                X = np.array([[acc_mean, acc_std, gyro_mean, gyro_std]])
                X_scaled = scaler.transform(X)

                prob = model.predict_proba(X_scaled)[0][1]
                print("🧠 Fall probability:", prob)

                if prob > THRESHOLD:
                    send_push(
                        "🚨 Fall Detected",
                        "Possible fall detected.",
                        alert_type="fall",
                        user_id=incoming_user_id or CURRENT_USER_ID,
                    )

            # ===== GPS =====
            elif msg_type == "gps":
                print("📍 GPS:", data["lat"], data["lon"])

    except Exception as e:
        print("WebSocket closed:", e)

# ================= START SERVERS =================


async def start_ws():
    server = await websockets.serve(
        ws_handler,
        "0.0.0.0",
        8765,
        ping_interval=None,
        max_size=None
    )
    print("🚀 WebSocket running on ws://0.0.0.0:8765")

    asyncio.create_task(processor())
    await asyncio.Future()


def start_flask():
    print("🌐 Flask running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000)


if __name__ == "__main__":
    Thread(target=start_flask).start()
    asyncio.run(start_ws())
