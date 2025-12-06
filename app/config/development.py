"""Development Environment Configuration"""
import os
from .settings import DatabaseConfig, ServerConfig, SecurityConfig, UIConfig, BackupConfig, LoggingConfig, BusinessRules

# Import tax system for dynamic rates
try:
    from ..stfoom.logic.taxes import get_current_tva_rate
except ImportError:
    # Fallback if tax system not available
    def get_current_tva_rate(): return 0.19

def get_development_config():
    """Get development configuration."""
    # Use the ROOT data directory (not app/data) - THIS WAS THE ISSUE!
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))  # Go up to STFOOM root
    data_dir = os.path.join(base_dir, "data")  # Use root/data not app/data
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    return {
        "database": DatabaseConfig(
            path=os.path.join(data_dir, "stfoom.db"),
            connection_pool_size=5,  # Smaller pool for dev
            timeout=10
        ),
        "server": ServerConfig(
            server_path=r"\\DESKTOP-BKIB183\data",  # Current working server
            sync_interval=60,  # Longer interval for dev
            max_retries=2,
            auto_sync=True,
            allowed_servers=["DESKTOP-BKIB183", "localhost", "127.0.0.1"]
        ),
        "security": SecurityConfig(
            bcrypt_rounds=10,  # Faster for dev
            session_timeout=7200,  # Longer sessions for dev
            max_failed_attempts=10,  # More lenient for dev
            lockout_duration=300
        ),
        "ui": UIConfig(
            theme="Sombre",
            language="English",
            auto_save=True,
            auto_save_interval=5
        ),
        "backup": BackupConfig(
            auto_backup=True,
            backup_retention=30,
            backup_interval=24
        ),
        "logging": LoggingConfig(
            debug_mode=True,  # Enable debug in development
            log_level="DEBUG"
        ),
        "business": BusinessRules(
            # Development uses dynamic rates from tax settings
            default_tva_rate=get_current_tva_rate(),  # Dynamic TVA rate from settings
            reduced_tva_rate=0.07,  # Reduced 7%
            zero_tva_rate=0.00,     # Exempt 0%
            default_payment_days=30,
            early_payment_discount_rate=0.02,  # 2%
            early_payment_threshold_days=10,
            late_payment_penalty_rate=0.05,    # 5%
            max_discount_percentage=25.0,       # 25%
            max_invoice_items=100,
            low_stock_threshold=10,
            currency_precision=3,               # Updated to 3 decimals for TD format
            rounding_method="round",
            currency_symbol="TD"                # Updated to TD currency symbol
        )
    }
