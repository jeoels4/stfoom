"""
Unified Notification System for STFOOM
Manages all application notifications with a central button in the footer
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import List, Dict, Optional, Callable
from datetime import datetime
import threading
import json
import os

class NotificationManager:
    """Centralized notification management system"""
    
    def __init__(self):
        self.notifications = []
        self.listeners = []
        self.notification_file = "data/notifications.json"
        self.auto_check_enabled = False
        self.check_thread = None
        self.root_window = None
        self.current_user = None
        self.load_notifications()
    
    def set_root_window(self, root):
        """Set the root window for GUI operations"""
        self.root_window = root
    
    def set_current_user(self, user):
        """Set current user - notifications only work when logged in"""
        self.current_user = user
        if user:
            self.start_auto_check()
        else:
            self.stop_auto_check()
            self.clear_user_notifications()
    
    def load_notifications(self):
        """Load notifications from file"""
        try:
            if os.path.exists(self.notification_file):
                with open(self.notification_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.notifications = data.get('notifications', [])
        except Exception as e:
            print(f"[NOTIFICATIONS] Error loading notifications: {e}")
            self.notifications = []
    
    def save_notifications(self):
        """Save notifications to file"""
        try:
            os.makedirs(os.path.dirname(self.notification_file), exist_ok=True)
            data = {'notifications': self.notifications}
            with open(self.notification_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[NOTIFICATIONS] Error saving notifications: {e}")
    
    def add_notification(self, title: str, message: str, type_: str = "info", 
                        data: Optional[Dict] = None, auto_dismiss: bool = False):
        """Add a new notification"""
        if not self.current_user:
            print("[NOTIFICATIONS] User not logged in, skipping notification")
            return
        
        notification = {
            'id': len(self.notifications) + 1,
            'title': title,
            'message': message,
            'type': type_,  # info, success, warning, error
            'timestamp': datetime.now().isoformat(),
            'seen': False,
            'dismissed': auto_dismiss,
            'data': data or {},
            'user_id': getattr(self.current_user, 'id', None)
        }
        
        self.notifications.append(notification)
        self.save_notifications()
        self.notify_listeners()
        
        print(f"[NOTIFICATIONS] Added: {title}")
    
    def mark_seen(self, notification_id: int):
        """Mark a notification as seen"""
        for notif in self.notifications:
            if notif['id'] == notification_id:
                notif['seen'] = True
                break
        self.save_notifications()
        self.notify_listeners()
    
    def mark_all_seen(self):
        """Mark all notifications as seen"""
        for notif in self.notifications:
            notif['seen'] = True
        self.save_notifications()
        self.notify_listeners()
    
    def dismiss_notification(self, notification_id: int):
        """Dismiss a notification"""
        self.notifications = [n for n in self.notifications if n['id'] != notification_id]
        self.save_notifications()
        self.notify_listeners()
    
    def get_notifications(self, include_dismissed: bool = False) -> List[Dict]:
        """Get all notifications"""
        current_user_id = getattr(self.current_user, 'id', None)
        notifications = []
        
        for notif in self.notifications:
            # Filter by user
            if notif.get('user_id') != current_user_id:
                continue
            
            # Filter dismissed if needed
            if not include_dismissed and notif.get('dismissed', False):
                continue
                
            notifications.append(notif)
        
        return sorted(notifications, key=lambda x: x['timestamp'], reverse=True)
    
    def get_unseen_count(self) -> int:
        """Get count of unseen notifications"""
        return len([n for n in self.get_notifications() if not n['seen']])
    
    def clear_user_notifications(self):
        """Clear notifications for current user when logging out"""
        self.notifications = []
        self.save_notifications()
        self.notify_listeners()
    
    def add_listener(self, callback: Callable):
        """Add a listener for notification updates"""
        self.listeners.append(callback)
    
    def remove_listener(self, callback: Callable):
        """Remove a listener"""
        if callback in self.listeners:
            self.listeners.remove(callback)
    
    def notify_listeners(self):
        """Notify all listeners of updates"""
        for callback in self.listeners:
            try:
                callback()
            except Exception as e:
                print(f"[NOTIFICATIONS] Error in listener callback: {e}")
    
    def start_auto_check(self):
        """Start automatic notification checking"""
        if not self.auto_check_enabled and self.current_user:
            self.auto_check_enabled = True
            self.check_thread = threading.Thread(target=self._auto_check_loop, daemon=True)
            self.check_thread.start()
            print("[NOTIFICATIONS] Auto-check started")
    
    def stop_auto_check(self):
        """Stop automatic notification checking"""
        self.auto_check_enabled = False
        print("[NOTIFICATIONS] Auto-check stopped")
    
    def _auto_check_loop(self):
        """Background loop for checking new notifications"""
        import time
        
        while self.auto_check_enabled and self.current_user:
            try:
                # Check for monthly avoir notifications
                if self.current_user:  # Double-check user is still logged in
                    self._check_monthly_avoir()
                
                # Check for calendar notifications (events due tomorrow)
                if self.current_user:  # Double-check user is still logged in
                    self._check_calendar_notifications()
                
                # Add other notification checks here
                
                time.sleep(60)  # Check every minute
                
            except Exception as e:
                print(f"[NOTIFICATIONS] Error in auto-check: {e}")
                time.sleep(60)
            
            # Extra safety check
            if not self.current_user:
                print("[NOTIFICATIONS] User logged out, stopping auto-check")
                break
    
    def _check_monthly_avoir(self):
        """Check for monthly avoir notifications"""
        if not self.current_user:
            return  # Don't check if no user is logged in
            
        try:
            # TODO: Replace with AvoirService when available
            # from stfoom.logic.monthly_avoir_manager import MonthlyAvoirManager  # DISABLED: using placeholder
            
            # Placeholder for monthly avoir notifications
            print("[NOTIFICATIONS] Monthly avoir check skipped - service migration needed")
            return
            
            monthly_manager = MonthlyAvoirManager()
            pending = monthly_manager.get_pending_notifications()
            
            for notif_data in pending:
                # Check if we already have this notification
                existing = False
                for existing_notif in self.notifications:
                    if (existing_notif.get('type') == 'monthly_avoir' and 
                        existing_notif.get('data', {}).get('month') == notif_data['month']):
                        existing = True
                        break
                
                if not existing:
                    self.add_notification(
                        title="🎉 Avoir Mensuel Disponible!",
                        message=notif_data['message'],
                        type_="success",
                        data={
                            'type': 'monthly_avoir',
                            'month': notif_data['month'],
                            'quantity': notif_data['quantity'],
                            'avoir_amount': notif_data['avoir_amount']
                        }
                    )
                    
                    # Mark as notified in the monthly system
                    monthly_manager.mark_notification_sent(notif_data['month'])
        
        except Exception as e:
            print(f"[NOTIFICATIONS] Error checking monthly avoir: {e}")
    
    def _check_calendar_notifications(self):
        """Check for calendar notifications (events due tomorrow)"""
        if not self.current_user:
            return  # Don't check if no user is logged in
            
        try:
            # TODO: Replace with CalendarService when available
            # from stfoom.logic.calendar_base import get_pending_calendar_notifications  # DISABLED: using placeholder
            
            # Placeholder for calendar notifications 
            print("[NOTIFICATIONS] Calendar check skipped - service migration needed")
            return
            
            pending_events = get_pending_calendar_notifications()
            
            for event_data in pending_events:
                # Check if we already have this notification for this specific event and date
                existing = False
                for existing_notif in self.notifications:
                    notif_data = existing_notif.get('data', {})
                    if (notif_data.get('type') == 'calendar_reminder' and 
                        notif_data.get('event_id') == event_data['event_id'] and
                        notif_data.get('date') == event_data['date']):
                        existing = True
                        break
                
                if not existing:
                    self.add_notification(
                        title="📅 Rappel Calendrier",
                        message=event_data['message'],
                        type_="warning",
                        data={
                            'type': 'calendar_reminder',
                            'event_id': event_data['event_id'],
                            'event_title': event_data['title'],
                            'date': event_data['date'],
                            'category': event_data['category'],
                            'description': event_data['description']
                        }
                    )
                    print(f"[NOTIFICATIONS] Added calendar reminder for: {event_data['title']}")
        
        except Exception as e:
            print(f"[NOTIFICATIONS] Error checking calendar notifications: {e}")
    
    def check_calendar_now(self):
        """Manually trigger calendar notification check (useful when calendar is modified)"""
        if self.current_user:
            print("[NOTIFICATIONS] Manual calendar check triggered")
            self._check_calendar_notifications()
    
    def check_all_notifications_now(self):
        """Manually trigger all notification checks"""
        if self.current_user:
            print("[NOTIFICATIONS] Manual notification check triggered")
            self._check_monthly_avoir()
            self._check_calendar_notifications()


# Global notification manager instance
notification_manager = NotificationManager()


class NotificationButton(ttk.Frame):
    """Notification button widget for the footer"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.notification_window = None
        
        # Create button with bell icon
        self.btn = ttk.Button(
            self,
            text="🔔",
            width=3,
            command=self.show_notifications
        )
        self.btn.pack(side="left")
        
        # Badge for unread count
        self.badge = tk.Label(
            self,
            text="",
            font=("Arial", 8, "bold"),
            fg="white",
            bg="red",
            width=2,
            height=1,
            bd=0
        )
        
        # Add listener to notification manager
        notification_manager.add_listener(self.update_badge)
        
        # Initial update
        self.update_badge()
    
    def update_badge(self):
        """Update the notification badge"""
        try:
            unseen_count = notification_manager.get_unseen_count()
            
            if unseen_count > 0:
                if unseen_count > 99:
                    badge_text = "99+"
                else:
                    badge_text = str(unseen_count)
                
                self.badge.config(text=badge_text)
                self.badge.place(x=20, y=0, width=15, height=15)
                
                # Change button appearance
                self.btn.config(text="🔔")
            else:
                self.badge.place_forget()
                self.btn.config(text="🔔")
                
        except Exception as e:
            print(f"[NOTIFICATIONS] Error updating badge: {e}")
    
    def show_notifications(self):
        """Show notifications window"""
        try:
            if self.notification_window and self.notification_window.winfo_exists():
                self.notification_window.lift()
                return
            
            self.notification_window = NotificationWindow(self)
        except Exception as e:
            print(f"[NOTIFICATIONS] Error showing notification window: {e}")
            # Reset window reference if there was an error
            self.notification_window = None
    
    def destroy(self):
        """Clean up when widget is destroyed"""
        notification_manager.remove_listener(self.update_badge)
        super().destroy()


class NotificationWindow(tk.Toplevel):
    """Window showing all notifications"""
    
    def __init__(self, parent):
        super().__init__(parent)
        
        self.title("🔔 Notifications")
        self.geometry("500x600")
        self.transient(parent.winfo_toplevel())
        
        # Center window
        self.center_window()
        
        self.setup_ui()
        self.load_notifications()
        
        # Bind cleanup on window destroy
        self.protocol("WM_DELETE_WINDOW", self.cleanup_and_destroy)
    
    def cleanup_and_destroy(self):
        """Clean up resources before destroying window"""
        try:
            # Unbind mouse wheel event
            if hasattr(self, '_mousewheel_callback'):
                self.unbind_all("<MouseWheel>")
            
            # Destroy canvas safely
            if hasattr(self, 'canvas') and self.canvas.winfo_exists():
                self.canvas.destroy()
                
        except Exception as e:
            print(f"[NOTIFICATIONS] Error during cleanup: {e}")
        finally:
            self.destroy()
    
    def center_window(self):
        """Center the window on screen"""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (600 // 2)
        self.geometry(f"500x600+{x}+{y}")
    
    def setup_ui(self):
        """Setup the UI"""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=(20, 10))
        
        ttk.Label(header_frame, text="🔔 Notifications", 
                 font=("Segoe UI", 16, "bold")).pack(side="left")
        
        # Action buttons
        btn_frame = ttk.Frame(header_frame)
        btn_frame.pack(side="right")
        
        ttk.Button(btn_frame, text="✓ Tout marquer comme lu", 
                  command=self.mark_all_seen).pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_frame, text="❌ Fermer", 
                  command=self.destroy).pack(side="left")
        
        # Notifications list
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Scrollable frame
        canvas = tk.Canvas(list_frame, bg="white")
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Store canvas reference for cleanup
        self.canvas = canvas
        
        # Mouse wheel binding
        def _on_mousewheel(event):
            try:
                if canvas.winfo_exists():
                    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
            except tk.TclError:
                # Canvas was destroyed, unbind the event
                try:
                    canvas.unbind_all("<MouseWheel>")
                except:
                    pass
        
        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        self._mousewheel_callback = _on_mousewheel
    
    def load_notifications(self):
        """Load and display notifications"""
        # Clear existing
        for widget in self.scrollable_frame.winfo_children():
            widget.destroy()
        
        notifications = notification_manager.get_notifications()
        
        if not notifications:
            no_notif_label = ttk.Label(
                self.scrollable_frame, 
                text="📭 Aucune notification",
                font=("Segoe UI", 12),
                foreground="#666666"
            )
            no_notif_label.pack(pady=50)
            return
        
        for notif in notifications:
            self.create_notification_widget(notif)
    
    def create_notification_widget(self, notif: Dict):
        """Create a widget for a single notification"""
        # Notification frame
        notif_frame = ttk.LabelFrame(self.scrollable_frame, padding=10)
        notif_frame.pack(fill="x", pady=(0, 10))
        
        # Header row
        header_row = ttk.Frame(notif_frame)
        header_row.pack(fill="x")
        
        # Title with type icon
        type_icons = {
            'info': '💬',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        icon = type_icons.get(notif['type'], '💬')
        
        title_text = f"{icon} {notif['title']}"
        if not notif['seen']:
            title_text = f"🆕 {title_text}"
        
        title_label = ttk.Label(header_row, text=title_text, 
                               font=("Segoe UI", 11, "bold"))
        title_label.pack(side="left")
        
        # Timestamp
        try:
            timestamp = datetime.fromisoformat(notif['timestamp'])
            time_str = timestamp.strftime("%d/%m/%Y %H:%M")
        except:
            time_str = "Date inconnue"
        
        time_label = ttk.Label(header_row, text=time_str, 
                              font=("Segoe UI", 9), foreground="#666666")
        time_label.pack(side="right")
        
        # Message
        message_label = ttk.Label(notif_frame, text=notif['message'], 
                                 font=("Segoe UI", 10), wraplength=450)
        message_label.pack(anchor="w", pady=(5, 0))
        
        # Action buttons
        action_frame = ttk.Frame(notif_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        if not notif['seen']:
            ttk.Button(action_frame, text="✓ Marquer comme lu",
                      command=lambda: self.mark_seen(notif['id'])).pack(side="left", padx=(0, 10))
        
        ttk.Button(action_frame, text="🗑️ Supprimer",
                  command=lambda: self.dismiss_notification(notif['id'])).pack(side="left")
        
        # Special actions for monthly avoir
        if notif.get('data', {}).get('type') == 'monthly_avoir':
            ttk.Button(action_frame, text="📊 Voir Détails",
                      command=lambda: self.show_monthly_avoir_details(notif['data'])).pack(side="right")
    
    def mark_seen(self, notification_id: int):
        """Mark notification as seen"""
        try:
            notification_manager.mark_seen(notification_id)
            self.load_notifications()  # Refresh display
        except Exception as e:
            print(f"[NOTIFICATIONS] Error marking notification as seen: {e}")
    
    def mark_all_seen(self):
        """Mark all notifications as seen"""
        try:
            notification_manager.mark_all_seen()
            self.load_notifications()  # Refresh display
        except Exception as e:
            print(f"[NOTIFICATIONS] Error marking all notifications as seen: {e}")
    
    def dismiss_notification(self, notification_id: int):
        """Dismiss a notification"""
        try:
            notification_manager.dismiss_notification(notification_id)
            self.load_notifications()  # Refresh display
        except Exception as e:
            print(f"[NOTIFICATIONS] Error dismissing notification: {e}")
    
    def show_monthly_avoir_details(self, data: Dict):
        """Show monthly avoir details"""
        month = data.get('month', 'Unknown')
        quantity = data.get('quantity', 0)
        avoir_amount = data.get('avoir_amount', 0)
        
        message = f"""Détails de l'avoir mensuel:

📅 Mois: {month}
📦 Quantité totale: {quantity:.1f} tonnes
🎯 Seuil 200T: ✅ Atteint
💰 Avoir éligible: {avoir_amount:.3f} DT

Pour gérer cet avoir, allez dans:
🏗️ Ciment/Matière Première → 🎯 Avoirs 200T/Mois"""
        
        messagebox.showinfo("📊 Détails Avoir Mensuel", message)


def get_notification_manager():
    """Get the global notification manager"""
    return notification_manager
