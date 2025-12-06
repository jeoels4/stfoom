"""
Minimal secure_database shim exposing exec_read_all used by UI modules.
Uses the centralized DB path via app.core.path_manager if available.
"""
from __future__ import annotations
import sqlite3
import os


def _get_db_path() -> str:
    try:
        from app.core.path_manager import get_db_path
        return get_db_path()
    except Exception:
        return os.path.join(os.getcwd(), 'data', 'stfoom.db')


def exec_read_all(sql: str, params: tuple | None = None):
    db = _get_db_path()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.execute(sql, params or ())
        return cur.fetchall()


def exec_read_one(sql: str, params: tuple | None = None):
    db = _get_db_path()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.execute(sql, params or ())
        return cur.fetchone()


def exec_read_dicts(sql: str, params: tuple | None = None):
    db = _get_db_path()
    with sqlite3.connect(db) as con:
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(sql, params or ())
        rows = cur.fetchall()
        return [dict(r) for r in rows]


def exec_write(sql: str, params: tuple | None = None):
    db = _get_db_path()
    with sqlite3.connect(db) as con:
        cur = con.cursor()
        cur.execute(sql, params or ())
        con.commit()
        try:
            return cur.lastrowid
        except Exception:
            return None
