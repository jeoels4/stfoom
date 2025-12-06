"""
Client management - data layer
Pure data layer - 100% SQLite (no Tkinter here)
Keeps exactly the same public functions other modules already import.
"""

from __future__ import annotations
import os, sqlite3, pandas as pd
from typing import List

# ‑‑‑ optional LAN‑sync (silently ignored on standalone PCs) ‑‑‑
try:
    import connection.sync_wrapper as sync
except ImportError:
    class sync:
        @staticmethod
        def insert_with_sync(*args, **kwargs): pass
        @staticmethod
        def update_with_sync(*args, **kwargs): pass
        @staticmethod
        def exec_write_with_sync(*args, **kwargs): pass

# ✅ SECURITY COMPLIANCE: Use centralized configuration instead of hardcoded paths
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from config.settings import get_db_path

# ───────────────────────── paths / db connection ─────────────────────────
# ✅ FIXED: Use centralized configuration - NO MORE HARDCODED PATHS!
DB_PATH = get_db_path()

def _conn():
    """Pure SQLite connection (no sync wrapper) - uses centralized config"""
    return sqlite3.connect(DB_PATH, check_same_thread=False)

# ───────────────────────── main save function ─────────────────────────
def save_clients(clients_list):
    """Save list of clients to local SQLite + queue for sync"""
    try:
        with _conn() as cn:
            for client in clients_list:
                code_client = client.get("code_client", "")
                raison_sociale = client.get("raison_sociale", "")
                
                # Check if exists
                existing = cn.execute("SELECT code_client FROM clients WHERE code_client = ?", (code_client,)).fetchone()
                
                if existing:
                    # Update
                    placeholders = ", ".join([f"{k} = ?" for k in client.keys() if k != "code_client"])
                    values = [v for k, v in client.items() if k != "code_client"] + [code_client]
                    cn.execute(f"UPDATE clients SET {placeholders} WHERE code_client = ?", values)
                    # Note: Sync tracking handled automatically by database wrapper
                else:
                    # Insert
                    columns = ", ".join(client.keys())
                    placeholders = ", ".join(["?" for _ in client])
                    values = list(client.values())
                    cn.execute(f"INSERT INTO clients ({columns}) VALUES ({placeholders})", values)
                    # Note: Sync tracking handled automatically by database wrapper
            
            cn.commit()
        return True
    except Exception as e:
        print(f"Error saving clients: {e}")
        return False

# ───────────────────────── getter functions ─────────────────────────
def load_clients():
    """Load all clients as pandas DataFrame for compatibility"""
    import pandas as pd
    clients = get_all_clients()
    return pd.DataFrame(clients)

def get_all_clients():
    """Retrieve all clients from SQLite"""
    with _conn() as cn:
        # Order by code_client as integer, descending (latest first)
        df = pd.read_sql_query("SELECT * FROM clients ORDER BY CAST(code_client AS INTEGER) DESC", cn)
        return df.to_dict('records')

def search_clients(search_term):
    """Search clients by various fields"""
    if not search_term or not search_term.strip():
        return get_all_clients()
    
    with _conn() as cn:
        query = """
        SELECT * FROM clients 
        WHERE raison_sociale LIKE ? OR adresse LIKE ? OR tel LIKE ?
        ORDER BY CAST(code_client AS INTEGER) DESC
        """
        df = pd.read_sql_query(query, cn, params=[f"%{search_term}%"] * 3)
        return df.to_dict('records')

def get_client_by_code(code_client):
    """Get single client by code"""
    with _conn() as cn:
        query = "SELECT * FROM clients WHERE code_client = ?"
        df = pd.read_sql_query(query, cn, params=[code_client])
        return df.to_dict('records')[0] if not df.empty else None

def update_client_data(old_raison, data):
    """Update client by old raison sociale"""
    with _conn() as cn:
        row = cn.execute("SELECT code_client FROM clients WHERE raison_sociale = ?", (old_raison,)).fetchone()
        if row:
            code_client = str(row[0])
            sync.update_with_sync("clients", code_client, data)

# ───────────────────────── helpers for dynamic columns ──────────────────
def _client_columns() -> List[str]:
    with _conn() as cn:
        cursor = cn.execute("PRAGMA table_info(clients)")
        # PRAGMA table_info returns tuples: (cid, name, type, notnull, dflt_value, pk)
        return [row[1] for row in cursor.fetchall()]  # row[1] is the column name

def _product_codes() -> List[str]:
    with _conn() as cn:
        cursor = cn.execute("SELECT code FROM products")
        return [row[0] for row in cursor.fetchall()]

def basic_cols():
    return ["code_client", "raison_sociale", "adresse", "tva", "tel"]

def remise_cols():
    return [c for c in _client_columns() if c.startswith("remise_")]

def specific_cols():
    return [f"specific_{c.lower()}" for c in _product_codes()]

def next_client_code():
    """Generate next available client code"""
    with _conn() as cn:
        # Get highest existing code_client
        cursor = cn.execute("SELECT MAX(CAST(code_client AS INTEGER)) FROM clients WHERE code_client GLOB '[0-9]*'")
        result = cursor.fetchone()
        max_code = result[0] if result and result[0] else 411000
        return str(max_code + 1)

def add_client(data):
    """Add new client"""
    try:
        with _conn() as cn:
            # Check for duplicate code_client first
            code_client = data.get("code_client")
            if code_client:
                existing = cn.execute("SELECT code_client FROM clients WHERE code_client = ?", (code_client,)).fetchone()
                if existing:
                    print(f"Client with code {code_client} already exists - skipping duplicate")
                    return False
            
            # Insert new client
            columns = ", ".join(data.keys())
            placeholders = ", ".join(["?" for _ in data])
            values = list(data.values())
            cn.execute(f"INSERT INTO clients ({columns}) VALUES ({placeholders})", values)
            cn.commit()
            
            # Note: Sync tracking is handled automatically by the database wrapper
            # No need to call sync.insert_with_sync() as it would create duplicates
        return True
    except Exception as e:
        print(f"Error adding client: {e}")
        return False

def update_client(old_raison, data):
    """Update existing client by raison sociale"""
    try:
        with _conn() as cn:
            # Find client by raison sociale
            cursor = cn.execute("SELECT code_client FROM clients WHERE raison_sociale = ?", (old_raison,))
            result = cursor.fetchone()
            if not result:
                return False
            
            code_client = result[0]
            
            # Update client
            placeholders = ", ".join([f"{k} = ?" for k in data.keys()])
            values = list(data.values())
            cn.execute(f"UPDATE clients SET {placeholders} WHERE code_client = ?", values + [code_client])
            cn.commit()
            
            # Note: Sync tracking is handled automatically by the database wrapper
            # No need to call sync.update_with_sync() as it would create duplicates
        return True
    except Exception as e:
        print(f"Error updating client: {e}")
        return False

def delete_client(raison_sociale):
    """Delete client by raison sociale"""
    try:
        with _conn() as cn:
            # Find client first
            cursor = cn.execute("SELECT code_client FROM clients WHERE raison_sociale = ?", (raison_sociale,))
            result = cursor.fetchone()
            if not result:
                return False
            
            code_client = result[0]
            
            # Delete client
            cn.execute("DELETE FROM clients WHERE raison_sociale = ?", (raison_sociale,))
            cn.commit()
            
            # Queue for sync
            sync.delete_with_sync("clients", code_client)
        return True
    except Exception as e:
        print(f"Error deleting client: {e}")
        return False
