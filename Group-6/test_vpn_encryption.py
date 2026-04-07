import json
import os
from zero_trust_vpn.crypto_utils import encrypt_payload, decrypt_payload, load_private_key, load_public_key

def test_encrypt_decrypt_roundtrip():
    print("[TEST] Starting RSA+AES round-trip test...")
    # Prepare dummy payload
    payload = {"jwt": "dummy_token", "path": "/admin/dashboard"}
    
    # Load keys
    base_dir = os.path.dirname(__file__)
    pub_key_path = os.path.join(base_dir, "zero_trust_vpn", "keys", "public.pem")
    priv_key_path = os.path.join(base_dir, "zero_trust_vpn", "keys", "private.pem")
    
    public_key = load_public_key(pub_key_path)
    private_key = load_private_key(priv_key_path)

    # 1. Encrypt (expects JSON string and public key object)
    plaintext = json.dumps(payload)
    encrypted_blob = encrypt_payload(plaintext, public_key)
    print(f"[TEST] Encrypted blob size: {len(encrypted_blob)} bytes")

    # 2. Decrypt (expects bytes and private key object)
    decrypted_json = decrypt_payload(encrypted_blob, private_key)
    result = json.loads(decrypted_json)

    # 3. Assert
    assert result == payload
    print("✅ RSA+AES round-trip test passed!")

if __name__ == "__main__":
    try:
        test_encrypt_decrypt_roundtrip()
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
