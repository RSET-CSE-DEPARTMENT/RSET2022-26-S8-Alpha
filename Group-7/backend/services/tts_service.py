"""
services/tts_service.py

Text-to-Speech using Microsoft Edge TTS (edge-tts).
- Free, no API key required
- High-quality neural voices (same engine as Microsoft Edge browser)
- Returns audio as in-memory bytes (mp3) that FastAPI streams to the frontend

Usage:
    audio_bytes = await synthesize("Hello, welcome to your interview!")
"""

from __future__ import annotations

import io
import asyncio
import edge_tts

from config import get_settings

settings = get_settings()


async def synthesize(text: str, voice: str | None = None) -> bytes:
    """
    Convert text to speech using edge-tts.

    Args:
        text:  The text to speak.
        voice: Optional override voice name (e.g. "en-GB-RyanNeural").
               Defaults to TTS_VOICE in .env.

    Returns:
        MP3 audio as raw bytes.
    """
    voice = voice or settings.tts_voice

    # edge_tts writes to a file-like object; we capture into memory
    buf = io.BytesIO()
    communicate = edge_tts.Communicate(text=text, voice=voice)

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            buf.write(chunk["data"])

    buf.seek(0)
    return buf.read()


async def list_voices() -> list[dict]:
    """Return all available edge-tts voices (useful for a settings page)."""
    voices = await edge_tts.list_voices()
    return [
        {
            "name": v["ShortName"],
            "locale": v["Locale"],
            "gender": v["Gender"],
        }
        for v in voices
    ]
