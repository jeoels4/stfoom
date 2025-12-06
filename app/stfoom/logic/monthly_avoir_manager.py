"""
Monthly Avoir Management System (200T/month)
Separate from the daily payment avoir system
"""

import sqlite3
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from stfoom.logic.secure_database import exec_read_all, exec_read_one
from connection.sync_wrapper import exec_write_with_sync

# Flag to prevent repeated initialization messages
_tables_initialized = False

def init_monthly_avoir_tables():
    """Initialize monthly avoir tables"""
    global _tables_initialized
    try:
        # Table for tracking monthly totals and notifications
        exec_write_with_sync("""
            CREATE TABLE IF NOT EXISTS monthly_avoir_tracking (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL, -- Format: YYYY-MM
                total_quantity REAL DEFAULT 0.0,
                avoir_rate REAL DEFAULT 0.0,
                total_avoir_amount REAL DEFAULT 0.0,
                notification_sent INTEGER DEFAULT 0,
                is_processed INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(year_month)
            )
        """)
        
        # Table for tracking which factures contribute to monthly totals
        exec_write_with_sync("""
            CREATE TABLE IF NOT EXISTS monthly_avoir_factures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                year_month TEXT NOT NULL,
                facture_id INTEGER NOT NULL,
                quantity REAL NOT NULL,
                avoir_amount REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (facture_id) REFERENCES ciment_factures(id),
                UNIQUE(year_month, facture_id)
            )
        """)
        
        if not _tables_initialized:
            print("[MONTHLY_AVOIR] Tables initialized successfully")
            _tables_initialized = True
        
    except Exception as e:
        print(f"[MONTHLY_AVOIR] Error initializing tables: {e}")

class MonthlyAvoirManager:
    """Manages 200T/month avoir system separately from payment avoir"""
    
    def __init__(self):
        self.init_tables()
    
    def init_tables(self):
        """Initialize monthly avoir tables"""
        init_monthly_avoir_tables()
    
    def get_current_month_key(self) -> str:
        """Get current month key in YYYY-MM format"""
        return datetime.now().strftime("%Y-%m")
    
    def get_month_key_from_date(self, date_str: str) -> str:
        """Extract month key from date string"""
        if isinstance(date_str, str) and len(date_str) >= 7:
            return date_str[:7]  # YYYY-MM
        return self.get_current_month_key()
    
    def update_monthly_totals(self, facture_id: int) -> Dict:
        """Update monthly totals when a facture is created/modified"""
        try:
            # Get facture data
            facture_data = exec_read_one("""
                SELECT f.date_facture, SUM(bl.quantite) as total_qty
                FROM ciment_factures f
                JOIN ciment_facture_bls cfb ON f.id = cfb.facture_id
                JOIN bon_livraison bl ON cfb.bl_id = bl.id
                WHERE f.id = ?
                GROUP BY f.id
            """, (facture_id,))
            
            if not facture_data:
                return {"error": "Facture not found"}
            
            date_facture, facture_quantity = facture_data
            month_key = self.get_month_key_from_date(date_facture)
            
            # Update or insert facture tracking
            exec_write_with_sync("""
                INSERT OR REPLACE INTO monthly_avoir_factures 
                (year_month, facture_id, quantity, avoir_amount)
                VALUES (?, ?, ?, 0.0)
            """, (month_key, facture_id, facture_quantity))
            
            # Recalculate monthly total
            monthly_total = exec_read_one("""
                SELECT SUM(quantity) 
                FROM monthly_avoir_factures 
                WHERE year_month = ?
            """, (month_key,))[0] or 0.0
            
            # Get current 200T avoir rate
            from stfoom.logic.avoir_manager import avoir_manager
            config = avoir_manager.get_avoir_config()
            rate = config.get('total_factures_200t_month', {}).get('rate', 0.0)
            
            # Calculate total avoir if >= 200T
            total_avoir = 0.0
            notification_needed = False
            
            if monthly_total >= 200.0:
                total_avoir = monthly_total * rate
                notification_needed = True
            
            # Update monthly tracking
            exec_write_with_sync("""
                INSERT OR REPLACE INTO monthly_avoir_tracking 
                (year_month, total_quantity, avoir_rate, total_avoir_amount, notification_sent)
                VALUES (?, ?, ?, ?, 0)
            """, (month_key, monthly_total, rate, total_avoir))
            
            result = {
                "month": month_key,
                "total_quantity": monthly_total,
                "threshold_met": monthly_total >= 200.0,
                "avoir_rate": rate,
                "total_avoir": total_avoir,
                "notification_needed": notification_needed
            }
            
            print(f"[MONTHLY_AVOIR] Updated {month_key}: {monthly_total:.3f}T, Avoir: {total_avoir:.3f}DT")
            
            return result
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error updating monthly totals: {e}")
            return {"error": str(e)}
    
    def get_monthly_summary(self, year_month: str = None) -> Dict:
        """Get monthly avoir summary for a specific month"""
        try:
            from .authentication_guard import SystemOperationContext
            with SystemOperationContext("Get monthly summary"):
                if not year_month:
                    year_month = self.get_current_month_key()
                
                # Get monthly tracking data
                tracking_data = exec_read_one("""
                    SELECT total_quantity, avoir_rate, total_avoir_amount, 
                           notification_sent, is_processed
                    FROM monthly_avoir_tracking 
                    WHERE year_month = ?
                """, (year_month,))
                
                if not tracking_data:
                    return {
                        "month": year_month,
                        "total_quantity": 0.0,
                        "threshold_met": False,
                        "avoir_rate": 0.0,
                        "total_avoir": 0.0,
                        "notification_sent": False,
                        "is_processed": False,
                    "factures": []
                }
            
            total_qty, rate, total_avoir, notif_sent, is_processed = tracking_data
            
            # Get contributing factures
            factures = exec_read_all("""
                SELECT maf.facture_id, maf.quantity, f.numero_facture, f.date_facture
                FROM monthly_avoir_factures maf
                JOIN ciment_factures f ON maf.facture_id = f.id
                WHERE maf.year_month = ?
                ORDER BY f.date_facture
            """, (year_month,))
            
            facture_list = []
            for facture_id, quantity, numero, date_facture in factures:
                facture_list.append({
                    "id": facture_id,
                    "numero": numero,
                    "date": date_facture,
                    "quantity": quantity
                })
            
            return {
                "month": year_month,
                "total_quantity": total_qty,
                "threshold_met": total_qty >= 200.0,
                "avoir_rate": rate,
                "total_avoir": total_avoir,
                "notification_sent": bool(notif_sent),
                "is_processed": bool(is_processed),
                "factures": facture_list
            }
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error getting monthly summary: {e}")
            return {"error": str(e)}
    
    def get_pending_notifications(self) -> List[Dict]:
        """Get months that need notifications (>= 200T but not notified)"""
        try:
            from .authentication_guard import SystemOperationContext
            with SystemOperationContext("Get pending notifications"):
                pending = exec_read_all("""
                    SELECT year_month, total_quantity, total_avoir_amount
                    FROM monthly_avoir_tracking 
                    WHERE total_quantity >= 200.0 
                    AND notification_sent = 0
                    ORDER BY year_month DESC
                """)
                
                notifications = []
                for month, qty, avoir in pending:
                    notifications.append({
                        "month": month,
                        "quantity": qty,
                        "avoir_amount": avoir,
                        "message": f"Mois {month}: {qty:.3f}T (≥200T) - Avoir éligible: {avoir:.3f}DT"
                    })
                
                return notifications
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error getting pending notifications: {e}")
            return []
    
    def mark_notification_sent(self, year_month: str) -> bool:
        """Mark notification as sent for a specific month"""
        try:
            exec_write_with_sync("""
                UPDATE monthly_avoir_tracking 
                SET notification_sent = 1, updated_at = CURRENT_TIMESTAMP
                WHERE year_month = ?
            """, (year_month,))
            
            return True
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error marking notification sent: {e}")
            return False
    
    def get_all_months_summary(self) -> List[Dict]:
        """Get summary for all months with data"""
        try:
            months = exec_read_all("""
                SELECT year_month, total_quantity, total_avoir_amount, 
                       notification_sent, is_processed
                FROM monthly_avoir_tracking 
                ORDER BY year_month DESC
                LIMIT 12  -- Last 12 months
            """)
            
            summary_list = []
            for month, qty, avoir, notif_sent, is_processed in months:
                summary_list.append({
                    "month": month,
                    "total_quantity": qty,
                    "threshold_met": qty >= 200.0,
                    "total_avoir": avoir,
                    "notification_sent": bool(notif_sent),
                    "is_processed": bool(is_processed)
                })
            
            return summary_list
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error getting all months summary: {e}")
            return []
    
    def get_pending_notifications(self) -> List[Dict]:
        """Get months that need notifications sent (for notification system)"""
        try:
            from .authentication_guard import SystemOperationContext
            with SystemOperationContext("Get pending notifications"):
                # Find months with 200T+ that haven't been notified yet
                months = exec_read_all("""
                    SELECT year_month, total_quantity, total_avoir_amount
                    FROM monthly_avoir_tracking
                    WHERE total_quantity >= 200.0 
                    AND notification_sent = 0
                    ORDER BY year_month DESC
                """)
                
                notifications = []
            for month, qty, avoir in months:
                try:
                    # Format month for display
                    date_obj = datetime.strptime(month + "-01", "%Y-%m-%d")
                    month_name = date_obj.strftime("%B %Y")
                    
                    notifications.append({
                        'month': month,
                        'month_display': month_name,
                        'quantity': qty,
                        'avoir_amount': avoir,
                        'message': f"Vous avez atteint {qty:.1f} tonnes en {month_name}! Avoir de {avoir:.3f} DT disponible."
                    })
                    
                except Exception as e:
                    print(f"[MONTHLY_AVOIR] Error formatting notification for {month}: {e}")
                    continue
            
            return notifications
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error getting pending notifications: {e}")
            return []
    
    def mark_notification_sent(self, month_key: str):
        """Mark that notification has been sent for a month"""
        try:
            exec_write_with_sync("""
                UPDATE monthly_avoir_tracking
                SET notification_sent = 1, updated_at = CURRENT_TIMESTAMP
                WHERE year_month = ?
            """, (month_key,))
            
            print(f"[MONTHLY_AVOIR] Marked notification sent for {month_key}")
            
        except Exception as e:
            print(f"[MONTHLY_AVOIR] Error marking notification sent for {month_key}: {e}")

# Global instance
monthly_avoir_manager = MonthlyAvoirManager()
