"""
services/agent_service.py

Calls the AI server (exposed via ngrok) for question generation
and answer evaluation:

  POST {NGROK_BASE_URL}/Agent/generate_question
  POST {NGROK_BASE_URL}/Agent/evaluate_interview_conv

No mock/fallback — both endpoints require NGROK_BASE_URL to be set.
"""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

import httpx

from config import get_settings

settings = get_settings()

def _ngrok_url(path: str) -> str:
    base = settings.ngrok_base_url.rstrip("/")
    return f"{base}{path}"


# ─── Public API ──────────────────────────────────────────────────────────────

async def generate_question(
    conversation_history: list[dict],
    cade_id: str | None = None,
    interview_id: str | None = None,
) -> str:
    """Generate the next interview question."""
    if not settings.ngrok_base_url:
        raise RuntimeError("NGROK_BASE_URL is not set; cannot call question generation API")

    # Ensure every entry has the expected { AIMessage, HumanMessage } shape.
    normalised: list[dict] = []
    for turn in conversation_history:
        normalised.append({
            "AIMessage": turn.get("AIMessage", ""),
            "HumanMessage": turn.get("HumanMessage", ""),
        })

    payload: dict = {"conversation": normalised}
    if cade_id:
        payload["cade_id"] = cade_id
    if interview_id:
        payload["interview_id"] = interview_id

    target_url = _ngrok_url("/Agent/generate_question")
    print(f"[agent_service] POST {target_url}")
    print(f"[agent_service] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"[agent_service] Response: {json.dumps(data, indent=2, ensure_ascii=False)}")

            if isinstance(data, dict):
                question = (
                    data.get("generated_question")
                    or data.get("question")
                    or data.get("text")
                    or str(data)
                )
                return question
            return str(data)
    except Exception as e:
        raise RuntimeError(
            f"External question generation API call failed: {type(e).__name__}: {e!r}"
        ) from e


async def evaluate_answer(question: str, answer: str) -> dict[str, Any]:
    """Evaluate a candidate's answer."""
    if not settings.ngrok_base_url:
        raise RuntimeError("NGROK_BASE_URL is not set; cannot call external evaluation API")

    target_url = _ngrok_url("/Agent/evaluate_interview_conv")
    payload = {"question": question, "answer": answer}

    print(f"[agent_service] POST {target_url}")
    print(f"[agent_service] Question: {question}")
    print(f"[agent_service] Answer: {answer}")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"[agent_service] Evaluation Result:\n{json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
    except Exception as e:
        print(f"[agent_service] Evaluation API failed: {e}")
        raise RuntimeError(f"External evaluation API call failed: {e}") from e


async def insert_tech_score(
    cade_id: str,
    interview_id: str,
    evaluation: dict[str, Any],
) -> dict[str, Any]:
    """Post per-question tech scores extracted from evaluation output."""
    if not settings.ngrok_base_url:
        raise RuntimeError("NGROK_BASE_URL is not set; cannot call insert_tech_score API")

    output = evaluation.get("result", {}).get("output", {})

    payload = {
        "candidate_id": cade_id,
        "interview_id": interview_id,
        "output": {
            "tech_revelance": output.get("revelance", 0),
            "tech_language_proficency": output.get("language_proficency", 0),
            "tech_knowledge": output.get("tech_knowledge", 0),
        },
    }

    target_url = _ngrok_url("/db/insert_tech_score")
    print(f"[agent_service] POST {target_url}")
    print(f"[agent_service] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"[agent_service] Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
    except Exception as e:
        print(f"[agent_service] insert_tech_score failed: {e}")
        return {"error": str(e)}


async def calculate_final_score(
    cade_id: str,
    interview_id: str,
) -> dict[str, Any]:
    """Calculate the final interview score at the end of the interview."""
    if not settings.ngrok_base_url:
        raise RuntimeError("NGROK_BASE_URL is not set; cannot call calculate_final_score API")

    payload = {
        "candidate_id": cade_id,
        "interview_id": interview_id,
    }

    target_url = _ngrok_url("/db/calculate_final_score")
    print(f"[agent_service] POST {target_url}")
    print(f"[agent_service] Payload: {json.dumps(payload, indent=2, ensure_ascii=False)}")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.post(
                target_url,
                json=payload,
                headers={"ngrok-skip-browser-warning": "true"},
            )
            resp.raise_for_status()
            data = resp.json()
            print(f"[agent_service] Final interview score calculated")
            print(f"[agent_service] Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
            return data
    except Exception as e:
        print(f"[agent_service] calculate_final_score failed: {e}")
        return {"error": str(e)}


