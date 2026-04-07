"""
main.py — Intervexa FastAPI Backend

Start with:
    uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings
from api.agent import router as agent_router
from api.interview.ws_room import router as ws_router
from api.confidence import router as confidence_router
from api.execute import router as execute_router
from api.candidate import router as candidate_router

settings = get_settings()

app = FastAPI(
    title="Intervexa AI Interviewer API",
    description="Backend for the Intervexa AI-powered interview platform",
    version="1.0.0",
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin, "http://localhost:3000", "http://localhost:5173", "http://localhost:5174"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ───────────────────────────────────────────────────────────────────
app.include_router(agent_router)
app.include_router(ws_router)
app.include_router(confidence_router)
app.include_router(execute_router)
app.include_router(candidate_router)

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "ok",
        "tts_voice": settings.tts_voice,
        "openai_configured": bool(settings.openai_api_key),
    }
