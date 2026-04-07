# =============================================================================
# STUDENT MANAGEMENT PORTAL - Complete Flask Application
# Features: Student, Parent, Faculty, Admin Portals with Zero Trust Security
# =============================================================================

import os
import time
import socket
import json
import sqlite3
import secrets
import hashlib
import random
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import Flask, render_template, request, session, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash, check_password_hash
from vpn_client_adapter import check_access
from dotenv import load_dotenv
import jwt
import smtplib
import ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from base64 import b64decode
import sys
import io
import base64
import pyotp
import qrcode

# Load environment variables from .env (must match vpn_server.py)
load_dotenv()

# Add zero_trust_vpn to path for logger import
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "zero_trust_vpn"))
import logger
from db_adapter import db_adapter

# =============================================================================
# CONFIGURATION
# =============================================================================
SECRET_KEY = os.getenv("SECRET_KEY", "your_super_secret_key_change_in_production_12345")
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_key")
DB_PATH = "db/portal.db"
PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
TRUST_SCORE_THRESHOLD = 50
SENSITIVE_TRUST_THRESHOLD = 60  # Marks, Attendance, Fees require at least 60
IDLE_TIMEOUT_SECONDS = 300  # 5 minutes idle timeout
BLOCK_DURATION_MINUTES = 10
DEVICE_TRUST_THRESHOLD = 1
LOG_FILE = "logs/actions.log"
READ_ONLY_MODE = False

# SMTP CONFIG
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SENDER_EMAIL = "techupport2363@gmail.com"
APP_PASSWORD = "vjjd brfa uiul aetm"
ADMIN_EMAIL = "techupport2363@gmail.com"

app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = PERMANENT_SESSION_LIFETIME

def get_real_ip():
    """Get real client IP behind reverse proxy (Render, Nginx, etc.)."""
    forwarded = request.headers.get('X-Forwarded-For', '')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.remote_addr or ''

# Detective helper for Postgres (used for conditional logic in routes)
def is_postgres_mode():
    return db_adapter.is_postgres

# =============================================================================
# DATABASE INITIALIZATION
# =============================================================================
def init_db():
    if not os.path.exists("logs"):
        os.mkdir("logs")
    
    conn = db_adapter.get_connection()
    
    # Tables with compatibility adjustments (SERIAL/AUTOINCREMENT/TIMESTAMP)
    current_is_postgres = conn.is_postgres
    id_type = "SERIAL PRIMARY KEY" if current_is_postgres else "INTEGER PRIMARY KEY AUTOINCREMENT"
    ts_type = "TIMESTAMP DEFAULT CURRENT_TIMESTAMP" if current_is_postgres else "DATETIME DEFAULT CURRENT_TIMESTAMP"
    
    schema = f"""
    -- Users table with security fields
    CREATE TABLE IF NOT EXISTS users (
        id {id_type},
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('student', 'parent', 'faculty', 'admin')),
        email TEXT NOT NULL,
        name TEXT NOT NULL,
        phone TEXT,
        trust_score INTEGER DEFAULT 100,
        blocked_until TEXT,
        failed_attempts INTEGER DEFAULT 0,
        otp_failures INTEGER DEFAULT 0,
        last_login TEXT,
        login_count INTEGER DEFAULT 0,
        active_session INTEGER DEFAULT 0,
        device_fp TEXT,
        typical_login_hour INTEGER,
        last_ip TEXT
    );

    -- Students table
    CREATE TABLE IF NOT EXISTS students (
        id {id_type},
        user_id INTEGER UNIQUE,
        roll TEXT UNIQUE NOT NULL,
        department TEXT DEFAULT 'Computer Science',
        semester INTEGER DEFAULT 1,
        marks TEXT,
        attendance TEXT,
        fees_due REAL DEFAULT 0,
        fees_paid REAL DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Parents table (linked to students)
    CREATE TABLE IF NOT EXISTS parents (
        id {id_type},
        user_id INTEGER UNIQUE,
        student_id INTEGER,
        relationship TEXT DEFAULT 'Parent',
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Faculty table
    CREATE TABLE IF NOT EXISTS faculty (
        id {id_type},
        user_id INTEGER UNIQUE,
        employee_id TEXT UNIQUE,
        department TEXT,
        designation TEXT,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Access logs for security auditing
    CREATE TABLE IF NOT EXISTS access_logs (
        id {id_type},
        user_id INTEGER,
        action TEXT,
        resource TEXT,
        resource_id INTEGER,
        allowed INTEGER,
        reason TEXT,
        ip TEXT,
        ua TEXT,
        timestamp {ts_type}
    );

    -- Profile change requests
    CREATE TABLE IF NOT EXISTS profile_change_requests (
        id {id_type},
        student_id INTEGER,
        field_name TEXT,
        old_value TEXT,
        new_value TEXT,
        trust_score INTEGER,
        requested_at {ts_type},
        status TEXT DEFAULT 'pending',
        reviewed_by INTEGER,
        reviewed_at {ts_type},
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(reviewed_by) REFERENCES users(id)
    );

    -- Trusted devices for adaptive MFA
    CREATE TABLE IF NOT EXISTS trusted_devices (
        id {id_type},
        user_id INTEGER,
        device_id TEXT,
        first_seen {ts_type},
        last_seen {ts_type},
        seen_count INTEGER DEFAULT 1,
        risk_flag INTEGER DEFAULT 0,
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Trust score history
    CREATE TABLE IF NOT EXISTS trust_history (
        id {id_type},
        user_id INTEGER,
        old_score INTEGER,
        new_score INTEGER,
        reason TEXT,
        timestamp {ts_type},
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Announcements
    CREATE TABLE IF NOT EXISTS announcements (
        id {id_type},
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        posted_by INTEGER,
        target_role TEXT DEFAULT 'all',
        created_at {ts_type},
        FOREIGN KEY(posted_by) REFERENCES users(id)
    );

    -- Grievances
    CREATE TABLE IF NOT EXISTS grievances (
        id {id_type},
        student_id INTEGER,
        subject TEXT,
        description TEXT,
        status TEXT DEFAULT 'pending',
        submitted_at {ts_type},
        resolved_at {ts_type},
        resolved_by INTEGER,
        FOREIGN KEY(student_id) REFERENCES users(id),
        FOREIGN KEY(resolved_by) REFERENCES users(id)
    );

    -- Marks table (detailed)
    CREATE TABLE IF NOT EXISTS marks (
        id {id_type},
        student_id INTEGER,
        subject TEXT,
        marks_obtained INTEGER,
        faculty_id INTEGER,
        class_id INTEGER,
        max_marks INTEGER DEFAULT 100,
        exam_type TEXT DEFAULT 'Internal',
        entered_by INTEGER,
        entered_at {ts_type},
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(entered_by) REFERENCES users(id)
    );

    -- Attendance table (detailed)
    CREATE TABLE IF NOT EXISTS attendance (
        id {id_type},
        student_id INTEGER,
        date TEXT,
        status TEXT CHECK(status IN ('present', 'absent', 'late')),
        subject TEXT,
        marked_by INTEGER,
        faculty_id INTEGER,
        class_id INTEGER,
        marked_at {ts_type},
        FOREIGN KEY(student_id) REFERENCES students(id),
        FOREIGN KEY(marked_by) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS device_fingerprints (
        id {id_type},
        user_id INTEGER,
        user_agent TEXT,
        ip_address TEXT,
        first_seen {ts_type}
    );

    CREATE TABLE IF NOT EXISTS parent_grievances (
        id {id_type},
        parent_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'Pending',
        submitted_at {ts_type},
        resolved_at {ts_type},
        resolved_by INTEGER,
        FOREIGN KEY(parent_id) REFERENCES users(id),
        FOREIGN KEY(resolved_by) REFERENCES users(id)
    );

    -- Fee payments
    CREATE TABLE IF NOT EXISTS fee_payments (
        id {id_type},
        student_id INTEGER,
        amount REAL,
        payment_date {ts_type},
        payment_method TEXT,
        transaction_id TEXT,
        FOREIGN KEY(student_id) REFERENCES students(id)
    );

    -- Login history for anomaly detection
    CREATE TABLE IF NOT EXISTS login_history (
        id {id_type},
        user_id INTEGER,
        login_hour INTEGER,
        ip_address TEXT,
        timestamp {ts_type},
        FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    -- Classes table
    CREATE TABLE IF NOT EXISTS classes (
        id {id_type},
        name TEXT NOT NULL,
        department TEXT,
        faculty_id INTEGER,
        semester INTEGER,
        FOREIGN KEY(faculty_id) REFERENCES faculty(id)
    );

    -- Class Enrollments (Students <-> Classes)
    CREATE TABLE IF NOT EXISTS class_enrollments (
        id {id_type},
        class_id INTEGER,
        student_id INTEGER,
        UNIQUE(class_id, student_id),
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- Assignments table
    CREATE TABLE IF NOT EXISTS assignments (
        id {id_type},
        class_id INTEGER,
        title TEXT NOT NULL,
        description TEXT,
        due_date TEXT,
        faculty_id INTEGER,
        created_at {ts_type},
        FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
        FOREIGN KEY(faculty_id) REFERENCES faculty(id)
    );

    -- Submissions table
    CREATE TABLE IF NOT EXISTS submissions (
        id {id_type},
        assignment_id INTEGER,
        student_id INTEGER,
        submission_text TEXT,
        submitted_at {ts_type},
        grade TEXT,
        feedback TEXT,
        FOREIGN KEY(assignment_id) REFERENCES assignments(id) ON DELETE CASCADE,
        FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
    );

    -- New: System Logs (Cloud-ready encrypted logs)
    CREATE TABLE IF NOT EXISTS system_logs (
        id {id_type},
        category TEXT NOT NULL, -- SESSION, SECURITY, ERROR
        username TEXT,
        seq INTEGER,
        nonce TEXT,
        encrypted_data TEXT,
        plain_message TEXT, -- Fallback for unencrypted items
        timestamp {ts_type}
    );
    """
    conn.executescript(schema)
    
    # Ensure trust_history only keeps latest 50 entries
    if current_is_postgres:
        try:
            conn.execute("""
            CREATE OR REPLACE FUNCTION limit_trust_history()
            RETURNS TRIGGER AS $$
            BEGIN
                DELETE FROM trust_history
                WHERE id NOT IN (
                    SELECT id FROM trust_history
                    ORDER BY timestamp DESC, id DESC
                    LIMIT 50
                );
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql;
            """)
            conn.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT 1 FROM pg_trigger WHERE tgname = 'trg_limit_trust_history') THEN
                    CREATE TRIGGER trg_limit_trust_history
                    AFTER INSERT ON trust_history
                    FOR EACH STATEMENT
                    EXECUTE FUNCTION limit_trust_history();
                END IF;
            END
            $$;
            """)
            conn.commit()
        except Exception as e:
            print(f"[WARN] Failed to create Postgres trigger for trust_history: {e}")
    else:
        try:
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS limit_trust_history 
            AFTER INSERT ON trust_history
            BEGIN
                DELETE FROM trust_history WHERE id NOT IN (
                    SELECT id FROM trust_history ORDER BY timestamp DESC, id DESC LIMIT 50
                );
            END;
            """)
            conn.commit()
        except Exception as e:
            print(f"[WARN] Failed to create SQLite trigger for trust_history: {e}")
    
    # Check if we need a default admin
    existing = conn.fetchone("SELECT COUNT(*) as count FROM users")["count"]
    if existing == 0:
        # Create a default admin user if the database is empty
        admin_pass = generate_password_hash("admin123")
        conn.execute("""
            INSERT INTO users (username, password_hash, role, email, name, phone) 
            VALUES (?,?,?,?,?,?)
        """, ("admin", admin_pass, "admin", "admin@portal.com", "System Admin", "0000000000"))
        conn.commit()
        print("[INFO] Empty database detected. Created default admin: 'admin' / 'admin123'")
    
    # Ensure new columns exist (Migration)
    for col_sql in [
        "ALTER TABLE users ADD COLUMN typical_login_hour INTEGER",
        "ALTER TABLE users ADD COLUMN last_ip TEXT",
        "ALTER TABLE users ADD COLUMN totp_secret TEXT",
    ]:
        try:
            conn.execute(col_sql)
            conn.commit()
        except:
            pass

    # Reset active sessions on startup
    try:
        conn.execute("UPDATE users SET active_session=0")
        conn.commit()
        print("[INFO] Active sessions reset")
    except Exception as e:
        print(f"[WARN] Failed to reset sessions: {e}")

    conn.close()


init_db()

# =============================================================================
# DATABASE HELPER
# =============================================================================
def get_db():
    if 'db' not in g:
        g.db = db_adapter.get_connection()
    return g.db

@app.teardown_appcontext
def close_db(error):
    if hasattr(g, 'db'):
        g.db.close()

# =============================================================================
# LOGGING UTILITIES
# =============================================================================
def write_access_log(conn, user_id, action, resource, resource_id, allowed, reason):
    ip = get_real_ip()
    ua = request.headers.get('User-Agent', '')
    conn.execute(
        "INSERT INTO access_logs (user_id, action, resource, resource_id, allowed, reason, ip, ua, timestamp) VALUES (?,?,?,?,?,?,?,?,?)",
        (user_id, action, resource, resource_id, int(bool(allowed)), reason, ip, ua, datetime.utcnow().isoformat())
    )
    # Auto-prune: keep only the latest 50 rows
    try:
        conn.execute("DELETE FROM access_logs WHERE id NOT IN (SELECT id FROM access_logs ORDER BY id DESC LIMIT 50)")
    except Exception as e:
        print(f"[LOG PRUNE] access_logs prune error: {e}")
    conn.commit()

# =============================================================================
# SECURE LOG DECRYPTION FOR ADMIN
# =============================================================================
def parse_log_line(content):
    """Parses a pipe-delimited log string into a structured dictionary."""
    if " | " not in content:
        return {"message": content}
    
    parts = content.split(" | ")
    data = {}
    
    # Track which parts highlight specific known fields
    for part in parts:
        part = part.strip()
        if not part: continue
        
        if "=" in part:
            key, val = part.split("=", 1)
            data[key.lower().strip()] = val.strip()
        elif "⚠ SUSPICIOUS" in part:
            data["decision"] = "ALERT"
            data["status"] = "SUSPICIOUS"
        elif "❌ ERROR" in part:
            data["decision"] = "ERROR"
            data["status"] = "ERROR"
        elif "TRUST_CHANGE" in part:
            data["action"] = "Trust Change"
        elif " → " in part:
            data["action_detail"] = part
            # Extract new trust score from "100 → 85"
            try:
                data["trust"] = part.split(" → ")[-1].strip()
            except: pass
        elif "Trust reduced to" in part:
            try:
                data["trust"] = part.split("reduced to")[-1].strip()
            except: pass
        else:
            # If it's just text, it's probably the action or message
            if "action" not in data:
                data["action"] = part
            elif "message" not in data:
                data["message"] = part
            else:
                data["message"] = data.get("message", "") + " | " + part
                
    # Normalize decision for UI badges
    if "decision" not in data:
        if "status" in data:
            data["decision"] = data["status"]
        else:
            data["decision"] = "INFO"

    # Normalize user field
    if "user" not in data and "username" in data:
        data["user"] = data["username"]
            
    # Normalize action/message for better UI display
    if "action" not in data and "path" in data:
         data["action"] = data["path"]
            
    return data

def get_decrypted_log_entries(log_type="session", limit=100):
    """Refactored to fetch and decrypt entries from the system_logs database table."""
    conn = get_db()
    try:
        cur = conn.execute(
            "SELECT category, seq, nonce, encrypted_data, plain_message, timestamp FROM system_logs WHERE category = ? ORDER BY id DESC LIMIT ?",
            (log_type.upper(), limit)
        )
        rows = cur.fetchall()
    except Exception as e:
        print(f"[ERROR] DB Log Fetch Error: {e}")
        return []

    # Get log key for decryption
    env_key = os.getenv("LOG_KEY")
    aesgcm = None
    if env_key:
        try:
            log_key = base64.b64decode(env_key)
            aesgcm = AESGCM(log_key)
        except:
            pass
    if not aesgcm:
        try:
            with open(logger.LOG_KEY_PATH, "rb") as f:
                log_key = f.read()
            aesgcm = AESGCM(log_key)
        except:
            pass

    entries = []
    for row in rows:
        entry_data = {
            "timestamp": row["timestamp"],
            "encrypted": bool(row["encrypted_data"])
        }
        
        try:
            if row["encrypted_data"] and aesgcm:
                nonce = b64decode(row["nonce"])
                ciphertext = b64decode(row["encrypted_data"])
                decrypted = aesgcm.decrypt(nonce, ciphertext, None).decode("utf-8")
                
                # Split SEQ if present (logger.py adds it)
                if " | " in decrypted:
                    parts = decrypted.split(" | ", 1)
                    if parts[0].startswith("SEQ="):
                        entry_data["seq"] = parts[0].split("=", 1)[1]
                        content = parts[1]
                    else:
                        content = decrypted
                else:
                    content = decrypted
            else:
                # Fallback to plain message if logic or key missing
                content = row["plain_message"] or "Log not decryptable"
                if row["seq"]: entry_data["seq"] = row["seq"]

            # Parse the actual log content (remains same logic)
            parsed = parse_log_line(content)
            entry_data.update(parsed)
            # Format timestamp properly to local time
            try:
                if entry_data.get('timestamp'):
                    dt = datetime.fromisoformat(entry_data['timestamp'].replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    entry_data['timestamp'] = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            
            entries.append(entry_data)
        except Exception as e:
            entries.append({"timestamp": row["timestamp"], "message": f"Error parsing log: {str(e)}"})
    
    return entries

def log_action(action):
    """Updated to use the secure encrypted logger."""
    username = session.get("username", "system")
    logger.log_event(username, "WEB_PORTAL_ACTION", "INFO", action)

# =============================================================================
# SECURITY UTILITIES
# =============================================================================
def trust_allows_sensitive():
    return session.get("trust_score", 100) >= SENSITIVE_TRUST_THRESHOLD

def get_device_fingerprint():
    """Use a persistent secure cookie for device fingerprinting instead of volatile IPs."""
    device_id = request.cookies.get("trusted_device")
    if device_id:
        return device_id
        
    # Fallback if cookie not set yet: hash User-Agent and IP subnet (first 3 octets)
    ua = request.headers.get("User-Agent", "")
    ip = get_real_ip()
    # Mask last octet to prevent false flags on minor mobile IP cycles
    subnet = ".".join(ip.split(".")[:3]) if "." in ip else ip
    raw = ua + subnet
    return hashlib.sha256(raw.encode()).hexdigest()

def check_device_fingerprint(user_id):
    device_id = get_device_fingerprint()
    ua = request.headers.get("User-Agent", "")
    ip = get_real_ip()

    conn = get_db()
    existing = conn.execute("""
        SELECT id FROM device_fingerprints
        WHERE user_id=? AND ip_address=?
    """, (user_id, device_id)).fetchone()

    if not existing:
        conn.execute("""
            INSERT INTO device_fingerprints (user_id, user_agent, ip_address)
            VALUES (?, ?, ?)
        """, (user_id, ua, device_id))
        conn.commit()

        flash("⚠ New device detected. Trust score reduced.", "warning")


def blocked(user_row):
    if not user_row:
        return False
    bu = user_row["blocked_until"]
    if bu:
        try:
            return datetime.fromisoformat(bu) > datetime.utcnow()
        except:
            return False
    return False

def calculate_trust(user_row):
    score = 100
    fa = user_row["failed_attempts"] or 0
    score -= min(fa * 5, 40)
    of = user_row["otp_failures"] or 0
    score -= min(of * 7, 35)
    last_login = user_row["last_login"]
    if last_login:
        try:
            last_dt = datetime.fromisoformat(last_login)
            if datetime.utcnow() - last_dt > timedelta(days=30):
                score -= 10
        except:
            pass
    return max(0, min(100, score))

def record_trust_change(conn, user_id, old, new, reason):
    conn.execute("INSERT INTO trust_history (user_id, old_score, new_score, reason, timestamp) VALUES (?,?,?,?,?)",
                 (user_id, old, new, reason, datetime.utcnow().isoformat()))
    conn.commit()

def record_device(conn, user_id, device_id):
    now = datetime.utcnow().isoformat()
    row = conn.execute("SELECT * FROM trusted_devices WHERE user_id=? AND device_id=?", (user_id, device_id)).fetchone()
    if row:
        conn.execute("UPDATE trusted_devices SET last_seen=?, seen_count = seen_count + 1 WHERE id=?", (now, row["id"]))
    else:
        conn.execute("INSERT INTO trusted_devices (user_id, device_id, first_seen, last_seen, seen_count) VALUES (?,?,?,?,?)",
                     (user_id, device_id, now, now, 1))
    conn.commit()

def device_seen_count(conn, user_id, device_id):
    row = conn.execute("SELECT seen_count FROM trusted_devices WHERE user_id=? AND device_id=?", (user_id, device_id)).fetchone()
    return row["seen_count"] if row else 0

def should_trigger_mfa(conn, user_row, device_id):
    if device_seen_count(conn, user_row["id"], device_id) < DEVICE_TRUST_THRESHOLD:
        return True
    trust_score = user_row["trust_score"] if user_row["trust_score"] is not None else calculate_trust(user_row)
    if trust_score < 50:
        return True
    hour = datetime.utcnow().hour
    if hour < 5 or hour > 22:
        return True
    if (user_row["failed_attempts"] or 0) >= 3:
        return True
    return False

def send_otp_email(email, otp):
    """Send OTP via real SMTP email service (Disabled for TOTP)"""
    pass

def detect_anomalies(user_id, current_ip):
    """Detect Time-of-Day and Impossible Travel anomalies"""
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        return []

    anomalies = []
    
    # 1. Time-of-Day Analysis
    current_hour = datetime.now().hour
    typical_hour = user["typical_login_hour"]
    
    if typical_hour is not None:
        # If login is more than 4 hours away from typical hour, it's an anomaly
        diff = abs(current_hour - typical_hour)
        if diff > 12: diff = 24 - diff # Handle circular clock
        
        if diff > 4:
            anomalies.append({
                "type": "TIME_OF_DAY",
                "penalty": 10,
                "msg": f"Unusual login time: {current_hour}:00 (Typical: {typical_hour}:00)"
            })

    # 2. Impossible Travel Detection (Temporarily disabled mock IP distance math)
    # The previous logic subtracted IP octets and acted as kilometers, 
    # breaking completely with public routing. We'll only check Time-of-Day for now.
    last_ip = user["last_ip"]
    last_login_str = user["last_login"]
    
    if last_ip and last_ip != current_ip and last_login_str:
        # Just record that an IP change happened, but don't penalize 
        # heavily unless we have a real GeoIP DB.
        pass
        
    return anomalies

def record_login_event(user_id, ip):
    """Record login for future anomaly detection history"""
    conn = get_db()
    now_hour = datetime.now().hour
    now_time = datetime.utcnow().isoformat()
    
    # Record in history
    conn.execute(
        "INSERT INTO login_history (user_id, login_hour, ip_address, timestamp) VALUES (?, ?, ?, ?)",
        (user_id, now_hour, ip, now_time)
    )
    
    # Calculate new typical hour (most frequent)
    history = conn.execute(
        "SELECT login_hour, COUNT(*) as count FROM login_history WHERE user_id=? GROUP BY login_hour ORDER BY count DESC LIMIT 1",
        (user_id,)
    ).fetchone()
    
    typical_hour = history["login_hour"] if history else now_hour
    
    # Update user record
    conn.execute(
        "UPDATE users SET typical_login_hour=?, last_ip=?, last_login=?, login_count=login_count+1 WHERE id=?",
        (typical_hour, ip, now_time, user_id)
    )
    conn.commit()

# =============================================================================
# BEHAVIOR TRACKING
# =============================================================================
def track_behavior(action):
    now = datetime.now().timestamp()
    if "behavior_log" not in session:
        session["behavior_log"] = []
        session["behavior_log_last_reset"] = now
    
    last_reset = session.get("behavior_log_last_reset", now)
    if now - last_reset > 600:
        session["behavior_log"] = []
        session["behavior_log_last_reset"] = now
        log_action(f"Behavior log auto-reset for {session.get('username')}")
    
    session["behavior_log"].append({"action": action, "timestamp": now})

def is_behavior_unusual():
    logs = session.get("behavior_log", [])
    now = datetime.now().timestamp()
    recent_actions = [l for l in logs if now - l["timestamp"] < 60]
    
    if len(recent_actions) > 30:
        return True
    
    toggle_count = sum(1 for l in recent_actions if l["action"] == "toggle_readonly")
    if toggle_count > 5:
        return True
    
    return False

def update_trust(action=None):
    if "trust_score" not in session:
        session["trust_score"] = 100
    if action == "suspicious":
        session["trust_score"] -= random.randint(10, 30)
    else:
        session["trust_score"] -= random.randint(0, 2)
    session["trust_score"] = max(0, min(100, session["trust_score"]))

# =============================================================================
# DECORATORS
# =============================================================================
SAFE_ROUTES = {
    "static",
    "dashboard",
    "student_notices",
    "faculty_notices",
    "parent_notices",
    "logout",
    "index",
    "verify_otp",
    "enroll_totp"
}


def reduce_trust(reason, points):
    conn = get_db()
    uid = session.get("pre_auth_user_id") or session.get("user_id")

    if not uid:
        return

    user = conn.execute(
        "SELECT trust_score FROM users WHERE id=?",
        (uid,)
    ).fetchone()

    current = user["trust_score"] if user["trust_score"] is not None else 100
    new_score = max(current - points, 0)

    conn.execute(
        "UPDATE users SET trust_score=? WHERE id=?",
        (new_score, uid)
    )
    conn.commit()

    session["trust_score"] = new_score
    log_action(f"Trust reduced by {points} due to {reason}")

# Rate limiting decorator
def rate_limit(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return f(*args, **kwargs)
        
        # Track this request
        track_behavior(request.endpoint or "unknown")
        
        # Check for unusual behavior (rate limiting)
        if is_behavior_unusual():
            conn = get_db()
            user_id = session.get("user_id")
            username = session.get("username")
            
            # Check if already flagged for rate limiting in this session
            rate_limit_count = session.get("rate_limit_violations", 0)
            session["rate_limit_violations"] = rate_limit_count + 1
            
            # Get current trust score
            try:
                user = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
                old_trust = user["trust_score"] if user else 100
                new_trust = max(old_trust - 10, 0)
                
                # Update trust score in database
                conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
                
                # Log to trust_history table
                conn.execute(
                    "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                    (user_id, old_trust, new_trust, "RATE_LIMIT - Excessive requests")
                )
                conn.commit()
                
                # Update session
                session["trust_score"] = new_trust
                
                # Log to actions.log
                log_action(
                    f"TRUST_REDUCED | User: {username} | "
                    f"Reason: RATE_LIMIT | {old_trust} -> {new_trust} | Violations: {session['rate_limit_violations']}"
                )
                
                # Console print for debugging
                print(f"[RATE_LIMIT] User {username} exceeded rate limit | Trust: {old_trust} -> {new_trust} | Violations: {session['rate_limit_violations']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to reduce trust score for rate limit: {e}")
                log_action(f"ERROR reducing trust score for rate limit for user {user_id}: {e}")
            
            # Block access if too many violations (>3 in this session)
            if session["rate_limit_violations"] > 7:
                session["logout_reason"] = f"Security Alert: Excessive requests. Trust score reduced to {new_trust}."
                return redirect(url_for("logout"))
            
            # Show warning
            flash(f"⚠️ Slow down! Rate limit warning. Trust score reduced to {new_trust}.", "warning")
        
        return f(*args, **kwargs)
    
    return wrapper


def check_trust_recovery():
    """Award trust points for sustained good behavior (5 minutes without violations)"""
    if "user_id" not in session:
        return

    now = datetime.now().timestamp()
    last_recovery = session.get("last_trust_recovery")
    
    # Initialize last_recovery if not set
    if not last_recovery:
        session["last_trust_recovery"] = now
        return

    # Check if 5 minutes (300 seconds) has passed
    if now - last_recovery >= 300:
        user_id = session.get("user_id")
        username = session.get("username")
        conn = get_db()
        
        try:
            user = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
            if user:
                old_trust = user["trust_score"]
                if old_trust < 100:
                    new_trust = min(100, old_trust + 2)
                    
                    # Update database
                    conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
                    
                    # Log to history
                    conn.execute(
                        "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                        (user_id, old_trust, new_trust, "PASSIVE_RECOVERY - Sustained good behavior")
                    )
                    conn.commit()
                    
                    # Update session
                    session["trust_score"] = new_trust
                    session["last_trust_recovery"] = now
                    
                    # Log to actions.log
                    log_action(f"TRUST_RECOVERED | User: {username} | Reason: PASSIVE_RECOVERY | {old_trust} -> {new_trust}")
                    print(f"[RECOVERY] User {username} gained trust | {old_trust} -> {new_trust}")
                else:
                    # Already at max, just reset the timer
                    session["last_trust_recovery"] = now
        except Exception as e:
            print(f"[ERROR] Trust recovery failed: {e}")

def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            flash("Please login to continue.", "warning")
            return redirect(url_for('login'))
        
        # Check for trust recovery
        check_trust_recovery()

        # === SOFT LOCK CHECK ===
        trust_score = session.get("trust_score", 100)
        if trust_score < 25 and request.endpoint not in ['restricted', 'request_admin_help', 'logout', 'static']:
            return redirect(url_for('restricted'))
        
        # === RATE LIMITING CHECK ===
        # Track this request
        track_behavior(request.endpoint or "unknown")
        
        # Check for unusual behavior (rate limiting)
        if is_behavior_unusual():
            conn = get_db()
            user_id = session.get("user_id")
            username = session.get("username")
            
            # Check if already flagged for rate limiting in this session
            rate_limit_count = session.get("rate_limit_violations", 0)
            session["rate_limit_violations"] = rate_limit_count + 1
            
            # Get current trust score
            try:
                user = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
                old_trust = user["trust_score"] if user else 100
                new_trust = max(old_trust - 10, 0)
                
                # Update trust score in database
                conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
                
                # Log to trust_history table
                conn.execute(
                    "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                    (user_id, old_trust, new_trust, "RATE_LIMIT - Excessive requests")
                )
                conn.commit()
                
                # Update session
                session["trust_score"] = new_trust
                
                # Log to actions.log
                log_action(
                    f"TRUST_REDUCED | User: {username} | "
                    f"Reason: RATE_LIMIT | {old_trust} -> {new_trust} | Violations: {session['rate_limit_violations']}"
                )
                
                # Console print for debugging
                print(f"[RATE_LIMIT] User {username} exceeded rate limit | Trust: {old_trust} -> {new_trust} | Violations: {session['rate_limit_violations']}")
                
            except Exception as e:
                print(f"[ERROR] Failed to reduce trust score for rate limit: {e}")
                log_action(f"ERROR reducing trust score for rate limit for user {user_id}: {e}")
            
            # Block access if too many violations (>3 in this session)
            if session["rate_limit_violations"] > 7:
                flash(f"⛔ Too many requests! Your account has been temporarily restricted. Trust score: {new_trust}", "danger")
                return redirect(url_for("logout"))
            
            # Show warning
            flash(f"⚠️ Slow down! Rate limit warning. Trust score reduced to {new_trust}.", "warning")
        
        # === END RATE LIMITING CHECK ===
        
        # Check idle timeout
        last_activity = session.get("last_activity")
        if last_activity:
            last_dt = datetime.fromisoformat(last_activity)
            if (datetime.utcnow() - last_dt).total_seconds() > IDLE_TIMEOUT_SECONDS:
                uid = session.get("user_id")
                conn = get_db()
                if uid:
                    conn.execute("UPDATE users SET active_session=0 WHERE id=?", (uid,))
                    write_access_log(conn, uid, "auto_logout", "session", None, True, "idle_timeout")
                conn.commit()
                session["logout_reason"] = "Session expired due to inactivity."
                return redirect(url_for("logout"))
        
        # Check trust score
        conn = get_db()
        user = conn.execute("SELECT trust_score FROM users WHERE id=?", (session["user_id"],)).fetchone()
        trust = user["trust_score"] if user else 0
        endpoint = request.endpoint
        
        if trust < 30:
            write_access_log(conn, session["user_id"], "trust_block", endpoint, None, False, f"trust={trust}")
            session["logout_reason"] = f"Account locked: Trust score ({trust}) below critical threshold."
            return redirect(url_for("logout"))
        
        if 30 <= trust < 50 and endpoint not in SAFE_ROUTES:
            flash("Limited access due to low trust score.", "warning")
            write_access_log(conn, session["user_id"], "trust_limited", endpoint, None, False, f"trust={trust}")
            return redirect(url_for("dashboard"))
        
        session["last_activity"] = datetime.utcnow().isoformat()
        return f(*args, **kwargs)
    return wrapped

from vpn_client_adapter import check_access   # new module

def role_required(allowed_roles, readonly_for_admin=False):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):

            if "user_id" not in session:
                return redirect(url_for("login"))

            # Simple role check with trust score reduction and logging
            role = session.get("role")
            path = request.path
            
            if role not in allowed_roles:
                # RBAC VIOLATION - Reduce trust score and log
                conn = get_db()
                user_id = session.get("user_id")
                username = session.get("username")
                
                try:
                    # Get current trust score
                    user = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
                    old_trust = user["trust_score"] if user else 100
                    new_trust = max(old_trust - 15, 0)
                    
                    # Update trust score in database
                    conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
                    
                    # Log to trust_history table
                    conn.execute(
                        "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                        (user_id, old_trust, new_trust, f"RBAC_VIOLATION - Path: {path}")
                    )
                    conn.commit()
                    
                    # Update session
                    session["trust_score"] = new_trust
                    
                    # Log to actions.log file
                    log_action(
                        f"TRUST_REDUCED | User: {username} | "
                        f"Path: {path} | {old_trust} -> {new_trust} | Reason: RBAC_VIOLATION"
                    )
                    
                    # Console print for debugging
                    print(f"[RBAC] User {username} ({role}) denied access to {path} | Trust: {old_trust} -> {new_trust}")
                    
                except Exception as e:
                    print(f"[ERROR] Failed to reduce trust score: {e}")
                    log_action(f"ERROR reducing trust score for user {user_id}: {e}")
                
                flash(f"⛔ Access denied: Trust score reduced to {new_trust}. Reason: RBAC violation", "danger")
                
                # If trust dropped significantly, force logout
                if new_trust < 40:
                    session["logout_reason"] = f"Security Policy Violation: Unauthorized access attempt to {path}. Trust score dropped to {new_trust}."
                    return redirect(url_for("logout"))
                    
                return redirect(url_for("dashboard"))
            
            # Check for readonly mode vs admin logic
            if readonly_for_admin and role == "admin" and "faculty" in allowed_roles:
               kwargs["readonly"] = True
            
            return func(*args, **kwargs)

            # VPN ENFORCEMENT (TEMPORARILY DISABLED - causing connection issues)
            # jwt_token = session.get("jwt")
            # path = request.path
            # 
            # # 🔐 Ask Zero Trust VPN Server
            # decision = check_access(jwt_token, path)
            # 
            # # 🚨 SESSION TERMINATED
            # if decision.startswith("SESSION_TERMINATED"):
            #     session.clear()
            #     flash(f"Session terminated: {decision}", "danger")
            #     return redirect(url_for("login"))
            # 
            # # 🚫 ACCESS DENIED
            # if decision.startswith("ACCESS_DENIED"):
            #     flash("Access denied by Zero Trust policy.", "danger")
            #     return render_template("access_denied.html")
            # 
            # # 🔐 JWT DOWNGRADED - RBAC Violation detected
            # if decision.startswith("{"):
            #     data = json.loads(decision)
            #     if data.get("action") == "JWT_DOWNGRADED":
            #         # Get old trust score before update
            #         old_trust = session.get("trust_score", 100)
            #         new_trust = data["trust"]
            #         reason = data.get("reason", "UNKNOWN")
            #         
            #         # 1. Update Session Trust
            #         session["trust_score"] = new_trust
            #         
            #         # 2. Persist to DB!
            #         try:
            #             conn = get_db()
            #             user = conn.execute("SELECT trust_score FROM users WHERE id=?", (session["user_id"],)).fetchone()
            #             db_old_trust = user["trust_score"] if user else old_trust
            #             
            #             conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, session["user_id"]))
            #             
            #             # Log to trust_history table
            #             conn.execute(
            #                 "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
            #                 (session["user_id"], db_old_trust, new_trust, f"{reason} - Path: {path}")
            #             )
            #             conn.commit()
            #             
            #             # Log to file
            #             log_action(
            #                 f"TRUST_REDUCED | User: {session.get('username')} | "
            #                 f"Path: {path} | {db_old_trust} → {new_trust} | Reason: {reason}"
            #             )
            #             
            #             # Console print for debugging
            #             print(f"[TRUST] User {session.get('username')} trust reduced: {db_old_trust} → {new_trust} (Reason: {reason})")
            #             
            #         except Exception as e:
            #             print(f"[ERROR] Failed to persist trust score: {e}")
            #             log_action(f"ERROR persisting trust score for user {session.get('user_id')}: {e}")
            # 
            #         # 3. BLOCK ACCESS
            #         flash(f"⛔ ACCESS DENIED: Trust score reduced to {new_trust}. Reason: {reason}", "danger")
            #         return redirect(url_for("dashboard"))
            # 
            # # ✅ Allow Only if Explicitly Approved
            # if decision.startswith("ALLOWED:"):
            #     # Check for readonly mode vs admin logic
            #     role = session.get("role")
            #     if readonly_for_admin and role == "admin" and "faculty" in allowed_roles:
            #        kwargs["readonly"] = True
            #     return func(*args, **kwargs)
            # 
            # # ⛔ FALLBACK DENY
            # flash("Access verification failed (Security Policy).", "danger")
            # return redirect(url_for("dashboard"))

        return wrapper
    return decorator


# =============================================================================
# ROUTES - AUTHENTICATION
# =============================================================================
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        if not username or not password:
            flash("Please enter both username and password.", "warning")
            return render_template("login.html")
        
        conn = get_db()
        user = conn.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        
        if not user or not check_password_hash(user["password_hash"], password):
            if user:
                conn.execute("UPDATE users SET failed_attempts = failed_attempts + 1 WHERE id=?", (user["id"],))
                conn.commit()
                log_action(f"Failed login attempt for {username}")
            flash("Invalid username or password.", "danger")
            return render_template("login.html")
        
        if blocked(user):
            flash("Account temporarily blocked due to security reasons. Try again later.", "danger")
            return render_template("login.html", can_contact_admin=True, restricted_user=username)
        
        # Check for low trust score at login
        if (user["trust_score"] or 100) < 25:
            flash("Access Restricted: Your trust score is too low. Please contact admin.", "danger")
            return render_template("login.html", can_contact_admin=True, restricted_user=username)
        
        # Device fingerprint check (Limit of 2 per account)
        current_fp = get_device_fingerprint()
        security_alert = None
        
        devices = conn.execute("SELECT device_id FROM trusted_devices WHERE user_id=?", (user["id"],)).fetchall()
        device_ids = [d["device_id"] for d in devices]
        
        if current_fp in device_ids:
            # Update last seen
            conn.execute("UPDATE trusted_devices SET last_seen=?, seen_count=seen_count+1 WHERE user_id=? AND device_id=?", 
                         (datetime.utcnow().isoformat(), user["id"], current_fp))
            conn.commit()
        else:
            if len(device_ids) >= 2:
                flash("Login blocked: Maximum of 2 trusted devices reached. Please contact admin to reset.", "danger")
                return render_template("login.html")
            else:
                conn.execute("INSERT INTO trusted_devices (user_id, device_id, first_seen, last_seen) VALUES (?, ?, ?, ?)",
                             (user["id"], current_fp, datetime.utcnow().isoformat(), datetime.utcnow().isoformat()))
                
                # Add to device_fingerprints table too for forensic logs
                ip = get_real_ip() or "127.0.0.1"
                ua = request.headers.get("User-Agent", "")
                conn.execute("INSERT INTO device_fingerprints (user_id, user_agent, ip_address, first_seen) VALUES (?, ?, ?, ?)",
                             (user["id"], ua, ip, datetime.utcnow().isoformat()))
                
                if len(device_ids) > 0:
                    new_trust = max((user["trust_score"] or 100) - 10, 0)
                    conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user["id"]))
                    security_alert = "New device detected. Trust score reduced for security."
                    flash(security_alert, "trust_alert")
                
                conn.commit()
        
        # Store pre-auth session variables
        session["pre_auth_user_id"] = user["id"]
        session["pre_auth_role"] = user["role"]
        session["pre_auth_username"] = user["username"]
        if security_alert:
            session["pre_auth_security_alert"] = security_alert
        
        log_action(f"{username} initiated login, proceeding to TOTP")
        
        return redirect(url_for("verify_otp"))
    
    return render_template("login.html")

# ==============================================================================
# VPN TUNNEL MIDDLEWARE — RSA + AES Encrypted
# Every authenticated request is verified against the Zero Trust Policy Server.
# Traffic is encrypted: AES-256-CBC payload + RSA-2048-OAEP key exchange.
# ==============================================================================
import sys as _sys
_vpn_dir = os.path.join(os.path.dirname(__file__), "zero_trust_vpn")
if _vpn_dir not in _sys.path:
    _sys.path.insert(0, _vpn_dir)
from crypto_utils import encrypt_payload, load_public_key

VPN_HOST = "127.0.0.1"
VPN_PORT = 5012
VPN_TIMEOUT = 3.0

# Paths that bypass the VPN tunnel
VPN_PUBLIC_PATHS = ["/login", "/verify_totp", "/public-request-help", "/static"]

_VPN_PUBLIC_KEY_PATH = os.path.join(os.path.dirname(__file__), "zero_trust_vpn", "keys", "public.pem")
try:
    _VPN_PUBLIC_KEY = load_public_key(_VPN_PUBLIC_KEY_PATH)
    print(f"[VPN] RSA public key loaded from {_VPN_PUBLIC_KEY_PATH}")
except FileNotFoundError:
    _VPN_PUBLIC_KEY = None
    print(f"[VPN] WARNING: RSA public key not found. Run: python zero_trust_vpn/generate_keys.py")

@app.before_request
def vpn_tunnel():
    """VPN Tunnel: ALL authenticated requests pass through the encrypted Zero Trust channel."""
    path = request.path
    if any(path.startswith(p) for p in VPN_PUBLIC_PATHS) or path == "/":
        return

    jwt_token = session.get("jwt")
    if not jwt_token:
        return  # Not logged in — @login_required handles the redirect

    if _VPN_PUBLIC_KEY is None:
        flash("Security Error: VPN keys not generated. Run generate_keys.py.", "danger")
        return redirect(url_for("login"))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(VPN_TIMEOUT)
            s.connect((VPN_HOST, VPN_PORT))

            # Encrypt payload: RSA-protected AES session key + AES-encrypted JWT/path
            plaintext = json.dumps({"jwt": jwt_token, "path": path})
            wire_data = encrypt_payload(plaintext, _VPN_PUBLIC_KEY)
            s.sendall(wire_data)

            response = s.recv(4096).decode()

        if response.startswith("ALLOWED"):
            return  # Approved — proceed to route

        elif response == "TOKEN_INVALID":
            session.clear()
            flash("Your VPN session token is invalid. Please login again.", "danger")
            return redirect(url_for("login"))

        elif response == "SESSION_TERMINATED_LOW_TRUST":
            session.clear()
            flash("VPN Session Terminated: Trust Score critically low.", "danger")
            return redirect(url_for("login"))

        else:
            try:
                data = json.loads(response)
                if data.get("action") == "JWT_DOWNGRADED":
                    new_trust = data.get("trust", 0)
                    session["trust_score"] = new_trust
                    # Persist to DB so session and DB stay in sync
                    user_id = session.get("user_id")
                    if user_id:
                        conn = get_db()
                        conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
                        conn.commit()
                    flash("VPN Access Denied: Unauthorized resource. Trust score reduced.", "trust_alert")
                    return redirect(url_for("restricted"))
            except Exception:
                pass
            flash("VPN Access Denied.", "danger")
            return redirect(url_for("restricted"))

    except (ConnectionRefusedError, OSError) as e:
        print(f"[VPN CRITICAL] Policy server unreachable: {e}")
        flash("Security Error: VPN Policy Server is offline. Please contact admin.", "danger")
        return redirect(url_for("login"))

    except socket.timeout:
        print(f"[VPN CRITICAL] Policy server timed out for {path}")
        flash("Security Error: VPN Policy Server timed out. Please ensure it is running.", "danger")
        return redirect(url_for("login"))

@app.before_request
def enforce_zero_trust():
    if not session.get("user_id"):
        return

    # Sync session trust from DB (source of truth) for consistent display
    if session.get("user_id"):
        conn = get_db()
        user = conn.execute("SELECT trust_score FROM users WHERE id=?", (session["user_id"],)).fetchone()
        if user is not None:
            db_trust = user["trust_score"] if user["trust_score"] is not None else 100
            session["trust_score"] = db_trust
    trust = session.get("trust_score", 100)

    # Just mark restriction, don't redirect
    session["low_trust"] = trust < SENSITIVE_TRUST_THRESHOLD


@app.route("/self-service-verify")
@login_required
def self_service_verify():
    """Trigger OTP for self-service trust recovery"""
    user_id = session.get("user_id")
    conn = get_db()
    user = conn.execute("SELECT email, username FROM users WHERE id=?", (user_id,)).fetchone()
    
    # Generate OTP
    otp = f"{secrets.randbelow(1000000):06d}"
    session["recovery_otp"] = otp
    session["recovery_otp_expiry"] = (datetime.utcnow() + timedelta(minutes=5)).timestamp()
    
    send_otp_email(user["email"], otp)
    flash("Verification OTP sent to your registered email.", "info")
    log_action(f"SELF_SERVICE | {user['username']} initiated identity re-verification")
    
    return render_template("verify_recovery.html")

@app.route("/restricted")
@login_required
def restricted():
    return render_template("restricted.html")

@app.route("/request-admin-help", methods=["POST"])
@login_required
def request_admin_help():
    uid = session.get("user_id")
    username = session.get("username")
    conn = get_db()
    
    # Log the alert
    conn.execute("""
        INSERT INTO parent_grievances (parent_id, title, description, status)
        VALUES (?, ?, ?, ?)
    """, (uid, "Access Request (Low Trust)", f"User {username} (ID: {uid}) requested access review due to low trust score ({session.get('trust_score')})", "Pending"))
    conn.commit()
    
    log_action(f"SECURITY_ALERT | User {username} sent admin alert for low trust access restriction")
    flash("Admin has been notified. They will review your account soon.", "success")
    return redirect(url_for("restricted"))

@app.route("/public-request-help", methods=["POST"])
def public_request_help():
    username = request.form.get("username", "").strip()
    if not username:
        flash("Invalid request.", "danger")
        return redirect(url_for("login"))
        
    conn = get_db()
    user = conn.execute("SELECT id, trust_score FROM users WHERE username=?", (username,)).fetchone()
    
    if user:
        # Log the alert
        conn.execute("""
            INSERT INTO parent_grievances (parent_id, title, description, status)
            VALUES (?, ?, ?, ?)
        """, (user["id"], "Public Access Request (Blocked/Low Trust)", 
              f"User {username} (ID: {user['id']}) requested access review from login page. Current trust: {user['trust_score']}", "Pending"))
        conn.commit()
        
        log_action(f"SECURITY_ALERT | User {username} sent PUBLIC admin alert for access restriction")
        flash("Admin has been notified. They will review your account soon.", "success")
    else:
        flash("User not found.", "danger")
        
    return redirect(url_for("login"))

@app.route("/confirm-recovery", methods=["POST"])
@login_required
def confirm_recovery_otp():
    """Verify recovery OTP and grant trust boost"""
    code = request.form.get("otp", "").strip()
    otp = session.get("recovery_otp")
    expiry = session.get("recovery_otp_expiry", 0)
    
    if not otp or datetime.utcnow().timestamp() > expiry:
        flash("OTP expired or invalid. Please try again.", "danger")
        return redirect(url_for("dashboard"))
        
    if code == otp:
        user_id = session.get("user_id")
        username = session.get("username")
        conn = get_db()
        
        try:
            user = conn.execute("SELECT trust_score FROM users WHERE id=?", (user_id,)).fetchone()
            old_trust = user["trust_score"]
            new_trust = min(100, old_trust + 20)
            
            # Update DB
            conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
            
            # Log Hist
            conn.execute(
                "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                (user_id, old_trust, new_trust, "SELF_SERVICE_VERIFICATION - Completed identity re-check")
            )
            conn.commit()
            
            # Update session
            session["trust_score"] = new_trust
            session.pop("recovery_otp", None)
            
            log_action(f"TRUST_RECOVERED | User: {username} | Type: SELF_SERVICE_VERIFICATION | {old_trust} -> {new_trust}")
            flash(f"✅ Identity verified! Your trust score has been boosted to {new_trust}.", "success")
        except Exception as e:
            flash("Error processing trust boost.", "danger")
            print(f"[ERROR] Self-service boost failed: {e}")
            
        return redirect(url_for("dashboard"))
    else:
        flash("Invalid OTP code.", "danger")
        return render_template("verify_recovery.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp():
    if "pre_auth_user_id" not in session:
        return redirect(url_for("login"))

    user_id = session["pre_auth_user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()

    # --- Get or generate TOTP secret ---
    totp_secret = None
    try:
        totp_secret = user["totp_secret"]
    except (IndexError, KeyError):
        pass

    if not totp_secret:
        totp_secret = pyotp.random_base32()
        try:
            conn.execute("UPDATE users SET totp_secret=? WHERE id=?", (totp_secret, user_id))
            conn.commit()
        except Exception as e:
            print(f"[ERROR] Could not save TOTP secret: {e}")

    # --- Generate QR code for the template ---
    totp = pyotp.TOTP(totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user["email"], issuer_name="ZeroTrust Portal")
    qr = qrcode.QRCode(version=1, box_size=8, border=3)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buf = io.BytesIO()
    img.save(buf)
    qr_b64 = base64.b64encode(buf.getvalue()).decode("ascii")

    if request.method == "POST":
        code = request.form.get("otp", "").strip()

        # ✅ TOTP SUCCESS
        if totp.verify(code):
            # 1. Detect Anomalies and Calculate Trust
            current_ip = get_real_ip() or "127.0.0.1"
            username = session.get("pre_auth_username")
            anomalies = detect_anomalies(user_id, current_ip)
            
            # Base trust: Give +5 for successful login
            current_trust = user["trust_score"] or 100
            new_trust = min(100, current_trust + 5)
            
            penalty = 0
            for anomaly in anomalies:
                penalty += anomaly["penalty"]
                log_action(f"ANOMALY_DETECTED | User: {username} | Type: {anomaly['type']} | {anomaly['msg']}")
                flash(f"⚠ Security Alert: {anomaly['msg']} (Trust -{anomaly['penalty']})", "trust_alert")
            
            new_trust = max(0, new_trust - penalty)
            
            # 2. Update Basic Security Records
            now = datetime.utcnow().isoformat()
            device_fp = get_device_fingerprint()

            conn.execute("""
                UPDATE users SET
                    trust_score=?,
                    otp_failures=0,
                    blocked_until=NULL,
                    active_session=1,
                    device_fp=?
                WHERE id=?
            """, (new_trust, device_fp, user_id))
            conn.commit()

            # 3. Record Login Pattern for Future Detection
            record_login_event(user_id, current_ip)

            # ⚠️ SAVE ROLE AND ALERTS BEFORE CLEAR
            role = session.get("pre_auth_role")
            security_alert = session.get("pre_auth_security_alert")
            
            session.clear()
            # Generate JWT
            jwt_payload = {
                "sub": username,
                "role": role,
                "exp": datetime.utcnow() + timedelta(hours=2)
            }
            token = jwt.encode(jwt_payload, JWT_SECRET, algorithm="HS256")

            session.update({
                "user_id": user_id,
                "role": role,
                "username": username,
                "trust_score": new_trust,
                "login_time": now,
                "last_activity": now,
                "jwt": token
            })

            if security_alert:
                flash(security_alert, "trust_alert")

            flash("Login successful!", "success")
            from flask import make_response
            resp = make_response(redirect(url_for("dashboard")))
            # Ensure the device fingerprint cookie is set so the device is consistently remembered
            if request.cookies.get("trusted_device") != device_fp:
                resp.set_cookie("trusted_device", device_fp, max_age=31536000, httponly=True, secure=True)
            return resp

        # ❌ OTP FAILURE
        conn.execute(
            "UPDATE users SET otp_failures = otp_failures + 1, trust_score = trust_score - 10 WHERE id=?",
            (user_id,)
        )
        flash("Invalid OTP. Trust score reduced.", "trust_alert")
        conn.commit()

        user = conn.execute(
            "SELECT trust_score, otp_failures FROM users WHERE id=?",
            (user_id,)
        ).fetchone()

        if user["trust_score"] <= 0 or user["otp_failures"] >= 5:
            block_until = datetime.utcnow() + timedelta(minutes=BLOCK_DURATION_MINUTES)
            conn.execute(
                "UPDATE users SET blocked_until=? WHERE id=?",
                (block_until.isoformat(), user_id)
            )
            conn.commit()

            flash("Account blocked due to multiple OTP failures.", "danger")
            session.clear()
            return redirect(url_for("login"))


    return render_template("verify_otp.html", qr_b64=qr_b64, secret=totp_secret)

@app.route("/enroll_totp")
@login_required
def enroll_totp():
    """Generates a base32 secret and QR code for Google Auth enrollment."""
    user_id = session.get("user_id")
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    
    if not user:
        return redirect(url_for("login"))
        
    # Get or generate secret
    totp_secret = None
    try:
        totp_secret = user["totp_secret"]
    except IndexError:
        pass
        
    if not totp_secret:
        # Generate new secret if they don't have one
        totp_secret = pyotp.random_base32()
        try:
            conn.execute("UPDATE users SET totp_secret=? WHERE id=?", (totp_secret, user_id))
            conn.commit()
            log_action(f"Generated new TOTP secret for {user['username']}")
        except Exception as e:
            print(f"[ERROR] Could not save TOTP secret: {e}")
            flash("Failed to generate MFA token. Please contact logic administrator.", "danger")
            return redirect(url_for("dashboard"))

    # Generate Provisioning URI
    totp = pyotp.TOTP(totp_secret)
    provisioning_uri = totp.provisioning_uri(name=user["email"], issuer_name="ZeroTrust Portal")

    # Generate QR Code Graphic
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(provisioning_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save Image to purely active memory Buffer
    buf = io.BytesIO()
    img.save(buf)
    image_base64 = base64.b64encode(buf.getvalue()).decode("ascii")
    
    return render_template("enroll_totp.html", secret=totp_secret, qr_b64=image_base64)

@app.route('/logout')
def logout():
    uid = session.get("user_id")
    username = session.get("username")
    reason = session.get("logout_reason")
    conn = get_db()
    if uid:
        conn.execute("UPDATE users SET active_session=0 WHERE id=?", (uid,))
        login_time = session.get("login_time")
        if login_time:
            try:
                duration = (datetime.utcnow() - datetime.fromisoformat(login_time)).seconds
                write_access_log(conn, uid, "logout", "user", None, True, f"session_{duration}s")
            except:
                write_access_log(conn, uid, "logout", "user", None, True, "logout")
        conn.commit()
        log_action(f"User {session.get('username')} logged out")
    elif username:
        conn.execute("UPDATE users SET active_session=0 WHERE username=?", (username,))
    
    session.clear()
    if reason:
        flash(reason, "logout_reason")
    else:
        flash("Logged out successfully.", "info")
    return redirect(url_for("login"))

# =============================================================================
# ROUTES - DASHBOARD
# =============================================================================
@app.route('/dashboard')
@login_required
def dashboard():
    uid = session["user_id"]
    role = session["role"]
    conn = get_db()

    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    trust = user["trust_score"] if user else 0

    track_behavior("view_dashboard")

    context = {
        "user": user,
        "trust": trust,
        "role": role,
        "security_alert": session.pop("security_alert", None)
    }

    # Role-specific data
    if role == "student":
        context["student"] = conn.execute(
            "SELECT * FROM students WHERE user_id=?", (uid,)
        ).fetchone()

    elif role == "parent":
        parent = conn.execute(
            "SELECT * FROM parents WHERE user_id=?", (uid,)
        ).fetchone()
        context["parent"] = parent

    elif role == "faculty":
        faculty = conn.execute(
            "SELECT * FROM faculty WHERE user_id=?", (uid,)
        ).fetchone()
        context["faculty"] = faculty
        if faculty:
            # Count assigned classes
            context["assigned_count"] = conn.execute(
                "SELECT COUNT(*) FROM classes WHERE faculty_id=?", (faculty["id"],)
            ).fetchone()[0]

    write_access_log(conn, uid, "view_dashboard", "dashboard", None, True, "ok")

    return render_template(f"{role}/dashboard.html", **context)

# =============================================================================
# ROUTES - STUDENT PORTAL
# =============================================================================
@app.route('/student/marks')
@login_required
@role_required(['student'])


def student_marks():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view marks.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    
    if not student:
        flash("Student record not found.", "warning")
        return redirect(url_for("dashboard"))

    # Fetch detailed marks from the 'marks' table
    detailed_marks = conn.execute("""
        SELECT m.*, COALESCE(u.name, 'N/A') as faculty_name 
        FROM marks m 
        LEFT JOIN users u ON m.entered_by = u.id
        WHERE m.student_id=? 
        ORDER BY m.entered_at DESC
    """, (student["id"],)).fetchall()
    
    # Calculate semester-wise SGPA (Simplified logic for now)
    semesters = {}
    for mark in detailed_marks:
        sem = student['semester'] # Current semester or we could add semester to marks table
        if sem not in semesters:
            semesters[sem] = {"subjects": [], "sgpa": 0}
        semesters[sem]["subjects"].append(mark)
    
    track_behavior("view_marks")
    write_access_log(conn, uid, "view_marks", "student", student["id"], True, "ok")
    return render_template("student/marks.html", student=student, detailed_marks=detailed_marks, semesters=semesters)

@app.route('/student/attendance')
@login_required
@role_required(['student'])
def student_attendance():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view attendance.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    
    if not student:
        flash("Student record not found.", "warning")
        return redirect(url_for("dashboard"))

    attendance_records = conn.execute("""
        SELECT a.*, u.name as faculty_name 
        FROM attendance a 
        JOIN users u ON a.marked_by = u.id
        WHERE a.student_id=? 
        ORDER BY a.date DESC LIMIT 30
    """, (student["id"],)).fetchall()
    
    # Calculate stats
    total = len(attendance_records)
    present = sum(1 for r in attendance_records if r['status'] == 'present')
    absent = sum(1 for r in attendance_records if r['status'] == 'absent')
    percentage = (present / total * 100) if total > 0 else 0
    
    track_behavior("view_attendance")
    write_access_log(conn, uid, "view_attendance", "student", student["id"], True, "ok")
    return render_template("student/attendance.html", 
                           student=student, 
                           records=attendance_records,
                           stats={'total': total, 'present': present, 'absent': absent, 'percentage': round(percentage, 1)})

@app.route('/student/fees')
@login_required
@role_required(['student'])
def student_fees():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view fees.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    
    if not student:
        flash("Student record not found.", "warning")
        return redirect(url_for("dashboard"))

    payments = conn.execute("""SELECT * FROM fee_payments WHERE student_id=? ORDER BY payment_date DESC""",
                           (student["id"],)).fetchall()
    
    # Calculate summary
    total_fees = 150000  # Default or pull from a settings table if available
    fees_paid = student['fees_paid'] or 0
    fees_due = total_fees - fees_paid
    
    # Static due date for demo or logic based on semester
    next_due = "Jan 15" if fees_due > 0 else "N/A"
    
    track_behavior("view_fees")
    write_access_log(conn, uid, "view_fees", "student", student["id"], True, "ok")
    return render_template("student/fees.html", 
                           student=student, 
                           payments=payments, 
                           total_fees=total_fees,
                           fees_paid=fees_paid,
                           fees_due=fees_due,
                           next_due=next_due)

@app.route('/student/pay_fees', methods=['POST'])
@login_required
@role_required(['student'])
def pay_fees():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to make payments.", "warning")
        return redirect(url_for("restricted"))
        
    uid = session["user_id"]
    try:
        amount = float(request.form.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
        
    payment_method = request.form.get("payment_method", "").strip()
    totp_code = request.form.get("totp_code", "").strip()
    
    if amount <= 0 or not payment_method or not totp_code:
        flash("Invalid payment details or missing TOTP code.", "danger")
        return redirect(url_for("student_fees"))
        
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    
    if not student or not user:
        flash("Record not found.", "danger")
        return redirect(url_for("dashboard"))
        
    # Verify TOTP code
    totp_secret = user["totp_secret"] if "totp_secret" in dict(user).keys() else None
    
    if not totp_secret:
        flash("TOTP not enrolled. Please contact admin.", "danger")
        return redirect(url_for("student_fees"))

    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(totp_code):
        reduce_trust("invalid_totp_payment", 10)
        flash("Invalid TOTP code. Trust score reduced.", "trust_alert")
        log_action(f"PAYMENT_FAILED | User: {user['username']} | Invalid TOTP for payment of ₹{amount}")
        return redirect(url_for("student_fees"))

    # Update DB for successful payment
    import uuid
    transaction_id = "TXN" + str(uuid.uuid4().hex[:10]).upper()
    now = datetime.utcnow().isoformat()
    
    # Track the new values
    new_paid = (student['fees_paid'] or 0) + amount
    # Instead of re-calculating due statically from 150000, rely on the column if it's there
    new_due = (student['fees_due'] or 0) - amount
    if new_due < 0: new_due = 0
    
    conn.execute("""
        INSERT INTO fee_payments (student_id, amount, payment_date, payment_method, transaction_id)
        VALUES (?, ?, ?, ?, ?)
    """, (student["id"], amount, now, payment_method, transaction_id))
    
    conn.execute("""
        UPDATE students SET fees_paid=?, fees_due=? WHERE id=?
    """, (new_paid, new_due, student["id"]))
    
    conn.commit()
    
    write_access_log(conn, uid, "pay_fees", "student", student["id"], True, f"paid_{amount}")
    log_action(f"PAYMENT_SUCCESS | User {uid} paid ₹{amount} via {payment_method}. TXN: {transaction_id}")
    flash(f"Payment of ₹{amount} successful! Transaction ID: {transaction_id}", "success")
    
    return redirect(url_for("student_fees"))

@app.route('/student/receipt/<txn_id>')
@login_required
@role_required(['student'])
def download_receipt(txn_id):
    uid = session["user_id"]
    conn = get_db()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    if not student:
        flash("Record not found.", "danger")
        return redirect(url_for("dashboard"))
        
    payment = conn.execute("SELECT * FROM fee_payments WHERE transaction_id=? AND student_id=?", (txn_id, student["id"])).fetchone()
    
    if not payment:
        flash("Transaction not found.", "danger")
        return redirect(url_for("student_fees"))
        
    return render_template("student/receipt.html", payment=payment, student=student)

@app.route('/student/notices')
@login_required
@role_required(['student'])
def student_notices():
    conn = get_db()
    notices = conn.execute("""
        SELECT a.*, u.name AS posted_by_name
        FROM announcements a
        LEFT JOIN users u ON a.posted_by = u.id
        WHERE a.target_role IN ('all', 'student')
        ORDER BY a.created_at DESC
        LIMIT 20
    """).fetchall()

    track_behavior("view_notices")
    write_access_log(conn, session["user_id"], "view_notices", "student", None, True, "ok")
    return render_template("student/notices.html", notices=notices)

@app.route('/student/grievance', methods=['GET', 'POST'])
@login_required
@role_required(['student'])
def student_grievance():
    uid = session["user_id"]
    conn = get_db()

    if request.method == "POST":
        subject = request.form.get("subject", "").strip()
        description = request.form.get("description", "").strip()

        if subject and description:
            conn.execute("""
                INSERT INTO grievances (student_id, subject, description)
                VALUES (?, ?, ?)
            """, (uid, subject, description))
            conn.commit()

            flash("Grievance submitted successfully!", "success")
        else:
            flash("Please fill all fields.", "warning")

    grievances = conn.execute("""
        SELECT id, subject, description, status, submitted_at
        FROM grievances
        WHERE student_id = ?
        ORDER BY submitted_at DESC
    """, (uid,)).fetchall()

    return render_template(
        "student/grievance.html",
        grievances=grievances
    )

@app.route('/student/profile')
@login_required
@role_required(['student'])
def student_profile():
    uid = session["user_id"]
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
    student = conn.execute("SELECT * FROM students WHERE user_id=?", (uid,)).fetchone()
    
    pending_requests = conn.execute("""SELECT * FROM profile_change_requests 
                                      WHERE student_id=? AND status='pending' ORDER BY requested_at DESC""", (uid,)).fetchall()
    
    track_behavior("view_profile")
    return render_template("student/profile.html", user=user, student=student, pending_requests=pending_requests)



# =============================================================================
# ROUTES - PARENT PORTAL
# =============================================================================

@app.route('/parent/grievances')
@login_required
@role_required(['parent'])
def parent_grievances():
    uid = session["user_id"]
    conn = get_db()

    # Fetch grievances submitted by this parent
    grievances = conn.execute("""
        SELECT g.id, g.title, g.description, g.status, g.submitted_at
        FROM parent_grievances g
        WHERE g.parent_id = ?
        ORDER BY g.submitted_at DESC
    """, (uid,)).fetchall()

    return render_template(
        "parent/grievances.html",
        grievances=grievances
    )

@app.route('/parent/grievances/submit', methods=['POST'])
@login_required
@role_required(['parent'])
def submit_parent_grievance():
    uid = session["user_id"]
    title = request.form.get("title")
    description = request.form.get("description")
    conn = get_db()

    if title and description:
        conn.execute("""
            INSERT INTO parent_grievances (parent_id, title, description, status, submitted_at)
            VALUES (?, ?, ?, 'Pending', CURRENT_TIMESTAMP)
        """, (uid, title, description))
        conn.commit()
        flash("Grievance submitted successfully!", "success")

    return redirect(url_for("parent_grievances"))


@app.route('/parent/marks')
@login_required
@role_required(['parent'])
def parent_marks():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view your child's marks.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    parent = conn.execute("SELECT * FROM parents WHERE user_id=?", (uid,)).fetchone()
    
    if not parent:
        flash("No linked student found.", "warning")
        return redirect(url_for("dashboard"))
    
    student = conn.execute("SELECT s.*, u.name as student_name FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=?",
                          (parent["student_id"],)).fetchone()
    
    detailed_marks = conn.execute("""
        SELECT m.*, u.name as faculty_name
        FROM marks m
        LEFT JOIN users u ON m.entered_by = u.id
        WHERE m.student_id=?
        ORDER BY m.entered_at DESC
    """, (student["id"] if student else 0,)).fetchall()

    track_behavior("parent_view_marks")
    write_access_log(conn, uid, "parent_view_marks", "student", student["id"] if student else None, True, "ok")
    return render_template("parent/marks.html", detailed_marks=detailed_marks, student=student)

@app.route('/parent/attendance')
@login_required
@role_required(['parent'])
def parent_attendance():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view your child's attendance.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    parent = conn.execute("SELECT * FROM parents WHERE user_id=?", (uid,)).fetchone()
    
    if not parent:
        flash("No linked student found.", "warning")
        return redirect(url_for("dashboard"))
    
    student = conn.execute("SELECT s.*, u.name as student_name FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=?",
                          (parent["student_id"],)).fetchone()

    attendance_records = conn.execute("""
        SELECT a.*, u.name as faculty_name
        FROM attendance a
        LEFT JOIN users u ON a.marked_by = u.id
        WHERE a.student_id=?
        ORDER BY a.date DESC LIMIT 30
    """, (student["id"] if student else 0,)).fetchall()

    total = len(attendance_records)
    present = sum(1 for r in attendance_records if r['status'] == 'present')
    absent = sum(1 for r in attendance_records if r['status'] == 'absent')
    percentage = round(present / total * 100, 1) if total > 0 else 0

    track_behavior("parent_view_attendance")
    write_access_log(conn, uid, "parent_view_attendance", "student", student["id"] if student else None, True, "ok")
    return render_template("parent/attendance.html",
                           records=attendance_records,
                           stats={'total': total, 'present': present, 'absent': absent, 'percentage': percentage},
                           student=student)

@app.route('/parent/fees')
@login_required
@role_required(['parent'])
def parent_fees():
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to view fee details.", "warning")
        return redirect(url_for("restricted"))
    uid = session["user_id"]
    conn = get_db()
    parent = conn.execute("SELECT * FROM parents WHERE user_id=?", (uid,)).fetchone()
    
    if not parent or not parent['student_id']:
        flash("No linked student found.", "warning")
        return redirect(url_for("dashboard"))
    
    student = conn.execute("SELECT s.*, u.name as student_name FROM students s JOIN users u ON s.user_id=u.id WHERE s.id=?",
                          (parent["student_id"],)).fetchone()
    
    if not student:
        flash("Student record not found.", "warning")
        return redirect(url_for("dashboard"))

    payments = conn.execute("""SELECT * FROM fee_payments WHERE student_id=? ORDER BY payment_date DESC""",
                           (student["id"],)).fetchall()
    
    # Calculate summary
    total_fees = 150000 
    fees_paid = student['fees_paid'] or 0
    fees_due = total_fees - fees_paid
    next_due = "Jan 15" if fees_due > 0 else "N/A"
    
    track_behavior("parent_view_fees")
    write_access_log(conn, uid, "parent_view_fees", "student", student["id"], True, "ok")
    return render_template("parent/fees.html", 
                           student=student, 
                           payments=payments,
                           total_fees=total_fees,
                           fees_paid=fees_paid,
                           fees_due=fees_due,
                           next_due=next_due)

@app.route('/parent/notices')
@login_required
@role_required(['parent'])
def parent_notices():
    conn = get_db()
    notices = conn.execute("""
        SELECT a.*, u.name AS posted_by_name
        FROM announcements a
        LEFT JOIN users u ON a.posted_by = u.id
        WHERE a.target_role IN ('all', 'parent')
        ORDER BY a.created_at DESC
        LIMIT 20
    """).fetchall()

    track_behavior("parent_view_notices")
    write_access_log(conn, session["user_id"], "parent_view_notices", "parent", None, True, "ok")
    return render_template("parent/notices.html", notices=notices)

# =============================================================================
# ROUTES - FACULTY PORTAL
# =============================================================================

# Class Management placeholder
@app.route('/faculty/class_management')
@login_required
@role_required(['faculty', 'admin'])
def class_management():
    return render_template('faculty/class_management.html')

# Student List placeholder
@app.route('/faculty/student_list')
@login_required
@role_required(['faculty', 'admin'])
def student_list():
    conn = get_db()
    uid = session["user_id"]
    faculty = conn.execute("SELECT id FROM faculty WHERE user_id=?", (uid,)).fetchone()
    
    assigned_classes = []
    if faculty:
        assigned_classes = conn.execute("SELECT * FROM classes WHERE faculty_id=?", (faculty["id"],)).fetchall()
        
    class_id = request.args.get("class_id")
    selected_class = None
    students = []
    
    if class_id:
        selected_class = conn.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
        students = conn.execute("""
            SELECT s.id, s.roll, u.name as student_name, s.department, s.semester 
            FROM students s 
            JOIN users u ON s.user_id = u.id
            JOIN class_enrollments ce ON s.id = ce.student_id
            WHERE ce.class_id = ?
        """, (class_id,)).fetchall()
        
    return render_template('faculty/student_list.html', 
                           assigned_classes=assigned_classes, 
                           selected_class=selected_class, 
                           students=students)


@app.route('/faculty/marks', methods=['GET', 'POST'])
@login_required
@role_required(['faculty', 'admin'], readonly_for_admin=True)
def faculty_marks(readonly=False):
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to access marks entry.", "warning")
        return redirect(url_for("restricted"))
    if READ_ONLY_MODE:
        flash("System is in Read-Only Mode. Changes are not allowed.", "warning")
        return redirect(url_for("dashboard"))

    uid = session["user_id"]
    conn = get_db()
    faculty = conn.execute("SELECT id FROM faculty WHERE user_id=?", (uid,)).fetchone()
    
    assigned_classes = []
    if faculty:
        assigned_classes = conn.execute("SELECT * FROM classes WHERE faculty_id=?", (faculty["id"],)).fetchall()

    class_id = request.args.get("class_id") or request.form.get("class_id")
    selected_class = None
    students = []
    
    if class_id:
        selected_class = conn.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
        students = conn.execute("""
            SELECT s.id, s.roll, u.name as student_name
            FROM students s
            JOIN users u ON s.user_id = u.id
            JOIN class_enrollments ce ON s.id = ce.student_id
            WHERE ce.class_id = ?
        """, (class_id,)).fetchall()

    if request.method == "POST" and not readonly and selected_class:
        exam_type = request.form.get("exam_type", "Internal")
        max_marks = request.form.get("max_marks", 100)
        
        for student in students:
            marks = request.form.get(f"marks_{student['id']}")
            if marks:
                conn.execute("""
                    INSERT INTO marks (student_id, subject, marks_obtained, max_marks, exam_type, entered_by)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (student["id"], selected_class["name"], marks, max_marks, exam_type, uid))
        
        conn.commit()
        flash(f"Marks for {selected_class['name']} submitted successfully!", "success")
        return redirect(url_for("faculty_marks", class_id=class_id))

    return render_template(
        "faculty/marks.html",
        assigned_classes=assigned_classes,
        selected_class=selected_class,
        students=students,
        readonly=readonly
    )

@app.route('/faculty/attendance', methods=['GET', 'POST'])
@login_required
@role_required(['faculty', 'admin'], readonly_for_admin=True)
def faculty_attendance(readonly=False):
    if not trust_allows_sensitive():
        flash("Trust score must be at least 60 to access attendance entry.", "warning")
        return redirect(url_for("restricted"))
    if READ_ONLY_MODE:
        flash("System is in Read-Only Mode. Changes are not allowed.", "warning")
        return redirect(url_for("dashboard"))

    uid = session["user_id"]
    conn = get_db()
    faculty = conn.execute("SELECT id FROM faculty WHERE user_id=?", (uid,)).fetchone()
    
    assigned_classes = []
    if faculty:
        assigned_classes = conn.execute("SELECT * FROM classes WHERE faculty_id=?", (faculty["id"],)).fetchall()

    class_id = request.args.get("class_id") or request.form.get("class_id")
    selected_class = None
    students = []
    
    if class_id:
        selected_class = conn.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
        students = conn.execute("""
            SELECT s.id, s.roll, u.name as student_name
            FROM students s
            JOIN users u ON s.user_id = u.id
            JOIN class_enrollments ce ON s.id = ce.student_id
            WHERE ce.class_id = ?
        """, (class_id,)).fetchall()

    today = datetime.now().strftime("%Y-%m-%d")

    if request.method == "POST" and not readonly and selected_class:
        date = request.form.get("date", today)
        for student in students:
            status = request.form.get(f"status_{student['id']}")
            if status:
                conn.execute("""
                    INSERT INTO attendance (student_id, date, status, subject, marked_by, faculty_id, class_id)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (student["id"], date, status, selected_class["name"], uid, faculty["id"], class_id))
        
        conn.commit()
        flash(f"Attendance for {selected_class['name']} submitted successfully!", "success")
        return redirect(url_for("faculty_attendance", class_id=class_id))
    
    return render_template("faculty/attendance.html", 
                           assigned_classes=assigned_classes,
                           selected_class=selected_class,
                           students=students,
                           today=today, 
                           readonly=readonly)

@app.route('/faculty/announcements', methods=['GET', 'POST'])
@login_required
@role_required(['faculty', 'admin'], readonly_for_admin=True)
def faculty_announcements(readonly=False):
    uid = session["user_id"]
    conn = get_db()
    
    track_behavior("faculty_announcements")
    
    if is_behavior_unusual():
        flash("Unusual behavior detected. Some actions are temporarily restricted.", "warning")
        readonly = True
    
    if READ_ONLY_MODE:
        readonly = True
    
    if request.method == "POST" and not readonly:
        title = request.form.get("title")
        message = request.form.get("message")
        target = request.form.get("target", "all")
        
        if title and message:
            conn.execute("INSERT INTO announcements (title, message, posted_by, target_role) VALUES (?, ?, ?, ?)",
                        (title, message, uid, target))
            conn.commit()
            write_access_log(conn, uid, "post_announcement", "announcement", None, True, "ok")
            log_action(f"Announcement posted by faculty {uid}")
            flash("Announcement posted successfully!", "success")
            return redirect(url_for("faculty_announcements"))
    
    announcements = conn.execute("""SELECT a.*, u.name as posted_by_name FROM announcements a 
                                   LEFT JOIN users u ON a.posted_by=u.id 
                                   ORDER BY created_at DESC LIMIT 20""").fetchall()
    
    return render_template("faculty/announcements.html", announcements=announcements, 
                          readonly=readonly, trust_score=session.get("trust_score", 100))

@app.route('/faculty/my_classes')
@login_required
@role_required(['faculty'])
def faculty_my_classes():
    conn = get_db()
    uid = session["user_id"]
    faculty = conn.execute("SELECT id FROM faculty WHERE user_id=?", (uid,)).fetchone()
    assigned_classes = []
    if faculty:
        assigned_classes = conn.execute("SELECT * FROM classes WHERE faculty_id=?", (faculty["id"],)).fetchall()
    return render_template("faculty/my_classes.html", assigned_classes=assigned_classes)

# =============================================================================
# ROUTES - ADMIN PORTAL
# =============================================================================
@app.route('/admin/users')
@login_required
@role_required(['admin'])
def admin_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users ORDER BY role, name").fetchall()
    
    track_behavior("admin_users")
    write_access_log(conn, session["user_id"], "view_users", "admin", None, True, "ok")
    
    return render_template("admin/users.html", users=users, trust_score=session.get("trust_score", 100))

@app.route('/admin/users/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def admin_add_user():
    conn = get_db()
    
    if request.method == "POST":
        username    = request.form.get("username", "").strip()
        password    = request.form.get("password", "").strip()
        role        = request.form.get("role")
        email       = request.form.get("email", "").strip()
        name        = request.form.get("name", "").strip()
        phone       = request.form.get("phone", "").strip()

        # Student-specific
        department  = request.form.get("department", "Computer Science")
        semester    = request.form.get("semester", 1)
        batch_year  = request.form.get("batch_year", datetime.now().year)

        # Parent-specific: link via student email
        student_email = request.form.get("student_email", "").strip()
        student_id    = request.form.get("student_id", "").strip()

        if not all([username, password, role, email, name]):
            flash("Please fill all required fields.", "warning")
            return redirect(url_for("admin_add_user"))

        # Validate parent must have a linked student
        if role == "parent" and not student_id:
            # Try to resolve from email if JS didn't fill hidden field
            student_user = conn.execute("SELECT id FROM users WHERE email=? AND role='student'", (student_email,)).fetchone()
            if student_user:
                student_rec = conn.execute("SELECT id FROM students WHERE user_id=?", (student_user["id"],)).fetchone()
                student_id = student_rec["id"] if student_rec else None
            if not student_id:
                flash("Could not find a student with that email address.", "danger")
                return redirect(url_for("admin_add_user"))

        existing = conn.execute("SELECT id FROM users WHERE username=?", (username,)).fetchone()
        if existing:
            flash("Username already exists.", "danger")
            return redirect(url_for("admin_add_user"))

        password_hash = generate_password_hash(password)
        conn.execute(
            "INSERT INTO users (username, password_hash, role, email, name, phone) VALUES (?, ?, ?, ?, ?, ?)",
            (username, password_hash, role, email, name, phone)
        )
        conn.commit()

        user_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Role-specific records
        if role == "student":
            # Auto-generate roll: YEAR-DEPTCODE-USERID (e.g. 2024-CS-0042)
            dept_codes = {
                "Computer Science": "CS", "Information Technology": "IT",
                "Electronics": "EC",      "Mechanical": "ME",
                "Civil": "CV",            "Electrical": "EE"
            }
            code = dept_codes.get(department, department[:2].upper())
            roll = f"{batch_year}-{code}-{str(user_id).zfill(4)}"
            conn.execute(
                "INSERT INTO students (user_id, roll, department, semester) VALUES (?, ?, ?, ?)",
                (user_id, roll, department, semester)
            )

        elif role == "faculty":
            emp_id = f"FAC{str(user_id).zfill(4)}"
            conn.execute("INSERT INTO faculty (user_id, employee_id) VALUES (?, ?)", (user_id, emp_id))

        elif role == "parent":
            conn.execute("INSERT INTO parents (user_id, student_id) VALUES (?, ?)", (user_id, student_id))

        conn.commit()

        write_access_log(conn, session["user_id"], "add_user", "admin", None, True, f"added_{username}")
        log_action(f"Admin added {role} user: {username} (Roll: {roll if role == 'student' else 'N/A'})")
        flash(f"User '{username}' created successfully!", "success")
        return redirect(url_for("admin_users"))

    # GET: fetch students with their emails for the parent email-lookup map
    students = conn.execute("""
        SELECT s.id AS student_id, u.name, u.email
        FROM students s
        JOIN users u ON s.user_id = u.id
    """).fetchall()
    return render_template("admin/add_user.html", students=students, trust_score=session.get("trust_score", 100))

@app.route('/admin/users/delete/<int:user_id>')
@login_required
@role_required(['admin'])
def admin_delete_user(user_id):
    if user_id == session.get("user_id"):
        flash("You cannot delete your own account.", "danger")
        return redirect(url_for("admin_users"))
        
    conn = get_db()
    user = conn.execute("SELECT username FROM users WHERE id=?", (user_id,)).fetchone()
    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("admin_users"))
        
    conn.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    
    log_action(f"Admin deleted user {user['username']}")
    flash(f"User {user['username']} deleted successfully.", "success")
    return redirect(url_for("admin_users"))

@app.route('/admin/change_requests')
@login_required
@role_required(['admin'])
def admin_change_requests():
    conn = get_db()
    requests = conn.execute("""
    SELECT pcr.*, u.name as student_name, u.username 
    FROM profile_change_requests pcr 
    JOIN users u ON pcr.student_id=u.id 
    WHERE pcr.status = 'pending'
    ORDER BY pcr.requested_at DESC
""").fetchall()

    track_behavior("admin_change_requests")
    return render_template("admin/change_requests.html", requests=requests, trust_score=session.get("trust_score", 100))

@app.route('/admin/change_requests/<int:request_id>/<action>')
@login_required
@role_required(['admin'])
def admin_handle_request(request_id, action):
    if action not in ['approve', 'reject']:
        flash("Invalid action.", "danger")
        return redirect(url_for("admin_change_requests"))
    
    conn = get_db()
    req = conn.execute("SELECT * FROM profile_change_requests WHERE id=?", (request_id,)).fetchone()
    
    if not req:
        flash("Request not found.", "danger")
        return redirect(url_for("admin_change_requests"))
    
    if action == 'approve':
        # Apply the change
        field = req["field_name"]
        new_value = req["new_value"]
        student_id = req["student_id"]
        
        if field in ['email', 'phone', 'name']:
            conn.execute(f"UPDATE users SET {field}=? WHERE id=?", (new_value, student_id))
            
            # If email changed, clear TOTP secret so user must re-enroll with new email
            if field == 'email':
                conn.execute("UPDATE users SET totp_secret=NULL WHERE id=?", (student_id,))
                log_action(f"TOTP_RESET | User ID {student_id} email changed — TOTP secret cleared")
        
        conn.execute("UPDATE profile_change_requests SET status='approved', reviewed_by=?, reviewed_at=? WHERE id=?",
                    (session["user_id"], datetime.utcnow().isoformat(), request_id))
        conn.commit()
        flash("Request approved and changes applied.", "success")
    else:
        conn.execute("UPDATE profile_change_requests SET status='rejected', reviewed_by=?, reviewed_at=? WHERE id=?",
                    (session["user_id"], datetime.utcnow().isoformat(), request_id))
        conn.commit()
        flash("Request rejected.", "info")
    
    write_access_log(conn, session["user_id"], f"change_request_{action}", "admin", request_id, True, "ok")
    return redirect(url_for("admin_change_requests"))

@app.route('/admin/logs')
@login_required
@role_required(['admin'])
def admin_logs():
    log_type = request.args.get('type', 'session')
    
    if log_type == 'database':
        conn = get_db()
        # Fetch with role and trust score for better UI
        rows = conn.execute("""SELECT al.*, u.username, u.role, u.trust_score 
                               FROM access_logs al 
                               LEFT JOIN users u ON al.user_id=u.id 
                               ORDER BY al.timestamp DESC LIMIT 200""").fetchall()
        
        # Convert rows to dicts and normalize 'decision' from 'allowed'
        logs = []
        for r in rows:
            entry = dict(r)
            entry['decision'] = 'ALLOW' if entry['allowed'] else 'DENY'
            
            # Format timestamp properly
            try:
                if entry.get('timestamp'):
                    dt = datetime.fromisoformat(str(entry['timestamp']).replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    entry['timestamp'] = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
                
            logs.append(entry)
            
        return render_template("admin/logs.html", logs=logs, type='database', trust_score=session.get("trust_score", 100))
    elif log_type == 'security':
        conn = get_db()
        rows = conn.execute("""
            SELECT th.*, u.username, u.role, u.trust_score 
            FROM trust_history th 
            LEFT JOIN users u ON th.user_id = u.id 
            ORDER BY th.timestamp DESC LIMIT 100
        """).fetchall()
        
        logs = []
        for r in rows:
            entry = dict(r)
            # Format timestamp properly
            try:
                if entry.get('timestamp'):
                    dt = datetime.fromisoformat(str(entry['timestamp']).replace('Z', '+00:00'))
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=timezone.utc)
                    entry['timestamp'] = dt.astimezone().strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            
            entry['action'] = 'Trust Adjustment'
            entry['decision'] = 'ALERT' if entry.get('new_score', 0) < entry.get('old_score', 0) else 'INFO'
            entry['message'] = f"Score: {entry.get('old_score', '?')} → {entry.get('new_score', '?')}"
            entry['trust'] = entry.get('new_score', entry.get('trust_score', 100))
            entry['encrypted'] = False 
            entry['resource'] = 'trust_history' # Explicitly reference the table
            logs.append(entry)
            
        track_behavior("admin_logs_security")
        return render_template("admin/logs.html", decrypted_logs=logs, type=log_type, trust_score=session.get("trust_score", 100))
    else:
        # Fetch from encrypted files
        entries = get_decrypted_log_entries(log_type)
        track_behavior("admin_logs_secure")
        return render_template("admin/logs.html", decrypted_logs=entries, type=log_type, trust_score=session.get("trust_score", 100))

@app.route('/admin/grievances')
@login_required
@role_required(['admin'])
def admin_grievances():
    conn = get_db()

    grievances = conn.execute("""
        SELECT 
            g.id,
            u.name AS submitter_name,
            'Student' AS submitter_role,
            g.subject AS title,
            g.description,
            g.status,
            g.submitted_at,
            g.resolved_at
        FROM grievances g
        JOIN users u ON g.student_id = u.id

        UNION ALL

        SELECT
            pg.id,
            u.name AS submitter_name,
            'Parent' AS submitter_role,
            pg.title AS title,
            pg.description,
            pg.status,
            pg.submitted_at,
            pg.resolved_at
        FROM parent_grievances pg
        JOIN users u ON pg.parent_id = u.id

        ORDER BY submitted_at DESC
    """).fetchall()

    track_behavior("admin_grievances")

    return render_template(
        "admin/grievances.html",
        grievances=grievances,
        trust_score=session.get("trust_score", 100)
    )

@app.route('/admin/grievances/<int:grievance_id>/resolve', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_resolve_grievance(grievance_id):
    source = request.args.get("source")  # student / parent
    conn = get_db()

    if source == "parent":
        conn.execute("""
            UPDATE parent_grievances
            SET status='Resolved',
                resolved_at=?,
                resolved_by=?
            WHERE id=?
        """, (datetime.utcnow().isoformat(), session["user_id"], grievance_id))

    else:  # default → student grievance
        conn.execute("""
            UPDATE grievances
            SET status='resolved',
                resolved_at=?,
                resolved_by=?
            WHERE id=?
        """, (datetime.utcnow().isoformat(), session["user_id"], grievance_id))

    conn.commit()
    flash("Grievance marked as resolved.", "success")
    return redirect(url_for("admin_grievances"))

@app.route('/admin/trust_management')
@login_required
@role_required(['admin'])
def admin_trust_management():
    conn = get_db()
    users = conn.execute("SELECT id, username, role, trust_score FROM users").fetchall()
    return render_template("admin/trust_management.html", users=users)

@app.route('/admin/reset_trust/<int:user_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_reset_trust(user_id):
    conn = get_db()
    try:
        user = conn.execute("SELECT username, trust_score FROM users WHERE id=?", (user_id,)).fetchone()
        if user:
            old_trust = user["trust_score"]
            new_trust = 100
            
            # Update database
            conn.execute("UPDATE users SET trust_score=? WHERE id=?", (new_trust, user_id))
            
            # Log to history
            conn.execute(
                "INSERT INTO trust_history (user_id, old_score, new_score, reason) VALUES (?, ?, ?, ?)",
                (user_id, old_trust, new_trust, "ADMIN_RESET - Manually reset by admin")
            )
            conn.commit()
            
            # Log to actions.log
            log_action(f"TRUST_RESET | User: {user['username']} | Reset by Admin: {session.get('username')} | {old_trust} -> {new_trust}")
            flash(f"Trust score for {user['username']} has been reset to 100.", "success")
        else:
            flash("User not found.", "danger")
    except Exception as e:
        print(f"[ERROR] Trust reset failed: {e}")
        flash("Failed to reset trust score.", "danger")
    
    return redirect(url_for('admin_trust_management'))

@app.route('/admin/toggle_readonly')
@login_required
@role_required(['admin'])
def admin_toggle_readonly():
    global READ_ONLY_MODE
    
    track_behavior("toggle_readonly")
    
    if is_behavior_unusual():
        update_trust("suspicious")
        flash("Toggle blocked due to unusual behavior.", "warning")
        return redirect(url_for("dashboard"))
    
    READ_ONLY_MODE = not READ_ONLY_MODE
    status = "ON" if READ_ONLY_MODE else "OFF"
    log_action(f"Admin toggled Read-Only Mode: {status}")
    flash(f"Read-Only Mode is now {status}.", "info")
    return redirect(url_for("dashboard"))

@app.route('/admin/classes')
@login_required
@role_required(['admin'])
def admin_classes():
    conn = get_db()
    classes = conn.execute("""
        SELECT c.*, u.name as faculty_name 
        FROM classes c 
        LEFT JOIN faculty f ON c.faculty_id = f.id
        LEFT JOIN users u ON f.user_id = u.id
    """).fetchall()
    return render_template("admin/manage_classes.html", classes=classes)

@app.route('/admin/classes/add', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def add_class():
    conn = get_db()
    if request.method == "POST":
        name = request.form.get("name")
        dept = request.form.get("department")
        faculty_id = request.form.get("faculty_id")
        semester = request.form.get("semester")
        
        if name and dept:
            try:
                conn.execute("INSERT INTO classes (name, department, faculty_id, semester) VALUES (?, ?, ?, ?)",
                             (name, dept, faculty_id, semester))
                conn.commit()
                flash(f"Class '{name}' added successfully!", "success")
            except Exception as e:
                flash(f"Error adding class: {e}", "danger")
            return redirect(url_for("admin_classes"))
            
    # Fetch all users with role 'faculty'
    faculty = conn.execute("SELECT f.id, u.name FROM faculty f JOIN users u ON f.user_id = u.id").fetchall()
    departments = ["CSBS", "IT", "CS", "EC", "EEE"]
    return render_template("admin/add_class.html", faculty=faculty, departments=departments)

@app.route('/admin/classes/delete/<int:class_id>', methods=['POST'])
@login_required
@role_required(['admin'])
def admin_delete_class(class_id):
    conn = get_db()
    try:
        # Enrollments will be cascade deleted if foreign keys are enabled, 
        # but let's be explicit just in case PRAGMA foreign_keys is off.
        conn.execute("DELETE FROM class_enrollments WHERE class_id = ?", (class_id,))
        conn.execute("DELETE FROM classes WHERE id = ?", (class_id,))
        conn.commit()
        flash("Class deleted successfully!", "success")
    except Exception as e:
        flash(f"Error deleting class: {e}", "danger")
    return redirect(url_for("admin_classes"))

@app.route('/admin/classes/enroll', methods=['GET', 'POST'])
@login_required
@role_required(['admin'])
def enroll_student():
    conn = get_db()
    if request.method == "POST":
        class_id = request.form.get("class_id")
        student_id = request.form.get("student_id")
        
        if class_id and student_id:
            try:
                conn.execute("INSERT INTO class_enrollments (class_id, student_id) VALUES (?, ?)",
                             (class_id, student_id))
                conn.commit()
                flash("Student enrolled successfully!", "success")
            except sqlite3.IntegrityError:
                flash("Student is already enrolled in this class.", "warning")
            return redirect(url_for("admin_classes"))
            
    classes = conn.execute("SELECT * FROM classes").fetchall()
    students = conn.execute("SELECT s.id, u.name, s.roll FROM students s JOIN users u ON s.user_id = u.id").fetchall()
    return render_template("admin/enroll_student.html", classes=classes, students=students)

# NEWLY ADDED
def create_change_request(student_id, field, new_value, old_value="", trust_score=100):
    conn = get_db()

    conn.execute("""
        INSERT INTO profile_change_requests 
        (student_id, field_name, old_value, new_value, trust_score, requested_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (student_id, field, old_value, new_value, trust_score, datetime.utcnow().isoformat()))

    conn.commit()

@app.route('/student/request-profile-change', methods=['POST'])
@login_required
@role_required(['student'])
def request_profile_change():
    """Verify TOTP and submit profile change request in one step."""
    uid = session["user_id"]
    field_name = request.form.get("field_name", "").strip()
    new_value = request.form.get("new_value", "").strip()
    totp_code = request.form.get("totp_code", "").strip()

    if not field_name or not new_value or not totp_code:
        flash("All fields are required including TOTP code.", "danger")
        return redirect(url_for("student_profile"))

    if field_name not in ['email', 'phone']:
        flash("Invalid field.", "danger")
        return redirect(url_for("student_profile"))

    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()

    if not user:
        flash("User not found.", "danger")
        return redirect(url_for("student_profile"))

    # Verify TOTP code
    totp_secret = None
    try:
        totp_secret = user["totp_secret"]
    except (IndexError, KeyError):
        pass

    if not totp_secret:
        flash("TOTP not enrolled. Please contact admin.", "danger")
        return redirect(url_for("student_profile"))

    totp = pyotp.TOTP(totp_secret)
    if not totp.verify(totp_code):
        reduce_trust("invalid_totp_profile_change", 10)
        flash("Invalid TOTP code. Trust score reduced.", "trust_alert")
        log_action(f"PROFILE_CHANGE_FAILED | User: {user['username']} | Invalid TOTP for {field_name}")
        return redirect(url_for("student_profile"))

    # TOTP verified — create the change request
    trust_score = user["trust_score"] if user["trust_score"] else 100
    old_value = user[field_name] if field_name in dict(user).keys() else ""

    create_change_request(
        student_id=uid,
        field=field_name,
        new_value=new_value,
        old_value=old_value,
        trust_score=trust_score
    )

    write_access_log(conn, uid, "profile_change_request", "user", None, True, f"requested_{field_name}")
    log_action(f"Profile change requested by user {uid}: {field_name} (TOTP verified)")
    flash("Profile change request submitted successfully.", "success")
    return redirect(url_for("student_profile"))

# =============================================================================
# ASSIGNMENT HUB ROUTES
# =============================================================================

@app.route("/faculty/assignments", methods=["GET", "POST"])
@login_required
@role_required(['faculty'])
def faculty_assignments():
    conn = get_db()
    faculty_id = conn.execute("SELECT id FROM faculty WHERE user_id=?", (session['user_id'],)).fetchone()['id']
    
    if request.method == "POST":
        class_id = request.form.get("class_id")
        title = request.form.get("title")
        description = request.form.get("description")
        due_date = request.form.get("due_date")
        
        conn.execute("""
            INSERT INTO assignments (class_id, title, description, due_date, faculty_id)
            VALUES (?, ?, ?, ?, ?)
        """, (class_id, title, description, due_date, faculty_id))
        conn.commit()
        flash("Assignment posted successfully!", "success")
        return redirect(url_for('faculty_assignments'))
    
    # Get faculty's classes
    classes = conn.execute("SELECT * FROM classes WHERE faculty_id=?", (faculty_id,)).fetchall()
    # Get posted assignments
    assignments = conn.execute("""
        SELECT a.*, c.name as class_name 
        FROM assignments a 
        JOIN classes c ON a.class_id = c.id 
        WHERE a.faculty_id=?
        ORDER BY a.created_at DESC
    """, (faculty_id,)).fetchall()
    
    return render_template("faculty/assignments.html", classes=classes, assignments=assignments)

@app.route("/faculty/view-submissions/<int:assignment_id>")
@login_required
@role_required(['faculty'])
def faculty_view_submissions(assignment_id):
    conn = get_db()
    assignment = conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
    submissions = conn.execute("""
        SELECT s.*, u.name as student_name 
        FROM submissions s 
        JOIN students std ON s.student_id = std.id 
        JOIN users u ON std.user_id = u.id 
        WHERE s.assignment_id=?
        ORDER BY s.submitted_at DESC
    """, (assignment_id,)).fetchall()
    return render_template("faculty/view_submissions.html", assignment=assignment, submissions=submissions)

@app.route("/student/assignments")
@login_required
@role_required(['student'])
def student_assignments():
    conn = get_db()
    student_id = conn.execute("SELECT id FROM students WHERE user_id=?", (session['user_id'],)).fetchone()['id']
    
    # Get assignments for classes the student is enrolled in
    assignments = conn.execute("""
        SELECT a.*, c.name as class_name, u.name as faculty_name,
               (SELECT COUNT(*) FROM submissions s WHERE s.assignment_id = a.id AND s.student_id = ?) as is_submitted
        FROM assignments a
        JOIN classes c ON a.class_id = c.id
        JOIN class_enrollments ce ON c.id = ce.class_id
        JOIN faculty f ON a.faculty_id = f.id
        JOIN users u ON f.user_id = u.id
        WHERE ce.student_id = ?
        ORDER BY a.due_date ASC
    """, (student_id, student_id)).fetchall()
    
    return render_template("student/assignments.html", assignments=assignments)

@app.route("/student/submit-assignment/<int:assignment_id>", methods=["GET", "POST"])
@login_required
@role_required(['student'])
def student_submit_assignment(assignment_id):
    conn = get_db()
    student_id = conn.execute("SELECT id FROM students WHERE user_id=?", (session['user_id'],)).fetchone()['id']
    
    if request.method == "POST":
        text = request.form.get("submission_text")
        # Check if already submitted
        existing = conn.execute("SELECT id FROM submissions WHERE assignment_id=? AND student_id=?", (assignment_id, student_id)).fetchone()
        
        if existing:
            conn.execute("UPDATE submissions SET submission_text=?, submitted_at=CURRENT_TIMESTAMP WHERE id=?", (text, existing['id']))
        else:
            conn.execute("""
                INSERT INTO submissions (assignment_id, student_id, submission_text)
                VALUES (?, ?, ?)
            """, (assignment_id, student_id, text))
        conn.commit()
        flash("Assignment submitted successfully!", "success")
        return redirect(url_for('student_assignments'))
    
    assignment = conn.execute("SELECT * FROM assignments WHERE id=?", (assignment_id,)).fetchone()
    submission = conn.execute("SELECT * FROM submissions WHERE assignment_id=? AND student_id=?", (assignment_id, student_id)).fetchone()
    return render_template("student/submit_assignment.html", assignment=assignment, submission=submission)

#==============================================================================
# ERROR HANDLERS
# =============================================================================
@app.route('/admin/classes/<int:class_id>/students')
@login_required
@role_required(['admin'])
def admin_class_students(class_id):
    conn = get_db()
    class_info = conn.execute("SELECT * FROM classes WHERE id=?", (class_id,)).fetchone()
    if not class_info:
        flash("Class not found.", "danger")
        return redirect(url_for("admin_classes"))
        
    students = conn.execute("""
        SELECT s.id, s.roll, u.name, s.department, s.semester 
        FROM students s 
        JOIN users u ON s.user_id = u.id
        JOIN class_enrollments ce ON s.id = ce.student_id
        WHERE ce.class_id = ?
    """, (class_id,)).fetchall()
    
    return render_template("admin/class_students.html", class_info=class_info, students=students)

@app.errorhandler(404)
def not_found(e):
    return render_template("404.html"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template("500.html"), 500

# =============================================================================
# RUN APPLICATION
# =============================================================================
if __name__ == "__main__":
    print("=" * 60)
    print("STUDENT MANAGEMENT PORTAL")
    print("=" * 60)
    print("-" * 40)
    print("\nStarting server at http://127.0.0.1:5000")
    print("=" * 60)
    port = int(os.getenv("FLASK_PORT", 5000))
    app.run(debug=True, host="0.0.0.0", port=port)