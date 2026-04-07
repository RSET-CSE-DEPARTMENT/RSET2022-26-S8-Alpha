import requests
import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
BASE_URL = os.getenv("NGROK_BASE_URL", "http://localhost:8000")
url = f"{BASE_URL}/upload_resume"

data = {
    "cade_id": "abin_67461481741274891"
}

files = {
    "file": open("resume1.pdf", "rb")  # Change to your file path
}

response = requests.post(url, data=data, files=files)

print("Status Code:", response.status_code)
print("Response:", response.text)
