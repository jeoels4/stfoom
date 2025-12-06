"""
Cheque Repository
================
Handles all database operations for the cheque module.
"""
import sqlite3
from typing import List, Dict, Optional
from datetime import datetime
import logging
from app.core.path_manager import get_db_path

# Use centralized DB helpers for automatic sync tracking
from app.stfoom.logic.db_helpers import insert_row, update_row

logger = logging.getLogger(__name__)

class ChequeRepository:
    """Repository for cheque management operations"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
        self._init_tables()
        logger.info("ChequeRepository initialized")
    
    def _init_tables(self):
        """Initialize cheque tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Cheque records table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cheques (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero_cheque INTEGER NOT NULL,
                    banque_id INTEGER NOT NULL,
                    date_cheque DATE NOT NULL,
                    montant REAL NOT NULL,
                    fournisseur TEXT NOT NULL,
                    beneficiaire TEXT,
                    statut TEXT DEFAULT 'emis',  -- 'emis', 'annule', 'encaisse'
                    motif_annulation TEXT,
                    bank_transaction_id INTEGER, -- lien vers transactions_bancaires.id
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (banque_id) REFERENCES banques(id),
                    UNIQUE(numero_cheque, banque_id)
                )
            """)
            # Backward-compatible migrations
            try:
                cursor.execute("ALTER TABLE cheques ADD COLUMN bank_transaction_id INTEGER")
            except sqlite3.OperationalError:
                pass
            
            # Cheque configuration table (per bank)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS cheque_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    banque_id INTEGER NOT NULL,
                    carne_dernier_numero INTEGER NOT NULL,
                    mini_cheque_alert INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (banque_id) REFERENCES banques(id),
                    UNIQUE(banque_id)
                )
            """)
            
            # Create indexes for performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheques_banque ON cheques(banque_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheques_numero ON cheques(numero_cheque)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheques_date ON cheques(date_cheque)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheques_statut ON cheques(statut)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_cheques_bank_tx ON cheques(bank_transaction_id)")
            
            conn.commit()
    
    def get_all_cheques(self, banque_id: Optional[int] = None) -> List[Dict]:
        """Get all cheques, optionally filtered by bank"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = """
                SELECT c.*, b.nom_banque 
                FROM cheques c
                JOIN banques b ON c.banque_id = b.id
            """
            params = []
            
            if banque_id:
                query += " WHERE c.banque_id = ?"
                params.append(banque_id)
            
            query += " ORDER BY c.banque_id, c.numero_cheque DESC"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def create_cheque(self, cheque_data: Dict) -> int:
        """Create a new cheque record using centralized DB helpers."""
        try:
            # Use parking lot dispenser for automatic sync tracking
            insert_row('cheques', cheque_data)
            
            # Get the inserted ID
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id FROM cheques 
                    WHERE numero_cheque = ? AND banque_id = ? 
                    ORDER BY id DESC LIMIT 1
                """, (cheque_data['numero_cheque'], cheque_data['banque_id']))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"Error creating cheque: {e}")
            raise
    
    def update_cheque(self, cheque_id: int, updates: Dict) -> bool:
        """Update an existing cheque using centralized DB helpers."""
        try:
            # Use parking lot dispenser for automatic sync tracking
            update_row('cheques', 'id', cheque_id, updates)
            return True
        except Exception as e:
            logger.error(f"Error updating cheque {cheque_id}: {e}")
            return False
    
    def annuler_cheque(self, cheque_id: int, motif: str = '') -> bool:
        """Mark a cheque as cancelled"""
        return self.update_cheque(cheque_id, {
            'statut': 'annule',
            'motif_annulation': motif
        })

    def get_cheque_by_id(self, cheque_id: int) -> Optional[Dict]:
        """Get a cheque by its ID"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM cheques WHERE id = ?", (cheque_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def set_bank_transaction_link(self, cheque_id: int, transaction_id: Optional[int]) -> bool:
        """Link a cheque to a bank transaction (or unlink with None)"""
        return self.update_cheque(cheque_id, {
            'bank_transaction_id': transaction_id
        })
    
    def get_cheque_config(self, banque_id: int) -> Optional[Dict]:
        """Get cheque configuration for a bank"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM cheque_config WHERE banque_id = ?
            """, (banque_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def set_cheque_config(self, banque_id: int, carne_dernier_numero: int, mini_cheque_alert: int = 10) -> bool:
        """Set or update cheque configuration for a bank.
        Note: Uses direct SQL for UPSERT operation (INSERT OR REPLACE) since db_helpers doesn't support upsert.
        This is configuration data that may not require sync tracking.
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO cheque_config 
                    (banque_id, carne_dernier_numero, mini_cheque_alert, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (banque_id, carne_dernier_numero, mini_cheque_alert))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error setting cheque config for bank {banque_id}: {e}")
            return False
    
    def get_next_cheque_number(self, banque_id: int) -> Optional[int]:
        """Get the next cheque number for a bank"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get the highest cheque number used for this bank
            cursor.execute("""
                SELECT MAX(numero_cheque) FROM cheques WHERE banque_id = ?
            """, (banque_id,))
            
            max_used = cursor.fetchone()[0]
            return (max_used + 1) if max_used else 1
    
    def check_cheque_availability(self, banque_id: int) -> Dict:
        """Check cheque availability and alert status"""
        config = self.get_cheque_config(banque_id)
        if not config:
            return {'needs_config': True}
        
        next_number = self.get_next_cheque_number(banque_id)
        if not next_number:
            next_number = 1
        
        carne_fin = config['carne_dernier_numero']
        mini_alert = config['mini_cheque_alert']
        cheques_remaining = carne_fin - next_number + 1
        
        return {
            'needs_config': False,
            'next_number': next_number,
            'carne_fin': carne_fin,
            'cheques_remaining': cheques_remaining,
            'need_alert': cheques_remaining <= mini_alert,
            'mini_alert_threshold': mini_alert
        }
    
    def get_missing_cheque_numbers(self, banque_id: int) -> List[int]:
        """Get list of missing cheque numbers (gaps in sequence)"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT numero_cheque FROM cheques 
                WHERE banque_id = ? AND statut != 'annule'
                ORDER BY numero_cheque
            """, (banque_id,))
            
            used_numbers = [row[0] for row in cursor.fetchall()]
            
            if not used_numbers:
                return []
            
            # Find gaps in sequence
            missing = []
            for i in range(1, max(used_numbers)):
                if i not in used_numbers:
                    missing.append(i)
            
            return missing
    
    def get_cheques_by_status(self, banque_id: int, statut: str) -> List[Dict]:
        """Get cheques filtered by status"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT c.*, b.nom_banque 
                FROM cheques c
                JOIN banques b ON c.banque_id = b.id
                WHERE c.banque_id = ? AND c.statut = ?
                ORDER BY c.numero_cheque DESC
            """, (banque_id, statut))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_outgoing_cheques_from_bank(self, banque_id: Optional[int] = None) -> List[Dict]:
        """Get outgoing cheques from bank transactions that haven't been imported yet"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Get outgoing cheques from bank transactions
            # Only get transactions that are:
            # 1. Outgoing (decaissement)
            # 2. Payment method is cheque OR has a cheque number
            # 3. Has a valid cheque number (not empty, not '.')
            query = """
                SELECT 
                    id as transaction_id,
                    banque_id,
                    date_transaction,
                    montant,
                    numero_cheque,
                    nom_client,
                    description
                FROM transactions_bancaires 
                WHERE type_transaction = 'decaissement' 
                AND (mode_paiement = 'cheque' OR numero_cheque IS NOT NULL)
                AND numero_cheque IS NOT NULL 
                AND numero_cheque != ''
                AND numero_cheque != '.'
                AND numero_cheque != 'None'
            """
            params: List = []
            if banque_id is not None:
                query += " AND banque_id = ?"
                params.append(banque_id)
            query += " ORDER BY date_transaction DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def sync_with_bank_transactions(self, banque_id: Optional[int] = None) -> Dict:
        """Synchronize cheques with related bank transactions.
        - Update montant/date for linked cheques
        - Link encours cheques to bank transactions by numero_cheque
        - Mark as annulé if linked transaction has been deleted
        - Auto-import missing cheques from bank for this bank
        Returns a dictionary with counts of changes.
        """
        changes = {
            'updated': 0,
            'linked': 0,
            'annule_from_delete': 0,
            'imported': 0
        }
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # 1) For linked cheques, update montant/date to match transaction
            link_filter = " WHERE bank_transaction_id IS NOT NULL"
            params: List = []
            if banque_id is not None:
                link_filter += " AND banque_id = ?"
                params.append(banque_id)
            cursor.execute(f"SELECT * FROM cheques{link_filter}", params)
            linked = [dict(r) for r in cursor.fetchall()]
            for ch in linked:
                tx = conn.execute("SELECT id, montant, date_transaction FROM transactions_bancaires WHERE id = ?",
                                  (ch.get('bank_transaction_id'),)).fetchone()
                if tx:
                    txd = dict(tx)
                    # Only update if different
                    if (abs((ch.get('montant') or 0) - abs(txd['montant'])) > 0.0001) or ((ch.get('date_cheque') or '') != (txd['date_transaction'] or '')):
                        conn.execute("UPDATE cheques SET montant = ?, date_cheque = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                     (abs(txd['montant']), txd['date_transaction'], ch['id']))
                        changes['updated'] += 1
                else:
                    # Transaction deleted: mark cheque as annulé if not already
                    if ch.get('statut') != 'annule':
                        conn.execute("UPDATE cheques SET statut = 'annule', motif_annulation = COALESCE(motif_annulation,'') || ' | Supprimé en banque', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                                     (ch['id'],))
                        changes['annule_from_delete'] += 1

            # 2) Link 'encours' cheques by matching numero_cheque for this bank
            enc_filter = " WHERE statut = 'encours'"
            enc_params: List = []
            if banque_id is not None:
                enc_filter += " AND banque_id = ?"
                enc_params.append(banque_id)
            cursor.execute(f"SELECT * FROM cheques{enc_filter}", enc_params)
            encours_list = [dict(r) for r in cursor.fetchall()]
            for ch in encours_list:
                tx = conn.execute(
                    """
                    SELECT id, montant, date_transaction FROM transactions_bancaires
                    WHERE banque_id = ? AND numero_cheque = ? AND type_transaction = 'decaissement'
                    ORDER BY date_transaction DESC, id DESC LIMIT 1
                    """,
                    (ch['banque_id'], str(ch['numero_cheque']))
                ).fetchone()
                if tx:
                    txd = dict(tx)
                    conn.execute(
                        "UPDATE cheques SET bank_transaction_id = ?, montant = ?, date_cheque = ?, statut = 'emis', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (txd['id'], abs(txd['montant']), txd['date_transaction'], ch['id'])
                    )
                    changes['linked'] += 1

            conn.commit()

            # 3) Auto-import missing cheques from bank for this bank
            bank_rows = self.get_outgoing_cheques_from_bank(banque_id)
            # Existing cheques set per bank
            existing = set()
            ex_params: List = []
            ex_query = "SELECT numero_cheque, banque_id FROM cheques"
            if banque_id is not None:
                ex_query += " WHERE banque_id = ?"
                ex_params.append(banque_id)
            for row in conn.execute(ex_query, ex_params).fetchall():
                existing.add((row[0], row[1]))
            for b in bank_rows:
                try:
                    if not b['numero_cheque']:
                        continue
                    num = int(b['numero_cheque']) if not isinstance(b['numero_cheque'], int) else b['numero_cheque']
                except Exception:
                    continue
                key = (num, b['banque_id'])
                if key in existing:
                    continue
                # Insert new cheque imported
                conn.execute(
                    """
                    INSERT OR IGNORE INTO cheques (numero_cheque, banque_id, date_cheque, montant, fournisseur, beneficiaire, statut, notes, bank_transaction_id)
                    VALUES (?, ?, ?, ?, ?, ?, 'emis', ?, ?)
                    """,
                    (
                        num,
                        b['banque_id'],
                        b['date_transaction'],
                        abs(float(b['montant'])),
                        b.get('nom_client') or 'Importé de la banque',
                        b.get('nom_client') or '',
                        f"Importé automatiquement depuis transaction bancaire #{b['transaction_id']}",
                        b['transaction_id']
                    )
                )
                changes['imported'] += 1
            conn.commit()

    def create(self, cheque_data: Dict) -> bool:
        """
        Generic create method for sync testing.
        Delegates to create_cheque for automatic sync tracking.
        
        Args:
            cheque_data: Cheque data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.create_cheque(cheque_data) is not None
    
    def update(self, cheque_id: int, cheque_data: Dict, id_column: str = "id") -> bool:
        """
        Generic update method for sync testing.
        Delegates to update_cheque for automatic sync tracking.
        
        Args:
            cheque_id: Cheque ID to update
            cheque_data: Updated cheque data
            id_column: ID column name (ignored, always uses 'id')
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.update_cheque(cheque_id, cheque_data)
    
    def delete(self, cheque_id: int, id_column: str = "id") -> bool:
        """
        Generic delete method for sync testing.
        Uses soft delete with deleted_at field.
        
        Args:
            cheque_id: Cheque ID to delete
            id_column: ID column name (ignored, always uses 'id')
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Custom soft delete for cheques table which uses deleted_at field
            from datetime import datetime
            now = datetime.now().isoformat()
            
            # Update using direct SQL since we need custom soft delete
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    "UPDATE cheques SET deleted_at = ?, updated_at = ? WHERE id = ?",
                    (now, now, cheque_id)
                )
                conn.commit()
            
            # Track the change for sync
            from app.stfoom.data.base_repository import BaseRepository
            base_repo = BaseRepository()
            base_repo._track_change('cheques', 'delete', {'id': cheque_id})
            
            return True
        except Exception as e:
            logger.error(f"Error deleting cheque {cheque_id}: {e}")
            return False
    
    def get_all(self) -> List[Dict]:
        """
        Generic get_all method for sync testing.
        Returns all active (non-deleted) cheques.
        
        Returns:
            List[Dict]: List of all active cheque records
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT c.*, b.nom_banque 
                    FROM cheques c
                    JOIN banques b ON c.banque_id = b.id
                    WHERE c.(deleted = 0 OR deleted IS NULL)
                    ORDER BY c.banque_id, c.numero_cheque DESC
                """)
                
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            logger.error(f"Error getting all cheques: {e}")
            return []