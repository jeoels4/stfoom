# stfoom/ui/shared_widgets.py
import tkinter as tk
from tkinter import ttk
from app.connection import sync
from .language_manager import language_manager
from .notification_system import NotificationButton

_footer_instance = None  # shared singleton


class FooterStatusBar(ttk.Frame):
    """Bottom bar that always shows connection status and temporary sync messages."""

    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.pack(side="bottom", fill="x")

        global _footer_instance
        _footer_instance = self  # expose singleton for get_footer()

        # Configure style for footer
        style = ttk.Style()
        style.configure('FooterStatusBar.TFrame', background='white', relief='solid', borderwidth=1)
        style.configure('FooterStatus.TLabel', font=('Arial', 11), background='white')
        style.configure('FooterSync.TLabel', font=('Arial', 11, 'italic'), background='white', foreground='#0078D7')
        style.configure('FooterPending.TLabel', font=('Arial', 10), background='white', foreground='#ff6b35')
        style.configure('FooterSettings.TButton', font=('Arial', 10), padding=5)
        
        self.configure(style='FooterStatusBar.TFrame')

        # Left‑hand permanent pieces
        self.indicator = tk.Label(self, text="●", font=("Arial", 14, "bold"), bg='white')
        self.text = ttk.Label(self, style='FooterStatus.TLabel')
        
        # Middle - pending changes indicator
        self.pending_label = ttk.Label(self, style='FooterPending.TLabel')

        # Right‑hand area with settings button and sync message
        right_frame = ttk.Frame(self, style='FooterStatusBar.TFrame')
        right_frame.pack(side="right", fill="y")
        
        # Notification button (before chat)
        self.notification_btn = NotificationButton(right_frame)
        self.notification_btn.pack(side="right", padx=(6, 6), pady=8)
        
        # Chat button (between notifications and settings)
        self.chat_btn = ttk.Button(
            right_frame,
            text="💬",
            style='FooterSettings.TButton',
            width=3,
            command=self._show_chat
        )
        self.chat_btn.pack(side="right", padx=(6, 6), pady=8)
        
        # Settings button (small, bottom right)
        self.settings_btn = ttk.Button(
            right_frame,
            text="⚙️",
            style='FooterSettings.TButton',
            width=3
        )
        self.settings_btn.pack(side="right", padx=(6, 12), pady=8)

        # Right‑hand transient sync message (bright blue so it stands out)
        self.extra = ttk.Label(right_frame, style='FooterSync.TLabel')
        self.extra.pack(side="right", padx=12, pady=8)

        self.indicator.pack(side="left", padx=12, pady=8)
        self.text.pack(side="left", padx=(0, 12), pady=8)
        self.pending_label.pack(side="left", padx=(0, 24), pady=8)

        self._msg_timer_id = None  # track the auto‑clear timer
        # Start polling after a short delay to avoid initialization during import
        self.after(1000, self.update_status)

    # ────────────────── permanent connection indicator ──────────────────
    def update_status(self):
        # Check if footer still exists before updating
        if not self.winfo_exists():
            return
            
        # Check server connection
        if sync.server_online():
            self.indicator.config(fg="green")
            self.text.config(text=language_manager.get_text("sync_status_online"))
        else:
            self.indicator.config(fg="red")
            self.text.config(text=language_manager.get_text("sync_status_offline"))

        # Check pending changes
        try:
            pending_count = sync.get_pending_changes_count()
            if pending_count > 0:
                self.pending_label.config(text=f"⏳ {pending_count} changements en attente")
                self.pending_label.config(foreground='#ff6b35')
            else:
                self.pending_label.config(text="✓ Synchronisé")
                self.pending_label.config(foreground='#27ae60')
        except Exception as e:
            self.pending_label.config(text="⚠ Erreur sync")
            self.pending_label.config(foreground='#e74c3c')

        # check again every 5 s (only if footer still exists)
        if self.winfo_exists():
            self.after(5000, self.update_status)

    # ────────────────── transient sync message ──────────────────
    def set_sync_message(self, msg: str):
        """Show *msg* in the right‑hand area for 5 s (resets timer if called again)."""
        # Check if footer still exists before updating
        if not self.winfo_exists():
            return
            
        self.extra.config(text=msg)
        print("[FOOTER] set_sync_message:", msg)

        # cancel previous timer so each message lives a full 5 s
        if self._msg_timer_id is not None:
            self.after_cancel(self._msg_timer_id)

        # Schedule clear message (only if footer still exists)
        if self.winfo_exists():
            self._msg_timer_id = self.after(5000, self._clear_sync_message)

    def _clear_sync_message(self):
        # Check if footer still exists before clearing
        if not self.winfo_exists():
            return
            
        self.extra.config(text="")
        self._msg_timer_id = None

    def set_settings_command(self, command):
        """Set the command for the settings button."""
        self.settings_btn.config(command=command)
    
    def _show_chat(self):
        """Show chat window."""
        from .simple_chat import SimpleChatWindow
        # Check if chat window is already open
        if not hasattr(self, '_chat_window') or not self._chat_window or not self._chat_window.winfo_exists():
            self._chat_window = SimpleChatWindow(self.winfo_toplevel())
        else:
            # Bring existing window to front
            self._chat_window.lift()
            self._chat_window.focus_set()


# helper so other modules can fetch the footer and call set_sync_message()
def get_footer() -> "FooterStatusBar | None":
    return _footer_instance

# CURRENCY FORMATTING UTILITY FOR UI COMPONENTS
def format_money(amount: float) -> str:
    """Format money values with standardized 3 decimal places and TD currency.
    
    This function provides a centralized way to format all money values in the UI
    using the application's currency settings (3 decimals, TD symbol).
    
    Args:
        amount (float): The monetary amount to format
        
    Returns:
        str: Formatted string like "123.000 TD"
    """
    try:
        from app.config.settings import settings
        return settings.format_currency(amount)
    except ImportError:
        # Fallback if settings not available
        return f"{amount:.3f} TD"
