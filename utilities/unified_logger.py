"""
Lightweight unified logger shim
Provides minimal logging APIs used across the app to avoid import errors.
Writes to config/error.log and prints to console.
"""
from __future__ import annotations
import os
import sys
import traceback
from datetime import datetime


class _UnifiedLogger:
    def _ensure_dir(self):
        try:
            os.makedirs('config', exist_ok=True)
        except Exception:
            pass

    def _write(self, level: str, component: str, message: str):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] [{level}] [{component}] {message}\n"
        print(line.strip())
        try:
            self._ensure_dir()
            with open(os.path.join('config', 'error.log'), 'a', encoding='utf-8') as f:
                f.write(line)
        except Exception:
            pass

    def log_info(self, component: str, message: str):
        self._write('INFO', component, message)

    def log_error(self, component: str, message: str):
        self._write('ERROR', component, message)

    def log_exception(self, component: str, message: str, exc: BaseException, extra: dict | None = None):
        self._write('EXCEPTION', component, f"{message}: {exc}")
        try:
            self._ensure_dir()
            with open(os.path.join('config', 'error.log'), 'a', encoding='utf-8') as f:
                traceback.print_exception(type(exc), exc, exc.__traceback__, file=f)
                if extra:
                    f.write(f"Extra: {extra}\n")
        except Exception:
            pass


unified_logger = _UnifiedLogger()


def setup_global_exception_handler():
    def _hook(exc_type, exc_value, exc_traceback):
        try:
            unified_logger.log_exception('GLOBAL', 'Unhandled exception', exc_value, {
                'exc_type': getattr(exc_type, '__name__', str(exc_type)),
                'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        except Exception:
            pass
    try:
        sys.excepthook = _hook
    except Exception:
        pass


def migrate_old_log_files():
    # No-op shim for compatibility
    try:
        os.makedirs('config', exist_ok=True)
    except Exception:
        pass
