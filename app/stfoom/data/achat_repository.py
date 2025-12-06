"""
STFOOM Achat Repository

This repository provides data access layer for purchase (achat) operations,
handling all database interactions and data transformations.
"""

# ✅ SECURITY COMPLIANCE: Use centralized configuration
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from config.settings import get_db_path, get_data_dir

import sqlite3
import json
import logging
from typing import List, Dict, Optional
from datetime import datetime
from app.connection import sync
from app.stfoom.logic.db_helpers import insert_row, update_row
from datetime import datetime
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)
# REMOVED: No more logic imports - using direct database connection

logger = logging.getLogger(__name__)

class AchatRepository:
    """Repository for achat (purchase) data access operations."""
    
    def __init__(self):
        """Initialize the achat repository."""
        self.data_dir = get_data_dir()  # ✅ FIXED: No more hardcoded paths
        self.db_path = get_db_path()  # ✅ FIXED: No more hardcoded paths
        self._init_db()
        logger.info("AchatRepository initialized")
    
    def _conn(self) -> sqlite3.Connection:
        """Get database connection directly."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # ✅ FIXED: Enable Row objects for dict() conversion
        return conn
    
    def _init_db(self):
        """Initialize the achats table if it doesn't exist."""
        try:
            with self._conn() as cn:
                cn.execute('''
                    CREATE TABLE IF NOT EXISTS achats (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        date TEXT NOT NULL,
                        fournisseur TEXT NOT NULL,
                        fournisseur_alias TEXT, -- Optional alias to display when using 401000 (fournisseur divers)
                        num_facture TEXT,
                        mt_ht REAL,
                        ttc REAL,
                        timbre REAL,
                        taxes TEXT, -- JSON: list of {name, value}
                        notes TEXT,
                        paiement_statut TEXT,
                        paiement_methode TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                # Ensure the new colonne fournisseur_alias exists on older databases
                try:
                    cur = cn.execute("PRAGMA table_info(achats)")
                    cols = [row[1] for row in cur.fetchall()]
                    if 'fournisseur_alias' not in cols:
                        cn.execute("ALTER TABLE achats ADD COLUMN fournisseur_alias TEXT")
                        logger.info("Added fournisseur_alias column to achats table")
                except Exception as mig_e:
                    logger.warning(f"Could not ensure fournisseur_alias column exists: {mig_e}")
                cn.commit()
                logger.info("Achats table initialized")
        except Exception as e:
            logger.error(f"Error initializing achats table: {e}")
            raise
    
    def fetch_all_achats(self) -> List[Dict]:
        """
        Fetch all achat records from the database.
        
        Returns:
            List of achat dictionaries with parsed taxes
        """
        try:
            # Order by date descending, handling both 'YYYY-MM-DD' and 'DD/MM/YYYY' stored formats
            # Normalize DD/MM/YYYY into ISO format for ordering; otherwise use date as-is
            sql = (
                "SELECT * FROM achats "
                "WHERE (deleted = 0 OR deleted IS NULL) "
                "ORDER BY CASE "
                "WHEN date LIKE '__/__/____' THEN substr(date,7,4)||'-'||substr(date,4,2)||'-'||substr(date,1,2) "
                "ELSE date END DESC, id DESC"
            )
            with self._conn() as cn:
                rows = cn.execute(sql).fetchall()
                out = []
                for row in rows:
                    d = dict(row)
                    # Parse taxes JSON
                    try:
                        d['taxes'] = json.loads(d['taxes']) if d['taxes'] else []
                    except Exception:
                        d['taxes'] = []
                    
                    # Handle NULL values for numeric fields - convert to 0.0
                    d['mt_ht'] = float(d.get('mt_ht') or 0)
                    d['ttc'] = float(d.get('ttc') or 0)
                    d['timbre'] = float(d.get('timbre') or 0)
                    
                    out.append(d)
                logger.info(f"Fetched {len(out)} achat records")
                return out
        except Exception as e:
            logger.error(f"Error fetching all achats: {e}")
            return []
    
    def fetch_achat_by_id(self, achat_id: int) -> Optional[Dict]:
        """
        Fetch a single achat record by ID.
        
        Args:
            achat_id: The ID of the achat to fetch
            
        Returns:
            Achat dictionary or None if not found
        """
        try:
            sql = "SELECT * FROM achats WHERE id = ? AND (deleted = 0 OR deleted IS NULL) LIMIT 1"
            with self._conn() as cn:
                row = cn.execute(sql, (achat_id,)).fetchone()
                if not row:
                    return None
                d = dict(row)
                # Parse taxes JSON
                try:
                    d['taxes'] = json.loads(d['taxes']) if d['taxes'] else []
                except Exception:
                    d['taxes'] = []
                
                # Handle NULL values for numeric fields - convert to 0.0
                d['mt_ht'] = float(d.get('mt_ht') or 0)
                d['ttc'] = float(d.get('ttc') or 0)
                d['timbre'] = float(d.get('timbre') or 0)
                
                logger.info(f"Fetched achat {achat_id}")
                return d
        except Exception as e:
            logger.error(f"Error fetching achat {achat_id}: {e}")
            return None
    
    def insert_achat(self, data: Dict) -> Optional[int]:
        """
        Insert a new achat record.
        
        Args:
            data: Dictionary containing achat information
            
        Returns:
            The ID of the inserted record if successful, None otherwise
        """
        try:
            # Convert taxes to JSON
            taxes_json = json.dumps(data.get('taxes', []), ensure_ascii=False)
            data_to_insert = data.copy()
            data_to_insert['taxes'] = taxes_json
            
            # Use db_helpers for automatic sync tracking
            insert_row('achats', data_to_insert)
            
            # Get the ID of the inserted record
            with self._conn() as conn:
                cursor = conn.execute("SELECT last_insert_rowid() as id")
                result = cursor.fetchone()
                achat_id = result['id'] if result else None
            
            logger.info(f"Inserted achat for fournisseur: {data.get('fournisseur')}, ID: {achat_id}")
            return achat_id
        except Exception as e:
            logger.error(f"Error inserting achat: {e}")
            return None
    
    def update_achat(self, achat_id: int, data: Dict) -> bool:
        """
        Update an existing achat record.
        
        Args:
            achat_id: The ID of the achat to update
            data: Dictionary containing updated achat information
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Get the original achat details before updating
            original_achat = self.fetch_achat_by_id(achat_id)
            if not original_achat:
                logger.error(f"Achat {achat_id} not found for update")
                return False
            
            # Convert taxes to JSON
            taxes_json = json.dumps(data.get('taxes', []), ensure_ascii=False)
            data_to_update = data.copy()
            data_to_update['taxes'] = taxes_json
            
            # Use db_helpers for automatic sync tracking
            update_row('achats', 'id', achat_id, data_to_update)
            
            # Update related data if key fields changed
            self._update_related_data(achat_id, data, original_achat)
            
            # Sync changes to ciment module
            self._sync_achat_changes_to_ciment(achat_id, data, original_achat)
            
            logger.info(f"Updated achat {achat_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating achat {achat_id}: {e}")
            return False
    
    def delete_achat(self, achat_id: int) -> bool:
        """
        Delete an achat record and clean up related data.
        
        Args:
            achat_id: The ID of the achat to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # First, get the achat details to clean up related data
            achat_details = self.fetch_achat_by_id(achat_id)
            
            if achat_details:
                # Clean up related data before deleting
                self._cleanup_related_data(achat_id, achat_details)
            
            # Soft delete the achat record using db_helpers
            update_row('achats', 'id', achat_id, {'deleted_at': datetime.now().timestamp()})
            logger.info(f"Deleted achat {achat_id}")
            
            # Log the deletion
            if achat_details:
                log_delete_action(
                    module="achat",
                    resource_type="achat",
                    resource_id=achat_id,
                    deleted_data={
                        "fournisseur": achat_details.get('fournisseur'),
                        "num_facture": achat_details.get('num_facture'),
                        "montant": achat_details.get('ttc'),
                        "date": achat_details.get('date')
                    }
                )
            
            return True
        except Exception as e:
            logger.error(f"Error deleting achat {achat_id}: {e}")
            return False
    
    def _update_related_data(self, achat_id: int, new_data: Dict, original_achat: Dict):
        """Update related data when achat is modified."""
        try:
            original_fournisseur = original_achat.get('fournisseur', '')
            original_num_facture = original_achat.get('num_facture', '')
            new_fournisseur = new_data.get('fournisseur', '')
            new_num_facture = new_data.get('num_facture', '')
            
            if (original_fournisseur != new_fournisseur or 
                original_num_facture != new_num_facture):
                
                # Update related data through services (no more logic imports)
                self._update_related_transactions(achat_id, new_fournisseur, new_num_facture, 
                                                original_fournisseur, original_num_facture)
        except Exception as e:
            logger.error(f"Error updating related data for achat {achat_id}: {e}")
    
    def _update_bank_transactions(self, achat_id, new_fournisseur, new_num_facture, 
                                original_num_facture, bank):
        """Update bank transactions related to this achat."""
        try:
            bank_transactions = bank.get_transactions()
            for tx in bank_transactions:
                should_update = False
                
                # Check if this transaction is for this achat
                if (tx.get('type_transaction') == 'decaissement' and 
                    tx.get('description', '').startswith(f"Paiement achat {achat_id}")):
                    should_update = True
                # Also check by old num_facture if it matches
                elif (tx.get('type_transaction') == 'decaissement' and 
                      tx.get('num_facture') == original_num_facture and
                      original_num_facture and original_num_facture.strip()):
                    should_update = True
                
                if should_update:
                    bank.modifier_transaction(
                        transaction_id=tx['id'],
                        type_transaction='decaissement',
                        montant=tx['montant'],
                        date_transaction=tx['date_transaction'],
                        nfacture=achat_id,
                        nom_client=new_fournisseur,
                        numero_cheque=tx.get('numero_cheque', ''),
                        description=f"Paiement achat {achat_id} - {new_fournisseur}",
                        mode_paiement=tx.get('mode_paiement', ''),
                        echeance=tx.get('echeance', ''),
                        num_facture=new_num_facture if new_num_facture else None
                    )
        except Exception as e:
            logger.error(f"Error updating bank transactions: {e}")
    
    def _update_caisse_transactions(self, achat_id, new_fournisseur, new_num_facture, 
                                  original_num_facture, caisse):
        """Update caisse transactions related to this achat."""
        try:
            caisse_transactions = caisse.get_transactions()
            for tx in caisse_transactions:
                should_update = False
                
                # Check if this transaction is for this achat
                if (tx.get('type') == 'decaissement' and 
                    tx.get('description', '').startswith(f"Paiement achat {achat_id}")):
                    should_update = True
                # Also check by old num_facture if it matches
                elif (tx.get('type') == 'decaissement' and 
                      tx.get('num_facture') == original_num_facture and
                      original_num_facture and original_num_facture.strip()):
                    should_update = True
                
                if should_update:
                    caisse.modifier_transaction(
                        transaction_id=tx['id'],
                        type_transaction='decaissement',
                        montant=tx['montant'],
                        date_transaction=tx['date_transaction'],
                        nfacture=achat_id,
                        nom_client=new_fournisseur,
                        numero_recu=tx.get('numero_recu', ''),
                        description=f"Paiement achat {achat_id} - {new_fournisseur}",
                        mode_paiement=tx.get('mode_paiement', ''),
                        echeance=tx.get('echeance', '')
                    )
        except Exception as e:
            logger.error(f"Error updating caisse transactions: {e}")
    
    def _update_retenus(self, achat_id, new_fournisseur, new_num_facture, 
                       original_fournisseur, original_num_facture):
        """Update retenus related to this achat."""
        try:
            with self._conn() as cn:
                # Update retenus by achat ID
                cn.execute("""
                    UPDATE retenus SET client = ?, nfacture = ? 
                    WHERE nfacture = ? AND source = 'achat'
                """, (new_fournisseur, new_num_facture if new_num_facture else achat_id, achat_id))
                
                # Update retenus by old num_facture if it was a valid number
                if original_num_facture and original_num_facture.strip():
                    try:
                        original_num_facture_int = int(original_num_facture)
                        cn.execute("""
                            UPDATE retenus SET client = ?, nfacture = ? 
                            WHERE nfacture = ? AND source = 'achat'
                        """, (new_fournisseur, new_num_facture if new_num_facture else achat_id, original_num_facture_int))
                    except (ValueError, TypeError):
                        # If not int, update by string
                        cn.execute("""
                            UPDATE retenus SET client = ?, nfacture = ? 
                            WHERE nfacture = ? AND source = 'achat'
                        """, (new_fournisseur, new_num_facture if new_num_facture else achat_id, original_num_facture))
                
                # Update retenus by old fournisseur name
                if original_fournisseur:
                    cn.execute("""
                        UPDATE retenus SET client = ?, nfacture = ? 
                        WHERE client = ? AND source = 'achat'
                    """, (new_fournisseur, new_num_facture if new_num_facture else achat_id, original_fournisseur))
                
                cn.commit()
        except Exception as e:
            logger.error(f"Error updating retenus: {e}")
    
    def _cleanup_related_data(self, achat_id: int, achat_details: Dict):
        """Clean up related data when deleting an achat."""
        try:
            fournisseur = achat_details.get('fournisseur', '')
            num_facture_achat = achat_details.get('num_facture', '')
            
            # Clean up related transactions and records using centralized cascade manager
            try:
                from app.stfoom.services.cascade_manager import cascade_manager
                cascade_result = cascade_manager.delete_achat_cascade(achat_id)
                if 'error' in cascade_result:
                    logger.warning(f"Cascade manager reported error for achat {achat_id}: {cascade_result['error']}")
                else:
                    logger.info(f"Cascade deleted for achat {achat_id}: payments={len(cascade_result.get('payments', []))}, retenus={len(cascade_result.get('retenu_records', []))}")
            except Exception as e:
                logger.warning(f"Cascade manager not available or failed for achat {achat_id}: {e}")
                # Fallback: try to delete direct relations using sync system
                try:
                    with self._conn() as cn:
                        # Get IDs first for sync deletion
                        payment_ids = cn.execute("SELECT id FROM paiements_factures WHERE nfacture = ?", (achat_id,)).fetchall()
                        bank_tx_ids = cn.execute("SELECT id FROM transactions_bancaires WHERE nfacture = ? AND type_transaction = 'decaissement'", (achat_id,)).fetchall()
                        caisse_tx_ids = cn.execute("SELECT id FROM caisse_transactions WHERE nfacture = ? AND type = 'decaissement'", (achat_id,)).fetchall()
                        retenu_ids = cn.execute("SELECT id FROM retenus WHERE nfacture = ?", (achat_id,)).fetchall()
                        
                        # Delete using sync system
                        for row in payment_ids:
                            sync.delete_with_sync('paiements_factures', str(row[0]))
                        for row in bank_tx_ids:
                            sync.delete_with_sync('transactions_bancaires', str(row[0]))
                        for row in caisse_tx_ids:
                            sync.delete_with_sync('caisse_transactions', str(row[0]))
                        for row in retenu_ids:
                            sync.delete_with_sync('retenus', str(row[0]))
                            
                except Exception as e2:
                    logger.error(f"Fallback cleanup failed for achat {achat_id}: {e2}")
            
            # Handle ciment facture relationship
            self._cleanup_ciment_relationship(num_facture_achat)
            
        except Exception as e:
            logger.error(f"Error cleaning up related data: {e}")
    
    def _cleanup_ciment_relationship(self, num_facture_achat):
        """Clean up ciment facture relationship when deleting achat."""
        try:
            if num_facture_achat and num_facture_achat.strip():
                # Use direct database access instead of logic imports
                with self._conn() as conn:
                    # Find the corresponding ciment facture
                    ciment_facture = conn.execute(
                        "SELECT id FROM ciment_factures WHERE numero_facture = ?", 
                        (num_facture_achat,)
                    ).fetchone()
                    if ciment_facture:
                        # Delete the ciment facture using sync system
                        try:
                            sync.delete_with_sync('ciment_factures', str(ciment_facture[0]))
                            
                            # Update related BLs using sync system
                            bl_ids = conn.execute(
                                "SELECT id FROM ciment_bons_livraison WHERE numero_facture = ?", 
                                (num_facture_achat,)
                            ).fetchall()
                            
                            for bl_row in bl_ids:
                                sync.update_with_sync('ciment_bons_livraison', str(bl_row[0]), {
                                    'statut': 'en_attente',
                                    'numero_facture': None
                                })
                            
                            logger.info(f"Deleted ciment facture {num_facture_achat} and reset {len(bl_ids)} BLs to 'en_attente' with sync")
                        except Exception as e:
                            logger.warning(f"Could not delete ciment facture: {e}")
        except Exception as e:
            logger.warning(f"Could not handle ciment facture relationship: {e}")
    
    def _sync_achat_changes_to_ciment(self, achat_id: int, new_data: dict, original_data: dict):
        """Sync achat changes to corresponding ciment facture."""
        try:
            # Get the facture numbers
            original_num_facture = original_data.get('num_facture', '')
            new_num_facture = new_data.get('num_facture', '')
            
            # If no facture number, nothing to sync
            if not original_num_facture and not new_num_facture:
                return
            
            # Use direct database access instead of logic imports
            with self.get_connection() as conn:
                # Find corresponding ciment facture
                ciment_facture = None
                if original_num_facture:
                    ciment_facture = conn.execute(
                        "SELECT id, numero_facture FROM ciment_factures WHERE numero_facture = ?", 
                        (original_num_facture,)
                    ).fetchone()
            
            if ciment_facture:
                facture_id, current_numero = ciment_facture
                
                # Prepare ciment facture update data
                ciment_update = {}
                
                # Sync facture number
                if new_num_facture and new_num_facture != original_num_facture:
                    ciment_update["numero_facture"] = new_num_facture
                
                # Sync amount
                if "montant" in new_data:
                    montant_total = float(new_data["montant"])
                    # Calculate HT and TVA (assuming 19% TVA)
                    montant_ht = montant_total / 1.19
                    tva = montant_total - montant_ht
                    
                    ciment_update["montant_total"] = montant_total
                    ciment_update["montant_ht"] = montant_ht
                    ciment_update["tva"] = tva
                
                # Sync date
                if "date_facture" in new_data:
                    ciment_update["date_facture"] = new_data["date_facture"]
                
                # Sync supplier
                if "fournisseur" in new_data and new_data["fournisseur"] != original_data.get("fournisseur", ""):
                    # Try to find supplier code (this is approximate)
                    supplier_name = new_data["fournisseur"]
                    supplier = conn.execute(
                        "SELECT code_fournisseur FROM fournisseurs WHERE nom_fournisseur LIKE ?", 
                        (f"%{supplier_name}%",)
                    ).fetchone()
                    if supplier:
                        ciment_update["code_fournisseur"] = supplier[0]
                
                # Apply updates if any
                if ciment_update:
                    ciment_update["updated_at"] = datetime.now().isoformat()
                    # Update ciment facture directly
                    set_clause = ", ".join([f"{k} = ?" for k in ciment_update.keys()])
                    values = list(ciment_update.values()) + [facture_id]
                    conn.execute(f"UPDATE ciment_factures SET {set_clause} WHERE id = ?", values)
                    conn.commit()
                    logger.info(f"Synced changes to ciment facture {current_numero}")
            
        except Exception as e:
            logger.error(f"Error syncing to ciment: {e}")
    
    def _update_related_transactions(self, achat_id, new_fournisseur, new_num_facture, 
                                   original_fournisseur, original_num_facture):
        """Update related transactions when achat details change."""
        # TODO: Implement through BankService and CaisseService when available
        logger.info(f"Achat {achat_id} related transactions update deferred to services")
    
    def _cleanup_related_transactions(self, achat_id, num_facture_achat):
        """Clean up related transactions when deleting achat."""  
        # TODO: Implement through BankService, CaisseService, and CalendarService when available
        logger.info(f"Achat {achat_id} related transactions cleanup deferred to services")

    # ===== GENERIC CRUD INTERFACE FOR SYNC TESTING =====

    def create(self, data: Dict) -> Optional[int]:
        """
        Generic create method for sync testing.
        
        Args:
            data: Dictionary containing achat information
            
        Returns:
            The ID of the created record if successful, None otherwise
        """
        return self.insert_achat(data)
    
    def update(self, achat_id: int, data: Dict) -> bool:
        """
        Generic update method for sync testing.
        
        Args:
            achat_id: The ID of the achat to update
            data: Dictionary containing updated achat information
            
        Returns:
            True if updated successfully, False otherwise
        """
        return self.update_achat(achat_id, data)
    
    def delete(self, achat_id: int) -> bool:
        """
        Generic delete method for sync testing (soft delete).
        
        Args:
            achat_id: The ID of the achat to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        return self.delete_achat(achat_id)
    
    def get_all(self) -> List[Dict]:
        """
        Generic get_all method for sync testing.
        
        Returns:
            List of all achat dictionaries
        """
        return self.fetch_all_achats()

    # ===== SUPPLIER MANAGEMENT METHODS =====
    
    def get_all_suppliers(self) -> List[Dict]:
        """
        Get all suppliers from database.
        
        Returns:
            List of supplier dictionaries
        """
        try:
            with self._conn() as conn:
                # First, try to get from fournisseurs table
                try:
                    cursor = conn.execute("SELECT * FROM fournisseurs WHERE (deleted = 0 OR deleted IS NULL) ORDER BY nom_fournisseur")
                    suppliers = [dict(row) for row in cursor.fetchall()]
                    logger.info(f"Retrieved {len(suppliers)} suppliers from fournisseurs table")
                    return suppliers
                except sqlite3.OperationalError:
                    # If fournisseurs table doesn't exist, create it and return empty list
                    logger.info("Creating fournisseurs table")
                    conn.execute('''
                        CREATE TABLE fournisseurs (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            code_fournisseur TEXT UNIQUE NOT NULL,
                            nom_fournisseur TEXT NOT NULL,
                            adresse TEXT,
                            telephone TEXT,
                            email TEXT,
                            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                        )
                    ''')
                    conn.commit()
                    return []
                    
        except Exception as e:
            logger.error(f"Error getting all suppliers: {e}")
            return []
    
    def create_supplier(self, supplier_data: Dict) -> bool:
        """
        Create a new supplier.
        
        Args:
            supplier_data: Dictionary containing supplier information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._conn() as conn:
                # Ensure fournisseurs table exists
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS fournisseurs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code_fournisseur TEXT UNIQUE NOT NULL,
                        nom_fournisseur TEXT NOT NULL,
                        adresse TEXT,
                        telephone TEXT,
                        email TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Insert supplier using db_helpers
                insert_row('fournisseurs', supplier_data)
                
                logger.info(f"Created supplier: {supplier_data.get('nom_fournisseur', 'Unknown')}")
                return True
                
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            return False
    
    def update_supplier(self, supplier_id: int, supplier_data: Dict) -> bool:
        """
        Update an existing supplier.
        
        Args:
            supplier_id: ID of the supplier to update
            supplier_data: Dictionary containing updated supplier information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._conn() as conn:
                # Update supplier using db_helpers
                update_row('fournisseurs', 'id', supplier_id, supplier_data)
                
                logger.info(f"Updated supplier ID {supplier_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {e}")
            return False
    
    def delete_supplier(self, supplier_id: int) -> bool:
        """
        Delete a supplier.
        
        Args:
            supplier_id: ID of the supplier to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self._conn() as conn:
                # Check if supplier is used in any achats
                cursor = conn.execute(
                    "SELECT COUNT(*) as count FROM achats WHERE fournisseur IN (SELECT nom_fournisseur FROM fournisseurs WHERE id = ?)",
                    (supplier_id,)
                )
                count = cursor.fetchone()[0]
                
                if count > 0:
                    logger.warning(f"Cannot delete supplier {supplier_id} - used in {count} achats")
                    return False
                
                # Soft delete supplier using db_helpers
                update_row('fournisseurs', 'id', supplier_id, {'deleted_at': datetime.now().timestamp()})
                
                logger.info(f"Soft deleted supplier ID {supplier_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error deleting supplier {supplier_id}: {e}")
            return False
    
    def get_next_supplier_code(self) -> str:
        """
        Get the next available supplier code (411xxx format).
        
        Returns:
            Next available supplier code
        """
        try:
            with self._conn() as conn:
                # Ensure fournisseurs table exists
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS fournisseurs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        code_fournisseur TEXT UNIQUE NOT NULL,
                        nom_fournisseur TEXT NOT NULL,
                        adresse TEXT,
                        telephone TEXT,
                        email TEXT,
                        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                        updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                # Find the highest existing 411xxx code
                cursor = conn.execute(
                    "SELECT code_fournisseur FROM fournisseurs WHERE code_fournisseur LIKE '411%' ORDER BY code_fournisseur DESC LIMIT 1"
                )
                result = cursor.fetchone()
                
                if result:
                    # Extract number and increment
                    last_code = result[0]
                    try:
                        last_number = int(last_code[3:])  # Get number after "411"
                        next_number = last_number + 1
                        return f"411{next_number:03d}"
                    except (ValueError, IndexError):
                        return "411001"
                else:
                    return "411001"
                    
        except Exception as e:
            logger.error(f"Error generating next supplier code: {e}")
            return "411001"
