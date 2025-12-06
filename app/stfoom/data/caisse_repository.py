"""
STFOOM Caisse Repository

This repository provides data access layer for cash management operations,
handling all database interactions and data transformations.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.stfoom.logic.db_helpers import insert_row, update_row
from datetime import datetime
# Connection pool removed - using direct SQLite connections
# from stfoom.logic.connection_pool import get_pooled_connection

# Get database path
from app.stfoom.logic.secure_database import _get_db_path
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)
logger = logging.getLogger(__name__)

class CaisseRepository:
    """Repository for cash transaction data access operations."""
    
    def __init__(self):
        """Initialize the caisse repository."""
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "data"))
        self.db_path = os.path.join(self.data_dir, "stfoom.db")
        self._init_db()
        logger.info("CaisseRepository initialized")
    
    def _conn(self) -> sqlite3.Connection:
        """Get database connection - using direct SQLite connection."""
        from app.stfoom.logic.secure_database import _get_db_path
        return sqlite3.connect(_get_db_path())
    
    def _init_db(self):
        """Initialize database tables."""
        try:
            with self._conn() as cn:
                cn.execute('''
                    CREATE TABLE IF NOT EXISTS caisse_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        montant REAL NOT NULL,
                        type TEXT NOT NULL,
                        description TEXT,
                        nfacture INTEGER,
                        num_facture TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                cn.commit()
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # ========================== Transaction Management ==========================
    
    def get_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """Get cash transactions with optional date filtering."""
        try:
            with self._conn() as cn:
                query = "SELECT * FROM caisse_transactions WHERE (deleted = 0 OR deleted IS NULL)"
                params = []
                
                if start_date:
                    query += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND date <= ?"
                    params.append(end_date)
                
                query += " ORDER BY date DESC, id DESC"
                
                cursor = cn.execute(query, params)
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transactions.append({
                        'id': row[0],
                        'date': row[1],
                        'montant': row[2],
                        'type': row[3],
                        'description': row[4] or '',
                        'nfacture': row[5],
                        'num_facture': row[6] or ''
                    })
                
                return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def ajouter_transaction(self, montant: float, date_str: str, type_: str, 
                           description: str = "", nfacture: Optional[int] = None, 
                           num_facture: Optional[str] = None) -> bool:
        """Add a new cash transaction using centralized DB helpers."""
        try:
            data = {
                "date": date_str,
                "montant": montant,
                "type": type_,
                "description": description,
                "nfacture": nfacture,
                "num_facture": num_facture
            }
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            insert_row("caisse_transactions", data)
            return True
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return False
    
    def supprimer_transaction(self, transaction_id: int) -> bool:
        """Soft delete a cash transaction using custom soft delete with deleted_at."""
        try:
            update_row("caisse_transactions", "id", transaction_id, {'deleted_at': datetime.now().timestamp()})
            return True
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False
    
    def modifier_transaction(self, transaction_id: int, type_transaction: str, 
                            montant: float, date_transaction: str, 
                            nfacture: Optional[int] = None, nom_client: str = "",
                            numero_recu: str = "", description: str = "",
                            mode_paiement: str = "", echeance: str = "") -> bool:
        """Update an existing cash transaction using centralized DB helpers."""
        try:
            data = {
                "date": date_transaction,
                "montant": montant,
                "type": type_transaction,
                "description": description,
                "nfacture": nfacture,
                "num_facture": nom_client  # Note: original code maps nom_client to num_facture
            }
            # Remove None values
            data = {k: v for k, v in data.items() if v is not None}
            update_row("caisse_transactions", "id", transaction_id, data)
            return True
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    # ========================== Financial Calculations ==========================
    
    def get_solde(self) -> float:
        """Get current cash balance."""
        try:
            with self._conn() as cn:
                # Get total encaissements
                cursor_enc = cn.execute(
                    "SELECT SUM(montant) as total FROM caisse_transactions WHERE type = 'encaissement' AND (deleted = 0 OR deleted IS NULL)"
                )
                encaissements = cursor_enc.fetchone()
                
                # Get total decaissements
                cursor_dec = cn.execute(
                    "SELECT SUM(montant) as total FROM caisse_transactions WHERE type = 'decaissement' AND (deleted = 0 OR deleted IS NULL)"
                )
                decaissements = cursor_dec.fetchone()
                
                total_enc = encaissements[0] if encaissements[0] is not None else 0
                total_dec = decaissements[0] if decaissements[0] is not None else 0
                
                total = total_enc - total_dec
                return float(total)
        except Exception as e:
            logger.error(f"Error calculating balance: {e}")
            return 0.0
    
    def get_resume_periode(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """Get period summary with encaissements and decaissements."""
        try:
            with self._conn() as cn:
                where_clause = "WHERE 1=1"
                params = []
                
                if start_date:
                    where_clause += " AND date >= ?"
                    params.append(start_date)
                
                if end_date:
                    where_clause += " AND date <= ?"
                    params.append(end_date)
                
                # Get encaissements summary
                enc_query = f"""SELECT COUNT(*) as n, SUM(montant) as total 
                               FROM caisse_transactions {where_clause} AND type = 'encaissement' AND (deleted = 0 OR deleted IS NULL)"""
                cursor_enc = cn.execute(enc_query, params)
                enc = cursor_enc.fetchone()
                
                # Get decaissements summary
                dec_query = f"""SELECT COUNT(*) as n, SUM(montant) as total 
                               FROM caisse_transactions {where_clause} AND type = 'decaissement' AND (deleted = 0 OR deleted IS NULL)"""
                cursor_dec = cn.execute(dec_query, params)
                dec = cursor_dec.fetchone()
                
                return {
                    'encaissements': {
                        'nombre': enc[0] if enc[0] is not None else 0,
                        'total': float(enc[1] if enc[1] is not None else 0)
                    },
                    'decaissements': {
                        'nombre': dec[0] if dec[0] is not None else 0,
                        'total': float(dec[1] if dec[1] is not None else 0)
                    },
                    'solde': self.get_solde()
                }
        except Exception as e:
            logger.error(f"Error getting period summary: {e}")
            return {
                'encaissements': {'nombre': 0, 'total': 0.0},
                'decaissements': {'nombre': 0, 'total': 0.0},
                'solde': 0.0
            }
    
    # ========================== Formatting Utilities ==========================
    
    def formater_montant(self, amount: float) -> str:
        """Format amount for display."""
        try:
            # Format with thousands separator and currency
            return f"{amount:,.3f} DZD".replace(',', ' ')
        except Exception as e:
            logger.error(f"Error formatting amount: {e}")
            return f"{amount:.3f} DZD"
    
    def formater_date(self, date_str: str) -> str:
        """Format date for display."""
        try:
            # Convert from YYYY-MM-DD to DD/MM/YYYY
            if date_str and len(date_str) >= 10:
                dt = datetime.strptime(date_str[:10], "%Y-%m-%d")
                return dt.strftime("%d/%m/%Y")
            return date_str
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date_str

    # ===== GENERIC CRUD INTERFACE FOR SYNC TESTING =====

    def create(self, data: Dict) -> bool:
        """
        Generic create method for sync testing.
        
        Args:
            data: Dictionary containing transaction information
            
        Returns:
            True if created successfully, False otherwise
        """
        return self.ajouter_transaction(
            montant=data['montant'],
            date_str=data['date'],
            type_=data['type'],
            description=data.get('description', ''),
            nfacture=data.get('nfacture'),
            num_facture=data.get('num_facture')
        )
    
    def update(self, transaction_id: int, data: Dict) -> bool:
        """
        Generic update method for sync testing.
        
        Args:
            transaction_id: The ID of the transaction to update
            data: Dictionary containing updated transaction information
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Map data fields to modifier_transaction parameters
            type_transaction = data.get('type', data.get('type_transaction', 'encaissement'))
            montant = data.get('montant', 0)
            date_transaction = data.get('date', data.get('date_transaction', ''))
            nfacture = data.get('nfacture')
            nom_client = data.get('num_facture', data.get('nom_client', ''))
            description = data.get('description', '')
            
            return self.modifier_transaction(
                transaction_id=transaction_id,
                type_transaction=type_transaction,
                montant=montant,
                date_transaction=date_transaction,
                nfacture=nfacture,
                nom_client=nom_client,
                numero_recu='',
                description=description,
                mode_paiement='',
                echeance=''
            )
        except Exception as e:
            logger.error(f"Error in update method: {e}")
            return False
    
    def delete(self, transaction_id: int) -> bool:
        """
        Generic delete method for sync testing (soft delete).
        
        Args:
            transaction_id: The ID of the transaction to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        return self.supprimer_transaction(transaction_id)
    
    def get_all(self) -> List[Dict]:
        """
        Generic get_all method for sync testing.
        
        Returns:
            List of all transaction dictionaries
        """
        return self.get_transactions()
