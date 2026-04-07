"""Force migrate ALL access_logs from SQLite to Neon DB — no skips."""
import sqlite3
import psycopg2
import os
import sys
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = os.path.join(os.path.dirname(os.path.abspath(__file__)), "db", "portal.db")
db_url = os.getenv("DATABASE_URL")

print(f"[1/4] SQLite: {SQLITE_DB}")
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_conn.row_factory = sqlite3.Row

print("[2/4] Connecting to Neon...")
pg_conn = psycopg2.connect(db_url)
pg_cur = pg_conn.cursor()
print("    Connected!")

rows = sqlite_conn.execute("SELECT * FROM access_logs ORDER BY id").fetchall()
columns = rows[0].keys() if rows else []
print(f"    SQLite has {len(rows)} access_log rows")

# Clear + reinsert
print("[3/4] Truncating Neon access_logs and inserting all rows...")
pg_cur.execute("DELETE FROM access_logs;")
pg_conn.commit()

col_names = ", ".join(columns)
placeholders = ", ".join(["%s"] * len(columns))
insert_sql = f"INSERT INTO access_logs ({col_names}) VALUES ({placeholders})"

inserted = 0
errors = 0
for row in rows:
    try:
        pg_cur.execute(insert_sql, list(row))
        pg_conn.commit()
        inserted += 1
    except Exception as e:
        errors += 1
        pg_conn.rollback()
        if errors <= 5:
            print(f"    [WARN] Row id={row['id']}: {str(e).strip()[:100]}")

# Fix sequence
try:
    pg_cur.execute("SELECT setval(pg_get_serial_sequence('access_logs', 'id'), (SELECT COALESCE(MAX(id),1) FROM access_logs));")
    pg_conn.commit()
except:
    pg_conn.rollback()

pg_cur.execute("SELECT COUNT(*) FROM access_logs")
neon_count = pg_cur.fetchone()[0]

print(f"\n[4/4] DONE!")
print(f"    SQLite:  {len(rows)}")
print(f"    Inserted: {inserted}")
print(f"    Errors:   {errors}")
print(f"    Neon now: {neon_count}")

sqlite_conn.close()
pg_conn.close()
