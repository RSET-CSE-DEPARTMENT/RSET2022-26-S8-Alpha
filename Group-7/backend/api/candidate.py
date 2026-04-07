"""
api/candidate.py

Candidate & interview proxy endpoints for the company backend:
  POST /db/check_candidate_login      → Check if candidate exists and interview is valid
  POST /db/fetch_coding_question      → Fetch coding question
  POST /db/insert_coding_score        → Insert coding score
  POST /db/insert_aptitude_score      → Insert aptitude score
"""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, Body, HTTPException, UploadFile, File, Form
from pydantic import BaseModel

from config import get_settings

router = APIRouter(tags=["Candidate"])
settings = get_settings()


# ─── Schemas ─────────────────────────────────────────────────────────────────

class CheckCandidateLoginRequest(BaseModel):
    cade_id: str
    interview_id: str


# ─── Helper Functions ────────────────────────────────────────────────────────

def _ngrok_url(path: str) -> str:
    """Build the full NGROK URL."""
    base = settings.ngrok_base_url.rstrip("/")
    return f"{base}{path}"


async def _call_company_api(method: str, path: str, json_data: dict = None, files_data: dict = None) -> dict[str, Any]:
    """
    Make an HTTP call to the company backend with proper error handling.
    
    Args:
        method: 'POST', 'GET', etc.
        path: URL path (e.g., '/db/check_candidate_login')
        json_data: JSON payload (for JSON POST)
        files_data: Files payload (for multipart POST)
    
    Returns:
        Response dictionary from company backend
        
    Raises:
        HTTPException: If API call fails
    """
    if not settings.ngrok_base_url:
        raise HTTPException(
            status_code=500,
            detail="NGROK_BASE_URL is not configured. Cannot reach company backend."
        )

    target_url = _ngrok_url(path)
    
    print(f"[candidate_service] {method} {target_url}")
    if json_data:
        print(f"[candidate_service] Payload: {json.dumps(json_data, indent=2, ensure_ascii=False)}")

    try:
        async with httpx.AsyncClient(timeout=20) as client:
            if method.upper() == "POST":
                if files_data:
                    # Multipart form data for file uploads
                    resp = await client.post(
                        target_url,
                        files=files_data,
                        headers={"ngrok-skip-browser-warning": "true"},
                    )
                else:
                    # JSON payload
                    resp = await client.post(
                        target_url,
                        json=json_data,
                        headers={"ngrok-skip-browser-warning": "true"},
                    )
                resp.raise_for_status()
                data = resp.json()
                print(f"[candidate_service] Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
                return data
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
                
    except httpx.HTTPStatusError as e:
        error_msg = f"Company API returned {e.response.status_code}: {e.response.text}"
        print(f"[candidate_service] ERROR: {error_msg}")
        raise HTTPException(status_code=e.response.status_code, detail=error_msg) from e
    except Exception as e:
        error_msg = f"Company API call failed: {type(e).__name__}: {e!r}"
        print(f"[candidate_service] ERROR: {error_msg}")
        raise HTTPException(status_code=500, detail=error_msg) from e


# ─── Routes ──────────────────────────────────────────────────────────────────

@router.post("/db/check_candidate_login")
async def check_candidate_login(body: CheckCandidateLoginRequest) -> dict[str, Any]:
    """
    Validate candidate login credentials.
    
    Proxies to company backend: POST /db/check_candidate_login
    
    Request:
        {
            "cade_id": "b29b12b0-154b-11f1-8e75-b19d6bec35cd",
            "interview_id": "1db56462-154a-11f1-b948-c9692e84c1a5"
        }
    
    Response:
        {
            "exists": true,
            "valid": true,
            "message": "Candidate and interview found"
        }
        OR
        {
            "exists": false,
            "valid": false,
            "message": "Candidate or interview not found"
        }
    """
    payload = {
        "cade_id": body.cade_id,
        "interview_id": body.interview_id,
    }
    
    result = await _call_company_api("POST", "/db/check_candidate_login", json_data=payload)
    
    return result


@router.post("/upload_resume")
async def upload_resume(
    file: UploadFile = File(...),
    cade_id: str = Form(default="unknown")
) -> dict[str, Any]:
    """
    Upload a candidate's resume to the company backend.
    
    Proxies to company backend: POST /upload_resume
    """
    # Read file contents
    file_contents = await file.read()
    
    print(f"[candidate_service] Uploading resume for candidate: {cade_id}")
    print(f"[candidate_service] File: {file.filename} ({len(file_contents) / 1024:.1f} KB)")
    
    # Prepare multipart form data
    files_data = {
        "file": (file.filename, file_contents, file.content_type),
        "cade_id": (None, cade_id)
    }
    
    result = await _call_company_api("POST", "/upload_resume", files_data=files_data)
    return result



@router.post("/db/fetch_coding_question")
async def fetch_coding_question(body: dict = Body(...)) -> dict[str, Any]:
    """Proxy coding question fetch to company backend."""
    return await _call_company_api("POST", "/db/fetch_coding_question", json_data=body)


@router.post("/db/insert_coding_score")
async def insert_coding_score(body: dict = Body(...)) -> dict[str, Any]:
    """Proxy coding score insert to company backend."""
    return await _call_company_api("POST", "/db/insert_coding_score", json_data=body)


@router.post("/db/insert_aptitude_score")
async def insert_aptitude_score(body: dict = Body(...)) -> dict[str, Any]:
    """Proxy aptitude score insert to company backend."""
    return await _call_company_api("POST", "/db/insert_aptitude_score", json_data=body)
