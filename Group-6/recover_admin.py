import sqlite3
import os

DB_PATH = "db/portal.db"

def recover_admin():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # Check admin1
        user = c.execute("SELECT id, username, trust_score, failed_attempts, otp_failures, blocked_until FROM users WHERE username='admin'").fetchone()
        
        if user:
            print(f"Found User: {user['username']}")
            print(f"Current Trust Score: {user['trust_score']}")
            print(f"Current Blocked Until: {user['blocked_until']}")
            print(f"Failed/OTP Attempts: {user['failed_attempts']}/{user['otp_failures']}")

            # Reset security metrics
            c.execute("""
                UPDATE users 
                SET trust_score=100, 
                    failed_attempts=0, 
                    otp_failures=0, 
                    blocked_until=NULL, 
                    active_session=0 
                WHERE username='admin1'
            """)
            conn.commit()
            
            print("\n✅ Admin security metrics have been reset.")
            print("- Trust Score: 100")
            print("- Failures/Blocks: Cleared")
            print("- Session: Reset (You can log in now)")
            
            # Record the manual recovery in trust history
            c.execute("""
                INSERT INTO trust_history (user_id, old_score, new_score, reason)
                VALUES (?, ?, 100, ?)
            """, (user['id'], user['trust_score'], "MANUAL_RECOVERY - Admin requested reset"))
            conn.commit()
            
        else:
            print("Error: User 'admin1' not found in database.")
            
        conn.close()
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    recover_admin()
