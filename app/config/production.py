"""Production Environment Configuration"""
import os
from .settings import DatabaseConfig, ServerConfig, SecurityConfig, UIConfig, BackupConfig, LoggingConfig

def get_production_config():
    """Get production configuration."""
    # Production paths from environment variables with secure defaults
    base_dir = os.getenv("STFOOM_BASE_DIR", os.path.dirname(os.path.dirname(__file__)))
    data_dir = os.getenv("STFOOM_DATA_DIR", os.path.join(base_dir, "data"))
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    return {
        "database": DatabaseConfig(
            path=os.path.join(data_dir, "stfoom.db"),
            connection_pool_size=8,
            timeout=30
        ),
        "server": ServerConfig(
            server_path=os.getenv("STFOOM_SERVER_PATH", r"\\DESKTOP-BKIB183\data"),
            sync_interval=30,
            max_retries=3,
            auto_sync=True,
            allowed_servers=os.getenv("STFOOM_ALLOWED_SERVERS", "DESKTOP-BKIB183,STFOOM-SERVER,BACKUP-SERVER").split(",")
        ),
        "security": SecurityConfig(
            bcrypt_rounds=12,
            session_timeout=3600,
            max_failed_attempts=5,
            lockout_duration=900
        ),
        "ui": UIConfig(
            theme=os.getenv("STFOOM_THEME", "Sombre"),
            language=os.getenv("STFOOM_LANGUAGE", "English"),
            auto_save=os.getenv("STFOOM_AUTO_SAVE", "true").lower() == "true",
            auto_save_interval=int(os.getenv("STFOOM_AUTO_SAVE_INTERVAL", "5"))
        ),
        "backup": BackupConfig(
            auto_backup=os.getenv("STFOOM_AUTO_BACKUP", "true").lower() == "true",
            backup_retention=int(os.getenv("STFOOM_BACKUP_RETENTION", "30")),
            backup_interval=int(os.getenv("STFOOM_BACKUP_INTERVAL", "24"))
        ),
        "logging": LoggingConfig(
            debug_mode=os.getenv("STFOOM_DEBUG", "false").lower() == "true",
            log_level=os.getenv("STFOOM_LOG_LEVEL", "INFO")
        )
    }
