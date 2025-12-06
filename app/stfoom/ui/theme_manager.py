# stfoom/ui/theme_manager.py
import tkinter as tk
from tkinter import ttk
from typing import Dict, Any

class ThemeManager:
    """Manages application themes and styling."""
    
    def __init__(self):
        self.current_theme = "light"
        self.themes = {
            "light": self._get_light_theme(),
            "dark": self._get_dark_theme()
        }
    
    def _get_light_theme(self) -> Dict[str, Any]:
        """Get light theme colors and styles."""
        return {
            "bg_primary": "#ffffff",
            "bg_secondary": "#f7f7fa",
            "bg_tertiary": "#f0f0f0",
            "text_primary": "#222222",
            "text_secondary": "#666666",
            "accent_primary": "#27ae60",
            "accent_secondary": "#0078D7",
            "border_primary": "#e0e0e0",
            "border_secondary": "#d0d0d0",
            "success": "#27ae60",
            "warning": "#f39c12",
            "error": "#e74c3c",
            "info": "#3498db"
        }
    
    def _get_dark_theme(self) -> Dict[str, Any]:
        """Get dark theme colors and styles."""
        return {
            "bg_primary": "#2c2c2c",
            "bg_secondary": "#1e1e1e",
            "bg_tertiary": "#3c3c3c",
            "text_primary": "#ffffff",
            "text_secondary": "#cccccc",
            "accent_primary": "#4CAF50",
            "accent_secondary": "#2196F3",
            "border_primary": "#555555",
            "border_secondary": "#444444",
            "success": "#4CAF50",
            "warning": "#FF9800",
            "error": "#F44336",
            "info": "#2196F3"
        }
    
    def get_color(self, color_name: str) -> str:
        """Get color for the current theme."""
        return self.themes.get(self.current_theme, {}).get(color_name, "#000000")
    
    def set_theme(self, theme: str) -> bool:
        """Set the current theme."""
        if theme in self.themes:
            self.current_theme = theme
            return True
        return False
    
    def get_available_themes(self) -> list:
        """Get list of available themes."""
        return list(self.themes.keys())
    
    def get_theme_names(self) -> Dict[str, str]:
        """Get theme names for display."""
        return {
            "light": "Clair",
            "dark": "Sombre"
        }
    
    def apply_theme_to_root(self, root):
        """Apply current theme to the root window."""
        theme = self.themes[self.current_theme]
        
        # Configure root window
        root.configure(bg=theme["bg_secondary"])
        
        # Configure ttk styles
        style = ttk.Style()
        
        # Main frame styles
        style.configure("Main.TFrame", background=theme["bg_primary"])
        style.configure("Main.TButton", 
                       font=("Segoe UI", 15), 
                       padding=10,
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        
        # Settings page styles
        style.configure("Settings.TFrame", background=theme["bg_primary"])
        style.configure("SettingsHeader.TLabel", 
                       background=theme["bg_primary"], 
                       font=("Segoe UI", 24, "bold"), 
                       foreground=theme["text_primary"])
        style.configure("SettingsSection.TLabelframe", 
                       font=("Segoe UI", 13, "bold"), 
                       background=theme["bg_primary"], 
                       foreground=theme["text_primary"], 
                       borderwidth=1)
        style.configure("SettingsSection.TLabelframe.Label", 
                       font=("Segoe UI", 13, "bold"), 
                       foreground=theme["accent_primary"], 
                       background=theme["bg_primary"])
        style.configure("Settings.TButton", 
                       font=("Segoe UI", 11), 
                       padding=8,
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        style.configure("SettingsSave.TButton", 
                       font=("Segoe UI", 12, "bold"), 
                       foreground="#ffffff", 
                       background=theme["accent_primary"], 
                       padding=10)
        style.configure("SettingsDanger.TButton", 
                       font=("Segoe UI", 11), 
                       foreground="#ffffff", 
                       background=theme["error"], 
                       padding=8)
        
        # Facture page styles
        style.configure("FactureMain.TFrame", background=theme["bg_primary"])
        style.configure("FactureHeader.TFrame", background=theme["bg_primary"])
        style.configure("FactureHeader.TLabel", 
                       background=theme["bg_primary"], 
                       font=("Segoe UI", 22, "bold"), 
                       foreground=theme["text_primary"])
        style.configure("FactureSection.TLabelframe", 
                       font=("Segoe UI", 13, "bold"), 
                       background=theme["bg_primary"], 
                       foreground=theme["text_primary"], 
                       borderwidth=0)
        style.configure("FactureSection.TLabelframe.Label", 
                       font=("Segoe UI", 13, "bold"), 
                       foreground=theme["accent_primary"], 
                       background=theme["bg_primary"])
        style.configure("FactureRemise.TLabel", 
                       font=("Segoe UI", 11, "italic"), 
                       foreground=theme["error"], 
                       background=theme["bg_primary"])
        style.configure("FactureProducts.TFrame", background=theme["bg_primary"])
        style.configure("FactureCheck.TCheckbutton", 
                       font=("Segoe UI", 11), 
                       background=theme["bg_primary"])
        
        # Footer styles
        style.configure('FooterStatusBar.TFrame', 
                       background=theme["bg_primary"], 
                       relief='solid', 
                       borderwidth=1)
        style.configure('FooterStatus.TLabel', 
                       font=('Arial', 10), 
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        style.configure('FooterSync.TLabel', 
                       font=('Arial', 10, 'italic'), 
                       background=theme["bg_primary"], 
                       foreground=theme["accent_secondary"])
        style.configure('FooterPending.TLabel', 
                       font=('Arial', 9), 
                       background=theme["bg_primary"], 
                       foreground=theme["warning"])
        style.configure('FooterSettings.TButton', 
                       font=('Arial', 9), 
                       padding=2,
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        
        # General widget styles
        style.configure("TLabel", 
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        style.configure("TEntry", 
                       fieldbackground=theme["bg_tertiary"],
                       foreground=theme["text_primary"],
                       insertcolor=theme["text_primary"])
        style.configure("TCombobox", 
                       fieldbackground=theme["bg_tertiary"],
                       foreground=theme["text_primary"],
                       background=theme["bg_primary"])
        style.configure("TCheckbutton", 
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        style.configure("TRadiobutton", 
                       background=theme["bg_primary"],
                       foreground=theme["text_primary"])
        style.configure("TNotebook", 
                       background=theme["bg_primary"],
                       tabmargins=[2, 5, 2, 0])
        style.configure("TNotebook.Tab", 
                       background=theme["bg_tertiary"],
                       foreground=theme["text_primary"],
                       padding=[10, 5])
        style.map("TNotebook.Tab",
                 background=[("selected", theme["accent_primary"]),
                            ("active", theme["bg_secondary"])],
                 foreground=[("selected", "#ffffff"),
                            ("active", theme["text_primary"])])
        
        # Button styles
        style.map("TButton",
                 background=[("active", theme["bg_secondary"]),
                            ("pressed", theme["bg_tertiary"])],
                 foreground=[("active", theme["text_primary"]),
                            ("pressed", theme["text_primary"])])
        
        # Entry styles
        style.map("TEntry",
                 fieldbackground=[("focus", theme["bg_tertiary"]),
                                 ("readonly", theme["bg_secondary"])])
        
        # Combobox styles
        style.map("TCombobox",
                 fieldbackground=[("readonly", theme["bg_tertiary"]),
                                 ("focus", theme["bg_tertiary"])],
                 selectbackground=[("readonly", theme["accent_primary"])],
                 selectforeground=[("readonly", "#ffffff")])

# Global instance
theme_manager = ThemeManager() 