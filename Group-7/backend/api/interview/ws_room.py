"""
api/interview/ws_room.py

WebSocket endpoint for the live interview room.

Protocol (JSON messages over WS):
────────────────────────────────────────────────────────────────────
Frontend → Backend:
  { "type": "user_speech", "text": "..." }   — final STT transcript
  { "type": "ping" }                          — keep-alive
  { "type": "video_frame", "image": "..." }   — base64 JPEG for proctoring

Backend → Frontend:
  { "type": "agent_text",  "text": "...",  "audio_url": "/Agent/tts?text=..." }
  { "type": "evaluation",  "result": {...} }
  { "type": "proctoring_alert", "status": "..." }
  { "type": "error",       "message": "..." }
  { "type": "pong" }
────────────────────────────────────────────────────────────────────

Proctoring is INDEPENDENT of AI service:
  - WebSocket accepts all video_frame messages even if AI model is unavailable
  - Opening question generation failure is non-fatal (sends error, but keeps socket alive)
"""

from __future__ import annotations

import json
import os
import urllib.parse
from datetime import datetime
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from services import agent_service
from services.proctoring_service import ProctoringSession

router = APIRouter(prefix="/ws", tags=["WebSocket"])

# In-memory per-session state
_sessions: dict[str, dict[str, Any]] = {}

# Proctoring log file  (relative to backend/ root)
_BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
_PROCTOR_LOG_FILE = os.path.join(_BASE_DIR, "proctoring_log.json")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _append_proctor_log(session_id: str, status: str) -> None:
    """Persist a proctoring status-change to proctoring_log.json."""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_id": session_id,
        "status": status,
    }
    existing: list = []
    if os.path.exists(_PROCTOR_LOG_FILE):
        with open(_PROCTOR_LOG_FILE, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(entry)
    with open(_PROCTOR_LOG_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)


def _get_or_create_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "conversation_history": [],
            "question_count": 0,
            "current_question": None,
            "proctoring_session": ProctoringSession(),
        }
    return _sessions[session_id]


def _make_tts_url(text: str) -> str:
    encoded = urllib.parse.quote(text, safe="")
    return f"/Agent/tts?text={encoded}"


async def _send(ws: WebSocket, payload: dict):
    await ws.send_text(json.dumps(payload))


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/interview/{session_id}")
async def interview_ws(ws: WebSocket, session_id: str):
    await ws.accept()
    state = _get_or_create_session(session_id)

    print(f"\n[WS] Session connected: {session_id}")

    # ── Opening question (non-fatal — proctoring still works if this fails) ──
    try:
        opener = await agent_service.generate_question(state["conversation_history"])
        state["current_question"] = opener
        await _send(ws, {
            "type": "agent_text",
            "text": opener,
            "audio_url": _make_tts_url(opener),
        })
    except Exception as e:
        print(f"[WS] Warning: could not generate opening question: {e}")
        # Send a soft error to the frontend but DO NOT close the socket.
        # Proctoring video_frame messages will still be processed.
        await _send(ws, {
            "type": "error",
            "message": f"AI service unavailable — interview mode disabled. Proctoring is still active. ({e})",
        })

    # ── Main message loop ─────────────────────────────────────────────────────
    try:
        while True:
            raw = await ws.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                await _send(ws, {"type": "error", "message": "Invalid JSON"})
                continue

            msg_type = msg.get("type", "")

            # ── Ping/pong keep-alive ─────────────────────────────────────────
            if msg_type == "ping":
                await _send(ws, {"type": "pong"})
                continue

            # ── Video frame for proctoring ───────────────────────────────────
            if msg_type == "video_frame":
                frame_data = msg.get("image", "")
                if frame_data:
                    new_status = state["proctoring_session"].process_frame(frame_data)
                    if new_status:
                        # Send alert to frontend
                        await _send(ws, {"type": "proctoring_alert", "status": new_status})

                        # Print to terminal
                        ts = datetime.now().strftime("%H:%M:%S")
                        icon = "✅" if new_status == "Candidate OK" else "⚠️ "
                        print(f"[{ts}] [Proctoring] {icon} {session_id}: {new_status}")

                        # Persist to JSON log
                        _append_proctor_log(session_id, new_status)
                continue

            # ── Candidate spoke ──────────────────────────────────────────────
            if msg_type == "user_speech":
                answer = msg.get("text", "").strip()
                if not answer:
                    continue

                current_q = state["current_question"] or ""

                try:
                    evaluation = await agent_service.evaluate_answer(current_q, answer)
                    await _send(ws, {"type": "evaluation", "result": evaluation})
                except Exception as e:
                    print(f"[WS] evaluate_answer failed: {e}")

                state["conversation_history"].append({
                    "AIMessage": current_q,
                    "HumanMessage": answer,
                })
                state["question_count"] += 1

                try:
                    next_q = await agent_service.generate_question(state["conversation_history"])
                    state["current_question"] = next_q
                    await _send(ws, {
                        "type": "agent_text",
                        "text": next_q,
                        "audio_url": _make_tts_url(next_q),
                    })
                except Exception as e:
                    print(f"[WS] generate_question failed: {e}")

    except WebSocketDisconnect:
        print(f"[WS] Session disconnected: {session_id}")
        session_data = _sessions.pop(session_id, None)
        if session_data and "proctoring_session" in session_data:
            session_data["proctoring_session"].close()
