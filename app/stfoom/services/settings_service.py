import json
import logging
from typing import Dict, Any, List, Optional
from app.stfoom.data.settings_repository import SettingsRepository

class SettingsService:
    """Service layer for application settings management"""
    
    def __init__(self, settings_repository: Optional[SettingsRepository] = None):
        self.settings_repository = settings_repository or SettingsRepository()
        self._initialize_default_settings()
        
    def _initialize_default_settings(self):
        """Initialize default application settings if they don't exist"""
        defaults = [
            {
                'category': 'payments',
                'key': 'tolerance_amount',
                'value': '40.0',
                'description': 'Tolérance pour les paiements partiels (en DT)',
                'data_type': 'float'
            },
            {
                'category': 'payments',
                'key': 'include_retenu_in_calculation',
                'value': 'true',
                'description': 'Inclure le retenu dans le calcul du statut de paiement',
                'data_type': 'boolean'
            },
            {
                'category': 'payments',
                'key': 'retenu_minimum_threshold',
                'value': '1000.0',
                'description': 'Montant minimum pour lequel le retenu est obligatoire (en DT)',
                'data_type': 'float'
            }
        ]
        
        for default in defaults:
            existing = self.settings_repository.get_setting(default['category'], default['key'])
            if not existing:
                self.settings_repository.set_setting(
                    default['category'],
                    default['key'], 
                    default['value'],
                    default['description'],
                    default['data_type']
                )
        
    def get_setting(self, category: str, key: str, user_info: Dict[str, Any] = None) -> Any:
        """Get a specific setting value with type conversion"""
        setting = self.settings_repository.get_setting(category, key)
        if not setting:
            return None
            
        value = setting['value']
        data_type = setting.get('data_type', 'string')
        
        # Convert value based on data type
        if data_type == 'float':
            try:
                return float(value)
            except ValueError:
                return 0.0
        elif data_type == 'int':
            try:
                return int(value)
            except ValueError:
                return 0
        elif data_type == 'boolean':
            return str(value).lower() in ('true', '1', 'yes', 'on')
        else:
            return str(value)
        
    def set_setting(self, category: str, key: str, value: Any, 
                   description: str = None, user_info: Dict[str, Any] = None) -> bool:
        """Set a setting value"""
        # Convert value to string for storage
        if isinstance(value, bool):
            str_value = 'true' if value else 'false'
            data_type = 'boolean'
        elif isinstance(value, (int, float)):
            str_value = str(value)
            data_type = 'float' if isinstance(value, float) else 'int'
        else:
            str_value = str(value)
            data_type = 'string'
            
        return self.settings_repository.set_setting(category, key, str_value, description, data_type)
        
    def get_settings_by_category(self, category: str, user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get all settings for a category as a dictionary"""
        settings = self.settings_repository.get_settings_by_category(category)
        result = {}
        
        for setting in settings:
            key = setting['key']
            value = setting['value']
            data_type = setting.get('data_type', 'string')
            
            # Convert value based on data type
            if data_type == 'float':
                try:
                    result[key] = float(value)
                except ValueError:
                    result[key] = 0.0
            elif data_type == 'int':
                try:
                    result[key] = int(value)
                except ValueError:
                    result[key] = 0
            elif data_type == 'boolean':
                result[key] = str(value).lower() in ('true', '1', 'yes', 'on')
            else:
                result[key] = str(value)
        
        return result
        
    def delete_setting(self, category: str, key: str, user_info: Dict[str, Any] = None) -> bool:
        """Delete a setting"""
        return self.settings_repository.delete_setting(category, key)
        
    def get_all_categories(self, user_info: Dict[str, Any] = None) -> List[str]:
        """Get all setting categories"""
        return self.settings_repository.get_categories()
        
    def get_settings_statistics(self, user_info: Dict[str, Any] = None) -> Dict[str, Any]:
        """Get settings statistics"""
        return {
            'total_settings': self.settings_repository.get_settings_count(),
            'categories': len(self.get_all_categories()),
        }

    # Convenience methods for payment settings
    def get_payment_tolerance(self) -> float:
        """Get the payment tolerance amount in DT"""
        # First check config/settings.json file
        try:
            import os
            import json
            settings_file = os.path.join("config", "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    config_settings = json.load(f)
                    if 'payment_tolerance' in config_settings:
                        return float(config_settings['payment_tolerance'])
        except Exception as e:
            logging.warning(f"Could not read payment tolerance from config file: {e}")
        
        # Fallback to database setting
        return self.get_setting('payments', 'tolerance_amount') or 40.0
    
    def set_payment_tolerance(self, amount: float) -> bool:
        """Set the payment tolerance amount in DT"""
        return self.set_setting('payments', 'tolerance_amount', amount, 
                              'Tolérance pour les paiements partiels (en DT)')
    
    def should_include_retenu_in_payment_calculation(self) -> bool:
        """Check if retenu should be included in payment status calculation"""
        return self.get_setting('payments', 'include_retenu_in_calculation') or True
    
    def get_retenu_minimum_threshold(self) -> float:
        """Get the minimum invoice amount requiring retenu (in DT)"""
        # First check config/settings.json file
        try:
            import os
            import json
            settings_file = os.path.join("config", "settings.json")
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    config_settings = json.load(f)
                    if 'retenu_minimum_threshold' in config_settings:
                        return float(config_settings['retenu_minimum_threshold'])
        except Exception as e:
            logging.warning(f"Could not read retenu minimum threshold from config file: {e}")
        
        # Fallback to database setting
        return self.get_setting('payments', 'retenu_minimum_threshold') or 1000.0
    
    def set_retenu_minimum_threshold(self, amount: float) -> bool:
        """Set the minimum invoice amount requiring retenu (in DT)"""
        return self.set_setting('payments', 'retenu_minimum_threshold', amount,
                              'Montant minimum pour lequel le retenu est obligatoire (en DT)')
