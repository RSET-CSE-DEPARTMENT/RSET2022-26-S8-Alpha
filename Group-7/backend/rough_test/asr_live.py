import requests
import time
import sys
import os
from dotenv import load_dotenv
from RealtimeSTT import AudioToTextRecorder

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("NGROK_BASE_URL", "http://localhost:8000")
API_URL = f"{BASE_URL}/evaluate_interview_conv"

QUESTION = "Explain the difference between list and tuple in Python."


def send_to_backend(question, answer):
    try:
        response = requests.post(
            API_URL,
            json={
                "question": question,
                "answer": answer
            },
            timeout=15
        )

        print("\n===== API RESPONSE =====")
        print("Status Code:", response.status_code)

        try:
            data = response.json()
            print("Response:", data)

            if response.status_code == 200:
                output = data["result"]["output"]
                print("\n📊 Evaluation Scores:")
                print("Relevance:", output.get("revelance"))
                print("Language Proficiency:", output.get("language_proficency"))
                print("Technical Knowledge:", output.get("tech_knowledge"))

        except:
            print("Raw Response:", response.text)

    except requests.exceptions.RequestException as e:
        print("Request failed:", e)


if __name__ == "__main__":
    print("\n===== AI MOCK INTERVIEW =====")
    print("Question:", QUESTION)
    print("\n🎤 Speak now (Auto-stop after 3s silence)...\n")

    recorder = AudioToTextRecorder(
        model=r"C:\whisper_models\small",
        device="cuda",
        compute_type="float16",
        language="en",
        post_speech_silence_duration=3.0
    )

    try:
        final_answer = recorder.text()
    except Exception as e:
        print("ASR Error:", e)
        sys.exit(1)

    print("\n===== FINAL ANSWER =====")
    print(final_answer)

    print("\nSending to evaluation API...")
    send_to_backend(QUESTION, final_answer)

    print("\nInterview Complete.")

    recorder.shutdown()  
    time.sleep(0.5) 

    sys.exit(0)
