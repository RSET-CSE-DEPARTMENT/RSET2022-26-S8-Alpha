import os
import json
import base64
import sys
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Log Key Setup
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_KEY_PATH = os.path.join(BASE_DIR, "keys", "log_key.bin")

def decrypt_log_file(filepath):
    """Read an encrypted log file and print decrypted entries."""
    if not os.path.exists(LOG_KEY_PATH):
        print(f"ERROR: Log encryption key not found at {LOG_KEY_PATH}")
        return

    with open(LOG_KEY_PATH, "rb") as f:
        log_key = f.read()
    
    aesgcm = AESGCM(log_key)

    if not os.path.exists(filepath):
        print(f"ERROR: Log file not found at {filepath}")
        return

    print(f"\n--- Decrypting Log: {os.path.basename(filepath)} ---")
    print("-" * 60)

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                entry = json.loads(line)
                nonce = base64.b64decode(entry["nonce"])
                ciphertext = base64.b64decode(entry["data"])
                
                decrypted = aesgcm.decrypt(nonce, ciphertext, None)
                print(decrypted.decode("utf-8"))
            except Exception as e:
                # If not JSON or decryption fails, it might be a legacy plaintext line
                print(f"[UNENCRYPTED/CORRUPT] {line}")

    print("-" * 60)
    print("--- End of Log ---\n")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        # Default logs if no args provided
        LOGS_DIR = os.path.join(BASE_DIR, "..", "logs")
        for log_name in ["session.log", "security.log", "error.log"]:
            decrypt_log_file(os.path.join(LOGS_DIR, log_name))
    else:
        decrypt_log_file(sys.argv[1])
