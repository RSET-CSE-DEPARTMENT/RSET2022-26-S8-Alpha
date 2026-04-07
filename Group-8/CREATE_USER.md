# Creating a User for EchoJournal

## Method 1: Using Django Admin (Recommended)

1. Start the development server:
   ```
   python manage.py runserver
   ```

2. Create a superuser if you haven't already:
   ```
   python manage.py createsuperuser
   ```
   
3. Follow the prompts to set:
   - Username
   - Email (optional)
   - Password

## Method 2: Using Python Shell

1. Open Django shell:
   ```
   python manage.py shell
   ```

2. Run these commands:
   ```python
   from django.contrib.auth.models import User
   User.objects.create_user('testuser', 'test@example.com', 'testpass123')
   ```

## Logging In

1. Start the server: `python manage.py runserver`
2. Navigate to: `http://localhost:8000/login/`
3. Enter your username and password
4. You'll be redirected to the dashboard automatically!

## Default Test User (if created)
- Username: testuser
- Password: testpass123
