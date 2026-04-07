import sqlite3
import os

DB_PATH = "db/portal.db"

def clear_data():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found.")
        return

    confirm = input("This will DELETE all users (except admin), students, faculty, and related data. Are you sure? (y/n): ")
    if confirm.lower() != 'y':
        print("Aborted.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Clearing data...")
    
    try:
        # Tables to clear
        tables = [
            "students", "faculty", "parents", "marks", "attendance", 
            "announcements", "grievances", "fee_payments", "login_history",
            "trust_history", "access_logs", "profile_change_requests",
            "device_fingerprints", "parent_grievances", "trusted_devices",
            "class_enrollments", "classes"
        ]
        
        for table in tables:
            try:
                c.execute(f"DELETE FROM {table}")
                print(f"✓ Cleared {table}")
            except sqlite3.OperationalError:
                print(f"! Table {table} does not exist, skipping.")

        # Delete users except admin
        c.execute("DELETE FROM users WHERE role != 'admin'")
        print("✓ Cleared users (except admin)")
        
        # Reset auto-increments
        for table in tables + ["users"]:
            try:
                c.execute("DELETE FROM sqlite_sequence WHERE name=?", (table,))
            except:
                pass

        conn.commit()
        print("\nAll filler data cleared successfully.")
        print("You can now login with 'admin' / 'admin123' and start adding real data.")
    except Exception as e:
        print(f"Error during cleanup: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    clear_data()
