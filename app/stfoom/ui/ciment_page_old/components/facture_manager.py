"""
Facture Manager Component
========================
Handles all Facture (Invoice) UI operations

Extracted from monolithic ciment_page_simple.py
This component focuses solely on invoice management:
- Invoice creation from selected BLs
- Invoice list display and management
- Invoice search and filtering
- Invoice PDF generation and export

Benefits:
- Specialized invoice handling
- Clean BL selection interface
- Reusable across different contexts
- Better performance and maintainability
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Callable
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from stfoom.ui.ciment_page.services.ciment_service import CimentService, FactureData
from stfoom.logicold.ciment import BonLivraison, CimentFacture

# Import unified logger
try:
    from unified_logger import log_ui_error, log_ui_info
except ImportError:
    def log_ui_error(component, message, context=None, exception=None):
        print(f"[UI ERROR] {component}: {message}")
    def log_ui_info(component, message, context=None):
        print(f"[UI INFO] {component}: {message}")

class FactureManager:
    """Component for managing Facture (Invoice) operations."""
    
    def __init__(self, parent, ciment_service: CimentService):
        """Initialize Facture Manager component."""
        self.parent = parent
        self.service = ciment_service
        self.facture_frame = None
        self.current_factures: List[CimentFacture] = []
        self.selected_bls: List[BonLivraison] = []
        
        # UI variables
        self.facture_numero_var = None
        self.facture_date_var = None
        self.facture_client_var = None
        
        # Callbacks for parent communication
        self.on_facture_created: Optional[Callable[[CimentFacture], None]] = None
        self.on_bl_selection_changed: Optional[Callable[[List[BonLivraison]], None]] = None
        
        log_ui_info("FactureManager", "Component initialized")
    
    def create_facture_section(self, parent_frame) -> ttk.Frame:
        """Create the Facture management section."""
        try:
            # Main Facture frame
            self.facture_frame = ttk.LabelFrame(parent_frame, text="Gestion des Factures", padding="10")
            
            # Create two main sections
            self._create_bl_selection_section()
            self._create_facture_form()
            self._create_facture_list()
            
            # Load initial data
            self.refresh_facture_list()
            self.refresh_bl_selection()
            
            log_ui_info("FactureManager", "Facture section created successfully")
            return self.facture_frame
            
        except Exception as e:
            log_ui_error("FactureManager", "Error creating facture section", None, e)
            return ttk.Frame(parent_frame)  # Return empty frame on error
    
    def _create_bl_selection_section(self):
        """Create BL selection section for invoice generation."""
        # BL Selection frame
        bl_selection_frame = ttk.LabelFrame(self.facture_frame, text="Sélection des BL pour Facturation", padding="5")
        bl_selection_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Controls frame
        controls_frame = ttk.Frame(bl_selection_frame)
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Filter by client
        ttk.Label(controls_frame, text="Filtrer par fournisseur:").pack(side="left")
        self.bl_filter_var = tk.StringVar()
        filter_combo = ttk.Combobox(controls_frame, textvariable=self.bl_filter_var, width=20)
        filter_combo.pack(side="left", padx=(5, 10))
        filter_combo.bind("<<ComboboxSelected>>", self._on_filter_change)
        
        # Refresh button
        ttk.Button(controls_frame, text="Actualiser BL", command=self.refresh_bl_selection).pack(side="left", padx=(0, 10))
        
        # Select all/none buttons
        ttk.Button(controls_frame, text="Tout sélectionner", command=self._select_all_bls).pack(side="left", padx=(0, 5))
        ttk.Button(controls_frame, text="Tout déselectionner", command=self._deselect_all_bls).pack(side="left")
        
        # BL Treeview for selection
        tree_frame = ttk.Frame(bl_selection_frame)
        tree_frame.pack(fill="both", expand=True)
        
        self.bl_selection_tree = ttk.Treeview(tree_frame, height=8, show="tree headings")
        self.bl_selection_tree["columns"] = ("date", "fournisseur", "quantite", "unite", "montant")
        self.bl_selection_tree.heading("#0", text="☐ Numéro", anchor="w")
        self.bl_selection_tree.heading("date", text="Date", anchor="w")
        self.bl_selection_tree.heading("fournisseur", text="Fournisseur", anchor="w")
        self.bl_selection_tree.heading("quantite", text="Quantité", anchor="e")
        self.bl_selection_tree.heading("unite", text="Unité", anchor="w")
        self.bl_selection_tree.heading("montant", text="Montant", anchor="e")
        
        # Column widths
        self.bl_selection_tree.column("#0", width=120)
        self.bl_selection_tree.column("date", width=100)
        self.bl_selection_tree.column("fournisseur", width=150)
        self.bl_selection_tree.column("quantite", width=80)
        self.bl_selection_tree.column("unite", width=60)
        self.bl_selection_tree.column("montant", width=100)
        
        # Scrollbars
        v_scroll = ttk.Scrollbar(tree_frame, orient="vertical", command=self.bl_selection_tree.yview)
        h_scroll = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.bl_selection_tree.xview)
        self.bl_selection_tree.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)
        
        # Pack treeview and scrollbars
        self.bl_selection_tree.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")
        
        # Bind selection events
        self.bl_selection_tree.bind("<Button-1>", self._on_bl_selection_click)
        self.bl_selection_tree.bind("<space>", self._on_bl_selection_space)
        
        # Selected BL summary
        summary_frame = ttk.Frame(bl_selection_frame)
        summary_frame.pack(fill="x", pady=(10, 0))
        
        self.selected_summary_label = ttk.Label(summary_frame, text="Aucun BL sélectionné", font=("Segoe UI", 10, "bold"))
        self.selected_summary_label.pack(side="left")
        
        self.total_amount_label = ttk.Label(summary_frame, text="Total: 0.00 DA", font=("Segoe UI", 10, "bold"))
        self.total_amount_label.pack(side="right")
    
    def _create_facture_form(self):
        """Create facture creation form."""
        # Form frame
        form_frame = ttk.LabelFrame(self.facture_frame, text="Nouvelle Facture", padding="5")
        form_frame.pack(fill="x", pady=(0, 10))
        
        # Form fields
        fields_frame = ttk.Frame(form_frame)
        fields_frame.pack(fill="x")
        
        # Row 1: Numéro, Date
        row1 = ttk.Frame(fields_frame)
        row1.pack(fill="x", pady=2)
        
        ttk.Label(row1, text="Numéro Facture:").pack(side="left")
        self.facture_numero_var = tk.StringVar()
        numero_entry = ttk.Entry(row1, textvariable=self.facture_numero_var, width=20)
        numero_entry.pack(side="left", padx=(5, 20))
        
        ttk.Label(row1, text="Date:").pack(side="left")
        self.facture_date_var = tk.StringVar(value=date.today().strftime("%Y-%m-%d"))
        date_entry = ttk.Entry(row1, textvariable=self.facture_date_var, width=15)
        date_entry.pack(side="left", padx=(5, 0))
        
        # Row 2: Client
        row2 = ttk.Frame(fields_frame)
        row2.pack(fill="x", pady=2)
        
        ttk.Label(row2, text="Client:").pack(side="left")
        self.facture_client_var = tk.StringVar()
        client_entry = ttk.Entry(row2, textvariable=self.facture_client_var, width=40)
        client_entry.pack(side="left", padx=(5, 0))
        
        # Buttons frame
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill="x", pady=(10, 0))
        
        # Auto-numero button
        auto_btn = ttk.Button(buttons_frame, text="Auto-numéro", command=self._auto_facture_numero)
        auto_btn.pack(side="left", padx=(0, 10))
        
        # Create facture button
        create_btn = ttk.Button(buttons_frame, text="Créer Facture", command=self._create_facture, state="disabled")
        create_btn.pack(side="left", padx=(0, 10))
        self.create_facture_btn = create_btn  # Store reference
        
        # Clear button
        clear_btn = ttk.Button(buttons_frame, text="Effacer", command=self._clear_facture_form)
        clear_btn.pack(side="left")
    
    def _create_facture_list(self):
        """Create facture list display."""
        # List frame
        list_frame = ttk.LabelFrame(self.facture_frame, text="Liste des Factures", padding="5")
        list_frame.pack(fill="both", expand=True)
        
        # Search frame
        search_frame = ttk.Frame(list_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_frame, text="Rechercher:").pack(side="left")
        self.facture_search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.facture_search_var, width=30)
        search_entry.pack(side="left", padx=(5, 10))
        search_entry.bind("<KeyRelease>", self._on_facture_search_change)
        
        ttk.Button(search_frame, text="Actualiser", command=self.refresh_facture_list).pack(side="left")
        
        # Treeview for facture list
        self.facture_tree = ttk.Treeview(list_frame, height=8)
        self.facture_tree["columns"] = ("date", "client", "nb_bls", "montant", "statut")
        self.facture_tree.heading("#0", text="Numéro", anchor="w")
        self.facture_tree.heading("date", text="Date", anchor="w")
        self.facture_tree.heading("client", text="Client", anchor="w")
        self.facture_tree.heading("nb_bls", text="Nb BLs", anchor="e")
        self.facture_tree.heading("montant", text="Montant Total", anchor="e")
        self.facture_tree.heading("statut", text="Statut", anchor="w")
        
        # Column widths
        self.facture_tree.column("#0", width=120)
        self.facture_tree.column("date", width=100)
        self.facture_tree.column("client", width=200)
        self.facture_tree.column("nb_bls", width=60)
        self.facture_tree.column("montant", width=120)
        self.facture_tree.column("statut", width=100)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.facture_tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient="horizontal", command=self.facture_tree.xview)
        self.facture_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.facture_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Context menu
        self.facture_tree.bind("<Button-3>", self._show_facture_context_menu)
        self.facture_tree.bind("<Double-1>", self._on_facture_double_click)
        
        # Action buttons
        action_frame = ttk.Frame(list_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(action_frame, text="Voir BLs", command=self._view_facture_bls).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Exporter PDF", command=self._export_facture_pdf).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Supprimer", command=self._delete_selected_facture).pack(side="left")
    
    # ==================== EVENT HANDLERS ====================
    
    def _auto_facture_numero(self):
        """Auto-generate next facture numero."""
        try:
            next_numero = self.service.get_next_facture_numero()
            self.facture_numero_var.set(next_numero)
            log_ui_info("FactureManager", f"Auto-generated facture numero: {next_numero}")
        except Exception as e:
            log_ui_error("FactureManager", "Error generating auto facture numero", None, e)
            messagebox.showerror("Erreur", "Impossible de générer le numéro de facture automatiquement")
    
    def _create_facture(self):
        """Create a new facture from selected BLs."""
        try:
            if not self.selected_bls:
                messagebox.showwarning("Attention", "Veuillez sélectionner au moins un BL")
                return
            
            # Validate and create facture data
            facture_data = self._get_facture_data_from_form()
            if not facture_data:
                return
            
            # Create facture via service
            success = self.service.create_facture(facture_data)
            
            if success:
                messagebox.showinfo("Succès", f"Facture {facture_data.numero} créée avec succès!")
                self._clear_facture_form()
                self._deselect_all_bls()
                self.refresh_facture_list()
                self.refresh_bl_selection()  # Refresh to remove invoiced BLs
                
                # Notify parent if callback set
                if self.on_facture_created:
                    # Would need to get the actual facture object here
                    pass
                    
            else:
                messagebox.showerror("Erreur", "Impossible de créer la facture. Vérifiez les données.")
                
        except Exception as e:
            log_ui_error("FactureManager", "Error creating facture", None, e)
            messagebox.showerror("Erreur", f"Erreur lors de la création de la facture: {str(e)}")
    
    def _clear_facture_form(self):
        """Clear all facture form fields."""
        self.facture_numero_var.set("")
        self.facture_date_var.set(date.today().strftime("%Y-%m-%d"))
        self.facture_client_var.set("")
    
    def _on_bl_selection_click(self, event):
        """Handle BL selection clicks."""
        try:
            item = self.bl_selection_tree.identify_row(event.y)
            if item:
                self._toggle_bl_selection(item)
        except Exception as e:
            log_ui_error("FactureManager", "Error handling BL selection click", None, e)
    
    def _on_bl_selection_space(self, event):
        """Handle space key for BL selection."""
        try:
            selection = self.bl_selection_tree.selection()
            if selection:
                self._toggle_bl_selection(selection[0])
        except Exception as e:
            log_ui_error("FactureManager", "Error handling BL selection space", None, e)
    
    def _toggle_bl_selection(self, item):
        """Toggle BL selection state."""
        try:
            # Get BL data from item
            bl_numero = self.bl_selection_tree.item(item)['text'].replace("☐ ", "").replace("☑ ", "")
            
            # Find BL in current list
            bl = None
            for b in self.available_bls:
                if b.numero == bl_numero:
                    bl = b
                    break
            
            if not bl:
                return
            
            # Toggle selection
            if bl in self.selected_bls:
                self.selected_bls.remove(bl)
                # Update display
                self.bl_selection_tree.item(item, text=f"☐ {bl.numero}")
            else:
                self.selected_bls.append(bl)
                # Update display
                self.bl_selection_tree.item(item, text=f"☑ {bl.numero}")
            
            self._update_selection_summary()
            self._update_create_button_state()
            
            # Notify parent
            if self.on_bl_selection_changed:
                self.on_bl_selection_changed(self.selected_bls)
                
        except Exception as e:
            log_ui_error("FactureManager", "Error toggling BL selection", {"bl_numero": bl_numero}, e)
    
    def _select_all_bls(self):
        """Select all available BLs."""
        try:
            self.selected_bls = list(self.available_bls)
            self._refresh_bl_selection_display()
            self._update_selection_summary()
            self._update_create_button_state()
        except Exception as e:
            log_ui_error("FactureManager", "Error selecting all BLs", None, e)
    
    def _deselect_all_bls(self):
        """Deselect all BLs."""
        try:
            self.selected_bls.clear()
            self._refresh_bl_selection_display()
            self._update_selection_summary()
            self._update_create_button_state()
        except Exception as e:
            log_ui_error("FactureManager", "Error deselecting all BLs", None, e)
    
    def refresh_bl_selection(self):
        """Refresh the BL selection list."""
        try:
            # Get BLs waiting for invoicing
            self.available_bls = self.service.get_bls_en_attente()
            self.selected_bls.clear()
            
            # Populate filter combobox with unique fournisseurs
            fournisseurs = set()
            for bl in self.available_bls:
                fournisseur = bl.fournisseur_nom or bl.fournisseur_id
                if fournisseur:
                    fournisseurs.add(fournisseur)
            
            filter_combo = None
            for child in self.facture_frame.winfo_children():
                if isinstance(child, ttk.LabelFrame) and "Sélection des BL" in child['text']:
                    for widget in child.winfo_children():
                        if isinstance(widget, ttk.Frame):
                            for w in widget.winfo_children():
                                if isinstance(w, ttk.Combobox):
                                    filter_combo = w
                                    break
                    break
            
            if filter_combo:
                filter_combo['values'] = ["Tous"] + sorted(fournisseurs)
                if not self.bl_filter_var.get():
                    self.bl_filter_var.set("Tous")
            
            self._refresh_bl_selection_display()
            self._update_selection_summary()
            self._update_create_button_state()
            
            log_ui_info("FactureManager", f"Refreshed BL selection: {len(self.available_bls)} available")
            
        except Exception as e:
            log_ui_error("FactureManager", "Error refreshing BL selection", None, e)
    
    def _refresh_bl_selection_display(self):
        """Refresh the BL selection display."""
        try:
            # Clear existing items
            for item in self.bl_selection_tree.get_children():
                self.bl_selection_tree.delete(item)
            
            # Filter BLs if needed
            filter_value = self.bl_filter_var.get() if hasattr(self, 'bl_filter_var') else "Tous"
            filtered_bls = self.available_bls
            
            if filter_value and filter_value != "Tous":
                filtered_bls = [bl for bl in self.available_bls 
                               if (bl.fournisseur_nom or bl.fournisseur_id) == filter_value]
            
            # Populate treeview
            for bl in filtered_bls:
                is_selected = bl in self.selected_bls
                prefix = "☑ " if is_selected else "☐ "
                
                self.bl_selection_tree.insert("", "end", 
                                             text=f"{prefix}{bl.numero}",
                                             values=(
                                                 bl.date_livraison.strftime("%Y-%m-%d"),
                                                 bl.fournisseur_nom or bl.fournisseur_id,
                                                 f"{bl.quantite:.3f}",
                                                 bl.unite,
                                                 f"{bl.montant:.3f}"
                                             ))
            
        except Exception as e:
            log_ui_error("FactureManager", "Error refreshing BL selection display", None, e)
    
    def refresh_facture_list(self):
        """Refresh the facture list display."""
        try:
            # Clear existing items
            for item in self.facture_tree.get_children():
                self.facture_tree.delete(item)
            
            # Get all factures
            self.current_factures = self.service.get_all_factures()
            
            # Populate treeview
            for facture in self.current_factures:
                nb_bls = len(facture.bls) if hasattr(facture, 'bls') and facture.bls else 0
                
                self.facture_tree.insert("", "end", 
                                       text=facture.numero_facture,
                                       values=(
                                           facture.date_facture.strftime("%Y-%m-%d"),
                                           facture.fournisseur_nom or facture.fournisseur_id,
                                           nb_bls,
                                           f"{facture.montant_total:.3f}",
                                           facture.statut
                                       ))
            
            log_ui_info("FactureManager", f"Refreshed facture list: {len(self.current_factures)} items")
            
        except Exception as e:
            log_ui_error("FactureManager", "Error refreshing facture list", None, e)
    
    # ==================== HELPER METHODS ====================
    
    def _get_facture_data_from_form(self) -> Optional[FactureData]:
        """Extract facture data from form fields."""
        try:
            # Parse date
            try:
                facture_date = datetime.strptime(self.facture_date_var.get(), "%Y-%m-%d").date()
            except ValueError:
                messagebox.showerror("Erreur", "Format de date invalide (YYYY-MM-DD attendu)")
                return None
            
            # Calculate total amount from selected BLs
            total_amount = sum(bl.montant for bl in self.selected_bls)
            
            if total_amount <= 0:
                messagebox.showerror("Erreur", "Le montant total doit être positif")
                return None
            
            # Get BL numbers
            bl_numbers = [bl.numero for bl in self.selected_bls]
            
            # Create facture data
            facture_data = FactureData(
                numero=self.facture_numero_var.get().strip(),
                date=facture_date,
                client=self.facture_client_var.get().strip(),
                bls=bl_numbers,
                montant_total=total_amount
            )
            
            return facture_data
            
        except Exception as e:
            log_ui_error("FactureManager", "Error extracting facture data from form", None, e)
            return None
    
    def _update_selection_summary(self):
        """Update the selected BL summary display."""
        try:
            count = len(self.selected_bls)
            total = sum(bl.montant for bl in self.selected_bls)
            
            if count == 0:
                self.selected_summary_label.config(text="Aucun BL sélectionné")
                self.total_amount_label.config(text="Total: 0.00 DA")
            else:
                self.selected_summary_label.config(text=f"{count} BL(s) sélectionné(s)")
                self.total_amount_label.config(text=f"Total: {total:.3f} DA")
                
        except Exception as e:
            log_ui_error("FactureManager", "Error updating selection summary", None, e)
    
    def _update_create_button_state(self):
        """Update the create facture button state."""
        try:
            if hasattr(self, 'create_facture_btn'):
                if self.selected_bls and self.facture_numero_var.get().strip():
                    self.create_facture_btn.config(state="normal")
                else:
                    self.create_facture_btn.config(state="disabled")
        except Exception as e:
            log_ui_error("FactureManager", "Error updating create button state", None, e)
    
    def _on_filter_change(self, event):
        """Handle filter selection change."""
        self._refresh_bl_selection_display()
    
    def _on_facture_search_change(self, event):
        """Handle facture search input changes."""
        # TODO: Implement search filtering
        pass
    
    def _show_facture_context_menu(self, event):
        """Show context menu for facture."""
        # TODO: Implement context menu
        pass
    
    def _on_facture_double_click(self, event):
        """Handle double-click on facture."""
        # TODO: Implement double-click action
        pass
    
    def _view_facture_bls(self):
        """View BLs associated with selected facture."""
        # TODO: Implement BL viewing
        pass
    
    def _export_facture_pdf(self):
        """Export selected facture to PDF."""
        # TODO: Implement PDF export
        pass
    
    def _delete_selected_facture(self):
        """Delete selected facture."""
        # TODO: Implement facture deletion
        pass

# Convenience function
def create_facture_manager(parent, service: CimentService) -> FactureManager:
    """Factory function to create facture manager."""
    return FactureManager(parent, service)
