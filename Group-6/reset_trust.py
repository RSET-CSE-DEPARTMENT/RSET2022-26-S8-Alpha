import sqlite3

DB_PATH = "db/portal.db"

def reset_all_trust_scores():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        users = c.execute("SELECT id, username, trust_score, failed_attempts, otp_failures FROM users").fetchall()

        if not users:
            print("No users found in the database.")
            conn.close()
            return

        print(f"{'Username':<20} {'Trust Score':>12} {'Failed Attempts':>16} {'OTP Failures':>13}")
        print("-" * 65)
        for user in users:
            print(f"{user['username']:<20} {user['trust_score']:>12} {user['failed_attempts']:>16} {user['otp_failures']:>13}")

        c.execute("UPDATE users SET trust_score=100, failed_attempts=0, otp_failures=0")
        conn.commit()

        print(f"\nReset complete. {len(users)} user(s) updated: trust_score=100, failed_attempts=0, otp_failures=0.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    reset_all_trust_scores()
