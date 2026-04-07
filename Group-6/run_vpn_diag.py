import threading
import time
import socket
import sys
import os
import subprocess

# Ensure we are in the correct directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def run_server():
    print("[DIAG] Starting VPN Server...")
    # Using subprocess to run the server as a separate process but capture output
    proc = subprocess.Popen([sys.executable, "-u", "zero_trust_vpn/vpn_server.py"],
                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    for line in iter(proc.stdout.readline, ""):
        print(f"[SERVER] {line.strip()}")
    proc.wait()

def run_tests():
    time.sleep(3) # Wait for server to bind
    print("\n[DIAG] Starting Security Test Suite...")
    try:
        # Run the test suite and capture output
        output = subprocess.check_output([sys.executable, "test_security_suite.py"], 
                                         stderr=subprocess.STDOUT, text=True)
        print(output)
    except subprocess.CalledProcessError as e:
        print(f"[TEST ERROR] {e.output}")
    except Exception as e:
        print(f"[DIAG ERROR] {e}")

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    
    run_tests()
    print("[DIAG] Finished.")
