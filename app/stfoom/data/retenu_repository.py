"""
PHASE 2F MIGRATION - RETENU REPOSITORY
=====================================
Data access layer for retenu (retention/withholding) operations.

This repository handles all database operations for retenu records,
including CRUD operations, filtering, and aggregate queries.
"""

import os
import os as _os
import sqlite3
from typing import List, Dict, Optional, Any
from datetime import datetime
from app.connection import sync
from app.stfoom.logic.db_helpers import insert_row, update_row
from datetime import datetime
# Connection pool removed - using direct SQLite connections  
# from stfoom.logic.connection_pool import get_pooled_connection

# Get database path
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from config.settings import get_db_path

# Verbosity control for retenu logs: set env STFOOM_DEBUG_RETENU=1 to enable
_DEBUG_RETENU = _os.environ.get("STFOOM_DEBUG_RETENU", "0") == "1"

def _ret_repo_debug(msg: str):
    if _DEBUG_RETENU:
        try:
            print(msg)
        except Exception:
            pass
DATABASE_PATH = get_db_path()


class RetenuRepository:
    """
    Repository for retenu data access operations.
    
    Handles all database interactions for retenu records,
    including table initialization, CRUD operations, and reporting queries.
    """
    
    def __init__(self):
        """Initialize RetenuRepository and ensure database table exists."""
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        self.db_path = os.path.join(self.data_dir, "stfoom.db")
        self.create_table_if_not_exists()
    _ret_repo_debug("[RETENU REPOSITORY] Initialized with connection pooling")
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get database connection - using direct SQLite connection."""
        conn = sqlite3.connect(DATABASE_PATH)
        conn.row_factory = sqlite3.Row  # This enables dictionary-like access
        return conn
    
    def create_table_if_not_exists(self):
        """Create the retenus table if it doesn't exist."""
        try:
            with self._get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS retenus (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        client TEXT NOT NULL,
                        nfacture INTEGER,
                        retenu_percent REAL,
                        retenu_amount REAL,
                        party_type TEXT, -- 'client' or 'fournisseur'
                        source TEXT NOT NULL,
                        notes TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Backfill migration: ensure party_type column exists for older DBs
                try:
                    conn.execute("ALTER TABLE retenus ADD COLUMN party_type TEXT")
                except Exception:
                    pass
                conn.commit()
                _ret_repo_debug("[RETENU REPOSITORY] Table initialization completed")
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error creating table: {e}")
    
    def add_retenu(self, date: str, client: str, nfacture: Optional[int],
                   percent: float, amount: float, source: str, notes: str = "",
                   party_type: Optional[str] = None) -> bool:
        """
        Add a new retenu record to the database.
        
        Args:
            date: Date in YYYY-MM-DD format
            client: Client name
            nfacture: Optional invoice number
            percent: Retention percentage
            amount: Retention amount
            source: Source of the retention
            notes: Additional notes
            
        Returns:
            True if insertion successful, False otherwise
        """
        try:
            data = {
                "date": date,
                "client": client,
                "nfacture": nfacture,
                "retenu_percent": percent,
                "retenu_amount": amount,
                "party_type": party_type,
                "source": source,
                "notes": notes
            }
            
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            
            insert_row("retenus", data)
            
            _ret_repo_debug(f"[RETENU REPOSITORY] Added retenu for client: {client}")
            return True
            
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error adding retenu: {e}")
            return False
    
    def delete_retenu(self, retenu_id: int) -> bool:
        """
        Delete a retenu record from the database.
        
        Args:
            retenu_id: ID of the retenu to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            update_row("retenus", "id", retenu_id, {'deleted_at': datetime.now().timestamp()})
            
            _ret_repo_debug(f"[RETENU REPOSITORY] Soft deleted retenu ID: {retenu_id}")
            return True
            
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error deleting retenu {retenu_id}: {e}")
            return False
    
    def update_retenu(self, retenu_id: int, **fields) -> bool:
        """
        Update a retenu record in the database.
        
        Args:
            retenu_id: ID of the retenu to update
            **fields: Fields to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if not fields:
                print("[RETENU REPOSITORY] No fields provided for update")
                return False
            
            update_row("retenus", "id", retenu_id, fields)
            
            _ret_repo_debug(f"[RETENU REPOSITORY] Updated retenu ID: {retenu_id}")
            return True
            
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error updating retenu {retenu_id}: {e}")
            return False
    
    def get_all_retenus(self) -> List[Dict[str, Any]]:
        """
        Get all retenu records ordered by date (newest first).
        
        Returns:
            List of retenu dictionaries
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, date, client, nfacture, retenu_percent, retenu_amount,
                           party_type, source, notes, created_at
                    FROM retenus 
                    WHERE (deleted = 0 OR deleted IS NULL)
                    ORDER BY date DESC, id DESC
                """)
                
                rows = cursor.fetchall()
                retenus = [dict(row) for row in rows]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(retenus)} retenu records")
                return retenus
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving all retenus: {e}")
            return []
    
    def get_retenus_by_client(self, client: str) -> List[Dict[str, Any]]:
        """
        Get all retenu records for a specific client.
        
        Args:
            client: Client name to filter by
            
        Returns:
            List of retenu dictionaries for the specified client
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, date, client, nfacture, retenu_percent, retenu_amount,
                           party_type, source, notes, created_at
                    FROM retenus 
                    WHERE client = ? AND (deleted = 0 OR deleted IS NULL)
                    ORDER BY date DESC, id DESC
                """, (client,))
                
                rows = cursor.fetchall()
                retenus = [dict(row) for row in rows]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(retenus)} retenus for client: {client}")
                return retenus
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving retenus for client {client}: {e}")
            return []
    
    def get_retenus_by_facture(self, nfacture: int) -> List[Dict[str, Any]]:
        """
        Get all retenu records for a specific invoice number.
        
        Args:
            nfacture: Invoice number to filter by
            
        Returns:
            List of retenu dictionaries for the specified invoice
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT id, date, client, nfacture, retenu_percent, retenu_amount,
                           party_type, source, notes, created_at
                    FROM retenus 
                    WHERE nfacture = ? AND (deleted = 0 OR deleted IS NULL)
                    ORDER BY date DESC, id DESC
                """, (nfacture,))
                
                rows = cursor.fetchall()
                retenus = [dict(row) for row in rows]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(retenus)} retenus for invoice: {nfacture}")
                return retenus
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving retenus for invoice {nfacture}: {e}")
            return []
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of retenu data.
        
        Returns:
            Dictionary containing total amounts and breakdowns by client and month
        """
        try:
            with self._get_connection() as conn:
                # Get total amount
                total_cursor = conn.execute("SELECT SUM(retenu_amount) as total FROM retenus WHERE (deleted = 0 OR deleted IS NULL)")
                total_row = total_cursor.fetchone()
                total_amount = total_row['total'] if total_row and total_row['total'] else 0
                
                # Get breakdown by client
                client_cursor = conn.execute("""
                    SELECT client, SUM(retenu_amount) as total 
                    FROM retenus 
                    WHERE (deleted = 0 OR deleted IS NULL)
                    GROUP BY client 
                    ORDER BY total DESC
                """)
                by_client = {row['client']: row['total'] for row in client_cursor.fetchall()}
                
                # Get breakdown by month
                month_cursor = conn.execute("""
                    SELECT substr(date, 1, 7) as month, SUM(retenu_amount) as total 
                    FROM retenus 
                    WHERE (deleted = 0 OR deleted IS NULL)
                    GROUP BY month 
                    ORDER BY month DESC
                """)
                by_month = {row['month']: row['total'] for row in month_cursor.fetchall()}
                
                summary = {
                    'total': total_amount,
                    'by_client': by_client,
                    'by_month': by_month
                }
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Generated summary: {total_amount} total")
                return summary
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error generating summary: {e}")
            return {
                'total': 0,
                'by_client': {},
                'by_month': {}
            }
    
    def get_retenus_with_filters(self, client_filter: Optional[str] = None,
                                facture_filter: Optional[int] = None,
                                date_from: Optional[str] = None,
                                date_to: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get retenu records with optional filters.
        
        Args:
            client_filter: Optional client name filter
            facture_filter: Optional invoice number filter
            date_from: Optional start date filter (YYYY-MM-DD)
            date_to: Optional end date filter (YYYY-MM-DD)
            
        Returns:
            List of filtered retenu dictionaries
        """
        try:
            query = """
                SELECT id, date, client, nfacture, retenu_percent, retenu_amount,
                       party_type, source, notes, created_at
                FROM retenus 
                WHERE (deleted = 0 OR deleted IS NULL)
            """
            params = []
            
            if client_filter:
                query += " AND client LIKE ?"
                params.append(f"%{client_filter}%")
            
            if facture_filter:
                query += " AND nfacture = ?"
                params.append(facture_filter)
            
            if date_from:
                query += " AND date >= ?"
                params.append(date_from)
            
            if date_to:
                query += " AND date <= ?"
                params.append(date_to)
            
            query += " ORDER BY date DESC, id DESC"
            
            with self._get_connection() as conn:
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                retenus = [dict(row) for row in rows]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(retenus)} filtered retenus")
                return retenus
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving filtered retenus: {e}")
            return []
    
    def get_client_list(self) -> List[str]:
        """
        Get list of unique client names from retenu records.
        
        Returns:
            List of unique client names
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT client 
                    FROM retenus 
                    WHERE client IS NOT NULL AND client != '' AND (deleted = 0 OR deleted IS NULL)
                    ORDER BY client
                """)
                
                clients = [row['client'] for row in cursor.fetchall()]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(clients)} unique clients")
                return clients
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving client list: {e}")
            return []
    
    def get_invoice_list(self) -> List[int]:
        """
        Get list of unique invoice numbers from retenu records.
        
        Returns:
            List of unique invoice numbers
        """
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT nfacture 
                    FROM retenus 
                    WHERE nfacture IS NOT NULL AND (deleted = 0 OR deleted IS NULL)
                    ORDER BY nfacture DESC
                """)
                
                invoices = [row['nfacture'] for row in cursor.fetchall()]
                
                _ret_repo_debug(f"[RETENU REPOSITORY] Retrieved {len(invoices)} unique invoices")
                return invoices
                
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error retrieving invoice list: {e}")
            return []
    
    def formater_montant(self, montant: float) -> str:
        """
        Format amount with thousand separators and currency.
        
        Args:
            montant: Amount to format
            
        Returns:
            Formatted amount string
        """
        try:
            if not isinstance(montant, (int, float)):
                return "0.00 DZD"
            
            # Format with thousand separators
            formatted = f"{montant:,.3f}".replace(',', ' ')
            return f"{formatted} DZD"
            
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error formatting amount: {e}")
            return "0.00 DZD"
    
    def formater_date(self, date_str: str) -> str:
        """
        Format date string for display.
        
        Args:
            date_str: Date string in YYYY-MM-DD format
            
        Returns:
            Formatted date string in DD/MM/YYYY format
        """
        try:
            if not date_str:
                return ""
            
            # Parse YYYY-MM-DD format and convert to DD/MM/YYYY
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.strftime('%d/%m/%Y')
            
        except Exception as e:
            print(f"[RETENU REPOSITORY] Error formatting date: {e}")
            return date_str  # Return original if formatting fails

    # ===== GENERIC CRUD INTERFACE FOR SYNC TESTING =====

    def create(self, data: Dict) -> bool:
        """
        Generic create method for sync testing.
        
        Args:
            data: Dictionary containing retenu information
            
        Returns:
            True if created successfully, False otherwise
        """
        return self.add_retenu(
            date=data['date'],
            client=data['client'],
            nfacture=data.get('nfacture'),
            percent=data['retenu_percent'],  # Map retenu_percent to percent parameter
            amount=data['retenu_amount'],
            source=data['source'],
            notes=data.get('notes', ''),
            party_type=data.get('party_type')
        )
    
    def update(self, retenu_id: int, data: Dict) -> bool:
        """
        Generic update method for sync testing.
        
        Args:
            retenu_id: The ID of the retenu to update
            data: Dictionary containing updated retenu information
            
        Returns:
            True if updated successfully, False otherwise
        """
        return self.update_retenu(retenu_id, **data)
    
    def delete(self, retenu_id: int) -> bool:
        """
        Generic delete method for sync testing (soft delete).
        
        Args:
            retenu_id: The ID of the retenu to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        return self.delete_retenu(retenu_id)
    
    def get_all(self) -> List[Dict[str, Any]]:
        """
        Generic get_all method for sync testing.
        
        Returns:
            List of all retenu dictionaries
        """
        return self.get_all_retenus()
