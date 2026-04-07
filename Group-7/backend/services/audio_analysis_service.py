"""
services/audio_analysis_service.py

Bridge between the FastAPI endpoint and the analysis pipeline.

Accepts ANY audio format the browser can produce (WebM/Opus, MP4, OGG, WAV).
Heavy imports (librosa, faster_whisper, torch) are deferred inside the async
function so uvicorn startup stays clean regardless of package environment.
"""
from __future__ import annotations

import asyncio
import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Allow importing from rough_test/ without making it a package
_RT_DIR = Path(__file__).parent.parent / "rough_test"
_LOG_PATH = Path(__file__).parent.parent / "audio_scores.json"

SAMPLE_RATE = 16_000


def _decode_audio_bytes(audio_bytes: bytes):
    """
    Decode raw audio bytes into a (int16 array, int sample_rate) tuple.

    Strategy:
      1. Try soundfile — fast, handles WAV / OGG / FLAC / MP3.
      2. Fall back to librosa.load() — uses audioread which can handle
         WebM/Opus and MP4/AAC when ffmpeg is available.
    """
    import numpy as np
    import soundfile as sf

    try:
        data, sr = sf.read(io.BytesIO(audio_bytes), dtype="int16", always_2d=False)
        if data.ndim == 2:
            data = data.mean(axis=1).astype(np.int16)
        return data, sr
    except Exception as sf_err:
        pass  # fall through to librosa

    # Librosa fallback (handles WebM, MP4, etc. via audioread/ffmpeg)
    import librosa
    try:
        y_float, sr = librosa.load(io.BytesIO(audio_bytes), sr=None, mono=True)
        data = (y_float * 32767).clip(-32768, 32767).astype(np.int16)
        return data, sr
    except Exception as lr_err:
        raise RuntimeError(
            f"Could not decode audio. soundfile error: {sf_err} | librosa error: {lr_err}"
        )


async def analyse_wav_bytes(
    wav_bytes: bytes,
    question: str = "",
) -> dict:
    """
    Decode an audio blob (WAV / WebM / OGG / MP4 …), run the full
    speech-confidence pipeline, log results, and return the scores dict.
    """
    import numpy as np

    # Make rough_test importable
    if str(_RT_DIR) not in sys.path:
        sys.path.insert(0, str(_RT_DIR))

    # These trigger librosa / faster_whisper / torch — only on first call
    from analysis import analyze_audio
    from audio_score_logger import log_audio_score

    # ── Decode audio (any format) ─────────────────────────────────────────────
    audio_data, sample_rate = _decode_audio_bytes(wav_bytes)

    # ── Resample to 16 kHz if needed ─────────────────────────────────────────
    if sample_rate != SAMPLE_RATE:
        import librosa as _librosa
        y_float = audio_data.astype(np.float32) / 32768.0
        y_resampled = _librosa.resample(y_float, orig_sr=sample_rate, target_sr=SAMPLE_RATE)
        audio_data = (y_resampled * 32768.0).clip(-32768, 32767).astype(np.int16)

    duration_seconds = len(audio_data) / SAMPLE_RATE

    # ── Run pipeline in thread (CPU-bound) ───────────────────────────────────
    loop = asyncio.get_event_loop()
    result: dict = await loop.run_in_executor(
        None, analyze_audio, audio_data, duration_seconds, question
    )

    # ── Persist to log ────────────────────────────────────────────────────────
    try:
        log_audio_score(result, log_path=_LOG_PATH)
    except Exception as exc:
        print(f"[audio_analysis] Warning: could not write log: {exc}")

    return result
