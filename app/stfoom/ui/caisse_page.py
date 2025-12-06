import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
from tkcalendar import DateEntry
from .shared_widgets import format_money  # Import centralized money formatting
# from stfoom.logic import caisse  # Removed in Phase 3A - use CaisseService

class CaissePage(ttk.Frame):
    def __init__(self, parent, di_container=None, go_home=None):
        """
        Initialize CaissePage with dependency injection support.
        
        Args:
            parent: Parent widget
            di_container: Dependency injection container (for Phase 2E migration)
            go_home: Callback function to return to main menu
        """
        super().__init__(parent, style="FactureMain.TFrame")
        
        # Handle different constructor signatures for backward compatibility
        if go_home is None and hasattr(di_container, '__call__'):
            # Old signature: CaissePage(parent, go_home)
            self.go_home = di_container
            self.di_container = None
            self.caisse_service = None
        else:
            # New signature: CaissePage(parent, di_container, go_home)
            self.go_home = go_home
            self.di_container = di_container
            
            # Try to get caisse service from DI container
            try:
                if self.di_container:
                    self.caisse_service = self.di_container.get('caisse_service')
                    print("[CAISSE PAGE] Using CaisseService via dependency injection")
                else:
                    self.caisse_service = None
            except Exception as e:
                print(f"[CAISSE PAGE] Could not get CaisseService from container: {e}")
                self.caisse_service = None
        
        self.pack(fill="both", expand=True)
        self._create_ui()
        self._load_data()

    def _create_ui(self):
        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=self.go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Gestion Caisse", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- summary section ----------
        summary_frame = ttk.LabelFrame(self, text="Résumé", style="FactureSection.TLabelframe")
        summary_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        self.resume_label = ttk.Label(summary_frame, text="", font=("Segoe UI", 14, "bold"), foreground="#00796b", style="FactureRemise.TLabel")
        self.resume_label.pack(pady=10)

        # ---------- table section ----------
        table_frame = ttk.LabelFrame(self, text="Opérations Caisse", style="FactureSection.TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10), ipadx=8, ipady=8)

        # Table
        columns = ("date", "client_fournisseur", "encaissement", "decaissement", "nfacture", "desc")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16, style="Custom.Treeview")
        self.tree.heading("date", text="Date")
        self.tree.heading("client_fournisseur", text="Client/Fournisseur")
        self.tree.heading("encaissement", text="Encaissement")
        self.tree.heading("decaissement", text="Décaissement")
        self.tree.heading("nfacture", text="N° Facture")
        self.tree.heading("desc", text="Description")
        self.tree.column("date", width=90, anchor="center")
        self.tree.column("client_fournisseur", width=160, anchor="w")
        self.tree.column("encaissement", width=100, anchor="e")
        self.tree.column("decaissement", width=100, anchor="e")
        self.tree.column("nfacture", width=90, anchor="center")
        self.tree.column("desc", width=220, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        # Add tag styles
        self.tree.tag_configure("encaissement", background="#e6ffe6", foreground="#218838")
        self.tree.tag_configure("decaissement", background="#ffe6e6", foreground="#c82333")

        # ---------- action buttons ----------
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
        
        # Add transaction button (green)
        add_btn = tk.Button(
            btn_frame,
            text="➕ Nouvelle opération",
            command=self._add_transaction,
            font=("Segoe UI", 14, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        add_btn.grid(row=0, column=0, padx=10, sticky="ew", ipadx=20, ipady=8)
        
        # Modify button (blue) 
        self.modify_btn = tk.Button(
            btn_frame,
            text="✏️ Modifier",
            command=self._modify_selected,
            font=("Segoe UI", 14, "bold"),
            bg="#0074d9",
            fg="#fff",
            activebackground="#005fa3",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2",
            state="disabled"
        )
        self.modify_btn.grid(row=0, column=1, padx=10, sticky="ew", ipadx=20, ipady=8)
        
        # Delete button (red)
        self.delete_btn = tk.Button(
            btn_frame,
            text="❌ Supprimer",
            command=self._delete_selected,
            font=("Segoe UI", 14, "bold"),
            bg="#dc3545",
            fg="#fff",
            activebackground="#c82333",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2",
            state="disabled"
        )
        self.delete_btn.grid(row=0, column=2, padx=10, sticky="ew", ipadx=20, ipady=8)

    def _load_data(self):
        """Load transactions data from either service or legacy module."""
        try:
            # Clear existing items
            for i in self.tree.get_children():
                self.tree.delete(i)
            
            # Use service if available, otherwise fall back to legacy
            if self.caisse_service:
                txs = self.caisse_service.get_all_transactions()
                solde = self.caisse_service.get_balance()
                resume = self.caisse_service.get_period_summary()
                print(f"[CAISSE PAGE] Loaded {len(txs)} transactions via CaisseService")
            else:
                # Service should always be available after Phase 2
                print("Warning: CaisseService not available, initializing empty data")
                txs = []
                solde = 0.0
                resume = {"entrees": 0.0, "sorties": 0.0}
            
            # Display transactions in tree
            for t in txs:
                tag = t['type'] if t['type'] in ("encaissement", "decaissement") else ""
                enc = format_money(t['montant']) if t['type'] == 'encaissement' else ""
                dec = format_money(t['montant']) if t['type'] == 'decaissement' else ""
                # Show client/fournisseur if available (for achat/vente)
                client_fournisseur = t.get('nom_client') or t.get('client') or t.get('fournisseur') or ""
                # Show num_facture if available
                num_facture = t.get('num_facture') or t.get('nfacture') or ""
                self.tree.insert("", "end", iid=t['id'], values=(
                    t['date'],
                    client_fournisseur,
                    enc,
                    dec,
                    num_facture,
                    t.get('description') or ""
                ), tags=(tag,))
            
            # Update summary display
            self.resume_label.config(text=f"Solde: {format_money(solde)} | Encaissements: {format_money(resume['encaissements']['total'])} | Décaissements: {format_money(resume['decaissements']['total'])}")
            self.delete_btn.config(state="disabled")
            self.modify_btn.config(state="disabled")
            
        except Exception as e:
            print(f"[CAISSE PAGE] Error loading data: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des données: {e}")

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.delete_btn.config(state="normal")
            self.modify_btn.config(state="normal")
        else:
            self.delete_btn.config(state="disabled")
            self.modify_btn.config(state="disabled")

    def _delete_selected(self):
        """Delete selected transaction using service or legacy module."""
        sel = self.tree.selection()
        if sel:
            if messagebox.askyesno("Confirmer", "Supprimer cette opération ?"):
                try:
                    transaction_id = int(sel[0])
                    
                    # Use service if available, otherwise fall back to legacy
                    if self.caisse_service:
                        result = self.caisse_service.delete_transaction(transaction_id)
                        print(f"[CAISSE PAGE] Transaction {transaction_id} deleted via CaisseService: {result}")
                    else:
                        # Service should always be available after Phase 2
                        print(f"Warning: CaisseService not available, cannot delete transaction {transaction_id}")
                        result = False
                    
                    if result:
                        self._load_data()
                    else:
                        messagebox.showerror("Erreur", "Erreur lors de la suppression de la transaction")
                        
                except Exception as e:
                    print(f"[CAISSE PAGE] Error deleting transaction: {e}")
                    messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")

    def _modify_selected(self):
        """Modify selected transaction using service."""
        sel = self.tree.selection()
        if sel:
            try:
                transaction_id = int(sel[0])
                
                # Get transaction data
                if self.caisse_service:
                    transaction_data = self.caisse_service.get_transaction_by_id(transaction_id)
                    if transaction_data:
                        dialog = CaisseTransactionDialog(self, transaction_data)
                        if dialog.result:
                            self._load_data()
                    else:
                        messagebox.showerror("Erreur", "Transaction introuvable")
                else:
                    messagebox.showerror("Erreur", "Service caisse non disponible")
                        
            except Exception as e:
                print(f"[CAISSE PAGE] Error modifying transaction: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de la modification: {e}")

    def _add_transaction(self):
        dialog = CaisseTransactionDialog(self)
        if dialog.result:
            self._load_data()

class CaisseTransactionDialog:
    def __init__(self, parent, transaction_data=None):
        self.parent = parent
        self.result = False
        self.transaction_data = transaction_data  # None for add, data for modify
        self.window = tk.Toplevel(parent)
        
        if transaction_data:
            self.window.title("Modifier l'opération caisse")
        else:
            self.window.title("Nouvelle opération caisse")
            
        self.window.geometry("400x600")
        self._create_ui()
        
        if transaction_data:
            self._load_existing_data()
            
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_force()
        parent.wait_window(self.window)
    def _create_ui(self):
        ttk.Label(self.window, text="Type d'opération:").pack(pady=8)
        self.type_var = tk.StringVar(value="encaissement")
        ttk.Radiobutton(self.window, text="Encaissement", variable=self.type_var, value="encaissement").pack()
        ttk.Radiobutton(self.window, text="Décaissement", variable=self.type_var, value="decaissement").pack()
        ttk.Label(self.window, text="Montant (TND):").pack(pady=8)
        self.montant_var = tk.StringVar()
        ttk.Entry(self.window, textvariable=self.montant_var, width=15).pack()
        ttk.Label(self.window, text="Date (JJ/MM/AAAA):").pack(pady=8)
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.date_entry = DateEntry(self.window, textvariable=self.date_var, date_pattern="dd/MM/yyyy", width=15)
        self.date_entry.pack()
        ttk.Label(self.window, text="N° Facture (optionnel):").pack(pady=8)
        self.nfacture_var = tk.StringVar()
        ttk.Entry(self.window, textvariable=self.nfacture_var, width=15).pack()
        ttk.Label(self.window, text="Client/Fournisseur (optionnel):").pack(pady=8)
        self.client_var = tk.StringVar()
        ttk.Entry(self.window, textvariable=self.client_var, width=30).pack()
        
        ttk.Label(self.window, text="Description:").pack(pady=8)
        self.desc_text = tk.Text(self.window, height=3, width=30)
        self.desc_text.pack()
        
        btn_text = "Modifier" if self.transaction_data else "Enregistrer"
        ttk.Button(self.window, text=btn_text, command=self._save).pack(pady=12)
        ttk.Button(self.window, text="Annuler", command=self.window.destroy).pack()
    
    def _load_existing_data(self):
        """Load existing transaction data for modification."""
        if not self.transaction_data:
            return
            
        # Set type
        self.type_var.set(self.transaction_data.get('type', 'encaissement'))
        
        # Set amount
        self.montant_var.set(str(self.transaction_data.get('montant', '')))
        
        # Set date
        if 'date' in self.transaction_data:
            try:
                # Convert from database format to display format
                date_obj = datetime.strptime(self.transaction_data['date'], "%Y-%m-%d")
                self.date_var.set(date_obj.strftime("%d/%m/%Y"))
            except:
                self.date_var.set(self.transaction_data['date'])
        
        # Set invoice number
        nfacture = self.transaction_data.get('num_facture') or self.transaction_data.get('nfacture', '')
        self.nfacture_var.set(str(nfacture) if nfacture else '')
        
        # Set client/fournisseur
        client = self.transaction_data.get('nom_client') or self.transaction_data.get('client') or self.transaction_data.get('fournisseur', '')
        self.client_var.set(client)
        
        # Set description
        desc = self.transaction_data.get('description', '')
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", desc)
    def _save(self):
        try:
            montant = float(self.montant_var.get().replace(",", "."))
            if montant <= 0:
                raise ValueError("Montant doit être positif")
            date_str = datetime.strptime(self.date_var.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            type_ = self.type_var.get()
            desc = self.desc_text.get("1.0", "end").strip()
            nfacture = int(self.nfacture_var.get()) if self.nfacture_var.get().strip() else None
            client = self.client_var.get().strip()
            
            # Use service if available, otherwise fall back to legacy
            if hasattr(self.parent, 'caisse_service') and self.parent.caisse_service:
                if self.transaction_data:
                    # Modify existing transaction
                    result = self.parent.caisse_service.update_transaction(
                        transaction_id=self.transaction_data['id'],
                        montant=montant,
                        date=date_str,
                        type=type_,
                        description=desc,
                        num_facture=nfacture,
                        client=client
                    )
                    success_msg = "Opération modifiée."
                    print(f"[CAISSE DIALOG] Transaction modified via CaisseService: {result}")
                else:
                    # Create new transaction
                    result = self.parent.caisse_service.create_transaction(
                        montant=montant,
                        date=date_str,
                        type=type_,
                        description=desc,
                        num_facture=nfacture,
                        client=client
                    )
                    success_msg = "Opération ajoutée."
                    print(f"[CAISSE DIALOG] Transaction created via CaisseService: {result}")
            else:
                # Service should always be available after Phase 2
                print("Warning: CaisseService not available, cannot save transaction")
                result = False
            
            if result:
                messagebox.showinfo("Succès", success_msg)
                self.result = True
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", "Erreur lors de la sauvegarde.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}") 