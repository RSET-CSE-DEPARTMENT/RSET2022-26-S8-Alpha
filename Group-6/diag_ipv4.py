import socket
import os
from dotenv import load_dotenv

load_dotenv()

host = "db.vcifprkpwwrugsmkipvd.supabase.co"

print(f"--- IPv4 Specific Diagnosis ---")

try:
    print(f"Trying AF_INET for {host}...")
    # 0 = generic, socket.SOCK_STREAM = TCP, socket.IPPROTO_TCP = TCP, socket.AF_INET = IPv4 only
    infos = socket.getaddrinfo(host, 5432, socket.AF_INET, socket.SOCK_STREAM)
    print(f"[SUCCESS] Found {len(infos)} IPv4 addresses:")
    for info in infos:
        print(f" - {info[4][0]}")
except Exception as e:
    print(f"[FAILED] getaddrinfo (AF_INET) failed: {e}")

try:
    print(f"\nTrying AF_INET6 for {host}...")
    infos = socket.getaddrinfo(host, 5432, socket.AF_INET6, socket.SOCK_STREAM)
    print(f"[SUCCESS] Found {len(infos)} IPv6 addresses:")
    for info in infos:
        print(f" - {info[4][0]}")
except Exception as e:
    print(f"[FAILED] getaddrinfo (AF_INET6) failed: {e}")
