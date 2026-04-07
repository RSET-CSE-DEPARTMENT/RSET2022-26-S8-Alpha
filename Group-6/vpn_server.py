# zero_trust_vpn/vpn_server.py
# =========================
# Zero Trust Policy Server with RSA + AES Encryption
# =========================

import socket
import json
import jwt
import threading
import os
import sys
import struct
from dotenv import load_dotenv

# Add the root directory to sys.path to import db_adapter
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Add the current directory to sys.path for crypto_utils
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import time
import secrets
from crypto_utils import decrypt_payload, load_private_key
from db_adapter import db_adapter

load_dotenv()

HOST = os.getenv("VPN_HOST", "127.0.0.1")
PORT = int(os.getenv("VPN_PORT", "5012"))
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")

PRIVATE_KEY_PATH = os.path.join(os.path.dirname(__file__), "keys", "private.pem")

# Load RSA private key on startup
try:
    PRIVATE_KEY = load_private_key(PRIVATE_KEY_PATH)
    print(f"[VPN] RSA private key loaded from {PRIVATE_KEY_PATH}")
except FileNotFoundError:
    print(f"[VPN] ERROR: RSA private key not found at {PRIVATE_KEY_PATH}")
    print("[VPN] Run: python zero_trust_vpn/generate_keys.py")
    sys.exit(1)

try:
    from logger import log_event, log_suspicious, log_vpn_decision, log_error
except ImportError:
    def log_event(m): print(f"[LOG] {m}")
    def log_suspicious(u, m, d): print(f"[SUSPICIOUS] {u}: {m} | {d}")
    def log_vpn_decision(u, r, p, a, t): print(f"[VPN] {a} | {u} | {r} | {p} | trust:{t}")
    def log_error(m): print(f"[ERROR] {m}")

# Trust store and sessions are now handled via database

# Paths that are always allowed regardless of role
PUBLIC_PATHS = [
    "/logout",
    "/login",
    "/public-request-help",
    "/verify_otp",
    "/dashboard",  # Handled via RBAC but allowing public check fallback
    "/restricted",  # Low-trust landing page — must be reachable without RBAC penalty to avoid redirect loop
]

# RBAC policy
POLICY = {
    "student": ["/student", "/dashboard"],
    "parent":  ["/parent",  "/dashboard"],
    "faculty": ["/faculty", "/dashboard"],
    "admin":   ["/admin",   "/faculty",  "/dashboard"],  # admin can access faculty routes too
}

BASE_TRUST = 100

# How many points to deduct per RBAC violation
RBAC_PENALTY = 5  # was 15 — too aggressive

# Trust threshold below which session is terminated
TERMINATE_THRESHOLD = 10  # was 40 — way too aggressive

# Replay protection threshold (seconds)
REPLAY_WINDOW = 30
seen_nonces = set()
nonce_lock  = threading.Lock()

# Replay protection nonces are currently local (could be moved to Redis in a cluster)
# Session timeout for database cleanup
SESSION_TIMEOUT = 3600  # 1 hour

def allowed(role, path):
    for allowed_path in POLICY.get(role, []):
        if path.startswith(allowed_path):
            return True
    return False


def handle_client(conn, addr):
    print(f"[VPN TRACE] Handling client from {addr}")
    try:
        # Read 4-byte total message length
        header = conn.recv(4)
        if not header or len(header) < 4:
            print(f"[VPN TRACE] No header from {addr}")
            return
        total_len = struct.unpack(">I", header)[0]
        print(f"[VPN TRACE] total_len: {total_len}")

        # Read the entire message body
        wire_data = b""
        while len(wire_data) < total_len:
            part = conn.recv(min(4096, total_len - len(wire_data)))
            if not part: break
            wire_data += part
        
        print(f"[VPN TRACE] wire_data len: {len(wire_data)}")
        
        if len(wire_data) < total_len:
            print(f"[VPN TRACE] Incomplete message from {addr}")
            return

        # ─── RSA + AES Decrypt ───────────────────────────────────────────────
        try:
            plaintext = decrypt_payload(wire_data, PRIVATE_KEY)
            print(f"[VPN TRACE] Decryption successful.")
            request_data = json.loads(plaintext)
            print(f"[VPN TRACE] JSON parsed: {request_data.get('action', 'PATH_CHECK')}")
        except Exception as e:
            err_msg = f"DECRYPT_ERROR: {str(e)}"
            print(f"[VPN TRACE] {err_msg}")
            conn.sendall(err_msg.encode())
            return

        # ─── Replay Protection ───────────────────────────────────────────────
        ts = request_data.get("ts", 0)
        nonce = request_data.get("nonce")
        
        if abs(time.time() - ts) > REPLAY_WINDOW:
            print(f"[VPN] REPLAY_ATTACK_DETECTED: Timestamp {ts} is outside window.")
            conn.sendall(b"REPLAY_DETECTED")
            return
            
        with nonce_lock:
            if nonce in seen_nonces:
                print(f"[VPN] REPLAY_ATTACK_DETECTED: Nonce {nonce} already seen.")
                conn.sendall(b"REPLAY_DETECTED")
                return
            seen_nonces.add(nonce)

        path = request_data.get("path", "")
        action = request_data.get("action", "PATH_CHECK")

        # ─── Auth Resolution (JWT) ────────────────────────────────
        jwt_token = request_data.get("jwt")
        print(f"[VPN DEBUG] JWT: {jwt_token}")
        if not jwt_token:
            conn.sendall(b"AUTH_REQUIRED")
            return
        try:
            payload = jwt.decode(jwt_token, JWT_SECRET, algorithms=["HS256"])
            username = payload["sub"]
            role = payload["role"]
        except Exception as e:
            print(f"[VPN] JWT decode failed: {e}")
            conn.sendall(b"TOKEN_INVALID")
            return

        # ─── Auth Resolution (DB) ───────────────────────────────────────────
        db_conn = db_adapter.get_connection()
        try:
            user_record = db_conn.fetchone("SELECT trust_score FROM users WHERE username = ?", (username,))
            if not user_record:
                # Fallback for new users or if not in DB yet
                trust = BASE_TRUST
            else:
                trust = user_record["trust_score"]
        except Exception as e:
            print(f"[VPN] DB Trust Fetch Error: {e}")
            trust = BASE_TRUST

        # ─── Always allow public/utility paths ──────────────────────────────
        if any(path.startswith(p) for p in PUBLIC_PATHS):
            log_vpn_decision(username, role, path, "ALLOW_PUBLIC", trust)
            conn.sendall(f"ALLOWED:{path}".encode())
            return

        # ─── Low trust → terminate session ──────────────────────────────────
        if trust < TERMINATE_THRESHOLD:
            log_suspicious(username, "Trust critically low", f"Trust={trust}")
            conn.sendall(b"SESSION_TERMINATED_LOW_TRUST")
            return

        # ─── RBAC check ─────────────────────────────────────────────────────
        if not allowed(role, path):
            trust = max(0, trust - RBAC_PENALTY)
            
            try:
                db_conn.execute("UPDATE users SET trust_score = ? WHERE username = ?", (trust, username))
                db_conn.execute(
                    "INSERT INTO trust_history (user_id, old_score, new_score, reason, timestamp) VALUES ((SELECT id FROM users WHERE username=?), ?, ?, ?, ?)",
                    (username, user_record["trust_score"] if user_record else BASE_TRUST, trust, f"RBAC violation: {path}", datetime.utcnow().isoformat())
                )
                db_conn.commit()
            except Exception as e:
                print(f"[VPN] DB Trust Update Error: {e}")

            response = json.dumps({
                "action": "JWT_DOWNGRADED",
                "trust":  trust,
                "reason": "RBAC_VIOLATION",
            })

            log_suspicious(username, f"RBAC violation accessing {path}", f"Trust reduced to {trust}")
            log_vpn_decision(username, role, path, "DENY_RBAC", trust)
            conn.sendall(response.encode())
            return

        # ─── Allowed ────────────────────────────────────────────────────────
        log_vpn_decision(username, role, path, "ALLOW", trust)
        conn.sendall(f"ALLOWED:{path}".encode())

    except Exception as e:
        print(f"[VPN] Handler error: {e}")
    finally:
        if 'db_conn' in locals():
            db_conn.close()
        conn.close()


def session_cleanup_task():
    """Background thread to prune dead sessions in the database."""
    while True:
        time.sleep(300)
        try:
            db_conn = db_adapter.get_connection()
            # PostgreSQL requires slightly different interval syntax if strictly enforced,
            # but since app.py handles active_session=0 on startup, we'll keep it simple for now.
            db_conn.execute("UPDATE users SET active_session = 0 WHERE last_login < ?", 
                           ((datetime.utcnow() - timedelta(hours=1)).isoformat(),))
            db_conn.commit()
            db_conn.close()
        except Exception as e:
            print(f"[VPN] Background cleanup error: {e}")

from datetime import datetime, timedelta
threading.Thread(target=session_cleanup_task, daemon=True).start()

print(f"[VPN] Zero Trust Policy Server (RSA+AES encrypted) running on {HOST}:{PORT}")

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server:
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(50)

    while True:
        conn, addr = server.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()