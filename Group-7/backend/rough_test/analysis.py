"""
analysis.py — Speech Confidence Analyser
=========================================
Analyses a fixed-duration audio recording (or a pre-loaded numpy array) and
produces per-dimension scores that together form an overall confidence score.

Scores (all out of 10):
  • Speech Rate   — words-per-minute vs. ideal band [130, 170]
  • Pauses        — silence ratio vs. ideal band [30%, 55%]
  • Filler Words  — rate of filler words per minute
  • Energy        — RMS loudness + variability
  • Clarity       — average ASR word confidence
  • Pitch         — F0 standard-deviation (vocal expressiveness)

Overall confidence is a weighted combination of the six scores.

The module exposes:
  analyze_audio(audio_array, duration_seconds)  → dict
  record_fixed_duration(seconds)                → np.ndarray

Run as __main__ to record from microphone and stream results + write a log.
"""

# ---------------------------------------------------------------------------
# Imports — all consolidated at the top (fixes duplicate-import flaw)
# ---------------------------------------------------------------------------
import os
import json
import tempfile
import logging
from datetime import datetime
from pathlib import Path

import numpy as np
import scipy.io.wavfile
import sounddevice as sd
import soundfile as sf
import librosa
from faster_whisper import WhisperModel

# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SAMPLE_RATE: int = 16_000
RECORD_SECONDS: int = 30

NORMAL_MIN_WPM: float = 130.0
NORMAL_MAX_WPM: float = 170.0

MIN_PAUSE_SEC: float = 0.30       # shortest gap counted as a pause
ENERGY_THRESHOLD: int = 500       # amplitude below this → silent

IDEAL_PAUSE_MIN: float = 0.30     # 30 % silence  → ideal lower bound
IDEAL_PAUSE_MAX: float = 0.55     # 55 % silence  → ideal upper bound

FILLER_WORDS = {
    "uh", "um", "erm", "hmm",
    "like", "you know", "i mean",
    "so", "well", "actually", "basically",
    "sort of", "kind of",
}

CONFIDENCE_WEIGHTS = {
    "rate":    0.25,
    "pause":   0.20,
    "filler":  0.10,
    "energy":  0.20,
    "clarity": 0.15,
    "pitch":   0.10,
}

# ---------------------------------------------------------------------------
# Model (lazy-loaded so importing the module doesn't force a download)
# ---------------------------------------------------------------------------
_whisper_model: WhisperModel | None = None


def _get_model() -> WhisperModel:
    global _whisper_model
    if _whisper_model is None:
        log.info("Loading Whisper model (first call)…")
        _whisper_model = WhisperModel(
            "Systran/faster-whisper-base",
            device="cpu",
            compute_type="int8",
        )
        log.info("Whisper model loaded.")
    return _whisper_model


# ===========================================================================
# Recording
# ===========================================================================

def record_fixed_duration(seconds: int = RECORD_SECONDS) -> np.ndarray:
    """Record `seconds` of mono audio at SAMPLE_RATE. Returns int16 array."""
    print(f"🎤  Recording for {seconds} seconds — speak now…")
    try:
        recording = sd.rec(
            int(seconds * SAMPLE_RATE),
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
        )
        sd.wait()
    except Exception as exc:
        log.error("Recording failed: %s", exc)
        raise
    return recording.flatten()


# ===========================================================================
# Transcription
# ===========================================================================

def transcribe_from_array(audio_array: np.ndarray) -> tuple[str, float]:
    """
    Write audio to a temporary wav, transcribe with Whisper, return
    (transcript, avg_word_confidence).

    The temp file is always deleted on exit (fixes the tempfile-leak flaw).
    """
    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            tmp_path = f.name
            scipy.io.wavfile.write(f.name, SAMPLE_RATE, audio_array)

        segments, _ = _get_model().transcribe(
            tmp_path,
            language="en",
            word_timestamps=True,
        )

        words: list[str] = []
        confidences: list[float] = []

        for seg in segments:
            if not seg.words:
                continue
            for w in seg.words:
                words.append(w.word.strip())
                confidences.append(float(w.probability))

        transcript = " ".join(words)
        avg_conf = float(np.mean(confidences)) if confidences else 0.0
        return transcript, avg_conf

    except Exception as exc:
        log.error("Transcription failed: %s", exc)
        return "", 0.0
    finally:
        # Always clean up — fixes tempfile-leak flaw
        if tmp_path and os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


# ===========================================================================
# Scoring helpers
# ===========================================================================

def compute_speech_rate_score(
    transcript: str,
    duration_seconds: float,
    max_score: float = 10.0,
) -> tuple[float, float]:
    """Return (wpm, score/10)."""
    words = transcript.strip().split()
    num_words = len(words)

    if duration_seconds <= 0 or num_words == 0:
        return 0.0, 0.0

    wpm = num_words / (duration_seconds / 60.0)

    if NORMAL_MIN_WPM <= wpm <= NORMAL_MAX_WPM:
        score = max_score
    elif wpm < NORMAL_MIN_WPM:
        penalty = 0.1 * (NORMAL_MIN_WPM - wpm)
        score = max(max_score - penalty, 0.0)
    else:
        penalty = 0.1 * (wpm - NORMAL_MAX_WPM)
        score = max(max_score - penalty, 0.0)

    return wpm, score


def detect_pauses(
    audio_array: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
) -> tuple[list[float], float]:
    """
    Vectorised pause detection (fixes slow Python-loop flaw).
    Returns (list_of_pause_durations_in_seconds, total_pause_seconds).
    """
    energy = np.abs(audio_array.astype(np.int32))
    silent: np.ndarray = energy < ENERGY_THRESHOLD  # bool array

    # Find transitions: False→True (start of silence) and True→False (end)
    # Pad with False on both ends to catch leading / trailing silences
    padded = np.concatenate(([False], silent, [False]))
    diff = np.diff(padded.astype(np.int8))

    # +1 → start of a silent run,  -1 → end of a silent run
    starts = np.where(diff == 1)[0]
    ends   = np.where(diff == -1)[0]

    pauses = []
    for s, e in zip(starts, ends):
        duration = (e - s) / sample_rate
        if duration >= MIN_PAUSE_SEC:
            pauses.append(float(duration))

    return pauses, float(sum(pauses))


def compute_pause_score(
    total_pause_time: float,
    total_duration: float,
    max_score: float = 10.0,
) -> float:
    if total_duration <= 0:
        return 0.0

    pause_ratio = total_pause_time / total_duration

    if IDEAL_PAUSE_MIN <= pause_ratio <= IDEAL_PAUSE_MAX:
        return max_score

    if pause_ratio < IDEAL_PAUSE_MIN:
        diff = IDEAL_PAUSE_MIN - pause_ratio
        worst_diff = IDEAL_PAUSE_MIN
    else:
        diff = pause_ratio - IDEAL_PAUSE_MAX
        worst_diff = 1.0 - IDEAL_PAUSE_MAX

    penalty_ratio = min(diff / worst_diff, 1.0)
    return max_score * (1.0 - penalty_ratio)


def count_fillers(transcript: str) -> int:
    text = transcript.lower()
    count = 0

    # Multi-word phrases first (avoids double-counting)
    multi = ["you know", "i mean", "sort of", "kind of"]
    for phrase in multi:
        count += text.count(phrase)
        text = text.replace(phrase, " ")

    # Single-word fillers
    for w in text.split():
        w_clean = w.strip(".,!?;:")
        if w_clean in FILLER_WORDS:
            count += 1

    return count


def filler_score_from_counts(
    filler_count: int,
    duration_sec: float,
    max_score: float = 10.0,
) -> float:
    if duration_sec <= 0:
        return 0.0

    fpm = filler_count / (duration_sec / 60.0)
    if fpm <= 3:
        return max_score
    if fpm >= 15:
        return 0.0
    ratio = (fpm - 3) / (15 - 3)
    return max_score * (1.0 - ratio)


def compute_rms_and_f0(
    audio_array: np.ndarray,
    sample_rate: int = SAMPLE_RATE,
) -> dict:
    """Returns dict with rms_mean, rms_std, f0_mean, f0_std."""
    y = audio_array.astype(np.float32) / 32768.0

    rms = librosa.feature.rms(y=y, frame_length=1024, hop_length=512)[0]
    rms_mean = float(np.mean(rms))
    rms_std  = float(np.std(rms))

    f0 = librosa.yin(
        y,
        fmin=80,
        fmax=400,
        sr=sample_rate,
        frame_length=2048,
        hop_length=512,
    )
    f0 = f0[np.isfinite(f0) & (f0 > 0)]  # discard unvoiced frames
    f0_mean = float(np.mean(f0)) if len(f0) else 0.0
    f0_std  = float(np.std(f0))  if len(f0) else 0.0

    return {
        "rms_mean": rms_mean,
        "rms_std":  rms_std,
        "f0_mean":  f0_mean,
        "f0_std":   f0_std,
    }


def map_energy_emotion_score(
    rms_mean: float,
    rms_std: float,
    f0_std: float,
    w_rms: float = 0.4,
    w_rms_var: float = 0.2,
    w_f0_var: float = 0.4,
    max_score: float = 10.0,
) -> float:
    QUIET_RMS, LOUD_RMS = 0.005, 0.03
    rms_norm = max(0.0, min(1.0, (rms_mean - QUIET_RMS) / (LOUD_RMS - QUIET_RMS)))

    LOW_RMS_STD, HIGH_RMS_STD = 0.0005, 0.01
    rms_var_norm = max(0.0, min(1.0, (rms_std - LOW_RMS_STD) / (HIGH_RMS_STD - LOW_RMS_STD)))

    LOW_F0_STD, HIGH_F0_STD = 5.0, 40.0
    f0_var_norm = max(0.0, min(1.0, (f0_std - LOW_F0_STD) / (HIGH_F0_STD - LOW_F0_STD)))

    combined = (w_rms * rms_norm) + (w_rms_var * rms_var_norm) + (w_f0_var * f0_var_norm)
    return combined * max_score


def clarity_score_from_conf(avg_conf: float, max_score: float = 10.0) -> float:
    LOW, HIGH = 0.70, 0.95
    if avg_conf <= LOW:
        return 0.0
    if avg_conf >= HIGH:
        return max_score
    return ((avg_conf - LOW) / (HIGH - LOW)) * max_score


def voiced_ratio(total_pause_time: float, total_duration: float) -> float:
    if total_duration <= 0:
        return 0.0
    return max(0.0, min(1.0, 1.0 - total_pause_time / total_duration))


def pitch_score_from_f0(
    f0_std: float,
    voiced_ratio_value: float,
    max_score: float = 10.0,
) -> float:
    """
    Score based on F0 standard deviation (expressiveness).
    Ideal centre 40 Hz, tolerance band ±60 Hz (was ±30 — fixes narrow-band flaw).
    """
    if voiced_ratio_value < 0.2 or f0_std <= 1.0:
        return 0.0

    IDEAL_CENTER  = 40.0
    IDEAL_WIDTH   = 60.0   # widened from 30 → real speech commonly hits 40–80 Hz std
    MIN_STD       = 5.0
    MAX_STD       = 150.0

    f0_std = max(MIN_STD, min(MAX_STD, f0_std))
    dist   = abs(f0_std - IDEAL_CENTER)

    if dist >= IDEAL_WIDTH:
        return 0.0

    return (1.0 - dist / IDEAL_WIDTH) * max_score


def overall_confidence_score(
    rate_score: float,
    pause_score: float,
    filler_score: float,
    energy_score: float,
    clarity_score: float,
    pitch_score: float,
) -> float:
    w = CONFIDENCE_WEIGHTS
    return (
        w["rate"]    * rate_score   +
        w["pause"]   * pause_score  +
        w["filler"]  * filler_score +
        w["energy"]  * energy_score +
        w["clarity"] * clarity_score +
        w["pitch"]   * pitch_score
    )


# ===========================================================================
# Public one-shot pipeline
# ===========================================================================

def analyze_audio(
    audio_array: np.ndarray,
    duration_seconds: float,
    question: str = "",
) -> dict:
    """
    Run the full confidence-analysis pipeline on an already-recorded audio array.

    Parameters
    ----------
    audio_array      : int16 mono audio samples at SAMPLE_RATE
    duration_seconds : actual recording duration in seconds
    question         : (optional) interview question text, stored in the result

    Returns
    -------
    dict with keys:
        timestamp, question, transcript, wpm,
        rate_score, pause_score, filler_score,
        energy_score, clarity_score, pitch_score,
        overall_confidence
    """
    # 1. Transcribe
    transcript, avg_conf = transcribe_from_array(audio_array)

    # 2. Speech rate
    wpm, rate_score = compute_speech_rate_score(transcript, duration_seconds)

    # 3. Pause analysis (vectorised)
    pauses, total_pause_time = detect_pauses(audio_array, SAMPLE_RATE)
    pause_score = compute_pause_score(total_pause_time, duration_seconds)

    # 4. Filler words
    filler_count = count_fillers(transcript)
    filler_score = filler_score_from_counts(filler_count, duration_seconds)

    # 5. Prosody (RMS + F0)
    prosody     = compute_rms_and_f0(audio_array, SAMPLE_RATE)
    energy_score = map_energy_emotion_score(
        prosody["rms_mean"],
        prosody["rms_std"],
        prosody["f0_std"],
    )

    # 6. Clarity
    clarity_score = clarity_score_from_conf(avg_conf)

    # 7. Pitch
    vr          = voiced_ratio(total_pause_time, duration_seconds)
    pitch_score = pitch_score_from_f0(prosody["f0_std"], vr)

    # 8. Overall
    confidence = overall_confidence_score(
        rate_score, pause_score, filler_score,
        energy_score, clarity_score, pitch_score,
    )

    return {
        "timestamp":            datetime.now().isoformat(sep=" "),
        "question":             question,
        "transcript":           transcript,
        "wpm":                  round(wpm, 2),
        "avg_asr_confidence":   round(avg_conf, 4),
        "pause_count":          len(pauses),
        "total_pause_seconds":  round(total_pause_time, 3),
        "filler_count":         filler_count,
        # Individual scores (all /10)
        "rate_score":           round(rate_score,    2),
        "pause_score":          round(pause_score,   2),
        "filler_score":         round(filler_score,  2),
        "energy_score":         round(energy_score,  2),
        "clarity_score":        round(clarity_score, 2),
        "pitch_score":          round(pitch_score,   2),
        # Composite
        "overall_confidence":   round(confidence,    2),
    }


# ===========================================================================
# CLI entry-point
# ===========================================================================

if __name__ == "__main__":
    from audio_score_logger import log_audio_score

    LOG_PATH = Path(__file__).parent / "audio_scores.json"

    audio = record_fixed_duration(RECORD_SECONDS)
    print("[*] Transcribing...")

    result = analyze_audio(audio, RECORD_SECONDS, question="Live microphone test")

    print()
    print(f"[Transcript]      : {result['transcript']}")
    print(f"[Speech Rate]     : {result['wpm']:.1f} WPM")
    print(f"[ASR Confidence]  : {result['avg_asr_confidence']:.3f}")
    print(f"[Total Pauses]    : {result['total_pause_seconds']:.2f} s")
    print(f"[Filler Words]    : {result['filler_count']}")
    print()
    print(f"  Rate  score     : {result['rate_score']:.1f} / 10")
    print(f"  Pause score     : {result['pause_score']:.1f} / 10")
    print(f"  Filler score    : {result['filler_score']:.1f} / 10")
    print(f"  Energy score    : {result['energy_score']:.1f} / 10")
    print(f"  Clarity score   : {result['clarity_score']:.1f} / 10")
    print(f"  Pitch  score    : {result['pitch_score']:.1f} / 10")
    print()
    print(f"[OVERALL] Confidence score : {result['overall_confidence']:.1f} / 10")

    log_audio_score(result, log_path=str(LOG_PATH))
    print(f"\n[LOG] Score saved to {LOG_PATH}")