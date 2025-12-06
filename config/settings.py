"""
Minimal config.settings shim
Provides get_db_path used by services and main.
NOW DELEGATES TO PATH_MANAGER FOR CONSISTENT PATH RESOLUTION.
"""
from __future__ import annotations
import os


def get_db_path() -> str:
    """Get database path - delegates to path_manager for consistency."""
    try:
        # Delegate to centralized path manager
        from app.core.path_manager import path_manager
        return path_manager.db_path
    except Exception as e:
        # Fallback for import issues (shouldn't happen in normal operation)
        print(f"[SETTINGS] Warning: Could not import path_manager, using fallback: {e}")
        import sys
        if getattr(sys, 'frozen', False):
            # Fallback for frozen: use LOCALAPPDATA
            local_appdata = os.environ.get('LOCALAPPDATA', os.path.dirname(sys.executable))
            base = os.path.join(local_appdata, 'STFOOM', 'data')
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, 'stfoom.db')
        else:
            # Fallback for dev: use current working directory
            base = os.path.join(os.getcwd(), 'data')
            os.makedirs(base, exist_ok=True)
            return os.path.join(base, 'stfoom.db')


def get_data_dir() -> str:
    """Get the data directory path - delegates to path_manager for consistency."""
    try:
        # Delegate to centralized path manager
        from app.core.path_manager import path_manager
        return str(path_manager.data_path)
    except Exception as e:
        # Fallback for import issues
        print(f"[SETTINGS] Warning: Could not import path_manager, using fallback: {e}")
        import sys
        if getattr(sys, 'frozen', False):
            # Fallback for frozen: use LOCALAPPDATA
            local_appdata = os.environ.get('LOCALAPPDATA', os.path.dirname(sys.executable))
            base = os.path.join(local_appdata, 'STFOOM', 'data')
            os.makedirs(base, exist_ok=True)
            return base
        else:
            # Fallback for dev: use current working directory
            base = os.path.join(os.getcwd(), 'data')
            os.makedirs(base, exist_ok=True)
            return base


def get_last_change_timestamp() -> float:
    """Get the last time any local database change was made (parking lot dispenser timestamp)."""
    try:
        timestamp_file = os.path.join(get_data_dir(), 'last_change_timestamp.txt')
        if os.path.exists(timestamp_file):
            with open(timestamp_file, 'r') as f:
                return float(f.read().strip())
        return 0.0
    except Exception:
        return 0.0


def update_last_change_timestamp():
    """Update the last change timestamp to current time."""
    try:
        import time
        timestamp_file = os.path.join(get_data_dir(), 'last_change_timestamp.txt')
        with open(timestamp_file, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass  # Fail silently - timestamp tracking is not critical
