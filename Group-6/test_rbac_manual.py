"""
Manual Test to Verify RBAC and Trust Score Reduction
=======================================================

This script simulates a student trying to access an admin route.

Expected Behavior:
1. VPN server receives access request for /admin/users
2. VPN server detects RBAC violation (student accessing admin path)
3. VPN server reduces trust score by 15 points
4. VPN server returns JWT_DOWNGRADED response
5. App.py receives the response and:
   - Updates session trust score
   - Persists to database
   - Logs to trust_history table
   - Logs to actions.log
   - Blocks access and redirects to dashboard
6. User sees flash message with reduced trust score
"""

import requests
import jwt
from datetime import datetime, timedelta

# Configuration
APP_URL = "http://127.0.0.1:5000"
JWT_SECRET = "your_jwt_secret_key"

def create_jwt(username, role):
    """Create a JWT for testing"""
    payload = {
        "sub": username,
        "role": role,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def test_rbac_violation():
    """Test that student cannot access admin routes"""
    print("=" * 60)
    print("Testing RBAC Violation and Trust Score Reduction")
    print("=" * 60)
    
    # Create a session
    session = requests.Session()
    
    # 1. Login as student
    print("\n1. Logging in as student1...")
    login_data = {
        "username": "student1",
        "password": "student123"
    }
    response = session.post(f"{APP_URL}/login", data=login_data)
    print(f"   Login response: {response.status_code}")
    
    # Check if we got to OTP page
    if "verify_otp" in response.url or "OTP" in response.text:
        print("   ✓ Login initiated, OTP required")
        print("   NOTE: You need to complete OTP verification manually")
        print("   After OTP, try accessing: http://127.0.0.1:5000/admin/users")
        print("\n2. Expected behavior:")
        print("   - Should be redirected to /dashboard")
        print("   - Should see flash message: 'ACCESS DENIED: Trust score reduced'")
        print("   - Trust score should be reduced by 15 points")
        print("   - Check logs/actions.log for TRUST_REDUCED entry")
        print("   - Check logs/session.log for VPN decision log")
        print("   - Check logs/security.log for RBAC violation")
    else:
        print(f"   ✗ Unexpected response")
    
    print("\n" + "=" * 60)
    print("Check the following logs:")
    print("  - logs/actions.log")
    print("  - logs/session.log")
    print("  - logs/security.log")
    print("=" * 60)

if __name__ == "__main__":
    test_rbac_violation()
