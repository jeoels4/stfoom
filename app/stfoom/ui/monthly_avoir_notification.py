"""
DEPRECATED: Old monthly avoir notification system
This file is kept for compatibility but the new unified notification system
in notification_system.py should be used instead.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict
import threading
import time

class MonthlyAvoirNotificationSystem:
    """DEPRECATED: Legacy notification system - use unified system instead"""
    
    def __init__(self, root_window):
        print("[DEPRECATED] MonthlyAvoirNotificationSystem is deprecated. Use unified notification system.")
        pass
    
    def start_monitoring(self):
        """DEPRECATED: No longer starts monitoring"""
        print("[DEPRECATED] start_monitoring() is deprecated. Use unified notification system.")
        pass
    
    def stop_monitoring(self):
        """DEPRECATED: No longer stops monitoring"""
        print("[DEPRECATED] stop_monitoring() is deprecated. Use unified notification system.")
        pass
    
    def manual_check(self):
        """DEPRECATED: Manual check now handled by unified system"""
        print("[DEPRECATED] manual_check() is deprecated. Use unified notification system.")
        # Don't show any popups - just log
        pass

# Global instance (for compatibility)
_notification_system = None

def initialize_notification_system(root_window):
    """DEPRECATED: Initialize function that does nothing"""
    print("[DEPRECATED] initialize_notification_system() is deprecated. Use unified notification system.")
    pass

def get_notification_system():
    """DEPRECATED: Return None to prevent old system from running"""
    print("[DEPRECATED] get_notification_system() is deprecated. Use unified notification system.")
    return None
