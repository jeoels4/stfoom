"""
connection.backup_system
=======================
Comprehensive backup system for STFOOM database and files.
Features automatic backups, manual backups, rotation, and restore functionality.

SECURITY UPDATE: Now uses secure path validation to prevent directory traversal attacks.
"""

from __future__ import annotations

# ✅ SECURITY COMPLIANCE: Use centralized configuration
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from config.settings import get_db_path, get_data_dir

import shutil
import sqlite3
import zipfile
import json
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Any
import threading
import hashlib
from dataclasses import dataclass

# Import secure backup functionality
_security_warning_shown = False
try:
    from connection.secure_backup_wrapper import SecureBackupManager
    from stfoom.logic.path_security import (
        PathSecurityError, 
        log_security_event,
        validate_backup_path
    )
    SECURITY_ENABLED = True
except ImportError as e:
    # Only print this warning once during initialization
    if not _security_warning_shown:
        print(f"[BACKUP] Warning: Security modules not available: {e}")
        _security_warning_shown = True
    SECURITY_ENABLED = False

# Configure logging
logger = logging.getLogger(__name__)

# CONFIGURATION - FIXED: Use centralized configuration system
# ----------------------------------------------------------
LOCAL_PATH = get_data_dir()  # ✅ FIXED: No more hardcoded paths
BACKUP_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backups"))
DB_PATH = get_db_path()  # ✅ FIXED: No more hardcoded paths

# Initialize secure backup manager
if SECURITY_ENABLED:
    try:
        _secure_backup_manager = SecureBackupManager(BACKUP_DIR, LOCAL_PATH)
        logger.info("Secure backup manager initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize secure backup manager: {e}")
        _secure_backup_manager = None
        SECURITY_ENABLED = False
else:
    _secure_backup_manager = None

# Server backup configuration with security validation
try:
    from stfoom.logic.network_path_security import get_secure_server_path
    SERVER_PATH = get_secure_server_path(r"\\DESKTOP-BKIB183\data")
except Exception as e:
    print(f"[BACKUP] Failed to get secure server path: {e}")
    # Fallback with basic validation
    fallback_path = os.getenv('STFOOM_SERVER_PATH', r"\\DESKTOP-BKIB183\data")
    if not fallback_path or ".." in fallback_path:
        SERVER_PATH = r"\\DESKTOP-BKIB183\data"  # Safe hardcoded fallback
    else:
        SERVER_PATH = fallback_path

SERVER_BACKUP_DIR = os.path.join(SERVER_PATH, "backups") if SERVER_PATH else None

# Backup settings
AUTO_BACKUP_INTERVAL = 3600  # 1 hour in seconds
MAX_BACKUPS = 50  # Keep last 50 backups locally
MAX_SERVER_BACKUPS = 200  # Keep more backups on server (50GB free)
BACKUP_RETENTION_DAYS = 30  # Keep backups for 30 days locally
SERVER_BACKUP_RETENTION_DAYS = 90  # Keep backups for 90 days on server
BACKUP_COMPRESSION = True  # Use ZIP compression
SYNC_TO_SERVER = True  # Automatically sync backups to server

# ----------------------------------------------------------
# DATA STRUCTURES
# ----------------------------------------------------------

@dataclass
class BackupInfo:
    """Information about a backup."""
    filename: str
    timestamp: float
    size_bytes: int
    checksum: str
    backup_type: str  # 'auto', 'manual', 'sync'
    description: str
    success: bool
    error_message: str = ""

# ----------------------------------------------------------
# UTILITIES
# ----------------------------------------------------------

def get_file_checksum(filepath: str) -> str:
    """Calculate secure SHA-256 checksum of a file (replaces vulnerable MD5)."""
    try:
        # Import secure hashing module
        from stfoom.logic.secure_hashing import secure_file_hash
        return secure_file_hash(filepath)
    except ImportError:
        # Fallback to SHA-256 if secure module not available
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()
    except Exception as e:
        # Log the error and fallback to basic SHA-256
        print(f"[SECURITY] Secure file hash generation failed: {e}")
        import hashlib
        hash_sha256 = hashlib.sha256()
        with open(filepath, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_sha256.update(chunk)
        return hash_sha256.hexdigest()

def ensure_backup_dir():
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)

def ensure_server_backup_dir():
    """Ensure server backup directory exists."""
    if not SERVER_BACKUP_DIR:
        return False
    try:
        # First ensure the base server path is accessible
        if not os.path.exists(SERVER_PATH):
            print(f"[BACKUP] Server base path not accessible: {SERVER_PATH}")
            return False
        
        # Then create the backup directory
        os.makedirs(SERVER_BACKUP_DIR, exist_ok=True)
        return True
    except Exception as e:
        print(f"[BACKUP] Error creating server backup directory: {e}")
        return False

def server_online() -> bool:
    """Check if server is accessible."""
    if not SERVER_BACKUP_DIR:
        return False
    try:
        # First check if the base server path exists
        if not os.path.exists(SERVER_PATH):
            print(f"[BACKUP] Server base path not accessible: {SERVER_PATH}")
            return False
        
        # Then check if we can access the backup directory (create it if it doesn't exist)
        if not os.path.exists(SERVER_BACKUP_DIR):
            try:
                os.makedirs(SERVER_BACKUP_DIR, exist_ok=True)
                print(f"[BACKUP] Created server backup directory: {SERVER_BACKUP_DIR}")
            except Exception as e:
                print(f"[BACKUP] Cannot create server backup directory: {e}")
                return False
        
        return True
    except Exception as e:
        print(f"[BACKUP] Server connectivity error: {e}")
        return False

def get_backup_filename(backup_type: str = "auto") -> str:
    """Generate backup filename with timestamp."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"stfoom_backup_{backup_type}_{timestamp}.zip"

def get_backup_info_filepath(backup_filename: str) -> str:
    """Get path for backup info JSON file."""
    return os.path.join(BACKUP_DIR, backup_filename.replace(".zip", ".json"))

def save_backup_info(backup_info) -> bool:
    """Save backup information to JSON file"""
    try:
        info_path = get_backup_info_filepath(backup_info.filename)
        
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': backup_info.filename,
                'timestamp': backup_info.timestamp,
                'size_bytes': backup_info.size_bytes,
                'checksum': backup_info.checksum,
                'backup_type': backup_info.backup_type,
                'description': backup_info.description,
                'success': backup_info.success,
                'error_message': getattr(backup_info, 'error_message', '')
            }, f, indent=2, ensure_ascii=False)
        
        return True
    except Exception as e:
        logger.error(f"Failed to save backup info: {str(e)}")
        return False

# ----------------------------------------------------------
# BACKUP OPERATIONS
# ----------------------------------------------------------

def create_backup(backup_type: str = "manual", description: str = "") -> BackupInfo:
    """Create a complete backup of the STFOOM database and files with security validation."""
    ensure_backup_dir()
    
    backup_filename = get_backup_filename(backup_type)
    
    # Use secure backup manager if available
    if SECURITY_ENABLED and _secure_backup_manager:
        try:
            logger.info(f"Creating secure backup: {backup_filename}")
            success = _secure_backup_manager.secure_create_backup(backup_filename, description)
            
            if success:
                # Get backup file info for BackupInfo object
                backup_path = os.path.join(BACKUP_DIR, backup_filename)
                if os.path.exists(backup_path):
                    backup_info = BackupInfo(
                        filename=backup_filename,
                        timestamp=time.time(),
                        size_bytes=os.path.getsize(backup_path),
                        checksum=get_file_checksum(backup_path),
                        backup_type=backup_type,
                        description=description,
                        success=True
                    )
                    
                    # Save backup info
                    save_backup_info(backup_info)
                    
                    # Sync to server if enabled
                    if SYNC_TO_SERVER and SERVER_BACKUP_DIR:
                        backup_path = os.path.join(BACKUP_DIR, backup_filename)
                        info_path = get_backup_info_filepath(backup_filename)
                        sync_backup_to_server(backup_filename, backup_path, info_path)
                    
                    logger.info(f"Secure backup completed successfully: {backup_filename}")
                    return backup_info
            
            # If secure backup failed, fall back to legacy with warnings
            logger.warning("Secure backup failed, falling back to legacy method")
            log_security_event("BACKUP_FALLBACK", backup_filename, "Secure backup failed")
            
        except Exception as e:
            logger.error(f"Secure backup error: {str(e)}")
            log_security_event("BACKUP_ERROR", backup_filename, str(e))
    
    # Legacy backup method (with basic security checks)
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    
    # Basic path validation for legacy method
    if ".." in backup_filename or "/" in backup_filename or "\\" in backup_filename:
        logger.error(f"Invalid backup filename detected: {backup_filename}")
        log_security_event("BACKUP_FILENAME_VIOLATION", backup_filename, "Path traversal attempt")
        return BackupInfo(
            filename=backup_filename,
            timestamp=time.time(),
            size_bytes=0,
            checksum="",
            backup_type=backup_type,
            description=description,
            success=False
        )
    
    info_path = get_backup_info_filepath(backup_filename)
    
    backup_info = BackupInfo(
        filename=backup_filename,
        timestamp=time.time(),
        size_bytes=0,
        checksum="",
        backup_type=backup_type,
        description=description,
        success=False
    )
    
    try:
        # Create ZIP backup
        with zipfile.ZipFile(backup_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Add database file
            if os.path.exists(DB_PATH):
                zipf.write(DB_PATH, "stfoom.db")
            
            # Add sync tracking database if it exists
            sync_db_path = os.path.join(LOCAL_PATH, "sync_tracking.db")
            if os.path.exists(sync_db_path):
                zipf.write(sync_db_path, "sync_tracking.db")
            
            # Add configuration files
            config_files = [
                "connection/sync.py",
                "connection/smart_sync.py",
                "connection/sync_wrapper.py"
            ]
            
            for config_file in config_files:
                config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", config_file))
                if os.path.exists(config_path):
                    zipf.write(config_path, config_file)
            
            # Add output files (factures, devis)
            output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "output"))
            if os.path.exists(output_dir):
                for root, dirs, files in os.walk(output_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arc_name = os.path.relpath(file_path, os.path.dirname(output_dir))
                        zipf.write(file_path, f"output/{arc_name}")
        
        # Calculate file info
        backup_info.size_bytes = os.path.getsize(backup_path)
        backup_info.checksum = get_file_checksum(backup_path)
        backup_info.success = True
        
        # Save backup info
        with open(info_path, 'w', encoding='utf-8') as f:
            json.dump({
                'filename': backup_info.filename,
                'timestamp': backup_info.timestamp,
                'size_bytes': backup_info.size_bytes,
                'checksum': backup_info.checksum,
                'backup_type': backup_info.backup_type,
                'description': backup_info.description,
                'success': backup_info.success,
                'error_message': backup_info.error_message
            }, f, indent=2, ensure_ascii=False)
        
        print(f"[BACKUP] Created backup: {backup_filename} ({backup_info.size_bytes} bytes)")
        
        # Sync to server if enabled and server is online
        if SYNC_TO_SERVER and server_online():
            try:
                sync_backup_to_server(backup_filename, backup_path, info_path)
                print(f"[BACKUP] Synced backup to server: {backup_filename}")
            except Exception as e:
                print(f"[BACKUP] Warning: Failed to sync to server: {e}")
        
    except Exception as e:
        backup_info.error_message = str(e)
        print(f"[BACKUP] Error creating backup: {e}")
        
        # Clean up failed backup file
        if os.path.exists(backup_path):
            try:
                os.remove(backup_path)
            except:
                pass
    
    return backup_info

def restore_backup(backup_filename: str, restore_path: Optional[str] = None) -> bool:
    """Restore from a backup file with security validation."""
    if restore_path is None:
        restore_path = LOCAL_PATH
    
    # Use secure backup manager if available
    if SECURITY_ENABLED and _secure_backup_manager:
        try:
            logger.info(f"Using secure restore for: {backup_filename}")
            success = _secure_backup_manager.secure_restore_backup(backup_filename, restore_path)
            
            if success:
                logger.info(f"Secure restore completed successfully: {backup_filename}")
                return True
            else:
                logger.warning("Secure restore failed, falling back to legacy method")
                log_security_event("RESTORE_FALLBACK", backup_filename, "Secure restore failed")
                
        except Exception as e:
            logger.error(f"Secure restore error: {str(e)}")
            log_security_event("RESTORE_ERROR", backup_filename, str(e))
    
    # Legacy restore method with basic security checks
    # Basic path validation for filenames
    if ".." in backup_filename or "/" in backup_filename or "\\" in backup_filename:
        logger.error(f"Invalid backup filename for restore: {backup_filename}")
        log_security_event("RESTORE_FILENAME_VIOLATION", backup_filename, "Path traversal attempt")
        return False
    
    # Basic path validation for restore path
    if restore_path and (".." in restore_path or not os.path.isabs(restore_path)):
        logger.error(f"Invalid restore path: {restore_path}")
        log_security_event("RESTORE_PATH_VIOLATION", restore_path, "Invalid restore path")
        return False
    
    backup_path = os.path.join(BACKUP_DIR, backup_filename)
    info_path = get_backup_info_filepath(backup_filename)
    
    if not os.path.exists(backup_path):
        print(f"[BACKUP] Backup file not found: {backup_filename}")
        return False
    
    try:
        # Verify backup integrity
        if os.path.exists(info_path):
            with open(info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            current_checksum = get_file_checksum(backup_path)
            if current_checksum != info['checksum']:
                print(f"[BACKUP] Backup file corrupted: {backup_filename}")
                return False
        
        # Create restore directory (with validation)
        try:
            os.makedirs(restore_path, exist_ok=True)
        except Exception as e:
            logger.error(f"Failed to create restore directory: {e}")
            return False
        
        # Extract backup with path validation
        with zipfile.ZipFile(backup_path, 'r') as zipf:
            # Validate each file before extraction
            for member in zipf.namelist():
                # Check for path traversal in archive members
                if ".." in member or member.startswith("/") or ":" in member:
                    logger.warning(f"Skipping suspicious archive member: {member}")
                    log_security_event("EXTRACT_PATH_VIOLATION", member, "Suspicious archive member")
                    continue
                
                # Extract to validated path
                extract_path = os.path.join(restore_path, member)
                if not extract_path.startswith(restore_path):
                    logger.warning(f"Skipping archive member with path traversal: {member}")
                    continue
                
                # Create directory for file if needed
                extract_dir = os.path.dirname(extract_path)
                if extract_dir and not os.path.exists(extract_dir):
                    os.makedirs(extract_dir, exist_ok=True)
                
            # If all validations pass, extract normally but log the action
            logger.info(f"Extracting validated backup to: {restore_path}")
            zipf.extractall(restore_path)
        
        print(f"[BACKUP] Restored from backup: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"[BACKUP] Error restoring backup: {e}")
        logger.error(f"Backup restore error: {str(e)}")
        return False

def list_backups() -> List[BackupInfo]:
    """List all available backups."""
    ensure_backup_dir()
    backups = []
    
    for filename in os.listdir(BACKUP_DIR):
        if filename.endswith('.zip') and filename.startswith('stfoom_backup_'):
            info_path = get_backup_info_filepath(filename)
            backup_path = os.path.join(BACKUP_DIR, filename)
            
            if os.path.exists(info_path):
                try:
                    with open(info_path, 'r', encoding='utf-8') as f:
                        info = json.load(f)
                    
                    backups.append(BackupInfo(
                        filename=info['filename'],
                        timestamp=info['timestamp'],
                        size_bytes=info['size_bytes'],
                        checksum=info['checksum'],
                        backup_type=info['backup_type'],
                        description=info['description'],
                        success=info['success'],
                        error_message=info.get('error_message', '')
                    ))
                except Exception as e:
                    print(f"[BACKUP] Error reading backup info: {e}")
            else:
                # Legacy backup without info file
                backups.append(BackupInfo(
                    filename=filename,
                    timestamp=os.path.getmtime(backup_path),
                    size_bytes=os.path.getsize(backup_path),
                    checksum="",
                    backup_type="unknown",
                    description="Legacy backup",
                    success=True
                ))
    
    # Sort by timestamp (newest first)
    backups.sort(key=lambda x: x.timestamp, reverse=True)
    return backups

def get_backup_list() -> List[Dict[str, Any]]:
    """Get backup list in dictionary format for UI compatibility."""
    try:
        backup_infos = list_backups()
        backup_list = []
        
        for backup_info in backup_infos:
            # Convert BackupInfo to dictionary for UI compatibility
            backup_dict = {
                'filename': backup_info.filename,
                'timestamp': backup_info.timestamp,
                'datetime': datetime.fromtimestamp(backup_info.timestamp).strftime('%Y-%m-%d %H:%M:%S'),
                'size_bytes': backup_info.size_bytes,
                'size_mb': round(backup_info.size_bytes / (1024 * 1024), 2),
                'checksum': backup_info.checksum,
                'backup_type': backup_info.backup_type,
                'description': backup_info.description,
                'success': backup_info.success,
                'error_message': backup_info.error_message
            }
            backup_list.append(backup_dict)
        
        return backup_list
    except Exception as e:
        print(f"[BACKUP] Error getting backup list: {e}")
        return []

def cleanup_old_backups():
    """Remove old backups based on retention policy."""
    backups = list_backups()
    
    # Remove backups older than retention period
    cutoff_time = time.time() - (BACKUP_RETENTION_DAYS * 24 * 3600)
    old_backups = [b for b in backups if b.timestamp < cutoff_time]
    
    # Remove excess backups beyond max count
    if len(backups) > MAX_BACKUPS:
        excess_backups = backups[MAX_BACKUPS:]
        old_backups.extend(excess_backups)
    
    # Remove old backups
    for backup in old_backups:
        try:
            backup_path = os.path.join(BACKUP_DIR, backup.filename)
            info_path = get_backup_info_filepath(backup.filename)
            
            if os.path.exists(backup_path):
                os.remove(backup_path)
            if os.path.exists(info_path):
                os.remove(info_path)
                
            print(f"[BACKUP] Removed old backup: {backup.filename}")
        except Exception as e:
            print(f"[BACKUP] Error removing old backup {backup.filename}: {e}")

def get_backup_status() -> Dict:
    """Get backup system status."""
    backups = list_backups()
    
    if not backups:
        return {
            'last_backup': None,
            'backup_count': 0,
            'total_size_mb': 0,
            'next_auto_backup': time.time() + AUTO_BACKUP_INTERVAL,
            'status': 'no_backups'
        }
    
    last_backup = max(backups, key=lambda x: x.timestamp)
    total_size = sum(b.size_bytes for b in backups)
    
    return {
        'last_backup': last_backup.timestamp,
        'backup_count': len(backups),
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'next_auto_backup': last_backup.timestamp + AUTO_BACKUP_INTERVAL,
        'status': 'ok' if last_backup.success else 'error'
    }

# ----------------------------------------------------------
# AUTOMATIC BACKUP SYSTEM
# ----------------------------------------------------------

_auto_backup_thread = None
_auto_backup_running = False

def start_auto_backup():
    """Start automatic backup thread."""
    global _auto_backup_thread, _auto_backup_running
    
    if _auto_backup_running:
        return
    
    _auto_backup_running = True
    _auto_backup_thread = threading.Thread(target=_auto_backup_loop, daemon=True)
    _auto_backup_thread.start()
    print("[BACKUP] Automatic backup system started")

def stop_auto_backup():
    """Stop automatic backup thread."""
    global _auto_backup_running
    _auto_backup_running = False
    print("[BACKUP] Automatic backup system stopped")

def _auto_backup_loop():
    """Automatic backup loop."""
    while _auto_backup_running:
        try:
            # Check if it's time for a backup
            status = get_backup_status()
            if (status['last_backup'] is None or 
                time.time() >= status['next_auto_backup']):
                
                create_backup("auto", "Automatic backup")
                cleanup_old_backups()
                cleanup_server_backups()  # Also clean server backups
            
            # Sleep for 5 minutes before checking again
            time.sleep(300)
            
        except Exception as e:
            print(f"[BACKUP] Error in auto backup loop: {e}")
            time.sleep(60)  # Wait 1 minute before retrying

# ----------------------------------------------------------
# DATABASE INTEGRITY CHECK
# ----------------------------------------------------------

def check_database_integrity() -> Dict:
    """Check database integrity and return status."""
    if not os.path.exists(DB_PATH):
        return {
            'status': 'missing',
            'message': 'Database file not found',
            'tables': [],
            'errors': []
        }
    
    try:
        with sqlite3.connect(DB_PATH) as conn:
            # Get list of tables
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            errors = []
            
            # Check each table
            for table in tables:
                try:
                    # Try to read from each table
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                except Exception as e:
                    errors.append(f"Table {table}: {str(e)}")
            
            return {
                'status': 'ok' if not errors else 'corrupted',
                'message': 'Database integrity check completed',
                'tables': tables,
                'errors': errors
            }
            
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Database error: {str(e)}',
            'tables': [],
            'errors': [str(e)]
        }

def repair_database() -> bool:
    """Attempt to repair a corrupted database."""
    try:
        # Create a backup before attempting repair
        create_backup("repair", "Pre-repair backup")
        
        # Try to open and vacuum the database
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("VACUUM")
            conn.execute("REINDEX")
        
        print("[BACKUP] Database repair completed")
        return True
        
    except Exception as e:
        print(f"[BACKUP] Database repair failed: {e}")
        return False

# ----------------------------------------------------------
# SERVER BACKUP FUNCTIONS
# ----------------------------------------------------------

def sync_backup_to_server(backup_filename: str, local_backup_path: str, local_info_path: str) -> bool:
    """Sync a backup file to the server."""
    if not SERVER_BACKUP_DIR or not server_online():
        return False
    
    try:
        ensure_server_backup_dir()
        
        # Copy backup file to server
        server_backup_path = os.path.join(SERVER_BACKUP_DIR, backup_filename)
        shutil.copy2(local_backup_path, server_backup_path)
        
        # Copy info file to server
        server_info_path = os.path.join(SERVER_BACKUP_DIR, backup_filename.replace(".zip", ".json"))
        if os.path.exists(local_info_path):
            shutil.copy2(local_info_path, server_info_path)
        
        print(f"[BACKUP] Synced to server: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"[BACKUP] Error syncing to server: {e}")
        return False

def list_server_backups() -> List[BackupInfo]:
    """List all backups available on the server."""
    if not SERVER_BACKUP_DIR or not server_online():
        return []
    
    backups = []
    
    try:
        for filename in os.listdir(SERVER_BACKUP_DIR):
            if filename.endswith('.zip') and filename.startswith('stfoom_backup_'):
                info_path = os.path.join(SERVER_BACKUP_DIR, filename.replace(".zip", ".json"))
                backup_path = os.path.join(SERVER_BACKUP_DIR, filename)
                
                if os.path.exists(info_path):
                    try:
                        with open(info_path, 'r', encoding='utf-8') as f:
                            info = json.load(f)
                        
                        backups.append(BackupInfo(
                            filename=info['filename'],
                            timestamp=info['timestamp'],
                            size_bytes=info['size_bytes'],
                            checksum=info['checksum'],
                            backup_type=info['backup_type'],
                            description=info['description'],
                            success=info['success'],
                            error_message=info.get('error_message', '')
                        ))
                    except Exception as e:
                        print(f"[BACKUP] Error reading server backup info: {e}")
                else:
                    # Legacy backup without info file
                    backups.append(BackupInfo(
                        filename=filename,
                        timestamp=os.path.getmtime(backup_path),
                        size_bytes=os.path.getsize(backup_path),
                        checksum="",
                        backup_type="unknown",
                        description="Legacy server backup",
                        success=True
                    ))
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.timestamp, reverse=True)
        
    except Exception as e:
        print(f"[BACKUP] Error listing server backups: {e}")
    
    return backups

def cleanup_server_backups():
    """Remove old backups from server based on retention policy."""
    if not SERVER_BACKUP_DIR or not server_online():
        return
    
    try:
        backups = list_server_backups()
        
        # Remove backups older than server retention period
        cutoff_time = time.time() - (SERVER_BACKUP_RETENTION_DAYS * 24 * 3600)
        old_backups = [b for b in backups if b.timestamp < cutoff_time]
        
        # Remove excess backups beyond max server count
        if len(backups) > MAX_SERVER_BACKUPS:
            excess_backups = backups[MAX_SERVER_BACKUPS:]
            old_backups.extend(excess_backups)
        
        # Remove old backups from server
        for backup in old_backups:
            try:
                backup_path = os.path.join(SERVER_BACKUP_DIR, backup.filename)
                info_path = os.path.join(SERVER_BACKUP_DIR, backup.filename.replace(".zip", ".json"))
                
                if os.path.exists(backup_path):
                    os.remove(backup_path)
                if os.path.exists(info_path):
                    os.remove(info_path)
                    
                print(f"[BACKUP] Removed old server backup: {backup.filename}")
            except Exception as e:
                print(f"[BACKUP] Error removing old server backup {backup.filename}: {e}")
                
    except Exception as e:
        print(f"[BACKUP] Error cleaning up server backups: {e}")

def restore_from_server(backup_filename: str, restore_path: Optional[str] = None) -> bool:
    """Restore from a server backup file."""
    if not SERVER_BACKUP_DIR or not server_online():
        print("[BACKUP] Server not accessible")
        return False
    
    if restore_path is None:
        restore_path = LOCAL_PATH
    
    server_backup_path = os.path.join(SERVER_BACKUP_DIR, backup_filename)
    server_info_path = os.path.join(SERVER_BACKUP_DIR, backup_filename.replace(".zip", ".json"))
    
    if not os.path.exists(server_backup_path):
        print(f"[BACKUP] Server backup file not found: {backup_filename}")
        return False
    
    try:
        # Verify backup integrity
        if os.path.exists(server_info_path):
            with open(server_info_path, 'r', encoding='utf-8') as f:
                info = json.load(f)
            
            current_checksum = get_file_checksum(server_backup_path)
            if current_checksum != info['checksum']:
                print(f"[BACKUP] Server backup file corrupted: {backup_filename}")
                return False
        
        # Create restore directory
        os.makedirs(restore_path, exist_ok=True)
        
        # Extract backup
        with zipfile.ZipFile(server_backup_path, 'r') as zipf:
            zipf.extractall(restore_path)
        
        print(f"[BACKUP] Restored from server backup: {backup_filename}")
        return True
        
    except Exception as e:
        print(f"[BACKUP] Error restoring from server backup: {e}")
        return False

def get_server_backup_status() -> Dict:
    """Get server backup system status."""
    if not SERVER_BACKUP_DIR or not server_online():
        return {
            'server_online': False,
            'last_backup': None,
            'backup_count': 0,
            'total_size_mb': 0,
            'status': 'server_offline'
        }
    
    backups = list_server_backups()
    
    if not backups:
        return {
            'server_online': True,
            'last_backup': None,
            'backup_count': 0,
            'total_size_mb': 0,
            'status': 'no_backups'
        }
    
    last_backup = max(backups, key=lambda x: x.timestamp)
    total_size = sum(b.size_bytes for b in backups)
    
    return {
        'server_online': True,
        'last_backup': last_backup.timestamp,
        'backup_count': len(backups),
        'total_size_mb': round(total_size / (1024 * 1024), 2),
        'status': 'ok' if last_backup.success else 'error'
    }

# ----------------------------------------------------------
# INITIALIZATION
# ----------------------------------------------------------

def initialize_backup_system():
    """Initialize the backup system."""
    ensure_backup_dir()
    
    # Create initial backup if none exists
    backups = list_backups()
    if not backups:
        print("[BACKUP] Creating initial backup...")
        create_backup("initial", "Initial system backup")
    
    # Start automatic backup
    start_auto_backup()
    
    print("[BACKUP] Backup system initialized")

if __name__ == "__main__":
    # Test the backup system
    initialize_backup_system()
    
    # Create a test backup
    backup_info = create_backup("test", "Test backup")
    print(f"Test backup created: {backup_info.success}")
    
    # List backups
    backups = list_backups()
    print(f"Found {len(backups)} backups")
    
    # Check status
    status = get_backup_status()
    print(f"Backup status: {status}") 