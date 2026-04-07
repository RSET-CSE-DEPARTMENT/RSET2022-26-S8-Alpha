import json
import os
import sys

# Ensure we are in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))
from zero_trust_vpn.crypto_utils import encrypt_payload, decrypt_payload, load_public_key, load_private_key

def test_roundtrip():
    print("=== CRYPTO ROUNDTRIP TEST ===")
    
    pub_path = "zero_trust_vpn/keys/public.pem"
    priv_path = "zero_trust_vpn/keys/private.pem"
    
    pub_key = load_public_key(pub_path)
    priv_key = load_private_key(priv_path)
    
    original_payload = {"path": "/admin/users", "jwt": "dummy.jwt.token"}
    plaintext = json.dumps(original_payload)
    
    print(f"[TEST] Original: {plaintext}")
    
    # 1. Encrypt
    blob = encrypt_payload(plaintext, pub_key)
    print(f"[TEST] Encrypted Blob Len (with total_len header): {len(blob)}")
    
    # 2. Extract Body (Simulation of server.recv(4) then recv(total_len))
    import struct
    total_len = struct.unpack(">I", blob[:4])[0]
    body = blob[4:]
    print(f"[TEST] Total Len Header: {total_len} | Body Actual Len: {len(body)}")
    
    # 3. Decrypt
    try:
        decrypted_json = decrypt_payload(body, priv_key)
        print(f"[TEST] Decrypted: {decrypted_json}")
        
        recovered_data = json.loads(decrypted_json)
        if recovered_data["path"] == original_payload["path"]:
            print("[SUCCESS] Roundtrip complete and verified!")
        else:
            print("[FAILURE] Recovered data mismatch!")
    except Exception as e:
        print(f"[ERROR] Decryption failed: {e}")

if __name__ == "__main__":
    test_roundtrip()
