import requests
import json
import time
import sys
import os
from datetime import datetime
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder

# ================= CONFIG =================

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("NGROK_BASE_URL", "http://localhost:8000")

RESUME_UPLOAD_URL = f"{BASE_URL}/upload_resume"
QUESTION_API_URL = f"{BASE_URL}/Agent/generate_question"
EVALUATION_API_URL = f"{BASE_URL}/Agent/evaluate_interview_conv"

CADE_ID = "abin_67461481741274891"
RESUME_PATH = "resume1.pdf"

MAX_QUESTIONS = 3


# ================= UTILITIES =================

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


def append_json(filename, new_data):
    try:
        with open(filename, "r") as f:
            data = json.load(f)
    except:
        data = []

    data.append(new_data)

    with open(filename, "w") as f:
        json.dump(data, f, indent=4)


# ================= STEP 1: Upload Resume =================

def upload_resume():
    print("\nUploading resume...")

    with open(RESUME_PATH, "rb") as f:
        response = requests.post(
            RESUME_UPLOAD_URL,
            data={"cade_id": CADE_ID},
            files={"file": f}
        )

    print("Upload Status:", response.status_code)
    print("Response:", response.text)

    if response.status_code != 200:
        print("Resume upload failed.")
        sys.exit(1)


# ================= STEP 2: Generate Question =================

def generate_question(conversation_history):
    response = requests.post(
        QUESTION_API_URL,
        json=conversation_history,
        timeout=20
    )

    if response.status_code != 200:
        print("Question generation failed:", response.text)
        sys.exit(1)

    data = response.json()

    # Adjust based on actual response structure
    question = data.get("question") if isinstance(data, dict) else data

    return question


# ================= STEP 3: Evaluate Answer =================

def evaluate_answer(question, answer):
    response = requests.post(
        EVALUATION_API_URL,
        json={
            "question": question,
            "answer": answer
        },
        timeout=20
    )

    if response.status_code != 200:
        print("Evaluation failed:", response.text)
        return None

    return response.json()


# ================= MAIN INTERVIEW LOOP =================

def run_interview():
    conversation_history = []
    conversation_log = []

    recorder = AudioToTextRecorder(
        model=r"C:\whisper_models\small",
        device="cuda",
        compute_type="float16",
        language="en",
        post_speech_silence_duration=3.0
    )

    for i in range(MAX_QUESTIONS):

        print(f"\n===== QUESTION {i+1} =====")

        question = generate_question(conversation_history)
        print("AI:", question)

        print("\n🎤 Speak now...\n")

        try:
            answer = recorder.text()
        except Exception as e:
            print("ASR Error:", e)
            break

        print("\nYour Answer:", answer)

        # Store conversation
        conversation_history.append({
            "AIMessage": question,
            "HumanMessage": answer
        })

        conversation_log.append({
            "timestamp": str(datetime.now()),
            "question": question,
            "answer": answer
        })

        save_json("conversation_log.json", conversation_log)

        # Evaluate
        evaluation_result = evaluate_answer(question, answer)

        if evaluation_result:
            append_json("evaluation_log.json", {
                "timestamp": str(datetime.now()),
                "evaluation": evaluation_result
            })

            print("\n📊 Evaluation Stored.")

    recorder.shutdown()
    print("\nInterview Complete.")


# ================= ENTRY =================

if __name__ == "__main__":
    upload_resume()
    run_interview()
