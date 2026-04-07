import asyncio
import websockets
import numpy as np
import soundfile as sf
import os
import argparse
from datetime import datetime
from resemblyzer import VoiceEncoder, preprocess_wav

# ================= CONFIG =================
DEFAULT_MODE = "enroll"
DEFAULT_SPEAKER = "Ayush"
DEFAULT_WINDOW_SECONDS = 8
DEFAULT_TARGET_WINDOWS = 8
DEFAULT_SAVE_WAVS = True
DEFAULT_PORT = 8765

MODE = DEFAULT_MODE
CURRENT_SPEAKER = DEFAULT_SPEAKER
WINDOW_SECONDS = DEFAULT_WINDOW_SECONDS
TARGET_WINDOWS = DEFAULT_TARGET_WINDOWS
SAVE_WAVS = DEFAULT_SAVE_WAVS

SAMPLE_RATE = 16000
TARGET_SAMPLES = WINDOW_SECONDS * SAMPLE_RATE

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.join(SCRIPT_DIR, "data")

ENROLL_DIR = os.path.join(BASE_DIR, "enroll", CURRENT_SPEAKER)
EMBED_DIR = os.path.join(BASE_DIR, "embeddings")

os.makedirs(ENROLL_DIR, exist_ok=True)
os.makedirs(EMBED_DIR, exist_ok=True)

encoder = VoiceEncoder()

# ================= STATE =================
frame_queue = asyncio.Queue()
audio_buffer = []
embeddings = []
window_count = 0


def configure(
    speaker=DEFAULT_SPEAKER,
    mode=DEFAULT_MODE,
    window_seconds=DEFAULT_WINDOW_SECONDS,
    target_windows=DEFAULT_TARGET_WINDOWS,
    save_wavs=DEFAULT_SAVE_WAVS,
):
    global CURRENT_SPEAKER, MODE, WINDOW_SECONDS, TARGET_WINDOWS, SAVE_WAVS
    global TARGET_SAMPLES, ENROLL_DIR, audio_buffer, embeddings, window_count

    CURRENT_SPEAKER = speaker
    MODE = mode
    WINDOW_SECONDS = window_seconds
    TARGET_WINDOWS = target_windows
    SAVE_WAVS = save_wavs
    TARGET_SAMPLES = WINDOW_SECONDS * SAMPLE_RATE
    ENROLL_DIR = os.path.join(BASE_DIR, "enroll", CURRENT_SPEAKER)

    os.makedirs(ENROLL_DIR, exist_ok=True)
    os.makedirs(EMBED_DIR, exist_ok=True)

    audio_buffer = []
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
        audio_buffer.append(frame)

        total_samples = sum(len(f) for f in audio_buffer)

        if total_samples >= TARGET_SAMPLES:
            audio = np.concatenate(audio_buffer)[:TARGET_SAMPLES]
            audio_buffer = []

            audio = audio.astype(np.float32) / 32768.0
            audio = trim_silence(audio, SAMPLE_RATE)

            window_count += 1
            print(f"[{CURRENT_SPEAKER}] Window {window_count}/{TARGET_WINDOWS}")

            if SAVE_WAVS:
                fname = f"win_{window_count:02d}.wav"
                sf.write(os.path.join(ENROLL_DIR, fname), audio, SAMPLE_RATE)

            wav = preprocess_wav(audio, SAMPLE_RATE)

            # Run embedding in background thread
            emb = await loop.run_in_executor(
                None,
                encoder.embed_utterance,
                wav
            )

            embeddings.append(emb)

            if MODE == "enroll" and window_count >= TARGET_WINDOWS:
                final_emb = np.mean(embeddings, axis=0)
                out_path = os.path.join(EMBED_DIR, f"{CURRENT_SPEAKER}.npy")
                np.save(out_path, final_emb)

                print("\n✅ ENROLLMENT COMPLETE")
                print(f"Speaker : {CURRENT_SPEAKER}")
                print(f"Saved   : {out_path}\n")

                embeddings.clear()
                window_count = 0

# ================= SERVER =================


async def main(port=DEFAULT_PORT):
    server = await websockets.serve(
        handler,
        "0.0.0.0",
        port,
        ping_interval=None  # disable keepalive timeout (dev mode)
    )

    print(f"Enrollment backend running on ws://0.0.0.0:{port}")

    asyncio.create_task(processor())

    await asyncio.Future()


def _parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--speaker", default=os.getenv("VOICE_CURRENT_SPEAKER", DEFAULT_SPEAKER))
    parser.add_argument("--mode", default=os.getenv("VOICE_MODE", DEFAULT_MODE))
    parser.add_argument(
        "--window-seconds",
        type=int,
        default=int(os.getenv("VOICE_WINDOW_SECONDS", DEFAULT_WINDOW_SECONDS)),
    )
    parser.add_argument(
        "--target-windows",
        type=int,
        default=int(os.getenv("VOICE_TARGET_WINDOWS", DEFAULT_TARGET_WINDOWS)),
    )
    parser.add_argument(
        "--save-wavs",
        default=os.getenv("VOICE_SAVE_WAVS", str(DEFAULT_SAVE_WAVS)).lower(),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.getenv("VOICE_PORT", DEFAULT_PORT)),
    )
    return parser.parse_args()


def _as_bool(value):
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def run():
    args = _parse_args()
    configure(
        speaker=args.speaker,
        mode=args.mode,
        window_seconds=args.window_seconds,
        target_windows=args.target_windows,
        save_wavs=_as_bool(args.save_wavs),
    )
    asyncio.run(main(port=args.port))


if __name__ == "__main__":
    run()
