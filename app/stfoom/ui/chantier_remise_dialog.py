"""
Chantier Remise Dialog - UI for managing chantier-based discounts and specific prices
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Dict, List
import sys
import os

# Add app to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from stfoom.services.chantier_remise_service import ChantierRemiseService

class ChantierRemiseDialog:
    """Dialog for managing chantier remises and specific prices"""
    
    def __init__(self, parent, client_data=None, refresh_callback=None):
        self.parent = parent
        self.client_data = client_data
        self.chantier_service = ChantierRemiseService()
        self.dialog = None
        self.current_chantier = None
        self.product_entries = {}
        self.refresh_callback = refresh_callback
        
    def show(self):
        """Show the dialog"""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Gestion des Remises par Chantier")
        self.dialog.geometry("800x600")
        self.dialog.configure(bg='white')
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        self._create_widgets()
        self._load_chantiers()
        
        # Center the dialog
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() - self.dialog.winfo_width()) // 2
        y = (self.dialog.winfo_screenheight() - self.dialog.winfo_height()) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
    def _create_widgets(self):
        """Create the dialog widgets"""
        main_frame = ttk.Frame(self.dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Gestion des Remises par Chantier", 
                              font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Chantier selection frame
        chantier_frame = ttk.LabelFrame(main_frame, text="Sélection du Chantier", padding=10)
        chantier_frame.pack(fill="x", pady=(0, 20))
        
        # Chantier dropdown
        ttk.Label(chantier_frame, text="Chantier:").pack(side="left")
        self.chantier_var = tk.StringVar()
        self.chantier_combo = ttk.Combobox(chantier_frame, textvariable=self.chantier_var, width=40)
        self.chantier_combo.pack(side="left", padx=(10, 0))
        self.chantier_combo.bind("<<ComboboxSelected>>", self._on_chantier_selected)
        
        # New chantier button
        new_btn = ttk.Button(chantier_frame, text="➕ Nouveau Chantier", command=self._create_new_chantier)
        new_btn.pack(side="right", padx=(10, 0))
        
        # Remises configuration frame
        self.remises_frame = ttk.LabelFrame(main_frame, text="Configuration des Remises", padding=10)
        self.remises_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        # Buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x")
        
        save_btn = ttk.Button(buttons_frame, text="💾 Sauvegarder", command=self._save_remises)
        save_btn.pack(side="left")
        
        delete_btn = ttk.Button(buttons_frame, text="🗑️ Supprimer Chantier", command=self._delete_chantier)
        delete_btn.pack(side="left", padx=(10, 0))
        
        close_btn = ttk.Button(buttons_frame, text="Fermer", command=self.dialog.destroy)
        close_btn.pack(side="right")
        
    def _load_chantiers(self):
        """Load available chantiers for the selected client"""
        try:
            if self.client_data and self.client_data.get('code_client'):
                # Get client-specific chantiers
                client_code = self.client_data['code_client']
                chantiers = self.chantier_service.get_client_chantiers(client_code)
                
                # Also include client's primary chantier if not already configured
                client_chantier = self.client_data.get('chantier')
                if client_chantier and client_chantier.strip() and client_chantier != 'None':
                    if client_chantier not in chantiers:
                        chantiers.append(client_chantier)
                
                if not chantiers:
                    # If no chantiers, offer to create one based on client's chantier
                    if client_chantier and client_chantier.strip() and client_chantier != 'None':
                        chantiers = [client_chantier]
                    else:
                        chantiers = [f"Nouveau chantier pour {self.client_data.get('raison_sociale', 'client')}"]
            else:
                # Fallback to all available chantiers if no client selected
                chantiers = self.chantier_service.get_available_chantiers()
            
            self.chantier_combo['values'] = chantiers
            
            # Auto-select if only one chantier
            if len(chantiers) == 1:
                self.chantier_var.set(chantiers[0])
                self._on_chantier_selected()
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des chantiers: {e}")
    
    def _on_chantier_selected(self, event=None):
        """Handle chantier selection"""
        chantier = self.chantier_var.get()
        if not chantier:
            return
            
        self.current_chantier = chantier
        self._load_chantier_remises()
    
    def _load_chantier_remises(self):
        """Load remises for the selected chantier"""
        if not self.current_chantier:
            return
            
        # Clear existing widgets
        for widget in self.remises_frame.winfo_children():
            widget.destroy()
        
        try:
            # Get products and current remises
            products = self.chantier_service.get_products()
            remises = self.chantier_service.get_chantier_remises(self.current_chantier)
            
            # Create header
            header_frame = ttk.Frame(self.remises_frame)
            header_frame.pack(fill="x", pady=(0, 10))
            
            ttk.Label(header_frame, text="Produit", font=("Segoe UI", 10, "bold"), width=15).pack(side="left")
            ttk.Label(header_frame, text="Remise (%)", font=("Segoe UI", 10, "bold"), width=12).pack(side="left", padx=(20, 0))
            ttk.Label(header_frame, text="Prix Spécifique", font=("Segoe UI", 10, "bold"), width=15).pack(side="left", padx=(20, 0))
            
            # Create entries for each product
            self.product_entries = {}
            
            for product in products:
                product_code = product['code']
                designation = product['designation']
                current_remise = remises.get(product_code, {'remise_percentage': 0, 'prix_specifique': 0})
                
                product_frame = ttk.Frame(self.remises_frame)
                product_frame.pack(fill="x", pady=2)
                
                # Product label
                product_label = ttk.Label(product_frame, text=f"{product_code}", width=15)
                product_label.pack(side="left")
                
                # Remise entry
                remise_var = tk.StringVar(value=str(current_remise['remise_percentage']))
                remise_entry = ttk.Entry(product_frame, textvariable=remise_var, width=10)
                remise_entry.pack(side="left", padx=(20, 0))
                
                # Prix specifique entry
                prix_var = tk.StringVar(value=str(current_remise['prix_specifique']))
                prix_entry = ttk.Entry(product_frame, textvariable=prix_var, width=12)
                prix_entry.pack(side="left", padx=(20, 0))
                
                # Designation label
                desig_label = ttk.Label(product_frame, text=designation, width=30)
                desig_label.pack(side="left", padx=(10, 0))
                
                self.product_entries[product_code] = {
                    'remise_var': remise_var,
                    'prix_var': prix_var
                }
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des remises: {e}")
    
    def _create_new_chantier(self):
        """Create a new chantier"""
        dialog = tk.Toplevel(self.dialog)
        dialog.title("Nouveau Chantier")
        dialog.geometry("300x150")
        dialog.transient(self.dialog)
        dialog.grab_set()
        
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ttk.Label(frame, text="Nom du chantier:").pack(anchor="w")
        
        name_var = tk.StringVar()
        name_entry = ttk.Entry(frame, textvariable=name_var, width=30)
        name_entry.pack(fill="x", pady=(5, 20))
        name_entry.focus()
        
        def save_new_chantier():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Attention", "Veuillez saisir un nom de chantier")
                return
                
            try:
                # Get client code if available
                client_code = self.client_data.get('code_client') if self.client_data else None
                if self.chantier_service.create_new_chantier_for_client(name, client_code):
                    messagebox.showinfo("Succès", f"Chantier '{name}' créé avec succès")
                    dialog.destroy()
                    self._load_chantiers()
                    
                    # Notify parent to refresh its chantier selector
                    if self.refresh_callback:
                        self.refresh_callback()
                    self.chantier_var.set(name)
                    self._on_chantier_selected()
                else:
                    messagebox.showerror("Erreur", "Erreur lors de la création du chantier")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {e}")
        
        button_frame = ttk.Frame(frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Créer", command=save_new_chantier).pack(side="left")
        ttk.Button(button_frame, text="Annuler", command=dialog.destroy).pack(side="right")
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() - dialog.winfo_width()) // 2
        y = (dialog.winfo_screenheight() - dialog.winfo_height()) // 2
        dialog.geometry(f"+{x}+{y}")
    
    def _save_remises(self):
        """Save the current remises configuration"""
        if not self.current_chantier:
            messagebox.showwarning("Attention", "Veuillez sélectionner un chantier")
            return
        
        try:
            for product_code, entries in self.product_entries.items():
                remise_str = entries['remise_var'].get()
                prix_str = entries['prix_var'].get()
                
                try:
                    remise_pct = float(remise_str) if remise_str else 0
                    prix_spec = float(prix_str) if prix_str else 0
                except ValueError:
                    messagebox.showerror("Erreur", f"Valeurs invalides pour le produit {product_code}")
                    return
                
                client_code = self.client_data.get('code_client') if self.client_data else None
                self.chantier_service.save_chantier_remise(
                    self.current_chantier, product_code, remise_pct, prix_spec, client_code
                )
            
            messagebox.showinfo("Succès", "Remises sauvegardées avec succès")
            
            # Notify parent to refresh its chantier selector
            if self.refresh_callback:
                self.refresh_callback()
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def _delete_chantier(self):
        """Delete the current chantier and its remises"""
        if not self.current_chantier:
            messagebox.showwarning("Attention", "Veuillez sélectionner un chantier")
            return
        
        if messagebox.askyesno("Confirmation", 
                              f"Êtes-vous sûr de vouloir supprimer le chantier '{self.current_chantier}' "
                              "et toutes ses remises?"):
            try:
                self.chantier_service.delete_chantier_remises(self.current_chantier)
                messagebox.showinfo("Succès", f"Chantier '{self.current_chantier}' supprimé")
                
                # Refresh the interface
                self._load_chantiers()
                self.chantier_var.set("")
                self.current_chantier = None
                
                # Clear remises frame
                for widget in self.remises_frame.winfo_children():
                    widget.destroy()
                
                # Call the refresh callback to update the main UI
                if self.refresh_callback:
                    self.refresh_callback()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
