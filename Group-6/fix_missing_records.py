import sqlite3
import os

DB_PATH = "db/portal.db"

def fix():
    if not os.path.exists(DB_PATH):
        print("DB not found")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    # Fix Faculty
    print("Checking for missing Faculty records...")
    faculty_users = c.execute("SELECT id, username FROM users WHERE role='faculty'").fetchall()
    for user in faculty_users:
        existing = c.execute("SELECT id FROM faculty WHERE user_id=?", (user['id'],)).fetchone()
        if not existing:
            emp_id = f"FAC{str(user['id']).zfill(4)}"
            c.execute("INSERT INTO faculty (user_id, employee_id) VALUES (?, ?)", (user['id'], emp_id))
            print(f"Fixed Faculty: {user['username']}")

    # Fix Students
    print("Checking for missing Student records...")
    student_users = c.execute("SELECT id, username FROM users WHERE role='student'").fetchall()
    for user in student_users:
        existing = c.execute("SELECT id FROM students WHERE user_id=?", (user['id'],)).fetchone()
        if not existing:
            roll = f"STU{str(user['id']).zfill(4)}"
            c.execute("INSERT INTO students (user_id, roll) VALUES (?, ?)", (user['id'], roll))
            print(f"Fixed Student: {user['username']}")

    # Fix Parents
    print("Checking for missing Parent records...")
    parent_users = c.execute("SELECT id, username FROM users WHERE role='parent'").fetchall()
    for user in parent_users:
        existing = c.execute("SELECT id FROM parents WHERE user_id=?", (user['id'],)).fetchone()
        if not existing:
            c.execute("INSERT INTO parents (user_id) VALUES (?)", (user['id'],))
            print(f"Fixed Parent: {user['username']}")

    conn.commit()
    conn.close()
    print("Done!")

if __name__ == "__main__":
    fix()
