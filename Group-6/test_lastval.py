import psycopg2
from dotenv import load_dotenv
import os

load_dotenv()

try:
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()
    
    # Test table
    cur.execute("CREATE TEMP TABLE test_id (id SERIAL PRIMARY KEY, val TEXT)")
    
    # Insert and commit
    cur.execute("INSERT INTO test_id (val) VALUES ('test')")
    conn.commit()
    
    # Try lastval() after commit
    cur.execute("SELECT lastval()")
    val = cur.fetchone()[0]
    print(f"lastval after commit: {val}")
    
    conn.close()
    print("[SUCCESS] lastval() works after commit in the same session.")
except Exception as e:
    print(f"[FAILED] {e}")
