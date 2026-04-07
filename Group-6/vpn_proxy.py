from flask import Flask, request, Response
import requests
import sys
import os

# Add parent directory to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import vpn_client_adapter

import time

app = Flask(__name__)

@app.route('/', defaults={'path': ''}, methods=['GET', 'POST', 'PUT', 'DELETE'])
@app.route('/<path:path>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy(path):
    # 1. Intercept Request
    full_path = "/" + path
    if request.query_string:
        full_path += "?" + request.query_string.decode()
    
    jwt_token = request.headers.get("X-VPN-Token")
    if not jwt_token:
        return "VPN Token Required (X-VPN-Token)", 401

    print(f"[PROXY] Intercepting {request.method} {full_path}")

    # 2. Challenge via Zero Trust Adapter
    decision = vpn_client_adapter.check_access(jwt_token, full_path)

    print(f"[PROXY] Decision: {decision}")

    if decision.startswith("ALLOWED:"):
        target_path = decision.split(":", 1)[1]
        target_url = f"http://127.0.0.1:5000{target_path}"
        
        # 3. Forward to Backend
        try:
            resp = requests.request(
                method=request.method,
                url=target_url,
                headers={k: v for k, v in request.headers if k.lower() != 'host'},
                data=request.get_data(),
                cookies=request.cookies,
                allow_redirects=False
            )
            
            # 4. Return Backend Response
            excluded_headers = ['content-encoding', 'content-length', 'transfer-encoding', 'connection']
            headers = [(name, value) for (name, value) in resp.raw.headers.items()
                       if name.lower() not in excluded_headers]
            return Response(resp.content, resp.status_code, headers)
        except Exception as e:
            return f"Proxy Forwarding Error: {e}", 502
    else:
        return f"Zero Trust Policy Violation: {decision}", 403

if __name__ == "__main__":
    print("--- Zero Trust Flask Proxy Initialized ---")
    app.run(port=8081, debug=False)
