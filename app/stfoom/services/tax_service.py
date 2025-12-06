"""
Settings Service - Business Logic Layer
======================================
Service layer implementation for application settings business operations.
Part of Phase 3A: Logic → Services migration (Tax → Settings conversion).
"""

from typing import List, Dict, Optional, Union, Any
from ..data.settings_repository_clean import SettingsRepository
# from ..logicold.old.access_control import check_permission  # DISABLED: migrated to service
import json

# Placeholder for access control
def check_permission(permission_name, action=None):
    """Placeholder for permission check - always returns True during migration."""
    return True

class SettingsService:
    """Service for application settings business operations."""
    
    def __init__(self, settings_repository: SettingsRepository):
        """Initialize settings service with repository dependency."""
        self.settings_repository = settings_repository
        print("[SETTINGS_SERVICE] Initialized with repository dependency")
        self._ensure_default_settings()
    
    def _ensure_default_settings(self):
        """Ensure default application settings exist."""
        try:
            defaults = {
                # Tax settings
                ("taxes", "tva_rate", "19.0", "Default TVA rate percentage", "float"),
                ("taxes", "fodec_rate", "1.0", "Default FODEC rate percentage", "float"),
                ("taxes", "timbre_amount", "1.0", "Default timbre amount", "float"),
                
                # Company settings
                ("company", "name", "STFOOM", "Company name", "string"),
                ("company", "address", "", "Company address", "string"),
                ("company", "phone", "", "Company phone number", "string"),
                ("company", "email", "", "Company email", "string"),
                
                # Invoice settings
                ("invoice", "next_number", "1", "Next invoice number", "integer"),
                ("invoice", "prefix", "FAC", "Invoice number prefix", "string"),
                ("invoice", "auto_increment", "true", "Auto increment invoice numbers", "boolean"),
                
                # Application settings
                ("app", "theme", "default", "Application theme", "string"),
                ("app", "language", "fr", "Application language", "string"),
                ("app", "backup_frequency", "daily", "Backup frequency", "string"),
                ("app", "session_timeout", "3600", "Session timeout in seconds", "integer"),
            }
            
            for category, key, value, description, data_type in defaults:
                existing = self.settings_repository.get_setting(category, key)
                if not existing:
                    self.settings_repository.set_setting(category, key, value, description, data_type)
                    
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Error setting defaults: {e}")
    
    def get_all_settings(self) -> List[Dict]:
        """Get all settings with business logic validation."""
        try:
            # Check permissions
            if not check_permission("settings", "view"):
                print("[SETTINGS_SERVICE] Permission denied for settings:view")
                return []
            
            settings = self.settings_repository.get_all_settings()
            print(f"[SETTINGS_SERVICE] Retrieved {len(settings)} settings")
            return settings
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Get all settings error: {e}")
            return []
    
    def get_settings_by_category(self, category: str, user=None) -> Dict[str, Any]:
        """Get settings for a specific category."""
        try:
            # Check permissions
            if not check_permission("settings", "view"):
                print("[SETTINGS_SERVICE] Permission denied for settings:view")
                return {}
            
            # Validate input
            if not category or not isinstance(category, str):
                print(f"[SETTINGS_SERVICE] Invalid category: {category}")
                return {}
            
            settings_list = self.settings_repository.get_settings_by_category(category)
            print(f"[SETTINGS_SERVICE] Retrieved {len(settings_list)} settings for category '{category}'")
            
            # Convert list of settings to dict for easier access
            settings_dict = {}
            for setting in settings_list:
                key = setting['key']
                value = setting['value']
                data_type = setting.get('data_type', 'string')
                settings_dict[key] = self._convert_value(value, data_type, None)
            
            return settings_dict
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Get settings by category error: {e}")
            return {}
    
    def get_setting(self, category: str, key: str, user=None, default: Any = None) -> Any:
        """Get a specific setting value with type conversion."""
        try:
            # Check permissions for sensitive settings
            if category in ["security", "admin"] and not check_permission("settings", "admin"):
                print(f"[SETTINGS_SERVICE] Permission denied for admin setting: {category}.{key}")
                return default
            elif not check_permission("settings", "view"):
                print("[SETTINGS_SERVICE] Permission denied for settings:view")
                return default
            
            # Validate input
            if not category or not key:
                return default
            
            setting = self.settings_repository.get_setting(category, key)
            if not setting:
                return default
            
            # Convert value based on data type
            value = setting['value']
            data_type = setting.get('data_type', 'string')
            
            return self._convert_value(value, data_type, default)
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Get setting error: {e}")
            return default
    
    def set_setting(self, category: str, key: str, value: Any, user=None,
                   description: str = None, data_type: str = None) -> bool:
        """Set a setting value with validation."""
        try:
            # Check permissions
            if category in ["security", "admin"] and not check_permission("settings", "admin"):
                print(f"[SETTINGS_SERVICE] Permission denied for admin setting: {category}.{key}")
                return False
            elif not check_permission("settings", "update"):
                print("[SETTINGS_SERVICE] Permission denied for settings:update")
                return False
            
            # Validate input
            if not category or not key:
                print(f"[SETTINGS_SERVICE] Invalid category or key: {category}.{key}")
                return False
            
            # Auto-detect data type if not provided
            if data_type is None:
                data_type = self._detect_data_type(value)
            
            # Convert value to string for storage
            str_value = self._convert_to_string(value, data_type)
            if str_value is None:
                print(f"[SETTINGS_SERVICE] Invalid value for type {data_type}: {value}")
                return False
            
            # Set the setting
            success = self.settings_repository.set_setting(
                category, key, str_value, description, data_type
            )
            
            if success:
                print(f"[SETTINGS_SERVICE] Set setting {category}.{key} = {value}")
            else:
                print(f"[SETTINGS_SERVICE] Failed to set setting {category}.{key}")
            
            return success
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Set setting error: {e}")
            return False
    
    def delete_setting(self, category: str, key: str) -> bool:
        """Delete a setting with validation."""
        try:
            # Check permissions
            if category in ["security", "admin"] and not check_permission("settings", "admin"):
                print(f"[SETTINGS_SERVICE] Permission denied for admin setting: {category}.{key}")
                return False
            elif not check_permission("settings", "delete"):
                print("[SETTINGS_SERVICE] Permission denied for settings:delete")
                return False
            
            # Validate input
            if not category or not key:
                print(f"[SETTINGS_SERVICE] Invalid category or key: {category}.{key}")
                return False
            
            # Check if setting exists
            existing = self.settings_repository.get_setting(category, key)
            if not existing:
                print(f"[SETTINGS_SERVICE] Setting not found: {category}.{key}")
                return False
            
            # Delete setting
            success = self.settings_repository.delete_setting(category, key)
            if success:
                print(f"[SETTINGS_SERVICE] Deleted setting {category}.{key}")
            else:
                print(f"[SETTINGS_SERVICE] Failed to delete setting {category}.{key}")
            
            return success
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Delete setting error: {e}")
            return False
    
    def get_categories(self) -> List[str]:
        """Get all setting categories."""
        try:
            # Check permissions
            if not check_permission("settings", "view"):
                print("[SETTINGS_SERVICE] Permission denied for settings:view")
                return []
            
            categories = self.settings_repository.get_categories()
            print(f"[SETTINGS_SERVICE] Retrieved {len(categories)} categories")
            return categories
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Get categories error: {e}")
            return []
    
    def get_settings_statistics(self) -> Dict:
        """Get settings statistics."""
        try:
            # Check permissions
            if not check_permission("settings", "view"):
                print("[SETTINGS_SERVICE] Permission denied for settings:view")
                return {}
            
            total_count = self.settings_repository.get_settings_count()
            categories = self.settings_repository.get_categories()
            
            stats = {
                "total_settings": total_count,
                "categories": len(categories),
                "category_list": categories
            }
            
            # Add per-category counts
            category_counts = {}
            for category in categories:
                settings = self.settings_repository.get_settings_by_category(category)
                category_counts[category] = len(settings)
            
            stats["category_counts"] = category_counts
            
            print(f"[SETTINGS_SERVICE] Generated settings statistics: {total_count} settings")
            return stats
            
        except Exception as e:
            print(f"[SETTINGS_SERVICE] Get settings statistics error: {e}")
            return {}
    
    def _convert_value(self, str_value: str, data_type: str, default: Any) -> Any:
        """Convert string value to appropriate Python type."""
        try:
            if data_type == "integer":
                return int(str_value)
            elif data_type == "float":
                return float(str_value)
            elif data_type == "boolean":
                return str_value.lower() in ("true", "1", "yes", "on")
            elif data_type == "json":
                return json.loads(str_value)
            else:  # string or unknown
                return str_value
        except (ValueError, json.JSONDecodeError) as e:
            print(f"[SETTINGS_SERVICE] Value conversion error: {e}")
            return default
    
    def _convert_to_string(self, value: Any, data_type: str) -> Optional[str]:
        """Convert Python value to string for storage."""
        try:
            if data_type == "json":
                return json.dumps(value)
            elif data_type == "boolean":
                return "true" if value else "false"
            else:
                return str(value)
        except Exception as e:
            print(f"[SETTINGS_SERVICE] String conversion error: {e}")
            return None
    
    def _detect_data_type(self, value: Any) -> str:
        """Auto-detect data type from value."""
        if isinstance(value, bool):
            return "boolean"
        elif isinstance(value, int):
            return "integer"
        elif isinstance(value, float):
            return "float"
        elif isinstance(value, (dict, list)):
            return "json"
        else:
            return "string"
