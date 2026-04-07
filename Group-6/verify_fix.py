import unittest
from unittest.mock import patch, MagicMock
from flask import session, url_for
from app import app, role_required
import jwt
import datetime

class TestRBAC(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.app.config['TESTING'] = True
        self.app.secret_key = "test_secret"
        self.client = self.app.test_client()
        self.ctx = self.app.test_request_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    @patch('app.check_access')
    def test_role_required_block_on_downgrade(self, mock_check_access):
        # Mock VPN response for RBAC violation
        mock_check_access.return_value = '{"action": "JWT_DOWNGRADED", "trust": 45, "reason": "RBAC_VIOLATION"}'
        
        # Simulate logged in student
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
            sess['trust_score'] = 100
        
        # Define a protected route
        @role_required(['admin'])
        def admin_route():
            return "ok"
            
        # Call it
        result = admin_route()
        
        # Should be a redirect
        self.assertEqual(result.status_code, 302)
        self.assertTrue("/dashboard" in result.location)
        
        # Trust score should be updated in session
        self.assertEqual(session['trust_score'], 45)

    @patch('app.check_access')
    def test_role_required_allow(self, mock_check_access):
        # Mock VPN response for Allowed
        mock_check_access.return_value = 'ALLOWED:/student/marks'
        
        # Simulate logged in student
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
            sess['jwt'] = 'valid.jwt.token'
        
        # Define a protected route
        @role_required(['student'])
        def student_route():
            return "ok"
            
        # Call it
        result = student_route()
        
        # Should be ok
        self.assertEqual(result, "ok")

    @patch('app.check_access')
    def test_role_required_default_deny(self, mock_check_access):
        # Mock VPN response for Unknown/Invalid
        mock_check_access.return_value = 'TOKEN_INVALID'
        
        # Simulate logged in student
        with self.client.session_transaction() as sess:
            sess['user_id'] = 1
            sess['role'] = 'student'
        
        # Define a protected route
        @role_required(['student'])
        def student_route():
            return "ok"
            
        # Call it
        result = student_route()
        
        # Should be a redirect (Denied)
        self.assertEqual(result.status_code, 302)

if __name__ == '__main__':
    unittest.main()
