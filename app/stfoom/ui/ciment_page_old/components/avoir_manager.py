"""
Avoir Manager Component
======================
Handles all Avoir (Credit Note) UI operations

Extracted from monolithic ciment_page_simple.py
This component focuses solely on credit note management:
- Monthly avoir calculations and tracking
- Avoir creation and modification
- Avoir list display and management
- Integration with facture system

Benefits:
- Specialized credit note handling
- Monthly tracking and calculations
- Clean integration with invoice system
- Better performance and maintainability
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime
from typing import Optional, List, Dict, Any, Callable
import sys
import os

# Add paths
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))))

from stfoom.ui.ciment_page.services.ciment_service import CimentService

# Import unified logger
try:
    from unified_logger import log_ui_error, log_ui_info
except ImportError:
    def log_ui_error(component, message, context=None, exception=None):
        print(f"[UI ERROR] {component}: {message}")
    def log_ui_info(component, message, context=None):
        print(f"[UI INFO] {component}: {message}")

class AvoirManager:
    """Component for managing Avoir (Credit Note) operations."""
    
    def __init__(self, parent, ciment_service: CimentService):
        """Initialize Avoir Manager component."""
        self.parent = parent
        self.service = ciment_service
        self.avoir_frame = None
        self.current_avoirs: List[Dict[str, Any]] = []
        
        # UI variables
        self.current_month_var = None
        self.current_year_var = None
        self.avoir_rate_var = None
        
        # Callbacks for parent communication
        self.on_avoir_calculated: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_monthly_avoir_updated: Optional[Callable[[int, int, float], None]] = None
        
        log_ui_info("AvoirManager", "Component initialized")
    
    def create_avoir_section(self, parent_frame) -> ttk.Frame:
        """Create the Avoir management section."""
        try:
            # Main Avoir frame
            self.avoir_frame = ttk.LabelFrame(parent_frame, text="Gestion des Avoirs", padding="10")
            
            # Create sections
            self._create_monthly_avoir_section()
            self._create_avoir_calculation_section()
            self._create_avoir_history_section()
            
            # Initialize with current month
            current_date = date.today()
            self.current_month_var.set(str(current_date.month))
            self.current_year_var.set(str(current_date.year))
            
            # Load initial data
            self.refresh_monthly_avoir()
            
            log_ui_info("AvoirManager", "Avoir section created successfully")
            return self.avoir_frame
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error creating avoir section", None, e)
            return ttk.Frame(parent_frame)  # Return empty frame on error
    
    def _create_monthly_avoir_section(self):
        """Create monthly avoir tracking section."""
        # Monthly Avoir frame
        monthly_frame = ttk.LabelFrame(self.avoir_frame, text="Suivi Mensuel des Avoirs", padding="5")
        monthly_frame.pack(fill="x", pady=(0, 10))
        
        # Period selection
        period_frame = ttk.Frame(monthly_frame)
        period_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(period_frame, text="Période:").pack(side="left")
        
        # Month selection
        self.current_month_var = tk.StringVar()
        month_combo = ttk.Combobox(period_frame, textvariable=self.current_month_var, width=10)
        month_combo['values'] = [
            "1", "2", "3", "4", "5", "6", 
            "7", "8", "9", "10", "11", "12"
        ]
        month_combo.pack(side="left", padx=(5, 10))
        month_combo.bind("<<ComboboxSelected>>", self._on_period_change)
        
        # Year selection
        self.current_year_var = tk.StringVar()
        year_combo = ttk.Combobox(period_frame, textvariable=self.current_year_var, width=8)
        current_year = date.today().year
        year_combo['values'] = [str(y) for y in range(current_year - 2, current_year + 2)]
        year_combo.pack(side="left", padx=(0, 20))
        year_combo.bind("<<ComboboxSelected>>", self._on_period_change)
        
        # Refresh button
        ttk.Button(period_frame, text="Actualiser", command=self.refresh_monthly_avoir).pack(side="left")
        
        # Statistics display
        stats_frame = ttk.Frame(monthly_frame)
        stats_frame.pack(fill="x", pady=(10, 0))
        
        # Statistics labels
        self.stats_labels = {}
        stats_items = [
            ("total_bls", "Total BLs:", "0"),
            ("total_value", "Valeur totale:", "0.00 DA"),
            ("avoir_rate", "Taux avoir:", "0.0%"),
            ("avoir_amount", "Montant avoir:", "0.00 DA")
        ]
        
        for i, (key, label, default) in enumerate(stats_items):
            row, col = divmod(i, 2)
            
            label_frame = ttk.Frame(stats_frame)
            label_frame.grid(row=row, column=col, padx=10, pady=2, sticky="w")
            
            ttk.Label(label_frame, text=label, font=("Segoe UI", 9, "bold")).pack(side="left")
            stats_label = ttk.Label(label_frame, text=default, font=("Segoe UI", 9))
            stats_label.pack(side="left", padx=(10, 0))
            
            self.stats_labels[key] = stats_label
        
        # Configure grid weights
        stats_frame.columnconfigure(0, weight=1)
        stats_frame.columnconfigure(1, weight=1)
    
    def _create_avoir_calculation_section(self):
        """Create avoir calculation and adjustment section."""
        # Calculation frame
        calc_frame = ttk.LabelFrame(self.avoir_frame, text="Calcul et Ajustement des Avoirs", padding="5")
        calc_frame.pack(fill="x", pady=(0, 10))
        
        # Calculation controls
        controls_frame = ttk.Frame(calc_frame)
        controls_frame.pack(fill="x", pady=(0, 10))
        
        # Avoir rate input
        ttk.Label(controls_frame, text="Taux avoir (%):").pack(side="left")
        self.avoir_rate_var = tk.StringVar(value="2.0")
        rate_entry = ttk.Entry(controls_frame, textvariable=self.avoir_rate_var, width=10)
        rate_entry.pack(side="left", padx=(5, 20))
        
        # Calculate button
        ttk.Button(controls_frame, text="Calculer Avoir", command=self._calculate_monthly_avoir).pack(side="left", padx=(0, 10))
        
        # Save button
        ttk.Button(controls_frame, text="Sauvegarder", command=self._save_monthly_avoir).pack(side="left")
        
        # Calculation details
        details_frame = ttk.LabelFrame(calc_frame, text="Détails du calcul", padding="5")
        details_frame.pack(fill="x", pady=(10, 0))
        
        # Details treeview
        self.calc_details_tree = ttk.Treeview(details_frame, height=6)
        self.calc_details_tree["columns"] = ("fournisseur", "total_value", "avoir_rate", "avoir_amount")
        self.calc_details_tree.heading("#0", text="Période", anchor="w")
        self.calc_details_tree.heading("fournisseur", text="Fournisseur", anchor="w")
        self.calc_details_tree.heading("total_value", text="Valeur totale", anchor="e")
        self.calc_details_tree.heading("avoir_rate", text="Taux (%)", anchor="e")
        self.calc_details_tree.heading("avoir_amount", text="Montant avoir", anchor="e")
        
        # Column widths
        self.calc_details_tree.column("#0", width=100)
        self.calc_details_tree.column("fournisseur", width=150)
        self.calc_details_tree.column("total_value", width=100)
        self.calc_details_tree.column("avoir_rate", width=80)
        self.calc_details_tree.column("avoir_amount", width=100)
        
        # Scrollbar
        calc_scrollbar = ttk.Scrollbar(details_frame, orient="vertical", command=self.calc_details_tree.yview)
        self.calc_details_tree.configure(yscrollcommand=calc_scrollbar.set)
        
        # Pack treeview and scrollbar
        self.calc_details_tree.pack(side="left", fill="both", expand=True)
        calc_scrollbar.pack(side="right", fill="y")
    
    def _create_avoir_history_section(self):
        """Create avoir history display section."""
        # History frame
        history_frame = ttk.LabelFrame(self.avoir_frame, text="Historique des Avoirs", padding="5")
        history_frame.pack(fill="both", expand=True)
        
        # Search frame
        search_frame = ttk.Frame(history_frame)
        search_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(search_frame, text="Filtrer par année:").pack(side="left")
        self.history_year_var = tk.StringVar()
        year_filter = ttk.Combobox(search_frame, textvariable=self.history_year_var, width=10)
        current_year = date.today().year
        year_filter['values'] = ["Toutes"] + [str(y) for y in range(current_year - 5, current_year + 1)]
        year_filter.set("Toutes")
        year_filter.pack(side="left", padx=(5, 20))
        year_filter.bind("<<ComboboxSelected>>", self._on_history_filter_change)
        
        ttk.Button(search_frame, text="Actualiser", command=self.refresh_avoir_history).pack(side="left")
        
        # History treeview
        self.history_tree = ttk.Treeview(history_frame, height=10)
        self.history_tree["columns"] = ("year", "month", "total_value", "avoir_rate", "avoir_amount", "created_date")
        self.history_tree.heading("#0", text="ID", anchor="w")
        self.history_tree.heading("year", text="Année", anchor="e")
        self.history_tree.heading("month", text="Mois", anchor="e")
        self.history_tree.heading("total_value", text="Valeur totale", anchor="e")
        self.history_tree.heading("avoir_rate", text="Taux (%)", anchor="e")
        self.history_tree.heading("avoir_amount", text="Montant avoir", anchor="e")
        self.history_tree.heading("created_date", text="Date création", anchor="w")
        
        # Column widths
        self.history_tree.column("#0", width=50)
        self.history_tree.column("year", width=60)
        self.history_tree.column("month", width=60)
        self.history_tree.column("total_value", width=100)
        self.history_tree.column("avoir_rate", width=80)
        self.history_tree.column("avoir_amount", width=100)
        self.history_tree.column("created_date", width=120)
        
        # Scrollbars
        h_scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=self.history_tree.yview)
        v_scrollbar = ttk.Scrollbar(history_frame, orient="horizontal", command=self.history_tree.xview)
        self.history_tree.configure(yscrollcommand=h_scrollbar.set, xscrollcommand=v_scrollbar.set)
        
        # Pack treeview and scrollbars
        self.history_tree.pack(side="left", fill="both", expand=True)
        h_scrollbar.pack(side="right", fill="y")
        v_scrollbar.pack(side="bottom", fill="x")
        
        # Context menu
        self.history_tree.bind("<Button-3>", self._show_history_context_menu)
        self.history_tree.bind("<Double-1>", self._on_history_double_click)
        
        # Action buttons
        action_frame = ttk.Frame(history_frame)
        action_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(action_frame, text="Modifier", command=self._edit_selected_avoir).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Supprimer", command=self._delete_selected_avoir).pack(side="left", padx=(0, 10))
        ttk.Button(action_frame, text="Exporter", command=self._export_avoir_data).pack(side="left")
    
    # ==================== EVENT HANDLERS ====================
    
    def _on_period_change(self, event):
        """Handle period selection change."""
        self.refresh_monthly_avoir()
    
    def _calculate_monthly_avoir(self):
        """Calculate monthly avoir for selected period."""
        try:
            month = int(self.current_month_var.get())
            year = int(self.current_year_var.get())
            avoir_rate = float(self.avoir_rate_var.get())
            
            if avoir_rate < 0 or avoir_rate > 100:
                messagebox.showerror("Erreur", "Le taux d'avoir doit être entre 0 et 100%")
                return
            
            # Get monthly statistics from service
            stats = self.service.calculate_monthly_statistics(month, year)
            
            if not stats or stats.get('total_value', 0) == 0:
                messagebox.showinfo("Information", "Aucune donnée trouvée pour cette période")
                return
            
            # Calculate avoir details
            total_value = stats['total_value']
            avoir_amount = total_value * (avoir_rate / 100)
            
            # Update calculation details display
            self._update_calculation_details(stats, avoir_rate, avoir_amount)
            
            # Update statistics display
            self._update_statistics_display(stats, avoir_rate, avoir_amount)
            
            log_ui_info("AvoirManager", f"Calculated avoir for {month}/{year}: {avoir_amount:.3f} DA")
            
            # Notify parent
            if self.on_avoir_calculated:
                self.on_avoir_calculated({
                    'month': month,
                    'year': year,
                    'avoir_rate': avoir_rate,
                    'avoir_amount': avoir_amount,
                    'total_value': total_value,
                    'stats': stats
                })
            
        except ValueError as e:
            messagebox.showerror("Erreur", "Valeurs invalides. Vérifiez les champs numériques.")
            log_ui_error("AvoirManager", f"Value error in avoir calculation: {e}")
        except Exception as e:
            log_ui_error("AvoirManager", "Error calculating monthly avoir", None, e)
            messagebox.showerror("Erreur", f"Erreur lors du calcul: {str(e)}")
    
    def _save_monthly_avoir(self):
        """Save calculated monthly avoir."""
        try:
            # TODO: Implement saving logic
            # This would typically save to database via service
            messagebox.showinfo("Info", "Fonctionnalité de sauvegarde à implémenter")
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error saving monthly avoir", None, e)
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {str(e)}")
    
    def refresh_monthly_avoir(self):
        """Refresh monthly avoir data for selected period."""
        try:
            if not self.current_month_var.get() or not self.current_year_var.get():
                return
            
            month = int(self.current_month_var.get())
            year = int(self.current_year_var.get())
            
            # Get statistics for the period
            stats = self.service.calculate_monthly_statistics(month, year)
            
            # Update display
            self._update_statistics_display(stats, 0.0, 0.0)
            
            log_ui_info("AvoirManager", f"Refreshed monthly avoir for {month}/{year}")
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error refreshing monthly avoir", None, e)
    
    def refresh_avoir_history(self):
        """Refresh the avoir history display."""
        try:
            # Clear existing items
            for item in self.history_tree.get_children():
                self.history_tree.delete(item)
            
            # TODO: Load avoir history from database via service
            # This is a placeholder implementation
            log_ui_info("AvoirManager", "Refreshed avoir history")
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error refreshing avoir history", None, e)
    
    # ==================== HELPER METHODS ====================
    
    def _update_statistics_display(self, stats: Dict[str, Any], avoir_rate: float, avoir_amount: float):
        """Update the statistics display."""
        try:
            if not stats:
                # Reset all to zero
                self.stats_labels["total_bls"].config(text="0")
                self.stats_labels["total_value"].config(text="0.00 DA")
                self.stats_labels["avoir_rate"].config(text="0.0%")
                self.stats_labels["avoir_amount"].config(text="0.00 DA")
                return
            
            # Update statistics
            self.stats_labels["total_bls"].config(text=str(stats.get("total_bls", 0)))
            self.stats_labels["total_value"].config(text=f"{stats.get('total_value', 0):.3f} DA")
            self.stats_labels["avoir_rate"].config(text=f"{avoir_rate:.1f}%")
            self.stats_labels["avoir_amount"].config(text=f"{avoir_amount:.3f} DA")
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error updating statistics display", None, e)
    
    def _update_calculation_details(self, stats: Dict[str, Any], avoir_rate: float, total_avoir: float):
        """Update the calculation details display."""
        try:
            # Clear existing items
            for item in self.calc_details_tree.get_children():
                self.calc_details_tree.delete(item)
            
            # Add summary row
            period = f"{self.current_month_var.get()}/{self.current_year_var.get()}"
            self.calc_details_tree.insert("", "end",
                                        text=period,
                                        values=(
                                            "TOTAL",
                                            f"{stats.get('total_value', 0):.3f}",
                                            f"{avoir_rate:.1f}%",
                                            f"{total_avoir:.3f}"
                                        ))
            
            # Add details by fournisseur if available
            fournisseurs = stats.get('fournisseurs', {})
            for fournisseur, data in fournisseurs.items():
                fournisseur_avoir = data['value'] * (avoir_rate / 100)
                self.calc_details_tree.insert("", "end",
                                            text="",
                                            values=(
                                                fournisseur,
                                                f"{data['value']:.3f}",
                                                f"{avoir_rate:.1f}%",
                                                f"{fournisseur_avoir:.3f}"
                                            ))
            
        except Exception as e:
            log_ui_error("AvoirManager", "Error updating calculation details", None, e)
    
    def _on_history_filter_change(self, event):
        """Handle history filter change."""
        self.refresh_avoir_history()
    
    def _show_history_context_menu(self, event):
        """Show context menu for history."""
        # TODO: Implement context menu
        pass
    
    def _on_history_double_click(self, event):
        """Handle double-click on history item."""
        # TODO: Implement double-click action
        pass
    
    def _edit_selected_avoir(self):
        """Edit selected avoir record."""
        # TODO: Implement avoir editing
        pass
    
    def _delete_selected_avoir(self):
        """Delete selected avoir record."""
        # TODO: Implement avoir deletion
        pass
    
    def _export_avoir_data(self):
        """Export avoir data to file."""
        # TODO: Implement data export
        pass

# Convenience function
def create_avoir_manager(parent, service: CimentService) -> AvoirManager:
    """Factory function to create avoir manager."""
    return AvoirManager(parent, service)
