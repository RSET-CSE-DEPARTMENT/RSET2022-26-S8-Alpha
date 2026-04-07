from app import app
from flask import session, url_for
import unittest

class TestLogoutReason(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.config['WTF_CSRF_ENABLED'] = False
        self.client = self.app.test_client()

    def test_logout_with_reason(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'
            sess['logout_reason'] = "Security Alert: Reason"

        response = self.client.get('/logout', follow_redirects=True)
        
        # Check if logout_reason is flashed
        # In Flask tests, flashed messages are available in the session or can be checked in follow_redirects
        # But session is cleared in logout.
        # So we check if the message appears in the response data (rendered on login page)
        self.assertIn(b"Security Alert: Reason", response.data)
        self.assertIn(b"confirm", response.data or b"") # Just checking for JS alert logic if possible
        # Since we use alert() in base.html, we check if the JS is rendered
        self.assertIn(b'alert("Security Alert: Reason");', response.data)

    def test_logout_without_reason(self):
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['username'] = 'testuser'

        response = self.client.get('/logout', follow_redirects=True)
        self.assertIn(b"Logged out successfully.", response.data)

if __name__ == '__main__':
    unittest.main()
