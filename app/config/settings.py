"""
Central Configuration Management
===============================
Unified configuration system for STFOOM application.
Replaces scattered settings with centralized management.
"""
import os
import json
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from pathlib import Path

# ✅ SECURITY COMPLIANCE: Centralized path management functions
def get_db_path():
    """Get the database file path using centralized configuration."""
    app_root = Path(__file__).parent.parent.parent
    return str(app_root / "data" / "stfoom.db")

def get_data_dir():
    """Get the data directory path using centralized configuration."""
    app_root = Path(__file__).parent.parent.parent
    return str(app_root / "data")

def get_backup_dir():
    """Get the backup directory path."""
    app_root = Path(__file__).parent.parent.parent
    return str(app_root / "app" / "backups")

def get_output_dir():
    """Get the output directory path."""
    app_root = Path(__file__).parent.parent.parent
    return str(app_root / "app" / "output")

@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str
    connection_pool_size: int = 8
    timeout: int = 30
    
@dataclass  
class ServerConfig:
    """Server and sync configuration."""
    server_path: str
    sync_interval: int = 30
    max_retries: int = 3
    auto_sync: bool = True
    allowed_servers: List[str] = None
    
@dataclass
class SecurityConfig:
    """Security configuration."""
    bcrypt_rounds: int = 12
    session_timeout: int = 3600
    max_failed_attempts: int = 5
    lockout_duration: int = 900

@dataclass
class UIConfig:
    """UI and theme configuration."""
    theme: str = "Sombre"
    language: str = "English"
    auto_save: bool = True
    auto_save_interval: int = 5

@dataclass
class BackupConfig:
    """Backup configuration."""
    auto_backup: bool = True
    backup_retention: int = 30
    backup_interval: int = 24  # hours

@dataclass
class LoggingConfig:
    """Logging configuration."""
    debug_mode: bool = False
    log_level: str = "INFO"

@dataclass
class BusinessRules:
    """Business rules and calculations - REPLACES HARDCODED VALUES."""
    # Tax Configuration - NO MORE HARDCODED 19%!
    default_tva_rate: float = 0.19  # 19%
    reduced_tva_rate: float = 0.07  # 7% for reduced items
    zero_tva_rate: float = 0.00     # 0% for exempt items
    
    # Payment Terms - NO MORE HARDCODED DAYS!
    default_payment_days: int = 30
    early_payment_discount_rate: float = 0.02  # 2%
    early_payment_threshold_days: int = 10
    late_payment_penalty_rate: float = 0.05    # 5%
    
    # Limits and Thresholds - CONFIGURABLE LIMITS!
    max_discount_percentage: float = 25.0       # Maximum 25% discount
    max_invoice_items: int = 100                # Maximum items per invoice
    low_stock_threshold: int = 10               # Alert when stock < 10
    
    # Calculation Settings
    currency_precision: int = 3                 # Decimal places (updated to 3 for TD format)
    rounding_method: str = "round"              # round, ceil, floor
    currency_symbol: str = "TD"                 # Currency symbol (updated to TD)

class Settings:
    """Unified settings class that manages all application configuration."""
    
    def __init__(self, environment: str = "development"):
        self.environment = environment
        self.settings_file = os.path.join(os.path.dirname(__file__), "settings.json")  # Look in config directory
        self._load_settings()
    
    def _load_settings(self):
        """Load settings from environment config and user preferences."""
        # Load environment-specific defaults
        if self.environment == "production":
            from .production import get_production_config
            env_config = get_production_config()
        else:
            from .development import get_development_config
            env_config = get_development_config()
        
        # Load user preferences from settings.json (if exists)
        user_prefs = self._load_user_preferences()
        
        # Merge environment config with user preferences
        self.database = env_config["database"]
        self.server = self._merge_server_config(env_config["server"], user_prefs)
        self.security = env_config["security"]
        self.ui = self._merge_ui_config(env_config.get("ui", UIConfig()), user_prefs)
        self.backup = self._merge_backup_config(env_config.get("backup", BackupConfig()), user_prefs)
        self.logging = self._merge_logging_config(env_config.get("logging", LoggingConfig()), user_prefs)
        self.business = self._merge_business_config(env_config.get("business", BusinessRules()), user_prefs)
    
    def _load_user_preferences(self) -> Dict[str, Any]:
        """Load user preferences from settings.json."""
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"[CONFIG] Error loading user preferences: {e}")
        return {}
    
    def _merge_server_config(self, env_config: ServerConfig, user_prefs: Dict) -> ServerConfig:
        """Merge server config with user preferences."""
        return ServerConfig(
            server_path=env_config.server_path,
            sync_interval=user_prefs.get("sync_interval", env_config.sync_interval),
            max_retries=env_config.max_retries,
            auto_sync=user_prefs.get("auto_sync", env_config.auto_sync),
            allowed_servers=env_config.allowed_servers
        )
    
    def _merge_ui_config(self, env_config: UIConfig, user_prefs: Dict) -> UIConfig:
        """Merge UI config with user preferences."""
        return UIConfig(
            theme=user_prefs.get("theme", env_config.theme),
            language=user_prefs.get("language", env_config.language),
            auto_save=user_prefs.get("auto_save", env_config.auto_save),
            auto_save_interval=user_prefs.get("auto_save_interval", env_config.auto_save_interval)
        )
    
    def _merge_backup_config(self, env_config: BackupConfig, user_prefs: Dict) -> BackupConfig:
        """Merge backup config with user preferences."""
        return BackupConfig(
            auto_backup=user_prefs.get("auto_backup", env_config.auto_backup),
            backup_retention=user_prefs.get("backup_retention", env_config.backup_retention),
            backup_interval=env_config.backup_interval
        )
    
    def _merge_logging_config(self, env_config: LoggingConfig, user_prefs: Dict) -> LoggingConfig:
        """Merge logging config with user preferences."""
        return LoggingConfig(
            debug_mode=user_prefs.get("debug_mode", env_config.debug_mode),
            log_level=user_prefs.get("log_level", env_config.log_level)
        )
    
    def _merge_business_config(self, env_config: BusinessRules, user_prefs: Dict) -> BusinessRules:
        """Merge business rules with user preferences."""
        return BusinessRules(
            default_tva_rate=user_prefs.get("default_tva_rate", env_config.default_tva_rate),
            reduced_tva_rate=user_prefs.get("reduced_tva_rate", env_config.reduced_tva_rate),
            zero_tva_rate=user_prefs.get("zero_tva_rate", env_config.zero_tva_rate),
            default_payment_days=user_prefs.get("default_payment_days", env_config.default_payment_days),
            early_payment_discount_rate=user_prefs.get("early_payment_discount_rate", env_config.early_payment_discount_rate),
            early_payment_threshold_days=user_prefs.get("early_payment_threshold_days", env_config.early_payment_threshold_days),
            late_payment_penalty_rate=user_prefs.get("late_payment_penalty_rate", env_config.late_payment_penalty_rate),
            max_discount_percentage=user_prefs.get("max_discount_percentage", env_config.max_discount_percentage),
            max_invoice_items=user_prefs.get("max_invoice_items", env_config.max_invoice_items),
            low_stock_threshold=user_prefs.get("low_stock_threshold", env_config.low_stock_threshold),
            currency_precision=user_prefs.get("currency_precision", env_config.currency_precision),
            rounding_method=user_prefs.get("rounding_method", env_config.rounding_method),
            currency_symbol=user_prefs.get("currency_symbol", env_config.currency_symbol)
        )
    
    def save_user_preferences(self):
        """Save current settings back to settings.json."""
        try:
            user_settings = {
                "language": self.ui.language,
                "theme": self.ui.theme,
                "auto_save": self.ui.auto_save,
                "auto_save_interval": self.ui.auto_save_interval,
                "auto_sync": self.server.auto_sync,
                "sync_interval": self.server.sync_interval,
                "auto_backup": self.backup.auto_backup,
                "backup_retention": self.backup.backup_retention,
                "debug_mode": self.logging.debug_mode,
                "log_level": self.logging.log_level
            }
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(user_settings, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[CONFIG] Error saving user preferences: {e}")
            return False
    
    def update_setting(self, category: str, key: str, value: Any) -> bool:
        """Update a specific setting and save to file."""
        try:
            if category == "ui":
                setattr(self.ui, key, value)
            elif category == "server":
                setattr(self.server, key, value)
            elif category == "backup":
                setattr(self.backup, key, value)
            elif category == "logging":
                setattr(self.logging, key, value)
            else:
                return False
            
            return self.save_user_preferences()
        except Exception as e:
            print(f"[CONFIG] Error updating setting {category}.{key}: {e}")
            return False
    
    def get_db_path(self) -> str:
        """Get the database path - backward compatibility."""
        return self.database.path
    
    def get_server_path(self) -> str:
        """Get the server path - backward compatibility."""
        return self.server.server_path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert all settings to dictionary for UI display."""
        return {
            "database": asdict(self.database),
            "server": asdict(self.server),
            "security": asdict(self.security),
            "ui": asdict(self.ui),
            "backup": asdict(self.backup),
            "logging": asdict(self.logging)
        }

    def get_environment(self) -> str:
        """Get current environment."""
        return self.environment
    
    def get_database_path(self) -> str:
        """Get database path."""
        return self.database.path
    
    def get_user_settings(self) -> Dict[str, Any]:
        """Get user settings dictionary."""
        return self._load_user_preferences()
    
    # ═══════════════════════════════════════════════════════════════════════
    # BUSINESS CALCULATION METHODS - REPLACES ALL HARDCODED VALUES!
    # ═══════════════════════════════════════════════════════════════════════
    
    def get_tva_rate(self, item_type: str = "standard") -> float:
        """Get TVA rate based on item type - NO MORE HARDCODED 19%!"""
        if item_type == "reduced":
            return self.business.reduced_tva_rate
        elif item_type == "exempt":
            return self.business.zero_tva_rate
        return self.business.default_tva_rate
    
    def calculate_tva(self, amount: float, item_type: str = "standard") -> float:
        """Calculate TVA amount using configurable rates."""
        rate = self.get_tva_rate(item_type)
        tva = amount * rate
        return round(tva, self.business.currency_precision)
    
    def calculate_total_with_tva(self, amount: float, item_type: str = "standard") -> float:
        """Calculate total amount including TVA."""
        tva = self.calculate_tva(amount, item_type)
        total = amount + tva
        return round(total, self.business.currency_precision)
    
    def is_early_payment_eligible(self, days_since_invoice: int) -> bool:
        """Check if payment qualifies for early discount - NO MORE HARDCODED 10 DAYS!"""
        return days_since_invoice <= self.business.early_payment_threshold_days
    
    def calculate_early_payment_discount(self, amount: float) -> float:
        """Calculate early payment discount - NO MORE HARDCODED 2%!"""
        discount = amount * self.business.early_payment_discount_rate
        return round(discount, self.business.currency_precision)
    
    def calculate_late_payment_penalty(self, amount: float, days_overdue: int) -> float:
        """Calculate late payment penalty - NO MORE HARDCODED 5%!"""
        if days_overdue <= 0:
            return 0.0
        penalty = amount * self.business.late_payment_penalty_rate
        return round(penalty, self.business.currency_precision)
    
    def validate_discount(self, discount_percentage: float) -> bool:
        """Validate if discount is within allowed limits - NO MORE HARDCODED 25%!"""
        return 0 <= discount_percentage <= self.business.max_discount_percentage
    
    def format_currency(self, amount: float) -> str:
        """Format amount as currency with proper precision."""
        formatted = f"{amount:.{self.business.currency_precision}f}"
        return f"{formatted} {self.business.currency_symbol}"

# ═══════════════════════════════════════════════════════════════════════
# PARKING LOT DISPENSER - EFFICIENT SYNC CHANGE TRACKING
# ═══════════════════════════════════════════════════════════════════════

def get_last_change_timestamp() -> float:
    """Get the last time any local database change was made (parking lot dispenser timestamp)."""
    try:
        data_dir = get_data_dir()
        timestamp_file = os.path.join(data_dir, 'last_change_timestamp.txt')
        if os.path.exists(timestamp_file):
            with open(timestamp_file, 'r') as f:
                return float(f.read().strip())
        return 0.0
    except Exception:
        return 0.0


def update_last_change_timestamp():
    """Update the last change timestamp to current time."""
    try:
        import time
        data_dir = get_data_dir()
        timestamp_file = os.path.join(data_dir, 'last_change_timestamp.txt')
        with open(timestamp_file, 'w') as f:
            f.write(str(time.time()))
    except Exception:
        pass  # Fail silently - timestamp tracking is not critical

# Global settings instance
settings = Settings(os.getenv("STFOOM_ENV", "development"))

# Quick access to business rules for backward compatibility
business_rules = settings.business
