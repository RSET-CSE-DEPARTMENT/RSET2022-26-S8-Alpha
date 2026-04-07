"""
api/confidence.py

REST endpoints for video confidence analysis.
"""

from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from services import video_confidence_service

router = APIRouter(tags=["Confidence"])

@router.post("/confidence/evaluate")
async def evaluate_confidence(
    interview_id: str = Form(""),
    cade_id: str = Form(""),
    video: UploadFile = File(...)
):
    if not video.filename:
        raise HTTPException(status_code=400, detail="No video file provided")

    video_bytes = await video.read()
    if len(video_bytes) < 100:
        raise HTTPException(status_code=400, detail="Video file appears to be empty")

    try:
        result = video_confidence_service.analyze_video_blob(video_bytes, interview_id, cade_id)
        return result
    except Exception as e:
        # Return a safe fallback instead of crashing the server
        print(f"[confidence] ⚠️ analyze_video_blob crashed: {e}")
        return {
            "status": False,
            "interview_id": interview_id,
            "cade_id": cade_id,
            "confidence_analysis": {
                "eye_contact_score": 0.5,
                "blink_score": 0.5,
                "movement_score": 0.5,
                "final_confidence_score": 0.5,
            },
            "error": str(e),
        }
