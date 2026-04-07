# logger.py
import os
import time
import threading
import traceback
import json
import base64
import sys
from datetime import datetime
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# =========================
# DATABASE SETUP
# =========================
# Ensure we can find db_adapter
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    from db_adapter import db_adapter
except ImportError:
    # Fallback for when logger is used in isolation or early init
    db_adapter = None

# =========================
# LOG DIRECTORY SETUP (Backward Compatibility / Fallback)
# =========================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Thread lock to prevent race conditions during sequence increment
log_lock = threading.Lock()
_sequence_number = 0

# Load Log Encryption Key
# Load Log Encryption Key
LOG_KEY_PATH = os.path.join(BASE_DIR, "keys", "log_key.bin")

# 1. Try environment variable first (for Render/Cloud)
env_key = os.getenv("LOG_KEY")
if env_key:
    try:
        LOG_KEY = base64.b64decode(env_key)
        aesgcm = AESGCM(LOG_KEY)
    except Exception as e:
        print(f"[LOGGER] WARNING: Failed to parse LOG_KEY from env: {e}")
        LOG_KEY = None
else:
    # 2. Fallback to local file
    try:
        with open(LOG_KEY_PATH, "rb") as f:
            LOG_KEY = f.read()
        aesgcm = AESGCM(LOG_KEY)
    except FileNotFoundError:
        LOG_KEY = None
        print(f"[LOGGER] WARNING: Log encryption key not found. Logging in plaintext.")

# =========================
# INTERNAL WRITE FUNCTION
# =========================
def _write_log(category, username, message):
    global _sequence_number
    with log_lock:
        _sequence_number += 1
        
        nonce_str = None
        encrypted_data = None
        plain_message = None

        if LOG_KEY:
            # Encrypt with AES-GCM
            nonce = os.urandom(12)
            payload = f"SEQ={_sequence_number} | {message}".encode("utf-8")
            ciphertext = aesgcm.encrypt(nonce, payload, None)
            
            nonce_str = base64.b64encode(nonce).decode("utf-8")
            encrypted_data = base64.b64encode(ciphertext).decode("utf-8")
        else:
            plain_message = f"SEQ={_sequence_number} | {message}"

        # Write to Database
        if db_adapter:
            try:
                conn = db_adapter.get_connection()
                conn.execute(
                    "INSERT INTO system_logs (category, username, seq, nonce, encrypted_data, plain_message, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (category, username, _sequence_number, nonce_str, encrypted_data, plain_message, datetime.utcnow().isoformat())
                )
                # Auto-prune: keep only the latest 50 rows
                try:
                    conn.execute("DELETE FROM system_logs WHERE id NOT IN (SELECT id FROM system_logs ORDER BY id DESC LIMIT 50)")
                except Exception:
                    pass
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[LOGGER ERROR] Database write failed: {e}")
                # Fallback to local file if DB is down
                _write_to_file(category, _sequence_number, nonce_str, encrypted_data, plain_message)
        else:
            _write_to_file(category, _sequence_number, nonce_str, encrypted_data, plain_message)

def _write_to_file(category, seq, nonce, data, plain):
    """Fallback file logging"""
    filepath = os.path.join(LOGS_DIR, f"{category.lower()}.log")
    if plain:
        line = plain
    else:
        line = json.dumps({"seq": seq, "nonce": nonce, "data": data})
    
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except:
        pass

# =========================
# LOGGING INTERFACE
# =========================
def log_event(username, action, status, reason=""):
    msg = f"USER={username} | ACTION={action} | STATUS={status} | REASON={reason}"
    _write_log("SESSION", username, msg)

def log_suspicious(username, reason, metadata=""):
    msg = f"USER={username} | ⚠ SUSPICIOUS | {reason} | {metadata}"
    _write_log("SECURITY", username, msg)

def log_trust_change(username, old_score, new_score, reason):
    msg = f"USER={username} | TRUST_CHANGE | {old_score} → {new_score} | REASON={reason}"
    _write_log("SESSION", username, msg)

def log_vpn_decision(username, role, path, decision, trust_score):
    msg = f"USER={username} | ROLE={role} | PATH={path} | DECISION={decision} | TRUST={trust_score}"
    _write_log("SESSION", username, msg)

def log_error(context, exc: Exception):
    trace = traceback.format_exc()
    msg = f"❌ ERROR | CONTEXT={context}\n{trace}"
    _write_log("ERROR", "system", msg)
