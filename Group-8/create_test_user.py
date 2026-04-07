"""
Quick script to create a test user for EchoJournal.
Run with: python create_test_user.py
"""

import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'echojournal.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth import authenticate

def create_test_user():
    username = 'testuser'
    email = 'test@example.com'
    password = 'testpass123'
    
    print("=" * 50)
    print("ECHOJOURNAL USER MANAGEMENT")
    print("=" * 50)
    
    # List all existing users
    all_users = User.objects.all()
    print(f"\nExisting users in database: {all_users.count()}")
    for user in all_users:
        print(f"  - {user.username} (Active: {user.is_active})")
    
    # Check if user already exists
    if User.objects.filter(username=username).exists():
        print(f"\n⚠ User '{username}' already exists!")
        
        # Try to authenticate
        user = authenticate(username=username, password=password)
        if user is not None:
            print(f"✓ Authentication test PASSED for '{username}'")
        else:
            print(f"✗ Authentication test FAILED for '{username}'")
            print(f"\nDeleting existing user and creating new one...")
            User.objects.filter(username=username).delete()
            user = User.objects.create_user(username, email, password)
            user.save()
            print(f"✓ User recreated successfully!")
    else:
        # Create the user
        user = User.objects.create_user(username, email, password)
        user.save()
        print(f"\n✓ Successfully created user!")
    
    # Final authentication test
    test_auth = authenticate(username=username, password=password)
    print("\n" + "=" * 50)
    print("LOGIN CREDENTIALS:")
    print("=" * 50)
    print(f"  Username: {username}")
    print(f"  Password: {password}")
    print(f"  Login URL: http://localhost:8000/login/")
    print(f"\n  Auth Test: {'✓ PASSED' if test_auth else '✗ FAILED'}")
    print("=" * 50)

if __name__ == '__main__':
    create_test_user()
