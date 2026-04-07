import sqlite3
import os

DB_PATH = "db/portal.db"

def migrate():
    if not os.path.exists(DB_PATH):
        print(f"Error: Database {DB_PATH} not found. Please run app.py first.")
        return

    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    print("Applying migration...")
    
    try:
        # 1. Create Classes table
        c.execute("""
            CREATE TABLE IF NOT EXISTS classes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT,
                faculty_id INTEGER,
                semester INTEGER,
                FOREIGN KEY(faculty_id) REFERENCES faculty(id)
            )
        """)
        print("✓ Created 'classes' table")

        # 2. Create Class Enrollments table
        c.execute("""
            CREATE TABLE IF NOT EXISTS class_enrollments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_id INTEGER,
                student_id INTEGER,
                UNIQUE(class_id, student_id),
                FOREIGN KEY(class_id) REFERENCES classes(id) ON DELETE CASCADE,
                FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
            )
        """)
        print("✓ Created 'class_enrollments' table")
        
        conn.commit()
        print("\nMigration completed successfully.")
    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
