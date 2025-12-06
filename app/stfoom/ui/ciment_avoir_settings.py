#!/usr/bin/env python3
"""
Cement Module Settings UI - Avoir Configuration
"""

import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from app.core.path_manager import get_db_path

class SimpleSettingsManager:
    """Simple settings manager for direct database access"""
    
    def get_setting(self, key, default="0.0"):
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else default
        except:
            return default
    
    def set_setting(self, key, value):
        try:
            conn = sqlite3.connect(get_db_path())
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value, description, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ''', (key, str(value), "Carthage cement avoir setting"))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error saving setting: {e}")
            return False

class CimentAvoirSettings(ttk.Frame):
    """Cement Avoir Settings Interface"""
    
    def __init__(self, parent, di_container=None):
        super().__init__(parent)
        self.di_container = di_container
        
        # Use simple settings manager for direct database access
        self.settings_manager = SimpleSettingsManager()
                
        self.setup_ui()
        self.load_avoir_config()
    
    def setup_ui(self):
        """Setup the UI components"""
        # Title
        title_label = ttk.Label(self, text="Configuration Avoir - Module Ciment", 
                               font=("Segoe UI", 14, "bold"))
        title_label.pack(pady=(10, 20))
        
        # Description
        desc_label = ttk.Label(self, text="Configurez les taux d'avoir pour différents types de conditions:",
                              font=("Segoe UI", 10))
        desc_label.pack(pady=(0, 15))
        
        # Main frame for avoir configurations
        main_frame = ttk.LabelFrame(self, text="Types d'Avoir", padding=20)
        main_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Avoir types configuration
        self.entries = {}
        
        # 1. Payment before 20 days
        self.create_avoir_row(main_frame, "payment_before_20_days", 
                             "Paiement avant 20 jours", "DA/tonne", 0)
        
        # 2. Total factures 200T/month
        self.create_avoir_row(main_frame, "total_factures_200t_month", 
                             "Total factures 200 tonnes/mois", "DA/tonne", 1)
        
        # 3. Sur livraison
        self.create_avoir_row(main_frame, "sur_livraison", 
                             "Sur livraison", "DA/tonne", 2)
        
        # 4. Par année
        self.create_avoir_row(main_frame, "par_annee", 
                             "Par année", "DA/BL", 3)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        # Save button
        save_btn = ttk.Button(buttons_frame, text="💾 Sauvegarder", 
                             command=self.save_config, style="Accent.TButton")
        save_btn.pack(side="left", padx=(0, 10))
        
        # Reset button
        reset_btn = ttk.Button(buttons_frame, text="🔄 Réinitialiser", 
                              command=self.reset_config)
        reset_btn.pack(side="left")
        
        # Info frame
        info_frame = ttk.LabelFrame(self, text="Information", padding=10)
        info_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        info_text = """
📋 Comment ça marche:
• Les types "Paiement avant 20 jours" et "Total factures 200T/mois" sont cochés par défaut
• Vous pouvez modifier les taux ici et ils s'appliqueront automatiquement
• Les calculs se font par tonne: Quantité × Taux = Avoir
• Les avoirs s'additionnent selon les types sélectionnés pour chaque BL
        """
        
        info_label = ttk.Label(info_frame, text=info_text, font=("Segoe UI", 9))
        info_label.pack(anchor="w")
    
    def create_avoir_row(self, parent, avoir_type, label_text, unit, row):
        """Create a row for avoir configuration"""
        # Create frame for this row
        row_frame = ttk.Frame(parent)
        row_frame.grid(row=row, column=0, columnspan=3, sticky="ew", pady=8)
        parent.grid_columnconfigure(0, weight=1)
        
        # Label
        label = ttk.Label(row_frame, text=f"{label_text}:", font=("Segoe UI", 10, "bold"))
        label.grid(row=0, column=0, sticky="w", padx=(0, 10))
        
        # Entry for rate
        entry_frame = ttk.Frame(row_frame)
        entry_frame.grid(row=0, column=1, sticky="w")
        
        entry = ttk.Entry(entry_frame, width=12, font=("Segoe UI", 10))
        entry.grid(row=0, column=0, padx=(0, 5))
        
        unit_label = ttk.Label(entry_frame, text=unit, font=("Segoe UI", 10))
        unit_label.grid(row=0, column=1)
        
        # Store entry reference
        self.entries[avoir_type] = entry
        
        # Default indicator for payment and total factures
        if avoir_type in ["payment_before_20_days", "total_factures_200t_month"]:
            default_label = ttk.Label(row_frame, text="(Par défaut)", 
                                    font=("Segoe UI", 9, "italic"), 
                                    foreground="green")
            default_label.grid(row=0, column=2, sticky="w", padx=(10, 0))
    
    def load_avoir_config(self):
        """Load current avoir configuration from database"""
        try:
            # Map UI keys to database keys
            key_mapping = {
                "payment_before_20_days": "carthage_cement_avoir_payment_before_20_days",
                "total_factures_200t_month": "carthage_cement_avoir_total_factures_200t_month", 
                "sur_livraison": "carthage_cement_avoir_sur_livraison",
                "par_annee": "carthage_cement_avoir_par_annee"
            }
            
            for ui_key, db_key in key_mapping.items():
                if ui_key in self.entries:
                    value = self.settings_manager.get_setting(db_key, "0.0")
                    self.entries[ui_key].delete(0, tk.END)
                    self.entries[ui_key].insert(0, str(value))
                    
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement: {e}")
            # Set default values if load fails
            for entry in self.entries.values():
                entry.delete(0, tk.END)
                entry.insert(0, "0.0")
    
    def save_config(self):
        """Save avoir configuration to database"""
        try:
            # Map UI keys to database keys
            key_mapping = {
                "payment_before_20_days": "carthage_cement_avoir_payment_before_20_days",
                "total_factures_200t_month": "carthage_cement_avoir_total_factures_200t_month", 
                "sur_livraison": "carthage_cement_avoir_sur_livraison",
                "par_annee": "carthage_cement_avoir_par_annee"
            }
            
            success_count = 0
            
            for ui_key, db_key in key_mapping.items():
                if ui_key in self.entries:
                    try:
                        rate = float(self.entries[ui_key].get() or "0.0")
                        if self.settings_manager.set_setting(db_key, str(rate)):
                            success_count += 1
                        else:
                            messagebox.showerror("Erreur", f"Échec de sauvegarde pour {ui_key}")
                            return
                    except ValueError:
                        messagebox.showerror("Erreur", f"Valeur invalide pour {ui_key}")
                        return
            
            if success_count == len(key_mapping):
                messagebox.showinfo("Succès", "✅ Configuration sauvegardée avec succès!\n\nLes nouveaux taux d'avoir sont maintenant disponibles pour les calculs.")
            else:
                messagebox.showwarning("Attention", "Certaines configurations n'ont pas pu être sauvegardées")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def reset_config(self):
        """Reset to default configuration"""
        if messagebox.askyesno("Confirmation", 
                              "Êtes-vous sûr de vouloir réinitialiser la configuration?"):
            # Reset to defaults
            defaults = {
                "payment_before_20_days": 6.545,
                "total_factures_200t_month": 0.0,
                "sur_livraison": 0.0,
                "par_annee": 0.0
            }
            
            for avoir_type, default_value in defaults.items():
                if avoir_type in self.entries:
                    self.entries[avoir_type].delete(0, tk.END)
                    self.entries[avoir_type].insert(0, str(default_value))
            
            messagebox.showinfo("Info", "Configuration réinitialisée aux valeurs par défaut")
