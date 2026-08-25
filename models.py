"""
PulseCare Hospital Management System - Database Models & Helper Functions
"""
import sqlite3
import os
import shutil
import json
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

def get_db_path():
    """Resolves database path, copying to /tmp in serverless environments if needed."""
    bundled_db = os.path.join(os.path.dirname(__file__), "pulsecare.db")
    # Check if running in a serverless environment (Netlify / Lambda / Read-only root)
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("NETLIFY") or not os.access(os.path.dirname(bundled_db) or ".", os.W_OK):
        tmp_db = os.path.join("/tmp", "pulsecare.db")
        if not os.path.exists(tmp_db):
            if os.path.exists(bundled_db):
                try:
                    shutil.copy2(bundled_db, tmp_db)
                except Exception as e:
                    print(f"Error copying DB to /tmp: {e}")
            else:
                # If bundled DB doesn't exist yet, create schema in /tmp
                pass
        if os.path.exists(tmp_db) or not os.path.exists(bundled_db):
            return tmp_db
    return bundled_db

DB_PATH = get_db_path()

def get_db_connection():
    """Returns a SQLite connection configured with dict-like row factory and foreign keys."""
    db_file = get_db_path()
    conn = sqlite3.connect(db_file, timeout=30)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def query_db(query, args=(), one=False):
    """Executes a query and returns dictionaries."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (dict(rv[0]) if rv else None) if one else [dict(r) for r in rv]
    finally:
        conn.close()

def execute_db(query, args=()):
    """Executes an INSERT, UPDATE, or DELETE query and returns the lastrowid."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()

def execute_many_db(query, args_list):
    """Executes a parameterized query for multiple parameter sets."""
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.executemany(query, args_list)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()

def log_audit(user_id, action, module, details, ip_address="127.0.0.1"):
    """Logs an audit activity into the database."""
    try:
        execute_db(
            """INSERT INTO audit_logs (user_id, action, module, details, ip_address, timestamp)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (user_id, action, module, details, ip_address, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        )
    except Exception as e:
        print(f"Audit log error: {e}")

def get_setting(key, default=None):
    """Retrieves a setting value from hospital_settings table."""
    row = query_db("SELECT value FROM hospital_settings WHERE key = ?", (key,), one=True)
    return row["value"] if row else default

def set_setting(key, value):
    """Sets or updates a setting in hospital_settings table."""
    execute_db(
        "INSERT INTO hospital_settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value)
    )

def init_db(schema_file="schema.sql"):
    """Initializes the database schema."""
    conn = get_db_connection()
    try:
        with open(os.path.join(os.path.dirname(__file__), schema_file), "r", encoding="utf-8") as f:
            schema_sql = f.read()
        conn.executescript(schema_sql)
        conn.commit()
    finally:
        conn.close()
