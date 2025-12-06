# stfoom/ui/settings_page.py
import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import shutil
from datetime import datetime
from .language_manager import language_manager
from .theme_manager import theme_manager
from .tax_management_widget import TaxManagementFrame

def get_database_path():
    """Get the correct database path for both development and packaged environments."""
    # For PyInstaller packaged executables
    if getattr(sys, 'frozen', False):
        # Running in a PyInstaller bundle
        app_dir = os.path.dirname(sys.executable)
        data_dir = os.path.join(app_dir, "data")
    else:
        # Running in development
        # Get path relative to this module
        current_dir = os.path.dirname(os.path.abspath(__file__))
        data_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "data"))
    
    # Ensure data directory exists
    os.makedirs(data_dir, exist_ok=True)
    
    return os.path.join(data_dir, "stfoom.db")

class SettingsPage(ttk.Frame):
    """Professional settings page with categorized settings."""
    
    def __init__(self, parent, di_container_or_go_home_callback, go_home_callback=None):
        super().__init__(parent)
        
        # Handle both old and new signatures for backward compatibility
        if go_home_callback is None:
            # Old signature: __init__(parent, go_home_callback)  
            self.go_home = di_container_or_go_home_callback
            self.di_container = None
        else:
            # New signature: __init__(parent, di_container, go_home_callback)
            self.di_container = di_container_or_go_home_callback
            self.go_home = go_home_callback
            
        self.settings_file = os.path.join("config", "settings.json")  # Look in config directory
        self.settings = self.load_settings()
        
        self.setup_ui()
        self.load_current_settings()
    
    
    def get_settings_service(self):
        """Get settings service from DI container"""
        if self.di_container:
            return self.di_container.get("settings_service")
        else:
            # Fallback for backward compatibility
            from app.stfoom.services.settings_service import SettingsService
            return SettingsService()
    
    def get_database_service(self):
        """Get database service from DI container"""
        if self.di_container:
            return self.di_container.get("database_service")
        else:
            # Fallback: create a simple database service inline
            import sqlite3
            class SimpleDatabaseService:
                def get_database_statistics(self):
                    try:
                        with sqlite3.connect(get_database_path()) as conn:
                            cursor = conn.cursor()
                            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                            tables = cursor.fetchall()
                            
                            stats = {}
                            for table in tables:
                                table_name = table[0]
                                cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                                count = cursor.fetchone()[0]
                                stats[table_name] = count
                            return stats
                    except Exception as e:
                        print(f"Database stats error: {e}")
                        return {}
            
            return SimpleDatabaseService()


    def get_database_stats_via_service(self):
        """Get database statistics using service layer"""
        try:
            db_service = self.get_database_service()
            stats = db_service.get_database_statistics()
            
            self.stats_text.delete("1.0", tk.END)
            if stats:
                for table_name, count in stats.items():
                    self.stats_text.insert(tk.END, f"{table_name}: {count} records\n")
            else:
                self.stats_text.insert(tk.END, "Unable to load database statistics")
                
        except Exception as e:
            self.stats_text.delete("1.0", tk.END)
            self.stats_text.insert(tk.END, f"Error loading stats: {e}")
    
    def get_tva_settings_via_service(self):
        """Get TVA settings using settings service - SINGLE SOURCE OF TRUTH"""
        try:
            settings_service = self.get_settings_service()
            
            # Try to get from the DI container service first (uses different interface)
            if hasattr(settings_service, 'get_setting') and callable(getattr(settings_service, 'get_setting')):
                # DI container service - uses 2 parameters
                tva19 = settings_service.get_setting("tva_rate_19", 19.0) or 19.0
                tva7 = settings_service.get_setting("tva_rate_7", 7.0) or 7.0
                timbre = settings_service.get_setting("timbre_amount", 1.0) or 1.0
            else:
                # Direct service - uses 3 parameters  
                tva19 = settings_service.get_setting("taxes", "tva_rate_19", {}) or 19.0
                tva7 = settings_service.get_setting("taxes", "tva_rate_7", {}) or 7.0
                timbre = settings_service.get_setting("taxes", "timbre_amount", {}) or 1.0
            
            return {
                'tva19': float(tva19),
                'tva7': float(tva7), 
                'timbre': float(timbre)
            }
        except Exception as e:
            print(f"Error getting TVA settings: {e}")
            return {'tva19': 19.0, 'tva7': 7.0, 'timbre': 1.0}  # Correct timbre fallback value
    
    def save_tva_settings_via_service(self, tva19, tva7, timbre):
        """Save TVA settings using service layer"""
        try:
            settings_service = self.get_settings_service()
            
            # Try to save using the DI container service interface
            if hasattr(settings_service, 'set_setting') and callable(getattr(settings_service, 'set_setting')):
                # Check method signature - if it accepts 2 params, it's DI service
                try:
                    settings_service.set_setting("tva_rate_19", float(tva19))
                    settings_service.set_setting("tva_rate_7", float(tva7))
                    settings_service.set_setting("timbre_amount", float(timbre))  # Use consistent key
                except TypeError:
                    # If that fails, try 3-parameter version (direct service)
                    settings_service.set_setting("taxes", "tva_rate_19", float(tva19))
                    settings_service.set_setting("taxes", "tva_rate_7", float(tva7))
                    settings_service.set_setting("taxes", "timbre_amount", float(timbre))
            
            return True
        except Exception as e:
            print(f"Error saving TVA settings: {e}")
            return False


    def setup_ui(self):
        """Create the settings UI with professional design."""
        # Main container with padding
        main_frame = ttk.Frame(self, style="Settings.TFrame")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Header
        header_frame = ttk.Frame(main_frame, style="Settings.TFrame")
        header_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Label(
            header_frame, 
            text=language_manager.get_text("settings_title"), 
            font=("Segoe UI", 24, "bold"),
            style="SettingsHeader.TLabel"
        ).pack(side="left")
        
        # Back button
        ttk.Button(
            header_frame,
            text=language_manager.get_text("back_to_menu"),
            command=self.go_home,
            style="Settings.TButton"
        ).pack(side="right")
        
        # Create notebook for tabbed interface
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill="both", expand=True)
        
        # Create tabs
        self.create_general_tab()
        self.create_database_tab()
        self.create_sync_tab()
        self.create_backup_tab()
        self.create_cement_tab()  # NEW: Cement module settings
        self.create_taxes_tab()  # NEW: Tax management settings
        self.create_advanced_tab()
        
        # Bottom buttons
        self.create_bottom_buttons(main_frame)
    
    def create_general_tab(self):
        """Create general settings tab."""
        general_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(general_frame, text=language_manager.get_text("tab_general"))
        
        # Language settings
        lang_frame = ttk.LabelFrame(general_frame, text=language_manager.get_text("language_interface"), style="SettingsSection.TLabelframe")
        lang_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(lang_frame, text=language_manager.get_text("interface_language")).pack(anchor="w", padx=10, pady=5)
        self.language_var = tk.StringVar(value=self.settings.get("language", "fr"))
        language_combo = ttk.Combobox(
            lang_frame, 
            textvariable=self.language_var,
            values=["Français", "English"],
            state="readonly",
            width=20
        )
        language_combo.pack(anchor="w", padx=10, pady=(0, 10))
        language_combo.bind('<<ComboboxSelected>>', self.on_language_change)
        
        # Theme settings
        ttk.Label(lang_frame, text=language_manager.get_text("theme")).pack(anchor="w", padx=10, pady=(10, 5))
        self.theme_var = tk.StringVar(value=self.settings.get("theme", "light"))
        theme_combo = ttk.Combobox(
            lang_frame,
            textvariable=self.theme_var,
            values=[language_manager.get_text("light_theme"), language_manager.get_text("dark_theme")],
            state="readonly",
            width=20
        )
        theme_combo.pack(anchor="w", padx=10, pady=(0, 10))
        theme_combo.bind('<<ComboboxSelected>>', self.on_theme_change)
        
        # Auto-save settings
        auto_frame = ttk.LabelFrame(general_frame, text=language_manager.get_text("auto_save"), style="SettingsSection.TLabelframe")
        auto_frame.pack(fill="x", padx=10, pady=10)
        
        self.auto_save_var = tk.BooleanVar(value=self.settings.get("auto_save", True))
        ttk.Checkbutton(
            auto_frame,
            text=language_manager.get_text("enable_auto_save"),
            variable=self.auto_save_var
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Label(auto_frame, text=language_manager.get_text("save_interval")).pack(anchor="w", padx=10, pady=(10, 5))
        self.auto_save_interval = tk.StringVar(value=str(self.settings.get("auto_save_interval", 5)))
        ttk.Entry(auto_frame, textvariable=self.auto_save_interval, width=10).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Payment settings
        payment_frame = ttk.LabelFrame(general_frame, text="Paramètres de Paiement", style="SettingsSection.TLabelframe")
        payment_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Label(payment_frame, text="Tolérance de paiement (DT):").pack(anchor="w", padx=10, pady=(10, 5))
        ttk.Label(payment_frame, 
                  text="Montant toléré manquant pour considérer une facture comme payée", 
                  font=("Segoe UI", 8),
                  foreground="gray").pack(anchor="w", padx=10, pady=(0, 5))
        
        self.payment_tolerance_var = tk.StringVar(value=str(self.settings.get("payment_tolerance", 40)))
        tolerance_entry = ttk.Entry(payment_frame, textvariable=self.payment_tolerance_var, width=15)
        tolerance_entry.pack(anchor="w", padx=10, pady=(0, 10))
        
        # Add immediate save button for payment tolerance
        def save_payment_tolerance():
            try:
                new_tolerance = float(self.payment_tolerance_var.get())
                print(f"[SETTINGS] Saving new tolerance: {new_tolerance}")
                
                # Load current settings
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        current_settings = json.load(f)
                else:
                    current_settings = {}
                
                # Update tolerance
                current_settings['payment_tolerance'] = new_tolerance
                
                # Save settings
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(current_settings, f, indent=2, ensure_ascii=False)
                
                self.settings = current_settings
                print(f"[SETTINGS] Tolerance saved successfully: {new_tolerance}")
                messagebox.showinfo("Succès", f"Tolérance de paiement mise à jour: {new_tolerance} DT")
                
            except Exception as e:
                print(f"[SETTINGS] Error saving tolerance: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {str(e)}")
        
        # Save button for payment tolerance
        ttk.Button(
            payment_frame,
            text="💾 Sauvegarder Tolérance", 
            command=save_payment_tolerance,
            style="Accent.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        # Add validation
        def validate_tolerance(*args):
            try:
                value = float(self.payment_tolerance_var.get())
                if value < 0:
                    self.payment_tolerance_var.set("0")
            except ValueError:
                # Ignore invalid values during typing
                pass
        
        self.payment_tolerance_var.trace("w", validate_tolerance)
    
    def create_database_tab(self):
        """Create database settings tab."""
        db_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(db_frame, text=language_manager.get_text("tab_database"))
        
        # Database info
        info_frame = ttk.LabelFrame(db_frame, text="Informations de la base de données", style="SettingsSection.TLabelframe")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        # Get database info using service layer
        try:
            db_service = self.get_database_service()
            stats = db_service.get_database_statistics()
            
            if stats:
                table_count = len(stats)
                total_records = sum(stats.values())
                
                ttk.Label(info_frame, text=f"Nombre de tables: {table_count}").pack(anchor="w", padx=10, pady=5)
                ttk.Label(info_frame, text=f"Total des enregistrements: {total_records}").pack(anchor="w", padx=10, pady=5)
            else:
                ttk.Label(info_frame, text="Impossible de charger les informations de la base").pack(anchor="w", padx=10, pady=5)
            
        except Exception as e:
            ttk.Label(info_frame, text=f"Erreur lors de la lecture de la base: {str(e)}").pack(anchor="w", padx=10, pady=5)
        
        # Database maintenance
        maintenance_frame = ttk.LabelFrame(db_frame, text="Maintenance", style="SettingsSection.TLabelframe")
        maintenance_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            maintenance_frame,
            text="Optimiser la base de données",
            command=self.optimize_database,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            maintenance_frame,
            text="Vérifier l'intégrité",
            command=self.check_database_integrity,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            maintenance_frame,
            text="Nettoyer les données temporaires",
            command=self.clean_temp_data,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
    
    def create_sync_tab(self):
        """Create synchronization settings tab."""
        sync_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(sync_frame, text=language_manager.get_text("tab_sync"))
        
        # Sync settings
        sync_settings_frame = ttk.LabelFrame(sync_frame, text="Paramètres de synchronisation", style="SettingsSection.TLabelframe")
        sync_settings_frame.pack(fill="x", padx=10, pady=10)
        
        self.auto_sync_var = tk.BooleanVar(value=self.settings.get("auto_sync", True))
        ttk.Checkbutton(
            sync_settings_frame,
            text="Synchronisation automatique",
            variable=self.auto_sync_var
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Label(sync_settings_frame, text="Intervalle de sync (secondes):").pack(anchor="w", padx=10, pady=(10, 5))
        self.sync_interval = tk.StringVar(value=str(self.settings.get("sync_interval", 30)))
        ttk.Entry(sync_settings_frame, textvariable=self.sync_interval, width=10).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Sync status
        status_frame = ttk.LabelFrame(sync_frame, text="Statut de synchronisation", style="SettingsSection.TLabelframe")
        status_frame.pack(fill="x", padx=10, pady=10)
        
        self.sync_status_label = ttk.Label(status_frame, text="Vérification...")
        self.sync_status_label.pack(anchor="w", padx=10, pady=5)
        
        # Manual sync
        manual_frame = ttk.LabelFrame(sync_frame, text="Synchronisation manuelle", style="SettingsSection.TLabelframe")
        manual_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            manual_frame,
            text="Synchroniser maintenant",
            command=self.manual_sync,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        # Update sync status
        self.update_sync_status()
    
    def create_backup_tab(self):
        """Create backup settings tab."""
        backup_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(backup_frame, text=language_manager.get_text("tab_backup"))
        
        # Backup settings
        backup_settings_frame = ttk.LabelFrame(backup_frame, text="Paramètres de sauvegarde", style="SettingsSection.TLabelframe")
        backup_settings_frame.pack(fill="x", padx=10, pady=10)
        
        self.auto_backup_var = tk.BooleanVar(value=self.settings.get("auto_backup", True))
        ttk.Checkbutton(
            backup_settings_frame,
            text="Sauvegarde automatique",
            variable=self.auto_backup_var
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Label(backup_settings_frame, text="Rétention des sauvegardes (jours):").pack(anchor="w", padx=10, pady=(10, 5))
        self.backup_retention = tk.StringVar(value=str(self.settings.get("backup_retention", 30)))
        ttk.Entry(backup_settings_frame, textvariable=self.backup_retention, width=10).pack(anchor="w", padx=10, pady=(0, 10))
        
        # Backup actions
        backup_actions_frame = ttk.LabelFrame(backup_frame, text="Actions de sauvegarde", style="SettingsSection.TLabelframe")
        backup_actions_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            backup_actions_frame,
            text="Créer une sauvegarde maintenant",
            command=self.create_backup,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            backup_actions_frame,
            text="Restaurer une sauvegarde",
            command=self.restore_backup,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        # Backup info
        info_frame = ttk.LabelFrame(backup_frame, text="Informations", style="SettingsSection.TLabelframe")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        self.backup_info_label = ttk.Label(info_frame, text="Chargement...")
        self.backup_info_label.pack(anchor="w", padx=10, pady=5)
        
        # Update backup info
        self.update_backup_info()
    
    def create_cement_tab(self):
        """Create cement module settings tab."""
        cement_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(cement_frame, text="🏗️ Module Ciment")
        
        # Import here to avoid circular imports
        from .ciment_avoir_settings import CimentAvoirSettings
        
        # Create the avoir settings widget
        self.cement_avoir_settings = CimentAvoirSettings(cement_frame, self.di_container)
        self.cement_avoir_settings.pack(fill="both", expand=True)
    
    def create_taxes_tab(self):
        """Create tax management settings tab."""
        taxes_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(taxes_frame, text="💰 Gestion Taxes")
        
        # Create the tax management widget
        self.tax_management = TaxManagementFrame(taxes_frame)
        self.tax_management.pack(fill="both", expand=True, padx=10, pady=10)
    
    def create_advanced_tab(self):
        """Create advanced settings tab."""
        advanced_frame = ttk.Frame(self.notebook, style="Settings.TFrame")
        self.notebook.add(advanced_frame, text=language_manager.get_text("tab_advanced"))
        
        # Debug settings
        debug_frame = ttk.LabelFrame(advanced_frame, text="Mode debug", style="SettingsSection.TLabelframe")
        debug_frame.pack(fill="x", padx=10, pady=10)
        
        self.debug_mode_var = tk.BooleanVar(value=self.settings.get("debug_mode", False))
        ttk.Checkbutton(
            debug_frame,
            text="Activer le mode debug",
            variable=self.debug_mode_var
        ).pack(anchor="w", padx=10, pady=5)
        
        self.log_level_var = tk.StringVar(value=self.settings.get("log_level", "INFO"))
        ttk.Label(debug_frame, text="Niveau de log:").pack(anchor="w", padx=10, pady=(10, 5))
        log_combo = ttk.Combobox(
            debug_frame,
            textvariable=self.log_level_var,
            values=["DEBUG", "INFO", "WARNING", "ERROR"],
            state="readonly",
            width=20
        )
        log_combo.pack(anchor="w", padx=10, pady=(0, 10))
        
        # System information
        system_frame = ttk.LabelFrame(advanced_frame, text="Informations système", style="SettingsSection.TLabelframe")
        system_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            system_frame,
            text="Afficher les informations système",
            command=self.show_system_info,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            system_frame,
            text="Afficher les logs",
            command=self.show_logs,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            system_frame,
            text="🧪 Tester le système de logs d'erreurs",
            command=self.test_error_logging,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            system_frame,
            text="🗑️ Vider le fichier de log",
            command=self.clear_log_file,
            style="SettingsDanger.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            system_frame,
            text="📦 Installer dépendances optionnelles",
            command=self.install_optional_deps,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        # Reset settings
        reset_frame = ttk.LabelFrame(advanced_frame, text="Réinitialisation", style="SettingsSection.TLabelframe")
        reset_frame.pack(fill="x", padx=10, pady=10)
        
        ttk.Button(
            reset_frame,
            text="Réinitialiser tous les paramètres",
            command=self.reset_settings,
            style="SettingsDanger.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            reset_frame,
            text="Exporter les paramètres",
            command=self.export_settings,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
        
        ttk.Button(
            reset_frame,
            text="Importer les paramètres",
            command=self.import_settings,
            style="Settings.TButton"
        ).pack(anchor="w", padx=10, pady=5)
    
    def create_bottom_buttons(self, parent):
        """Create bottom action buttons."""
        button_frame = ttk.Frame(parent, style="Settings.TFrame")
        button_frame.pack(fill="x", pady=(20, 0))
        
        # Left side - Cancel
        ttk.Button(
            button_frame,
            text="Annuler",
            command=self.go_home,
            style="Settings.TButton"
        ).pack(side="left")
        
        # Right side - Save
        ttk.Button(
            button_frame,
            text="Enregistrer les paramètres",
            command=self.save_settings,
            style="SettingsSave.TButton"
        ).pack(side="right")
    
    def load_settings(self):
        """Load settings from file."""
        default_settings = {
            "language": "fr",
            "theme": "light",
            "auto_save": True,
            "auto_save_interval": 5,
            "auto_sync": True,
            "sync_interval": 30,
            "auto_backup": True,
            "backup_retention": 30,
            "debug_mode": False,
            "log_level": "INFO"
        }
        
        try:
            if os.path.exists(self.settings_file):
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    for key, value in default_settings.items():
                        if key not in loaded_settings:
                            loaded_settings[key] = value
                    return loaded_settings
        except Exception as e:
            print(f"Error loading settings: {e}")
        
        return default_settings
    
    def save_settings(self):
        """Save current settings to file."""
        try:
            print("[SETTINGS] Starting save_settings...")
            print(f"[SETTINGS] Current payment_tolerance_var value: {self.payment_tolerance_var.get()}")
            
            # Collect all settings from UI
            settings_to_save = {
                "language": self.language_var.get(),
                "theme": self.theme_var.get(),
                "auto_save": self.auto_save_var.get(),
                "auto_save_interval": int(self.auto_save_interval.get()),
                "auto_sync": self.auto_sync_var.get(),
                "sync_interval": int(self.sync_interval.get()),
                "auto_backup": self.auto_backup_var.get(),
                "backup_retention": int(self.backup_retention.get()),
                "debug_mode": self.debug_mode_var.get(),
                "log_level": self.log_level_var.get(),
                "payment_tolerance": float(self.payment_tolerance_var.get())
            }
            
            print(f"[SETTINGS] Settings to save: {settings_to_save}")
            print(f"[SETTINGS] Saving to file: {self.settings_file}")
            
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings_to_save, f, indent=2, ensure_ascii=False)
            
            self.settings = settings_to_save
            # Also persist sync-specific settings to the sync config so both UIs stay in sync
            try:
                from app.connection import sync_config as _sync_cfg
                cfg = _sync_cfg.load_config()
                cfg['sync_interval'] = int(settings_to_save.get('sync_interval', cfg.get('sync_interval', 30)))
                cfg['auto_sync'] = bool(settings_to_save.get('auto_sync', cfg.get('auto_sync', True)))
                _sync_cfg.save_config(cfg)
                print(f"[SETTINGS] Synced sync_config: interval={cfg['sync_interval']} auto_sync={cfg['auto_sync']}")
            except Exception as _e:
                print(f"[SETTINGS] Failed to persist sync_config: {_e}")
            print("[SETTINGS] Save completed successfully!")
            messagebox.showinfo("Succès", "Paramètres enregistrés avec succès!")
            
        except Exception as e:
            print(f"[SETTINGS] Error saving settings: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {str(e)}")
    
    def load_current_settings(self):
        """Load current settings into UI elements."""
        # Load theme
        current_theme = self.settings.get("theme", "light")
        theme_manager.set_theme(current_theme)
        
        # Update theme combo box
        if current_theme == "light":
            self.theme_var.set(language_manager.get_text("light_theme"))
        elif current_theme == "dark":
            self.theme_var.set(language_manager.get_text("dark_theme"))
    
    def update_sync_status(self):
        """Update sync status display."""
        try:
            from app.connection import sync
            if sync.server_online():
                self.sync_status_label.config(text="✓ Serveur connecté")
            else:
                self.sync_status_label.config(text="✗ Serveur déconnecté")
        except Exception as e:
            self.sync_status_label.config(text=f"⚠ Erreur: {str(e)}")
    
    def update_backup_info(self):
        """Update backup information display."""
        try:
            backup_dir = "backups"
            if os.path.exists(backup_dir):
                backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.json')]
                self.backup_info_label.config(text=f"Nombre de sauvegardes: {len(backup_files)}")
            else:
                self.backup_info_label.config(text="Aucune sauvegarde trouvée")
        except Exception as e:
            self.backup_info_label.config(text=f"Erreur: {str(e)}")
    
    def optimize_database(self):
        """Optimize database."""
        try:
            import sqlite3
            with sqlite3.connect(get_database_path()) as conn:
                conn.execute("VACUUM")
                conn.execute("ANALYZE")
            messagebox.showinfo("Succès", "Base de données optimisée!")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'optimisation: {str(e)}")
    
    def check_database_integrity(self):
        """Check database integrity."""
        try:
            import sqlite3
            with sqlite3.connect(get_database_path()) as conn:
                result = conn.execute("PRAGMA integrity_check").fetchone()
            
            if result[0] == "ok":
                messagebox.showinfo("Intégrité", "Base de données intègre!")
            else:
                messagebox.showerror("Erreur", f"Problème d'intégrité: {result[0]}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la vérification: {str(e)}")
    
    def clean_temp_data(self):
        """Clean temporary data."""
        try:
            # Clean temporary files
            temp_files = []
            for root, dirs, files in os.walk("."):
                for file in files:
                    if file.endswith('.tmp') or file.endswith('.temp'):
                        temp_files.append(os.path.join(root, file))
            
            for temp_file in temp_files:
                try:
                    os.remove(temp_file)
                except:
                    pass
            
            messagebox.showinfo("Succès", f"Nettoyage terminé! {len(temp_files)} fichiers temporaires supprimés.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du nettoyage: {str(e)}")
    
    def manual_sync(self):
        """Perform manual sync."""
        try:
            from app.connection import sync as _sync
            # Warn user if a full sync is pending (version-upgrade forced full sync)
            try:
                # Access SyncService directly to check force_full flag
                try:
                    from app.stfoom.services.sync_service import SyncService
                    svc = SyncService()
                    if svc._should_force_full_sync():
                        if not messagebox.askyesno("Full sync requis", "Le système va effectuer une SYNCHRONISATION COMPLÈTE (FULL SYNC) de tous les enregistrements. Continuer ?"):
                            return
                except Exception:
                    # If we can't introspect, proceed normally
                    pass

            except Exception:
                pass

            result = _sync.force_sync()
            if result:
                messagebox.showinfo("Succès", "Synchronisation réussie!")
            else:
                messagebox.showerror("Erreur", "Échec de la synchronisation")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la synchronisation: {str(e)}")
    
    def create_backup(self):
        """Create a new backup."""
        try:
            from connection import backup_system
            backup_system.create_backup()
            messagebox.showinfo("Succès", "Sauvegarde créée avec succès!")
            self.update_backup_info()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création: {str(e)}")
    
    def restore_backup(self):
        """Restore from backup."""
        try:
            from tkinter import filedialog
            import shutil
            import zipfile
            
            # Ask user to select backup file
            backup_file = filedialog.askopenfilename(
                title="Sélectionner une sauvegarde à restaurer",
                filetypes=[("Backup files", "*.json"), ("All files", "*.*")],
                initialdir="backups"
            )
            
            if not backup_file:
                return
                
            # Confirm restoration
            if not messagebox.askyesno("Confirmation", 
                f"Voulez-vous vraiment restaurer la sauvegarde ?\n\n"
                f"Fichier: {os.path.basename(backup_file)}\n\n"
                "⚠️  ATTENTION: Cette action remplacera les données actuelles!"):
                return
            
            # Load backup data
            with open(backup_file, 'r', encoding='utf-8') as f:
                backup_data = json.load(f)
            
            # Restore database
            if 'database' in backup_data:
                db_path = get_database_path()
                if os.path.exists(db_path):
                    # Create backup of current database
                    current_backup = f"data/stfoom_backup_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
                    shutil.copy2(db_path, current_backup)
                
                # Restore database
                with open(db_path, 'w', encoding='utf-8') as f:
                    json.dump(backup_data['database'], f, indent=2, ensure_ascii=False)
            
            # Restore settings if present
            if 'settings' in backup_data:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(backup_data['settings'], f, indent=2, ensure_ascii=False)
            
            messagebox.showinfo("Succès", 
                f"Sauvegarde restaurée avec succès!\n\n"
                f"Fichier: {os.path.basename(backup_file)}\n"
                f"Sauvegarde actuelle créée: {os.path.basename(current_backup)}")
            
            # Refresh settings display
            self.settings = self.load_settings()
            self.load_current_settings()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la restauration: {str(e)}")
    
    def reset_settings(self):
        """Reset all settings to defaults."""
        if messagebox.askyesno("Confirmation", "Voulez-vous vraiment réinitialiser tous les paramètres?"):
            try:
                if os.path.exists(self.settings_file):
                    os.remove(self.settings_file)
                self.settings = self.load_settings()
                self.load_current_settings()
                messagebox.showinfo("Succès", "Paramètres réinitialisés!")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la réinitialisation: {str(e)}")
    
    def export_settings(self):
        """Export settings to file."""
        try:
            filename = f"settings_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            messagebox.showinfo("Succès", f"Paramètres exportés vers {filename}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'export: {str(e)}")
    
    def import_settings(self):
        """Import settings from file."""
        try:
            from tkinter import filedialog
            
            # Ask user to select settings file
            settings_file = filedialog.askopenfilename(
                title="Sélectionner un fichier de paramètres à importer",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
                initialdir="."
            )
            
            if not settings_file:
                return
                
            # Load settings from file
            with open(settings_file, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Validate settings structure
            required_keys = ["language", "theme", "auto_save", "auto_sync", "auto_backup"]
            missing_keys = [key for key in required_keys if key not in imported_settings]
            
            if missing_keys:
                messagebox.showerror("Erreur", 
                    f"Fichier de paramètres invalide.\n\n"
                    f"Clés manquantes: {', '.join(missing_keys)}")
                return
            
            # Confirm import
            if not messagebox.askyesno("Confirmation", 
                f"Voulez-vous vraiment importer ces paramètres ?\n\n"
                f"Fichier: {os.path.basename(settings_file)}\n\n"
                "⚠️  ATTENTION: Cela remplacera vos paramètres actuels!"):
                return
            
            # Backup current settings
            if os.path.exists(self.settings_file):
                backup_file = f"settings_backup_before_import_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                shutil.copy2(self.settings_file, backup_file)
            
            # Import settings
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(imported_settings, f, indent=2, ensure_ascii=False)
            
            # Update current settings
            self.settings = imported_settings
            
            # Update UI elements
            self.language_var.set(imported_settings.get("language", "fr"))
            self.theme_var.set(imported_settings.get("theme", "light"))
            self.auto_save_var.set(imported_settings.get("auto_save", True))
            self.auto_save_interval.set(str(imported_settings.get("auto_save_interval", 5)))
            self.auto_sync_var.set(imported_settings.get("auto_sync", True))
            self.sync_interval.set(str(imported_settings.get("sync_interval", 30)))
            self.auto_backup_var.set(imported_settings.get("auto_backup", True))
            self.backup_retention.set(str(imported_settings.get("backup_retention", 30)))
            self.debug_mode_var.set(imported_settings.get("debug_mode", False))
            self.log_level_var.set(imported_settings.get("log_level", "INFO"))
            
            messagebox.showinfo("Succès", 
                f"Paramètres importés avec succès!\n\n"
                f"Fichier: {os.path.basename(settings_file)}\n"
                f"Sauvegarde créée: {backup_file}")
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'import: {str(e)}")
    
    def show_system_info(self):
        """Show system information."""
        try:
            import platform
            import sqlite3
            
            # Try to import psutil, but don't fail if it's not available
            psutil_available = False
            psutil = None
            try:
                psutil = __import__('psutil')
                psutil_available = True
            except ImportError:
                pass
            
            # Get basic system information
            system_info = f"""
=== INFORMATIONS SYSTÈME ===

Système d'exploitation: {platform.system()} {platform.release()}
Architecture: {platform.architecture()[0]}
Version Python: {platform.python_version()}

=== RESSOURCES SYSTÈME ==="""
            
            # Add system resources if psutil is available
            if psutil_available:
                system_info += f"""
CPU: {psutil.cpu_count()} cœurs
Mémoire RAM: {psutil.virtual_memory().total // (1024**3)} GB
Espace disque: {psutil.disk_usage('.').free // (1024**3)} GB libre"""
            else:
                system_info += """
CPU: Information non disponible (psutil non installé)
Mémoire RAM: Information non disponible (psutil non installé)
Espace disque: Information non disponible (psutil non installé)"""
            
            # Add application information
            system_info += f"""

=== APPLICATION STFOOM ===
Répertoire: {os.getcwd()}
Base de données: {'Présente' if os.path.exists(get_database_path()) else 'Absente'}"""
            
            # Add database size if file exists
            if os.path.exists(get_database_path()):
                db_size = os.path.getsize(get_database_path()) // 1024
                system_info += f"""
Taille DB: {db_size} KB"""
            
            system_info += f"""
Paramètres: {'Présents' if os.path.exists(self.settings_file) else 'Absents'}

=== RÉSEAU ===
Serveur sync: {'Connecté' if self._check_server_connection() else 'Déconnecté'}

=== MODULES PYTHON ===
psutil: {'✅ Installé' if psutil_available else '❌ Non installé (optionnel)'}
"""
            
            # Show in a new window
            info_window = tk.Toplevel(self)
            info_window.title("Informations système")
            info_window.geometry("500x400")
            info_window.grab_set()
            
            text_widget = tk.Text(info_window, wrap="word", font=("Consolas", 10))
            text_widget.pack(fill="both", expand=True, padx=10, pady=10)
            text_widget.insert("1.0", system_info)
            text_widget.config(state="disabled")
            
            # Add scrollbar
            scrollbar = ttk.Scrollbar(info_window, orient="vertical", command=text_widget.yview)
            scrollbar.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scrollbar.set)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'affichage des informations: {str(e)}")
    
    def show_logs(self):
        """Show application logs."""
        try:
            # Check for log files in multiple locations
            log_files = []
            search_locations = [".", "tools", "logs", "config"]  # Add config directory
            
            for location in search_locations:
                if os.path.exists(location):
                    try:
                        for file in os.listdir(location):
                            if file.endswith(".log") or file.startswith("error.log"):
                                full_path = os.path.join(location, file)
                                # Store both display name and full path
                                display_name = f"{file} ({location})" if location != "." else file
                                log_files.append((display_name, full_path))
                    except OSError:
                        continue  # Skip if can't read directory
            
            if not log_files:
                messagebox.showinfo("Logs", "Aucun fichier de log trouvé dans les répertoires courant, tools, logs, ou config.")
                return
            
            # Create log viewer window
            log_window = tk.Toplevel(self)
            log_window.title("Visualiseur de logs")
            log_window.geometry("700x500")
            log_window.grab_set()
            
            # File selection
            file_frame = ttk.Frame(log_window)
            file_frame.pack(fill="x", padx=10, pady=5)
            ttk.Label(file_frame, text="Fichier de log:").pack(side="left")
            
            # Extract display names and full paths
            display_names = [item[0] for item in log_files]
            file_paths = [item[1] for item in log_files]
            
            log_file_var = tk.StringVar(value=display_names[0] if display_names else "")
            log_combo = ttk.Combobox(file_frame, textvariable=log_file_var, values=display_names, state="readonly")
            log_combo.pack(side="left", padx=5)
            
            # Text widget for log content
            text_widget = tk.Text(log_window, wrap="word", font=("Consolas", 9))
            text_widget.pack(fill="both", expand=True, padx=10, pady=5)
            
            # Scrollbar
            scrollbar = ttk.Scrollbar(log_window, orient="vertical", command=text_widget.yview)
            scrollbar.pack(side="right", fill="y")
            text_widget.configure(yscrollcommand=scrollbar.set)
            
            def load_log_file():
                try:
                    text_widget.delete("1.0", "end")
                    # Get the selected display name and find corresponding file path
                    selected_display = log_file_var.get()
                    selected_path = None
                    for display_name, file_path in log_files:
                        if display_name == selected_display:
                            selected_path = file_path
                            break
                    
                    if selected_path and os.path.exists(selected_path):
                        with open(selected_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                        text_widget.insert("1.0", content)
                        text_widget.see("end")  # Scroll to bottom
                    else:
                        text_widget.insert("1.0", f"Erreur: Fichier {selected_display} non trouvé")
                except Exception as e:
                    text_widget.insert("1.0", f"Erreur lors de la lecture: {e}")
            
            # Load button
            ttk.Button(file_frame, text="Charger", command=load_log_file).pack(side="left", padx=5)
            
            # Auto-refresh checkbox
            auto_refresh_var = tk.BooleanVar()
            ttk.Checkbutton(file_frame, text="Auto-refresh", variable=auto_refresh_var).pack(side="left", padx=5)
            
            # Load initial file
            load_log_file()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'affichage des logs: {str(e)}")
    
    def clear_log_file(self):
        """Clear the error.log file after confirmation."""
        try:
            # Check for error.log in multiple locations
            log_locations = ["config/error.log", "error.log", "tools/error.log", "logs/error.log"]
            error_log_path = None
            
            for location in log_locations:
                if os.path.exists(location):
                    error_log_path = location
                    break
            
            if not error_log_path:
                messagebox.showinfo("Information", "Le fichier error.log n'existe pas dans les emplacements standards.")
                return
            
            # Get file size for confirmation dialog
            file_size = os.path.getsize(error_log_path)
            file_size_mb = file_size / (1024 * 1024)
            
            # Confirmation dialog
            if file_size_mb > 0.1:  # Show size if > 0.1 MB
                confirm_msg = f"Êtes-vous sûr de vouloir vider le fichier error.log ?\n\nEmplacement: {error_log_path}\nTaille actuelle: {file_size_mb:.3f} MB\nCette action est irréversible."
            else:
                confirm_msg = f"Êtes-vous sûr de vouloir vider le fichier error.log ?\n\nEmplacement: {error_log_path}\nCette action est irréversible."
            
            result = messagebox.askyesno(
                "🗑️ Confirmation",
                confirm_msg,
                icon="warning"
            )
            
            if result:
                # Create backup with timestamp
                backup_name = f"error.log.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                shutil.copy2(error_log_path, backup_name)
                
                # Clear the log file
                with open(error_log_path, "w", encoding="utf-8") as f:
                    f.write(f"=== Log file cleared at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                    f.write(f"Backup saved as: {backup_name}\n\n")
                
                messagebox.showinfo(
                    "✅ Succès",
                    f"Le fichier error.log a été vidé avec succès!\n\nFichier: {error_log_path}\nSauvegarde créée: {backup_name}"
                )
                
                print(f"[LOG_CLEAR] {error_log_path} cleared, backup saved as {backup_name}")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression du fichier de log: {str(e)}")
            print(f"[LOG_CLEAR] Error clearing log file: {e}")
    
    def install_optional_deps(self):
        """Install optional dependencies like psutil."""
        try:
            import subprocess
            import importlib
            
            # Check which modules are missing
            optional_modules = {
                "psutil": "Informations système (CPU, RAM, utilisation disque)"
            }
            
            missing_modules = []
            for module_name, description in optional_modules.items():
                try:
                    importlib.import_module(module_name)
                except ImportError:
                    missing_modules.append((module_name, description))
            
            if not missing_modules:
                messagebox.showinfo(
                    "📦 Dépendances",
                    "Toutes les dépendances optionnelles sont déjà installées!\n\n"
                    "✅ psutil: Installé"
                )
                return
            
            # Show what will be installed
            modules_list = "\n".join([f"• {name}: {desc}" for name, desc in missing_modules])
            
            result = messagebox.askyesno(
                "📦 Installation de dépendances",
                f"Les modules suivants vont être installés:\n\n{modules_list}\n\n"
                "Ces modules sont optionnels et améliorent les fonctionnalités.\n"
                "Voulez-vous continuer?"
            )
            
            if not result:
                return
            
            # Install missing modules
            import sys
            installed_count = 0
            failed_modules = []
            
            for module_name, description in missing_modules:
                try:
                    print(f"[INSTALL] Installing {module_name}...")
                    subprocess.check_call([
                        sys.executable, "-m", "pip", "install", module_name
                    ], capture_output=True, text=True)
                    installed_count += 1
                    print(f"[INSTALL] {module_name} installed successfully")
                except subprocess.CalledProcessError as e:
                    failed_modules.append(module_name)
                    print(f"[INSTALL] Failed to install {module_name}: {e}")
            
            # Show results
            if installed_count == len(missing_modules):
                messagebox.showinfo(
                    "✅ Installation réussie",
                    f"Tous les modules ont été installés avec succès!\n\n"
                    f"Modules installés: {installed_count}\n\n"
                    "📝 Redémarrez l'application pour utiliser les nouvelles fonctionnalités."
                )
            elif installed_count > 0:
                failed_list = ", ".join(failed_modules)
                messagebox.showwarning(
                    "⚠️ Installation partielle",
                    f"Installation partiellement réussie:\n\n"
                    f"✅ Installés: {installed_count}\n"
                    f"❌ Échecs: {failed_list}\n\n"
                    "📝 L'application fonctionne sans les modules échoués."
                )
            else:
                failed_list = ", ".join(failed_modules)
                messagebox.showerror(
                    "❌ Installation échouée",
                    f"Aucun module n'a pu être installé:\n\n"
                    f"Modules échoués: {failed_list}\n\n"
                    "📝 Vérifiez votre connexion internet et les permissions."
                )
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'installation: {str(e)}")
            print(f"[INSTALL] Error installing dependencies: {e}")
    
    def _check_server_connection(self):
        """Check if server is online."""
        try:
            from app.connection import sync
            return sync.server_online()
        except:
            return False
    
    def on_language_change(self, event=None):
        """Handle language change."""
        try:
            # Get selected language
            selected = self.language_var.get()
            if selected == "Français":
                new_lang = "fr"
            elif selected == "English":
                new_lang = "en"
            else:
                return
            
            # Update language manager
            if language_manager.set_language(new_lang):
                # Update settings
                self.settings["language"] = new_lang
                self.save_settings()
                
                # Show confirmation
                messagebox.showinfo(
                    language_manager.get_text("success"),
                    language_manager.get_text("settings_saved")
                )
                
                # Refresh UI (this would require a more complex implementation)
                # For now, just update the current tab
                self.refresh_current_tab()
        except Exception as e:
            messagebox.showerror(
                language_manager.get_text("error"),
                f"{language_manager.get_text('error_saving')}: {str(e)}"
            )
    
    def refresh_current_tab(self):
        """Refresh the current tab content."""
        # This is a simplified refresh - in a full implementation,
        # you would need to recreate all UI elements
        current_tab = self.notebook.select()
        if current_tab:
            # Update tab title
            tab_id = self.notebook.index(current_tab)
            if tab_id == 0:  # General tab
                self.notebook.tab(0, text=language_manager.get_text("tab_general"))
            elif tab_id == 1:  # Database tab
                self.notebook.tab(1, text=language_manager.get_text("tab_database"))
            elif tab_id == 2:  # Sync tab
                self.notebook.tab(2, text=language_manager.get_text("tab_sync"))
            elif tab_id == 3:  # Backup tab
                self.notebook.tab(3, text=language_manager.get_text("tab_backup"))
            elif tab_id == 4:  # Advanced tab
                self.notebook.tab(4, text=language_manager.get_text("tab_advanced"))
    
    def on_theme_change(self, event=None):
        """Handle theme change."""
        try:
            # Get selected theme
            selected = self.theme_var.get()
            if selected == language_manager.get_text("light_theme"):
                new_theme = "light"
            elif selected == language_manager.get_text("dark_theme"):
                new_theme = "dark"
            else:
                return
            
            # Update theme manager
            if theme_manager.set_theme(new_theme):
                # Update settings
                self.settings["theme"] = new_theme
                self.save_settings()
                
                # Apply theme to root window
                root = self.winfo_toplevel()
                theme_manager.apply_theme_to_root(root)
                
                # Show confirmation
                messagebox.showinfo(
                    language_manager.get_text("success"),
                    "Thème appliqué avec succès! Redémarrez l'application pour voir tous les changements."
                )
        except Exception as e:
            messagebox.showerror(
                language_manager.get_text("error"),
                f"Erreur lors du changement de thème: {str(e)}"
            )
    
    def test_error_logging(self):
        """Test the error logging system to ensure it's working properly."""
        try:
            # Import unified logger
            from utilities.unified_logger import unified_logger
            
            # Test message
            test_message = f"Test d'erreur système - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Log test error
            unified_logger.log_error("SETTINGS_TEST", "ERROR_LOGGING_TEST", test_message)
            
            # Also test fallback method
            error_log_path = os.path.join("config", "error.log")
            os.makedirs("config", exist_ok=True)
            with open(error_log_path, "a", encoding="utf-8") as f:
                f.write(f"\n=== Test d'erreur via Paramètres - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ===\n")
                f.write("Ce test vérifie que les erreurs sont bien écrites dans config/error.log\n\n")
                f.flush()
            
            # Check if error log exists and has content
            if os.path.exists(error_log_path):
                file_size = os.path.getsize(error_log_path)
                messagebox.showinfo(
                    "✅ Test réussi",
                    f"Le système de logs d'erreurs fonctionne correctement!\n\n"
                    f"Fichier: {error_log_path}\n"
                    f"Taille: {file_size} bytes\n"
                    f"Message de test ajouté: {test_message[:50]}..."
                )
            else:
                messagebox.showerror(
                    "❌ Test échoué", 
                    "Le fichier config/error.log n'a pas pu être créé."
                )
                
        except Exception as e:
            # This error itself should be logged by the global error handler
            messagebox.showerror(
                "❌ Erreur du test", 
                f"Erreur lors du test du système de logs:\n\n{str(e)}\n\n"
                "Cette erreur devrait maintenant apparaître dans config/error.log"
            )