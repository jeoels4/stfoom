"""
Settings Repository - Data Access Layer
======================================
Repository pattern implementation for application settings data operations.
Part of Phase 3A: Logic → Services migration (Tax → Settings conversion).
"""

from typing import List, Dict, Optional
from .base_repository import BaseRepository

class SettingsRepository(BaseRepository):
    """Repository for application settings data access operations."""
    
    def __init__(self):
        """Initialize settings repository."""
        super().__init__("application_settings")
        self._ensure_settings_table()
    
    def get_entity_name(self):
        """Return the entity name for this repository."""
        return "setting"
    
    def _ensure_settings_table(self):
        """Ensure settings table exists with proper structure."""
        try:
            with self.get_connection() as conn:
                conn.execute('''
                    CREATE TABLE IF NOT EXISTS application_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category TEXT NOT NULL,
                        key TEXT NOT NULL,
                        value TEXT NOT NULL,
                        description TEXT,
                        data_type TEXT DEFAULT 'string',
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(category, key)
                    )
                ''')
                
                # Create indexes for better performance
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_settings_category 
                    ON application_settings(category)
                ''')
                
                conn.execute('''
                    CREATE INDEX IF NOT EXISTS idx_settings_key 
                    ON application_settings(category, key)
                ''')
                
                conn.commit()
                
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Table initialization error: {e}")
    
    def get_all_settings(self) -> List[Dict]:
        """Get all settings ordered by category and key."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM application_settings 
                    ORDER BY category ASC, key ASC
                """)
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get all settings error: {e}")
            return []
    
    def get_settings_by_category(self, category: str) -> List[Dict]:
        """Get all settings for a specific category."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM application_settings 
                    WHERE category = ? 
                    ORDER BY key ASC
                """, (category,))
                columns = [col[0] for col in cursor.description]
                return [dict(zip(columns, row)) for row in cursor.fetchall()]
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings by category error: {e}")
            return []
    
    def get_setting(self, category: str, key: str) -> Optional[Dict]:
        """Get specific setting by category and key."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT * FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key))
                row = cursor.fetchone()
                if row:
                    columns = [col[0] for col in cursor.description]
                    return dict(zip(columns, row))
                return None
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get setting error: {e}")
            return None
    
    def set_setting(self, category: str, key: str, value: str, 
                   description: str = None, data_type: str = "string") -> bool:
        """Set/update a setting value with sync."""
        try:
            from app.connection import sync
            
            with self.get_connection() as conn:
                # Check if setting exists
                existing = conn.execute("""
                    SELECT id FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key)).fetchone()
                
                if existing:
                    # Update existing setting using sync
                    data = {
                        'value': value,
                        'description': description,
                        'data_type': data_type,
                        'updated_at': 'CURRENT_TIMESTAMP'
                    }
                    return sync.update_with_sync('application_settings', str(existing[0]), data)
                else:
                    # Insert new setting using sync
                    data = {
                        'category': category,
                        'key': key,
                        'value': value,
                        'description': description,
                        'data_type': data_type
                    }
                    return sync.insert_with_sync('application_settings', data)
                    
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Set setting error: {e}")
            return False
    
    def delete_setting(self, category: str, key: str) -> bool:
        """Delete a setting with sync."""
        try:
            from app.connection import sync
            
            with self.get_connection() as conn:
                # Get setting ID
                row = conn.execute("""
                    SELECT id FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key)).fetchone()
                
                if row:
                    return sync.delete_with_sync('application_settings', str(row[0]))
                return True  # Already deleted
                
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Delete setting error: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Get all unique setting categories."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT DISTINCT category FROM application_settings 
                    ORDER BY category ASC
                """)
                return [row[0] for row in cursor.fetchall()]
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get categories error: {e}")
            return []
    
    def get_settings_count(self) -> int:
        """Get total count of settings."""
        try:
            with self.get_connection() as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM application_settings")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings count error: {e}")
            return 0
