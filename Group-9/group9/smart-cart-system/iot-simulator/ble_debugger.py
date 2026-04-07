"""
BLE Signal Debugger — Smart Cart IoT System
=============================================
Standalone debug server that listens for the ESP32's POST payload
and prints a color-coded, ranked breakdown of the strongest beacons.

Runs on port 8080 (so it doesn't conflict with Django on 8000).
Zero external dependencies — uses only Python's built-in http.server.

Usage:
    python ble_debugger.py                  # default port 8080
    python ble_debugger.py --port 9090      # custom port
"""

import argparse
import json
import sys
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ─── ANSI Color Codes ──────────────────────────────────────────────────────
# Color-code the output so signal quality is obvious at a glance.

RESET   = "\033[0m"
BOLD    = "\033[1m"
DIM     = "\033[2m"

# Signal-quality palette
GREEN   = "\033[92m"   # Strong   (>= -65 dBm)
YELLOW  = "\033[93m"   # Medium   (-66 to -79 dBm)
RED     = "\033[91m"   # Weak     (<= -80 dBm)
CYAN    = "\033[96m"
MAGENTA = "\033[95m"
WHITE   = "\033[97m"

# Box-drawing characters for a clean layout
HEADER_LINE = f"{CYAN}{'─' * 56}{RESET}"
TOP_BAR     = f"{CYAN}╔{'═' * 54}╗{RESET}"
BOT_BAR     = f"{CYAN}╚{'═' * 54}╝{RESET}"
MID_BAR     = f"{CYAN}╟{'─' * 54}╢{RESET}"

# Ping counter
_ping_count = 0


def rssi_color(rssi: int) -> str:
    """Pick an ANSI color based on RSSI strength."""
    if rssi >= -65:
        return GREEN
    elif rssi >= -80:
        return YELLOW
    else:
        return RED


def rssi_bar(rssi: int, max_width: int = 20) -> str:
    """Return a visual bar showing relative signal strength.
    Maps the RSSI range [-100, -30] onto [0, max_width] blocks."""
    clamped = max(-100, min(-30, rssi))
    filled = int((clamped + 100) / 70 * max_width)
    color = rssi_color(rssi)
    return f"{color}{'█' * filled}{DIM}{'░' * (max_width - filled)}{RESET}"


def signal_label(rssi: int) -> str:
    """Human-readable signal quality label."""
    if rssi >= -55:
        return f"{GREEN}EXCELLENT{RESET}"
    elif rssi >= -65:
        return f"{GREEN}STRONG{RESET}"
    elif rssi >= -75:
        return f"{YELLOW}GOOD{RESET}"
    elif rssi >= -85:
        return f"{YELLOW}FAIR{RESET}"
    else:
        return f"{RED}WEAK{RESET}"


def print_ping(payload: dict):
    """Pretty-print a single ESP32 ping to stdout."""
    global _ping_count
    _ping_count += 1

    target_uuid = payload.get("target_uuid", "UNKNOWN")
    beacons     = payload.get("beacons", [])

    # Sort by RSSI descending (closest to 0 = strongest)
    beacons_sorted = sorted(beacons, key=lambda b: b.get("rssi", -999), reverse=True)
    top = beacons_sorted[:3]

    now = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    print()
    print(TOP_BAR)
    print(f"{CYAN}║{RESET}  {BOLD}{WHITE}📡  PING #{_ping_count:<6}{RESET}"
          f"  {DIM}@ {now}{RESET}"
          f"  {DIM}({len(beacons)} beacon{'s' if len(beacons) != 1 else ''} total){RESET}"
          f"     {CYAN}║{RESET}")
    print(f"{CYAN}║{RESET}  {DIM}UUID: {target_uuid}{RESET}"
          f"{' ' * max(1, 54 - 10 - len(target_uuid))}{CYAN}║{RESET}")
    print(MID_BAR)

    if not top:
        print(f"{CYAN}║{RESET}  {RED}  ⚠  No beacons in payload!{RESET}"
              f"{' ' * 26}{CYAN}║{RESET}")
    else:
        medals = ["🥇", "🥈", "🥉"]
        for i, b in enumerate(top):
            major = b.get("major", "?")
            minor = b.get("minor", "?")
            rssi  = b.get("rssi", -999)

            color  = rssi_color(rssi)
            medal  = medals[i] if i < len(medals) else "  "
            bar    = rssi_bar(rssi, max_width=16)
            label  = signal_label(rssi)

            line = (f"  {medal} {BOLD}#{i+1}{RESET}  "
                    f"Major: {BOLD}{major:<3}{RESET}  "
                    f"Minor: {BOLD}{minor:<3}{RESET}  "
                    f"{color}{BOLD}{rssi:>4} dBm{RESET}  "
                    f"{bar}  {label}")

            print(f"{CYAN}║{RESET}{line}")

    # Delta analysis: flag if top 2 beacons are dangerously close
    if len(top) >= 2:
        delta = abs(top[0].get("rssi", 0) - top[1].get("rssi", 0))
        if delta <= 5:
            print(MID_BAR)
            print(f"{CYAN}║{RESET}  {RED}{BOLD}⚠  JUMP RISK!{RESET}  "
                  f"{DIM}Top 2 signals only {delta} dBm apart — "
                  f"zone flicker likely{RESET}")
        elif delta <= 10:
            print(MID_BAR)
            print(f"{CYAN}║{RESET}  {YELLOW}⚡ CAUTION:{RESET}  "
                  f"{DIM}Top 2 signals {delta} dBm apart — "
                  f"borderline stability{RESET}")

    print(BOT_BAR)
    sys.stdout.flush()


class DebugHandler(BaseHTTPRequestHandler):
    """HTTP handler that accepts the ESP32 POST payload."""

    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)

        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b'{"error": "Invalid JSON"}')
            print(f"\n{RED}✗ Received malformed JSON — ignoring.{RESET}")
            return

        # Print the debug output
        print_ping(payload)

        # Reply with 201 so the ESP32 sees a success
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "debug_received",
            "ping": _ping_count,
        }).encode())

    def do_GET(self):
        """Health-check / landing page."""
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(
            b"Smart Cart BLE Debugger is running.\n"
            b"POST your ESP32 payload to this URL.\n"
        )

    def log_message(self, format, *args):
        """Suppress default access logs to keep console clean."""
        pass


def main():
    parser = argparse.ArgumentParser(
        description="BLE Signal Debugger — Smart Cart IoT System",
    )
    parser.add_argument(
        "--port", type=int, default=8080,
        help="Port to listen on (default: 8080)",
    )
    args = parser.parse_args()

    print(f"\n{BOLD}{CYAN}{'=' * 56}{RESET}")
    print(f"{BOLD}{WHITE}  📡  Smart Cart — BLE Signal Debugger{RESET}")
    print(f"{BOLD}{CYAN}{'=' * 56}{RESET}")
    print(f"  Listening on {BOLD}http://0.0.0.0:{args.port}/{RESET}")
    print(f"  Point your ESP32's API_URL here to inspect pings.")
    print(f"  Press {BOLD}Ctrl+C{RESET} to stop.\n")
    print(f"  {DIM}Signal legend:{RESET}")
    print(f"    {GREEN}██{RESET} Strong (≥ -65 dBm)    "
          f"{YELLOW}██{RESET} Medium (-66 to -79)    "
          f"{RED}██{RESET} Weak (≤ -80)")
    print(f"{BOLD}{CYAN}{'=' * 56}{RESET}\n")

    server = HTTPServer(("0.0.0.0", args.port), DebugHandler)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n{DIM}Debugger stopped. {_ping_count} pings received.{RESET}")
        server.server_close()


if __name__ == "__main__":
    main()
