"""
Devis Repository
===============
Data access layer for devis operations.
"""


from typing import List, Dict, Optional, Any
from datetime import datetime
import sqlite3
from app.stfoom.logic.db_helpers import insert_row, update_row, soft_delete_row
from app.stfoom.logic.secure_database import _get_db_path


class DatabasePlaceholder:
    """Placeholder database implementation for devis operations."""
    
    def get_connection(self):
        """Get database connection."""
        db_path = _get_db_path()
        return sqlite3.connect(db_path)
    
    def exec_write_system(self, sql: str, params=None, reason: str = None):
        """Execute system write operation."""
        return self.exec_write(sql, params)
    
    def exec_write(self, sql: str, params=None):
        """Execute write operation."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                if params:
                    conn.execute(sql, params)
                else:
                    conn.execute(sql)
                conn.commit()
                return True
        except Exception as e:
            print(f"[DB_PLACEHOLDER] Write error: {e}")
            return False
    
    def exec_read_one(self, sql: str, params=None):
        """Execute read operation returning one row."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params or ())
                row = cursor.fetchone()
                return dict(row) if row else None
        except Exception as e:
            print(f"[DB_PLACEHOLDER] Read error: {e}")
            return None
    
    def exec_read_all(self, sql: str, params=None):
        """Execute read operation returning all rows."""
        try:
            with self.get_connection() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(sql, params or ())
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"[DB_PLACEHOLDER] Read all error: {e}")
            return []
    
    def load_products(self):
        """Load all products."""
        sql = "SELECT * FROM products ORDER BY code"
        return self.exec_read_all(sql)
    
    def load_product_by_code(self, code: str):
        """Load product by code."""
        sql = "SELECT * FROM products WHERE code = ?"
        return self.exec_read_one(sql, (code,))


class DevisRepository:
    """Repository for devis data operations."""
    
    def __init__(self):
        self.table_name = "devis"
        self.db = DatabasePlaceholder()
        self.ensure_devis_table()
    
    def ensure_devis_table(self):
        """Ensure devis table exists."""
        create_sql = """
        CREATE TABLE IF NOT EXISTS devis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_number TEXT UNIQUE NOT NULL,
            client_name TEXT NOT NULL,
            is_grand_tunis BOOLEAN DEFAULT 1,
            total_ht REAL DEFAULT 0.0,
            total_ttc REAL DEFAULT 0.0,
            status TEXT DEFAULT 'draft',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            file_path TEXT,
            notes TEXT
        )
        """
        self.db.exec_write_system(create_sql, reason="Initialize devis table")
        
        # Also ensure devis_items table for storing selected products
        items_sql = """
        CREATE TABLE IF NOT EXISTS devis_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            devis_id INTEGER NOT NULL,
            product_code TEXT NOT NULL,
            product_name TEXT NOT NULL,
            custom_price REAL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY (devis_id) REFERENCES devis (id) ON DELETE CASCADE
        )
        """
        self.db.exec_write_system(items_sql, reason="Initialize devis_items table")
    
    def get_next_devis_number(self) -> str:
        """Generate next devis number in YYYY00001 format."""
        year = datetime.now().year
        year_prefix = str(year)
        
        # Get the last devis number for this year
        sql = "SELECT devis_number FROM devis WHERE devis_number LIKE ? ORDER BY devis_number DESC LIMIT 1"
        result = self.db.exec_read_one(sql, (f"{year_prefix}%",))
        
        if result:
            last_number = result["devis_number"]
            # Extract the numeric part and increment
            numeric_part = int(last_number[4:]) + 1
        else:
            numeric_part = 1
        
        # Format as YYYY00001
        return f"{year_prefix}{numeric_part:05d}"
    
    def create_devis(self, devis_data: Dict[str, Any]) -> Optional[int]:
        """Create a new devis record using centralized DB helpers."""
        if not devis_data.get("devis_number"):
            devis_data["devis_number"] = self.get_next_devis_number()
        try:
            insert_row('devis', devis_data)
            # Get the inserted ID
            result = self.db.exec_read_one("SELECT id FROM devis WHERE devis_number = ?", 
                                    (devis_data["devis_number"],))
            return result["id"] if result else None
        except Exception as e:
            print(f"[DEVIS_REPO] Error creating devis: {e}")
            return None
    
    def save_devis_items(self, devis_id: int, items: List[Dict[str, Any]]) -> bool:
        """Save devis items."""
        try:
            # Clear existing items
            self.db.exec_write("DELETE FROM devis_items WHERE devis_id = ?", (devis_id,))
            
            # Insert new items
            for item in items:
                item_data = {
                    "devis_id": devis_id,
                    "product_code": item["code"],
                    "product_name": item["name"],
                    "custom_price": item.get("price"),
                    "quantity": item.get("quantity", 1)
                }
                
                columns = ", ".join(item_data.keys())
                placeholders = ", ".join(["?" for _ in item_data])
                sql = f"INSERT INTO devis_items ({columns}) VALUES ({placeholders})"
                self.db.exec_write(sql, tuple(item_data.values()))
            
            return True
        except Exception as e:
            print(f"[DEVIS_REPO] Error saving items: {e}")
            return False
    
    def get_all_devis(self) -> List[Dict[str, Any]]:
        """Get all devis records."""
        sql = """
        SELECT d.*, COUNT(di.id) as item_count 
        FROM devis d 
        LEFT JOIN devis_items di ON d.id = di.devis_id 
        GROUP BY d.id 
        ORDER BY d.created_at DESC
        """
        return self.db.exec_read_all(sql)
    
    def get_devis_by_id(self, devis_id: int) -> Optional[Dict[str, Any]]:
        """Get devis by ID."""
        sql = "SELECT * FROM devis WHERE id = ?"
        return self.db.exec_read_one(sql, (devis_id,))
    
    def get_devis_by_number(self, devis_number: str) -> Optional[Dict[str, Any]]:
        """Get devis by number."""
        sql = "SELECT * FROM devis WHERE devis_number = ?"
        return self.db.exec_read_one(sql, (devis_number,))
    
    def get_devis_items(self, devis_id: int) -> List[Dict[str, Any]]:
        """Get items for a specific devis."""
        sql = "SELECT * FROM devis_items WHERE devis_id = ? ORDER BY id"
        return self.db.exec_read_all(sql, (devis_id,))
    
    def update_devis_status(self, devis_id: int, status: str) -> bool:
        """Update devis status using centralized DB helpers."""
        try:
            data = {'status': status}
            update_row('devis', 'id', devis_id, data)
            return True
        except Exception as e:
            print(f"[DEVIS_REPO] Error updating devis status: {e}")
            return False
    
    def update_devis_file_path(self, devis_id: int, file_path: str) -> bool:
        """Update devis file path after generation using centralized DB helpers."""
        try:
            data = {'file_path': file_path}
            update_row('devis', 'id', devis_id, data)
            return True
        except Exception as e:
            print(f"[DEVIS_REPO] Error updating devis file path: {e}")
            return False
    
    def update(self, devis_id: int, data: Dict[str, Any]) -> bool:
        """
        Generic update method for sync testing.
        
        Args:
            devis_id: The ID of the devis to update
            data: Dictionary containing updated devis information
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            update_row('devis', 'id', devis_id, data)
            return True
        except Exception as e:
            print(f"[DEVIS_REPO] Error updating devis {devis_id}: {e}")
            return False
    
    def get_devis_by_client(self, client_name: str) -> List[Dict[str, Any]]:
        """Get all devis for a specific client."""
        sql = """
        SELECT d.*, COUNT(di.id) as item_count 
        FROM devis d 
        LEFT JOIN devis_items di ON d.id = di.devis_id 
        WHERE d.client_name LIKE ? 
        GROUP BY d.id 
        ORDER BY d.created_at DESC
        """
        return self.db.exec_read_all(sql, (f"%{client_name}%",))
    
    def get_monthly_devis_stats(self, year: int, month: int) -> Dict[str, Any]:
        """Get devis statistics for a specific month."""
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"
        
        sql = """
        SELECT 
            COUNT(*) as total_count,
            SUM(total_ht) as total_ht,
            SUM(total_ttc) as total_ttc,
            COUNT(CASE WHEN status = 'accepted' THEN 1 END) as accepted_count,
            COUNT(CASE WHEN status = 'rejected' THEN 1 END) as rejected_count,
            COUNT(CASE WHEN status = 'draft' THEN 1 END) as draft_count
        FROM devis 
        WHERE created_at >= ? AND created_at < ?
        """
        
        result = self.db.exec_read_one(sql, (start_date, end_date))
        return result if result else {
            "total_count": 0, "total_ht": 0.0, "total_ttc": 0.0,
            "accepted_count": 0, "rejected_count": 0, "draft_count": 0
        }
    
    def delete_devis(self, devis_id: int) -> bool:
        """Soft delete a devis using centralized DB helpers."""
        try:
            soft_delete_row('devis', 'id', devis_id)
            return True
        except Exception as e:
            print(f"[DEVIS_REPO] Error deleting devis: {e}")
            return False
    
    def get_products(self):
        """Get all products from database."""
        return self.db.load_products()
    
    def get_product_by_code(self, code: str):
        """Get specific product by code."""
        return self.db.load_product_by_code(code)
