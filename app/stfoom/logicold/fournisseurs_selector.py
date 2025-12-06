"""
Fournisseur management - data layer
Pure data layer - 100% SQLite (no Tkinter here)
Similar to clients_selector but for suppliers with 411xxx prefix.
"""

from __future__ import annotations
import os, pandas as pd
import sqlite3
from app.stfoom.logic.secure_database import _get_db_path
from typing import List



# ✅ SECURITY COMPLIANCE: Use centralized configuration instead of hardcoded paths
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))



from app.stfoom.logic.db_helpers import insert_row, update_row, soft_delete_row, utc_now_iso

# ───────────────────────── main save function ─────────────────────────
def save_fournisseurs(fournisseurs_list):
    """Save list of fournisseurs to local SQLite + queue for sync"""
    try:
        for fournisseur in fournisseurs_list:
            code_fournisseur = fournisseur.get("code_fournisseur", "")
            # Check if exists
            import sqlite3
            from app.stfoom.logic.secure_database import _get_db_path
            db = _get_db_path()
            with sqlite3.connect(db) as cn:
                existing = cn.execute("SELECT code_fournisseur FROM fournisseurs WHERE code_fournisseur = ?", (code_fournisseur,)).fetchone()
            if existing:
                update_row("fournisseurs", "code_fournisseur", code_fournisseur, {k: v for k, v in fournisseur.items() if k != "code_fournisseur"})
            else:
                insert_row("fournisseurs", fournisseur)
        print(f"[FOURNISSEUR_DATA] Saved {len(fournisseurs_list)} fournisseurs to database")
        for fournisseur in fournisseurs_list:
            insert_row("fournisseurs", fournisseur)
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error saving fournisseurs: {e}")
        raise

# ───────────────────────── load from database ─────────────────────────
def load_fournisseurs():
    """Load fournisseurs DataFrame from SQLite database"""
    try:
        db = _get_db_path()
        with sqlite3.connect(db) as cn:
            # Ensure fournisseurs table exists with correct structure
            cn.execute('''
                CREATE TABLE IF NOT EXISTS fournisseurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_fournisseur TEXT UNIQUE NOT NULL,
                    nom_fournisseur TEXT NOT NULL,
                    adresse TEXT DEFAULT '',
                    telephone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Load data
            df = pd.read_sql_query("SELECT * FROM fournisseurs ORDER BY nom_fournisseur", cn)
            print(f"[FOURNISSEUR_DATA] Loaded {len(df)} fournisseurs from database")
            return df
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error loading fournisseurs: {e}")
        # Return empty DataFrame with correct structure
        return pd.DataFrame(columns=[
            'id', 'code_fournisseur', 'nom_fournisseur', 'adresse', 
            'telephone', 'email', 'created_at', 'updated_at'
        ])

# ───────────────────────── column definitions ─────────────────────────
def basic_cols():
    """Basic required columns for fournisseurs"""
    return ["code_fournisseur", "nom_fournisseur"]

def contact_cols():
    """Contact information columns for fournisseurs"""
    return ["adresse", "telephone", "email"]

def all_cols():
    """All editable columns for fournisseurs"""
    return basic_cols() + contact_cols()

# ───────────────────────── CRUD operations ─────────────────────────
def add_fournisseur(fournisseur_data):
    """Add a single fournisseur"""
    try:
        insert_row("fournisseurs", fournisseur_data)
        print(f"[FOURNISSEUR_DATA] Added fournisseur: {fournisseur_data.get('nom_fournisseur', 'Unknown')}")
        return True
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error adding fournisseur: {e}")
        return False

def update_fournisseur(code_fournisseur, new_data):
    """Update fournisseur by code_fournisseur"""
    try:
        update_row("fournisseurs", "code_fournisseur", code_fournisseur, new_data)
        print(f"[FOURNISSEUR_DATA] Updated fournisseur: {code_fournisseur}")
        return True
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error updating fournisseur: {e}")
        return False

def delete_fournisseur(nom_fournisseur):
    """Soft delete fournisseur by nom_fournisseur"""
    try:
        db = _get_db_path()
        with sqlite3.connect(db) as cn:
            cursor = cn.execute("SELECT COUNT(*) as count FROM achats WHERE fournisseur = ?", (nom_fournisseur,))
            count = cursor.fetchone()[0]
        if count > 0:
            print(f"[FOURNISSEUR_DATA] Cannot delete fournisseur '{nom_fournisseur}' - used in {count} achat(s)")
            return False
        # Soft delete (set deleted=1, updated_at)
        soft_delete_row("fournisseurs", "nom_fournisseur", nom_fournisseur)
        print(f"[FOURNISSEUR_DATA] Soft deleted fournisseur: {nom_fournisseur}")
        return True
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error deleting fournisseur: {e}")
        return False

# ───────────────────────── code generation ─────────────────────────
def next_fournisseur_code():
    """Generate next 401xxx fournisseur code"""
    try:
        db = _get_db_path()
        with sqlite3.connect(db) as cn:
            # Ensure table exists
            cn.execute('''
                CREATE TABLE IF NOT EXISTS fournisseurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_fournisseur TEXT UNIQUE NOT NULL,
                    nom_fournisseur TEXT NOT NULL,
                    adresse TEXT DEFAULT '',
                    telephone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            # Find the highest existing 401xxx code
            cursor = cn.execute(
                "SELECT code_fournisseur FROM fournisseurs WHERE code_fournisseur LIKE '401%' ORDER BY code_fournisseur DESC LIMIT 1"
            )
            result = cursor.fetchone()
            if result:
                # Extract number and increment
                last_code = result[0]
                try:
                    last_number = int(last_code[3:])  # Get number after "401"
                    next_number = last_number + 1
                    next_code = f"401{next_number:03d}"
                except (ValueError, IndexError):
                    next_code = "401001"
            else:
                next_code = "401001"
            print(f"[FOURNISSEUR_DATA] Generated next code: {next_code}")
            return next_code
    except Exception as e:
        print(f"[FOURNISSEUR_DATA] Error generating next code: {e}")
        return "411001"