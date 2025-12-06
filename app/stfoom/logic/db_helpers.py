"""
Centralized DB helpers for insert, update, and soft delete with automatic timestamps.
"""
import sqlite3
from datetime import datetime, timezone
from app.stfoom.logic.secure_database import _get_db_path

def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()

def insert_row(table: str, data: dict):
    db = _get_db_path()
    now = utc_now_iso()
    data.setdefault('created_at', now)
    data.setdefault('updated_at', now)
    columns = ','.join(data.keys())
    placeholders = ','.join('?' for _ in data)
    sql = f'INSERT INTO {table} ({columns}) VALUES ({placeholders})'
    with sqlite3.connect(db) as con:
        con.execute(sql, tuple(data.values()))
    # Update parking lot dispenser timestamp
    from config.settings import update_last_change_timestamp
    update_last_change_timestamp()

def update_row(table: str, pk_col: str, pk_val, data: dict):
    db = _get_db_path()
    now = utc_now_iso()
    data['updated_at'] = now
    set_clause = ','.join(f'{k}=?' for k in data)
    sql = f'UPDATE {table} SET {set_clause} WHERE {pk_col}=?'
    with sqlite3.connect(db) as con:
        con.execute(sql, tuple(data.values()) + (pk_val,))
    # Update parking lot dispenser timestamp
    from config.settings import update_last_change_timestamp
    update_last_change_timestamp()

def soft_delete_row(table: str, pk_col: str, pk_val):
    db = _get_db_path()
    now = utc_now_iso()
    sql = f'UPDATE {table} SET deleted=1, updated_at=? WHERE {pk_col}=?'
    with sqlite3.connect(db) as con:
        con.execute(sql, (now, pk_val))
    # Update parking lot dispenser timestamp
    from config.settings import update_last_change_timestamp
    update_last_change_timestamp()
