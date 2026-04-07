# 🔐 Login Troubleshooting Guide

## ✅ Verified Working Credentials

Based on the database check, these credentials are CONFIRMED working:

**Username:** `testuser`  
**Password:** `testpass123`

**Alternative User:**
**Username:** `adarsh` (superuser/admin)  
**Password:** [You set this password - if you forgot it, see reset instructions below]

---

## 🛠️ Troubleshooting Steps

### Step 1: Clear Browser Cache & Cookies
The most common issue is cached session data.

1. Press `Ctrl + Shift + Delete` (Windows/Linux) or `Cmd + Shift + Delete` (Mac)
2. Select "Cookies and other site data" and "Cached images and files"
3. Click "Clear data"
4. Or try **Incognito/Private mode**: `Ctrl + Shift + N`

### Step 2: Verify Server is Running
```powershell
python manage.py runserver
```
Server should be at: http://127.0.0.1:8000/

### Step 3: Try Direct Login URL
Go to: http://127.0.0.1:8000/login/ (not http://localhost:8000/login/)

### Step 4: Check for Typos
- Username: `testuser` (all lowercase, no spaces)
- Password: `testpass123` (all lowercase, no spaces)
- Make sure CAPS LOCK is off

### Step 5: Reset adarsh Password (If you want to use that account)
```powershell
python manage.py shell
```
Then run:
```python
from django.contrib.auth.models import User
user = User.objects.get(username='adarsh')
user.set_password('newpassword123')
user.save()
exit()
```

### Step 6: Create a New User
Run the creation script:
```powershell
python create_test_user.py
```

---

## 🔍 Manual Testing

Run this to verify authentication works:
```powershell
python test_login.py
```

---

## 📝 Common Issues

### Issue: "Invalid username or password"
**Causes:**
1. ❌ Browser has old session cookies
2. ❌ CAPS LOCK is on
3. ❌ Extra spaces in username/password
4. ❌ Using wrong password for 'adarsh' user

**Solution:** 
- Use testuser/testpass123
- Clear cookies
- Try incognito mode

### Issue: Form doesn't submit
**Causes:**
1. JavaScript error
2. CSRF token issue

**Solution:**
- Check browser console (F12)
- Reload page
- Try different browser

---

## ✨ Quick Start

1. **Start server:**
   ```powershell
   python manage.py runserver
   ```

2. **Open browser** (preferably in incognito mode)
   
3. **Go to:** http://127.0.0.1:8000/login/

4. **Login with:**
   - Username: `testuser`
   - Password: `testpass123`

5. **You should be redirected to:** http://127.0.0.1:8000/ (dashboard)

---

## 🆘 Still Not Working?

Try this step-by-step:

1. Stop the server (Ctrl+C if running)
2. Close all browser windows
3. Restart the server: `python manage.py runserver`
4. Open a NEW incognito window
5. Go to http://127.0.0.1:8000/login/
6. Type credentials carefully
7. Click "Sign In"

If this doesn't work, the issue might be with the session middleware. Check the terminal where the server is running for any error messages.
