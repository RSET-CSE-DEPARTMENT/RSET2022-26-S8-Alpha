import json
import time
import sys
from datetime import datetime
from RealtimeSTT import AudioToTextRecorder


# ================= CONFIG =================

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


# ================= MOCKED API FUNCTIONS =================

def upload_resume():
    print("\n[MOCK] Uploading resume...")
    time.sleep(1)
    print("[MOCK] Resume uploaded successfully.")


def generate_question(conversation_history):
    """
    Mock question generator.
    Uses conversation length to simulate dynamic flow.
    """

    question_bank = [
        "Tell me about yourself.",
        "Explain a challenging project you worked on.",
        "What is the difference between list and tuple in Python?",
        "How do you handle asynchronous programming in FastAPI?"
    ]

    index = len(conversation_history) % len(question_bank)
    return question_bank[index]


def evaluate_answer(question, answer):
    """
    Mock evaluation response.
    Generates fake but realistic scoring.
    """

    mock_response = {
        "status": "success",
        "result": {
            "question": question,
            "answer": answer,
            "output": {
                "revelance": 0.85,
                "language_proficency": 0.90,
                "tech_knowledge": 0.80
            }
        }
    }

    return mock_response


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

        # Mock Evaluation
        evaluation_result = evaluate_answer(question, answer)

        append_json("evaluation_log.json", {
            "timestamp": str(datetime.now()),
            "evaluation": evaluation_result
        })

        print("\n📊 Mock Evaluation Scores:")
        output = evaluation_result["result"]["output"]
        print("Relevance:", output["revelance"])
        print("Language Proficiency:", output["language_proficency"])
        print("Technical Knowledge:", output["tech_knowledge"])

    recorder.shutdown()
    print("\nInterview Complete.")


# ================= ENTRY =================

if __name__ == "__main__":
    upload_resume()
    run_interview()
