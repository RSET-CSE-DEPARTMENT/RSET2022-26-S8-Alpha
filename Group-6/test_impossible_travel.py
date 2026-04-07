"""
Test script for Impossible Travel detection (mock IP-based distance calculation).
Run: python test_impossible_travel.py
"""

def get_dist(ip1, ip2):
    """Same logic as app.py - mock distance based on first 2 IP octets."""
    if ":" in ip1 or ":" in ip2:
        return 0 if ip1 == ip2 else 1000
    try:
        p1 = [int(x) for x in ip1.split(".")]
        p2 = [int(x) for x in ip2.split(".")]
        if len(p1) < 2 or len(p2) < 2:
            return 0
        return abs(p1[0] - p2[0]) * 500 + abs(p1[1] - p2[1]) * 50
    except (ValueError, IndexError):
        return 0


SPEED_THRESHOLD = 800  # km/h - same as app.py


def test_impossible_travel(last_ip, current_ip, mins_ago):
    """Returns (distance_km, speed_kmh, flagged)."""
    dist = get_dist(last_ip, current_ip)
    speed = (dist * 60 / mins_ago) if mins_ago > 0 else 0
    flagged = speed > SPEED_THRESHOLD
    return dist, speed, flagged


# Test cases (matches your examples)
tests = [
    ("192.168.1.100", "192.168.2.100", 5, "Same first 2 octets → 0 km"),
    ("82.45.67.89", "82.45.89.12", 1, "Same first 2 octets → 0 km"),
    ("10.0.0.100", "10.0.255.100", 1, "Same first 2 octets → 0 km"),
    ("82.45.67.89", "83.45.67.89", 30, "First octet +1 → 500 km, 1000 km/h"),
    ("192.168.1.100", "195.168.1.100", 5, "First octet +3 → 1500 km, 18k km/h"),
]

print("=" * 75)
print("IMPOSSIBLE TRAVEL - Mock Distance Algorithm Test")
print("=" * 75)
print(f"Threshold: {SPEED_THRESHOLD} km/h  |  Formula: dist = |A1-A2|*500 + |B1-B2|*50")
print("-" * 75)
print(f"{'Last IP':<18} {'Current IP':<18} {'Time':<8} {'Dist':<8} {'Speed':<12} {'Result'}")
print("-" * 75)

for last_ip, current_ip, mins, _ in tests:
    dist, speed, flagged = test_impossible_travel(last_ip, current_ip, mins)
    result = "FLAG" if flagged else "OK"
    print(f"{last_ip:<18} {current_ip:<18} {mins} min   {dist:<8} {speed:>8.0f} km/h  {result}")

print("-" * 75)
print("\nAll test cases completed.")
