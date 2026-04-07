import socket
import json
import time
import jwt
import os
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from dotenv import load_dotenv

load_dotenv()

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from zero_trust_vpn.crypto_utils import encrypt_payload, decrypt_payload, load_public_key

VPN_HOST = os.getenv("VPN_HOST", "127.0.0.1")
VPN_PORT = int(os.getenv("VPN_PORT", 5012))
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key") 

def get_token(user, role):
    payload = {"sub": user, "role": role, "iat": int(time.time()), "exp": int(time.time()) + 3600}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def send_blob(blob):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(3)
        s.connect((VPN_HOST, VPN_PORT))
        s.sendall(blob)
        return s.recv(4096).decode()

def run_security_tests():
    print("=== ZERO TRUST VPN SECURITY TEST SUITE ===\n")
    
    public_key_path = "zero_trust_vpn/keys/public.pem"
    pub_key = load_public_key(public_key_path)

    # --- TEST 1: REPLAY ATTACK ---
    print("[TEST 1] Replay Attack Simulation")
    student_jwt = get_token("student1", "student")
    payload = {"path": "/dashboard", "jwt": student_jwt}
    blob = encrypt_payload(json.dumps(payload), pub_key)
    
    print("  > Sending original blob...")
    resp1 = send_blob(blob)
    print(f"  > First Response: {resp1}")
    
    print("  > Replaying same blob...")
    resp2 = send_blob(blob)
    print(f"  > Replay Response: {resp2}")
    if resp1 == resp2:
        print("  [!] VULNERABILITY: Replay Attack Succeeded (No tunnel-level nonce/timestamp detected).")
    else:
        print("  [OK] Replay Attack Blocked.")

    # --- TEST 2: MITM / DATA TAMPERING ---
    print("\n[TEST 2] MITM / Data Tampering Simulation")
    # Tamper with the ciphertext part of the blob
    tampered_blob = bytearray(blob)
    tampered_blob[-5] = (tampered_blob[-5] + 1) % 256 # Flip a bit
    
    print("  > Sending tampered blob...")
    try:
        resp_tamper = send_blob(bytes(tampered_blob))
        print(f"  > Tamper Response: {resp_tamper}")
        if "DECRYPT_ERROR" in resp_tamper:
            print("  [OK] Tampering detected (Decryption Failed).")
        else:
            print("  [!] VULNERABILITY: Tampered data accepted or handled incorrectly.")
    except Exception as e:
        print(f"  > Error: {e}")

    # --- TEST 3: UNAUTHORIZED ROLE ACCESS ---
    print("\n[TEST 3] Unauthorized Role Access (RBAC Bypass)")
    payload_admin = {"path": "/admin/users", "jwt": student_jwt}
    blob_admin = encrypt_payload(json.dumps(payload_admin), pub_key)
    
    print("  > student1 attempting access to /admin/users...")
    resp_rbac = send_blob(blob_admin)
    print(f"  > RBAC Response: {resp_rbac}")
    if "DENY_RBAC" in resp_rbac or "JWT_DOWNGRADED" in resp_rbac:
        print("  [OK] RBAC Enforced: Access Denied.")
    else:
        print("  [!] VULNERABILITY: RBAC bypass suspected.")

    # --- TEST 4: SESSION PERSISTENCE & HANDSHAKE ---
    print("\n[TEST 4] Session Management (Handshake & Reuse)")
    handshake_payload = {"action": "HANDSHAKE", "jwt": student_jwt}
    handshake_blob = encrypt_payload(json.dumps(handshake_payload), pub_key)
    
    print("  > Performing Handshake...")
    resp_hs = send_blob(handshake_blob)
    print(f"  > Handshake Response: {resp_hs}")
    
    if "SESSION_ESTABLISHED" in resp_hs:
        sess_id = resp_hs.split(":")[1]
        print(f"  > Using Session ID: {sess_id} for path check...")
        sess_payload = {"session_id": sess_id, "path": "/dashboard"}
        sess_blob = encrypt_payload(json.dumps(sess_payload), pub_key)
        resp_sess = send_blob(sess_blob)
        print(f"  > Session Path Response: {resp_sess}")
        if "ALLOWED" in resp_sess:
            print("  [OK] Session handling functional.")
        else:
            print("  [!] Session reuse failed.")
    else:
        print("  [!] Handshake failed.")

if __name__ == "__main__":
    run_security_tests()
