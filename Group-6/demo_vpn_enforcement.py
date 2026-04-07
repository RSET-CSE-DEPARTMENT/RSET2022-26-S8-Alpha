import requests
import jwt
import os
import sys
import time
import subprocess
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")
PROXY_URL = "http://127.0.0.1:8081"

def generate_token(username, role):
    payload = {
        "sub": username,
        "role": role,
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def run_test():
    print("=== ZERO TRUST VPN ENFORCEMENT DEMO ===")
    
    # 1. Generate a STUDENT Token
    student_token = generate_token("student1", "student")
    print(f"[DEMO] Generated Token for: student1 (Role: student)")

    # 2. Try to access Student Dashboard (ALLOWED)
    print("\n[DEMO] Attempt 1: student1 accessing /dashboard (Expected: 200 ALLOWED)")
    try:
        headers = {"X-VPN-Token": student_token}
        resp = requests.get(f"{PROXY_URL}/dashboard", headers=headers)
        print(f"Result: {resp.status_code} - Proceeding to backend.")
    except Exception as e:
        print(f"Error: {e}")

    # 3. Try to access Admin Users (DENIED)
    print("\n[DEMO] Attempt 2: student1 accessing /admin/users (Expected: 403 DENIED)")
    try:
        headers = {"X-VPN-Token": student_token}
        resp = requests.get(f"{PROXY_URL}/admin/users", headers=headers)
        print(f"Result: {resp.status_code}")
        print(f"Message from Proxy: {resp.text}")
    except Exception as e:
        print(f"Error: {e}")

    # 4. Generate an ADMIN Token
    admin_token = generate_token("admin1", "admin")
    print(f"\n[DEMO] Generated Token for: admin1 (Role: admin)")

    # 5. Try to access Admin Users (ALLOWED)
    print("\n[DEMO] Attempt 3: admin1 accessing /admin/users (Expected: 200 ALLOWED)")
    try:
        headers = {"X-VPN-Token": admin_token}
        resp = requests.get(f"{PROXY_URL}/admin/users", headers=headers)
        print(f"Result: {resp.status_code} - Proceeding to backend.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    # Ensure Proxy is running (Start in background if not)
    print("[DEMO] Checking if Zero Trust Proxy is active...")
    # Starting proxy in background for the demo
    proxy_proc = subprocess.Popen([sys.executable, "zero_trust_vpn/vpn_proxy.py"], 
                                  stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(3) # Wait for proxy to start
    
    try:
        run_test()
    finally:
        proxy_proc.terminate()
        print("\n=== DEMO COMPLETED ===")
