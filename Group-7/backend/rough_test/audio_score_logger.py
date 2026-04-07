"""
audio_score_logger.py — Persist speech-confidence scores to audio_scores.json
==============================================================================
Usage
-----
Standalone quick test:
    python audio_score_logger.py

Import in another module:
    from audio_score_logger import log_audio_score, read_audio_scores

    scores_dict = analyze_audio(audio_array, duration)          # from analysis.py
    log_audio_score(scores_dict, log_path="audio_scores.json")  # save it
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

# Default log file sits next to this script
DEFAULT_LOG_PATH = Path(__file__).parent / "audio_scores.json"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_audio_score(
    scores: dict[str, Any],
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> None:
    """
    Append one audio-analysis result entry to the JSON log file.

    Parameters
    ----------
    scores   : dict returned by ``analysis.analyze_audio()``
    log_path : path to the target JSON file (created if absent)

    The file is a JSON array of objects — same pattern as
    conversation_log.json and evaluation_log.json.
    """
    log_path = Path(log_path)

    # ── Load existing entries (or start fresh) ──────────────────────────────
    existing: list[dict] = []
    if log_path.exists():
        try:
            with log_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, list):
                existing = data
        except (json.JSONDecodeError, OSError) as exc:
            print(f"⚠  Could not read existing log ({exc}); starting fresh.")

    # ── Build the entry ─────────────────────────────────────────────────────
    entry = {
        "timestamp":   scores.get("timestamp", datetime.now().isoformat(sep=" ")),
        "question":    scores.get("question", ""),
        "transcript":  scores.get("transcript", ""),
        "metrics": {
            "wpm":                  scores.get("wpm",                  0.0),
            "avg_asr_confidence":   scores.get("avg_asr_confidence",   0.0),
            "pause_count":          scores.get("pause_count",          0),
            "total_pause_seconds":  scores.get("total_pause_seconds",  0.0),
            "filler_count":         scores.get("filler_count",         0),
        },
        "scores": {
            "rate_score":     scores.get("rate_score",    0.0),
            "pause_score":    scores.get("pause_score",   0.0),
            "filler_score":   scores.get("filler_score",  0.0),
            "energy_score":   scores.get("energy_score",  0.0),
            "clarity_score":  scores.get("clarity_score", 0.0),
            "pitch_score":    scores.get("pitch_score",   0.0),
        },
        "overall_confidence": scores.get("overall_confidence", 0.0),
    }

    existing.append(entry)

    # ── Write back atomically ────────────────────────────────────────────────
    tmp_path = log_path.with_suffix(".tmp")
    try:
        with tmp_path.open("w", encoding="utf-8") as f:
            json.dump(existing, f, indent=2, ensure_ascii=False)
        tmp_path.replace(log_path)  # atomic rename
    except OSError as exc:
        print(f"❌  Failed to write log: {exc}")
        raise


def read_audio_scores(
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> list[dict]:
    """
    Read all logged audio score entries.

    Returns an empty list if the file does not exist or is malformed.
    """
    log_path = Path(log_path)
    if not log_path.exists():
        return []
    try:
        with log_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (json.JSONDecodeError, OSError):
        return []


def summarise_session(
    log_path: str | Path = DEFAULT_LOG_PATH,
) -> dict:
    """
    Compute aggregate statistics across all logged entries.

    Returns a dict with per-dimension averages and overall average confidence.
    """
    entries = read_audio_scores(log_path)
    if not entries:
        return {"entry_count": 0}

    def avg(key: str) -> float:
        vals = [e["scores"].get(key, 0.0) for e in entries]
        return round(sum(vals) / len(vals), 2)

    return {
        "entry_count":          len(entries),
        "avg_rate_score":       avg("rate_score"),
        "avg_pause_score":      avg("pause_score"),
        "avg_filler_score":     avg("filler_score"),
        "avg_energy_score":     avg("energy_score"),
        "avg_clarity_score":    avg("clarity_score"),
        "avg_pitch_score":      avg("pitch_score"),
        "avg_overall_confidence": round(
            sum(e["overall_confidence"] for e in entries) / len(entries), 2
        ),
    }


# ---------------------------------------------------------------------------
# Self-test (no microphone required)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        test_log = Path(tmp) / "audio_scores.json"

        # Build a fake scores dict identical in shape to analyze_audio() output
        fake_scores = {
            "timestamp":           "2026-02-28 21:00:00",
            "question":            "Tell me about yourself.",
            "transcript":          "I am a software engineer with five years of experience.",
            "wpm":                 145.0,
            "avg_asr_confidence":  0.92,
            "pause_count":         3,
            "total_pause_seconds": 4.5,
            "filler_count":        1,
            "rate_score":          10.0,
            "pause_score":         9.5,
            "filler_score":        9.0,
            "energy_score":        7.5,
            "clarity_score":       8.8,
            "pitch_score":         6.0,
            "overall_confidence":  8.8,
        }

        # Write two entries, read back, summarise
        log_audio_score(fake_scores, log_path=test_log)
        log_audio_score({**fake_scores, "question": "What are your strengths?",
                         "overall_confidence": 7.5, "rate_score": 8.0},
                        log_path=test_log)

        entries = read_audio_scores(test_log)
        assert len(entries) == 2, "Expected 2 entries"

        summary = summarise_session(test_log)
        assert summary["entry_count"] == 2
        print("[PASS] Logger self-test passed!")
        print(f"   Entries written : {summary['entry_count']}")
        print(f"   Avg confidence  : {summary['avg_overall_confidence']}")
        print(f"   Avg rate score  : {summary['avg_rate_score']}")
