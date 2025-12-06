"""
Settings Repository - Data Access Layer
======================================
Repository pattern implementation for application settings data operations.
Part of Phase 3A: Logic → Services migration (Tax → Settings conversion).
"""

from typing import List, Dict, Optional
from ..logic.secure_database import exec_read_all, exec_read_one, exec_write
from app.connection.sync_wrapper import exec_write_with_sync
from ..logic.authentication_guard import system_operation

class SettingsRepository:
    """Repository for application settings data access operations."""
    
    def __init__(self):
        """Initialize settings repository."""
        self._ensure_settings_table()
    
    def _ensure_settings_table(self):
        """Ensure settings table exists with proper structure."""
        try:
            with system_operation("Initialize settings table"):
                exec_write_with_sync('''
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
                ''', ())
                
                # Create indexes for better performance
                exec_write_with_sync('''
                    CREATE INDEX IF NOT EXISTS idx_settings_category 
                    ON application_settings(category)
                ''', ())
                
                exec_write_with_sync('''
                    CREATE INDEX IF NOT EXISTS idx_settings_key 
                    ON application_settings(category, key)
                ''', ())
                
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Table initialization error: {e}")
    
    def get_all_settings(self) -> List[Dict]:
        """Get all settings ordered by category and key."""
        try:
            rows = exec_read_all("""
                SELECT * FROM application_settings 
                ORDER BY category ASC, key ASC
            """, ())
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get all settings error: {e}")
            return []
    
    def get_settings_by_category(self, category: str) -> List[Dict]:
        """Get all settings for a specific category."""
        try:
            rows = exec_read_all("""
                SELECT * FROM application_settings 
                WHERE category = ? 
                ORDER BY key ASC
            """, (category,))
            return [dict(row) for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings by category error: {e}")
            return []
    
    def get_setting(self, category: str, key: str) -> Optional[Dict]:
        """Get specific setting by category and key."""
        try:
            row = exec_read_one("""
                SELECT * FROM application_settings 
                WHERE category = ? AND key = ?
            """, (category, key))
            return dict(row) if row else None
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get setting error: {e}")
            return None
    
    def set_setting(self, category: str, key: str, value: str, 
                   description: str = None, data_type: str = "string") -> bool:
        """Set/update a setting value."""
        try:
            with system_operation(f"Set setting: {category}.{key}"):
                # Try to update first
                success = exec_write_with_sync("""
                    UPDATE application_settings 
                    SET value = ?, description = ?, data_type = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE category = ? AND key = ?
                """, (value, description, data_type, category, key))
                
                # If no rows affected, insert new setting
                if success:
                    # Check if any row was actually updated
                    existing = exec_read_one("""
                        SELECT id FROM application_settings 
                        WHERE category = ? AND key = ?
                    """, (category, key))
                    
                    if not existing:
                        # Insert new setting
                        success = exec_write_with_sync("""
                            INSERT INTO application_settings 
                            (category, key, value, description, data_type) 
                            VALUES (?, ?, ?, ?, ?)
                        """, (category, key, value, description, data_type))
                
                return bool(success)
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Set setting error: {e}")
            return False
    
    def delete_setting(self, category: str, key: str) -> bool:
        """Delete a setting."""
        try:
            with system_operation(f"Delete setting: {category}.{key}"):
                success = exec_write_with_sync("""
                    DELETE FROM application_settings 
                    WHERE category = ? AND key = ?
                """, (category, key))
                return bool(success)
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Delete setting error: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Get all unique setting categories."""
        try:
            rows = exec_read_all("""
                SELECT DISTINCT category FROM application_settings 
                ORDER BY category ASC
            """, ())
            return [row['category'] for row in rows] if rows else []
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get categories error: {e}")
            return []
    
    def get_settings_count(self) -> int:
        """Get total count of settings."""
        try:
            row = exec_read_one("SELECT COUNT(*) as count FROM application_settings", ())
            return row['count'] if row else 0
        except Exception as e:
            print(f"[SETTINGS_REPOSITORY] Get settings count error: {e}")
            return 0
