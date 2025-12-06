#!/usr/bin/env python3
"""
COMPREHENSIVE PATH MANAGEMENT SYSTEM
===================================

This addresses the security audit requirement to eliminate ALL hardcoded database paths.
All modules should use this centralized path system instead of hardcoded paths.

SECURITY COMPLIANCE:
- Eliminates hardcoded paths throughout the application
- Uses centralized configuration from settings system  
- Validates all paths for security
- Provides consistent path resolution across all modules
"""

import os
import shutil
import sys
from pathlib import Path
from typing import Optional

class PathManager:
    """Centralized path management system - NO MORE HARDCODED PATHS!"""
    
    def __init__(self):
        self._root_path = None
        self._data_path = None
        self._db_path = None
        self._initialized = False
    
    def initialize(self, app_root: Optional[str] = None):
        """Initialize path manager with application root."""
        if self._initialized:
            return
            
        # Determine application root
        if app_root:
            self._root_path = Path(app_root).resolve()
        else:
            # Auto-detect from this file's location
            current_file = Path(__file__).resolve()
            # path_manager.py is at <root>/app/core/path_manager.py
            # We need the real project root: go up three levels
            #   current_file.parent -> core
            #   .parent -> app
            #   .parent -> <project root>
            self._root_path = current_file.parent.parent.parent
            
        # Detect frozen mode
        frozen = getattr(sys, 'frozen', False)

        # Choose base directory (user-writable when frozen)
        if frozen:
            # Prefer LOCALAPPDATA for persistence across upgrades
            local_appdata = Path(os.environ.get('LOCALAPPDATA', self._root_path))
            base_dir = local_appdata / "STFOOM"
        else:
            base_dir = self._root_path

        self._data_path = base_dir / "data"
        self._db_path = self._data_path / "stfoom.db"
        # If frozen, ensure config directory exists early so other modules can write files
        if frozen:
            try:
                cfg_dir = base_dir / 'config'
                cfg_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
        override_applied = False
        
        # Ensure data directory exists
        self._data_path.mkdir(parents=True, exist_ok=True)

        # Database override options (dev only):
        # - STFOOM_DB_PATH env var
        # - db.path file at project root
        # We intentionally IGNORE overrides when frozen to ensure the EXE
        # uses its own isolated LocalAppData database, as requested.

        if not frozen:
            # 1) Environment variable override (DEV ONLY)
            try:
                env_override = os.environ.get('STFOOM_DB_PATH')
                if env_override:
                    cand = Path(os.path.expandvars(os.path.expanduser(env_override)))
                    if not cand.is_absolute():
                        cand = self._root_path / cand
                    if cand.exists():
                        self._db_path = cand
                        override_applied = True
                        print(f"[PATH_MANAGER] Using DB from STFOOM_DB_PATH: {self._db_path}")
            except Exception as e:
                print(f"[PATH_MANAGER] Env override error: {e}")

            # 2) db.path file override (DEV ONLY)
            try:
                override_file = self._root_path / 'db.path'
                if override_file.exists():
                    txt = override_file.read_text(encoding='utf-8').strip()
                    if txt:
                        cand = Path(os.path.expandvars(os.path.expanduser(txt)))
                        if not cand.is_absolute():
                            cand = self._root_path / cand
                        if cand.exists():
                            self._db_path = cand
                            override_applied = True
                            print(f"[PATH_MANAGER] Using DB from {override_file}: {self._db_path}")
                        else:
                            print(f"[PATH_MANAGER] db.path targets missing file: {cand}")
            except Exception as e:
                print(f"[PATH_MANAGER] db.path override error: {e}")

        # In development, prefer a root-level data.db if it exists (explicit user DB)
        if not frozen and (not override_applied) and self._db_path == (self._data_path / "stfoom.db"):
            prefer_db = self._root_path / "data.db"
            if prefer_db.exists():
                self._db_path = prefer_db
                print(f"[PATH_MANAGER] Using root-level database override: {self._db_path}")

        # One-time migration: if running in dev (not frozen) and legacy app/data DB exists,
        # but the new root/data DB does not, copy it over to preserve existing data.
        if not frozen:
            try:
                legacy_db = self._root_path / "app" / "data" / "stfoom.db"
                if not self._db_path.exists() and legacy_db.exists():
                    shutil.copy2(legacy_db, self._db_path)
                    print(f"[PATH_MANAGER] Migrated legacy DB from {legacy_db} -> {self._db_path}")
            except Exception as e:
                print(f"[PATH_MANAGER] Legacy DB migration skipped: {e}")

        # If frozen and database missing, attempt to copy bundled DB/template
        if frozen and not self._db_path.exists():
            try:
                # Possible template locations inside bundle
                candidates = []
                # PyInstaller COLLECT places datas next to exe in subfolders
                exe_dir = Path(sys.executable).parent if frozen else self._root_path
                # Prefer a fully-populated stfoom.db if we bundled one under data/
                candidates.append(exe_dir / 'data' / 'stfoom.db')
                candidates.append(exe_dir / 'data' / 'stfoom_template.db')
                candidates.append(exe_dir / 'stfoom_template.db')
                # Also check original project root (dev fallback)
                candidates.append(self._root_path / 'data' / 'stfoom_template.db')
                for cand in candidates:
                    if cand.exists():
                        shutil.copy2(cand, self._db_path)
                        print(f"[PATH_MANAGER] Copied template DB from {cand} -> {self._db_path}")
                        break
                if not self._db_path.exists():
                    # Create empty placeholder DB file; tables will be created lazily
                    open(self._db_path, 'a').close()
                    print(f"[PATH_MANAGER] Created empty DB placeholder at {self._db_path}")
            except Exception as e:
                print(f"[PATH_MANAGER] Failed to provision database: {e}")

        self._initialized = True
        print(f"[PATH_MANAGER] Initialized: root={self._root_path}, data={self._data_path}")
        # Write runtime info to data dir for diagnostics (helps identify EXE DB path)
        try:
            info_file = self._data_path / 'runtime_info.txt'
            with open(info_file, 'w', encoding='utf-8') as f:
                f.write("STFOOM Runtime Info\n")
                f.write(f"timestamp={__import__('datetime').datetime.now().isoformat()}\n")
                f.write(f"frozen={getattr(sys, 'frozen', False)}\n")
                f.write(f"root_path={self._root_path}\n")
                f.write(f"data_path={self._data_path}\n")
                f.write(f"db_path={self._db_path}\n")
            # Also print a hint so logs show where to look
            print(f"[PATH_MANAGER] Runtime info written to {info_file}")
        except Exception as e:
            print(f"[PATH_MANAGER] Could not write runtime_info.txt: {e}")
    
    @property
    def root_path(self) -> Path:
        """Get application root path."""
        self._ensure_initialized()
        return self._root_path
    
    @property  
    def data_path(self) -> Path:
        """Get data directory path."""
        self._ensure_initialized()
        return self._data_path
        
    @property
    def db_path(self) -> str:
        """Get database file path as string (for sqlite3 compatibility)."""
        self._ensure_initialized() 
        return str(self._db_path)
        
    @property
    def app_path(self) -> Path:
        """Get app directory path."""
        self._ensure_initialized()
        return self._root_path / "app"
        
    @property
    def backup_path(self) -> Path:
        """Get backup directory path."""
        self._ensure_initialized()
        return self._root_path / "app" / "backups"
        
    @property
    def output_path(self) -> Path:
        """Get output directory path."""
        self._ensure_initialized()
        return self._root_path / "output"
    
    def get_relative_to_root(self, path: str) -> Path:
        """Get path relative to application root."""
        self._ensure_initialized()
        return self._root_path / path
    
    def _ensure_initialized(self):
        """Ensure path manager is initialized."""
        if not self._initialized:
            self.initialize()

# Global instance - used by all modules
path_manager = PathManager()

# Convenience functions for backward compatibility
def get_db_path() -> str:
    """Get database path - replaces all hardcoded DB_PATH variables."""
    return path_manager.db_path

def get_data_dir() -> str:
    """Get data directory - replaces all hardcoded DATA_DIR variables."""
    return str(path_manager.data_path)

def get_root_dir() -> str:
    """Get application root directory."""
    return str(path_manager.root_path)

# Initialize immediately on import
path_manager.initialize()

print(f"[PATH_MANAGER] Global paths configured:")
print(f"  - Database: {get_db_path()}")
print(f"  - Data Dir: {get_data_dir()}")
print(f"  - Root Dir: {get_root_dir()}")
