import socket
import os
import sys
from dotenv import load_dotenv

load_dotenv()

hosts_to_test = [
    "google.com",
    "github.com",
    "db.vcifprkpwwrugsmkipvd.supabase.co"
]

print("--- Comprehensive Network Diagnosis ---")
print(f"Python Version: {sys.version}")

for host in hosts_to_test:
    print(f"\n[TEST] Resolving: {host}")
    try:
        addr = socket.gethostbyname(host)
        print(f"  Result: SUCCESS -> {addr}")
    except Exception as e:
        print(f"  Result: FAILED -> {e}")

db_url = os.getenv("DATABASE_URL")
if db_url:
    print(f"\n[DEBUG] Raw DATABASE_URL length: {len(db_url)}")
    print(f"[DEBUG] Raw DATABASE_URL repr: {repr(db_url)}")
    
    # Try to parse properties manually
    from urllib.parse import urlparse
    try:
        parsed = urlparse(db_url)
        print(f"[DEBUG] Parsed Host: {repr(parsed.hostname)}")
        print(f"[DEBUG] Parsed Port: {parsed.port}")
    except Exception as e:
        print(f"[DEBUG] Parsing Failed: {e}")
else:
    print("\n[ERROR] DATABASE_URL NOT FOUND IN ENV")
