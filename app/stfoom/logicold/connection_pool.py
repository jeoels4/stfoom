"""
Lightweight connection pool shim for legacy logicold modules.

Purpose:
- Provide get_pooled_connection() compatible API used by legacy modules
- Use centralized DB path resolution (config.settings -> app.core.path_manager)
- Keep it simple and thread-safe enough for SQLite in our usage
"""
from __future__ import annotations

import sqlite3
import os
import threading

# Use centralized DB path resolution
try:
    from config.settings import get_db_path
except Exception:
    # Fallback: LOCALAPPDATA/STFOOM/data/stfoom.db
    def get_db_path() -> str:
        base = os.environ.get("LOCALAPPDATA") or os.getcwd()
        data_dir = os.path.join(base, "STFOOM", "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "stfoom.db")


_lock = threading.Lock()

def get_pooled_connection() -> sqlite3.Connection:
    """
    Return a new SQLite connection to the centralized DB.
    Note: For SQLite, per-thread short-lived connections are fine; a full pool adds complexity
    and often isn't necessary. This shim maintains API compatibility with legacy code.
    """
    db_path = get_db_path()
    # Ensure directory exists in case settings fallback is used
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    # check_same_thread=False to allow usage across UI callbacks if needed
    with _lock:
        return sqlite3.connect(db_path, check_same_thread=False)

__all__ = ["get_pooled_connection"]
