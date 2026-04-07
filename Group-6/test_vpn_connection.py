#!/usr/bin/env python3
# Quick test to verify VPN server is responding

import socket
import json
import jwt
import os
from dotenv import load_dotenv

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")
VPN_HOST = "127.0.0.1"
VPN_PORT = 5012

# Create a test JWT token
test_token = jwt.encode(
    {"sub": "student1", "role": "student"},
    JWT_SECRET,
    algorithm="HS256"
)

# Test trying to access admin route as a student (should be RBAC violation)
def test_vpn_server():
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(5)
            sock.connect((VPN_HOST, VPN_PORT))
            
            request = {
                "jwt": test_token,
                "path": "/admin/users/add"  # Student trying to access admin route
            }
            
            print(f"Sending request: {request}")
            sock.sendall(json.dumps(request).encode())
            
            response = sock.recv(4096).decode()
            print(f"Response: {response}")
            
            # Check if logs were created
            import os
            logs_dir = "logs"
            if os.path.exists(os.path.join(logs_dir, "session.log")):
                print("\n✅ session.log was created!")
                with open(os.path.join(logs_dir, "session.log"), "r") as f:
                    print(f.read())
            else:
                print("\n❌ session.log NOT created")
                
            if os.path.exists(os.path.join(logs_dir, "security.log")):
                print("\n✅ security.log was created!")
                with open(os.path.join(logs_dir, "security.log"), "r") as f:
                    print(f.read())
            else:
                print("\n❌ security.log NOT created")
                
    except Exception as e:
        print(f"❌ Error connecting to VPN server: {e}")

if __name__ == "__main__":
    test_vpn_server()
