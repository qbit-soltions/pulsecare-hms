"""
PulseCare HMS - Supabase Data Migration & Sync Tool
Transfers all tables, records, and sequences from local SQLite to Supabase PostgreSQL.
"""
import os
import sys
import sqlite3
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv(override=False)
except ImportError:
    pass

import psycopg2
import psycopg2.extras

# Tables in topological dependency order (foreign keys respected)
TABLE_ORDER = [
    "hospital_settings",
    "facilities",
    "departments",
    "users",
    "patients",
    "vitals",
    "teleconsultations",
    "referrals",
    "high_risk_registry",
    "appointments",
    "consultations",
    "medicines",
    "facility_inventory",
    "prescriptions",
    "prescription_items",
    "pharmacy_dispenses",
    "wards",
    "beds",
    "admissions",
    "lab_tests_catalog",
    "facility_diagnostics",
    "lab_orders",
    "lab_order_items",
    "invoices",
    "invoice_items",
    "audit_logs"
]


def clean_pg_url(url):
    if url and url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql://", 1)
    return url


def run_migration():
    print("=" * 70)
    print("PulseCare HMS -> Supabase PostgreSQL Migration Tool")
    print("=" * 70)

    db_url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL") or os.environ.get("POSTGRES_URL")
    if not db_url:
        print("\n[ERROR] No DATABASE_URL or SUPABASE_DB_URL found in environment or .env file.")
        print("Please set DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres")
        print("Example:")
        print("  export DATABASE_URL=\"postgresql://postgres.xxx:password@aws-0-ap-south-1.pooler.supabase.com:6543/postgres?sslmode=require\"")
        print("  python migrate_to_supabase.py")
        sys.exit(1)

    db_url = clean_pg_url(db_url)
    sqlite_path = os.path.join(os.path.dirname(__file__), "pulsecare.db")

    if not os.path.exists(sqlite_path):
        print(f"\n[ERROR] Source SQLite database not found at: {sqlite_path}")
        sys.exit(1)

    print(f"\n[1/4] Connecting to Source SQLite: {sqlite_path}")
    sqlite_conn = sqlite3.connect(sqlite_path)
    sqlite_conn.row_factory = sqlite3.Row

    print(f"[2/4] Connecting to Target Supabase PostgreSQL...")
    try:
        pg_conn = psycopg2.connect(db_url)
        pg_cur = pg_conn.cursor()
        print("      Connected to Supabase PostgreSQL successfully!")
    except Exception as exc:
        print(f"[ERROR] Could not connect to Supabase: {exc}")
        sys.exit(1)

    # Apply Supabase Schema
    schema_path = os.path.join(os.path.dirname(__file__), "supabase_schema.sql")
    if os.path.exists(schema_path):
        print(f"[3/4] Ensuring Supabase tables exist from supabase_schema.sql...")
        with open(schema_path, "r", encoding="utf-8") as f:
            schema_sql = f.read()
        try:
            pg_cur.execute(schema_sql)
            pg_conn.commit()
            print("      Supabase schema verified / created successfully.")
        except Exception as exc:
            pg_conn.rollback()
            print(f"      Schema application notice: {exc}")

    # Transfer Records Table by Table
    print(f"\n[4/4] Migrating data records to Supabase...")
    total_migrated = 0

    for table in TABLE_ORDER:
        try:
            s_cur = sqlite_conn.cursor()
            s_cur.execute(f"SELECT * FROM {table}")
            rows = s_cur.fetchall()
            
            if not rows:
                print(f"  - {table:<25} : 0 rows (empty)")
                continue

            columns = [col[0] for col in s_cur.description]
            cols_str = ", ".join([f'"{c}"' for c in columns])
            placeholders = ", ".join(["%s"] * len(columns))

            # Upsert into PostgreSQL
            if table == "hospital_settings":
                upsert_sql = f"""
                    INSERT INTO {table} ({cols_str}) 
                    VALUES ({placeholders}) 
                    ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value
                """
            else:
                # Handle conflict on primary key id if applicable
                if "id" in columns:
                    update_cols = [f'"{c}" = EXCLUDED."{c}"' for c in columns if c != "id"]
                    update_str = ", ".join(update_cols)
                    if update_str:
                        upsert_sql = f"""
                            INSERT INTO {table} ({cols_str}) 
                            VALUES ({placeholders}) 
                            ON CONFLICT (id) DO UPDATE SET {update_str}
                        """
                    else:
                        upsert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT (id) DO NOTHING"
                else:
                    upsert_sql = f"INSERT INTO {table} ({cols_str}) VALUES ({placeholders}) ON CONFLICT DO NOTHING"

            batch_data = [[row[c] for c in columns] for row in rows]
            psycopg2.extras.execute_batch(pg_cur, upsert_sql, batch_data)
            pg_conn.commit()

            # Reset sequence for tables with serial id
            if "id" in columns:
                try:
                    pg_cur.execute(f"""
                        SELECT setval(pg_get_serial_sequence('{table}', 'id'), 
                                      COALESCE((SELECT MAX(id) FROM {table}), 1), 
                                      true);
                    """)
                    pg_conn.commit()
                except Exception:
                    pg_conn.rollback()

            print(f"  + {table:<25} : {len(rows):>4} rows migrated successfully")
            total_migrated += len(rows)

        except Exception as err:
            pg_conn.rollback()
            print(f"  x Error migrating table {table}: {err}")

    sqlite_conn.close()
    pg_conn.close()

    print("\n" + "=" * 70)
    print(f"MIGRATION COMPLETE! Total records migrated: {total_migrated}")
    print("Your PulseCare HMS is now connected and synced with Supabase PostgreSQL.")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_migration()
