"""
crypto_utils.py
---------------
Hybrid RSA + AES-256-CBC encryption utilities for VPN tunnel communication.

Flow (Flask → VPN Server):
  1. Flask generates a random 32-byte AES-256 key + 16-byte IV
  2. Flask encrypts the JSON payload with AES-256-CBC
  3. Flask encrypts the AES key with the VPN server's RSA-2048 public key (OAEP)
  4. Flask sends: [4-byte enc_key_len][encrypted_aes_key][iv][encrypted_payload]

Flow (VPN Server decryption):
  1. VPN Server reads the 4-byte length header, splits enc_key / rest
  2. Decrypts the AES key with its RSA private key
  3. Decrypts the payload with AES-256-CBC using the recovered key + IV
"""

import os
import struct
import time
import json
from cryptography.hazmat.primitives.asymmetric import padding as asym_padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend


# ─── AES Helpers ──────────────────────────────────────────────────────────────

def _pkcs7_pad(data: bytes, block_size: int = 16) -> bytes:
    pad_len = block_size - (len(data) % block_size)
    return data + bytes([pad_len] * pad_len)

def _pkcs7_unpad(data: bytes) -> bytes:
    pad_len = data[-1]
    return data[:-pad_len]

def aes_encrypt(plaintext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    encryptor = cipher.encryptor()
    return encryptor.update(_pkcs7_pad(plaintext)) + encryptor.finalize()

def aes_decrypt(ciphertext: bytes, key: bytes, iv: bytes) -> bytes:
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv), backend=default_backend())
    decryptor = cipher.decryptor()
    return _pkcs7_unpad(decryptor.update(ciphertext) + decryptor.finalize())


# ─── RSA Helpers ──────────────────────────────────────────────────────────────

def load_public_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_public_key(f.read())

def load_private_key(path: str):
    with open(path, "rb") as f:
        return serialization.load_pem_private_key(f.read(), password=None)

def rsa_encrypt(data: bytes, public_key) -> bytes:
    return public_key.encrypt(
        data,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )

def rsa_decrypt(ciphertext: bytes, private_key) -> bytes:
    return private_key.decrypt(
        ciphertext,
        asym_padding.OAEP(
            mgf=asym_padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )


# ─── Tunnel Wire Format ───────────────────────────────────────────────────────
# Wire format: [4 bytes: len(enc_aes_key)] [enc_aes_key] [16 bytes: iv] [aes_ciphertext]

def encrypt_payload(plaintext: str, public_key) -> bytes:
    """Encrypt a plaintext string for transmission over the VPN tunnel socket."""
    aes_key = os.urandom(32)   # AES-256
    print(f"[CRYPTO DEBUG] Generated AES Key (hex): {aes_key[:4].hex()}...")
    iv      = os.urandom(16)   # CBC IV

    # Add timestamp and nonce for replay protection
    data = json.loads(plaintext)
    data["ts"] = time.time()
    data["nonce"] = os.urandom(8).hex()
    
    enc_payload = aes_encrypt(json.dumps(data).encode("utf-8"), aes_key, iv)
    enc_aes_key = rsa_encrypt(aes_key, public_key)
    print(f"[CRYPTO DEBUG] Encrypted AES Key (hex): {enc_aes_key[:8].hex()}...")

    # Pack: 4-byte total length, 4-byte enc_aes_key length, then key, iv, payload
    body = struct.pack(">I", len(enc_aes_key)) + enc_aes_key + iv + enc_payload
    print(f"[CRYPTO DEBUG] Body Len: {len(body)} | EncKeyLen: {len(enc_aes_key)}")
    return struct.pack(">I", len(body)) + body

def decrypt_payload(wire_data: bytes, private_key) -> str:
    """Decrypt wire data received over the VPN tunnel socket."""
    # Wire data now starts with 4-byte total length, which we already read in server.
    # So we expect [4 bytes: enc_key_len] [enc_key] [16 bytes: iv] [payload]
    print(f"[CRYPTO DEBUG] Total Body Recv: {len(wire_data)}")
    enc_key_len = struct.unpack(">I", wire_data[:4])[0]
    print(f"[CRYPTO DEBUG] Parsed EncKeyLen: {enc_key_len}")
    enc_aes_key = wire_data[4 : 4 + enc_key_len]
    print(f"[CRYPTO DEBUG] Recv EncAESKey (hex): {enc_aes_key[:8].hex()}...")
    iv          = wire_data[4 + enc_key_len : 4 + enc_key_len + 16]
    enc_payload = wire_data[4 + enc_key_len + 16:]
    print(f"[CRYPTO DEBUG] Payload Len: {len(enc_payload)}")

    aes_key = rsa_decrypt(enc_aes_key, private_key)
    print(f"[CRYPTO DEBUG] Decrypted AES Key (hex): {aes_key[:4].hex()}...")
    return aes_decrypt(enc_payload, aes_key, iv).decode("utf-8")
