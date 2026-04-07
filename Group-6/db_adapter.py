import os
import sqlite3
import psycopg2
from psycopg2 import extras
from urllib.parse import urlparse

class ConnectionWrapper:
    def __init__(self, conn, is_postgres):
        self.conn = conn
        self.is_postgres = is_postgres

    def execute(self, query, params=None):
        if self.is_postgres:
            query = query.replace("?", "%s")
            # Intercept SQLite-specific last_insert_rowid()
            if "last_insert_rowid()" in query.lower():
                query = query.lower().replace("last_insert_rowid()", "lastval()")
        
        cur = self.conn.cursor()
        try:
            if params:
                cur.execute(query, params)
            else:
                cur.execute(query)
        except Exception as e:
            if self.is_postgres:
                self.conn.rollback()
            raise
        return cur

    def commit(self):
        self.conn.commit()

    def close(self):
        self.conn.close()

    def executescript(self, script):
        if self.is_postgres:
            # PostgreSQL: split by semicolons and execute each statement individually
            # so one failure doesn't abort the entire transaction
            cur = self.conn.cursor()
            statements = [s.strip() for s in script.split(';') if s.strip()]
            for stmt in statements:
                try:
                    cur.execute(stmt)
                except Exception as e:
                    print(f"[DB] Statement skipped (likely already exists): {e}")
                    self.conn.rollback()
            self.conn.commit()
        else:
            self.conn.executescript(script)

    def rollback(self):
        self.conn.rollback()

    def fetchone(self, query, params=None):
        cur = self.execute(query, params)
        return cur.fetchone()

    def fetchall(self, query, params=None):
        cur = self.execute(query, params)
        return cur.fetchall()

class DatabaseAdapter:
    def __init__(self):
        self._is_postgres = False
        
    def get_connection(self):
        db_url = os.getenv("DATABASE_URL")
        self._is_postgres = bool(db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")))
        
        if self._is_postgres:
            try:
                if "[YOUR-PASSWORD]" in db_url:
                    raise ValueError("You must replace [YOUR-PASSWORD] in your .env file with your actual database password.")
                
                conn = psycopg2.connect(db_url)
                print(f"[DB] Connected to POSTGRES (Neon DB)")
                conn.cursor_factory = extras.DictCursor
                return ConnectionWrapper(conn, True)
            except Exception as e:
                print(f"[CRITICAL] PostgreSQL Connection Failed: {e}")
                # We stop exactly here because the user wants POSTGRES ONLY.
                raise Exception("Cloud Deployment Error: Database is not available. Check DATABASE_URL.")

        # STRICT ENFORCEMENT: No SQLite fallback for production/cloud readiness
        print("[CRITICAL] DATABASE_URL not set or not a postgres URL.")
        raise Exception("Configuration Error: DATABASE_URL must be a valid PostgreSQL connection string for cloud deployment.")

    @property
    def is_postgres(self):
        db_url = os.getenv("DATABASE_URL")
        return bool(db_url and (db_url.startswith("postgres://") or db_url.startswith("postgresql://")))

db_adapter = DatabaseAdapter()
