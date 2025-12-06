"""
Settings Repository - Clean Data Access Layer
=============================================
Repository pattern implementation for application settings data operations.
Uses the BaseRepository pattern with direct database access.
"""

from typing import List, Dict, Optional
from .base_repository import BaseRepository


class SettingsRepository(BaseRepository):
    """Repository for application settings data access operations."""
    
    def __init__(self):
        """Initialize settings repository."""
        super().__init__("application_settings")
        self._ensure_settings_table()
    
    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "settings"
    
    def _ensure_settings_table(self):
        """Ensure settings table exists with proper structure."""
        try:
            create_sql = '''
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
            '''
            self.execute_command(create_sql)
            
            # Create indexes for better performance
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_settings_category
                ON application_settings(category)
            ''')
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_settings_key
                ON application_settings(category, key)
            ''')
            
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Table initialization error: {e}")
    
    def get_all_settings(self) -> List[Dict]:
        """Get all settings ordered by category and key."""
        try:
            sql = """
                SELECT * FROM application_settings
                ORDER BY category ASC, key ASC
            """
            rows = self.execute_query(sql)
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get all settings error: {e}")
            return []
    
    def get_settings_by_category(self, category: str) -> List[Dict]:
        """Get all settings for a specific category."""
        try:
            sql = """
                SELECT * FROM application_settings
                WHERE category = ?
                ORDER BY key ASC
            """
            rows = self.execute_query(sql, (category,))
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings by category error: {e}")
            return []
    
    def get_setting(self, category: str, key: str) -> Optional[Dict]:
        """Get a specific setting by category and key."""
        try:
            sql = """
                SELECT * FROM application_settings
                WHERE category = ? AND key = ?
            """
            rows = self.execute_query(sql, (category, key))
            return dict(rows[0]) if rows else None
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get setting error: {e}")
            return None
    
    def set_setting(self, category: str, key: str, value: str, 
                   description: str = None, data_type: str = 'string') -> bool:
        """Set or update a setting value."""
        try:
            # Check if setting exists
            existing = self.get_setting(category, key)
            
            if existing:
                # Update existing setting
                sql = """
                    UPDATE application_settings
                    SET value = ?, description = ?, data_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category = ? AND key = ?
                """
                success = self.execute_command(sql, (value, description, data_type, category, key))
            else:
                # Insert new setting
                sql = """
                    INSERT INTO application_settings (category, key, value, description, data_type)
                    VALUES (?, ?, ?, ?, ?)
                """
                success = self.execute_command(sql, (category, key, value, description, data_type))
            
            return success
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Set setting error: {e}")
            return False
    
    def delete_setting(self, category: str, key: str) -> bool:
        """Delete a setting."""
        try:
            sql = """
                DELETE FROM application_settings
                WHERE category = ? AND key = ?
            """
            success = self.execute_command(sql, (category, key))
            return success
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Delete setting error: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Get all unique categories."""
        try:
            sql = """
                SELECT DISTINCT category FROM application_settings
                ORDER BY category ASC
            """
            rows = self.execute_query(sql)
            return [row[0] for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get categories error: {e}")
            return []
    
    def get_settings_count(self) -> int:
        """Get total count of settings."""
        try:
            sql = """
                SELECT COUNT(*) FROM application_settings
            """
            rows = self.execute_query(sql)
            return rows[0][0] if rows else 0
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings count error: {e}")
            return 0
    
    def clear_category(self, category: str) -> bool:
        """Clear all settings in a category."""
        try:
            sql = """
                DELETE FROM application_settings WHERE category = ?
            """
            success = self.execute_command(sql, (category,))
            return success
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Clear category error: {e}")
            return False
