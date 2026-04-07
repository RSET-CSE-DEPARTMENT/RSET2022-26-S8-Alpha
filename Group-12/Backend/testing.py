import asyncio
import websockets
import numpy as np
import soundfile as sf
import os
from datetime import datetime   # ✅ added
from resemblyzer import VoiceEncoder, preprocess_wav

# ================= CONFIG =================
MODE = "identify"   # "enroll" or "identify"
CURRENT_SPEAKER = "Anitta"

WINDOW_SECONDS = 5
STEP_SECONDS = 2
TARGET_WINDOWS = 8
SAVE_WAVS = True

UNKNOWN_THRESHOLD = 0.75

SAMPLE_RATE = 16000
WINDOW_SAMPLES = WINDOW_SECONDS * SAMPLE_RATE
STEP_SAMPLES = STEP_SECONDS * SAMPLE_RATE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "data")

ENROLL_DIR = os.path.join(BASE_DIR, "enroll", CURRENT_SPEAKER)
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")

os.makedirs(ENROLL_DIR, exist_ok=True)
os.makedirs(EMBED_DIR, exist_ok=True)

encoder = VoiceEncoder()

# ================= LOAD STORED EMBEDDINGS =================


def load_embeddings():
    db = {}
    for file in os.listdir(EMBED_DIR):
        if file.endswith(".npy"):
            name = file.replace(".npy", "")
            db[name] = np.load(os.path.join(EMBED_DIR, file))
    print(f"Loaded {len(db)} enrolled speakers")
    return db


speaker_db = load_embeddings()

# ================= STATE =================
frame_queue = asyncio.Queue()
audio_buffer = np.array([], dtype=np.int16)

embeddings = []
window_count = 0

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
    mask = energies > (threshold * max_energy)

    if not mask.any():
        return audio

    start = np.argmax(mask) * hop
    end = (len(mask) - np.argmax(mask[::-1])) * hop

    return audio[start:end]

# ================= COSINE SIMILARITY =================


def compare_embedding(test_emb, timestamp_str):
    if not speaker_db:
        print(f"[{timestamp_str}] ⚠ No enrolled speakers found!")
        return

    results = []
    for name, stored_emb in speaker_db.items():
        score = np.dot(test_emb, stored_emb)
        results.append((name, score))

    results.sort(key=lambda x: x[1], reverse=True)

    best_name, best_score = results[0]

    print(f"\n[{timestamp_str}] Top Matches:")
    for i, (name, score) in enumerate(results[:5]):
        print(f"   {i+1}. {name} → {score:.4f}")

    # ===== UNKNOWN CHECK =====
    if best_score < UNKNOWN_THRESHOLD:
        print(
            f"[{timestamp_str}] Predicted Speaker: UNKNOWN (best={best_name}, score={best_score:.4f})\n")
    else:
        print(
            f"[{timestamp_str}] Predicted Speaker: {best_name} (score={best_score:.4f})\n")

# ================= FRAME RECEIVER =================


async def handler(ws):
    print("Client connected")
    try:
        async for msg in ws:
            await frame_queue.put(msg)
    except Exception as e:
        print("Connection closed:", e)

# ================= PROCESSOR TASK =================


async def processor():
    global audio_buffer, embeddings, window_count
    loop = asyncio.get_running_loop()

    while True:
        msg = await frame_queue.get()

        frame = np.frombuffer(msg, dtype=np.int16)
        audio_buffer = np.concatenate([audio_buffer, frame])

        while len(audio_buffer) >= WINDOW_SAMPLES:
            # timestamp for this window
            timestamp_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            audio = audio_buffer[:WINDOW_SAMPLES]

            # SLIDE WINDOW
            audio_buffer = audio_buffer[STEP_SAMPLES:]

            audio_f = audio.astype(np.float32) / 32768.0
            audio_f = trim_silence(audio_f, SAMPLE_RATE)

            window_count += 1
            print(f"\n[{timestamp_str}] Processing Window {window_count}")

            wav = preprocess_wav(audio_f, SAMPLE_RATE)

            emb = await loop.run_in_executor(
                None,
                encoder.embed_utterance,
                wav
            )

            # ========== ENROLL MODE ==========
            if MODE == "enroll":
                embeddings.append(emb)

                if SAVE_WAVS:
                    fname = f"win_{window_count:02d}.wav"
                    sf.write(os.path.join(ENROLL_DIR, fname),
                             audio_f, SAMPLE_RATE)

                if window_count >= TARGET_WINDOWS:
                    final_emb = np.mean(embeddings, axis=0)
                    out_path = os.path.join(
                        EMBED_DIR, f"{CURRENT_SPEAKER}.npy")
                    np.save(out_path, final_emb)

                    print(
                        f"[{timestamp_str}] ✅ ENROLLMENT COMPLETE for {CURRENT_SPEAKER}")
                    embeddings.clear()
                    window_count = 0

            # ========== IDENTIFY MODE ==========
            elif MODE == "identify":
                compare_embedding(emb, timestamp_str)

# ================= SERVER =================


async def main():
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        8765,
        ping_interval=None
    )

    print("Backend running on ws://0.0.0.0:8765")
    asyncio.create_task(processor())
    await asyncio.Future()

asyncio.run(main())
