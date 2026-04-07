import os
import sys
import json
import base64

# Add the zero_trust_vpn directory to sys.path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(BASE_DIR, "zero_trust_vpn"))

from logger import log_event, SESSION_LOG

def test_encrypted_logging():
    test_user = "test_audit_user"
    test_action = "VERIFY_ENCRYPTION"
    log_event(test_user, test_action, "SUCCESS", "Initial audit test")
    
    print(f"[TEST] Log written to {SESSION_LOG}")
    
    # Read the last line of the log
    with open(SESSION_LOG, "r", encoding="utf-8") as f:
        lines = f.readlines()
        last_line = lines[-1].strip()
    
    print(f"[TEST] Last log line: {last_line}")
    
    # Verify it is JSON and contains encrypted fields
    try:
        data = json.loads(last_line)
        assert "seq" in data
        assert "nonce" in data
        assert "data" in data
        print("✅ Log entry is successfully encrypted and JSON-formatted.")
    except Exception as e:
        print(f"❌ Failed to parse log entry: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_encrypted_logging()
