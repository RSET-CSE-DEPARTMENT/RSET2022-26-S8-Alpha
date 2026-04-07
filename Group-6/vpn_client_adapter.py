# vpn_client_adapter.py

"""Client adapter for the Zero‑Trust micro‑VPN.
It encrypts the JWT and requested path using hybrid RSA‑AES (provided by
`zero_trust_vpn/crypto_utils.py`) and sends the encrypted envelope to the
VPN server. The server replies with plain‑text decisions (e.g. "ALLOWED:/path").
"""

import socket
import json
import os

# Import crypto helpers
from zero_trust_vpn.crypto_utils import encrypt_payload, load_public_key

VPN_HOST = "127.0.0.1"
VPN_PORT = 5012


def check_access(jwt_token: str, path: str) -> str:
    """Encrypt the JWT and path, send to the VPN server, and return the response.

    Args:
        jwt_token: The JWT issued by the Zero‑Trust authentication module.
        path: The resource path the client wants to access.
    Returns:
        The server's response (e.g. "ALLOWED:/admin/users").
    """
    payload = {"jwt": jwt_token, "path": path}
    
    try:
        # Load the server's RSA public key
        public_key_path = os.path.join(os.path.dirname(__file__), "zero_trust_vpn", "keys", "public.pem")
        public_key = load_public_key(public_key_path)

        # Encrypt the payload
        encrypted_blob = encrypt_payload(json.dumps(payload), public_key)

        # Send to VPN server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(3)
            sock.connect((VPN_HOST, VPN_PORT))
            sock.sendall(encrypted_blob)
            response = sock.recv(4096)
            return response.decode()
    except Exception as e:
        print(f"[VPN CLIENT] Error: {e}")
        return "VPN_UNREACHABLE"
