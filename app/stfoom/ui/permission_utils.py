"""
Permission utilities for UI components
=====================================
Provides permission checking utilities for UI elements.
"""

from tkinter import messagebox
import tkinter as tk

# Global variables for current session
current_user = None
current_user_rank = None

def set_current_user(username, user_rank):
    """Set current user for permission checking"""
    global current_user, current_user_rank
    current_user = username
    current_user_rank = user_rank

def check_ui_permission(resource: str, action: str, show_error: bool = True) -> bool:
    """
    Check if current user has permission for UI operation.
    
    Args:
        resource: Resource name (e.g., 'sales', 'purchases') 
        action: Action name (e.g., 'create', 'delete')
        show_error: Whether to show error dialog
    
    Returns:
        True if has permission, False otherwise
    """
    try:
        # ✅ CRITICAL FIX: Import BasicPermissionService directly instead of from main
        # This prevents triggering main.py execution when checking permissions
        from app.stfoom.logic.basic_permission_service import BasicPermissionService
        
        permission_service = BasicPermissionService()
        
        # Get current user rank
        user_rank = current_user_rank or 'admin'  # Default to admin if not set
        
        # Check permission
        permission_name = f"{resource}.{action}"
        has_perm = permission_service.user_has_permission(user_rank, permission_name)
        
        if not has_perm and show_error:
            messagebox.showerror(
                "Permission Refusée", 
                f"Vous n'avez pas la permission d'effectuer cette action ({permission_name})"
            )
        
        return has_perm
    
    except Exception as e:
        print(f"[PERMISSION] Error checking permission: {e}")
        # Admin override on error - if we can't check permissions, allow admin actions
        if current_user_rank == "admin":
            print(f"[PERMISSION] Admin override - allowing action {resource}.{action}")
            return True
        return False

def require_ui_permission(resource: str, action: str):
    """
    Decorator to require permission for UI operations.
    Shows error dialog if permission denied.
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if check_ui_permission(resource, action):
                return func(*args, **kwargs)
            else:
                print(f"[PERMISSION] Access denied for {resource}.{action}")
                return None
        return wrapper
    return decorator

def disable_button_if_no_permission(button, resource: str, action: str):
    """
    Disable button if user doesn't have permission.
    
    Args:
        button: Tkinter button widget
        resource: Resource name
        action: Action name
    """
    try:
        if not check_ui_permission(resource, action, show_error=False):
            button.config(state="disabled")
            # Add tooltip or visual indication
            button.config(bg="lightgray")
    except Exception as e:
        print(f"[PERMISSION] Error checking permission for button: {e}")

def enable_button_if_permission(button, resource: str, action: str):
    """
    Enable button only if user has permission.
    
    Args:
        button: Tkinter button widget
        resource: Resource name
        action: Action name
    """
    try:
        if check_ui_permission(resource, action, show_error=False):
            button.config(state="normal")
        else:
            button.config(state="disabled")
            button.config(bg="lightgray")
    except Exception as e:
        print(f"[PERMISSION] Error enabling button: {e}")
        # Default to enabled if error and user is admin
        if current_user_rank == "admin":
            button.config(state="normal")

def get_permission_context():
    """Get current permission context for debugging"""
    return {
        'user': current_user,
        'rank': current_user_rank,
        'logged_in': current_user is not None
    }
