"""
Settings Page Tax Management Addition
====================================
Add tax management to the settings page instead of achat page.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Import the working tax logic
try:
    from ..logic import taxes as taxes_logic
    print("[TAX_WIDGET] Successfully imported tax logic system")
except ImportError as e:
    print(f"[TAX_WIDGET] Error importing tax logic: {e}")
    # Fallback to placeholder if import fails
    class TaxLogicPlaceholder:
        @staticmethod
        def get_all_taxes():
            return []
        @staticmethod
        def get_tax_by_id(tax_id):
            return None
        @staticmethod
        def add_tax(name, value):
            return False
        @staticmethod
        def update_tax(tax_id, name, value):
            return False
        @staticmethod
        def delete_tax(tax_id):
            return False
    taxes_logic = TaxLogicPlaceholder()

class TaxManagementFrame(ttk.LabelFrame):
    """Tax Management section for Settings page."""
    
    def __init__(self, parent):
        super().__init__(parent, text="🏷️ Gestion des Taxes", padding="10")
        self.create_widgets()
        self.load_taxes()
    
    def create_widgets(self):
        """Create tax management widgets."""
        
        # Info label
        info_label = ttk.Label(
            self, 
            text="Gérez les taux de taxes utilisés dans tout le système STFOOM.",
            font=("Segoe UI", 9)
        )
        info_label.pack(fill="x", pady=(0, 10))
        
        # Tax list frame
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        # Treeview for taxes
        columns = ('id', 'name', 'value')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings', height=6)
        
        # Configure columns
        self.tree.heading('id', text='ID')
        self.tree.heading('name', text='Nom de la Taxe')
        self.tree.heading('value', text='Taux (%)')
        
        self.tree.column('id', width=50, anchor='center')
        self.tree.column('name', width=200, anchor='w')
        self.tree.column('value', width=80, anchor='e')
        
        # Scrollbar for treeview
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack treeview and scrollbar
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x")
        
        # Tax management buttons
        ttk.Button(
            buttons_frame,
            text="➕ Ajouter Taxe",
            command=self.add_tax
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            buttons_frame,
            text="✏️ Modifier",
            command=self.edit_tax
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            buttons_frame,
            text="🗑️ Supprimer",
            command=self.delete_tax
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            buttons_frame,
            text="🔄 Actualiser",
            command=self.load_taxes
        ).pack(side="right")
    
    def load_taxes(self):
        """Load taxes into the tree view."""
        # Clear existing items
        for item in self.tree.get_children():
            self.tree.delete(item)
        
        # Get all taxes
        taxes = taxes_logic.get_all_taxes()
        
        # Insert taxes into tree
        for tax in taxes:
            self.tree.insert('', 'end', values=(
                tax['id'],
                tax['name'],
                f"{tax['value']:.1f}"
            ))
        
        print(f"[TAX_SETTINGS] Loaded {len(taxes)} taxes into settings")
    
    def add_tax(self):
        """Add a new tax."""
        name = simpledialog.askstring(
            "Ajouter Taxe",
            "Nom de la taxe:",
            parent=self
        )
        
        if not name:
            return
        
        value = simpledialog.askfloat(
            "Ajouter Taxe",
            "Taux de la taxe (%):",
            minvalue=0.0,
            maxvalue=100.0,
            parent=self
        )
        
        if value is None:
            return
        
        # Add tax
        success = taxes_logic.add_tax(name, value)
        
        if success:
            messagebox.showinfo("Succès", f"Taxe '{name}' ajoutée avec succès!")
            self.load_taxes()  # Refresh the list
        else:
            messagebox.showerror("Erreur", "Impossible d'ajouter la taxe.")
    
    def edit_tax(self):
        """Edit selected tax."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une taxe à modifier.")
            return
        
        # Get selected tax data
        item = self.tree.item(selection[0])
        values = item['values']
        tax_id = int(values[0])
        current_name = values[1]
        current_value = float(values[2])
        
        # Get tax details
        tax = taxes_logic.get_tax_by_id(tax_id)
        if not tax:
            messagebox.showerror("Erreur", "Taxe introuvable.")
            return
        
        # Edit name
        name = simpledialog.askstring(
            "Modifier Taxe",
            "Nom de la taxe:",
            initialvalue=current_name,
            parent=self
        )
        
        if not name:
            return
        
        # Edit value
        value = simpledialog.askfloat(
            "Modifier Taxe",
            "Taux de la taxe (%):",
            initialvalue=current_value,
            minvalue=0.0,
            maxvalue=100.0,
            parent=self
        )
        
        if value is None:
            return
        
        # Update tax
        success = taxes_logic.update_tax(tax_id, name, value)
        
        if success:
            messagebox.showinfo("Succès", f"Taxe '{name}' modifiée avec succès!")
            self.load_taxes()  # Refresh the list
        else:
            messagebox.showerror("Erreur", "Impossible de modifier la taxe.")
    
    def delete_tax(self):
        """Delete selected tax."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showwarning("Sélection", "Veuillez sélectionner une taxe à supprimer.")
            return
        
        # Get selected tax data
        item = self.tree.item(selection[0])
        values = item['values']
        tax_id = int(values[0])
        tax_name = values[1]
        
        # Confirm deletion
        if not messagebox.askyesno(
            "Confirmer Suppression",
            f"Êtes-vous sûr de vouloir supprimer la taxe '{tax_name}' ?"
        ):
            return
        
        # Delete tax
        success = taxes_logic.delete_tax(tax_id)
        
        if success:
            messagebox.showinfo("Succès", f"Taxe '{tax_name}' supprimée avec succès!")
            self.load_taxes()  # Refresh the list
        else:
            messagebox.showerror("Erreur", "Impossible de supprimer la taxe.")
