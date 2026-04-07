import os
import logging
import json
import base64
import requests
from typing import List
from datetime import datetime, timedelta
import pytz

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
import google.generativeai as genai
from pymongo import MongoClient

# Google Calendar API imports
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# Load environment variables
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Nyaya Sahayi Backend")

# Enable CORS for frontend interaction
app.add_middleware(
    CORSMiddleware, 
    allow_origins=["*"], 
    allow_credentials=True, 
    allow_methods=["*"], 
    allow_headers=["*"]
)

# ==========================================
# CONFIGURATIONS (Gemini & MongoDB)
# ==========================================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-2.5-flash-lite') 

MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    db = MongoClient(MONGO_URI)["nyaya_db"]
    clients_collection = db["clients"]
    appointments_collection = db["appointments"]
else:
    logger.warning("MONGO_URI not set. Database features will fail.")
    clients_collection = None
    appointments_collection = None

# ==========================================
# DATA MODELS
# ==========================================
class HistoryItem(BaseModel):
    role: str  # "user" or "ai"
    content: str

class ChatRequest(BaseModel):
    message: str
    client_id: str = "default_client"
    history: List[HistoryItem] = []

class BookRequest(BaseModel):
    client_id: str
    date: str       # "YYYY-MM-DD"
    time: str       # "10:00 AM"

def format_history(history: List[HistoryItem]) -> str:
    if not history:
        return "No previous conversation."
    return "\n".join([f"{h.role.upper()}: {h.content}" for h in history[-12:]]) 

# ==========================================
# SARVAM AI TEXT-TO-SPEECH (REST)
# ==========================================
def generate_malayalam_audio(text: str) -> str:
    """Converts Malayalam text to speech using Sarvam AI."""
    sarvam_key = os.getenv("SARVAM_API_KEY")
    if not sarvam_key:
        logger.warning("SARVAM_API_KEY not found. Skipping audio generation.")
        return None

    url = "https://api.sarvam.ai/text-to-speech"
    headers = {
        "api-subscription-key": sarvam_key,
        "Content-Type": "application/json"
    }
    
    clean_text = text.replace('\n', ' ').strip()
    
    payload = {
        "inputs": [clean_text],
        "target_language_code": "ml-IN",
        "speaker": "anushka",
        "pitch": 0,
        "pace": 1.0,
        "loudness": 1.5,
        "speech_sample_rate": 8000,
        "enable_preprocessing": True,
        "model": "bulbul:v2" 
    }
    
    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if "audios" in data and len(data["audios"]) > 0:
                return data["audios"][0]
        else:
            logger.error(f"Sarvam API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logger.error(f"TTS Request Error: {e}")
        return None

# ==========================================
# GOOGLE CALENDAR HELPERS
# ==========================================
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv("LAWYER_CALENDAR_ID", "primary")
TZ = pytz.timezone('Asia/Kolkata')

def get_calendar_service():
    if not os.path.exists("service_account.json"):
        return None
    try:
        creds = Credentials.from_service_account_file('service_account.json', scopes=SCOPES)
        return build('calendar', 'v3', credentials=creds)
    except Exception as e:
        logger.error(f"Failed to initialize Calendar service: {e}")
        return None

def get_available_slots() -> list:
    now = datetime.now(TZ)
    busy_periods = []
    service = get_calendar_service()

    if service:
        try:
            time_min = now.isoformat()
            time_max = (now + timedelta(days=14)).isoformat()

            events_result = service.events().list(
                calendarId=CALENDAR_ID, timeMin=time_min, timeMax=time_max,
                singleEvents=True, orderBy='startTime').execute()
            
            for event in events_result.get('items', []):
                start_str = event['start'].get('dateTime', event['start'].get('date'))
                end_str = event['end'].get('dateTime', event['end'].get('date'))
                if 'T' in start_str:
                    busy_periods.append((
                        datetime.fromisoformat(start_str.replace('Z', '+00:00')),
                        datetime.fromisoformat(end_str.replace('Z', '+00:00'))
                    ))
        except Exception as e:
            logger.error(f"Calendar Fetch Error: {e}")
    else:
        logger.warning("Calendar service unavailable. Showing all default slots as available.")

    available_slots = []
    for day_offset in range(1, 15):
        target_date = now + timedelta(days=day_offset)
        if target_date.weekday() >= 5:
            continue

        day_slots = []
        for hour in [10, 11, 14, 15, 16]: 
            slot_start = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            slot_end = slot_start + timedelta(hours=1)

            conflict = any(
                not (slot_end <= bs or slot_start >= be) for bs, be in busy_periods
            )
            if not conflict:
                day_slots.append(slot_start.strftime("%I:%M %p").lstrip('0'))

        if day_slots:
            available_slots.append({
                "date": target_date.strftime("%Y-%m-%d"),
                "day": target_date.strftime("%A"),
                "slots": day_slots
            })

    return available_slots

# ==========================================
# AGENTS & ROUTING
# ==========================================
def get_intent(user_message: str, history: List[HistoryItem]) -> str:
    history_text = format_history(history)
    prompt = f"""
    CHAT HISTORY:
    {history_text}
    
    NEW MESSAGE: '{user_message}'
    
    TASK: Based on the conversation history and the new message, is the user asking about a CASE or trying to SCHEDULE/confirm a meeting? 
    Reply with exactly one word: CASE or SCHEDULE.
    """
    try:
        response = model.generate_content(prompt)
        intent = response.text.strip().upper()
        return "SCHEDULE" if "SCHEDULE" in intent else "CASE"
    except Exception as e:
        logger.error(f"Router Error: {e}")
        return "CASE"

def handle_scheduling(client_id: str):
    slots = get_available_slots()
    
    if not slots:
        msg = "ക്ഷമിക്കണം, അടുത്ത ദിവസങ്ങളിൽ ലഭ്യമായ സ്ലോട്ടുകൾ ഒന്നുമില്ല."
        audio_b64 = generate_malayalam_audio(msg)
        return {
            "response": msg,
            "type": "text",
            "audio": audio_b64
        }
        
    msg = "ദയവായി നിങ്ങൾക്ക് സൗകര്യപ്രദമായ തീയതിയും സമയവും തിരഞ്ഞെടുക്കുക:"
    audio_b64 = generate_malayalam_audio(msg)
    
    return {
        "type": "calendar",
        "message": msg,
        "available_slots": slots,
        "audio": audio_b64
    }

def handle_case_query(user_message: str, client_id: str, history: List[HistoryItem]):
    case_context = "No data."
    if clients_collection is not None:
        client_data = clients_collection.find_one({"client_id": client_id}, {"_id": 0})
        if client_data:
            case_context = str(client_data)
            
    history_text = format_history(history)
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "reply_malayalam": {"type": "STRING"},
            "found_in_context": {"type": "BOOLEAN"}
        }
    }
    
    prompt = f"""
    CHAT HISTORY: {history_text}
    CASE FILE: {case_context}
    NEW MESSAGE: {user_message}
    
    TASK: Answer user in Malayalam ONLY using the Case File. Use the chat history to understand the context of their question.
    If the info is missing from the Case File or requires general legal advice, set found_in_context to false.
    """
    
    response = model.generate_content(
        prompt, 
        generation_config={"response_mime_type": "application/json", "response_schema": schema}
    )
    data = json.loads(response.text)
    
    if not data.get("found_in_context"):
        fallback_msg = "ക്ഷമിക്കണം, നിങ്ങളുടെ കേസ് ഫയലിലുള്ള കാര്യങ്ങൾ മാത്രമേ എനിക്ക് പറയാൻ കഴിയൂ, നിയമപരമായ ഉപദേശങ്ങൾ നൽകാൻ എനിക്ക് അധികാരമില്ല."
        audio_b64 = generate_malayalam_audio(fallback_msg)
        return {"response": fallback_msg, "audio": audio_b64}
    
    reply_msg = data.get("reply_malayalam")
    audio_b64 = generate_malayalam_audio(reply_msg)
    
    return {
        "response": reply_msg,
        "audio": audio_b64
    }

# ==========================================
# ENDPOINTS
# ==========================================
@app.post("/api/book")
async def book_appointment(request: BookRequest):
    if appointments_collection is None:
        raise HTTPException(status_code=500, detail="Database not configured")

    try:
        existing_booking = appointments_collection.find_one({
            "client_id": request.client_id,
            "date": request.date,
            "status": "booked"
        })
        
        if existing_booking:
            raise HTTPException(
                status_code=400, 
                detail="ഒരു ദിവസം ഒരു മീറ്റിംഗ് മാത്രമേ ബുക്ക് ചെയ്യാൻ സാധിക്കൂ. (You can only book one meeting per day.)"
            )

        start_dt_unaware = datetime.strptime(f"{request.date} {request.time}", "%Y-%m-%d %I:%M %p")
        start_dt = TZ.localize(start_dt_unaware)
        end_dt = start_dt + timedelta(hours=1)

        service = get_calendar_service()
        if not service:
             raise HTTPException(status_code=500, detail="Calendar service is unavailable.")

        events_result = service.events().list(
            calendarId=CALENDAR_ID,
            timeMin=start_dt.isoformat(),
            timeMax=end_dt.isoformat(),
            singleEvents=True
        ).execute()

        if events_result.get('items', []):
            raise HTTPException(
                status_code=409, 
                detail="ക്ഷമിക്കണം, ഈ സ്ലോട്ട് ഇപ്പോൾ മറ്റൊരാൾ ബുക്ക് ചെയ്തിട്ടുണ്ട്. മറ്റൊരു സമയം തിരഞ്ഞെടുക്കുക."
            )

        event_body = {
            'summary': f'Legal Consultation - {request.client_id}',
            'description': f'Automatically scheduled via Nyaya Sahayi Bot for Client ID: {request.client_id}',
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Kolkata',
            },
        }
        
        service.events().insert(calendarId=CALENDAR_ID, body=event_body).execute()

        appointments_collection.insert_one({
            "client_id": request.client_id,
            "date": request.date,
            "time": request.time,
            "status": "booked",
            "created_at": datetime.now()
        })
        
        logger.info(f"Booked {request.date} {request.time} for {request.client_id}")
        return {
            "success": True,
            "message": f"മീറ്റിംഗ് വിജയകരമായി ബുക്ക് ചെയ്തു!\n📅 {request.date}\n🕐 {request.time}"
        }
        
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Booking Error: {repr(e)}")
        raise HTTPException(status_code=500, detail="Booking failed due to a server error.")

@app.post("/api/chat")
async def chat_endpoint(request: ChatRequest):
    try:
        if "schedule" in request.message.lower() or "ബുക്ക്" in request.message:
            intent = "SCHEDULE"
            logger.info(f"Intent - schedule ")
        else:
            intent = get_intent(request.message, request.history)
            logger.info(f"Detected Intent: {intent} for Client: {request.client_id}")
        
        if intent == "SCHEDULE":
            return handle_scheduling(request.client_id)
        else:
            return handle_case_query(request.message, request.client_id, request.history)
            
    except Exception as e:
        logger.error(f"Endpoint Error: {repr(e)}")
        return {"response": "ക്ഷമിക്കണം, ഒരു സാങ്കേതിക തകരാർ ഉണ്ട്. ദയവായി അല്പം കഴിഞ്ഞ് വീണ്ടും ശ്രമിക്കുക."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)