import subprocess
import time
import requests
import json
import os

# 1. Starting the Proxy in a separate process
print("[TEST] Starting Zero Trust Proxy...")
proxy_proc = subprocess.Popen([os.path.join("venv", "Scripts", "python"), "zero_trust_vpn/vpn_proxy.py"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
time.sleep(2) # Wait for proxy to bind

# 2. Get a valid JWT for testing (from a previous session or simulate)
# In our project, we use 'admin1' / 'admin123'
# For this test, we skip the actual login flow and use a known valid structure 
# if we had a way to sign it, but it's easier to just show the redirection failure/success.

# We'll use a dummy JWT that's NOT signed by our HS256 secret to see a failure first.
dummy_jwt = "header.payload.signature"

print("\n[TEST] Attempt 1: Accessing /admin/users WITHOUT a valid token...")
try:
    # Hit the proxy directly on 8081
    resp = requests.get("http://127.0.0.1:8081/admin/users")
    print(f"Status (Expected 401/403): {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")

print("\n[TEST] Attempt 2: Accessing /admin/users WITH an invalid token...")
try:
    headers = {"X-VPN-Token": dummy_jwt}
    resp = requests.get("http://127.0.0.1:8081/admin/users", headers=headers)
    print(f"Status (Expected 403): {resp.status_code}")
    print(f"Body: {resp.text}")
except Exception as e:
    print(f"Exception: {e}")

# Cleanup
proxy_proc.terminate()
print("\n[TEST] Redirection test completed.")
