"""
Sync Service
===========
Modern sync service that follows the current service-oriented architecture.
Handles synchronization using services and repositories instead of direct SQL.
"""
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json
import sqlite3  # Module-level for type hints; re-imported in functions to get shimmed version
import os
from contextlib import contextmanager

from app.core.path_manager import get_db_path, get_data_dir

class SyncResult:
    """Result object for sync operations."""
    def __init__(self, success: bool, message: str, errors: List[str] = None):
        self.success = success
        self.message = message
        self.errors = errors or []

class SyncService:
    """Service for managing database synchronization using current architecture."""
    
    # SYNC VERSION - Increment this when sync logic changes significantly
    # Version 2: After Bug #7, #8, #9 fixes (Oct 18, 2025)
    CURRENT_SYNC_VERSION = 2
    
    def __init__(self):
        """Initialize the sync service."""
        self.computer_id = self._get_computer_id()
        self.sync_db_path = self._get_sync_db_path()
        self._ensure_sync_tables()
        self._check_sync_version()  # NEW: Check if full sync needed
        
        # Table-specific primary key mappings for sync
        self.table_pk_map = {
            # Core business tables
            'fournisseurs': 'code_fournisseur',
            'clients': 'code_client', 
            'products': 'code',  # FIXED: was 'reference', actual PK is 'code'
            
            # Transaction tables
            'achats': 'id',
            'ventes': 'nfacture',  # FIXED: was 'id', actual PK is 'nfacture'
            'factures': 'id',
            'devis': 'id',
            'devis_items': 'id',
            'paiements_factures': 'id',
            'retenus': 'id',
            'bon_livraison': 'id',
            'bon_livraison_avoirs': 'id',
            'bon_livraison_factures': 'id',
            
            # Financial tables
            'transactions_bancaires': 'id',  # CRITICAL FIX: was 'bank_transactions', actual table is 'transactions_bancaires'
            'banques': 'id',
            'caisse_transactions': 'id',
            'cheques': 'id',
            'cheque_config': 'id',
            'cheque_print_layout': 'id',
            
            # Configuration tables
            'avoir_applications': 'id',
            'avoir_config': 'id',
            'payment_methods': 'key',
            'application_settings': 'id',
            'settings': 'id',
            
            # Ciment (cement) tables
            'ciment_facture_bls': 'id',  # Junction table for facture-BL relationships
            'ciment_factures': 'id',
            'ciment_notif_sent': 'id',
            
            # Chantier (construction site) tables
            'chantier_remises': 'id',
            
            # Materials and monthly avoir
            'materials': 'id',
            'monthly_avoir_factures': 'id',
            'monthly_avoir_tracking': 'id',
            
            # Document management tables
            'documents': 'id',
            'document_folders': 'id',
            'document_permissions': 'id',
            'document_access_log': 'id',
            'document_downloads': 'id',
            
            # System tables
            'voitures': 'id',
            'users': 'id',
            'user_sessions': 'id',
            'system_permissions': 'id',
            'system_rank_permissions': 'id',
            'ranks': 'id',
            'rank_permissions': 'id',
            'permissions': 'id',
            'permission_types': 'id',
            'activity_logs': 'id',
            'calendar_events': 'id',
            # NOTE: sync_tombstones should NOT be synced - they're created locally by DELETE triggers
            # 'sync_tombstones': 'rowid',  # REMOVED: Causes duplicates on server
            'sync_metadata': 'key'
        }
    
    def _get_computer_id(self) -> str:
        """Get unique computer identifier."""
        import platform
        import getpass
        return getpass.getuser()  # Use current username as computer ID
    
    def _get_sync_db_path(self) -> str:
        """Get path to sync tracking database."""
        data_dir = get_data_dir()
        return os.path.join(data_dir, "sync_tracking.db")
    
    @contextmanager
    def get_sync_connection(self):
        """Get connection to sync tracking database."""
        import sqlite3  # Import here to ensure DB_SHIM is applied
        conn = sqlite3.connect(self.sync_db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    @contextmanager  
    def get_main_connection(self):
        """Get connection to main database."""
        import sqlite3  # Import here to ensure DB_SHIM is applied
        conn = sqlite3.connect(get_db_path())
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def _ensure_sync_tables(self):
        """Ensure sync tracking tables exist."""
        # Use file logging since print() doesn't work in frozen EXEs
        log_file = os.path.join(os.environ.get('LOCALAPPDATA', '.'), 'STFOOM', 'data', 'sync_debug.log')
        try:
            os.makedirs(os.path.dirname(log_file), exist_ok=True)
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"\n{'='*60}\n")
                f.write(f"[{datetime.now().isoformat()}] _ensure_sync_tables called\n")
                f.write(f"  sync_db_path: {self.sync_db_path}\n")
                f.flush()
        except:
            pass
        
        print(f"[SYNC_SERVICE][DEBUG] _ensure_sync_tables called, sync_db_path={self.sync_db_path}")
        
        try:
            with self.get_sync_connection() as conn:
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  Connection opened successfully\n")
                        f.flush()
                except:
                    pass
                print(f"[SYNC_SERVICE][DEBUG] Connection opened to {self.sync_db_path}")
                
                # Note: legacy queue-based sync_changes removed. We now use timestamp-based deltas
                # so there is no persistent per-change queue in this DB.
                # sync_status table
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_status (
                        computer_id TEXT PRIMARY KEY,
                        last_sync REAL,
                        last_successful_sync REAL,
                        sync_errors INTEGER DEFAULT 0,
                        total_synced INTEGER DEFAULT 0
                    )
                ''')
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  sync_status table created/verified\n")
                        f.flush()
                except:
                    pass
                print("[SYNC_SERVICE][DEBUG] sync_status table created/verified")
                
                # sync_metadata table - NEW: Track sync version and force full sync flag
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at REAL NOT NULL
                    )
                ''')
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  sync_metadata table created/verified\n")
                        f.flush()
                except:
                    pass
                print("[SYNC_SERVICE][DEBUG] sync_metadata table created/verified")

                # sync_errors: record skipped/failed change metadata for operator review
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS sync_errors (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        change_id INTEGER,
                        table_name TEXT,
                        record_id TEXT,
                        error TEXT,
                        timestamp REAL
                    )
                ''')
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  sync_errors table created/verified\n")
                        f.flush()
                except:
                    pass
                print("[SYNC_SERVICE][DEBUG] sync_errors table created/verified")
                
                conn.commit()
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  Tables committed\n")
                        f.flush()
                except:
                    pass
                print("[SYNC_SERVICE][DEBUG] Tables committed")
                
                # Initialize force_full_sync flag on first run
                # This ensures a brand new installation pulls all server data
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM sync_metadata WHERE key = 'force_full_sync'")
                count = cursor.fetchone()[0]
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  force_full_sync record count: {count}\n")
                        f.flush()
                except:
                    pass
                print(f"[SYNC_SERVICE][DEBUG] force_full_sync record count: {count}")
                
                if count == 0:
                    # First time setup - set force_full_sync to trigger initial full sync
                    from datetime import datetime
                    cursor.execute('''
                        INSERT INTO sync_metadata (key, value, updated_at)
                        VALUES ('force_full_sync', '1', ?)
                    ''', (datetime.now().timestamp(),))
                    conn.commit()
                    try:
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write(f"  **FIRST RUN** - force_full_sync set to '1'\n")
                            f.flush()
                    except:
                        pass
                    print("[SYNC_SERVICE] First run detected - force_full_sync flag set to '1'")
                else:
                    # Show current value
                    cursor.execute("SELECT value FROM sync_metadata WHERE key = 'force_full_sync'")
                    value = cursor.fetchone()[0]
                    try:
                        with open(log_file, 'a', encoding='utf-8') as f:
                            f.write(f"  force_full_sync already exists, value='{value}'\n")
                            f.flush()
                    except:
                        pass
                    print(f"[SYNC_SERVICE][DEBUG] force_full_sync already exists, value='{value}'")
                
                try:
                    with open(log_file, 'a', encoding='utf-8') as f:
                        f.write(f"  _ensure_sync_tables completed successfully\n")
                        f.flush()
                except:
                    pass
                print("[SYNC_SERVICE][DEBUG] _ensure_sync_tables completed successfully")
        except Exception as e:
            try:
                with open(log_file, 'a', encoding='utf-8') as f:
                    f.write(f"  **ERROR**: {e}\n")
                    import traceback
                    f.write(traceback.format_exc())
                    f.flush()
            except:
                pass
            print(f"[SYNC_SERVICE][ERROR] _ensure_sync_tables failed: {e}")
            import traceback
            traceback.print_exc()
            raise
            
            # Ensure expected columns exist for backward compatibility
            try:
                # Check sync_status for missing columns
                cols = conn.execute("PRAGMA table_info(sync_status)").fetchall()
                col_names = {c[1] for c in cols}
                if 'last_successful_sync' not in col_names:
                    conn.execute("ALTER TABLE sync_status ADD COLUMN last_successful_sync REAL")
                if 'sync_errors' not in col_names:
                    conn.execute("ALTER TABLE sync_status ADD COLUMN sync_errors INTEGER DEFAULT 0")
                if 'total_synced' not in col_names:
                    conn.execute("ALTER TABLE sync_status ADD COLUMN total_synced INTEGER DEFAULT 0")
                conn.commit()
            except Exception:
                # Best effort; ignore if ALTER not supported or already done
                pass

    def _log_sync_error(self, change_id: int | None, table_name: str, record_id: str, error: str):
        """Persist a short record about skipped or failed change for later inspection."""
        try:
            with self.get_sync_connection() as conn:
                conn.execute('''
                    INSERT INTO sync_errors (change_id, table_name, record_id, error, timestamp)
                    VALUES (?, ?, ?, ?, ?)
                ''', (change_id, table_name, record_id, str(error), datetime.now().timestamp()))
                conn.commit()
        except Exception:
            # Don't let logging errors break sync
            pass

    # --- Deprecated queue API compatibility ---------------------------------
    def add_sync_change(self, table_name: str, record_id: str, data: Dict[str, Any], operation: str):
        """
        Compatibility helper: stamp timestamps on the target record instead of
        using a persistent per-change queue.

        This updates the main database record to ensure `created_at`, `updated_at`
        and `deleted_at` (when available) are set as epoch seconds. Callers that
        previously queued changes should continue to call this method — it will
        now mark the row as changed so the timestamp-based scanner picks it up.

        operation: 'insert'|'update'|'delete'
        """
        try:
            now = datetime.now().timestamp()
            with self.get_main_connection() as conn:
                # Ensure table exists
                try:
                    conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
                except sqlite3.OperationalError:
                    # Table doesn't exist locally; nothing to stamp
                    return

                # Determine primary key
                pk = self.table_pk_map.get(table_name)
                if not pk:
                    pk = self._get_table_primary_key(table_name, conn)

                # Inspect columns
                cols = {r[1] for r in conn.execute(f"PRAGMA table_info({table_name})").fetchall()}

                if operation in ('insert', 'update'):
                    # If record exists, update its updated_at (and created_at if missing on insert)
                    exists = conn.execute(f"SELECT 1 FROM {table_name} WHERE {pk} = ?", (record_id,)).fetchone()
                    if exists:
                        sets = []
                        params = []
                        if 'updated_at' in cols:
                            sets.append('updated_at = ?')
                            params.append(now)
                        if sets:
                            sql = f"UPDATE {table_name} SET {', '.join(sets)} WHERE {pk} = ?"
                            conn.execute(sql, (*params, record_id))
                            conn.commit()
                            return

                    # Record does not exist -> try to INSERT a minimal row so it's visible to sync
                    insert_cols = [pk]
                    insert_vals = [record_id]
                    if 'created_at' in cols:
                        insert_cols.append('created_at'); insert_vals.append(now)
                    if 'updated_at' in cols:
                        insert_cols.append('updated_at'); insert_vals.append(now)
                    placeholders = ','.join(['?'] * len(insert_vals))
                    sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(insert_cols)}) VALUES ({placeholders})"
                    try:
                        conn.execute(sql, insert_vals)
                        conn.commit()
                    except Exception:
                        # If insert fails (schema constraints), fall back to best-effort update of timestamps
                        try:
                            sets = []
                            params = []
                            if 'updated_at' in cols:
                                sets.append('updated_at = ?'); params.append(now)
                            if 'created_at' in cols:
                                sets.append('created_at = ?'); params.append(now)
                            if sets:
                                sql = f"UPDATE {table_name} SET {', '.join(sets)} WHERE {pk} = ?"
                                conn.execute(sql, (*params, record_id))
                                conn.commit()
                        except Exception:
                            pass

                elif operation == 'delete':
                    # Prefer soft-delete (deleted_at) when available
                    if 'deleted_at' in cols:
                        sets = ['deleted_at = ?', 'updated_at = ?'] if 'updated_at' in cols else ['deleted_at = ?']
                        params = [now, now] if 'updated_at' in cols else [now]
                        sql = f"UPDATE {table_name} SET {', '.join(sets)} WHERE {pk} = ?"
                        try:
                            conn.execute(sql, (*params, record_id))
                            conn.commit()
                        except Exception:
                            # Fallback to hard delete if updating deleted_at fails
                            try:
                                conn.execute(f"DELETE FROM {table_name} WHERE {pk} = ?", (record_id,))
                                conn.commit()
                            except Exception:
                                pass
                    else:
                        # No deleted_at column: perform hard delete
                        try:
                            conn.execute(f"DELETE FROM {table_name} WHERE {pk} = ?", (record_id,))
                            conn.commit()
                        except Exception:
                            pass
        except Exception as e:
            print(f"[SYNC_SERVICE] Error stamping timestamps for {table_name}:{record_id}: {e}")

    def get_pending_changes(self) -> List[Dict[str, Any]]:
        """Compatibility shim: return empty list (no queue)."""
        return []

    def mark_change_synced(self, change_id: int):
        """Compatibility shim: no-op for legacy queue marking."""
        return
    
    def _check_sync_version(self):
        """Check if sync version has changed and set force_full_sync flag if needed."""
        with self.get_sync_connection() as conn:
            cursor = conn.cursor()
            
            # Get current stored version
            cursor.execute("SELECT value FROM sync_metadata WHERE key = 'sync_version'")
            row = cursor.fetchone()
            
            stored_version = int(row[0]) if row else 0
            
            if stored_version < self.CURRENT_SYNC_VERSION:
                print(f"[SYNC_SERVICE] Sync version upgraded: {stored_version} -> {self.CURRENT_SYNC_VERSION}")
                print(f"[SYNC_SERVICE] Will perform FULL SYNC on next sync cycle")
                
                # Set force_full_sync flag
                cursor.execute('''
                    INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                    VALUES ('force_full_sync', '1', ?)
                ''', (datetime.now().timestamp(),))
                
                # Update version
                cursor.execute('''
                    INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                    VALUES ('sync_version', ?, ?)
                ''', (str(self.CURRENT_SYNC_VERSION), datetime.now().timestamp()))
                
                conn.commit()
                
    def _should_force_full_sync(self) -> bool:
        """Check if we should force a full sync (ignore timestamps)."""
        try:
            with self.get_sync_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT value FROM sync_metadata WHERE key = 'force_full_sync'")
                row = cursor.fetchone()
                result = row and row[0] == '1'
                print(f"[SYNC_SERVICE][DEBUG] _should_force_full_sync: Force full sync = {result}")
                return result
        except Exception as e:
            print(f"[SYNC_SERVICE][DEBUG] _should_force_full_sync: Error checking force full sync: {e}")
            return False
    
    def _clear_force_full_sync(self):
        """Clear the force_full_sync flag after completing full sync."""
        with self.get_sync_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
                VALUES ('force_full_sync', '0', ?)
            ''', (datetime.now().timestamp(),))
            conn.commit()
            print("[SYNC_SERVICE] Full sync completed, returning to incremental sync")
    
    # Legacy queue-based per-change table removed. Use timestamp-based scanning.
    
    def apply_change_to_database(self, table_name: str, record_id: str, data: Dict[str, Any], operation: str, db_path: str) -> bool:
        """
        Apply a sync change to a database using modern architecture.
        
        Args:
            table_name: Table to modify
            record_id: Record ID
            data: Data to apply
            operation: Operation type (insert, update, delete)
            db_path: Path to target database
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Use direct SQL with proper parameterization (modern approach)
            conn = sqlite3.connect(db_path)
            conn.row_factory = sqlite3.Row
            
            try:
                # Get the correct primary key for this table
                primary_key = self._get_table_primary_key(table_name, conn)
                
                # Get valid columns for target table to filter out unknown fields
                try:
                    col_rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                    valid_columns = {row[1] for row in col_rows}
                except Exception:
                    valid_columns = set()
                
                # Filter provided data to only include columns that exist on target DB
                filtered_data = {k: v for k, v in (data or {}).items() if k in valid_columns}
                
                if operation == 'insert':
                    # If no valid columns remain (schema mismatch), skip as success
                    if not filtered_data:
                        return True
                    # Check required NOT NULL columns; if missing, skip to avoid constraint errors
                    required_cols = set()
                    try:
                        # PRAGMA: (cid, name, type, notnull, dflt_value, pk)
                        for row in col_rows:
                            name, notnull, dflt, pk = row[1], row[3], row[4], row[5]
                            if notnull == 1 and pk == 0 and dflt is None:
                                required_cols.add(name)
                    except Exception:
                        pass
                    if required_cols and not required_cols.issubset(set(filtered_data.keys())):
                        # Missing required fields for a safe insert; skip
                        return True
                    # Build parameterized INSERT with conflict handling
                    columns = list(filtered_data.keys())
                    placeholders = ['?' for _ in columns]
                    values = [filtered_data[col] for col in columns]
                    sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                    try:
                        conn.execute(sql, values)
                    except sqlite3.IntegrityError as ie:
                        msg = str(ie).lower()
                        # Treat common constraint violations as non-fatal (skip)
                        if any(k in msg for k in ("not null", "unique", "check", "foreign key")):
                                print(f"[SYNC_SERVICE] Integrity constraint when inserting {table_name}:{record_id}, skipping: {ie}")
                                try:
                                    # Record the skipped change for operator review
                                    self._log_sync_error(None, table_name, record_id, f"insert: {ie}")
                                except Exception:
                                    pass
                                return True
                        raise
                    except sqlite3.OperationalError as oe:
                        msg = str(oe)
                        if "no column named" in msg or "NOT NULL constraint failed" in msg:
                            # Treat as no-op success to avoid blocking queue on schema mismatch
                            return True
                        raise
                
                elif operation == 'update':
                    # If nothing valid to update (e.g., only unknown fields), treat as success
                    if not filtered_data:
                        return True
                    # Build parameterized UPDATE with correct primary key
                    set_clauses = [f"{col} = ?" for col in filtered_data.keys()]
                    values = list(filtered_data.values()) + [record_id]
                    sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {primary_key} = ?"
                    try:
                        result = conn.execute(sql, values)
                    except sqlite3.IntegrityError as ie:
                        msg = str(ie).lower()
                        if any(k in msg for k in ("not null", "unique", "check", "foreign key")):
                            print(f"[SYNC_SERVICE] Integrity constraint when updating {table_name}:{record_id}, skipping: {ie}")
                            try:
                                self._log_sync_error(None, table_name, record_id, f"update: {ie}")
                            except Exception:
                                pass
                            return True
                        raise
                    except sqlite3.OperationalError as oe:
                        msg = str(oe)
                        if "no column named" in msg:
                            return True
                        raise
                    
                    # CRITICAL FIX: If no rows were updated, record doesn't exist on server - INSERT it!
                    if result.rowcount == 0:
                        # Record doesn't exist, do an INSERT instead
                        print(f"[SYNC_SERVICE] Record {table_name}:{record_id} doesn't exist on server, inserting...")
                        columns = list(filtered_data.keys())
                        placeholders = ['?' for _ in columns]
                        values_insert = [filtered_data[col] for col in columns]
                        sql_insert = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                        try:
                            conn.execute(sql_insert, values_insert)
                            print(f"[SYNC_SERVICE] Successfully inserted {table_name}:{record_id} to server")
                        except sqlite3.OperationalError as oe:
                            msg = str(oe)
                            if "no column named" in msg or "NOT NULL constraint failed" in msg:
                                # Schema mismatch, treat as success to unblock queue
                                print(f"[SYNC_SERVICE] Schema mismatch for {table_name}:{record_id}, skipping")
                                return True
                            raise
                
                elif operation == 'delete':
                    # Use soft delete if available (same logic as push to server)
                    now = datetime.now().timestamp()
                    
                    # Check if table has soft delete columns
                    has_deleted = 'deleted' in valid_columns
                    has_deleted_at = 'deleted_at' in valid_columns
                    has_updated_at = 'updated_at' in valid_columns
                    
                    if has_deleted or has_deleted_at:
                        # Perform soft delete
                        sets = []
                        params = []
                        
                        if has_deleted:
                            sets.append('deleted = ?')
                            params.append(1)
                        
                        if has_deleted_at:
                            sets.append('deleted_at = ?')
                            params.append(now)
                        
                        if has_updated_at:
                            sets.append('updated_at = ?')
                            params.append(now)
                        
                        sql = f"UPDATE {table_name} SET {', '.join(sets)} WHERE {primary_key} = ?"
                        params.append(record_id)
                        
                        try:
                            conn.execute(sql, params)
                        except sqlite3.IntegrityError as ie:
                            msg = str(ie).lower()
                            if any(k in msg for k in ("foreign key", "check", "unique")):
                                print(f"[SYNC_SERVICE] Integrity constraint when soft-deleting {table_name}:{record_id}, skipping: {ie}")
                                try:
                                    self._log_sync_error(None, table_name, record_id, f"delete: {ie}")
                                except Exception:
                                    pass
                                return True
                            raise
                        except sqlite3.OperationalError as oe:
                            msg = str(oe)
                            if "no such column" in msg:
                                return True
                            raise
                    else:
                        # No soft delete columns: perform hard delete
                        sql = f"DELETE FROM {table_name} WHERE {primary_key} = ?"
                        try:
                            conn.execute(sql, (record_id,))
                        except sqlite3.IntegrityError as ie:
                            msg = str(ie).lower()
                            if any(k in msg for k in ("foreign key", "check", "unique")):
                                print(f"[SYNC_SERVICE] Integrity constraint when deleting {table_name}:{record_id}, skipping: {ie}")
                                try:
                                    self._log_sync_error(None, table_name, record_id, f"delete: {ie}")
                                except Exception:
                                    pass
                                return True
                            raise
                        except sqlite3.OperationalError as oe:
                            msg = str(oe)
                            if "no such column" in msg:
                                return True
                            raise
                
                conn.commit()
                return True
                
            finally:
                conn.close()
                
        except Exception as e:
            print(f"[SYNC_SERVICE] Error applying change to {table_name} (record_id: {record_id}): {e}")
            return False
    
    def _get_table_primary_key(self, table_name: str, conn) -> str:
        """Get the primary key field for a table."""
        try:
            cursor = conn.cursor()
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = cursor.fetchall()

            # Look for primary key column
            for column in columns:
                # pk flag is at index 5 in PRAGMA table_info
                if column[5] == 1:
                    return column[1]

            # Fallback to configured mapping
            return self.table_pk_map.get(table_name, 'id')  # default to 'id'
        except Exception as e:
            print(f"[SYNC_SERVICE] Error getting primary key for {table_name}: {e}")
            return 'id'  # fallback
    
    def update_sync_status(self, success: bool, synced_count: int = 0, errors: int = 0):
        """Update sync status after sync operation."""
        try:
            with self.get_sync_connection() as conn:
                now = datetime.now().timestamp()
                
                # Get current status
                current = conn.execute(
                    "SELECT sync_errors, total_synced, last_successful_sync FROM sync_status WHERE computer_id = ?",
                    (self.computer_id,)
                ).fetchone()
                
                if current:
                    new_errors = current['sync_errors'] + errors if not success else 0
                    new_total = current['total_synced'] + synced_count
                    
                    conn.execute('''
                        UPDATE sync_status 
                        SET last_sync = ?, last_successful_sync = ?, sync_errors = ?, total_synced = ?
                        WHERE computer_id = ?
                    ''', (now, now if success else current['last_successful_sync'], new_errors, new_total, self.computer_id))
                else:
                    conn.execute('''
                        INSERT INTO sync_status (computer_id, last_sync, last_successful_sync, sync_errors, total_synced)
                        VALUES (?, ?, ?, ?, ?)
                    ''', (self.computer_id, now, now if success else None, errors if not success else 0, synced_count))
                
                conn.commit()
        except Exception as e:
            print(f"[SYNC_SERVICE] Error updating sync status: {e}")

    def _get_last_successful_sync(self) -> float:
        """Return last successful sync timestamp for this computer (0 if none)."""
        try:
            with self.get_sync_connection() as conn:
                row = conn.execute("SELECT last_successful_sync FROM sync_status WHERE computer_id = ?", (self.computer_id,)).fetchone()
                if row and row['last_successful_sync']:
                    return float(row['last_successful_sync'])
        except Exception:
            pass
        return 0.0

    def _get_local_changes_since(self, last_sync: float) -> List[Dict[str, Any]]:
        """Scan local DB tables and return list of change dicts since last_sync.

        Each change dict: {'table': str, 'record_id': str, 'data': dict, 'operation': 'insert'|'update'|'delete'}
        """
        changes: List[Dict[str, Any]] = []
        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Scanning for changes since {last_sync} ({datetime.fromtimestamp(last_sync) if last_sync > 0 else 'never'})")
        try:
            dbp = get_db_path()
            server_db_path = self.get_server_db_path()
            
            with sqlite3.connect(dbp) as local_conn, sqlite3.connect(server_db_path) as server_conn:
                local_conn.row_factory = sqlite3.Row
                server_conn.row_factory = sqlite3.Row
                
                for table, pk in self.table_pk_map.items():
                    try:
                        # Ensure table exists locally
                        try:
                            local_conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                        except sqlite3.OperationalError:
                            continue

                        # Ensure table exists on server
                        try:
                            server_conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone()
                        except sqlite3.OperationalError:
                            continue

                        # Inspect columns
                        cols = local_conn.execute(f"PRAGMA table_info({table})").fetchall()
                        col_names = [c[1] for c in cols]
                        has_updated = 'updated_at' in col_names
                        has_created = 'created_at' in col_names
                        has_deleted = 'deleted_at' in col_names or 'deleted' in col_names

                        # Build timestamp expression preference
                        ts_cols = []
                        if has_updated:
                            ts_cols.append('updated_at')
                        if has_created:
                            ts_cols.append('created_at')
                        if has_deleted:
                            ts_cols.append('deleted_at' if 'deleted_at' in col_names else 'updated_at')

                        if not ts_cols:
                            # No timestamps, skip table
                            print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Skipping {table} - no timestamp columns")
                            continue

                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Checking {table} with timestamp cols: {ts_cols}")

                        # Build a robust timestamp expression that handles numeric epoch
                        # and text ISO timestamps (strftime handles parsing text dates).
                        def ts_expr(col_name: str) -> str:
                            # If text contains only digits (epoch stored as text), cast directly.
                            return (
                                f"(CASE WHEN typeof({col_name}) = 'text' AND {col_name} GLOB '[0-9]*' THEN CAST({col_name} AS REAL) "
                                f"WHEN typeof({col_name}) = 'text' THEN CAST(strftime('%s', {col_name}) AS REAL) ELSE {col_name} END)"
                            )

                        # First, find records that have been modified since last_sync
                        where_clauses = [f"({ts_expr(col)} > ?)" for col in ts_cols]
                        sql_modified = f"SELECT * FROM {table} WHERE {' OR '.join(where_clauses)}"
                        params = tuple([last_sync] * len(ts_cols))
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Query for modified {table}: {sql_modified} with params {params}")
                        modified_rows = local_conn.execute(sql_modified, params).fetchall()
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Found {len(modified_rows)} modified records in {table}")

                        # Second, find records that exist locally but not on server (regardless of timestamps)
                        # This handles records created before last_sync that were never synced
                        if pk == 'rowid':
                            # For tables using rowid as primary key, explicitly select it
                            sql_missing = f"SELECT rowid, * FROM {table}"
                        else:
                            sql_missing = f"SELECT * FROM {table}"
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Getting all local {table} records to check against server")
                        all_local_rows = local_conn.execute(sql_missing).fetchall()
                        missing_rows = []
                        
                        # Check each local record against server
                        for row in all_local_rows:
                            record_id = row[pk]
                            # Check if this record exists on server
                            server_cursor = server_conn.cursor()
                            server_cursor.execute(f"SELECT 1 FROM {table} WHERE {pk} = ?", (record_id,))
                            exists_on_server = server_cursor.fetchone() is not None
                            
                            if not exists_on_server:
                                missing_rows.append(row)
                        
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Found {len(missing_rows)} missing records in {table}")

                        # Combine both sets of rows
                        all_rows = modified_rows + missing_rows
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Total potential changes in {table}: {len(all_rows)}")

                        for r in all_rows:
                            rec = dict(r)
                            record_id = rec.get(pk)
                            if record_id is None:
                                continue
                            
                            # Helper function to normalize timestamp for comparison
                            def normalize_timestamp(ts_val):
                                """Convert timestamp to float for comparison."""
                                if ts_val is None:
                                    return None
                                if isinstance(ts_val, (int, float)):
                                    return float(ts_val)
                                if isinstance(ts_val, str):
                                    # Try to parse as Unix timestamp first
                                    try:
                                        if ts_val.replace('.', '').isdigit():
                                            return float(ts_val)
                                    except:
                                        pass
                                    # Try to parse as ISO timestamp
                                    try:
                                        import datetime
                                        dt = datetime.datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                        return dt.timestamp()
                                    except:
                                        pass
                                return None
                            
                            # Determine operation: delete if deleted_at exists and > last_sync or deleted flag
                            op = 'update'
                            deleted_at_ts = normalize_timestamp(rec.get('deleted_at'))
                            if deleted_at_ts and deleted_at_ts > last_sync:
                                op = 'delete'
                            elif rec.get('deleted') == 1:
                                updated_at_ts = normalize_timestamp(rec.get('updated_at'))
                                if updated_at_ts and updated_at_ts > last_sync:
                                    op = 'delete'

                            # Filter out internal-only columns (like large blobs if desired) — we'll send everything matching server schema later
                            changes.append({'table': table, 'record_id': str(record_id), 'data': rec, 'operation': op})
                            print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Added change {table}:{record_id} operation={op}")
                    except Exception as e:
                        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Error processing {table}: {e}")
                        continue
        except Exception as e:
            print(f"[SYNC_SERVICE] Error scanning local changes: {e}")
        print(f"[SYNC_SERVICE][DEBUG] _get_local_changes_since: Total changes found: {len(changes)}")
        return changes
    
    def _check_server_online(self) -> bool:
        """Check if sync server is online."""
        print("[SYNC_SERVICE] ========== _check_server_online() CALLED ==========")
        try:
            server_path = r"\\DESKTOP-BKIB183\data"
            print(f"[SYNC_SERVICE][DEBUG] _check_server_online: Checking server path: {server_path}")
            
            # Network paths fail with os.path.exists() in frozen EXE
            # Use listdir instead - more reliable for UNC paths
            try:
                os.listdir(server_path)
                print(f"[SYNC_SERVICE][DEBUG] _check_server_online: Server path ONLINE (listdir succeeded)")
                return True
            except (OSError, PermissionError) as e:
                print(f"[SYNC_SERVICE][DEBUG] _check_server_online: Server path OFFLINE: {e}")
                return False
        except Exception as e:
            print(f"[SYNC_SERVICE][DEBUG] _check_server_online: Error checking server: {e}")
            return False
    
    def get_server_db_path(self) -> str:
        """Get path to server database."""
        # Use configurable server path instead of hardcoded
        from app.connection import sync_config
        server_dir = sync_config.get_server_path()
        return os.path.join(server_dir, "stfoom.db")

    def _ensure_server_schema(self, server_db_path: str):
        """Ensure server DB has required columns to accept synced changes."""
        try:
            conn = sqlite3.connect(server_db_path)
            try:
                cur = conn.cursor()
                # Ensure achats has fournisseur_alias for 401000 display alias sync
                cur.execute("PRAGMA table_info(achats)")
                cols = {row[1] for row in cur.fetchall()}
                if 'fournisseur_alias' not in cols:
                    cur.execute("ALTER TABLE achats ADD COLUMN fournisseur_alias TEXT")
                    conn.commit()
                    print("[SYNC_SERVICE] Server schema: added achats.fournisseur_alias")
            finally:
                conn.close()
        except Exception as e:
            print(f"[SYNC_SERVICE] Server schema check failed: {e}")
    
    def sync_to_server(self) -> SyncResult:
        """
        Sync pending changes to server.
        
        Returns:
            SyncResult with success status, message, and any errors
        """
        import sqlite3  # Import here to ensure DB_SHIM is applied
        print("[SYNC_SERVICE][DEBUG] ########## sync_to_server() ENTERED ##########")
        # Legacy per-change queue removed; no per-change cleanup required here.

        # Timestamp-based push: find local records modified since the last successful sync
        print("[SYNC_SERVICE][DEBUG] About to call _get_last_successful_sync()...")
        last_sync = self._get_last_successful_sync()
        print(f"[SYNC_SERVICE][DEBUG] sync_to_server: Last successful sync: {last_sync} ({datetime.fromtimestamp(last_sync) if last_sync > 0 else 'never'})")

        server_db_path = self.get_server_db_path()
        if not self._check_server_online():
            return SyncResult(False, "Server offline", ["Server offline"])

        # Ensure server DB has expected schema for known recent migrations
        self._ensure_server_schema(server_db_path)

        local_changes = self._get_local_changes_since(last_sync)
        print(f"[SYNC_SERVICE][DEBUG] sync_to_server: Found {len(local_changes)} local changes to push")
        if not local_changes:
            # Nothing to push
            print("[SYNC_SERVICE][DEBUG] sync_to_server: No local changes to sync")
            return SyncResult(True, "No local changes to sync")

        synced_count = 0
        errors: List[str] = []

        # Build server schema cache
        try:
            server_conn = sqlite3.connect(server_db_path)
            server_conn.row_factory = sqlite3.Row
            
            # DEBUG: Check server DB state immediately after connecting
            print(f"[SYNC_SERVICE][CRITICAL] Connected to server DB: {server_db_path}")
            table_count = server_conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
            print(f"[SYNC_SERVICE][CRITICAL] Server has {table_count} tables")
            
            schema_cols: Dict[str, set] = {}
            def get_table_cols(table: str) -> set:
                if table not in schema_cols:
                    try:
                        rows = server_conn.execute(f"PRAGMA table_info({table})").fetchall()
                        schema_cols[table] = {r[1] for r in rows}
                        # DEBUG: Log schema for system_permissions
                        if table == 'system_permissions':
                            print(f"[SYNC_SERVICE][CRITICAL] PRAGMA table_info(system_permissions) returned {len(rows)} columns")
                            if len(rows) == 0:
                                print(f"[SYNC_SERVICE][CRITICAL] ❌ EMPTY SCHEMA! Checking if table exists...")
                                exists = server_conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='system_permissions'").fetchone()
                                print(f"[SYNC_SERVICE][CRITICAL] Table exists in sqlite_master? {exists is not None}")
                            else:
                                print(f"[SYNC_SERVICE][CRITICAL] ✓ Schema columns: {schema_cols[table]}")
                    except Exception as ex:
                        print(f"[SYNC_SERVICE][CRITICAL] ❌ Exception querying {table} schema: {ex}")
                        schema_cols[table] = set()
                return schema_cols[table]
        except Exception as e:
            return SyncResult(False, f"Could not open server DB: {e}", [str(e)])

        try:
            for change in local_changes:
                tbl = change.get('table')
                data = change.get('data') or {}
                op = change.get('operation', 'update')

                valid = get_table_cols(tbl)
                if not valid:
                    # table missing on server -> skip
                    continue

                # Filter keys to server schema
                filtered = {k: v for k, v in data.items() if k in valid}

                # Remove local-only fields
                if tbl == 'achats' and isinstance(filtered, dict):
                    filtered.pop('fournisseur_alias', None)

                # Track whether this change produced a real DB modification on server
                row_modified = False

                if op == 'delete':
                    # OPTION 3: Soft delete - mark deleted=1 instead of hard DELETE
                    # This preserves audit trail across all devices
                    primary_key = self._get_table_primary_key(tbl, server_conn)
                    try:
                        # Check if server table has 'deleted' and 'deleted_at' columns
                        server_cols = get_table_cols(tbl)
                        has_soft_delete = 'deleted' in server_cols and 'deleted_at' in server_cols
                        
                        if has_soft_delete:
                            # Soft delete: mark as deleted with timestamp
                            deleted_at = data.get('deleted_at') or datetime.now().timestamp()
                            sql = f"UPDATE {tbl} SET deleted = 1, deleted_at = ?, updated_at = ? WHERE {primary_key} = ?"
                            cur = server_conn.execute(sql, (deleted_at, deleted_at, change['record_id']))
                            row_modified = cur.rowcount > 0 if hasattr(cur, 'rowcount') else True
                            print(f"[SYNC_SERVICE][DEBUG] Soft deleted {tbl}:{change['record_id']} on server (deleted=1)")
                        else:
                            # Fallback: hard delete if table doesn't support soft delete
                            cur = server_conn.execute(f"DELETE FROM {tbl} WHERE {primary_key} = ?", (change['record_id'],))
                            row_modified = cur.rowcount > 0 if hasattr(cur, 'rowcount') else True
                            print(f"[SYNC_SERVICE][DEBUG] Hard deleted {tbl}:{change['record_id']} on server (no soft delete support)")
                    except Exception as e:
                        errors.append(f"delete {tbl}:{change['record_id']}: {e}")
                else:
                    try:
                        primary_key = self._get_table_primary_key(tbl, server_conn)

                        if filtered:
                            # Debug logging for system_permissions
                            if tbl == 'system_permissions' and synced_count < 10:
                                print(f"\n[SYNC_SERVICE][ERROR] ===== SYNC DEBUG #{synced_count + 1} =====")
                                print(f"[SYNC_SERVICE][ERROR] Table: {tbl}")
                                print(f"[SYNC_SERVICE][ERROR] Primary key: {primary_key}")
                                print(f"[SYNC_SERVICE][ERROR] Record ID from change: {change.get('record_id')}")
                                print(f"[SYNC_SERVICE][ERROR] Filtered data keys: {list(filtered.keys())}")
                                print(f"[SYNC_SERVICE][ERROR] Filtered['{primary_key}']: {filtered.get(primary_key)}")
                                print(f"[SYNC_SERVICE][ERROR] First 3 filtered items: {dict(list(filtered.items())[:3])}")
                            
                            # Check if record exists by primary key
                            pk_value = filtered.get(primary_key)
                            exists = False
                            if pk_value:
                                check = server_conn.execute(f"SELECT 1 FROM {tbl} WHERE {primary_key} = ?", (pk_value,)).fetchone()
                                exists = check is not None
                            
                            if exists:
                                # UPDATE existing record
                                set_clause = ', '.join([f"{col} = ?" for col in filtered.keys() if col != primary_key])
                                values = [filtered[col] for col in filtered.keys() if col != primary_key]
                                values.append(pk_value)
                                sql = f"UPDATE {tbl} SET {set_clause} WHERE {primary_key} = ?"
                                cur = server_conn.execute(sql, values)
                                row_modified = cur.rowcount > 0 if hasattr(cur, 'rowcount') else True
                            else:
                                # INSERT new record
                                columns = list(filtered.keys())
                                placeholders = ['?' for _ in columns]
                                values = [filtered[c] for c in columns]
                                sql = f"INSERT INTO {tbl} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
                                
                                # Debug: Log INSERT
                                if tbl == 'system_permissions' and synced_count < 10:
                                    print(f"[SYNC_SERVICE][ERROR] >>> INSERT SQL: {sql}")
                                    print(f"[SYNC_SERVICE][ERROR] >>> VALUES: {values}")
                                
                                cur = server_conn.execute(sql, values)
                                row_modified = cur.rowcount > 0 if hasattr(cur, 'rowcount') else True
                        else:
                            # No fields to send. Attempt a minimal insert using primary key (and timestamps if present) so a real row exists on server.
                            if primary_key in valid:
                                minimal = {primary_key: change['record_id']}
                                # include timestamps if the server table has them
                                from datetime import datetime as _dt
                                now_ts = _dt.now().timestamp()
                                for ts in ('created_at', 'updated_at', 'deleted_at'):
                                    if ts in valid:
                                        # prefer provided value, else now
                                        minimal[ts] = data.get(ts) or now_ts

                                cols = list(minimal.keys())
                                placeholders = ['?' for _ in cols]
                                values = [minimal[c] for c in cols]
                                sql_insert = f"INSERT OR REPLACE INTO {tbl} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                                try:
                                    cur = server_conn.execute(sql_insert, values)
                                    if getattr(cur, 'rowcount', None) is not None:
                                        row_modified = cur.rowcount > 0
                                    else:
                                        row_modified = True
                                    print(f"[SYNC_SERVICE][DEBUG] Minimal insert for {tbl}:{change['record_id']} applied on server")
                                except Exception as ie:
                                    # Schema mismatch or constraint prevents minimal insert: record as error but don't block
                                    errors.append(f"minimal-insert {tbl}:{change['record_id']}: {ie}")
                            else:
                                # Can't create a minimal row if primary key column missing on server
                                print(f"[SYNC_SERVICE][DEBUG] Skipping {tbl}:{change['record_id']} - no filtered fields and no primary key on server")
                                row_modified = False
                    except Exception as e:
                        errors.append(f"upsert {tbl}:{change['record_id']}: {e}")

                # Only count as synced when we actually modified the server DB
                if row_modified:
                    synced_count += 1

            server_conn.commit()
            server_conn.close()

            # Update sync status: set last_successful_sync to now if no errors
            self.update_sync_status(len(errors) == 0, synced_count, len(errors))

            if not errors:
                return SyncResult(True, f"Successfully pushed {synced_count} local changes")
            else:
                return SyncResult(False, f"Pushed {synced_count} local changes, {len(errors)} errors", errors)

        except Exception as e:
            try:
                server_conn.close()
            except Exception:
                pass
            return SyncResult(False, f"sync_to_server failed: {e}", [str(e)])
    
    def server_online(self) -> bool:
        """Check if sync server is online."""
        return self._check_server_online()
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get comprehensive sync status information."""
        try:
            # Get server online status
            server_online = self._check_server_online()
            
            # Get last successful sync timestamp
            last_sync = self._get_last_successful_sync()
            
            # Get sync error count
            sync_errors = 0
            try:
                with self.get_sync_connection() as conn:
                    cur = conn.execute("SELECT COUNT(*) FROM sync_errors")
                    sync_errors = cur.fetchone()[0]
            except Exception:
                sync_errors = 0
            
            return {
                'server_online': server_online,
                'last_sync': last_sync if last_sync > 0 else None,
                'sync_errors': sync_errors
            }
        except Exception as e:
            print(f"[SYNC_SERVICE] Error getting sync status: {e}")
            return {
                'server_online': False,
                'last_sync': None,
                'sync_errors': 0,
                'error': str(e)
            }
    
    def clean_invalid_sync_entries(self) -> int:
        """Clean up invalid sync entries that might be causing failures."""
        # Legacy queue cleanup removed. Nothing to clean in timestamp-based model.
        return 0
    
    def get_sync_queue_status(self) -> Dict[str, Any]:
        """Get status of sync queue using parking lot dispenser approach (no DB scans)."""
        try:
            last_sync = self._get_last_successful_sync()
            
            # Use parking lot dispenser: get last change timestamp from config
            from config.settings import get_last_change_timestamp
            last_change = get_last_change_timestamp()
            
            # If last change is after last sync, there are pending changes
            has_pending = last_change > last_sync
            
            if has_pending:
                # For backward compatibility, return a non-zero total with empty table breakdown
                # This indicates "pending changes exist" without expensive scanning
                return {
                    'total_pending': 1,  # Non-zero to indicate pending changes exist
                    'total_synced': 0, 
                    'pending_by_table': {}  # Empty dict - no per-table breakdown in dispenser mode
                }
            else:
                # No pending changes
                return {
                    'total_pending': 0,
                    'total_synced': 0,
                    'pending_by_table': {}
                }
        except Exception as e:
            print(f"[SYNC_SERVICE] Error getting sync queue status: {e}")
            return {'total_pending': 0, 'total_synced': 0, 'pending_by_table': {}}

    def sync_from_server(self) -> SyncResult:
        """
        SMART Sync changes from server to local database.
        Only syncs records that are newer on server than local (timestamp-based).
        
        If force_full_sync flag is set, syncs ALL records regardless of timestamps.
        This happens after sync version upgrade to ensure all historical data is synced.
        
        Returns:
            SyncResult with success status, message, and any errors
        """
        import sqlite3  # Import here to ensure DB_SHIM is applied
        print("[SYNC_SERVICE][DEBUG] sync_from_server: Starting pull from server")
        
        server_db_path = self.get_server_db_path()
        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Server DB path: {server_db_path}")
        
        if not self._check_server_online():
            print("[SYNC_SERVICE][DEBUG] sync_from_server: Server offline - aborting")
            return SyncResult(False, "Server offline", ["Server offline"])
        
        print("[SYNC_SERVICE][DEBUG] sync_from_server: Server is online")
        
        # Check if we should force full sync
        force_full = self._should_force_full_sync()
        if force_full:
            print("[SYNC_SERVICE] WARNING: FULL SYNC MODE - Syncing ALL records regardless of timestamps")
        else:
            print("[SYNC_SERVICE][DEBUG] sync_from_server: Incremental sync mode")
        
        local_db_path = get_db_path()  # Fixed: use get_db_path() instead of self.local_db_path
        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Local DB path: {local_db_path}")
        import os
        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Current working directory: {os.getcwd()}")
        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: get_db_path() returns: {get_db_path()}")
        
        synced_count = 0
        skipped_count = 0
        errors = []
        
        try:
            # Get list of tables to sync
            tables_to_sync = list(self.table_pk_map.keys())
            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Tables to sync: {tables_to_sync}")
            
            # DEBUG: Verify server path before connecting
            print(f"[SYNC_SERVICE][DEBUG] os.path.exists(server_db_path): {os.path.exists(server_db_path)}")
            print(f"[SYNC_SERVICE][DEBUG] os.path.isfile(server_db_path): {os.path.isfile(server_db_path)}")
            print(f"[SYNC_SERVICE][DEBUG] os.path.abspath(server_db_path): {os.path.abspath(server_db_path)}")
            
            # Create connections separately to avoid any context manager issues
            server_conn = sqlite3.connect(server_db_path)
            server_conn.row_factory = sqlite3.Row
            
            # CRITICAL DEBUG: Verify ACTUAL database file being used
            print(f"[SYNC_SERVICE][CRITICAL] About to connect to local database: {local_db_path}")
            print(f"[SYNC_SERVICE][CRITICAL] os.path.exists(local_db_path): {os.path.exists(local_db_path)}")
            print(f"[SYNC_SERVICE][CRITICAL] os.path.abspath(local_db_path): {os.path.abspath(local_db_path)}")
            
            local_conn = sqlite3.connect(local_db_path)
            local_conn.row_factory = sqlite3.Row
            
            # Verify connection is to correct database
            actual_db = local_conn.execute("PRAGMA database_list").fetchone()[2]
            print(f"[SYNC_SERVICE][CRITICAL] ACTUAL database file connected: {actual_db}")
            print(f"[SYNC_SERVICE][CRITICAL] Are they the same? {os.path.normpath(local_db_path) == os.path.normpath(actual_db)}")
            
            # DEBUG: Check what database we're actually connected to
            try:
                db_list = server_conn.execute("PRAGMA database_list").fetchall()
                print(f"[SYNC_SERVICE][DEBUG] Server connection database list: {db_list}")
                for row in db_list:
                    print(f"[SYNC_SERVICE][DEBUG] DB: seq={row[0]}, name={row[1]}, file={row[2]}")
                with open(r"C:\Users\saoud\Desktop\sync_debug.txt", "a") as f:
                    f.write(f"Server DB path from PRAGMA: {db_list}\n")
                    for row in db_list:
                        f.write(f"DB: seq={row[0]}, name={row[1]}, file={row[2]}\n")
                    f.write(f"Expected server path: {server_db_path}\n")
                    f.write(f"Local path: {local_db_path}\n")
            except Exception as e:
                print(f"[SYNC_SERVICE][DEBUG] Failed to get database list: {e}")
                with open(r"C:\Users\saoud\Desktop\sync_debug.txt", "a") as f:
                    f.write(f"Failed to get database list: {e}\n")
            
            for table_name in tables_to_sync:
                    print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Processing table: {table_name}")
                    
                    try:
                        primary_key = self.table_pk_map[table_name]
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Primary key for {table_name}: {primary_key}")
                        
                        # Check if table exists on both sides
                        try:
                            local_conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Table {table_name} exists locally")
                        except sqlite3.OperationalError as e:
                            # Table doesn't exist locally, skip it
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Skipping {table_name} - doesn't exist locally: {e}")
                            continue
                        
                        try:
                            server_conn.execute(f"SELECT 1 FROM {table_name} LIMIT 1").fetchone()
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Table {table_name} exists on server")
                        except sqlite3.OperationalError as e:
                            # Table doesn't exist on server, skip it
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Skipping {table_name} - doesn't exist on server: {e}")
                            continue
                        
                        # Check if table has timestamp column for smart sync
                        col_info = local_conn.execute(f"PRAGMA table_info({table_name})").fetchall()
                        has_updated_at = any(col[1] == 'updated_at' for col in col_info)
                        has_created_at = any(col[1] == 'created_at' for col in col_info)
                        timestamp_col = 'updated_at' if has_updated_at else ('created_at' if has_created_at else None)
                        
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Table {table_name} timestamp column: {timestamp_col}")
                        
                        # DEBUG: Test server connection and query
                        try:
                            test_count = server_conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: COUNT(*) query returned: {test_count}")
                            
                            # Write to debug file
                            with open(r"C:\Users\saoud\Desktop\sync_debug.txt", "a") as f:
                                f.write(f"Table {table_name}: COUNT(*) = {test_count}\n")
                        except Exception as e:
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: COUNT(*) query failed: {e}")
                            with open(r"C:\Users\saoud\Desktop\sync_debug.txt", "a") as f:
                                f.write(f"Table {table_name}: COUNT(*) failed: {e}\n")
                        
                        # Get all records from server
                        if primary_key == 'rowid':
                            # For tables using rowid as primary key, explicitly select it
                            server_records = server_conn.execute(f"SELECT rowid, * FROM {table_name}").fetchall()
                        else:
                            server_records = server_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                        server_count = len(server_records)
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Found {server_count} records on server for {table_name}")
                        
                        # DUPLICATE DETECTION: Check for duplicate primary key values on server
                        if server_count > 0:
                            # Get column index for primary key
                            col_names = [desc[0] for desc in server_conn.execute(f"SELECT * FROM {table_name} LIMIT 0").description]
                            if primary_key == 'rowid':
                                pk_index = 0  # rowid is first column when explicitly selected
                            else:
                                pk_index = col_names.index(primary_key) if primary_key in col_names else -1
                            
                            if pk_index >= 0:
                                # Extract primary key values
                                pk_values = [record[pk_index] for record in server_records]
                                unique_pk_values = set(pk_values)
                                
                                if len(pk_values) != len(unique_pk_values):
                                    duplicate_count = len(pk_values) - len(unique_pk_values)
                                    error_msg = (
                                        f"WARNING DUPLICATE PRIMARY KEY DETECTED on server table '{table_name}'!\n"
                                        f"  Total records: {len(pk_values)}\n"
                                        f"  Unique {primary_key} values: {len(unique_pk_values)}\n"
                                        f"  Duplicates: {duplicate_count}\n"
                                        f"  This will cause sync to LOSE DATA - only {len(unique_pk_values)} records will be synced!\n"
                                        f"  Run fix_duplicate_clients.py to fix the server schema."
                                    )
                                    print(f"[SYNC_SERVICE][ERROR] {error_msg}")
                                    errors.append(f"{table_name}: {duplicate_count} duplicate primary keys on server")
                                    
                                    # Show some example duplicates
                                    from collections import Counter
                                    pk_counter = Counter(pk_values)
                                    duplicates = [(pk, count) for pk, count in pk_counter.most_common(5) if count > 1]
                                    if duplicates:
                                        print(f"[SYNC_SERVICE][ERROR] Top duplicate {primary_key} values:")
                                        for pk, count in duplicates:
                                            print(f"[SYNC_SERVICE][ERROR]   {primary_key}={pk}: {count} duplicates")
                        
                        if server_count == 0 and test_count > 0:
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: WARNING - COUNT(*) shows {test_count} but SELECT * returned 0 records!")
                        
                        # Get all records from local for comparison
                        if primary_key == 'rowid':
                            # For tables using rowid as primary key, explicitly select it
                            local_records = local_conn.execute(f"SELECT rowid, * FROM {table_name}").fetchall()
                        else:
                            local_records = local_conn.execute(f"SELECT * FROM {table_name}").fetchall()
                        local_records_dict = {record[primary_key]: dict(record) for record in local_records}
                        local_count = len(local_records)
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Found {local_count} records locally for {table_name}")
                        
                        # Sync each server record to local (SMART: only if newer or doesn't exist)
                        table_synced = 0
                        table_skipped = 0
                        
                        for server_record in server_records:
                            record_data = dict(server_record)
                            record_id = record_data.get(primary_key)
                            
                            if record_id is None:
                                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Skipping record with null primary key in {table_name}")
                                continue
                            
                            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Processing {table_name}:{record_id}")
                            
                            # Check if record exists locally
                            if record_id in local_records_dict:
                                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Record {table_name}:{record_id} exists locally")
                                
                                # Record exists locally - check if server version is newer
                                # SKIP timestamp check if in force_full mode
                                if not force_full and timestamp_col and timestamp_col in record_data and timestamp_col in local_records_dict[record_id]:
                                    server_timestamp = record_data.get(timestamp_col)
                                    local_timestamp = local_records_dict[record_id].get(timestamp_col)
                                    
                                    # Helper function to normalize timestamp for comparison
                                    def normalize_timestamp(ts_val):
                                        """Convert timestamp to float for comparison."""
                                        if ts_val is None:
                                            return None
                                        if isinstance(ts_val, (int, float)):
                                            # Treat 0 as None (invalid/unset timestamp)
                                            return float(ts_val) if ts_val != 0 else None
                                        if isinstance(ts_val, str):
                                            # Try to parse as Unix timestamp first
                                            try:
                                                if ts_val.replace('.', '').isdigit():
                                                    val = float(ts_val)
                                                    return val if val != 0 else None
                                            except:
                                                pass
                                            # Try to parse as ISO timestamp
                                            try:
                                                import datetime
                                                dt = datetime.datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                                return dt.timestamp()
                                            except:
                                                pass
                                        return None
                                    
                                    server_ts_norm = normalize_timestamp(server_timestamp)
                                    local_ts_norm = normalize_timestamp(local_timestamp)
                                    
                                    print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Comparing timestamps - Server: {server_timestamp} ({server_ts_norm}), Local: {local_timestamp} ({local_ts_norm})")
                                    
                                    # If EITHER timestamp is NULL/0, always update (legacy/invalid data)
                                    if server_ts_norm is None or local_ts_norm is None:
                                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Updating {table_name}:{record_id} - NULL/0 timestamp detected (legacy data)")
                                        # Continue to update logic below
                                    # Skip if local is newer or same (both timestamps valid)
                                    elif local_ts_norm >= server_ts_norm:
                                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Skipping {table_name}:{record_id} - local is newer or same")
                                        table_skipped += 1
                                        skipped_count += 1
                                        continue
                                elif not force_full:
                                    # In incremental mode, if no timestamp column exists, update anyway
                                    # (better to sync than skip - schema might have evolved)
                                    print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Updating {table_name}:{record_id} - no timestamp column (table evolved)")
                                
                                # Update existing record (server is newer, no timestamp, or force_full mode)
                                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Updating {table_name}:{record_id}")
                                success, error_detail = self._update_local_record(local_conn, table_name, primary_key, record_id, record_data)
                            else:
                                # Insert new record (doesn't exist locally)
                                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Inserting new {table_name}:{record_id}")
                                success, error_detail = self._insert_local_record(local_conn, table_name, record_data)
                            

                            if success:
                                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Successfully synced {table_name}:{record_id}")
                                table_synced += 1
                                synced_count += 1
                            else:
                                error_msg = f"{table_name}:{record_id} - {error_detail}"
                                errors.append(error_msg)
                        
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Table {table_name} summary - Synced: {table_synced}, Skipped: {table_skipped}")
                        
                    except Exception as e:
                        error_msg = f"Error syncing table {table_name}: {str(e)}"
                        print(f"[SYNC_SERVICE][DEBUG] sync_from_server: {error_msg}")
                        errors.append(error_msg)
                        import traceback
                        traceback.print_exc()
            
            print("[SYNC_SERVICE][DEBUG] sync_from_server: Committing changes to local database")
            local_conn.commit()
            
            # CRITICAL DEBUG: Count clients IMMEDIATELY after commit
            try:
                client_count_after_commit = local_conn.execute("SELECT COUNT(*) FROM clients").fetchone()[0]
                print(f"[SYNC_SERVICE][CRITICAL] IMMEDIATE POST-COMMIT COUNT: clients table has {client_count_after_commit} rows")
            except Exception as e:
                print(f"[SYNC_SERVICE][CRITICAL] Failed to count clients after commit: {e}")
            
            # Clear force_full_sync flag if it was set
            if force_full:
                print("[SYNC_SERVICE][DEBUG] sync_from_server: Clearing force full sync flag")
                self._clear_force_full_sync()
            
            print(f"[SYNC_SERVICE][DEBUG] sync_from_server: Final counts - Synced: {synced_count}, Skipped: {skipped_count}, Errors: {len(errors)}")
            
            # Print first 20 errors for debugging
            if errors:
                print(f"[SYNC_SERVICE][ERROR] ===== FIRST 20 ERRORS =====")
                for i, error in enumerate(errors[:20], 1):
                    print(f"[SYNC_SERVICE][ERROR] {i}. {error}")
                print(f"[SYNC_SERVICE][ERROR] ===== END ERRORS =====")
            
            if len(errors) == 0:
                msg = f"Successfully synced {synced_count} records from server"
                if force_full:
                    msg += " (FULL SYNC)"
                if skipped_count > 0:
                    msg += f" (skipped {skipped_count} up-to-date records)"
                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: SUCCESS - {msg}")
                return SyncResult(True, msg)
            else:
                msg = f"Synced {synced_count} records, {len(errors)} errors"
                print(f"[SYNC_SERVICE][DEBUG] sync_from_server: PARTIAL SUCCESS - {msg}")
                return SyncResult(False, msg, errors)
                
        finally:
            server_conn.close()
            local_conn.close()
    
    def _insert_local_record(self, conn: sqlite3.Connection, table_name: str, data: Dict[str, Any]) -> tuple:
        """Insert a record into local database. Returns (success: bool, error_msg: str)"""
        try:
            # Get valid columns for this table
            col_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            valid_columns = {row[1] for row in col_info}
            
            # Filter data to only include valid columns
            filtered_data = {k: v for k, v in data.items() if k in valid_columns}
            
            if not filtered_data:
                # No direct fields match local schema. Attempt a minimal insert using
                # the configured primary key (from table_pk_map) if that column exists
                primary_key = self.table_pk_map.get(table_name) or self._get_table_primary_key(table_name, conn)
                if primary_key in valid_columns and primary_key in data:
                    # Build minimal insert using primary key and optional timestamps
                    cols = [primary_key]
                    vals = [data.get(primary_key)]
                    now = datetime.now().timestamp()
                    for ts in ('created_at', 'updated_at', 'deleted_at'):
                        if ts in valid_columns:
                            cols.append(ts)
                            vals.append(data.get(ts, now if ts != 'deleted_at' else 0))
                    placeholders = ['?' for _ in cols]
                    sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                    try:
                        conn.execute(sql, vals)
                        return (True, "")
                    except Exception as e:
                        error_msg = f"Minimal insert failed: {str(e)}"
                        return (False, error_msg)
                # Nothing we can do safely
                return (True, "")
            
            columns = list(filtered_data.keys())
            placeholders = ['?' for _ in columns]
            values = [filtered_data[col] for col in columns]
            
            sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(columns)}) VALUES ({', '.join(placeholders)})"
            
            cursor = conn.execute(sql, values)
            rows_affected = cursor.rowcount
            
            # Check if this was a REPLACE (rowcount=1 but total didn't increase)
            # This indicates a duplicate primary key on server
            if rows_affected == 1:
                primary_key = self.table_pk_map.get(table_name) or self._get_table_primary_key(table_name, conn)
                pk_value = filtered_data.get(primary_key, "UNKNOWN")
                
                # Check if row count increased (true INSERT) or stayed same (REPLACE)
                count_before = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
                # The INSERT already happened, so we can't compare before/after
                # Instead, check if this pk_value already exists (which would mean REPLACE happened)
                existing = conn.execute(f"SELECT COUNT(*) FROM {table_name} WHERE {primary_key} = ?", (pk_value,)).fetchone()[0]
                
                if existing > 1:
                    # This should never happen with PRIMARY KEY constraint
                    error_msg = f"⚠ CRITICAL: Multiple rows with same {primary_key}={pk_value} after INSERT!"
                    print(f"[SYNC_SERVICE][ERROR] {error_msg}")
                    return (False, error_msg)
            
            return (True, "")
            
        except Exception as e:
            error_msg = f"Insert error: {str(e)}"
            return (False, error_msg)
    
    def _update_local_record(self, conn: sqlite3.Connection, table_name: str, primary_key: str, record_id: Any, data: Dict[str, Any]) -> tuple:
        """Update a record in local database. Returns (success: bool, error_msg: str)"""
        try:
            # Get valid columns for this table
            col_info = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
            valid_columns = {row[1] for row in col_info}
            
            # Filter data to only include valid columns (exclude primary key)
            filtered_data = {k: v for k, v in data.items() if k in valid_columns and k != primary_key}
            
            # CRITICAL FIX: Always include updated_at = updated_at to prevent timestamp trigger from firing
            # This ensures the trigger condition (NEW.updated_at IS NULL OR NEW.updated_at = 0) is not met
            if 'updated_at' in valid_columns:
                filtered_data['updated_at'] = conn.execute(f"SELECT updated_at FROM {table_name} WHERE {primary_key} = ?", (record_id,)).fetchone()[0]
            
            if not filtered_data:
                # No fields to update; attempt a minimal insert if the local table has the primary key column
                if primary_key in valid_columns:
                    try:
                        # If record doesn't exist locally, insert minimal
                        exists = conn.execute(f"SELECT 1 FROM {table_name} WHERE {primary_key} = ?", (record_id,)).fetchone()
                        if not exists:
                            cols = [primary_key]
                            vals = [record_id]
                            now = datetime.now().timestamp()
                            for ts in ('created_at', 'updated_at', 'deleted_at'):
                                if ts in valid_columns:
                                    cols.append(ts)
                                    vals.append(data.get(ts, now if ts != 'deleted_at' else 0))
                            placeholders = ['?' for _ in cols]
                            sql = f"INSERT OR REPLACE INTO {table_name} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"
                            conn.execute(sql, vals)
                            return (True, "")
                        else:
                            return (True, "")
                    except Exception as e:
                        error_msg = f"Minimal insert failed: {str(e)}"
                        return (False, error_msg)
                return (True, "")  # nothing to update and no primary key locally
            
            set_clauses = [f"{col} = ?" for col in filtered_data.keys()]
            values = list(filtered_data.values()) + [record_id]
            
            sql = f"UPDATE {table_name} SET {', '.join(set_clauses)} WHERE {primary_key} = ?"
            conn.execute(sql, values)
            return (True, "")
            
        except Exception as e:
            error_msg = f"Update error: {str(e)}"
            return (False, error_msg)