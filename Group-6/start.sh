#!/bin/bash
# start.sh — Render startup script
# Starts the VPN policy server in the background, then launches Gunicorn

echo "[DEPLOY] Starting Zero Trust VPN Policy Server..."
cd /opt/render/project/src/Student_Management_System
python zero_trust_vpn/vpn_server.py &

echo "[DEPLOY] Starting Flask App via Gunicorn..."
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2 --timeout 120
