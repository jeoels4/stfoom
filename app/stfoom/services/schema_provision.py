"""Schema provisioning helper

Provides an idempotent function to ensure the main DB and sync tracking DB
have the minimum required tables and columns so SyncService can run safely on a
fresh install.

This module will:
 - instantiate SyncService to ensure sync_tracking DB and its tables exist
 - for each table referenced by SyncService.table_pk_map, ensure the table
   exists locally with at least the primary key column and created_at/updated_at
   columns (safe minimal skeleton). If the table exists, missing timestamp
   columns are added.
 - create simple AFTER INSERT/UPDATE triggers to set timestamps when missing.

The approach is conservative and aims to unblock sync operations while
avoiding destructive schema changes.
"""
from typing import Dict
import sqlite3
import os
from datetime import datetime

from config.settings import get_db_path
from app.stfoom.services.sync_service import SyncService


def ensure_schema_ready(db_path: str = None) -> None:
    """Ensure required tables/columns/triggers exist for smart sync to run.

    This is idempotent and safe to call at startup.
    
    Args:
        db_path: Optional path to database. If None, uses default from get_db_path()
    """
    # Ensure sync tracking DB/tables exist
    svc = SyncService()

    if db_path is None:
        db_path = get_db_path()
    os.makedirs(os.path.dirname(db_path), exist_ok=True)

    table_map: Dict[str, str] = getattr(svc, 'table_pk_map', {}) or {}

    conn = sqlite3.connect(db_path)
    try:
        cur = conn.cursor()
        for table, pk in table_map.items():
            try:
                # Check if table exists
                cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
                if not cur.fetchone():
                    # Create a minimal skeleton table with primary key, timestamps, and soft delete columns
                    pk_type = 'INTEGER' if pk == 'id' else 'TEXT'
                    create_sql = f"""
                        CREATE TABLE IF NOT EXISTS {table} (
                            {pk} {pk_type} PRIMARY KEY,
                            created_at REAL DEFAULT 0,
                            updated_at REAL DEFAULT 0,
                            deleted INTEGER DEFAULT 0,
                            deleted_at REAL DEFAULT 0
                        )
                    """
                    cur.execute(create_sql)
                    conn.commit()
                    print(f"[SCHEMA_PROVISION] Created skeleton table: {table} ({pk})")
                else:
                    # Ensure created_at/updated_at/deleted/deleted_at exist
                    cur.execute(f"PRAGMA table_info({table})")
                    cols = {r[1] for r in cur.fetchall()}
                    altered = False
                    if 'created_at' not in cols:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN created_at REAL DEFAULT 0")
                        altered = True
                    if 'updated_at' not in cols:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN updated_at REAL DEFAULT 0")
                        altered = True
                    if 'deleted' not in cols:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN deleted INTEGER DEFAULT 0")
                        altered = True
                    if 'deleted_at' not in cols:
                        cur.execute(f"ALTER TABLE {table} ADD COLUMN deleted_at REAL DEFAULT 0")
                        altered = True
                    if altered:
                        conn.commit()
                        print(f"[SCHEMA_PROVISION] Added timestamp/soft-delete columns to: {table}")

                # Create simple triggers to set timestamps when missing. Use AFTER triggers
                # with WHEN clauses so they are idempotent and avoid infinite loops.
                trg_ins = f"trg_{table}_set_created_at"
                trg_upd = f"trg_{table}_set_updated_at"

                # Drop existing INSERT trigger if it exists (might have old schema)
                try:
                    cur.execute(f"DROP TRIGGER IF EXISTS {trg_ins}")
                except:
                    pass
                
                cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (trg_ins,))
                if not cur.fetchone():
                    try:
                        # Create AFTER INSERT trigger with simpler logic
                        # Use COALESCE to handle NULL/0 cases cleanly
                        cur.execute(f"""
                            CREATE TRIGGER {trg_ins}
                            AFTER INSERT ON {table}
                            FOR EACH ROW
                            WHEN NEW.created_at IS NULL OR NEW.created_at = 0 OR NEW.updated_at IS NULL OR NEW.updated_at = 0
                            BEGIN
                                UPDATE {table} SET
                                    created_at = COALESCE(NULLIF(NEW.created_at, 0), strftime('%s','now')),
                                    updated_at = COALESCE(NULLIF(NEW.updated_at, 0), strftime('%s','now'))
                                WHERE {pk} = NEW.{pk};
                            END;
                        """)
                        conn.commit()
                        print(f"[SCHEMA_PROVISION] Created trigger: {trg_ins} for {table}")
                    except Exception as e:
                        print(f"[SCHEMA_PROVISION] Warning: Failed to create INSERT trigger for {table}: {e}")
                        pass

                # Drop existing UPDATE trigger if it exists (might have old schema)
                try:
                    cur.execute(f"DROP TRIGGER IF EXISTS {trg_upd}")
                except:
                    pass
                
                cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (trg_upd,))
                if not cur.fetchone():
                    try:
                        # Check if table has 'deleted' column to avoid referencing non-existent columns
                        cur.execute(f"PRAGMA table_info({table})")
                        cols = {r[1] for r in cur.fetchall()}
                        has_deleted = 'deleted' in cols
                        has_deleted_at = 'deleted_at' in cols
                        
                        # Create UPDATE trigger - only fires if updated_at/created_at CHANGED
                        # This prevents recursive firing when INSERT trigger sets timestamps
                        # Key: Check OLD.updated_at != NEW.updated_at to avoid recursion
                        if has_deleted and has_deleted_at:
                            # Full trigger with deleted handling
                            cur.execute(f"""
                                CREATE TRIGGER {trg_upd}
                                AFTER UPDATE ON {table}
                                FOR EACH ROW
                                WHEN (OLD.updated_at IS DISTINCT FROM NEW.updated_at AND (NEW.updated_at IS NULL OR NEW.updated_at = 0))
                                BEGIN
                                    UPDATE {table} SET
                                        updated_at = strftime('%s','now')
                                    WHERE {pk} = NEW.{pk};
                                END;
                            """)
                        else:
                            # Simplified trigger - only update updated_at when it's NULL/0 and changed
                            cur.execute(f"""
                                CREATE TRIGGER {trg_upd}
                                AFTER UPDATE ON {table}
                                FOR EACH ROW
                                WHEN (OLD.updated_at IS DISTINCT FROM NEW.updated_at AND (NEW.updated_at IS NULL OR NEW.updated_at = 0))
                                BEGIN
                                    UPDATE {table} SET
                                        updated_at = strftime('%s','now')
                                    WHERE {pk} = NEW.{pk};
                                END;
                            """)
                        conn.commit()
                        print(f"[SCHEMA_PROVISION] Created trigger: {trg_upd} for {table}")
                    except Exception as e:
                        print(f"[SCHEMA_PROVISION] Warning: Failed to create UPDATE trigger for {table}: {e}")
                        pass

                # Cleanup legacy datetime('now') triggers that set ISO timestamps
                # These older triggers (e.g., *_ts_ai, *_ts_au) write human-readable
                # timestamps like datetime('now'). They interfere with our epoch-based
                # triggers. Best-effort: drop triggers that update created_at/updated_at
                # using datetime('now'). This is conservative and only targets
                # triggers that contain the pattern.
                try:
                    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='trigger' AND tbl_name=?", (table,))
                    for name, sql in cur.fetchall():
                        if sql and "datetime('now')" in sql and ("created_at" in sql or "updated_at" in sql):
                            try:
                                cur.execute(f"DROP TRIGGER IF EXISTS {name}")
                                print(f"[SCHEMA_PROVISION] Removed legacy trigger: {name} for {table}")
                            except Exception:
                                pass
                except Exception:
                    pass

                # Recreate tombstone trigger (epoch) if sync_tombstones table exists
                try:
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sync_tombstones'")
                    if cur.fetchone():
                        tomb_trigger = f"trg_{table}_tombstone"
                        cur.execute("SELECT name FROM sqlite_master WHERE type='trigger' AND name=?", (tomb_trigger,))
                        if not cur.fetchone():
                            try:
                                cur.execute(f"CREATE TRIGGER {tomb_trigger} AFTER DELETE ON {table} BEGIN INSERT OR REPLACE INTO sync_tombstones(table_name, pk_value, deleted_at) VALUES ('{table}', CAST(OLD.{pk} AS TEXT), (strftime('%s','now'))); END;")
                                conn.commit()
                                print(f"[SCHEMA_PROVISION] Created tombstone trigger: {tomb_trigger} for {table}")
                            except Exception:
                                pass
                except Exception:
                    pass

            except Exception as e:
                print(f"[SCHEMA_PROVISION] Warning for table {table}: {e}")
        # Final commit
        conn.commit()
    finally:
        conn.close()


if __name__ == '__main__':
    print("[SCHEMA_PROVISION] Running as script – ensuring schema is ready")
    ensure_schema_ready()
