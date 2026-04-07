import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from app import app

def test_enrollment():
    with app.test_client() as client:
        # Mock a logged in session for a user
        with client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = "student1"
            sess['role'] = "student"
            sess['trust_score'] = 100
            
        print("Fetching /enroll_totp...")
        response = client.get('/enroll_totp')
        print(f"Status Code: {response.status_code}")
        
        html = response.data.decode('utf-8')
        if "Setup Google Authenticator" in html and "data:image/png;base64" in html:
            print("SUCCESS: QR Code and Setup page rendered correctly!")
        else:
            print("FAILED: Did not find expected QR code HTML.")
            if "Redirecting" in html:
                print("Got redirected! Check login state.")
            
if __name__ == "__main__":
    test_enrollment()
