"""
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
from typing import Optional, List
import sys
import os
from stfoom.logic.ciment import (
from stfoom.logic.secure_database import exec_read_all
from stfoom.ui.permission_utils import check_ui_permission, disable_button_if_no_permission
from tkcalendar import DateEntry
from .shared_widgets import format_money  # Import centralized money formatting
Ciment/Matière Première UI Module (Simplified)
==============================================
Simplified user interface for cement/raw materials operations.
"""

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    BonLivraison, CimentFacture, create_bon_livraison, get_all_bons_livraison,
    create_ciment_facture, get_all_ciment_factures, get_bls_en_attente,
    get_next_bl_numero, get_next_facture_numero, delete_bon_livraison
)

class CimentPage(ttk.Frame):
    """Simplified ciment management page."""
    
    def __init__(self, parent, go_back):
        super().__init__(parent)
        self.parent = parent
        self.go_back = go_back
        self.current_user_id = getattr(parent, 'current_user_id', None)
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the user interface."""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(header_frame, text="Gestion Ciment/Matière Première", 
                 font=("Arial", 16, "bold")).pack(side=tk.LEFT)
        
        ttk.Button(header_frame, text="← Retour", 
                  command=self.go_back).pack(side=tk.RIGHT)
        
        # Notebook for tabs
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Bon de Livraison tab
        self.setup_bl_tab()
        
        # Factures tab
        self.setup_factures_tab()
        
        # Statistics tab
        self.setup_stats_tab()
    
    def setup_bl_tab(self):
        """Setup Bon de Livraison tab."""
        bl_frame = ttk.Frame(self.notebook)
        self.notebook.add(bl_frame, text="Bon de Livraison")
        
        # Controls frame
        controls_frame = ttk.Frame(bl_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add BL button
        self.add_bl_btn = ttk.Button(controls_frame, text="+ Nouveau BL", 
                                    command=self.add_bon_livraison)
        self.add_bl_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.add_bl_btn, "bon_livraison", "create")
        
        # Delete BL button
        self.delete_bl_btn = ttk.Button(controls_frame, text="❌ Supprimer BL", 
                                       command=self.delete_bl)
        self.delete_bl_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.delete_bl_btn, "bon_livraison", "delete")
        
        # Separator
        ttk.Separator(controls_frame, orient='vertical').pack(side=tk.LEFT, fill=tk.Y, padx=10)
        
        # Set facture number button
        self.set_facture_btn = ttk.Button(controls_frame, text="📋 Définir N° Facture", 
                                         command=self.set_facture_numero)
        self.set_facture_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.set_facture_btn, "bon_livraison", "update")
        
        # Set avoir button
        self.set_avoir_btn = ttk.Button(controls_frame, text="💰 Définir Avoir", 
                                       command=self.set_avoir_amount)
        self.set_avoir_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.set_avoir_btn, "bon_livraison", "update")
        
        # Refresh button
        ttk.Button(controls_frame, text="🔄 Actualiser", 
                  command=self.load_bl_data).pack(side=tk.LEFT)
        
        # BL Treeview - Excel-like columns
        columns = ("numero", "date", "fournisseur", "quantite", "montant", "facture_numero", "avoir")
        self.bl_tree = ttk.Treeview(bl_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.bl_tree.heading("numero", text="Numéro")
        self.bl_tree.heading("date", text="Date Livraison")
        self.bl_tree.heading("fournisseur", text="Fournisseur")
        self.bl_tree.heading("quantite", text="Quantité")
        self.bl_tree.heading("montant", text="Montant")
        self.bl_tree.heading("facture_numero", text="N° Facture")
        self.bl_tree.heading("avoir", text="Avoir")
        
        self.bl_tree.column("numero", width=100)
        self.bl_tree.column("date", width=120)
        self.bl_tree.column("fournisseur", width=150)
        self.bl_tree.column("quantite", width=100)
        self.bl_tree.column("montant", width=100)
        self.bl_tree.column("facture_numero", width=120)
        self.bl_tree.column("avoir", width=100)
        
        # Scrollbar
        bl_scrollbar = ttk.Scrollbar(bl_frame, orient=tk.VERTICAL, command=self.bl_tree.yview)
        self.bl_tree.configure(yscrollcommand=bl_scrollbar.set)
        
        # Pack tree and scrollbar
        self.bl_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bl_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click
        self.bl_tree.bind("<Double-1>", self.edit_bl)
    
    def setup_factures_tab(self):
        """Setup Factures tab."""
        factures_frame = ttk.Frame(self.notebook)
        self.notebook.add(factures_frame, text="Factures")
        
        # Controls frame
        controls_frame = ttk.Frame(factures_frame)
        controls_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Add facture button
        self.add_facture_btn = ttk.Button(controls_frame, text="+ Nouvelle Facture", 
                                         command=self.add_ciment_facture)
        self.add_facture_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.add_facture_btn, "ciment_factures", "create")
        
        # Edit facture button
        self.edit_facture_btn = ttk.Button(controls_frame, text="✏️ Modifier Facture", 
                                          command=self.edit_ciment_facture)
        self.edit_facture_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.edit_facture_btn, "ciment_factures", "update")
        
        # Delete facture button
        self.delete_facture_btn = ttk.Button(controls_frame, text="❌ Supprimer Facture", 
                                            command=self.delete_ciment_facture)
        self.delete_facture_btn.pack(side=tk.LEFT, padx=(0, 10))
        disable_button_if_no_permission(self.delete_facture_btn, "ciment_factures", "delete")
        
        # Refresh button
        ttk.Button(controls_frame, text="🔄 Actualiser", 
                  command=self.load_factures_data).pack(side=tk.LEFT)
        
        # Factures Treeview
        columns = ("numero", "date", "fournisseur", "montant_total", "statut", "bls")
        self.factures_tree = ttk.Treeview(factures_frame, columns=columns, show="headings", height=15)
        
        # Configure columns
        self.factures_tree.heading("numero", text="Numéro")
        self.factures_tree.heading("date", text="Date Facture")
        self.factures_tree.heading("fournisseur", text="Fournisseur")
        self.factures_tree.heading("montant_total", text="Montant Total")
        self.factures_tree.heading("statut", text="Statut")
        self.factures_tree.heading("bls", text="BLs Inclus")
        
        self.factures_tree.column("numero", width=100)
        self.factures_tree.column("date", width=120)
        self.factures_tree.column("fournisseur", width=150)
        self.factures_tree.column("montant_total", width=120)
        self.factures_tree.column("statut", width=100)
        self.factures_tree.column("bls", width=100)
        
        # Scrollbar
        factures_scrollbar = ttk.Scrollbar(factures_frame, orient=tk.VERTICAL, command=self.factures_tree.yview)
        self.factures_tree.configure(yscrollcommand=factures_scrollbar.set)
        
        # Pack tree and scrollbar
        self.factures_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        factures_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind double-click
        self.factures_tree.bind("<Double-1>", self.edit_ciment_facture)
    
    def setup_stats_tab(self):
        """Setup Statistics tab."""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="Statistiques")
        
        # Statistics display
        self.stats_text = tk.Text(stats_frame, height=20, width=60)
        self.stats_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Refresh button
        ttk.Button(stats_frame, text="🔄 Actualiser Statistiques", 
                  command=self.load_stats).pack(pady=10)
    
    def load_data(self):
        """Load all data."""
        self.load_bl_data()
        self.load_factures_data()
        self.load_stats()
    
    def load_bl_data(self):
        """Load Bon de Livraison data with Excel-like display."""
        # Clear existing items
        for item in self.bl_tree.get_children():
            self.bl_tree.delete(item)
        
        # Get BLs with facture information
        from stfoom.logic.ciment import get_bls_with_facture_info
        bls_data = get_bls_with_facture_info()
        
        # Group by facture for visual merging
        facture_groups = {}
        non_facture_bls = []
        
        for bl_data in bls_data:
            if bl_data['numero_facture']:
                facture_num = bl_data['numero_facture']
                if facture_num not in facture_groups:
                    facture_groups[facture_num] = []
                facture_groups[facture_num].append(bl_data)
            else:
                non_facture_bls.append(bl_data)
        
        # Insert items with visual merging for factures
        for facture_num, bls_in_facture in facture_groups.items():
            for i, bl_data in enumerate(bls_in_facture):
                # Show facture number only on first BL (merge effect)
                facture_display = facture_num if i == 0 else ""
                
                # Format avoir (empty for now, TODO: implement avoir)
                avoir_display = ""
                
                self.bl_tree.insert("", tk.END, values=(
                    bl_data['numero'],
                    bl_data['date_livraison'].strftime("%d/%m/%Y"),
                    bl_data['fournisseur_nom'] or f"ID: {bl_data['fournisseur_id']}",
                    f"{bl_data['quantite']} {bl_data['unite']}",
                    format_money(bl_data['montant']),
                    facture_display,
                    avoir_display
                ), tags=(str(bl_data['id']), "facture" if bl_data['numero_facture'] else "no_facture"))
        
        # Insert non-facture BLs
        for bl_data in non_facture_bls:
            self.bl_tree.insert("", tk.END, values=(
                bl_data['numero'],
                bl_data['date_livraison'].strftime("%d/%m/%Y"),
                bl_data['fournisseur_nom'] or f"ID: {bl_data['fournisseur_id']}",
                f"{bl_data['quantite']} {bl_data['unite']}",
                format_money(bl_data['montant']),
                "",  # No facture
                ""   # No avoir yet
            ), tags=(str(bl_data['id']), "no_facture"))
        
        # Configure tags for visual styling
        self.bl_tree.tag_configure("facture", background="#E8F5E8")  # Light green for factured BLs
        self.bl_tree.tag_configure("no_facture", background="#FFF8DC")  # Light yellow for pending BLs
    
    def load_factures_data(self):
        """Load Factures data."""
        # Clear existing items
        for item in self.factures_tree.get_children():
            self.factures_tree.delete(item)
        
        # Get factures
        factures = get_all_ciment_factures()
        
        # Add to treeview
        for facture in factures:
            statut_display = {
                "en_attente": "En Attente",
                "payee": "Payée",
                "annulee": "Annulée"
            }.get(facture.statut, facture.statut)
            
            # Count BLs
            bl_count = len(facture.bls_inclus) if facture.bls_inclus else 0
            
            self.factures_tree.insert("", tk.END, values=(
                facture.numero_facture,
                facture.date_facture.strftime("%d/%m/%Y"),
                facture.fournisseur_nom or f"ID: {facture.fournisseur_id}",
                format_money(facture.montant_total),
                statut_display,
                f"{bl_count} BL(s)"
            ), tags=(str(facture.id),))
    
    def load_stats(self):
        """Load and display statistics."""
        from stfoom.logic.ciment import get_ciment_statistics
        
        stats = get_ciment_statistics()
        
        stats_text = "📊 Statistiques Ciment/Matière Première\n"
        stats_text += "=" * 50 + "\n\n"
        
        stats_text += f"📋 Bon de Livraison:\n"
        stats_text += f"  - Total: {stats.get('total_bls', 0)}\n"
        stats_text += f"  - Quantité totale: {stats.get('total_quantite', 0):.3f} tonnes\n"
        stats_text += f"  - Montant total: {stats.get('total_montant_bls', 0):.3f} DT\n"
        stats_text += f"  - Moyenne par BL: {stats.get('moyenne_montant_bl', 0):.3f} DT\n\n"
        
        stats_text += f"📄 Factures:\n"
        stats_text += f"  - Total: {stats.get('total_factures', 0)}\n"
        stats_text += f"  - Montant total: {stats.get('total_montant_factures', 0):.3f} DT\n"
        stats_text += f"  - Moyenne par facture: {stats.get('moyenne_montant_facture', 0):.3f} DT\n\n"
        
        self.stats_text.delete(1.0, tk.END)
        self.stats_text.insert(1.0, stats_text)
    
    def add_bon_livraison(self):
        """Add new Bon de Livraison."""
        if not check_ui_permission("bon_livraison", "create"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de créer un BL")
            return
        
        dialog = BonLivraisonDialog(self, "Nouveau Bon de Livraison")
        if dialog.result:
            self.load_bl_data()
    
    def delete_bl(self):
        """Delete selected BL."""
        if not check_ui_permission("bon_livraison", "delete"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de supprimer un BL")
            return
        
        selection = self.bl_tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un BL à supprimer")
            return
        
        bl_id = int(self.bl_tree.item(selection[0], "tags")[0])
        bl_numero = self.bl_tree.item(selection[0], "values")[0]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirmer suppression", 
            f"Êtes-vous sûr de vouloir supprimer le BL '{bl_numero}' ?\n\nCette action est irréversible."
        )
        
        if result:
            success, message = delete_bon_livraison(bl_id)
            if success:
                messagebox.showinfo("Succès", message)
                self.load_bl_data()
            else:
                messagebox.showerror("Erreur", message)
    
    def edit_bl(self, event=None):
        """Edit selected BL."""
        selection = self.bl_tree.selection()
        if not selection:
            return
        
        bl_id = self.bl_tree.item(selection[0], "tags")[0]
        messagebox.showinfo("Info", "Fonction d'édition à implémenter")
    
    def set_facture_numero(self):
        """Set facture number for selected BLs."""
        if not check_ui_permission("bon_livraison", "update"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de modifier un BL")
            return
        
        selections = self.bl_tree.selection()
        if not selections:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un ou plusieurs BLs")
            return
        
        # Get facture number from user
        dialog = FactureNumeroDialog(self, "Définir Numéro de Facture")
        if not dialog.result:
            return
        
        facture_numero = dialog.result['numero_facture']
        bl_ids = [int(self.bl_tree.item(item, "tags")[0]) for item in selections]
        
        # Create or link to facture
        from stfoom.logic.ciment import create_facture_for_bls
        success, message = create_facture_for_bls(facture_numero, bl_ids)
        
        if success:
            messagebox.showinfo("Succès", message)
            self.load_bl_data()
        else:
            messagebox.showerror("Erreur", message)
    
    def set_avoir_amount(self):
        """Set avoir amount for selected BL."""
        if not check_ui_permission("bon_livraison", "update"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de modifier un BL")
            return
        
        selection = self.bl_tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un BL")
            return
        
        if len(selection) > 1:
            messagebox.showwarning("Sélection multiple", "Veuillez sélectionner un seul BL pour l'avoir")
            return
        
        bl_id = int(self.bl_tree.item(selection[0], "tags")[0])
        bl_numero = self.bl_tree.item(selection[0], "values")[0]
        
        # Get avoir amount from user
        dialog = AvoirAmountDialog(self, f"Définir Avoir pour BL {bl_numero}")
        if not dialog.result:
            return
        
        avoir_amount = dialog.result['avoir_amount']
        
        # TODO: Implement avoir functionality when avoir table is created
        messagebox.showinfo("Info", f"Fonctionnalité avoir en cours de développement.\nMontant saisi: {avoir_amount:.3f} DT")
        
        # For now, just refresh to show the change would work
        # self.load_bl_data()
    
    def add_ciment_facture(self):
        """Add new Ciment Facture."""
        if not check_ui_permission("ciment_factures", "create"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de créer une facture")
            return
        
        dialog = CimentFactureDialog(self, "Nouvelle Facture Ciment")
        if dialog.result:
            self.load_factures_data()
    
    def edit_ciment_facture(self, event=None):
        """Edit selected facture."""
        selection = self.factures_tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une facture à modifier")
            return
        
        facture_id = int(self.factures_tree.item(selection[0], "tags")[0])
        dialog = CimentFactureDialog(self, "Modifier Facture Ciment", facture_id)
        if dialog.result:
            self.load_factures_data()
    
    def delete_ciment_facture(self):
        """Delete selected facture."""
        if not check_ui_permission("ciment_factures", "delete"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de supprimer une facture")
            return
        
        selection = self.factures_tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner une facture à supprimer")
            return
        
        facture_id = int(self.factures_tree.item(selection[0], "tags")[0])
        facture_numero = self.factures_tree.item(selection[0], "values")[0]
        
        # Confirm deletion
        result = messagebox.askyesno(
            "Confirmer suppression", 
            f"Êtes-vous sûr de vouloir supprimer la facture '{facture_numero}' ?\n\nCette action est irréversible."
        )
        
        if result:
            from stfoom.logic.ciment import delete_ciment_facture
            success, message = delete_ciment_facture(facture_id)
            if success:
                messagebox.showinfo("Succès", message)
                self.load_factures_data()
            else:
                messagebox.showerror("Erreur", message)


class BonLivraisonDialog(tk.Toplevel):
    """Dialog for creating Bon de Livraison."""
    
    def __init__(self, parent, title):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        
        self.title(title)
        self.geometry("500x450")
        self.resizable(False, False)
        
        # Center window
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        self.center_window()
    
    def setup_ui(self):
        """Setup the dialog UI."""
        # Main frame
        main_frame = ttk.Frame(self, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Numéro
        ttk.Label(main_frame, text="Numéro:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.numero_var = tk.StringVar()
        self.numero_entry = ttk.Entry(main_frame, textvariable=self.numero_var, width=30)
        self.numero_entry.grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Date de livraison
        ttk.Label(main_frame, text="Date de livraison:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_entry = DateEntry(main_frame, width=20, date_pattern='dd/mm/yyyy')
        self.date_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Fournisseur
        ttk.Label(main_frame, text="Fournisseur:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.fournisseur_var = tk.StringVar()
        self.fournisseur_combo = ttk.Combobox(main_frame, textvariable=self.fournisseur_var, width=30)
        self.fournisseur_combo.grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        self.load_fournisseurs()
        
        # Quantité
        ttk.Label(main_frame, text="Quantité:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.quantite_var = tk.StringVar()
        self.quantite_entry = ttk.Entry(main_frame, textvariable=self.quantite_var, width=20)
        self.quantite_entry.grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Unité
        ttk.Label(main_frame, text="Unité:").grid(row=3, column=2, sticky=tk.W, pady=5, padx=(20, 0))
        self.unite_var = tk.StringVar(value="tonnes")
        unite_combo = ttk.Combobox(main_frame, textvariable=self.unite_var,
                                  values=["tonnes", "kg", "m³"], width=10)
        unite_combo.grid(row=3, column=3, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Montant
        ttk.Label(main_frame, text="Montant (DT):").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.montant_var = tk.StringVar()
        self.montant_entry = ttk.Entry(main_frame, textvariable=self.montant_var, width=20)
        self.montant_entry.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Description
        ttk.Label(main_frame, text="Description:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.description_text = tk.Text(main_frame, height=4, width=40)
        self.description_text.grid(row=5, column=1, columnspan=3, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=6, column=0, columnspan=4, pady=20)
        
        ttk.Button(button_frame, text="Enregistrer", command=self.save).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side=tk.LEFT)
    
    def center_window(self):
        """Center the dialog window."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def load_fournisseurs(self):
        """Load fournisseurs for combobox."""
        fournisseurs = exec_read_all("SELECT code_fournisseur, nom_fournisseur FROM fournisseurs ORDER BY nom_fournisseur")
        fournisseur_list = [f"{f[1]} ({f[0]})" for f in fournisseurs]
        
        self.fournisseur_combo['values'] = fournisseur_list
        if fournisseur_list:
            self.fournisseur_combo.set(fournisseur_list[0])
    
    def get_selected_fournisseur_id(self):
        """Get the selected fournisseur ID from combobox."""
        selected = self.fournisseur_var.get()
        if selected:
            # Extract code from "Name (Code)" format
            try:
                return selected.split("(")[1].rstrip(")")
            except:
                return None
        return None
    
    def save(self):
        """Save the BL."""
        try:
            # Validate inputs
            numero = self.numero_var.get().strip()
            if not numero:
                messagebox.showerror("Erreur", "Le numéro est requis")
                return
            
            date_livraison = self.date_entry.get_date()
            if not date_livraison:
                messagebox.showerror("Erreur", "La date de livraison est requise")
                return
            
            fournisseur_id = self.get_selected_fournisseur_id()
            if not fournisseur_id:
                messagebox.showerror("Erreur", "Le fournisseur est requis")
                return
            
            try:
                quantite = float(self.quantite_var.get())
            except ValueError:
                messagebox.showerror("Erreur", "La quantité doit être un nombre")
                return
            
            try:
                montant = float(self.montant_var.get())
            except ValueError:
                messagebox.showerror("Erreur", "Le montant doit être un nombre")
                return
            
            unite = self.unite_var.get()
            description = self.description_text.get(1.0, tk.END).strip()
            
            # Create BL
            success, message, bl_id = create_bon_livraison(
                numero=numero,
                date_livraison=date_livraison,
                fournisseur_id=fournisseur_id,
                quantite=quantite,
                montant=montant,
                unite=unite,
                description=description if description else None,
                created_by=self.parent.current_user_id
            )
            
            if success:
                messagebox.showinfo("Succès", message)
                self.result = bl_id
                self.destroy()
            else:
                messagebox.showerror("Erreur", message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def cancel(self):
        """Cancel the dialog."""
        self.destroy()


class CimentFactureDialog(tk.Toplevel):
    """Dialog for creating/editing Ciment Factures (similar to AchatDialog)."""
    
    def __init__(self, parent, title, facture_id=None):
        super().__init__(parent)
        self.parent = parent
        self.result = None
        self.facture_id = facture_id
        self.selected_fournisseur = None
        self.selected_bls = []
        
        self.title(title)
        self.geometry("700x750")
        self.resizable(True, True)
        
        # Center window
        self.transient(parent)
        self.grab_set()
        
        self.setup_ui()
        self.center_window()
        
        # Load initial BLs after UI is set up
        self.load_initial_bls()
        
        if facture_id:
            self.load_facture_data(facture_id)
    
    def setup_ui(self):
        """Setup the dialog UI."""
        # Main container
        main_container = ttk.Frame(self)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollable content frame
        canvas = tk.Canvas(main_container, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        main_frame = ttk.Frame(canvas)
        
        main_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=main_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Fournisseur
        fournisseur_frame = ttk.LabelFrame(main_frame, text="Fournisseur")
        fournisseur_frame.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=10)
        
        def on_fournisseur_select(fournisseur_data):
            self.selected_fournisseur = fournisseur_data
            self.fournisseur_var.set(fournisseur_data.get('nom_fournisseur', ''))
            # Update BL list when fournisseur changes
            self.load_available_bls()
        
        self.fournisseur_combo = self.create_fournisseur_selector(fournisseur_frame, on_fournisseur_select)
        self.fournisseur_var = tk.StringVar()
        # Set initial fournisseur if available
        if hasattr(self, 'selected_fournisseur') and self.selected_fournisseur:
            self.fournisseur_var.set(self.selected_fournisseur.get('nom_fournisseur', ''))
        
        # Facture details
        details_frame = ttk.LabelFrame(main_frame, text="Détails de la Facture")
        details_frame.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=10)
        
        # Numéro Facture
        ttk.Label(details_frame, text="Numéro Facture:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.numero_facture_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.numero_facture_var, width=20).grid(row=0, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Date Facture
        ttk.Label(details_frame, text="Date Facture:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.date_entry = DateEntry(details_frame, width=20, date_pattern='dd/mm/yyyy')
        self.date_entry.grid(row=1, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Montant HT
        ttk.Label(details_frame, text="Montant HT:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.montant_ht_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.montant_ht_var, width=15).grid(row=2, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Timbre
        ttk.Label(details_frame, text="Timbre:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.timbre_var = tk.StringVar(value="0")
        ttk.Entry(details_frame, textvariable=self.timbre_var, width=15).grid(row=3, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Taxes
        ttk.Label(details_frame, text="Taxes:").grid(row=4, column=0, sticky=tk.W, pady=5)
        tax_frame = ttk.Frame(details_frame)
        tax_frame.grid(row=4, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Tax management button
        ttk.Button(tax_frame, text="Gérer les taxes", 
                  command=lambda: self.manage_taxes()).pack(side=tk.LEFT, padx=(0, 10))
        
        # Tax display frame
        self.taxes_frame = ttk.Frame(details_frame)
        self.taxes_frame.grid(row=5, column=0, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        self.taxes_vars = []  # List of (tax_id_var, value_var, row_frame)
        self._add_tax_row("TVA 19%", "0", is_default=True)
        ttk.Button(details_frame, text="+ Ajouter une taxe", 
                  command=self._add_tax_row).grid(row=6, column=0, columnspan=2, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Montant Total
        ttk.Label(details_frame, text="Montant Total:").grid(row=7, column=0, sticky=tk.W, pady=5)
        self.montant_total_var = tk.StringVar()
        ttk.Entry(details_frame, textvariable=self.montant_total_var, width=15).grid(row=7, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # Date Échéance
        ttk.Label(details_frame, text="Date Échéance:").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.date_echeance_entry = DateEntry(details_frame, width=20, date_pattern='dd/mm/yyyy')
        self.date_echeance_entry.grid(row=8, column=1, sticky=tk.W, pady=5, padx=(10, 0))
        
        # BLs Selection
        bls_frame = ttk.LabelFrame(main_frame, text="Bon de Livraison à Inclure")
        bls_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10), ipadx=10, ipady=10)
        
        # BLs Treeview
        columns = ("numero", "date", "quantite", "montant", "statut")
        self.bls_tree = ttk.Treeview(bls_frame, columns=columns, show="headings", height=8)
        
        # Configure columns
        self.bls_tree.heading("numero", text="Numéro")
        self.bls_tree.heading("date", text="Date")
        self.bls_tree.heading("quantite", text="Quantité")
        self.bls_tree.heading("montant", text="Montant")
        self.bls_tree.heading("statut", text="Statut")
        
        self.bls_tree.column("numero", width=100)
        self.bls_tree.column("date", width=100)
        self.bls_tree.column("quantite", width=80)
        self.bls_tree.column("montant", width=100)
        self.bls_tree.column("statut", width=80)
        
        # Scrollbar for BLs
        bls_scrollbar = ttk.Scrollbar(bls_frame, orient=tk.VERTICAL, command=self.bls_tree.yview)
        self.bls_tree.configure(yscrollcommand=bls_scrollbar.set)
        
        # Pack BLs tree and scrollbar
        self.bls_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        bls_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # BLs controls
        bls_controls = ttk.Frame(bls_frame)
        bls_controls.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(bls_controls, text="Ajouter BL", command=self.add_bl_to_facture).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(bls_controls, text="Retirer BL", command=self.remove_bl_from_facture).pack(side=tk.LEFT)
        
        # Notes
        notes_frame = ttk.LabelFrame(main_frame, text="Notes")
        notes_frame.pack(fill=tk.X, pady=(0, 10), ipadx=10, ipady=10)
        
        self.notes_text = tk.Text(notes_frame, height=4, width=60)
        self.notes_text.pack(fill=tk.BOTH, expand=True)
        
        # Buttons (outside scrollable area)
        button_frame = ttk.Frame(main_container)
        button_frame.pack(fill=tk.X, pady=10, side=tk.BOTTOM)
        
        # Make buttons more visible with better styling
        save_btn = tk.Button(button_frame, text="Enregistrer", command=self.save, 
                            bg="#28a745", fg="white", font=("Arial", 10, "bold"),
                            relief="flat", padx=20, pady=5)
        save_btn.pack(side=tk.RIGHT, padx=(0, 10))
        
        cancel_btn = tk.Button(button_frame, text="Annuler", command=self.cancel,
                              bg="#6c757d", fg="white", font=("Arial", 10),
                              relief="flat", padx=20, pady=5)
        cancel_btn.pack(side=tk.RIGHT)
    
    def center_window(self):
        """Center the dialog window."""
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (self.winfo_width() // 2)
        y = (self.winfo_screenheight() // 2) - (self.winfo_height() // 2)
        self.geometry(f"+{x}+{y}")
    
    def create_fournisseur_selector(self, parent, on_select):
        """Create fournisseur selector similar to achat module."""
        # Simple combobox for now
        fournisseurs = exec_read_all("SELECT code_fournisseur, nom_fournisseur FROM fournisseurs ORDER BY nom_fournisseur")
        fournisseur_list = [f"{f[1]} ({f[0]})" for f in fournisseurs]
        
        combo = ttk.Combobox(parent, values=fournisseur_list, width=40)
        combo.pack(anchor=tk.W, padx=10, pady=5)
        
        # Bind selection event
        def on_combo_select(event):
            selected = combo.get()
            if selected:
                # Extract fournisseur data from "Name (Code)" format
                try:
                    name = selected.split("(")[0].strip()
                    code = selected.split("(")[1].rstrip(")")
                    fournisseur_data = {
                        'nom_fournisseur': name,
                        'code_fournisseur': code
                    }
                    on_select(fournisseur_data)
                except:
                    pass
        
        combo.bind("<<ComboboxSelected>>", on_combo_select)
        
        if fournisseur_list:
            combo.set(fournisseur_list[0])
            # Don't trigger initial selection here - let the dialog finish initializing first
        
        return combo
    
    def manage_taxes(self):
        """Open tax management dialog."""
        from stfoom.ui.achat_page import TaxesDialog
        TaxesDialog(self)
    
    def _add_tax_row(self, name_val="", value_val="", is_default=False):
        """Add a tax row to the taxes frame."""
        row = tk.Frame(self.taxes_frame)
        if is_default:
            tk.Label(row, text="TVA 19%", width=18).pack(side=tk.LEFT, padx=2)
            value_var = tk.StringVar(value=value_val)
            tk.Entry(row, textvariable=value_var, width=10).pack(side=tk.LEFT, padx=2)
            del_btn = tk.Label(row, text="(défaut)")
            del_btn.pack(side=tk.LEFT, padx=2)
            row.pack(pady=1)
            self.taxes_vars.append((None, value_var, row))
        else:
            from stfoom.logic import taxes as taxes_logic
            taxes = taxes_logic.get_all_taxes()
            tax_names = [t['name'] for t in taxes]
            tax_id_var = tk.StringVar()
            tax_combo = ttk.Combobox(row, textvariable=tax_id_var, values=tax_names, state="readonly", width=18)
            tax_combo.pack(side=tk.LEFT, padx=2)
            value_var = tk.StringVar(value=value_val)
            tk.Entry(row, textvariable=value_var, width=10).pack(side=tk.LEFT, padx=2)
            del_btn = tk.Button(row, text="Supprimer", command=lambda: self._remove_tax_row(row, tax_id_var))
            del_btn.pack(side=tk.LEFT, padx=2)
            row.pack(pady=1)
            self.taxes_vars.append((tax_id_var, value_var, row))

    def _remove_tax_row(self, row, tax_id_var):
        """Remove a tax row."""
        # Prevent removing TVA 19% default
        if tax_id_var is None:
            messagebox.showwarning("Action interdite", "TVA 19% ne peut pas être supprimée.")
            return
        for i, (n, _, r) in enumerate(self.taxes_vars):
            if r == row:
                r.destroy()
                self.taxes_vars.pop(i)
                break
    
    def load_initial_bls(self):
        """Load initial BLs for the first fournisseur."""
        if hasattr(self, 'selected_fournisseur') and self.selected_fournisseur:
            self.load_available_bls()
        else:
            # Get the first fournisseur and load their BLs
            fournisseurs = exec_read_all("SELECT code_fournisseur, nom_fournisseur FROM fournisseurs ORDER BY nom_fournisseur")
            if fournisseurs:
                first_fournisseur = {
                    'nom_fournisseur': fournisseurs[0][1],
                    'code_fournisseur': fournisseurs[0][0]
                }
                self.selected_fournisseur = first_fournisseur
                self.fournisseur_var.set(first_fournisseur['nom_fournisseur'])
                self.load_available_bls()
    
    def load_available_bls(self):
        """Load available BLs for the selected fournisseur."""
        # Clear existing items
        for item in self.bls_tree.get_children():
            self.bls_tree.delete(item)
        
        if not self.selected_fournisseur:
            return
        
        fournisseur_code = self.selected_fournisseur.get('code_fournisseur')
        if not fournisseur_code:
            return
        
        # Get BLs en attente for this fournisseur
        bls = get_bls_en_attente(fournisseur_code)
        
        # Add to treeview
        for bl in bls:
            statut_display = {
                "en_attente": "En Attente",
                "facturee": "Facturée",
                "annulee": "Annulée"
            }.get(bl.statut, bl.statut)
            
            self.bls_tree.insert("", tk.END, values=(
                bl.numero,
                bl.date_livraison.strftime("%d/%m/%Y"),
                f"{bl.quantite} {bl.unite}",
                format_money(bl.montant),
                statut_display
            ), tags=(str(bl.id),))
    
    def add_bl_to_facture(self):
        """Add selected BL to facture."""
        selection = self.bls_tree.selection()
        if not selection:
            messagebox.showwarning("Aucune sélection", "Veuillez sélectionner un BL à ajouter")
            return
        
        bl_id = int(self.bls_tree.item(selection[0], "tags")[0])
        bl_data = self.bls_tree.item(selection[0], "values")
        
        # Check if BL is already selected
        if any(bl['id'] == bl_id for bl in self.selected_bls):
            messagebox.showwarning("BL déjà sélectionné", "Ce BL est déjà inclus dans la facture")
            return
        
        # Add to selected BLs
        self.selected_bls.append({
            'id': bl_id,
            'numero': bl_data[0],
            'montant': float(bl_data[3].replace(' DT', ''))
        })
        
        # Update montant total
        self.update_montant_total()
        
        messagebox.showinfo("Succès", f"BL {bl_data[0]} ajouté à la facture")
    
    def remove_bl_from_facture(self):
        """Remove BL from facture."""
        if not self.selected_bls:
            messagebox.showwarning("Aucun BL", "Aucun BL sélectionné pour cette facture")
            return
        
        # Show dialog to select BL to remove
        bl_list = [f"{bl['numero']} - {bl['montant']:.3f} DT" for bl in self.selected_bls]
        selected = simpledialog.askstring("Retirer BL", "Entrez le numéro du BL à retirer:")
        
        if selected:
            # Find and remove BL
            for i, bl in enumerate(self.selected_bls):
                if bl['numero'] == selected:
                    removed_bl = self.selected_bls.pop(i)
                    self.update_montant_total()
                    messagebox.showinfo("Succès", f"BL {removed_bl['numero']} retiré de la facture")
                    return
            
            messagebox.showwarning("BL introuvable", "BL non trouvé dans la facture")
    
    def update_montant_total(self):
        """Update montant total based on selected BLs."""
        total_bls = sum(bl['montant'] for bl in self.selected_bls)
        self.montant_total_var.set(f"{total_bls:.3f}")
    
    def load_facture_data(self, facture_id):
        """Load existing facture data for editing."""
        from stfoom.logic.ciment import get_ciment_facture
        
        facture = get_ciment_facture(facture_id)
        if not facture:
            messagebox.showerror("Erreur", "Facture introuvable")
            self.destroy()
            return
        
        # Load facture data
        self.numero_facture_var.set(facture.numero_facture)
        self.date_entry.set_date(facture.date_facture)
        self.montant_ht_var.set(str(facture.montant_ht))
        self.timbre_var.set("0")  # Default timbre for existing factures
        self.montant_total_var.set(str(facture.montant_total))
        
        # Load taxes - set TVA 19% value
        if self.taxes_vars and len(self.taxes_vars) > 0:
            self.taxes_vars[0][1].set(str(facture.tva))
        if facture.date_echeance:
            self.date_echeance_entry.set_date(facture.date_echeance)
        if facture.notes:
            self.notes_text.insert("1.0", facture.notes)
        
        # Load fournisseur
        if facture.fournisseur_nom:
            self.fournisseur_var.set(facture.fournisseur_nom)
        
        # Load BLs
        if facture.bls_inclus:
            self.selected_bls = [
                {
                    'id': bl.id,
                    'numero': bl.numero,
                    'montant': bl.montant
                }
                for bl in facture.bls_inclus
            ]
    
    def save(self):
        """Save the facture."""
        try:
            # Validate inputs
            numero_facture = self.numero_facture_var.get().strip()
            if not numero_facture:
                messagebox.showerror("Erreur", "Le numéro de facture est requis")
                return
            
            date_facture = self.date_entry.get_date()
            if not date_facture:
                messagebox.showerror("Erreur", "La date de facture est requise")
                return
            
            if not self.selected_fournisseur:
                messagebox.showerror("Erreur", "Le fournisseur est requis")
                return
            
            try:
                montant_ht = float(self.montant_ht_var.get())
                timbre = float(self.timbre_var.get())
                montant_total = float(self.montant_total_var.get())
                
                # Calculate taxes from tax rows
                taxes = [
                    {'name': 'TVA 19%', 'value': float(self.taxes_vars[0][1].get().replace(",", ".")) if self.taxes_vars[0][1].get().strip() else 0}
                ] + [
                    {'name': n.get(), 'value': float(v.get().replace(",", ".")) if v.get().strip() else 0}
                    for n, v, _ in self.taxes_vars[1:] if n and n.get()
                ]
                
                # Calculate total tax amount
                total_taxes = sum(tax['value'] for tax in taxes)
                
            except ValueError:
                messagebox.showerror("Erreur", "Les montants doivent être des nombres")
                return
            
            date_echeance = self.date_echeance_entry.get_date()
            notes = self.notes_text.get(1.0, tk.END).strip()
            
            # Get BL IDs
            bl_ids = [bl['id'] for bl in self.selected_bls]
            
            if self.facture_id:
                # Update existing facture
                from stfoom.logic.ciment import update_ciment_facture
                success, message = update_ciment_facture(
                    facture_id=self.facture_id,
                    numero_facture=numero_facture,
                    date_facture=date_facture,
                    fournisseur_id=self.selected_fournisseur['code_fournisseur'],
                    montant_total=montant_total,
                    montant_ht=montant_ht,
                    tva=total_taxes,
                    date_echeance=date_echeance,
                    notes=notes if notes else None
                )
            else:
                # Create new facture
                success, message, facture_id = create_ciment_facture(
                    numero_facture=numero_facture,
                    date_facture=date_facture,
                    fournisseur_id=self.selected_fournisseur['code_fournisseur'],
                    montant_total=montant_total,
                    montant_ht=montant_ht,
                    tva=total_taxes,  # Use total taxes instead of just TVA
                    timbre=timbre,  # Pass timbre
                    taxes=taxes,  # Pass full tax structure
                    date_echeance=date_echeance,
                    notes=notes if notes else None,
                    bl_ids=bl_ids,
                    created_by=self.parent.current_user_id
                )
            
            if success:
                messagebox.showinfo("Succès", message)
                self.result = True
                self.destroy()
            else:
                messagebox.showerror("Erreur", message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
    
    def cancel(self):
        """Cancel the dialog."""
        self.destroy() 
 
 c l a s s   F a c t u r e N u m e r o D i a l o g ( t k . T o p l e v e l ) : 
 
         " " " D i a l o g   f o r   s e t t i n g   f a c t u r e   n u m b e r . " " " 
 
         
 
         d e f   _ _ i n i t _ _ ( s e l f ,   p a r e n t ,   t i t l e ) : 
 
                 s u p e r ( ) . _ _ i n i t _ _ ( p a r e n t ) 
 
                 s e l f . p a r e n t   =   p a r e n t 
 
                 s e l f . r e s u l t   =   N o n e 
 
                 
 
                 s e l f . t i t l e ( t i t l e ) 
 
                 s e l f . g e o m e t r y ( " 4 0 0 x 1 5 0 " ) 
 
                 s e l f . r e s i z a b l e ( F a l s e ,   F a l s e ) 
 
                 
 
                 #   C e n t e r   w i n d o w 
 
                 s e l f . t r a n s i e n t ( p a r e n t ) 
 
                 s e l f . g r a b _ s e t ( ) 
 
                 
 
                 s e l f . s e t u p _ u i ( ) 
 
                 s e l f . c e n t e r _ w i n d o w ( ) 
 
         
 
         d e f   s e t u p _ u i ( s e l f ) : 
 
                 " " " S e t u p   t h e   d i a l o g   U I . " " " 
 
                 #   M a i n   f r a m e 
 
                 m a i n _ f r a m e   =   t t k . F r a m e ( s e l f ,   p a d d i n g = " 2 0 " ) 
 
                 m a i n _ f r a m e . p a c k ( f i l l = t k . B O T H ,   e x p a n d = T r u e ) 
 
                 
 
                 #   F a c t u r e   n u m b e r 
 
                 t t k . L a b e l ( m a i n _ f r a m e ,   t e x t = " N u m � � r o   d e   f a c t u r e : " ) . p a c k ( a n c h o r = t k . W ,   p a d y = ( 0 ,   5 ) ) 
 
                 s e l f . n u m e r o _ v a r   =   t k . S t r i n g V a r ( ) 
 
                 s e l f . n u m e r o _ e n t r y   =   t t k . E n t r y ( m a i n _ f r a m e ,   t e x t v a r i a b l e = s e l f . n u m e r o _ v a r ,   w i d t h = 3 0 ) 
 
                 s e l f . n u m e r o _ e n t r y . p a c k ( f i l l = t k . X ,   p a d y = ( 0 ,   2 0 ) ) 
 
                 s e l f . n u m e r o _ e n t r y . f o c u s ( ) 
 
                 
 
                 #   B u t t o n s 
 
                 b u t t o n s _ f r a m e   =   t t k . F r a m e ( m a i n _ f r a m e ) 
 
                 b u t t o n s _ f r a m e . p a c k ( f i l l = t k . X ) 
 
                 
 
                 t t k . B u t t o n ( b u t t o n s _ f r a m e ,   t e x t = " A n n u l e r " ,   c o m m a n d = s e l f . c a n c e l ) . p a c k ( s i d e = t k . R I G H T ,   p a d x = ( 1 0 ,   0 ) ) 
 
                 t t k . B u t t o n ( b u t t o n s _ f r a m e ,   t e x t = " V a l i d e r " ,   c o m m a n d = s e l f . v a l i d a t e ) . p a c k ( s i d e = t k . R I G H T ) 
 
                 
 
                 #   B i n d   E n t e r   k e y 
 
                 s e l f . b i n d ( ' < R e t u r n > ' ,   l a m b d a   e :   s e l f . v a l i d a t e ( ) ) 
 
                 s e l f . b i n d ( ' < E s c a p e > ' ,   l a m b d a   e :   s e l f . c a n c e l ( ) ) 
 
         
 
         d e f   c e n t e r _ w i n d o w ( s e l f ) : 
 
                 " " " C e n t e r   t h e   w i n d o w   o n   p a r e n t . " " " 
 
                 s e l f . u p d a t e _ i d l e t a s k s ( ) 
 
                 x   =   ( s e l f . p a r e n t . w i n f o _ r o o t x ( )   +   ( s e l f . p a r e n t . w i n f o _ w i d t h ( )   / /   2 ) )   -   ( s e l f . w i n f o _ w i d t h ( )   / /   2 ) 
 
                 y   =   ( s e l f . p a r e n t . w i n f o _ r o o t y ( )   +   ( s e l f . p a r e n t . w i n f o _ h e i g h t ( )   / /   2 ) )   -   ( s e l f . w i n f o _ h e i g h t ( )   / /   2 ) 
 
                 s e l f . g e o m e t r y ( f " + { x } + { y } " ) 
 
         
 
         d e f   v a l i d a t e ( s e l f ) : 
 
                 " " " V a l i d a t e   a n d   s a v e . " " " 
 
                 n u m e r o   =   s e l f . n u m e r o _ v a r . g e t ( ) . s t r i p ( ) 
 
                 i f   n o t   n u m e r o : 
 
                         m e s s a g e b o x . s h o w e r r o r ( " E r r e u r " ,   " V e u i l l e z   s a i s i r   u n   n u m � � r o   d e   f a c t u r e " ) 
 
                         r e t u r n 
 
                 
 
                 s e l f . r e s u l t   =   { ' n u m e r o _ f a c t u r e ' :   n u m e r o } 
 
                 s e l f . d e s t r o y ( ) 
 
         
 
         d e f   c a n c e l ( s e l f ) : 
 
                 " " " C a n c e l   t h e   d i a l o g . " " " 
 
                 s e l f . d e s t r o y ( ) 
 
 
 
 
 
 c l a s s   A v o i r A m o u n t D i a l o g ( t k . T o p l e v e l ) : 
 
         " " " D i a l o g   f o r   s e t t i n g   a v o i r   a m o u n t . " " " 
 
         
 
         d e f   _ _ i n i t _ _ ( s e l f ,   p a r e n t ,   t i t l e ) : 
 
                 s u p e r ( ) . _ _ i n i t _ _ ( p a r e n t ) 
 
                 s e l f . p a r e n t   =   p a r e n t 
 
                 s e l f . r e s u l t   =   N o n e 
 
                 
 
                 s e l f . t i t l e ( t i t l e ) 
 
                 s e l f . g e o m e t r y ( " 4 0 0 x 1 5 0 " ) 
 
                 s e l f . r e s i z a b l e ( F a l s e ,   F a l s e ) 
 
                 
 
                 #   C e n t e r   w i n d o w 
 
                 s e l f . t r a n s i e n t ( p a r e n t ) 
 
                 s e l f . g r a b _ s e t ( ) 
 
                 
 
                 s e l f . s e t u p _ u i ( ) 
 
                 s e l f . c e n t e r _ w i n d o w ( ) 
 
         
 
         d e f   s e t u p _ u i ( s e l f ) : 
 
                 " " " S e t u p   t h e   d i a l o g   U I . " " " 
 
                 #   M a i n   f r a m e 
 
                 m a i n _ f r a m e   =   t t k . F r a m e ( s e l f ,   p a d d i n g = " 2 0 " ) 
 
                 m a i n _ f r a m e . p a c k ( f i l l = t k . B O T H ,   e x p a n d = T r u e ) 
 
                 
 
                 #   A v o i r   a m o u n t 
 
                 t t k . L a b e l ( m a i n _ f r a m e ,   t e x t = " M o n t a n t   a v o i r   ( D T ) : " ) . p a c k ( a n c h o r = t k . W ,   p a d y = ( 0 ,   5 ) ) 
 
                 s e l f . a m o u n t _ v a r   =   t k . S t r i n g V a r ( ) 
 
                 s e l f . a m o u n t _ e n t r y   =   t t k . E n t r y ( m a i n _ f r a m e ,   t e x t v a r i a b l e = s e l f . a m o u n t _ v a r ,   w i d t h = 3 0 ) 
 
                 s e l f . a m o u n t _ e n t r y . p a c k ( f i l l = t k . X ,   p a d y = ( 0 ,   2 0 ) ) 
 
                 s e l f . a m o u n t _ e n t r y . f o c u s ( ) 
 
                 
 
                 #   B u t t o n s 
 
                 b u t t o n s _ f r a m e   =   t t k . F r a m e ( m a i n _ f r a m e ) 
 
                 b u t t o n s _ f r a m e . p a c k ( f i l l = t k . X ) 
 
                 
 
                 t t k . B u t t o n ( b u t t o n s _ f r a m e ,   t e x t = " A n n u l e r " ,   c o m m a n d = s e l f . c a n c e l ) . p a c k ( s i d e = t k . R I G H T ,   p a d x = ( 1 0 ,   0 ) ) 
 
                 t t k . B u t t o n ( b u t t o n s _ f r a m e ,   t e x t = " V a l i d e r " ,   c o m m a n d = s e l f . v a l i d a t e ) . p a c k ( s i d e = t k . R I G H T ) 
 
                 
 
                 #   B i n d   E n t e r   k e y 
 
                 s e l f . b i n d ( ' < R e t u r n > ' ,   l a m b d a   e :   s e l f . v a l i d a t e ( ) ) 
 
                 s e l f . b i n d ( ' < E s c a p e > ' ,   l a m b d a   e :   s e l f . c a n c e l ( ) ) 
 
         
 
         d e f   c e n t e r _ w i n d o w ( s e l f ) : 
 
                 " " " C e n t e r   t h e   w i n d o w   o n   p a r e n t . " " " 
 
                 s e l f . u p d a t e _ i d l e t a s k s ( ) 
 
                 x   =   ( s e l f . p a r e n t . w i n f o _ r o o t x ( )   +   ( s e l f . p a r e n t . w i n f o _ w i d t h ( )   / /   2 ) )   -   ( s e l f . w i n f o _ w i d t h ( )   / /   2 ) 
 
                 y   =   ( s e l f . p a r e n t . w i n f o _ r o o t y ( )   +   ( s e l f . p a r e n t . w i n f o _ h e i g h t ( )   / /   2 ) )   -   ( s e l f . w i n f o _ h e i g h t ( )   / /   2 ) 
 
                 s e l f . g e o m e t r y ( f " + { x } + { y } " ) 
 
         
 
         d e f   v a l i d a t e ( s e l f ) : 
 
                 " " " V a l i d a t e   a n d   s a v e . " " " 
 
                 t r y : 
 
                         a m o u n t _ s t r   =   s e l f . a m o u n t _ v a r . g e t ( ) . s t r i p ( ) . r e p l a c e ( " , " ,   " . " ) 
 
                         i f   n o t   a m o u n t _ s t r : 
 
                                 m e s s a g e b o x . s h o w e r r o r ( " E r r e u r " ,   " V e u i l l e z   s a i s i r   u n   m o n t a n t " ) 
 
                                 r e t u r n 
 
                         
 
                         a m o u n t   =   f l o a t ( a m o u n t _ s t r ) 
 
                         i f   a m o u n t   <   0 : 
 
                                 m e s s a g e b o x . s h o w e r r o r ( " E r r e u r " ,   " L e   m o n t a n t   d o i t   � � t r e   p o s i t i f " ) 
 
                                 r e t u r n 
 
                         
 
                         s e l f . r e s u l t   =   { ' a v o i r _ a m o u n t ' :   a m o u n t } 
 
                         s e l f . d e s t r o y ( ) 
 
                         
 
                 e x c e p t   V a l u e E r r o r : 
 
                         m e s s a g e b o x . s h o w e r r o r ( " E r r e u r " ,   " M o n t a n t   i n v a l i d e " ) 
 
         
 
         d e f   c a n c e l ( s e l f ) : 
 
                 " " " C a n c e l   t h e   d i a l o g . " " " 
 
                 s e l f . d e s t r o y ( ) 
 
 