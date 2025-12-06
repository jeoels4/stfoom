"""
Avoir Management System for Cement Module
Handles different types of avoir calculations and configurations
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from stfoom.logic.secure_database import exec_read_all, exec_read_one
from connection.sync_wrapper import exec_write_with_sync

def init_avoir_tables():
    """Initialize avoir tables in the main database (standalone function for main.py)"""
    try:
        # Create avoir_config table for storing rates
        exec_write_with_sync("""
            CREATE TABLE IF NOT EXISTS avoir_config (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                type TEXT UNIQUE NOT NULL,
                rate REAL NOT NULL DEFAULT 0.0,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create avoir_applications table for tracking which types apply to each BL
        exec_write_with_sync("""
            CREATE TABLE IF NOT EXISTS avoir_applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bl_id INTEGER NOT NULL,
                avoir_type TEXT NOT NULL,
                is_applied INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bl_id) REFERENCES bon_livraison(id),
                UNIQUE(bl_id, avoir_type)
            )
        """)
        
        print("[AVOIR] Tables initialized successfully")
        
    except Exception as e:
        print(f"[AVOIR] Error initializing tables: {e}")

class AvoirManager:
    """Manages avoir configurations and calculations for cement module"""
    
    def __init__(self):
        self.init_avoir_tables()
    
    def init_avoir_tables(self):
        """Initialize avoir configuration tables"""
        try:
            # Create avoir_config table for storing rates
            exec_write_with_sync("""
                CREATE TABLE IF NOT EXISTS avoir_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT UNIQUE NOT NULL,
                    rate REAL NOT NULL DEFAULT 0.0,
                    description TEXT,
                    is_active INTEGER DEFAULT 1,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create avoir_applications table for tracking which types apply to each BL
            exec_write_with_sync("""
                CREATE TABLE IF NOT EXISTS avoir_applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bl_id INTEGER NOT NULL,
                    avoir_type TEXT NOT NULL,
                    is_applied INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (bl_id) REFERENCES bon_livraison(id),
                    UNIQUE(bl_id, avoir_type)
                )
            """)
            
            # Insert default avoir types with default rates
            self.setup_default_avoir_types()
            
        except Exception as e:
            print(f"[AVOIR] Error initializing tables: {e}")
    
    def setup_default_avoir_types(self):
        """Setup default avoir types with initial rates"""
        from .authentication_guard import SystemOperationContext
        
        default_types = [
            ("payment_before_20_days", 6.545, "Paiement avant 20 jours"),
            ("total_factures_200t_month", 0.0, "Total factures 200 tonnes/mois"),
            ("sur_livraison", 0.0, "Sur livraison"),
            ("par_annee", 0.0, "Par année")
        ]
        
        with SystemOperationContext("Avoir default types setup"):
            for avoir_type, rate, description in default_types:
                try:
                    # Check if type already exists
                    existing = exec_read_one(
                        "SELECT id FROM avoir_config WHERE type = ?", 
                        (avoir_type,)
                    )
                    
                    if not existing:
                        exec_write_with_sync("""
                            INSERT INTO avoir_config (type, rate, description) 
                            VALUES (?, ?, ?)
                        """, (avoir_type, rate, description))
                        print(f"[AVOIR] Added default type: {avoir_type}")
                        
                except Exception as e:
                    print(f"[AVOIR] Error setting up default type {avoir_type}: {e}")
    
    def get_avoir_config(self) -> Dict[str, Dict]:
        """Get all avoir configuration"""
        try:
            from .authentication_guard import SystemOperationContext
            with SystemOperationContext("Get avoir configuration"):
                config = exec_read_all("""
                    SELECT type, rate, description, is_active 
                    FROM avoir_config 
                    ORDER BY 
                        CASE type 
                            WHEN 'payment_before_20_days' THEN 1
                            WHEN 'total_factures_200t_month' THEN 2
                            WHEN 'sur_livraison' THEN 3
                            WHEN 'par_annee' THEN 4
                            ELSE 5
                        END
                """)
                
                result = {}
            for row in config:
                avoir_type, rate, description, is_active = row
                result[avoir_type] = {
                    'rate': rate,
                    'description': description,
                    'is_active': bool(is_active)
                }
            
            return result
            
        except Exception as e:
            print(f"[AVOIR] Error getting config: {e}")
            return {}
    
    def update_avoir_rate(self, avoir_type: str, rate: float) -> bool:
        """Update avoir rate for a specific type"""
        try:
            exec_write_with_sync("""
                UPDATE avoir_config 
                SET rate = ?, updated_at = CURRENT_TIMESTAMP 
                WHERE type = ?
            """, (rate, avoir_type))
            
            print(f"[AVOIR] Updated {avoir_type} rate to {rate}")
            return True
            
        except Exception as e:
            print(f"[AVOIR] Error updating rate for {avoir_type}: {e}")
            return False
    
    def get_default_avoir_selection(self) -> List[str]:
        """Get default avoir types that should be checked by default"""
        return ["payment_before_20_days", "total_factures_200t_month"]

    
    def set_bl_avoir_applications(self, bl_id: int, selected_types: List[str]) -> bool:
        """Set which avoir types apply to a specific BL"""
        try:
            # First, remove all existing applications for this BL
            exec_write_with_sync("DELETE FROM avoir_applications WHERE bl_id = ?", (bl_id,))
            
            # Insert new applications
            for avoir_type in selected_types:
                exec_write_with_sync("""
                    INSERT INTO avoir_applications (bl_id, avoir_type) 
                    VALUES (?, ?)
                """, (bl_id, avoir_type))
            
            print(f"[AVOIR] Set applications for BL {bl_id}: {selected_types}")
            return True
            
        except Exception as e:
            print(f"[AVOIR] Error setting applications for BL {bl_id}: {e}")
            return False
    
    def get_bl_avoir_applications(self, bl_id: int) -> List[str]:
        """Get avoir types applied to a specific BL"""
        try:
            applications = exec_read_all("""
                SELECT avoir_type 
                FROM avoir_applications 
                WHERE bl_id = ? AND is_applied = 1
            """, (bl_id,))
            
            return [app[0] for app in applications]
            
        except Exception as e:
            print(f"[AVOIR] Error getting applications for BL {bl_id}: {e}")
            return []
    
    def calculate_bl_avoir_total(self, bl_id: int, bl_quantity: float) -> Dict[str, float]:
        """Calculate ONLY 20-day payment avoir for a BL (default avoir column)"""
        try:
            # Get avoir config
            config = self.get_avoir_config()
            
            avoir_details = {}
            total_avoir = 0.0
            applied_types = []
            
            # ONLY apply default payment_before_20_days avoir (automatic for all BLs)
            if 'payment_before_20_days' in config and config['payment_before_20_days']['is_active']:
                rate = config['payment_before_20_days']['rate']
                avoir_amount = bl_quantity * rate
                avoir_details['payment_before_20_days'] = avoir_amount
                total_avoir = avoir_amount
                applied_types.append('payment_before_20_days')
            
            return {
                'total': total_avoir,
                'details': avoir_details,
                'applied_types': applied_types
            }
            
        except Exception as e:
            print(f"[AVOIR] Error calculating avoir for BL {bl_id}: {e}")
            return {'total': 0.0, 'details': {}, 'applied_types': []}
            return {'total': 0.0, 'details': {}, 'applied_types': []}
    
    def get_facture_monthly_quantity(self, facture_id: int) -> float:
        """Get total quantity for all factures in the same month as the given facture"""
        try:
            # Get the facture date
            facture_data = exec_read_one("""
                SELECT date_facture FROM factures WHERE id = ?
            """, (facture_id,))
            
            if not facture_data:
                return 0.0
            
            facture_date = facture_data[0]
            
            # Extract year and month from the date
            # Assuming date format is YYYY-MM-DD
            if isinstance(facture_date, str):
                year_month = facture_date[:7]  # Get YYYY-MM part
            else:
                # Handle other date formats if needed
                year_month = str(facture_date)[:7]
            
            # Get total quantity for all factures in that month
            monthly_total = exec_read_one("""
                SELECT SUM(bl.quantite) as total_qty
                FROM factures f
                JOIN ciment_facture_bls cfb ON f.id = cfb.facture_id
                JOIN bon_livraison bl ON cfb.bl_id = bl.id
                WHERE f.date_facture LIKE ?
            """, (f"{year_month}%",))
            
            return monthly_total[0] if monthly_total and monthly_total[0] else 0.0
            
        except Exception as e:
            print(f"[AVOIR] Error getting monthly quantity for facture {facture_id}: {e}")
            return 0.0
    
    def calculate_facture_avoir_summary(self, facture_id: int) -> Dict[str, float]:
        """Calculate ONLY payment avoir summary for a facture (20-day payment avoir only)"""
        try:
            # Get all BLs for this facture
            bls = exec_read_all("""
                SELECT bl.id, bl.quantite 
                FROM bon_livraison bl
                JOIN ciment_facture_bls cfb ON bl.id = cfb.bl_id
                WHERE cfb.facture_id = ?
            """, (facture_id,))
            
            summary = {
                'payment_before_20_days': 0.0,
                'total': 0.0
            }
            
            # Calculate ONLY BL-level payment avoir
            for bl_id, quantity in bls:
                bl_avoir = self.calculate_bl_avoir_total(bl_id, quantity)
                summary['payment_before_20_days'] += bl_avoir['details'].get('payment_before_20_days', 0.0)
            
            # Total is just the payment avoir (monthly 200T avoir is handled separately)
            summary['total'] = summary['payment_before_20_days']
            
            return summary
            
        except Exception as e:
            print(f"[AVOIR] Error calculating facture avoir summary for {facture_id}: {e}")
            return {'payment_before_20_days': 0.0, 'total': 0.0}

# Global instance
avoir_manager = AvoirManager()
