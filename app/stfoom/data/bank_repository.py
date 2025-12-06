"""
STFOOM Bank Repository

This repository provides data access layer for bank and transaction operations,
handling all database interactions and data transformations.
"""

# ✅ SECURITY COMPLIANCE: Use centralized configuration
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from config.settings import get_db_path, get_data_dir

import sqlite3
import logging
from typing import List, Dict, Optional
from datetime import datetime

# Get database path
DATABASE_PATH = get_db_path()
from datetime import datetime
from app.stfoom.logic.db_helpers import insert_row, update_row
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)
# Connection pool removed - using direct SQLite connections
# from stfoom.logic.connection_pool import get_pooled_connection

logger = logging.getLogger(__name__)

class BankRepository:
    """Repository for bank and transaction data access operations."""
    
    def __init__(self):
        """Initialize the bank repository."""
        self.data_dir = get_data_dir()  # ✅ FIXED: No more hardcoded paths
        self.db_path = get_db_path()  # ✅ FIXED: No more hardcoded paths
        self._init_db()
        logger.info("BankRepository initialized")
    
    def _conn(self) -> sqlite3.Connection:
        """Get database connection - using direct SQLite connection."""
        return sqlite3.connect(DATABASE_PATH)
    
    def _init_db(self):
        """Initialize bank and transaction tables if they don't exist."""
        try:
            with self._conn() as cn:
                # Banks table - compatible with existing schema
                cn.execute('''
                    CREATE TABLE IF NOT EXISTS banques (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        nom_banque TEXT NOT NULL,
                        numero_compte TEXT,
                        solde_initial REAL DEFAULT 0,
                        devise TEXT DEFAULT 'TND',
                        actif INTEGER DEFAULT 1,
                        est_defaut INTEGER DEFAULT 0
                    )
                ''')
                
                # Add created_at column if it doesn't exist (for backward compatibility)
                try:
                    cn.execute('ALTER TABLE banques ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP')
                except sqlite3.OperationalError:
                    # Column already exists or table structure doesn't allow it
                    pass
                
                # Bank transactions table - compatible with existing schema
                cn.execute('''
                    CREATE TABLE IF NOT EXISTS transactions_bancaires (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        banque_id INTEGER NOT NULL,
                        date_transaction TEXT NOT NULL,
                        type_transaction TEXT NOT NULL, -- 'encaissement' or 'decaissement'
                        montant REAL NOT NULL,
                        nfacture INTEGER,
                        nom_client TEXT,
                        numero_cheque TEXT,
                        description TEXT,
                        verifie INTEGER DEFAULT 0,
                        date_verification TEXT,
                        mode_paiement TEXT,
                        echeance TEXT,
                        FOREIGN KEY (banque_id) REFERENCES banques (id)
                    )
                ''')
                
                # Add created_at column to transactions if it doesn't exist
                try:
                    cn.execute('ALTER TABLE transactions_bancaires ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP')
                except sqlite3.OperationalError:
                    # Column already exists or table structure doesn't allow it
                    pass
                
                # Payment methods table
                cn.execute('''
                    CREATE TABLE IF NOT EXISTS payment_methods (
                        key TEXT PRIMARY KEY,
                        label TEXT NOT NULL
                    )
                ''')
                
                cn.commit()
                
                # Initialize default payment methods if table is empty
                existing_methods = cn.execute('SELECT COUNT(*) FROM payment_methods').fetchone()[0]
                if existing_methods == 0:
                    defaults = [
                        ("especes", "💵 Espèces"),
                        ("cheque", "🧾 Chèque"),
                        ("virement", "💳 Virement"),
                        ("virement_interne", "🔄 Virement Interne (Banque ↔ Caisse)"),
                        ("traite", "📄 Traite"),
                        ("cb", "💳 Carte bancaire"),
                        ("prelevement", "🔄 Prélèvement")
                    ]
                    cn.executemany('INSERT INTO payment_methods (key, label) VALUES (?, ?)', defaults)
                    cn.commit()
                
        except Exception as e:
            logger.error(f"Error initializing database: {e}")
    
    # ========================== Bank Management ==========================
    
    def get_banques(self) -> List[Dict]:
        """Get all bank accounts."""
        try:
            with self._conn() as cn:
                cursor = cn.execute('''
                    SELECT id, nom_banque, numero_compte, solde_initial, est_defaut
                    FROM banques ORDER BY nom_banque
                ''')
                rows = cursor.fetchall()
                
                banks = []
                for row in rows:
                    banks.append({
                        'id': row[0],
                        'nom_banque': row[1],
                        'numero_compte': row[2] or '',
                        'solde_initial': row[3],
                        'est_defaut': bool(row[4])
                    })
                
                return banks
        except Exception as e:
            logger.error(f"Error getting banks: {e}")
            return []
    
    def ajouter_banque(self, nom_banque: str, numero_compte: str = "", solde_initial: float = 0) -> bool:
        """Add a new bank account."""
        try:
            data = {
                'nom_banque': nom_banque,
                'numero_compte': numero_compte,
                'solde_initial': solde_initial,
                'est_defaut': 0
            }
            
            try:
                insert_row("banques", data)
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error adding bank: {e}")
            return False
    
    def get_banque_by_id(self, banque_id: int) -> Optional[Dict]:
        """Get a bank account by ID."""
        try:
            with self._conn() as cn:
                cursor = cn.execute('''
                    SELECT id, nom_banque, numero_compte, solde_initial, est_defaut
                    FROM banques WHERE id = ?
                ''', (banque_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'nom_banque': row[1],
                        'numero_compte': row[2] or '',
                        'solde_initial': row[3],
                        'est_defaut': bool(row[4])
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting bank by ID: {e}")
            return None
    
    def modifier_banque(self, banque_id: int, nom_banque: str, numero_compte: str = "", solde_initial: float = 0) -> bool:
        """Update a bank account."""
        try:
            data = {
                'nom_banque': nom_banque,
                'numero_compte': numero_compte,
                'solde_initial': solde_initial
            }
            
            try:
                update_row("banques", "id", banque_id, data)
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error updating bank: {e}")
            return False
    
    def supprimer_banque(self, banque_id: int) -> bool:
        """Delete a bank account."""
        try:
            # Check if bank has transactions
            with self._conn() as cn:
                cursor = cn.execute('SELECT COUNT(*) FROM transactions_bancaires WHERE banque_id = ?', (banque_id,))
                transaction_count = cursor.fetchone()[0]
                
                if transaction_count > 0:
                    logger.warning(f"Cannot delete bank {banque_id}: has {transaction_count} transactions")
                    return False
            
            try:
                with self._conn() as cn:
                    cn.execute("DELETE FROM banques WHERE id = ?", (banque_id,))
                    cn.commit()
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error deleting bank: {e}")
            return False
    
    def get_banque_defaut(self) -> Optional[Dict]:
        """Get the default bank account."""
        try:
            with self._conn() as cn:
                cursor = cn.execute('''
                    SELECT id, nom_banque, numero_compte, solde_initial, est_defaut
                    FROM banques WHERE est_defaut = 1 LIMIT 1
                ''')
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'nom_banque': row[1],
                        'numero_compte': row[2] or '',
                        'solde_initial': row[3],
                        'est_defaut': bool(row[4])
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting default bank: {e}")
            return None
    
    def definir_banque_defaut(self, banque_id: int) -> bool:
        """Set the default bank account."""
        try:
            with self._conn() as cn:
                # First, remove default from all banks
                cn.execute('UPDATE banques SET est_defaut = 0')
                # Then set the new default
                cn.execute('UPDATE banques SET est_defaut = 1 WHERE id = ?', (banque_id,))
                cn.commit()
                
                # Sync changes - use direct SQL since these are simple updates
                try:
                    # These are simple updates that don't need complex sync logic
                    pass  # Skip sync for now since these are configuration changes
                except Exception as _e:
                    logger.info(f"Sync default bank update skipped/fallback: {_e}")
                return True
        except Exception as e:
            logger.error(f"Error setting default bank: {e}")
            return False
    
    # ========================== Transaction Management ==========================
    
    def get_transactions(self, banque_id: int = None, date_debut: str = None, date_fin: str = None) -> List[Dict]:
        """Get bank transactions with optional filtering."""
        try:
            with self._conn() as cn:
                query = '''
                    SELECT id, banque_id, type_transaction, montant, date_transaction,
                           description, numero_cheque, nfacture, nom_client,
                           mode_paiement, echeance, verifie, num_facture
                    FROM transactions_bancaires
                    WHERE 1=1
                '''
                params = []
                
                if banque_id is not None:
                    query += ' AND banque_id = ?'
                    params.append(banque_id)
                
                if date_debut:
                    query += ' AND date_transaction >= ?'
                    params.append(date_debut)
                
                if date_fin:
                    query += ' AND date_transaction <= ?'
                    params.append(date_fin)
                
                query += ' ORDER BY date_transaction DESC, id DESC'
                
                cursor = cn.execute(query, params)
                rows = cursor.fetchall()
                
                transactions = []
                for row in rows:
                    transactions.append({
                        'id': row[0],
                        'banque_id': row[1],
                        'type_transaction': row[2],
                        'montant': row[3],
                        'date_transaction': row[4],
                        'description': row[5] or '',
                        'numero_cheque': row[6] or '',
                        'nfacture': row[7],
                        'nom_client': row[8] or '',
                        'mode_paiement': row[9] or '',
                        'echeance': row[10] or '',
                        'verifie': bool(row[11]),
                        'num_facture': row[12] or ''
                    })
                
                return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def ajouter_transaction(self, banque_id: int, type_transaction: str, montant: float,
                          date_transaction: str, description: str = "", numero_cheque: str = "",
                          nfacture: int = None, nom_client: str = "", mode_paiement: str = "",
                          echeance: str = "", num_facture: str = "") -> bool:
        """Add a new bank transaction with duplicate prevention."""
        try:
            # DUPLICATE PREVENTION: Check if an identical transaction already exists
            with self._conn() as cn:
                existing = cn.execute("""
                    SELECT id FROM transactions_bancaires
                    WHERE banque_id = ?
                      AND date_transaction = ?
                      AND type_transaction = ?
                      AND ABS(montant - ?) < 0.001
                      AND COALESCE(nfacture, '') = COALESCE(?, '')
                      AND COALESCE(numero_cheque, '') = COALESCE(?, '')
                      AND COALESCE(description, '') = COALESCE(?, '')
                    LIMIT 1
                """, (
                    banque_id,
                    date_transaction,
                    type_transaction,
                    montant,
                    nfacture if nfacture is not None else '',
                    numero_cheque or '',
                    description or ''
                )).fetchone()
                
                if existing:
                    logger.warning(f"Duplicate transaction prevented: ID {existing[0]} already exists with same key fields")
                    return False  # Transaction already exists, don't add duplicate
            
            # No duplicate found - proceed with insert using sync system
            data = {
                'banque_id': banque_id,
                'date_transaction': date_transaction,
                'type_transaction': type_transaction,
                'montant': montant,
                'nfacture': nfacture,
                'nom_client': nom_client,
                'numero_cheque': numero_cheque,
                'description': description,
                'verifie': 0,
                'mode_paiement': mode_paiement,
                'echeance': echeance,
                'num_facture': num_facture
            }
            
            # Use db_helpers for insert
            try:
                insert_row('transactions_bancaires', data)
                # Get the inserted row ID
                with self._conn() as cn:
                    cursor = cn.execute("SELECT last_insert_rowid()")
                    new_id = cursor.fetchone()[0]
            except Exception as e:
                logger.error("Failed to insert transaction with db helpers")
                return False
            
            logger.info(f"Added transaction ID {new_id}")
            
            # Log the transaction creation
            log_create_action(
                module="bank",
                resource_type="transaction",
                resource_id=new_id,
                data={
                    "banque_id": banque_id,
                    "type": type_transaction,
                    "montant": montant,
                    "client": nom_client,
                    "date": date_transaction,
                    "nfacture": nfacture
                }
            )
            
            # Handle "virement_interne" mode_paiement - automatic bank-caisse transactions
            if mode_paiement == "virement_interne":
                self._handle_virement_interne_caisse_transaction(
                    type_transaction, montant, date_transaction, 
                    description, nom_client, nfacture, num_facture, new_id
                )
            
            # Handle calendar integration for traites
            if mode_paiement == "traite" and echeance and nom_client:
                self._handle_traite_calendar_event(nfacture, echeance, nom_client, montant, numero_cheque)
            
            return True
        except Exception as e:
            logger.error(f"Error adding transaction: {e}")
            return False
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict]:
        """Get a transaction by ID."""
        try:
            with self._conn() as cn:
                cursor = cn.execute('''
                    SELECT id, banque_id, type_transaction, montant, date_transaction,
                           description, numero_cheque, nfacture, nom_client,
                           mode_paiement, echeance, verifie, num_facture
                    FROM transactions_bancaires WHERE id = ?
                ''', (transaction_id,))
                row = cursor.fetchone()
                
                if row:
                    return {
                        'id': row[0],
                        'banque_id': row[1],
                        'type_transaction': row[2],
                        'montant': row[3],
                        'date_transaction': row[4],
                        'description': row[5] or '',
                        'numero_cheque': row[6] or '',
                        'nfacture': row[7],
                        'nom_client': row[8] or '',
                        'mode_paiement': row[9] or '',
                        'echeance': row[10] or '',
                        'verifie': bool(row[11]),
                        'num_facture': row[12] or ''
                    }
                return None
        except Exception as e:
            logger.error(f"Error getting transaction by ID: {e}")
            return None
    
    def modifier_transaction(self, transaction_id: int, **kwargs) -> bool:
        """Update a bank transaction."""
        try:
            # Filter out None values and prepare data
            data = {k: v for k, v in kwargs.items() if v is not None}
            
            try:
                update_row("transactions_bancaires", "id", transaction_id, data)
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    def supprimer_transaction(self, transaction_id: int) -> bool:
        """Delete a bank transaction."""
        try:
            # Get transaction details for cleanup and logging
            transaction = self.get_transaction_by_id(transaction_id)
            
            # Remove calendar event if it's a traite
            if transaction and transaction.get('mode_paiement') == 'traite' and transaction.get('echeance'):
                self._cleanup_traite_calendar_event(transaction)
            
            # Clean up linked caisse transaction if it's a virement_interne transaction
            if transaction and transaction.get('mode_paiement') == 'virement_interne':
                self._cleanup_virement_interne_caisse_transaction(transaction, transaction_id)
            
            # Use direct SQL for delete
            try:
                with self._conn() as cn:
                    cn.execute("DELETE FROM transactions_bancaires WHERE id = ?", (transaction_id,))
                    cn.commit()
                success = True
            except Exception:
                success = False
            logger.info(f"Delete transaction {transaction_id}: success={success}")
            
            # Log the deletion
            if success and transaction:
                log_delete_action(
                    module="bank",
                    resource_type="transaction",
                    resource_id=transaction_id,
                    deleted_data={
                        "banque_id": transaction.get('banque_id'),
                        "type": transaction.get('type_transaction'),
                        "montant": transaction.get('montant'),
                        "client": transaction.get('nom_client'),
                        "date": transaction.get('date_transaction')
                    }
                )
            
            return success
        except Exception as e:
            logger.error(f"Error deleting transaction: {e}")
            return False
    
    def verifier_transaction(self, transaction_id: int) -> bool:
        """Verify/check a bank transaction WITHOUT deleting other transactions."""
        try:
            # Diagnostics: open debug log in data dir
            debug_log_path = None
            try:
                from app.core.path_manager import get_data_dir as _pm_data
                debug_log_path = os.path.join(_pm_data(), 'bank_verify_debug.log')
            except Exception:
                pass
            def _dbg(msg: str):
                try:
                    logger.info(msg)
                    if debug_log_path:
                        with open(debug_log_path, 'a', encoding='utf-8') as _f:
                            _f.write(f"{datetime.now().isoformat()} | {msg}\n")
                except Exception:
                    pass

            # Fetch the transaction to verify
            with self._conn() as cn:
                cn.row_factory = sqlite3.Row
                row = cn.execute(
                    "SELECT id, banque_id, date_transaction, type_transaction, montant, nfacture, numero_cheque, description FROM transactions_bancaires WHERE id = ?",
                    (transaction_id,)
                ).fetchone()
                if not row:
                    logger.error(f"Transaction {transaction_id} not found")
                    return False
                
                # DIAGNOSTIC: Log what we're verifying
                _dbg(f"VERIFY START id={transaction_id} cheque={row['numero_cheque']} nfacture={row['nfacture']} montant={row['montant']}")
                
                # DIAGNOSTIC: Count similar transactions BEFORE verification
                similar_count_before = cn.execute("""
                    SELECT COUNT(*) FROM transactions_bancaires
                    WHERE banque_id = ? AND nfacture = ? AND ABS(montant - ?) < 0.001
                """, (row['banque_id'], row['nfacture'], row['montant'])).fetchone()[0]
                _dbg(f"SIMILAR BEFORE={similar_count_before} for facture {row['nfacture']}")
            
            # Use db_helpers for verification
            try:
                update_row("transactions_bancaires", "id", transaction_id, {
                    "verifie": 1,
                    "date_verification": datetime.now().isoformat(),
                    # Ensure timestamp-based sync picks up this change even if no DB trigger exists
                    "updated_at": datetime.now().isoformat()
                })
                success = True
            except Exception:
                success = False
            
            if not success:
                logger.error(f"Failed to verify transaction {transaction_id} via sync system")
                _dbg(f"VERIFY UPDATE FAILED id={transaction_id}")
                return False

            # Background sync is handled automatically by the sync service
            # try:
            #     sync.queue_sync_for_save()
            # except Exception as e:
            #     logger.warning(f"Background sync after verification failed to queue: {e}")
            #     _dbg(f"QUEUE SYNC FAILED: {e}")
            
            # Verify the update was successful
            with self._conn() as cn:
                # DIAGNOSTIC: Count similar transactions AFTER verification
                similar_count_after = cn.execute("""
                    SELECT COUNT(*) FROM transactions_bancaires
                    WHERE banque_id = ? AND nfacture = ? AND ABS(montant - ?) < 0.001
                """, (row['banque_id'], row['nfacture'], row['montant'])).fetchone()[0]
                _dbg(f"SIMILAR AFTER={similar_count_after} for facture {row['nfacture']}")
                
                if similar_count_after < similar_count_before:
                    logger.error(f"BUG DETECTED: {similar_count_before - similar_count_after} transactions DELETED during verification!")
                    _dbg(f"BUG: {similar_count_before - similar_count_after} rows deleted during verify!")
            
            # Log the verification
            log_verification_action(
                module="bank",
                resource_type="transaction",
                resource_id=transaction_id,
                verified=True
            )
            
            _dbg(f"VERIFY OK id={transaction_id}")
            return True
        except Exception as e:
            logger.error(f"Error verifying transaction: {e}")
            try:
                _dbg(f"VERIFY EXCEPTION id={transaction_id} err={e}")
            except Exception:
                pass
            return False
    
    # ========================== Balance & Summary ==========================
    
    def get_solde_banque(self, banque_id: int, date_calcul: str = None, verifie_seulement: bool = True) -> float:
        """Get bank balance."""
        try:
            with self._conn() as cn:
                # Get initial balance
                cursor = cn.execute('SELECT solde_initial FROM banques WHERE id = ?', (banque_id,))
                bank_row = cursor.fetchone()
                if not bank_row:
                    return 0.0
                
                solde = bank_row[0]
                
                # Build query for transactions
                query = '''
                    SELECT type_transaction, SUM(montant)
                    FROM transactions_bancaires
                    WHERE banque_id = ?
                '''
                params = [banque_id]
                
                if date_calcul:
                    query += ' AND date_transaction <= ?'
                    params.append(date_calcul)
                
                if verifie_seulement:
                    query += ' AND verifie = 1'
                
                query += ' GROUP BY type_transaction'
                
                cursor = cn.execute(query, params)
                rows = cursor.fetchall()
                
                for row in rows:
                    transaction_type, total = row
                    if transaction_type == 'encaissement':
                        solde += total
                    elif transaction_type == 'decaissement':
                        solde -= total
                
                return solde
        except Exception as e:
            logger.error(f"Error calculating bank balance: {e}")
            return 0.0
    
    def get_resume_periode(self, banque_id: int, date_debut: str, date_fin: str) -> Dict:
        """Get period summary for a bank."""
        try:
            with self._conn() as cn:
                # Get encaissements
                cursor = cn.execute('''
                    SELECT SUM(montant), COUNT(*)
                    FROM transactions_bancaires
                    WHERE banque_id = ? AND type_transaction = 'encaissement'
                    AND date_transaction BETWEEN ? AND ?
                ''', (banque_id, date_debut, date_fin))
                enc_row = cursor.fetchone()
                enc_total = enc_row[0] or 0
                enc_count = enc_row[1] or 0
                
                # Get decaissements
                cursor = cn.execute('''
                    SELECT SUM(montant), COUNT(*)
                    FROM transactions_bancaires
                    WHERE banque_id = ? AND type_transaction = 'decaissement'
                    AND date_transaction BETWEEN ? AND ?
                ''', (banque_id, date_debut, date_fin))
                dec_row = cursor.fetchone()
                dec_total = dec_row[0] or 0
                dec_count = dec_row[1] or 0
                
                return {
                    'encaissements': {
                        'total': enc_total,
                        'count': enc_count
                    },
                    'decaissements': {
                        'total': dec_total,
                        'count': dec_count
                    }
                }
        except Exception as e:
            logger.error(f"Error getting period summary: {e}")
            return {'encaissements': {'total': 0, 'count': 0}, 'decaissements': {'total': 0, 'count': 0}}
    
    # ========================== Payment Methods ==========================
    
    def get_payment_methods(self) -> List[tuple]:
        """Get available payment methods."""
        try:
            with self._conn() as cn:
                cursor = cn.execute('SELECT key, label FROM payment_methods ORDER BY label')
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return []
    
    def add_payment_method(self, key: str, label: str) -> bool:
        """Add a new payment method with sync."""
        try:
            data = {'key': key, 'label': label}
            try:
                insert_row('payment_methods', data)
                return True
            except Exception:
                return False
        except Exception as e:
            logger.error(f"Error adding payment method: {e}")
            return False
    
    def remove_payment_method(self, key: str) -> bool:
        """Remove a payment method with sync."""
        try:
            # Get the ID first
            with self._conn() as cn:
                row = cn.execute('SELECT id FROM payment_methods WHERE key = ?', (key,)).fetchone()
                if not row:
                    return False
                payment_id = row[0]
            
            # Use direct SQL for delete
            try:
                with self._conn() as cn:
                    cn.execute("DELETE FROM payment_methods WHERE id = ?", (payment_id,))
                    cn.commit()
                success = True
            except Exception:
                success = False
            if success:
                logger.info(f"Removed payment method: {key}")
            return success
        except Exception as e:
            logger.error(f"Error removing payment method: {e}")
            return False
    
    # ========================== Utilities ==========================
    
    def formater_montant(self, montant: float) -> str:
        """Format amount for display."""
        try:
            return f"{montant:,.3f} DZD".replace(",", " ")
        except Exception as e:
            logger.error(f"Error formatting amount: {e}")
            return f"{montant:.3f} DZD"
    
    def formater_date(self, date_str: str) -> str:
        """Format date for display."""
        try:
            if not date_str:
                return ""
            
            # Try to parse and reformat
            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
            return date_obj.strftime("%d/%m/%Y")
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date_str
    
    # ========================== Calendar Integration ==========================
    
    def _handle_traite_calendar_event(self, nfacture, echeance, client, montant, numero_traite):
        """Handle calendar event creation for traite."""
        try:
            # TODO: Use CalendarService when available
            logger.info(f"Calendar event for traite {numero_traite} deferred to CalendarService")
            
            # title = f"Traite à encaisser: Facture {nfacture}"
            # description = f"Client: {client}\nMontant: {self.formater_montant(montant)}\nNuméro: {numero_traite}"
            
        except Exception as e:
            logger.warning(f"Could not create calendar event for traite: {e}")
    
    def _cleanup_traite_calendar_event(self, transaction):
        """Clean up calendar event for traite."""
        try:
            # TODO: Use CalendarService when available  
            logger.info(f"Calendar event cleanup for traite deferred to CalendarService")
            
        except Exception as e:
            logger.warning(f"Could not cleanup calendar event for traite: {e}")

    def _handle_virement_interne_caisse_transaction(self, type_transaction: str, montant: float,
                                         date_transaction: str, description: str,
                                         nom_client: str, nfacture: int, 
                                         num_facture: str, bank_transaction_id: int):
        """
        Handle automatic caisse transaction when bank transaction type is 'virement_interne'.
        
        - If bank type is 'décaissement': Money goes FROM bank TO caisse (caisse receives = encaissement)
        - If bank type is 'encaissement': Money goes FROM caisse TO bank (caisse pays = décaissement)
        
        Args:
            type_transaction: Bank transaction type ('décaissement' or 'encaissement')
            montant: Transaction amount
            date_transaction: Transaction date
            description: Transaction description
            nom_client: Client name
            nfacture: Invoice number
            num_facture: Invoice reference
            bank_transaction_id: The bank transaction ID for linking
        """
        try:
            from app.stfoom.data.caisse_repository import CaisseRepository
            caisse_repo = CaisseRepository()
            
            # Determine caisse transaction type (opposite of bank)
            if type_transaction.lower() == 'décaissement':
                # Bank décaissement = money leaving bank = money entering caisse
                caisse_type = 'encaissement'
                caisse_description = f"Virement interne depuis banque - {description}" if description else f"Virement interne depuis banque (Transaction bancaire #{bank_transaction_id})"
            elif type_transaction.lower() == 'encaissement':
                # Bank encaissement = money entering bank = money leaving caisse
                caisse_type = 'décaissement'
                caisse_description = f"Virement interne vers banque - {description}" if description else f"Virement interne vers banque (Transaction bancaire #{bank_transaction_id})"
            else:
                logger.warning(f"Unknown transaction type for virement_interne handling: {type_transaction}")
                return
            
            # Create the linked caisse transaction
            success = caisse_repo.ajouter_transaction(
                montant=montant,
                date_str=date_transaction,
                type_=caisse_type,
                description=caisse_description,
                nfacture=nfacture,
                num_facture=num_facture
            )
            
            if success:
                logger.info(f"Created automatic caisse {caisse_type} transaction for bank virement_interne transaction #{bank_transaction_id}")
                
                # Log the linked transaction creation
                log_create_action(
                    module="bank",
                    resource_type="caisse_link",
                    resource_id=f"bank_{bank_transaction_id}",
                    data={
                        "bank_transaction_id": bank_transaction_id,
                        "bank_type": type_transaction,
                        "caisse_type": caisse_type,
                        "montant": montant,
                        "date": date_transaction
                    }
                )
            else:
                logger.error(f"Failed to create automatic caisse transaction for bank virement_interne #{bank_transaction_id}")
                
        except Exception as e:
            logger.error(f"Error creating automatic caisse transaction for virement_interne: {e}")
            # Don't fail the bank transaction if caisse link fails

    def _cleanup_virement_interne_caisse_transaction(self, transaction: Dict, bank_transaction_id: int):
        """
        Clean up linked caisse transaction when deleting a virement_interne bank transaction.
        
        Args:
            transaction: The bank transaction being deleted
            bank_transaction_id: The bank transaction ID
        """
        try:
            from app.stfoom.data.caisse_repository import CaisseRepository
            caisse_repo = CaisseRepository()
            
            # Determine what type of caisse transaction to look for (opposite of bank)
            bank_type = transaction.get('type_transaction', '').lower()
            if bank_type == 'décaissement':
                caisse_type = 'encaissement'
            elif bank_type == 'encaissement':
                caisse_type = 'décaissement'
            else:
                logger.warning(f"Unknown transaction type for virement_interne cleanup: {bank_type}")
                return
            
            # Find and delete matching caisse transaction
            montant = transaction.get('montant')
            date_transaction = transaction.get('date_transaction')
            
            # Look for caisse transaction with matching criteria
            with self._conn() as cn:
                # Use the main database connection to query caisse
                cursor = cn.execute("""
                    SELECT id FROM caisse_transactions
                    WHERE type = ?
                      AND ABS(montant - ?) < 0.001
                      AND date = ?
                      AND (description LIKE ? OR description LIKE ?)
                    LIMIT 1
                """, (
                    caisse_type,
                    montant,
                    date_transaction,
                    f"%Transaction bancaire #{bank_transaction_id}%",
                    f"%Virement interne%"
                ))
                
                caisse_row = cursor.fetchone()
                
                if caisse_row:
                    caisse_id = caisse_row[0]
                    # Delete the linked caisse transaction
                    if caisse_repo.supprimer_transaction(caisse_id):
                        logger.info(f"Deleted linked caisse transaction #{caisse_id} for bank virement_interne transaction #{bank_transaction_id}")
                    else:
                        logger.warning(f"Failed to delete linked caisse transaction #{caisse_id}")
                else:
                    logger.info(f"No linked caisse transaction found for bank virement_interne transaction #{bank_transaction_id}")
                    
        except Exception as e:
            logger.error(f"Error cleaning up linked caisse transaction: {e}")
            # Don't fail the bank transaction deletion if caisse cleanup fails
