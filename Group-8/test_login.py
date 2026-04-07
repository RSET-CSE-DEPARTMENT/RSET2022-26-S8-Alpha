"""
Test script to verify login functionality
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'echojournal.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate
from django.test import Client

print("\n" + "="*60)
print("TESTING LOGIN FUNCTIONALITY")
print("="*60)

# Test 1: List all users
print("\n1. Checking users in database:")
users = User.objects.all()
for user in users:
    print(f"   ✓ {user.username} (active: {user.is_active}, staff: {user.is_staff})")

# Test 2: Authentication test
print("\n2. Testing authentication:")
test_users = [
    ('testuser', 'testpass123'),
    ('adarsh', 'testpass123'),  # Try with common password
]

for username, password in test_users:
    user = authenticate(username=username, password=password)
    if user:
        print(f"   ✓ {username} - Authentication SUCCESSFUL")
    else:
        print(f"   ✗ {username} - Authentication FAILED")

# Test 3: HTTP Login test
print("\n3. Testing HTTP login:")
client = Client()

response = client.get('/login/')
print(f"   Login page status: {response.status_code}")

# Try to login with testuser
response = client.post('/login/', {
    'username': 'testuser',
    'password': 'testpass123'
})
print(f"   POST login status: {response.status_code}")
print(f"   Redirect location: {response.get('Location', 'No redirect')}")

print("\n" + "="*60)
print("CREDENTIALS TO TRY:")
print("="*60)
print("Username: testuser")
print("Password: testpass123")
print("\nOR\n")
print("Username: adarsh")
print("Password: [Try the password you set for this user]")
print("="*60 + "\n")
