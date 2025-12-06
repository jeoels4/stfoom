from app.stfoom.logic.db_helpers import insert_row, update_row, soft_delete_row
"""
FactureRepository - Phase 2I Migration
======================================
Repository layer for invoice generation data access.
Migrated from direct secure_database and invoice_gen dependencies.
"""

from typing import Dict, List, Optional, Any
import logging
import sqlite3
from contextlib import contextmanager
from app.stfoom.logic.secure_database import _get_db_path
from app.stfoom.data.base_repository import BaseRepository

# Placeholder database functions for migration
class DatabasePlaceholder:
    """Placeholder for database operations during migration."""
    
    @contextmanager
    def get_connection(self):
        """Get database connection."""
        db_path = _get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def load_clients(self):
        """Load clients from database."""
        try:
            import pandas as pd
            with self.get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM clients", conn)
        except:
            import pandas as pd
            return pd.DataFrame()
    
    def load_products(self):
        """Load products from database."""
        try:
            import pandas as pd
            with self.get_connection() as conn:
                return pd.read_sql_query("SELECT * FROM products", conn)
        except:
            import pandas as pd
            return pd.DataFrame()
    
    def load_client_by_code(self, code: str):
        """Load client by code."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT * FROM clients WHERE code_client = ?", (code,))
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[CLIENT LOOKUP] Error: {e}")
            return None
    
    def exec_read_one(self, sql: str, params=()):
        """Execute read query returning one result."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute(sql, params)
                row = cursor.fetchone()
                if row:
                    # Convert SQLite Row to dictionary properly
                    return {key: row[key] for key in row.keys()}
                return None
        except:
            return None
    
    def exec_write(self, sql: str, params=()):
        """Execute write query."""
        try:
            with self.get_connection() as conn:
                conn.execute(sql, params)
                conn.commit()
                return True
        except:
            return False

# Use app connection sync_wrapper for database access
import sqlite3
import os
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)


def exec_read_all(query: str, params=()) -> list:
    """Execute a SELECT query and return all results as list of dicts."""
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
    except Exception as e:
        print(f"[FACTURE REPO] Database read error: {e}")
        return []

def exec_write(query: str, params=()) -> int:
    """Execute an INSERT/UPDATE/DELETE query."""
    try:
        with sqlite3.connect(_get_db_path()) as conn:
            cursor = conn.cursor()
            if isinstance(params, dict):
                # Named parameters
                cursor.execute(query, params)
            else:
                # Positional parameters
                cursor.execute(query, params)
            conn.commit()
            return cursor.rowcount
    except Exception as e:
        print(f"[FACTURE REPO] Database write error: {e}")
        return 0

class FactureRepository:
    """Repository for invoice generation data access."""
    
    def __init__(self):
        """Initialize FactureRepository."""
        self.logger = logging.getLogger('facture_repository')
        print("[FACTURE REPOSITORY] Initialized")
    
    def get_all_clients(self) -> List[Dict]:
        """
        Get all clients from database.
        
        Returns:
            List[Dict]: List of client dictionaries
        """
        try:
            clients = exec_read_all("""
                SELECT code_client, raison_sociale, adresse, tva,
                       tel, chantier 
                FROM clients 
                ORDER BY raison_sociale
            """, ())
            return clients
        except Exception as e:
            self.logger.error(f"Error loading clients: {e}")
            print(f"[FACTURE REPOSITORY] Error loading clients: {e}")
            return []
    
    def get_all_products(self) -> List[Dict]:
        """
        Get all products from database.
        
        Returns:
            List[Dict]: List of product dictionaries
        """
        try:
            print("[FACTURE REPOSITORY] Loading products from database...")
            products = exec_read_all("""
                SELECT code, designation, unite, prix_ht
                FROM products 
                ORDER BY designation
            """, ())
            
            if not products:
                print("[FACTURE REPOSITORY] No products found in database")
                return []
                
            print(f"[FACTURE REPOSITORY] Loaded {len(products)} products")
            return products
            
        except Exception as e:
            self.logger.error(f"Error loading products: {e}")
            print(f"[FACTURE REPOSITORY] Error loading products: {e}")
            
            # Use unified logger if available
            try:
                from unified_logger import log_database_error
                log_database_error(f"Error loading products: {e}", {"repository": "facture_repository"}, e)
            except ImportError:
                pass
                
            import traceback
            traceback.print_exc()
            return []
    
    def get_client_by_code(self, code_client: str) -> Optional[Dict]:
        """
        Get a client by their code.
        
        Args:
            code_client: Client code to search for
            
        Returns:
            Optional[Dict]: Client data or None if not found
        """
        try:
            clients = exec_read_all(
                "SELECT * FROM clients WHERE code_client = ?",
                (code_client,)
            )
            if not clients:
                return None
            
            client_dict = clients[0]
            return client_dict
        except Exception as e:
            self.logger.error(f"Error loading client by code {code_client}: {e}")
            print(f"[FACTURE REPOSITORY] Error loading client by code {code_client}: {e}")
            return None
    
    def get_last_invoice_number_for_year(self, year: int) -> int:
        """
        Get the last invoice number for a specific year.
        
        Args:
            year: Year to search for
            
        Returns:
            int: Last invoice number for the year (0 if none found)
        """
        try:
            # Use direct database access for reliability
            import sqlite3
            import os
            
            # Get database path directly
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            db_path = os.path.join(data_dir, 'stfoom.db')
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT COALESCE(MAX(nfacture), 0) as max_invoice FROM ventes WHERE nfacture LIKE ?",
                    (f"{year}%",)
                )
                row = cursor.fetchone()
                if row:
                    return row[0] if hasattr(row, '__getitem__') else row[0]
                return 0
        except Exception as e:
            self.logger.error(f"Error getting last invoice number for year {year}: {e}")
            print(f"[FACTURE REPOSITORY] Error getting last invoice number for year {year}: {e}")
            return 0
    
    def invoice_exists(self, nfacture_int: int) -> bool:
        """
        Check if an invoice number already exists.
        
        Args:
            nfacture_int: Invoice number to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        try:
            result = exec_read_all("SELECT COUNT(*) FROM ventes WHERE nfacture = ?", (nfacture_int,))
            return result[0]['COUNT(*)'] > 0 if result else False
        except Exception as e:
            self.logger.error(f"Error checking invoice existence for {nfacture_int}: {e}")
            print(f"[FACTURE REPOSITORY] Error checking invoice existence for {nfacture_int}: {e}")
            return False
    
    def generate_invoice_file(self, client: Dict, chantier: str, selection: List[Dict], 
                             nfacture_int: int, date_facture: Optional[str] = None) -> str:
        """
        Generate an invoice file using the invoice generation engine.
        
        Args:
            client: Client data dictionary
            chantier: Project/site name
            selection: List of selected products with quantities
            nfacture_int: Invoice number to use
            date_facture: Optional specific invoice date
            
        Returns:
            str: Path to generated invoice file
            
        Raises:
            Exception: If invoice generation fails
        """
        try:
            # ✅ PHASE 2I MIGRATION: Use new invoice generation engine
            from ..services.invoice_generation_engine import InvoiceGenerator
            
            # Create invoice generator with this repository as dependency
            invoice_gen = InvoiceGenerator(self)
            
            # Generate invoice using the complete logic
            file_path = invoice_gen.generate_invoice(
                client, chantier, selection, nfacture_int, date_facture
            )
            
            self.logger.info(f"Invoice generated successfully: {file_path}")
            print(f"[FACTURE REPOSITORY] Invoice generated successfully: {file_path}")
            return file_path
            
        except Exception as e:
            self.logger.error(f"Error generating invoice file: {e}")
            print(f"[FACTURE REPOSITORY] Error generating invoice file: {e}")
            raise
    
    def get_product_by_code(self, code_product: str) -> Optional[Dict]:
        """
        Get a product by its code.
        
        Args:
            code_product: Product code to search for
            
        Returns:
            Optional[Dict]: Product data or None if not found
        """
        try:
            import sqlite3
            import os
            
            # Get database path directly
            data_dir = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'data')
            db_path = os.path.join(data_dir, 'stfoom.db')
            
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT * FROM products WHERE code = ?",
                    (code_product,)
                )
                product_row = cursor.fetchone()
                if product_row is None:
                    return None
            
                # Convert to dict if needed
                if hasattr(product_row, 'keys'):
                    return dict(product_row)
                else:
                    # Row object from sqlite3 - get column names
                    columns = [description[0] for description in cursor.description]
                    return dict(zip(columns, product_row))
        except Exception as e:
            self.logger.error(f"Error loading product by code {code_product}: {e}")
            print(f"[FACTURE REPOSITORY] Error loading product by code {code_product}: {e}")
            return None
    
    def create_vente_record(self, vente_data: Dict) -> bool:
        """
        Create a new vente (sale) record in the database using centralized DB helpers.
        """
        try:
            insert_row('ventes', vente_data)
            self.logger.info(f"Vente record created successfully for invoice {vente_data.get('nfacture', 'unknown')}")
            print(f"[FACTURE REPOSITORY] Vente record created successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error creating vente record: {e}")
            print(f"[FACTURE REPOSITORY] Error creating vente record: {e}")
            return False
    
    def get_vente_by_invoice_number(self, nfacture_int: int) -> Optional[Dict]:
        """
        Get a vente record by invoice number.
        
        Args:
            nfacture_int: Invoice number to search for
            
        Returns:
            Optional[Dict]: Vente data or None if not found
        """
        try:
            # ✅ PHASE 2I MIGRATION: Use real database access
            rows = exec_read_all("SELECT * FROM ventes WHERE nfacture = ?", (nfacture_int,))
            if rows:
                return rows[0]  # Return first row as dict
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching vente by invoice number {nfacture_int}: {e}")
            print(f"[FACTURE REPOSITORY] Error fetching vente by invoice number {nfacture_int}: {e}")
            return None
    
    # ================================ FACTURES CRUD METHODS ================================
    # Added for Smart Sync integration - handles factures table operations
    
    def create(self, facture_data: Dict) -> bool:
        """
        Generic create method for sync testing.
        Delegates to create_facture for automatic sync tracking.
        
        Args:
            facture_data: Facture data dictionary
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.create_facture(facture_data) is not None
    
    def update(self, facture_id: int, facture_data: Dict, id_column: str = "id") -> bool:
        """
        Generic update method for sync testing.
        Delegates to update_facture for automatic sync tracking.
        
        Args:
            facture_id: Facture ID to update
            facture_data: Updated facture data
            id_column: ID column name (ignored, always uses 'id')
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.update_facture(facture_id, facture_data)
    
    def delete(self, facture_id: int, id_column: str = "id") -> bool:
        """
        Generic delete method for sync testing.
        Delegates to delete_facture for automatic sync tracking.
        
        Args:
            facture_id: Facture ID to delete
            id_column: ID column name (ignored, always uses 'id')
            
        Returns:
            bool: True if successful, False otherwise
        """
        return self.delete_facture(facture_id)
    
    def get_all(self) -> List[Dict]:
        """
        Generic get_all method for sync testing.
        Delegates to get_all_factures.
        
        Returns:
            List[Dict]: List of all facture records
        """
        return self.get_all_factures()
    
    def create_facture(self, facture_data: Dict) -> Optional[int]:
        """
        Create a new facture record using centralized DB helpers.
        Automatically adds timestamps and sync tracking.
        
        Args:
            facture_data: Facture data dictionary
            
        Returns:
            Optional[int]: ID of created facture or None if failed
        """
        try:
            # Ensure required fields - map nfacture to numero_facture
            if 'nfacture' in facture_data and 'numero_facture' not in facture_data:
                facture_data['numero_facture'] = facture_data.pop('nfacture')
            elif not facture_data.get('numero_facture'):
                facture_data['numero_facture'] = self._generate_next_facture_number()
            
            # Insert using parking lot dispenser (automatic timestamps + sync tracking)
            insert_row('factures', facture_data)
            
            # Get the inserted ID
            result = exec_read_all("SELECT id FROM factures WHERE numero_facture = ? ORDER BY id DESC LIMIT 1", 
                                 (facture_data['numero_facture'],))
            if result:
                facture_id = result[0]['id']
                self.logger.info(f"Facture record created successfully: {facture_data['numero_facture']}")
                print(f"[FACTURE REPOSITORY] Facture record created: {facture_data['numero_facture']}")
                return facture_id
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error creating facture record: {e}")
            print(f"[FACTURE REPOSITORY] Error creating facture record: {e}")
            return None
    
    def update_facture(self, facture_id: int, facture_data: Dict) -> bool:
        """
        Update an existing facture record using centralized DB helpers.
        Automatically adds timestamps and sync tracking.
        
        Args:
            facture_id: Facture ID to update
            facture_data: Updated facture data
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Update using parking lot dispenser (automatic timestamps + sync tracking)
            update_row('factures', 'id', facture_id, facture_data)
            self.logger.info(f"Facture record updated successfully: {facture_id}")
            print(f"[FACTURE REPOSITORY] Facture record updated: {facture_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error updating facture record {facture_id}: {e}")
            print(f"[FACTURE REPOSITORY] Error updating facture record {facture_id}: {e}")
            return False
    
    def delete_facture(self, facture_id: int) -> bool:
        """
        Soft delete a facture record using centralized DB helpers.
        Automatically adds timestamps and sync tracking.
        
        Args:
            facture_id: Facture ID to delete
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Custom soft delete for factures table which uses deleted_at instead of deleted
            from datetime import datetime
            now = datetime.now().isoformat()
            
            # Update using direct SQL since factures table uses deleted_at field
            exec_write(
                "UPDATE factures SET deleted_at = ?, updated_at = ? WHERE id = ?",
                (now, now, facture_id)
            )
            
            # Track the change for sync
            from app.stfoom.data.base_repository import BaseRepository
            base_repo = BaseRepository()
            base_repo._track_change('factures', 'delete', {'id': facture_id})
            
            self.logger.info(f"Facture record soft deleted successfully: {facture_id}")
            print(f"[FACTURE REPOSITORY] Facture record soft deleted: {facture_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error deleting facture record {facture_id}: {e}")
            print(f"[FACTURE REPOSITORY] Error deleting facture record {facture_id}: {e}")
            return False
    
    def get_all_factures(self) -> List[Dict]:
        """
        Get all facture records for sync testing.
        Used by the smart sync system to verify repository functionality.
        
        Returns:
            List[Dict]: List of all facture records
        """
        try:
            factures = exec_read_all("""
                SELECT * FROM factures 
                WHERE (deleted = 0 OR deleted IS NULL) 
                ORDER BY created_at DESC
            """, ())
            return factures
            
        except Exception as e:
            self.logger.error(f"Error loading all factures: {e}")
            print(f"[FACTURE REPOSITORY] Error loading all factures: {e}")
            return []
    
    def get_facture_by_id(self, facture_id: int) -> Optional[Dict]:
        """
        Get a facture record by ID.
        
        Args:
            facture_id: Facture ID to search for
            
        Returns:
            Optional[Dict]: Facture data or None if not found
        """
        try:
            factures = exec_read_all("SELECT * FROM factures WHERE id = ? AND (deleted = 0 OR deleted IS NULL)", (facture_id,))
            if factures:
                return factures[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching facture by ID {facture_id}: {e}")
            print(f"[FACTURE REPOSITORY] Error fetching facture by ID {facture_id}: {e}")
            return None
    
    def get_facture_by_number(self, nfacture: str) -> Optional[Dict]:
        """
        Get a facture record by facture number.
        
        Args:
            nfacture: Facture number to search for
            
        Returns:
            Optional[Dict]: Facture data or None if not found
        """
        try:
            factures = exec_read_all("SELECT * FROM factures WHERE numero_facture = ? AND (deleted = 0 OR deleted IS NULL)", (nfacture,))
            if factures:
                return factures[0]
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching facture by number {nfacture}: {e}")
            print(f"[FACTURE REPOSITORY] Error fetching facture by number {nfacture}: {e}")
            return None
    
    def _generate_next_facture_number(self) -> str:
        """
        Generate the next facture number in YYYY00001 format.
        
        Returns:
            str: Next facture number
        """
        try:
            from datetime import datetime
            year = datetime.now().year
            year_prefix = str(year)
            
            # Get the last facture number for this year
            result = exec_read_all(
                "SELECT numero_facture FROM factures WHERE numero_facture LIKE ? ORDER BY numero_facture DESC LIMIT 1",
                (f"{year_prefix}%",)
            )
            
            if result:
                last_number = result[0]['numero_facture']
                # Extract the numeric part and increment
                numeric_part = int(last_number[4:]) + 1
            else:
                numeric_part = 1
            
            # Format as YYYY00001
            return f"{year_prefix}{numeric_part:05d}"
            
        except Exception as e:
            self.logger.error(f"Error generating next facture number: {e}")
            print(f"[FACTURE REPOSITORY] Error generating next facture number: {e}")
            # Fallback to timestamp-based number
            import time
            return f"{year}{int(time.time()) % 100000:05d}"
