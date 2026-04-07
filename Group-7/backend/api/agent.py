"""
api/agent.py

REST endpoints for the AI interview agent.
These mirror the original routes from test.py:
  POST /Agent/generate_question
  POST /Agent/evaluate_interview_conv

Also exposes:
  POST /Agent/tts  → returns streamed MP3 audio for a given text
  POST /upload_resume  → receives and logs a resume file upload
"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel
import io
import json
import os
from datetime import datetime

from services import agent_service, tts_service, audio_analysis_service

router = APIRouter(tags=["Agent"])

# ─── Log file paths (next to main.py) ─────────────────────────────────────────
_BASE_DIR          = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
_CONV_LOG_FILE     = os.path.join(_BASE_DIR, "conversation_log.json")
_CONV_TXT_FILE     = os.path.join(_BASE_DIR, "conversation_log.txt")
_EVAL_LOG_FILE     = os.path.join(_BASE_DIR, "evaluation_log.json")
_AUDIO_SCORE_FILE  = os.path.join(_BASE_DIR, "audio_scores.json")


def _append_json(path: str, entry: dict):
    """Thread-safe-enough append for low-volume interview logs."""
    existing: list = []
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            try:
                existing = json.load(f)
            except json.JSONDecodeError:
                existing = []
    existing.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2, ensure_ascii=False)



# ─── Schemas ─────────────────────────────────────────────────────────────────

class ConversationTurn(BaseModel):
    AIMessage: str
    HumanMessage: str


class GenerateQuestionRequest(BaseModel):
    conversation: list[ConversationTurn] = []
    cade_id: str | None = None
    interview_id: str | None = None


class EvaluateRequest(BaseModel):
    question: str
    answer: str


class TTSRequest(BaseModel):
    text: str
    voice: str | None = None


class ChatMessage(BaseModel):
    text: str
    sender: str  # "ai" or "user"
    time: str
    fromSpeech: bool | None = None


class ConversationLogRequest(BaseModel):
    sessionId: str
    role: str
    interviewType: str
    difficulty: str
    messages: list[ChatMessage]
    savedAt: str


class InsertTechScoreRequest(BaseModel):
    cade_id: str
    interview_id: str
    evaluation: dict


class CalculateFinalScoreRequest(BaseModel):
    cade_id: str
    interview_id: str


# ─── Routes ──────────────────────────────────────────────────────────────────




@router.post("/Agent/generate_question")
async def generate_question(body: GenerateQuestionRequest):
    """
    Generate the next interview question based on conversation history.
    Mirrors the original /Agent/generate_question endpoint from test.py.
    """
    history = [t.model_dump() for t in body.conversation]
    q_index = len(history) + 1

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] 🤖  GENERATE QUESTION  (turn {q_index})")
    print(f"    cade_id      : {body.cade_id}")
    print(f"    interview_id : {body.interview_id}")
    if history:
        last = history[-1]
        print(f"    Last answer  : {last.get('HumanMessage', '')[:120]}")

    try:
        question = await agent_service.generate_question(history, body.cade_id, body.interview_id)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    print(f"    → Question   : {question[:120]}")
    return {"question": question}


@router.post("/Agent/evaluate_interview_conv")
async def evaluate_interview_conv(body: EvaluateRequest):
    """
    Evaluate a candidate's answer and append to evaluation_log.json.
    Mirrors the original /Agent/evaluate_interview_conv endpoint.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] 📊  EVALUATING ANSWER")
    print(f"    Question : {body.question[:120]}")
    print(f"    Answer   : {body.answer[:120]}")

    try:
        result = await agent_service.evaluate_answer(body.question, body.answer)
    except Exception as e:
        raise HTTPException(status_code=502, detail=str(e))

    # Print evaluation scores
    if isinstance(result, dict):
        inner = result.get("result", result)
        output = inner.get("output", inner) if isinstance(inner, dict) else inner
        print(f"    Scores   : {output}")

    # Append to evaluation_log.json  (mirrors test.py's append_json)
    try:
        eval_entry = {
            "timestamp": ts,
            "question": body.question,
            "answer": body.answer,
            "evaluation": result,
        }
        _append_json(_EVAL_LOG_FILE, eval_entry)
        print(f"    Saved    → {_EVAL_LOG_FILE}")
    except Exception as e:
        print(f"    Warning: could not write evaluation log: {e}")

    return result


@router.post("/Agent/insert_tech_score")
async def insert_tech_score(body: InsertTechScoreRequest):
    """
    Forward per-question tech scores to the external scoring DB.
    Called by the frontend after each evaluation response.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] 📈  INSERT TECH SCORE")
    print(f"    cade_id      : {body.cade_id}")
    print(f"    interview_id : {body.interview_id}")

    try:
        result = await agent_service.insert_tech_score(
            body.cade_id, body.interview_id, body.evaluation
        )
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"    Warning: insert_tech_score failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/Agent/calculate_final_score")
async def calculate_final_score(body: CalculateFinalScoreRequest):
    """
    Calculate the final interview score at the end of the interview.
    Called by the frontend when the interview ends.
    """
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] 🏁  CALCULATE FINAL SCORE")
    print(f"    cade_id      : {body.cade_id}")
    print(f"    interview_id : {body.interview_id}")

    try:
        result = await agent_service.calculate_final_score(
            body.cade_id, body.interview_id
        )
        return {"status": "success", "result": result}
    except Exception as e:
        print(f"    Warning: calculate_final_score failed: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/tts")
async def text_to_speech(body: TTSRequest):
    """
    Convert text to speech and return raw MP3 audio.
    The frontend fetches this and plays it via <audio> element.
    """
    if not body.text.strip():
        raise HTTPException(status_code=400, detail="text must not be empty")

    audio_bytes = await tts_service.synthesize(body.text, body.voice)
    return Response(
        content=audio_bytes,
        media_type="audio/mpeg",
        headers={"Content-Disposition": "inline; filename=speech.mp3"},
    )


@router.get("/tts/voices")
async def get_voices():
    """List all available TTS voices."""
    voices = await tts_service.list_voices()
    return {"voices": voices}


@router.post("/Agent/save_log")
async def save_conversation_log(body: ConversationLogRequest):
    """
    Receive a completed interview conversation from the frontend.
    Prints a formatted transcript to the terminal,
    and writes both conversation_log.json and conversation_log.txt.
    """
    log_entry = body.model_dump()
    ts_display = body.savedAt

    # ── 1. Print to uvicorn terminal ─────────────────────────────────────────
    sep = "=" * 60
    print(f"\n{sep}")
    print(f"📋  INTERVIEW COMPLETE  |  {ts_display}")
    print(f"    Session  : {body.sessionId}")
    print(f"    Role     : {body.role}")
    print(f"    Type     : {body.interviewType}  |  Difficulty: {body.difficulty}")
    print(f"    Messages : {len(body.messages)}")
    print("-" * 60)
    for msg in body.messages:
        speaker = "AI  " if msg.sender == "ai" else "USER"
        print(f"  [{speaker}] {msg.text}")
    print(f"{sep}\n")

    # ── 2. Append to conversation_log.json ───────────────────────────────────
    try:
        _append_json(_CONV_LOG_FILE, log_entry)
        print(f"[ConversationLog] ✓ JSON  → {_CONV_LOG_FILE}")
    except Exception as e:
        print(f"[ConversationLog] Warning: could not write JSON log: {e}")

    # ── 3. Write / append to conversation_log.txt (human-readable) ───────────
    try:
        with open(_CONV_TXT_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"INTERVIEW SESSION  |  {ts_display}\n")
            f.write(f"Session  : {body.sessionId}\n")
            f.write(f"Role     : {body.role}\n")
            f.write(f"Type     : {body.interviewType}  |  Difficulty: {body.difficulty}\n")
            f.write("-" * 60 + "\n")
            for msg in body.messages:
                speaker = "AI  " if msg.sender == "ai" else "USER"
                f.write(f"[{speaker}] {msg.text}\n")
            f.write(f"{'='*60}\n")
        print(f"[ConversationLog] ✓ TXT   → {_CONV_TXT_FILE}")
    except Exception as e:
        print(f"[ConversationLog] Warning: could not write TXT log: {e}")

    return {"status": "ok"}


@router.post("/Agent/analyze_audio")
async def analyze_audio_response(
    audio: UploadFile = File(..., description="WAV audio file of the candidate's answer"),
    question: str     = Form(default="", description="Interview question being answered"),
):
    """
    Accept a WAV recording of a candidate's spoken answer, run the full
    speech-confidence analysis pipeline, log results to audio_scores.json,
    and return all six dimension scores plus an overall confidence score.

    Expected multipart/form-data fields:
      - audio    : WAV file blob
      - question : (optional) text of the question that was asked

    Response JSON:
    {
      "timestamp": "...",
      "question": "...",
      "transcript": "...",
      "wpm": 145.0,
      "scores": {
        "rate_score": 10.0,
        "pause_score": 8.5,
        "filler_score": 9.0,
        "energy_score": 7.5,
        "clarity_score": 8.8,
        "pitch_score": 6.0
      },
      "overall_confidence": 8.6
    }
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided")

    wav_bytes = await audio.read()
    if len(wav_bytes) < 100:
        raise HTTPException(status_code=400, detail="Audio file appears to be empty")

    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n[{ts}] [AUDIO] Analysing speech for question: {question[:80]}")

    try:
        result = await audio_analysis_service.analyse_wav_bytes(wav_bytes, question=question)
    except Exception as exc:
        print(f"[AUDIO] Analysis failed: {exc}")
        raise HTTPException(status_code=500, detail=f"Audio analysis error: {exc}")

    print(
        f"[AUDIO] Done — WPM={result['wpm']:.0f}  "
        f"Confidence={result['overall_confidence']:.1f}/10  "
        f"Saved to audio_scores.json"
    )

    # Return a clean, structured response
    return {
        "timestamp":          result["timestamp"],
        "question":           result["question"],
        "transcript":         result["transcript"],
        "wpm":                result["wpm"],
        "avg_asr_confidence": result["avg_asr_confidence"],
        "pause_count":        result["pause_count"],
        "total_pause_seconds":result["total_pause_seconds"],
        "filler_count":       result["filler_count"],
        "scores": {
            "rate_score":     result["rate_score"],
            "pause_score":    result["pause_score"],
            "filler_score":   result["filler_score"],
            "energy_score":   result["energy_score"],
            "clarity_score":  result["clarity_score"],
            "pitch_score":    result["pitch_score"],
        },
        "overall_confidence": result["overall_confidence"],
    }
