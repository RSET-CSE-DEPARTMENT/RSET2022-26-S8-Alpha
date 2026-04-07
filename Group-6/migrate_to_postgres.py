import sqlite3
import psycopg2
import os
from dotenv import load_dotenv
from db_adapter import db_adapter

load_dotenv()

SQLITE_DB = "db/portal.db"

# Tables in dependency order (parents before children)
TABLE_ORDER = [
    "users",
    "students",
    "faculty",
    "parents",
    "classes",
    "access_logs",
    "profile_change_requests",
    "trusted_devices",
    "trust_history",
    "announcements",
    "grievances",
    "marks",
    "attendance",
    "device_fingerprints",
    "parent_grievances",
    "fee_payments",
    "login_history",
    "class_enrollments",
    "assignments",
    "submissions",
]

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("[ERROR] DATABASE_URL not found in .env")
        return

    print(f"[MIGRATE] Connecting to SQLite: {SQLITE_DB}")
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cur = sqlite_conn.cursor()

    print(f"[MIGRATE] Connecting to Postgres...")
    db_url = os.getenv("DATABASE_URL")
    try:
        pg_conn = psycopg2.connect(db_url)
        # Use a standard cursor (NOT RealDictCursor) for migration
        pg_cur = pg_conn.cursor()
        print("[MIGRATE] Connected to PostgreSQL!")
    except Exception as e:
        print(f"[ERROR] PostgreSQL connection failed: {e}")
        return

    # Get tables that actually exist in SQLite
    sqlite_cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
    sqlite_tables = set(row['name'] for row in sqlite_cur.fetchall())

    # Merge: ordered tables first, then any extras not in our list
    tables_to_migrate = [t for t in TABLE_ORDER if t in sqlite_tables]
    extras = [t for t in sqlite_tables if t not in TABLE_ORDER]
    tables_to_migrate.extend(extras)

    total_inserted = 0
    total_skipped = 0

    for table in tables_to_migrate:
        print(f"[MIGRATE] Migrating table: {table}")
        
        # Check if table exists in Postgres
        pg_cur.execute("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = %s)", (table,))
        if not pg_cur.fetchone()[0]:
            print(f"  -> Skipping {table} (not in Postgres schema)")
            continue
        
        sqlite_cur.execute(f"SELECT * FROM {table}")
        rows = sqlite_cur.fetchall()
        
        if not rows:
            print(f"  -> Skipping {table} (no data)")
            continue

        columns = rows[0].keys()
        placeholders = ", ".join(["%s"] * len(columns))
        col_names = ", ".join(columns)
        
        # Clear existing data
        pg_cur.execute(f"TRUNCATE TABLE {table} CASCADE")
        pg_conn.commit()
        
        insert_query = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"
        all_data = [list(row) for row in rows]
        
        count = 0
        errors = 0
        
        # Try batch insert first (fast)
        try:
            from psycopg2.extras import execute_batch
            execute_batch(pg_cur, insert_query, all_data, page_size=500)
            pg_conn.commit()
            count = len(all_data)
        except Exception as batch_err:
            pg_conn.rollback()
            print(f"  -> Batch insert failed, falling back to row-by-row...")
            # Fall back to per-row (handles FK violations gracefully)
            for row_data in all_data:
                try:
                    pg_cur.execute(insert_query, row_data)
                    pg_conn.commit()
                    count += 1
                except Exception as e:
                    errors += 1
                    pg_conn.rollback()
                    if errors <= 3:
                        print(f"  -> [WARN] Skipped row: {str(e).strip()[:100]}")
        
        print(f"  -> Inserted {count} rows into {table}" + (f" ({errors} skipped)" if errors else ""))
        total_inserted += count
        total_skipped += errors

        # Fix SERIAL sequences
        try:
            pg_cur.execute(f"SELECT setval(pg_get_serial_sequence('{table}', 'id'), (SELECT COALESCE(MAX(id), 1) FROM {table}))")
            pg_conn.commit()
        except Exception:
            pg_conn.rollback()

    print(f"\n[MIGRATE] Migration complete! {total_inserted} rows inserted, {total_skipped} skipped.")
    
    sqlite_conn.close()
    pg_conn.close()

if __name__ == "__main__":
    print("[INFO] Make sure you have run app.py once to initialize the Postgres schema!")
    confirm = input("Continue with data migration? (y/n): ")
    if confirm.lower() == 'y':
        migrate()
