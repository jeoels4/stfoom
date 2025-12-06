"""
connection.smart_sync
====================
Smart record-level sync system for LAN database synchronization.
Updated to use modern service-oriented architecture.
"""

from __future__ import annotations
import os
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass

# Use modern service architecture
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from stfoom.services.sync_service import SyncService

# ----------------------------------------------------------
# CONFIGURATION
# ----------------------------------------------------------
SERVER_PATH = r"\\DESKTOP-BKIB183\data"
LOCAL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))

# Sync settings
SYNC_INTERVAL = 30  # seconds between syncs
CONFLICT_RESOLUTION = "server_wins"  # or "client_wins", "manual"
MAX_RETRIES = 3

# ----------------------------------------------------------
# DATA STRUCTURES
# ----------------------------------------------------------

@dataclass
class SyncRecord:
    """Represents a record that needs to be synced."""
    table: str
    record_id: str
    data: Dict[str, Any]
    timestamp: float
    computer_id: str
    operation: str
    record_hash: str

@dataclass  
class SyncStatus:
    """Status of sync operation."""
    success: bool
    message: str
    conflicts: List[Any]
    synced_records: int
    errors: List[str]

# ----------------------------------------------------------
# GLOBAL STATE
# ----------------------------------------------------------
_sync_service: Optional[SyncService] = None
_initialized = False
_initialization_lock = threading.Lock()

def ensure_initialized():
    """Ensure sync service is initialized."""
    global _sync_service, _initialized
    
    if not _initialized:
        with _initialization_lock:
            if not _initialized:  # Double-check locking
                try:
                    _sync_service = SyncService()
                    _initialized = True
                    print("[SYNC] Modern sync service initialized successfully")
                except Exception as e:
                    print(f"[SYNC] Error initializing sync service: {e}")
                    raise

def get_computer_id() -> str:
    """Get computer ID."""
    ensure_initialized()
    return _sync_service.computer_id if _sync_service else "unknown"
    record_id: str
    data: Dict[str, Any]
    timestamp: float
    computer_id: str
    operation: str  # 'insert', 'update', 'delete'
    hash: str

@dataclass
class SyncStatus:
    """Sync operation status."""
    success: bool
    message: str
    conflicts: List[Dict]
    synced_records: int
    errors: List[str]

# ----------------------------------------------------------
# UTILITIES
# ----------------------------------------------------------

def get_computer_id() -> str:
    """Get unique computer identifier."""
    try:
        return socket.gethostname()
    except:
        return f"computer_{int(time.time())}"

def get_record_hash(data: Dict[str, Any]) -> str:
    """Generate secure hash for record data using SHA-256."""
    try:
        # Import secure hashing module
        from stfoom.logic.secure_hashing import secure_record_hash
        return secure_record_hash(data)
    except ImportError:
        # Fallback to SHA-256 if secure module not available
        import hashlib
        import json
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode()).hexdigest()
    except Exception as e:
        # Log the error and fallback to basic SHA-256
        print(f"[SECURITY] Secure hash generation failed: {e}")
        import hashlib
        import json
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        return hashlib.sha256(data_str.encode()).hexdigest()

def server_online() -> bool:
    """Check if server is accessible."""
    # Cache server status for 30 seconds to improve performance
    current_time = time.time()
    
    if (hasattr(server_online, '_cache') and 
        hasattr(server_online, '_cache_time') and
        current_time - server_online._cache_time < 30):
        return server_online._cache
    
    try:
        server_name = SERVER_PATH.split("\\")[2]
        socket.gethostbyname(server_name)
        result = os.path.exists(SERVER_PATH)
        
        # Cache the result
        server_online._cache = result
        server_online._cache_time = current_time
        return result
    except Exception:
        # Cache failure as well
        server_online._cache = False
        server_online._cache_time = current_time
        return False

def get_db_path(is_server: bool = False) -> str:
    """Get database path for local or server."""
    base_path = SERVER_PATH if is_server else LOCAL_PATH
    return os.path.join(base_path, "stfoom.db")

def get_sync_db_path(is_server: bool = False) -> str:
    """Get sync tracking database path."""
    base_path = SERVER_PATH if is_server else LOCAL_PATH
    return os.path.join(base_path, "sync_tracking.db")

# ----------------------------------------------------------
# SYNC TRACKING DATABASE
# ----------------------------------------------------------

def init_sync_tracking():
    """Initialize sync tracking database."""
    sync_db_path = get_sync_db_path()
    os.makedirs(os.path.dirname(sync_db_path), exist_ok=True)
    
    with sqlite3.connect(sync_db_path) as conn:
        # Enable WAL mode for better performance
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA cache_size = 10000")
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_changes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                data TEXT NOT NULL,
                timestamp REAL NOT NULL,
                computer_id TEXT NOT NULL,
                operation TEXT NOT NULL,
                record_hash TEXT NOT NULL,
                synced INTEGER DEFAULT 0,
                sync_timestamp REAL,
                UNIQUE(table_name, record_id, timestamp, computer_id)
            )
        """)
        
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sync_status (
                computer_id TEXT PRIMARY KEY,
                last_sync REAL,
                last_successful_sync REAL,
                sync_errors INTEGER DEFAULT 0,
                total_synced INTEGER DEFAULT 0
            )
        """)
        
        # Add performance indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_table_record ON sync_changes(table_name, record_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_timestamp ON sync_changes(timestamp)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_synced ON sync_changes(synced)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sync_computer ON sync_changes(computer_id)")
        
        conn.commit()

def add_sync_change(table: str, record_id: str, data: Dict, operation: str):
    """Add a change to the sync tracking."""
    ensure_initialized()
    
    try:
        sync_db_path = get_sync_db_path()
        
        # Use WAL mode for better concurrent performance
        with sqlite3.connect(sync_db_path) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")  # Faster than FULL
            
            record_hash = get_record_hash(data)
            conn.execute("""
                INSERT OR REPLACE INTO sync_changes 
                (table_name, record_id, data, timestamp, computer_id, operation, record_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                table, record_id, json.dumps(data), 
                time.time(), get_computer_id(), operation, record_hash
            ))
            # Don't force immediate commit - let SQLite handle it
    except Exception as e:
        print(f"[SYNC] Error adding sync change: {e}")

def get_pending_changes() -> List[SyncRecord]:
    """Get all pending changes to be synced."""
    ensure_initialized()
    
    try:
        sync_db_path = get_sync_db_path()
        with sqlite3.connect(sync_db_path) as conn:
            cursor = conn.execute("""
                SELECT table_name, record_id, data, timestamp, computer_id, operation, record_hash
                FROM sync_changes 
                WHERE synced = 0
                ORDER BY timestamp ASC
            """)
            
            changes = []
            for row in cursor.fetchall():
                changes.append(SyncRecord(
                    table=row[0],
                    record_id=row[1],
                    data=json.loads(row[2]),
                    timestamp=row[3],
                    computer_id=row[4],
                    operation=row[5],
                    hash=row[6]
                ))
            return changes
    except Exception as e:
        print(f"[SYNC] Error getting pending changes: {e}")
        return []

# ----------------------------------------------------------
# DATABASE OPERATIONS
# ----------------------------------------------------------

def get_table_primary_key(table: str, db_path: str) -> str:
    """Get primary key column for a table."""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(f"PRAGMA table_info({table})")
            for row in cursor.fetchall():
                if row[5] == 1:  # is primary key
                    return row[1]
        return "id"  # fallback
    except Exception:
        return "id"

def apply_record_change(table: str, record_id: str, data: Dict, operation: str, db_path: str) -> bool:
    """Apply a record change to the database."""
    try:
        # Skip sqlite_sequence table changes to prevent sync errors
        if table == "sqlite_sequence":
            print(f"[SYNC] Skipping sqlite_sequence operation: {operation}")
            return True
            
        with sqlite3.connect(db_path) as conn:
            if operation == "delete":
                from stfoom.logic.sql_injection_prevention import SecureQueryBuilder, SQLInjectionError
                try:
                    builder = SecureQueryBuilder()
                    pk_col = get_table_primary_key(table, db_path)
                    where_conditions = {pk_col: record_id}
                    sql, params = builder.build_delete(table, where_conditions)
                    conn.execute(sql, params)
                except SQLInjectionError as e:
                    print(f"[SECURITY] SQL injection attempt blocked in apply_change (delete): {e}")
                    return False
            elif operation == "insert":
                from stfoom.logic.sql_injection_prevention import SecureQueryBuilder, SQLInjectionError
                try:
                    builder = SecureQueryBuilder()
                    # Use INSERT OR REPLACE for sync operations
                    columns = list(data.keys())
                    placeholders = ", ".join("?" for _ in columns)
                    sql = f"INSERT OR REPLACE INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
                    # Validate table and columns first
                    builder.validate_inputs(table, columns)
                    conn.execute(sql, list(data.values()))
                except SQLInjectionError as e:
                    print(f"[SECURITY] SQL injection attempt blocked in apply_change (insert): {e}")
                    return False
            elif operation == "update":
                from stfoom.logic.sql_injection_prevention import SecureQueryBuilder, SQLInjectionError
                try:
                    builder = SecureQueryBuilder()
                    pk_col = get_table_primary_key(table, db_path)
                    # Remove primary key from update data
                    update_data = {k: v for k, v in data.items() if k != pk_col}
                    where_conditions = {pk_col: record_id}
                    sql, params = builder.build_update(table, update_data, where_conditions)
                    conn.execute(sql, params)
                except SQLInjectionError as e:
                    print(f"[SECURITY] SQL injection attempt blocked in apply_change (update): {e}")
                    return False
            conn.commit()
            return True
    except Exception as e:
        print(f"[SYNC] Error applying change to {table}: {e}")
        return False

def get_table_data(table: str, db_path: str) -> List[Dict]:
    """Get all data from a table."""
    try:
        from stfoom.logic.sql_injection_prevention import SecureQueryBuilder, SQLInjectionError
        
        # Use secure query builder to prevent SQL injection
        builder = SecureQueryBuilder()
        sql, params = builder.build_select(table)
        
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(sql, params)
            columns = [description[0] for description in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except SQLInjectionError as e:
        print(f"[SECURITY] SQL injection attempt blocked in get_table_data: {e}")
        return []
    except Exception as e:
        print(f"[SYNC] Error getting data from {table}: {e}")
        return []

# ----------------------------------------------------------
# CONFLICT RESOLUTION
# ----------------------------------------------------------

def detect_conflicts(local_changes: List[SyncRecord], server_changes: List[SyncRecord]) -> List[Dict]:
    """Detect conflicts between local and server changes."""
    conflicts = []
    
    # Group changes by table and record_id
    local_by_record = {}
    for change in local_changes:
        key = (change.table, change.record_id)
        if key not in local_by_record:
            local_by_record[key] = []
        local_by_record[key].append(change)
    
    server_by_record = {}
    for change in server_changes:
        key = (change.table, change.record_id)
        if key not in server_by_record:
            server_by_record[key] = []
        server_by_record[key].append(change)
    
    # Check for conflicts
    for key in set(local_by_record.keys()) & set(server_by_record.keys()):
        table, record_id = key
        local_records = local_by_record[key]
        server_records = server_by_record[key]
        
        # Check if there are conflicting changes
        for local_change in local_records:
            for server_change in server_records:
                if (local_change.operation != server_change.operation or 
                    local_change.hash != server_change.hash):
                    conflicts.append({
                        'table': table,
                        'record_id': record_id,
                        'local_change': local_change,
                        'server_change': server_change,
                        'resolution': CONFLICT_RESOLUTION
                    })
    
    return conflicts

def resolve_conflicts(conflicts: List[Dict], local_changes: List[SyncRecord]) -> List[SyncRecord]:
    """Resolve conflicts based on configured strategy. If no conflicts, return all local_changes."""
    if not conflicts:
        return local_changes
    resolved_changes = []
    for conflict in conflicts:
        if conflict['resolution'] == "server_wins":
            resolved_changes.append(conflict['server_change'])
        elif conflict['resolution'] == "client_wins":
            resolved_changes.append(conflict['local_change'])
        elif conflict['resolution'] == "manual":
            # For manual resolution, we'll need to implement a UI
            # For now, default to server wins
            resolved_changes.append(conflict['server_change'])
    return resolved_changes

# ----------------------------------------------------------
# MAIN SYNC FUNCTIONS
# ----------------------------------------------------------

def sync_to_server() -> SyncStatus:
    """Sync local changes to server."""
    ensure_initialized()
    
    if not server_online():
        return SyncStatus(False, "Server offline", [], 0, ["Server not accessible"])
    try:
        # Get pending changes
        local_changes = get_pending_changes()
        if not local_changes:
            return SyncStatus(True, "No changes to sync", [], 0, [])
        # Get server changes
        server_changes = get_pending_changes_server()
        # Detect conflicts
        conflicts = detect_conflicts(local_changes, server_changes)
        # Resolve conflicts
        resolved_changes = resolve_conflicts(conflicts, local_changes)
        # Apply changes to server
        synced_count = 0
        errors = []
        for change in local_changes:
            if change not in resolved_changes:  # Skip conflicting changes
                continue
            success = apply_record_change(
                change.table, change.record_id, change.data, 
                change.operation, get_db_path(is_server=True)
            )
            if success:
                synced_count += 1
                # Mark as synced
                mark_change_synced(change)
            else:
                errors.append(f"Failed to sync {change.table}:{change.record_id}")
        # Update sync status
        update_sync_status(True, synced_count, errors)
        return SyncStatus(
            success=len(errors) == 0,
            message=f"Synced {synced_count} records",
            conflicts=conflicts,
            synced_records=synced_count,
            errors=errors
        )
    except Exception as e:
        error_msg = f"Sync error: {str(e)}"
        update_sync_status(False, 0, [error_msg])
        return SyncStatus(False, error_msg, [], 0, [error_msg])

def sync_from_server() -> SyncStatus:
    """Sync server changes to local."""
    ensure_initialized()
    
    if not server_online():
        return SyncStatus(False, "Server offline", [], 0, ["Server not accessible"])
    
    try:
        # Get server changes
        server_changes = get_pending_changes_server()
        if not server_changes:
            return SyncStatus(True, "No server changes", [], 0, [])
        
        # Get local changes
        local_changes = get_pending_changes()
        
        # Detect conflicts
        conflicts = detect_conflicts(local_changes, server_changes)
        
        # Resolve conflicts
        resolved_changes = resolve_conflicts(conflicts, server_changes)
        
        # Apply changes to local
        synced_count = 0
        errors = []
        
        for change in server_changes:
            if change not in resolved_changes:  # Skip conflicting changes
                continue
                
            success = apply_record_change(
                change.table, change.record_id, change.data, 
                change.operation, get_db_path(is_server=False)
            )
            
            if success:
                synced_count += 1
                # Mark server change as synced
                mark_change_synced_server(change)
            else:
                errors.append(f"Failed to sync {change.table}:{change.record_id}")
        
        # Update sync status
        update_sync_status(True, synced_count, errors)
        
        return SyncStatus(
            success=len(errors) == 0,
            message=f"Synced {synced_count} records from server",
            conflicts=conflicts,
            synced_records=synced_count,
            errors=errors
        )
        
    except Exception as e:
        error_msg = f"Sync error: {str(e)}"
        update_sync_status(False, 0, [error_msg])
        return SyncStatus(False, error_msg, [], 0, [error_msg])

# ----------------------------------------------------------
# HELPER FUNCTIONS
# ----------------------------------------------------------

def get_pending_changes_server() -> List[SyncRecord]:
    """Get pending changes from server."""
    try:
        sync_db_path = get_sync_db_path(is_server=True)
        if not os.path.exists(sync_db_path):
            return []
            
        with sqlite3.connect(sync_db_path) as conn:
            cursor = conn.execute("""
                SELECT table_name, record_id, data, timestamp, computer_id, operation, record_hash
                FROM sync_changes 
                WHERE synced = 0
                ORDER BY timestamp ASC
            """)
            
            changes = []
            for row in cursor.fetchall():
                changes.append(SyncRecord(
                    table=row[0],
                    record_id=row[1],
                    data=json.loads(row[2]),
                    timestamp=row[3],
                    computer_id=row[4],
                    operation=row[5],
                    hash=row[6]
                ))
            return changes
    except Exception as e:
        print(f"[SYNC] Error getting server changes: {e}")
        return []

def mark_change_synced(change: SyncRecord):
    """Mark a change as synced."""
    try:
        sync_db_path = get_sync_db_path()
        with sqlite3.connect(sync_db_path) as conn:
            conn.execute("""
                UPDATE sync_changes 
                SET synced = 1, sync_timestamp = ?
                WHERE table_name = ? AND record_id = ? AND timestamp = ? AND computer_id = ?
            """, (time.time(), change.table, change.record_id, change.timestamp, change.computer_id))
            conn.commit()
    except Exception as e:
        print(f"[SYNC] Error marking change synced: {e}")

def mark_change_synced_server(change: SyncRecord):
    """Mark a server change as synced."""
    try:
        sync_db_path = get_sync_db_path(is_server=True)
        with sqlite3.connect(sync_db_path) as conn:
            conn.execute("""
                UPDATE sync_changes 
                SET synced = 1, sync_timestamp = ?
                WHERE table_name = ? AND record_id = ? AND timestamp = ? AND computer_id = ?
            """, (time.time(), change.table, change.record_id, change.timestamp, change.computer_id))
            conn.commit()
    except Exception as e:
        print(f"[SYNC] Error marking server change synced: {e}")

def update_sync_status(success: bool, synced_count: int, errors: List[str]):
    """Update sync status tracking."""
    try:
        sync_db_path = get_sync_db_path()
        computer_id = get_computer_id()
        current_time = time.time()
        
        with sqlite3.connect(sync_db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO sync_status 
                (computer_id, last_sync, last_successful_sync, sync_errors, total_synced)
                VALUES (?, ?, ?, ?, ?)
            """, (
                computer_id,
                current_time,
                current_time if success else None,
                len(errors),
                synced_count
            ))
            conn.commit()
    except Exception as e:
        print(f"[SYNC] Error updating sync status: {e}")

# ----------------------------------------------------------
# INITIALIZATION
# ----------------------------------------------------------

def initialize_smart_sync():
    """Initialize the smart sync system."""
    print("[SYNC] Initializing smart sync system...")
    
    # Initialize sync tracking databases
    init_sync_tracking()
    
    # Initialize server sync tracking if server is online
    if server_online():
        try:
            server_sync_db = get_sync_db_path(is_server=True)
            os.makedirs(os.path.dirname(server_sync_db), exist_ok=True)
            
            with sqlite3.connect(server_sync_db) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_changes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        table_name TEXT NOT NULL,
                        record_id TEXT NOT NULL,
                        data TEXT NOT NULL,
                        timestamp REAL NOT NULL,
                        computer_id TEXT NOT NULL,
                        operation TEXT NOT NULL,
                        record_hash TEXT NOT NULL,
                        synced INTEGER DEFAULT 0,
                        sync_timestamp REAL,
                        UNIQUE(table_name, record_id, timestamp, computer_id)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS sync_status (
                        computer_id TEXT PRIMARY KEY,
                        last_sync REAL,
                        last_successful_sync REAL,
                        sync_errors INTEGER DEFAULT 0,
                        total_synced INTEGER DEFAULT 0
                    )
                """)
                conn.commit()
        except Exception as e:
            print(f"[SYNC] Warning: Could not initialize server sync tracking: {e}")
    
    print(f"[SYNC] Smart sync initialized. Computer ID: {get_computer_id()}")
    print(f"[SYNC] Local path: {LOCAL_PATH}")
    print(f"[SYNC] Server path: {SERVER_PATH}")
    print(f"[SYNC] Server online: {server_online()}")

# Don't initialize automatically - will be initialized when first sync operation is called
_initialized = False

def ensure_initialized():
    """Ensure smart sync is initialized."""
    global _initialized
    if not _initialized:
        initialize_smart_sync()
        _initialized = True

def push_local_changes_to_server():
    """Push local database changes to server using smart sync."""
    ensure_initialized()
    
    if not server_online():
        print("[SYNC] Server offline, cannot push changes")
        return False
    
    try:
        # Use the existing smart sync system instead of file copying
        result = sync_to_server()
        
        if result.success:
            print(f"[SYNC] Successfully pushed {result.synced_records} changes to server")
            return True
        else:
            print(f"[SYNC] Failed to push changes: {result.message}")
            return False
            
    except Exception as e:
        print(f"[SYNC] Error pushing changes to server: {e}")
        return False

def ensure_server_connection():
    """Ensure server connection is available."""
    return server_online()

def get_local_db_path():
    """Get local database path."""
    return get_db_path(is_server=False)

def get_server_db_path():
    """Get server database path."""
    return get_db_path(is_server=True)

def get_local_tracking_db_path():
    """Get local tracking database path."""
    return get_sync_db_path(is_server=False)

def get_server_tracking_db_path():
    """Get server tracking database path."""
    return get_sync_db_path(is_server=True)

def _close_all_connections():
    """Close all database connections to release file locks."""
    try:
        # Close main database connections
        import gc
        gc.collect()  # Force garbage collection to close orphaned connections
        
        # Close any active connections in db.py
        try:
            from stfoom.logic import db
            if hasattr(db, '_connection') and db._connection:
                db._connection.close()
                db._connection = None
        except Exception:
            pass
            
    except Exception as e:
        print(f"[SYNC] Error closing connections: {e}")

def _copy_with_retry(src_path, dest_path, max_retries=5, delay=2):
    """Copy file with retry logic for locked files."""
    import shutil
    import time
    
    for attempt in range(max_retries):
        try:
            # Check if source file exists
            if not os.path.exists(src_path):
                print(f"[SYNC] Source file does not exist: {src_path}")
                return False
            
            # Create destination directory if it doesn't exist
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            
            # Try to copy the file
            shutil.copy2(src_path, dest_path)
            return True
            
        except PermissionError as e:
            if "being used by another process" in str(e) or "locked" in str(e).lower():
                print(f"[SYNC] File locked: {src_path}, retry {attempt + 1}/{max_retries}")
                if attempt < max_retries - 1:
                    time.sleep(delay * (attempt + 1))  # Exponential backoff
                continue
            else:
                print(f"[SYNC] Permission error copying {src_path}: {e}")
                return False
        except Exception as e:
            print(f"[SYNC] Error copying {src_path}: {e}")
            return False
    
    print(f"[SYNC] Failed to copy after {max_retries} attempts: {src_path}")
    return False

# Main sync function that combines both directions
def full_sync():
    """Perform full bidirectional sync."""
    ensure_initialized()
    
    if not server_online():
        print("[SYNC] Server offline")
        return False
    
    try:
        print("[SYNC] Starting full sync...")
        
        # Sync from server first
        from_result = sync_from_server()
        print(f"[SYNC] Sync from server: {from_result.message}")
        
        # Then sync to server
        to_result = sync_to_server()
        print(f"[SYNC] Sync to server: {to_result.message}")
        
        success = from_result.success and to_result.success
        total_synced = from_result.synced_records + to_result.synced_records
        
        if success:
            print(f"[SYNC] Full sync completed successfully. Total records: {total_synced}")
        else:
            print("[SYNC] Full sync completed with errors")
        
        return success
        
    except Exception as e:
        print(f"[SYNC] Error in full sync: {e}")
        return False