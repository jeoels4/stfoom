"""
BL Manager Component
====================
Handles all Bon de Livraison UI operations

Extracted from monolithic ciment_page_simple.py
This component focuses solely on BL management:
- BL creation form and validation
- BL list display and editing
- BL search and filtering
- BL deletion and status management

Benefits:
- Single responsibility principle
- Reusable across different pages
- Easier testing and maintenance  
- Better performance (lighter components)
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Callable
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from stfoom.ui.ciment_page.services.ciment_service import CimentService, BLData
from stfoom.logicold.ciment import BonLivraison

# Import unified logger
try:
    from unified_logger import log_ui_error, log_ui_info
except ImportError:
    def log_ui_error(component, message, context=None, exception=None):
        print(f"[UI ERROR] {component}: {message}")
    def log_ui_info(component, message, context=None):
        print(f"[UI INFO] {component}: {message}")

class BLManager:
    """Component for managing Bon de Livraison operations."""
    
    def __init__(self, parent, ciment_service: CimentService):
        """Initialize BL Manager component."""
        self.parent = parent
        self.service = ciment_service
        self.bl_frame = None
        self.current_bls: List[BonLivraison] = []
        
        # Callbacks for parent communication
        self.on_bl_created: Optional[Callable[[BonLivraison], None]] = None
        self.on_bl_deleted: Optional[Callable[[int], None]] = None
        self.on_bl_selected: Optional[Callable[[BonLivraison], None]] = None
        
        log_ui_info("BLManager", "Component initialized")
    
    def create_bl_section(self, parent_frame) -> ttk.Frame:
        """Create the BL management section."""
        try:
            # Main BL frame
            self.bl_frame = ttk.LabelFrame(parent_frame, text="Bons de Livraison", padding="10")
            
            # Create BL form
            self._create_bl_form()
            
            # Create BL list
            self._create_bl_list()
            
            # Load initial data
            self.refresh_bl_list()
            
            log_ui_info("BLManager", "BL section created successfully")
            return self.bl_frame
            
        except Exception as e:
            log_ui_error("BLManager", "Error creating BL section", None, e)
            return ttk.Frame(parent_frame)  # Return empty frame on error
    
    def _create_bl_form(self):
        """Create BL creation form."""
        # Form frame
        form_frame = ttk.LabelFrame(self.bl_frame, text="Nouveau BL", padding="5")
        form_frame.pack(fill="x", pady=(0, 10))
        
        # Form fields
        fields_frame = ttk.Frame(form_frame)
        fields_frame.pack(fill="x")
        
        # Row 1: Numéro, Date
        row1 = ttk.Frame(fields_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="Numéro:").pack(side="left")
        self.numero_var = tk.StringVar()
        numero_entry = ttk.Entry(row1, textvariable=self.numero_var, width=15)
        numero_entry.pack(side="left", padx=(5, 20))
        
        ttk.Label(row1, text="Date:").pack(side="left")
        self.date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(row1, textvariable=self.date_var, width=15)
        date_entry.pack(side="left", padx=(5, 0))
        
        # Row 2: Fournisseur
        row2 = ttk.Frame(fields_frame)
        row2.pack(fill="x", pady=2)
        
        ttk.Label(row2, text="Fournisseur:").pack(side="left")
        self.fournisseur_var = tk.StringVar()
        fournisseur_entry = ttk.Entry(row2, textvariable=self.fournisseur_var, width=30)
        fournisseur_entry.pack(side="left", padx=(5, 0))
        
        # Row 3: Quantité, Unité, Montant
        row3 = ttk.Frame(fields_frame)
        row3.pack(fill="x", pady=2)
        
        ttk.Label(row3, text="Quantité:").pack(side="left")
        self.quantite_var = tk.StringVar()
        quantite_entry = ttk.Entry(row3, textvariable=self.quantite_var, width=10)
        quantite_entry.pack(side="left", padx=(5, 10))
        
        ttk.Label(row3, text="Unité:").pack(side="left")
        self.unite_var = tk.StringVar(value="tonnes")
        unite_combo = ttk.Combobox(row3, textvariable=self.unite_var, width=10)
        unite_combo['values'] = ("tonnes", "m³", "unités", "kg")
        unite_combo.pack(side="left", padx=(5, 10))
        
        ttk.Label(row3, text="Montant:").pack(side="left")
        self.montant_var = tk.StringVar()
        montant_entry = ttk.Entry(row3, textvariable=self.montant_var, width=12)
        montant_entry.pack(side="left", padx=(5, 0))
        
        # Row 4: Description
        row4 = ttk.Frame(fields_frame)
        row4.pack(fill="x", pady=2)
        
        ttk.Label(row4, text="Description:").pack(side="left")
        self.description_var = tk.StringVar()
        description_entry = ttk.Entry(row4, textvariable=self.description_var, width=50)
        description_entry.pack(side="left", padx=(5, 0))
        
        # Buttons frame
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Auto-number button
        auto_btn = ttk.Button(buttons_frame, text="Auto-numéro", command=self._auto_numero)
        auto_btn.pack(side="left", padx=(0, 10))
        
        # Create button
        create_btn = ttk.Button(buttons_frame, text="Créer BL", command=self._create_bl)
        create_btn.pack(side="left", padx=(0, 10))
        
        # Clear button
        clear_btn = ttk.Button(buttons_frame, text="Effacer", command=self._clear_form)
        clear_btn.pack(side="left")
    
    def _create_bl_list(self):
        """Create BL list display."""
        # List frame
        list_frame = ttk.LabelFrame(self.bl_frame, text="Liste des BL", padding="5")
        list_frame.pack(fill="both", expand=True)
        
        # Search frame
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_frame, text="Rechercher:").pack(side="left")
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=30)
        search_entry.pack(side="left", padx=(5, 10))
        search_entry.bind("<KeyRelease>", self._on_search_change)
        
        ttk.Button(search_frame, text="Actualiser", command=self.refresh_bl_list).pack(side="left")
        
        # Treeview for BL list
        self.bl_tree = ttk.Treeview(list_frame, height=10)
        self.bl_tree["columns"] = ("date", "fournisseur", "quantite", "unite", "montant", "statut")
        self.bl_tree.heading("#0", text="Numéro", anchor="w")
        self.bl_tree.heading("date", text="Date", anchor="w")
        self.bl_tree.heading("fournisseur", text="Fournisseur", anchor="w")
        self.bl_tree.heading("quantite", text="Quantité", anchor="e")
        self.bl_tree.heading("unite", text="Unité", anchor="w")
        self.bl_tree.heading("montant", text="Montant", anchor="e")
        self.bl_tree.heading("statut", text="Statut", anchor="w")
        
        # Column widths
        self.bl_tree.column("#0", width=100)
        self.bl_tree.column("date", width=100)
        self.bl_tree.column("fournisseur", width=150)
        self.bl_tree.column("quantite", width=80)
        self.bl_tree.column("unite", width=60)
        self.bl_tree.column("montant", width=100)
        self.bl_tree.column("statut", width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.bl_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.bl_tree.xview)
        self.bl_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.bl_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Context menu
        self.bl_tree.bind("<Button-3>", self._show_bl_context_menu)
        self.bl_tree.bind("<Double-1>", self._on_bl_double_click)
        
        # Action buttons
        action_frame = ttk.Frame(list_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(action_frame, text="Supprimer", command=self._delete_selected_bl).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Modifier", command=self._edit_selected_bl).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Voir détails", command=self._view_bl_details).pack(side="left")
    
    # ==================== EVENT HANDLERS ====================
    
    def _auto_numero(self):
        """Auto-generate next BL numero."""
        try:
            next_numero = self.service.get_next_bl_numero()
            self.numero_var.set(next_numero)
            log_ui_info("BLManager", f"Auto-generated numero: {next_numero}")
        except Exception as e:
            log_ui_error("BLManager", "Error generating auto numero", None, e)
            messagebox.showerror("Erreur", "Impossible de générer le numéro automatiquement")
    
    def _create_bl(self):
        """Create a new BL."""
        try:
            # Validate and create BL data
            bl_data = self._get_bl_data_from_form()
            if not bl_data:
                return
            
            # Create BL via service
            success = self.service.create_bon_livraison(bl_data)
            
            if success:
                messagebox.showinfo("Succès", f"BL {bl_data.numero} créé avec succès!")
                self._clear_form()
                self.refresh_bl_list()
                
                # Notify parent if callback set
                if self.on_bl_created:
                    # Would need to get the actual BL object here
                    pass
                    
            else:
                messagebox.showerror("Erreur", "Impossible de créer le BL. Vérifiez les données.")
                
        except Exception as e:
            log_ui_error("BLManager", "Error creating BL", None, e)
            messagebox.showerror("Erreur", f"Erreur lors de la création du BL: {str(e)}")
    
    def _clear_form(self):
        """Clear all form fields."""
        self.numero_var.set("")
        self.date_var.set(date.today().strftime("%Y-%m-%d"))
        self.fournisseur_var.set("")
        self.quantite_var.set("")
        self.unite_var.set("tonnes")
        self.montant_var.set("")
        self.description_var.set("")
    
    def _delete_selected_bl(self):
        """Delete selected BL."""
        try:
            selection = self.bl_tree.selection()
            if not selection:
                messagebox.showwarning("Attention", "Veuillez sélectionner un BL à supprimer")
                return
            
            # Get BL ID from selection
            bl_data = self.bl_tree.item(selection[0])
            bl_numero = bl_data['text']
            
            # Find BL ID
            bl_id = None
            for bl in self.current_bls:
                if bl.numero == bl_numero:
                    bl_id = bl.id
                    break
            
            if not bl_id:
                messagebox.showerror("Erreur", "BL introuvable")
                return
            
            # Confirm deletion
            if messagebox.askyesno("Confirmer", f"Êtes-vous sûr de vouloir supprimer le BL {bl_numero}?"):
                success = self.service.delete_bon_livraison(bl_id)
                
                if success:
                    messagebox.showinfo("Succès", f"BL {bl_numero} supprimé avec succès")
                    self.refresh_bl_list()
                    
                    # Notify parent
                    if self.on_bl_deleted:
                        self.on_bl_deleted(bl_id)
                else:
                    messagebox.showerror("Erreur", "Impossible de supprimer le BL")
                    
        except Exception as e:
            log_ui_error("BLManager", "Error deleting BL", None, e)
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {str(e)}")
    
    def refresh_bl_list(self):
        """Refresh the BL list display."""
        try:
            # Clear existing items
            for item in self.bl_tree.get_children():
                self.bl_tree.delete(item)
            
            # Get all BLs
            self.current_bls = self.service.get_all_bons_livraison()
            
            # Populate treeview
            for bl in self.current_bls:
                self.bl_tree.insert("", "end", 
                                   text=bl.numero,
                                   values=(
                                       bl.date_livraison.strftime("%Y-%m-%d"),
                                       bl.fournisseur_nom or bl.fournisseur_id,
                                       f"{bl.quantite:.3f}",
                                       bl.unite,
                                       f"{bl.montant:.3f}",
                                       bl.statut
                                   ))
            
            log_ui_info("BLManager", f"Refreshed BL list: {len(self.current_bls)} items")
            
        except Exception as e:
            log_ui_error("BLManager", "Error refreshing BL list", None, e)
    
    # ==================== HELPER METHODS ====================
    
    def _get_bl_data_from_form(self) -> Optional[BLData]:
        """Extract BL data from form fields."""
        try:
            # Parse date
            try:
                bl_date = datetime.strptime(self.date_var.get(), "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Erreur", "Format de date invalide (YYYY-MM-DD attendu)")
                return None
            
            # Parse numeric fields
            try:
                quantite = float(self.quantite_var.get())
                montant = float(self.montant_var.get())
            except ValueError:
                messagebox.showerror("Erreur", "Quantité et montant doivent être des nombres")
                return None
            
            # Create BL data
            bl_data = BLData(
                numero=self.numero_var.get().strip(),
                date_livraison=bl_date,
                fournisseur_id=self.fournisseur_var.get().strip(),
                quantite=quantite,
                montant=montant,
                unite=self.unite_var.get().strip(),
                description=self.description_var.get().strip() or None
            )
            
            return bl_data
            
        except Exception as e:
            log_ui_error("BLManager", "Error extracting BL data from form", None, e)
            return None
    
    def _on_search_change(self, event):
        """Handle search input changes."""
        # TODO: Implement search filtering
        pass
    
    def _show_bl_context_menu(self, event):
        """Show context menu for BL."""
        # TODO: Implement context menu
        pass
    
    def _on_bl_double_click(self, event):
        """Handle double-click on BL."""
        # TODO: Implement double-click action
        pass
    
    def _edit_selected_bl(self):
        """Edit selected BL."""
        # TODO: Implement BL editing
        pass
    
    def _view_bl_details(self):
        """View BL details."""
        # TODO: Implement details view
        pass

# Convenience function
def create_bl_manager(parent, service: CimentService) -> BLManager:
    """Factory function to create BL manager."""
    return BLManager(parent, service)
