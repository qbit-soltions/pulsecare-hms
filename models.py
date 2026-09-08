"""
PulseCare Hospital Management System - Database Models & Helper Functions
Supports dual-mode database operation:
- Supabase PostgreSQL (via DATABASE_URL or SUPABASE_DB_URL)
- Local SQLite (pulsecare.db) for offline development & testing
"""
import os
import re
import shutil
import json
from datetime import datetime, date
from decimal import Decimal
from werkzeug.security import generate_password_hash, check_password_hash

# Try loading .env if python-dotenv is present
try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

# Supabase PostgreSQL / Database URL detection
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or os.environ.get("POSTGRES_URL")
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY") or os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or os.environ.get("SUPABASE_ANON_KEY")

# Driver detection
_HAS_PSYCOPG2 = False
_HAS_PG8000 = False
_HAS_SUPABASE = False

try:
    import psycopg2
    import psycopg2.extras
    _HAS_PSYCOPG2 = True
except ImportError:
    pass

try:
    import pg8000
    import pg8000.native
    _HAS_PG8000 = True
except ImportError:
    pass

try:
    from supabase import create_client, Client
    _HAS_SUPABASE = True
except ImportError:
    pass

import sqlite3


def is_postgres():
    """Returns False to unlink from remote Supabase and enforce local SQLite for maximum speed."""
    return False


def get_supabase_client():
    """Unlinked from Supabase - returns None to ensure local-only execution."""
    return None



def get_db_path():
    """Resolves local SQLite database path, copying to /tmp in serverless environments if needed."""
    bundled_db = os.path.join(os.path.dirname(__file__), "pulsecare.db")
    if os.environ.get("AWS_LAMBDA_FUNCTION_NAME") or os.environ.get("NETLIFY") or not os.access(os.path.dirname(bundled_db) or ".", os.W_OK):
        tmp_db = os.path.join("/tmp", "pulsecare.db")
        if not os.path.exists(tmp_db):
            if os.path.exists(bundled_db):
                try:
                    shutil.copy2(bundled_db, tmp_db)
                except Exception as e:
                    print(f"Error copying DB to /tmp: {e}")
        if os.path.exists(tmp_db) or not os.path.exists(bundled_db):
            return tmp_db
    return bundled_db


DB_PATH = get_db_path()


def _clean_pg_url(url):
    """Ensure postgresql:// scheme is used instead of legacy postgres:// for psycopg2/pg8000."""
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def _connect_postgres_resilient(db_url):
    """Connect to PostgreSQL with multi-IP DNS resolution fallback for Supabase poolers."""
    from urllib.parse import urlparse, unquote
    import socket
    
    p = urlparse(db_url)
    hostname = p.hostname
    port = p.port or 5432
    user = unquote(p.username or "postgres")
    password = unquote(p.password or "")
    dbname = p.path.lstrip("/") or "postgres"

    # Build candidate host list: hostname first, then resolved IPv4s
    candidate_hosts = [hostname]
    try:
        addr_info = socket.getaddrinfo(hostname, port, socket.AF_INET, socket.SOCK_STREAM)
        for item in addr_info:
            ip = item[4][0]
            if ip not in candidate_hosts:
                candidate_hosts.append(ip)
    except Exception:
        pass

    last_err = None
    for h in candidate_hosts:
        try:
            if _HAS_PSYCOPG2:
                conn = psycopg2.connect(
                    host=h,
                    port=port,
                    dbname=dbname,
                    user=user,
                    password=password,
                    sslmode="require",
                    connect_timeout=5
                )
                return conn
            elif _HAS_PG8000:
                conn = pg8000.connect(
                    host=h,
                    port=port,
                    database=dbname,
                    user=user,
                    password=password,
                    ssl_context=True
                )
                return conn
        except Exception as exc:
            last_err = exc
            continue

    if last_err:
        raise last_err
    raise RuntimeError("Unable to connect to PostgreSQL database.")


def get_db_connection():
    """
    Returns a high-performance local SQLite connection.
    Configured with WAL mode, 32MB cache, and 256MB memory mapping for instantaneous queries.
    """
    db_file = get_db_path()
    conn = sqlite3.connect(db_file, timeout=30, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")       # Ultra-fast concurrent reads/writes
    conn.execute("PRAGMA synchronous = NORMAL")     # Safe with WAL, maximum throughput
    conn.execute("PRAGMA cache_size = -32000")      # 32MB in-memory page cache
    conn.execute("PRAGMA temp_store = MEMORY")      # Temporary tables and indices in RAM
    conn.execute("PRAGMA mmap_size = 268435456")    # 256MB memory-mapped file I/O for instant reads
    return conn



def _normalize_query_for_postgres(query):
    """
    Translates SQLite syntax to PostgreSQL syntax:
    - Replaces '?' placeholders with '%s'
    - Replaces datetime('now') with CURRENT_TIMESTAMP
    - Replaces date('now') with CURRENT_DATE
    """
    pg_query = query.replace("?", "%s")
    pg_query = re.sub(r"\bdatetime\('now'\)", "CURRENT_TIMESTAMP", pg_query, flags=re.IGNORECASE)
    pg_query = re.sub(r"\bdate\('now'\)", "CURRENT_DATE", pg_query, flags=re.IGNORECASE)
    return pg_query


def _format_row_dict(d):
    """Convert PostgreSQL Decimal, Date, and Timestamp objects to JSON/template-friendly formats."""
    clean = {}
    for k, v in d.items():
        if isinstance(v, Decimal):
            clean[k] = float(v) if "." in str(v) else int(v)
        elif isinstance(v, (datetime, date)):
            clean[k] = str(v)
        else:
            clean[k] = v
    return clean


def query_db(query, args=(), one=False):
    """Executes a query and returns dictionaries."""
    conn = get_db_connection()
    try:
        if not isinstance(conn, sqlite3.Connection) and is_postgres():
            cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) if _HAS_PSYCOPG2 else conn.cursor()
            pg_query = _normalize_query_for_postgres(query)
            if args:
                cur.execute(pg_query, args)
            else:
                cur.execute(pg_query)
            rows = cur.fetchall()
            
            if _HAS_PSYCOPG2:
                results = [_format_row_dict(dict(r)) for r in rows]
            else:
                col_names = [col[0] for col in cur.description] if cur.description else []
                results = [_format_row_dict(dict(zip(col_names, row))) for row in rows]
                
            return (results[0] if results else None) if one else results

        # SQLite Mode
        cur = conn.cursor()
        cur.execute(query, args)
        rv = cur.fetchall()
        return (dict(rv[0]) if rv else None) if one else [dict(r) for r in rv]
    finally:
        conn.close()


def execute_db(query, args=()):
    """
    Executes an INSERT, UPDATE, or DELETE query.
    Returns:
    - On INSERT: The newly created integer ID (lastrowid)
    - On UPDATE/DELETE: The number of rows affected
    """
    conn = get_db_connection()
    try:
        if not isinstance(conn, sqlite3.Connection) and is_postgres():
            cur = conn.cursor()
            pg_query = _normalize_query_for_postgres(query)
            is_insert = pg_query.strip().upper().startswith("INSERT INTO")
            has_returning = "RETURNING" in pg_query.upper()

            if is_insert and not has_returning and "hospital_settings" not in pg_query.lower():
                pg_query = pg_query.rstrip("; ") + " RETURNING id"
                if args:
                    cur.execute(pg_query, args)
                else:
                    cur.execute(pg_query)
                res = cur.fetchone()
                conn.commit()
                return res[0] if res else None
            else:
                if args:
                    cur.execute(pg_query, args)
                else:
                    cur.execute(pg_query)
                conn.commit()
                if has_returning:
                    res = cur.fetchone()
                    return res[0] if res else None
                return cur.rowcount

        # SQLite Mode
        cur = conn.cursor()
        cur.execute(query, args)
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()



def execute_many_db(query, args_list):
    """Executes a parameterized query for multiple parameter sets."""
    if not args_list:
        return 0
    conn = get_db_connection()
    try:
        if is_postgres():
            cur = conn.cursor()
            pg_query = _normalize_query_for_postgres(query)
            cur.executemany(pg_query, args_list)
            conn.commit()
            return cur.rowcount

        # SQLite Mode
        cur = conn.cursor()
        cur.executemany(query, args_list)
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


def log_audit(user_id, action, module, details, ip_address="127.0.0.1", facility_id=None):
    """Logs an audit activity into the database."""
    try:
        execute_db(
            """INSERT INTO audit_logs (user_id, facility_id, action, module, details, ip_address, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (user_id, facility_id, action, module, details, ip_address, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
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
    """Initializes the database schema (works for SQLite and PostgreSQL)."""
    conn = get_db_connection()
    try:
        if isinstance(conn, sqlite3.Connection):
            schema_path = os.path.join(os.path.dirname(__file__), "schema.sql")
            with open(schema_path, "r", encoding="utf-8") as f:
                schema_sql = f.read()
            conn.executescript(schema_sql)
            conn.commit()
            print("Successfully initialized SQLite database schema!")
        else:
            schema_path = os.path.join(os.path.dirname(__file__), "supabase_schema.sql")
            if not os.path.exists(schema_path):
                schema_path = os.path.join(os.path.dirname(__file__), schema_file)
            with open(schema_path, "r", encoding="utf-8") as f:
                sql_script = f.read()
            cur = conn.cursor()
            cur.execute(sql_script)
            conn.commit()
            print("Successfully initialized Supabase PostgreSQL database schema!")
    finally:
        conn.close()
