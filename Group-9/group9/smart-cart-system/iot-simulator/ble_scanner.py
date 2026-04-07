"""
BLE iBeacon Scanner — Smart Cart IoT System
============================================
Scans for a specific iBeacon (phone) via Bluetooth Low Energy using *bleak*
and POSTs the RSSI readings to the Django Fog Node API.

Target beacon:
    UUID  = 11112222-3333-4444-5555-666677778888
    Major = 1
    Minor = 1

Usage:
    python ble_scanner.py                           # default API at localhost:8000
    python ble_scanner.py --api http://host:port    # custom API base
"""

import argparse
import asyncio
import logging
import struct
import sys
import time

import requests
from bleak import BleakScanner

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("ble_scanner")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_API_BASE = "http://localhost:8000"
LOCATION_ENDPOINT = "/api/location/update/"
SCAN_INTERVAL_SECONDS = 3
BLE_SCAN_TIMEOUT_SECONDS = 5

# Target beacon identifiers
TARGET_UUID = "11112222-3333-4444-5555-666677778888"
TARGET_MAJOR = 1
TARGET_MINOR = 1

# Apple iBeacon company ID and prefix
APPLE_COMPANY_ID = 0x004C
IBEACON_TYPE = 0x0215


# ---------------------------------------------------------------------------
# iBeacon parser
# ---------------------------------------------------------------------------
def parse_ibeacon(manufacturer_data: dict) -> dict | None:
    """
    Parse iBeacon data from BLE manufacturer-specific advertisement data.
    Returns a dict with uuid, major, minor if valid iBeacon, else None.
    """
    apple_data = manufacturer_data.get(APPLE_COMPANY_ID)
    if apple_data is None:
        return None

    # iBeacon payload: 0x02 0x15 + 16-byte UUID + 2-byte major + 2-byte minor + 1-byte TX power
    if len(apple_data) < 23:
        return None

    beacon_type = (apple_data[0] << 8) | apple_data[1]
    if beacon_type != IBEACON_TYPE:
        return None

    # Extract UUID (bytes 2–17)
    uuid_bytes = apple_data[2:18]
    uuid_str = "{:08X}-{:04X}-{:04X}-{:04X}-{:012X}".format(
        struct.unpack(">I", uuid_bytes[0:4])[0],
        struct.unpack(">H", uuid_bytes[4:6])[0],
        struct.unpack(">H", uuid_bytes[6:8])[0],
        struct.unpack(">H", uuid_bytes[8:10])[0],
        struct.unpack(">Q", b"\x00\x00" + uuid_bytes[10:16])[0],
    )

    # Extract Major (bytes 18–19) and Minor (bytes 20–21)
    major = struct.unpack(">H", apple_data[18:20])[0]
    minor = struct.unpack(">H", apple_data[20:22])[0]

    return {"uuid": uuid_str, "major": major, "minor": minor}


# ---------------------------------------------------------------------------
# BLE scanning
# ---------------------------------------------------------------------------
async def scan_for_target():
    """
    Scan for BLE devices and return the target beacon reading if found.
    Returns a dict with uuid, major, minor, rssi — or None.
    """
    logger.info(
        "Scanning for beacon  UUID=%s  Major=%s  Minor=%s  (%ss) …",
        TARGET_UUID, TARGET_MAJOR, TARGET_MINOR, BLE_SCAN_TIMEOUT_SECONDS,
    )

    try:
        results = await BleakScanner.discover(
            timeout=BLE_SCAN_TIMEOUT_SECONDS, return_adv=True
        )
    except Exception as exc:
        logger.error("BLE scan failed: %s", exc)
        return None

    for device, adv_data in results.values():
        if not adv_data.manufacturer_data:
            continue

        beacon = parse_ibeacon(adv_data.manufacturer_data)
        if beacon is None:
            continue

        # Check if this is our target beacon
        if (
            beacon["uuid"].upper() == TARGET_UUID.upper()
            and beacon["major"] == TARGET_MAJOR
            and beacon["minor"] == TARGET_MINOR
        ):
            logger.info(
                "✓ Target beacon found!  Device=%s  RSSI=%s dBm",
                device.name or device.address, adv_data.rssi,
            )
            return {
                "uuid": beacon["uuid"],
                "major": beacon["major"],
                "minor": beacon["minor"],
                "rssi": adv_data.rssi,
            }

        # Log other beacons for debugging
        logger.debug(
            "Ignored beacon  UUID=%s  Major=%s  Minor=%s",
            beacon["uuid"], beacon["major"], beacon["minor"],
        )

    logger.info("Target beacon not found in this scan cycle.")
    return None


def do_scan():
    """Synchronous wrapper around the async BLE scan."""
    return asyncio.run(scan_for_target())


# ---------------------------------------------------------------------------
# Payload sender
# ---------------------------------------------------------------------------
def send_payload(api_url: str, payload: dict):
    """POST a single BLE reading to the Fog Node API."""
    try:
        resp = requests.post(api_url, json=payload, timeout=5)
        if resp.status_code == 201:
            logger.info(
                "✓ Sent to API — UUID=%s  Major=%s  Minor=%s  RSSI=%s dBm",
                payload["uuid"], payload["major"], payload["minor"], payload["rssi"],
            )
        else:
            logger.warning("API responded %s: %s", resp.status_code, resp.text)
    except requests.ConnectionError:
        logger.error("Cannot reach %s — is the Django server running?", api_url)
    except Exception as exc:
        logger.error("Error sending payload: %s", exc)


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
def main(api_base: str):
    api_url = api_base.rstrip("/") + LOCATION_ENDPOINT
    logger.info("Smart Cart BLE Scanner starting …")
    logger.info("API endpoint : %s", api_url)
    logger.info("Target beacon: UUID=%s  Major=%s  Minor=%s", TARGET_UUID, TARGET_MAJOR, TARGET_MINOR)

    try:
        while True:
            reading = do_scan()

            if reading:
                send_payload(api_url, reading)
            else:
                logger.debug("No target beacon detected this cycle.")

            time.sleep(SCAN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        logger.info("Scanner stopped by user.")
        sys.exit(0)


# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BLE iBeacon Scanner — Smart Cart")
    parser.add_argument(
        "--api",
        default=DEFAULT_API_BASE,
        help=f"Base URL of the Fog Node API (default: {DEFAULT_API_BASE})",
    )
    args = parser.parse_args()
    main(api_base=args.api)
