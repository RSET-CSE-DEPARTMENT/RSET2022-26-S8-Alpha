import psycopg2
from psycopg2 import extras
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor(cursor_factory=extras.DictCursor)
    cur.execute('SELECT 1 as val, 2 as second')
    row = cur.fetchone()
    print(f"Index access row[0]: {row[0]}")
    print(f"Index access row[1]: {row[1]}")
    print(f"Key access row['val']: {row['val']}")
    print(f"Key access row['second']: {row['second']}")
    conn.close()
    print("[SUCCESS] DictCursor supports both!")
except Exception as e:
    print(f"[FAILED] {e}")
