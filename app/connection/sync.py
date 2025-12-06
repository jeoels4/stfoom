"""Compatibility shim module for legacy imports of `connection.sync`.

The project now uses a modern row-level sync service located at:

    app/stfoom/services/sync_service.py

This module provides a small, safe compatibility layer so legacy import
sites that expect functions like `sync_to_server()` continue to work while
delegating to the new SyncService implementation.

The previous file-copy based implementation has been removed intentionally to
avoid accidental copying of database files and backup archives.
"""
from typing import Any, Dict

try:
    from app.stfoom.services.sync_service import SyncService
except Exception:
    # Support alternate import paths used in some scripts
    from stfoom.services.sync_service import SyncService  # type: ignore


__all__ = [
    'sync_to_server', 'sync_from_server', 'server_online',
    'get_pending_changes_count', 'get_sync_status', 'get_estimated_transfer_bytes',
    'start_server_watcher', 'stop_server_watcher', 'force_sync'
]


_svc: SyncService | None = None


def _get_service() -> SyncService:
    global _svc
    if _svc is None:
        _svc = SyncService()
    return _svc


def sync_to_server() -> Dict[str, Any]:
    """Proxy to SyncService.sync_to_server(). Returns a simple dict result."""
    svc = _get_service()
    try:
        res = svc.sync_to_server()
        return {'success': res.success, 'message': res.message, 'errors': getattr(res, 'errors', [])}
    except Exception as e:
        return {'success': False, 'message': str(e), 'errors': []}


def sync_from_server() -> Dict[str, Any]:
    svc = _get_service()
    try:
        res = svc.sync_from_server()
        return {'success': res.success, 'message': res.message, 'errors': getattr(res, 'errors', [])}
    except Exception as e:
        return {'success': False, 'message': str(e), 'errors': []}


def server_online() -> bool:
    try:
        return _get_service().server_online()
    except Exception:
        return False


def get_pending_changes_count() -> int:
    try:
        return _get_service().get_sync_queue_status().get('total_pending', 0)
    except Exception:
        return 0


def get_sync_status() -> Dict[str, Any]:
    try:
        return _get_service().get_sync_status()
    except Exception as e:
        return {'error': str(e)}


def get_estimated_transfer_bytes() -> int:
    """Legacy estimator is not applicable to row-level sync; return 0."""
    return 0


def start_server_watcher(*args, **kwargs):
    """No-op compatibility stub (legacy watcher removed)."""
    return None


def stop_server_watcher(*args, **kwargs):
    return None


def _unwrap_result(res) -> bool:
    """Helper: accept either SyncResult-like object or legacy dict and return boolean success."""
    try:
        if res is None:
            return False
        if isinstance(res, dict):
            return bool(res.get('success', False))
        # object with attribute
        return bool(getattr(res, 'success', False))
    except Exception:
        return False


def force_sync() -> bool:
    """Compatibility convenience: perform a push then a pull using SyncService.

    Returns True if both operations report success (best-effort). This keeps
    legacy callers that expect sync.force_sync() working while delegating to
    the row-level SyncService.
    """
    print("[SYNC][DEBUG] ========== force_sync() CALLED ==========")
    try:
        print("[SYNC][DEBUG] Getting SyncService instance...")
        svc = _get_service()
        print(f"[SYNC][DEBUG] SyncService instance obtained: {svc}")
        
        # First push local changes
        push_res = None
        pull_res = None
        try:
            print("[SYNC][DEBUG] *** About to call svc.sync_to_server() ***")
            push_res = svc.sync_to_server()
            print(f"[SYNC][DEBUG] *** sync_to_server() returned: {push_res} ***")
        except Exception as e:
            # tolerate and continue to try pull
            print(f"[SYNC][DEBUG] *** sync_to_server() raised exception: {e} ***")
            import traceback
            traceback.print_exc()
            push_res = {'success': False, 'message': str(e)}

        try:
            print("[SYNC][DEBUG] *** About to call svc.sync_from_server() ***")
            pull_res = svc.sync_from_server()
            print(f"[SYNC][DEBUG] *** sync_from_server() returned: {pull_res} ***")
        except Exception as e:
            print(f"[SYNC][DEBUG] *** sync_from_server() raised exception: {e} ***")
            import traceback
            traceback.print_exc()
            pull_res = {'success': False, 'message': str(e)}

        result = _unwrap_result(push_res) and _unwrap_result(pull_res)
        print(f"[SYNC][DEBUG] ========== force_sync() RETURNING: {result} ==========")
        return result
    except Exception as e:
        print(f"[SYNC][DEBUG] ========== force_sync() EXCEPTION: {e} ==========")
        import traceback
        traceback.print_exc()
        return False
