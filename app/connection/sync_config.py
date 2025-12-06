"""
connection.sync_config
=====================
Configuration for the smart sync system.
"""

import os
import json
import sys
from pathlib import Path
from typing import Dict, Any

# Default configuration
DEFAULT_CONFIG = {
    "server_path": r"\\DESKTOP-BKIB183\data",
    "sync_interval": 30,  # seconds
    "conflict_resolution": "server_wins",  # server_wins, client_wins, manual
    "max_retries": 3,
    "auto_sync": True,
    "sync_on_startup": True,
    "sync_on_shutdown": True,
    "log_sync_operations": True,
    "backup_before_sync": True
}

def _resolve_config_file() -> str:
    """Resolve a persistent config file location.
    In frozen mode, use %LOCALAPPDATA%/STFOOM/config/sync_config.json.
    In dev, keep it next to this module.
    """
    frozen = getattr(sys, 'frozen', False)
    if frozen:
        base = Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'STFOOM' / 'config'
        base.mkdir(parents=True, exist_ok=True)
        return str(base / 'sync_config.json')
    return os.path.join(os.path.dirname(__file__), 'sync_config.json')

try:
    CONFIG_FILE = _resolve_config_file()
    print(f"[SYNC] Using config file: {CONFIG_FILE}")
except Exception as e:
    print(f"[SYNC] ERROR resolving config file: {e}")
    # Fallback to a safe default
    CONFIG_FILE = str(Path(os.environ.get('LOCALAPPDATA', Path.home())) / 'STFOOM' / 'config' / 'sync_config.json')

def load_config() -> Dict[str, Any]:
    """Load sync configuration from file."""
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Merge with defaults to ensure all keys exist
                merged_config = DEFAULT_CONFIG.copy()
                merged_config.update(config)
                return merged_config
        else:
            # Create default config file
            save_config(DEFAULT_CONFIG)
            return DEFAULT_CONFIG
    except Exception as e:
        print(f"[SYNC] Error loading config: {e}")
        return DEFAULT_CONFIG

def save_config(config: Dict[str, Any]):
    """Save sync configuration to file."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[SYNC] Error saving config: {e}")

def get_server_path() -> str:
    """Get configured server path with security validation."""
    config = load_config()
    raw_path = config.get("server_path", DEFAULT_CONFIG["server_path"])
    
    # Validate the path for security
    try:
        from stfoom.logic.network_path_security import SecurePathManager
        
        path_manager = SecurePathManager()
        is_valid, normalized_path, errors = path_manager.validate_and_normalize_path(raw_path)
        
        if is_valid:
            return normalized_path
        else:
            print(f"[SYNC] Warning: Configured server path is invalid: {'; '.join(errors)}")
            print(f"[SYNC] Using default path: {DEFAULT_CONFIG['server_path']}")
            return DEFAULT_CONFIG["server_path"]
            
    except ImportError:
        # Basic validation fallback
        if ".." in raw_path or not raw_path.strip():
            print(f"[SYNC] Warning: Server path contains dangerous patterns, using default")
            return DEFAULT_CONFIG["server_path"]
        return raw_path
    except Exception as e:
        print(f"[SYNC] Error validating server path: {e}")
        return DEFAULT_CONFIG["server_path"]

def get_sync_interval() -> int:
    """Get configured sync interval."""
    config = load_config()
    return config.get("sync_interval", DEFAULT_CONFIG["sync_interval"])

def get_conflict_resolution() -> str:
    """Get configured conflict resolution strategy."""
    config = load_config()
    return config.get("conflict_resolution", DEFAULT_CONFIG["conflict_resolution"])

def set_server_path(new_path: str):
    """Set server path in configuration (alias for update_server_path)."""
    update_server_path(new_path)

def set_sync_interval(new_interval: int):
    """Set sync interval in configuration (alias for update_sync_interval)."""
    update_sync_interval(new_interval)

def update_server_path(new_path: str):
    """Update server path in configuration with security validation."""
    # Import security module
    try:
        from stfoom.logic.network_path_security import SecurePathManager, NetworkPathError
        
        # Validate the new path
        path_manager = SecurePathManager()
        is_valid, normalized_path, errors = path_manager.validate_and_normalize_path(new_path)
        
        if not is_valid:
            error_msg = f"Invalid server path: {'; '.join(errors)}"
            print(f"[SYNC] {error_msg}")
            raise NetworkPathError(error_msg)
        
        # Update configuration with validated path
        config = load_config()
        config["server_path"] = normalized_path
        save_config(config)
        print(f"[SYNC] Server path securely updated to: {normalized_path}")
        
        if errors:
            print(f"[SYNC] Validation warnings: {'; '.join(errors)}")
            
    except ImportError:
        # Fallback to basic validation if security module not available
        if not new_path or ".." in new_path:
            raise ValueError("Invalid server path: contains dangerous patterns")
        
        config = load_config()
        config["server_path"] = new_path
        save_config(config)
        print(f"[SYNC] Server path updated to: {new_path} (basic validation)")
    except Exception as e:
        print(f"[SYNC] Failed to update server path: {e}")
        raise

def update_sync_interval(new_interval: int):
    """Update sync interval in configuration."""
    config = load_config()
    config["sync_interval"] = new_interval
    save_config(config)
    print(f"[SYNC] Sync interval updated to: {new_interval} seconds")

def update_conflict_resolution(new_strategy: str):
    """Update conflict resolution strategy."""
    if new_strategy not in ["server_wins", "client_wins", "manual"]:
        print(f"[SYNC] Invalid conflict resolution strategy: {new_strategy}")
        return
    
    config = load_config()
    config["conflict_resolution"] = new_strategy
    save_config(config)
    print(f"[SYNC] Conflict resolution updated to: {new_strategy}")

def get_config_summary() -> str:
    """Get a summary of current configuration."""
    config = load_config()
    return f"""
Sync Configuration:
- Server Path: {config['server_path']}
- Sync Interval: {config['sync_interval']} seconds
- Conflict Resolution: {config['conflict_resolution']}
- Auto Sync: {config['auto_sync']}
- Sync on Startup: {config['sync_on_startup']}
- Sync on Shutdown: {config['sync_on_shutdown']}
- Log Operations: {config['log_sync_operations']}
- Backup Before Sync: {config['backup_before_sync']}
"""

# Config file will be initialized on first load_config() call 