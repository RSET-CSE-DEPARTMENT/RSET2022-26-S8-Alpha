"""
generate_keys.py
----------------
One-time script to generate the RSA 2048-bit keypair for the VPN tunnel.
Run this ONCE before starting the VPN server:

    python generate_keys.py

Keys are saved to:
    zero_trust_vpn/keys/private.pem   (kept on VPN server only)
    zero_trust_vpn/keys/public.pem    (shared with Flask app)
    zero_trust_vpn/keys/log_key.bin   (symmetric key for log encryption)
"""

import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization

KEYS_DIR = os.path.join(os.path.dirname(__file__), "keys")
os.makedirs(KEYS_DIR, exist_ok=True)

PRIVATE_KEY_PATH = os.path.join(KEYS_DIR, "private.pem")
PUBLIC_KEY_PATH  = os.path.join(KEYS_DIR, "public.pem")
LOG_KEY_PATH     = os.path.join(KEYS_DIR, "log_key.bin")

def generate_rsa_keypair():
    print("[KEYGEN] Generating RSA 2048-bit keypair...")

    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )

    # Save private key (PEM, no passphrase for simplicity — add one in production)
    with open(PRIVATE_KEY_PATH, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))

    # Save public key
    with open(PUBLIC_KEY_PATH, "wb") as f:
        f.write(private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    print(f"[KEYGEN] Private key saved → {PRIVATE_KEY_PATH}")
    print(f"[KEYGEN] Public  key saved → {PUBLIC_KEY_PATH}")
    print("[KEYGEN] Done. Keep private.pem on the VPN server only.")

def generate_log_key():
    print("[KEYGEN] Generating 32-byte symmetric log key...")
    log_key = os.urandom(32)
    with open(LOG_KEY_PATH, "wb") as f:
        f.write(log_key)
    print(f"[KEYGEN] Log key saved → {LOG_KEY_PATH}")


if __name__ == "__main__":
    generate_rsa_keypair()
    generate_log_key()
