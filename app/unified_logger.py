"""
App-level shim to expose unified_logger for modules that do:
    from unified_logger import ...
It forwards to utilities.unified_logger
"""
from utilities.unified_logger import (
    unified_logger,
    setup_global_exception_handler,
    migrate_old_log_files,
)

__all__ = [
    'unified_logger',
    'setup_global_exception_handler',
    'migrate_old_log_files',
]
