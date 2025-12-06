"""
Chantier Remise Service - Manages worksite-based discounts and specific prices
"""

from __future__ import annotations
import sqlite3
import pandas as pd
from typing import List, Dict, Optional
from datetime import datetime
from app.core.path_manager import get_db_path

class ChantierRemiseService:
    """Service for managing chantier-based remises and specific prices"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
    
    def _get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path, check_same_thread=False)
    
    def get_all_chantiers(self) -> List[str]:
        """Get list of all chantier names that have remises configured"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT chantier_name FROM chantier_remises ORDER BY chantier_name')
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_chantiers(self) -> List[str]:
        """Get list of all chantiers from clients table (for selection)"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT DISTINCT chantier FROM clients WHERE chantier IS NOT NULL AND chantier != "" ORDER BY chantier')
            return [row[0] for row in cursor.fetchall() if row[0] and row[0].strip()]
    
    def get_client_chantiers(self, client_code: int) -> List[str]:
        """
        Get chantiers for a specific client
        
        Args:
            client_code: Client code to get chantiers for
            
        Returns:
            List of chantier names for this client
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            # First check if client has remises already configured
            # Handle both string and integer client_code formats
            cursor.execute('''
                SELECT DISTINCT chantier_name 
                FROM chantier_remises 
                WHERE client_code = ? OR client_code = CAST(? AS TEXT)
                ORDER BY chantier_name
            ''', (client_code, client_code))
            configured_chantiers = [row[0] for row in cursor.fetchall() if row[0] and row[0].strip()]
            
            if configured_chantiers:
                return configured_chantiers
            
            # If no configured remises, get client's chantier from clients table
            cursor.execute('SELECT chantier FROM clients WHERE code_client = ?', (client_code,))
            result = cursor.fetchone()
            if result and result[0] and result[0].strip() and result[0] != 'None':
                chantier_name = result[0].strip()
                
                # Auto-create remises for this chantier if they don't exist
                cursor.execute('SELECT COUNT(*) FROM chantier_remises WHERE chantier_name = ?', (chantier_name,))
                remise_count = cursor.fetchone()[0]
                
                if remise_count == 0:
                    print(f"[CHANTIER] Auto-creating remises for chantier '{chantier_name}' for client {client_code}")
                    # Create remises outside the current connection context
                    self.create_new_chantier_for_client(chantier_name, client_code)
                
                return [chantier_name]
            
            return []
    
    def get_products(self) -> List[Dict]:
        """Get list of all products"""
        with self._get_connection() as conn:
            df = pd.read_sql_query('SELECT code, designation FROM products ORDER BY code', conn)
            return df.to_dict('records')
    
    def get_chantier_remises(self, chantier_name: str) -> Dict[str, Dict]:
        """
        Get all remises for a specific chantier
        
        Returns:
            Dict with product_code as key and remise data as value
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT product_code, remise_percentage, prix_specifique 
                FROM chantier_remises 
                WHERE chantier_name = ?
            ''', (chantier_name,))
            
            remises = {}
            for row in cursor.fetchall():
                product_code, remise_pct, prix_spec = row
                remises[product_code] = {
                    'remise_percentage': remise_pct or 0,
                    'prix_specifique': prix_spec or 0
                }
            return remises
    
    def save_chantier_remise(self, chantier_name: str, product_code: str, 
                           remise_percentage: float = 0, prix_specifique: float = 0, client_code: int = None):
        """Save or update remise for a specific chantier and product"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO chantier_remises 
                (chantier_name, product_code, remise_percentage, prix_specifique, client_code, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (chantier_name, product_code, remise_percentage, prix_specifique, client_code, datetime.now()))
            conn.commit()
    
    def delete_chantier_remises(self, chantier_name: str):
        """Delete all remises for a chantier and update client references"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Delete the chantier remises
            cursor.execute('DELETE FROM chantier_remises WHERE chantier_name = ?', (chantier_name,))
            deleted_count = cursor.rowcount
            
            # Update clients table - clear chantier field for clients that reference this chantier
            cursor.execute('''
                UPDATE clients 
                SET chantier = NULL 
                WHERE chantier = ?
            ''', (chantier_name,))
            updated_clients = cursor.rowcount
            
            conn.commit()
            
            print(f"[CHANTIER DELETE] Deleted {deleted_count} remises and updated {updated_clients} client references")
            return deleted_count > 0
    
    def delete_chantier_product_remise(self, chantier_name: str, product_code: str):
        """Delete specific remise for a chantier and product"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                DELETE FROM chantier_remises 
                WHERE chantier_name = ? AND product_code = ?
            ''', (chantier_name, product_code))
            conn.commit()
    
    def create_new_chantier(self, chantier_name: str) -> bool:
        """Create a new chantier with default remises (0% for all products) - legacy method"""
        return self.create_new_chantier_for_client(chantier_name, None)
    
    def create_new_chantier_for_client(self, chantier_name: str, client_code: int = None) -> bool:
        """Create a new chantier with default remises (0% for all products) for a specific client"""
        if not chantier_name or not chantier_name.strip():
            return False
        
        chantier_name = chantier_name.strip()
        products = self.get_products()
        
        try:
            for product in products:
                self.save_chantier_remise(chantier_name, product['code'], 0, 0, client_code)
            return True
        except Exception as e:
            print(f"Error creating chantier {chantier_name} for client {client_code}: {e}")
            return False
    
    def get_remise_for_product(self, chantier_name: str, product_code: str) -> Dict:
        """Get remise information for a specific chantier and product"""
        remises = self.get_chantier_remises(chantier_name)
        return remises.get(product_code, {'remise_percentage': 0, 'prix_specifique': 0})
    
    def calculate_chantier_discounts(self, chantier_name: str, products_df: pd.DataFrame) -> List[str]:
        """
        Calculate discount messages for a chantier (similar to old client-based system)
        """
        if not chantier_name:
            return []
        
        remises = self.get_chantier_remises(chantier_name)
        discount_messages = []
        
        for _, product in products_df.iterrows():
            product_code = str(product['code']).upper()
            if product_code in remises:
                remise_data = remises[product_code]
                if remise_data['remise_percentage'] > 0:
                    discount_messages.append(
                        f"- {product['designation']}: {int(remise_data['remise_percentage'])}%"
                    )
        
        return discount_messages
