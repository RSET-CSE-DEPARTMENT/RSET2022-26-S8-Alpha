# suspicious_activity_tracker.py

import time
from collections import defaultdict
from datetime import datetime, time as dtime

failed_logins = defaultdict(int)
failed_otps = defaultdict(int)
rbac_violations = defaultdict(int)
request_timestamps = defaultdict(list)

MAX_FAILED_LOGINS = 5
MAX_FAILED_OTPS = 3
MAX_RBAC_VIOLATIONS = 3
MAX_REQUESTS_PER_10_SEC = 7

def record_failed_login(username):
    failed_logins[username] += 1
    return failed_logins[username] >= MAX_FAILED_LOGINS

def record_failed_otp(username):
    failed_otps[username] += 1
    return failed_otps[username] >= MAX_FAILED_OTPS

def record_rbac_violation(username):
    rbac_violations[username] += 1
    return rbac_violations[username] >= MAX_RBAC_VIOLATIONS

def record_request(username):
    now = time.time()
    request_timestamps[username].append(now)

    request_timestamps[username] = [
        t for t in request_timestamps[username] if now - t <= 10
    ]

    return len(request_timestamps[username]) >= MAX_REQUESTS_PER_10_SEC

def reset_user(username):
    failed_logins[username] = 0
    failed_otps[username] = 0
    rbac_violations[username] = 0
    request_timestamps[username] = []

def is_suspicious_login_time():
    """
    Returns True if login occurs between 01:30 AM and 04:30 AM
    """
    now = datetime.now().time()

    start = dtime(1, 30)   # 01:30 AM
    end = dtime(4, 30)     # 04:30 AM

    return start <= now <= end

