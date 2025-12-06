import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
# from stfoom.logicold import retenu  # DISABLED: migrated to RetenuService
# from stfoom.logic import vente  # Removed - not needed after Phase 2
from tkcalendar import Calendar, DateEntry

class RetenuPage(ttk.Frame):
    def __init__(self, parent, di_container_or_go_home, go_home=None):
        """
        Initialize RetenuPage with dependency injection support.
        
        Args:
            parent: Parent widget
            di_container_or_go_home: DI container (new) or go_home callback (legacy)
            go_home: Go home callback (new) or None (legacy)
        """
        super().__init__(parent, style="FactureMain.TFrame")
        
        # Handle different constructor signatures for backward compatibility
        if go_home is None:
            # Old signature: RetenuPage(parent, go_home)
            self.go_home = di_container_or_go_home
            self.di_container = None
            self.retenu_service = None
            print("[RETENU PAGE] Using legacy mode (no dependency injection)")
        else:
            # New signature: RetenuPage(parent, di_container, go_home)
            self.go_home = go_home
            self.di_container = di_container_or_go_home
            
            # Try to get retenu service from DI container
            try:
                if self.di_container and hasattr(self.di_container, 'get'):
                    self.retenu_service = self.di_container.get('retenu_service')
                    print("[RETENU PAGE] Using RetenuService via dependency injection")
                else:
                    self.retenu_service = None
                    print("[RETENU PAGE] No valid DI container, falling back to legacy mode")
            except Exception as e:
                print(f"[RETENU PAGE] Could not get RetenuService from container: {e}")
                self.retenu_service = None
                print("[RETENU PAGE] Falling back to legacy mode due to service error")
        
        self.pack(fill="both", expand=True)
        self._create_ui()
        self._load_data()

    def _create_ui(self):
        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=self.go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Récapitulatif des Retenus", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- filters section ----------
        filter_frame = ttk.LabelFrame(self, text="Filtres", style="FactureSection.TLabelframe")
        filter_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        filter_inner = ttk.Frame(filter_frame)
        filter_inner.pack(fill="x", padx=10, pady=5)
        ttk.Label(filter_inner, text="Client:").pack(side="left")
        self.client_var = tk.StringVar()
        self.client_entry = ttk.Combobox(filter_inner, textvariable=self.client_var, width=20)
        self.client_entry.pack(side="left", padx=5)
        ttk.Label(filter_inner, text="Facture:").pack(side="left")
        self.facture_var = tk.StringVar()
        self.facture_entry = ttk.Combobox(filter_inner, textvariable=self.facture_var, width=10)
        self.facture_entry.pack(side="left", padx=5)
        ttk.Button(filter_inner, text="Filtrer", command=self._load_data).pack(side="left", padx=8)
        reset_btn = ttk.Button(filter_inner, text="Réinitialiser", command=self._reset_filters)
        reset_btn.pack(side="left", padx=8)
        reset_btn.bind("<Enter>", lambda e: self._show_tooltip(reset_btn, "Réinitialiser = afficher toutes les retenues"))
        reset_btn.bind("<Leave>", lambda e: self._hide_tooltip())

        # ---------- table section ----------
        table_frame = ttk.LabelFrame(self, text="Liste des Retenus", style="FactureSection.TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10), ipadx=8, ipady=8)

        # Table
        columns = ("date", "nom", "methode_paiement", "num_facture", "retenu_client", "retenu_fournisseur", "notes")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16, style="Custom.Treeview")
        for col, label, w in zip(columns,
            ["Date", "Nom", "Méthode", "Numéro Facture", "Retenu Client", "Retenu Fournisseur", "Notes"],
            [90, 150, 100, 120, 120, 120, 200]):
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor="center" if col!="notes" else "w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)
        # Add tag styles
        self.tree.tag_configure("client", background="#e6ffe6", foreground="#218838")
        self.tree.tag_configure("fournisseur", background="#ffe6e6", foreground="#c82333")

        # ---------- action buttons ----------
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
        
        # Add Retenu button (green)
        add_btn = tk.Button(
            btn_frame,
            text="➕ Ajouter Retenu",
            command=self._add_retenu,
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
        
        # Delete button (red)
        self.delete_btn = tk.Button(
            btn_frame,
            text="❌ Supprimer la retenue sélectionnée",
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
        self.delete_btn.grid(row=0, column=1, padx=10, sticky="ew", ipadx=20, ipady=8)
        
        # Edit button (blue)
        self.edit_btn = tk.Button(
            btn_frame,
            text="✏️ Modifier",
            command=self._edit_selected,
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
        self.edit_btn.grid(row=0, column=2, padx=10, sticky="ew", ipadx=20, ipady=8)

        # ---------- summary section ----------
        summary_frame = ttk.LabelFrame(self, text="Résumé", style="FactureSection.TLabelframe")
        summary_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        self.summary_label = ttk.Label(summary_frame, text="", font=("Segoe UI", 14, "bold"), foreground="#00796b", style="FactureRemise.TLabel")
        self.summary_label.pack(pady=10)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _reset_filters(self):
        self.client_var.set("")
        self.facture_var.set("")
        self._load_data()

    def _load_data(self):
        """Load retenu data from either service or legacy module."""
        try:
            self.tree.delete(*self.tree.get_children())
            
            # Use service if available, otherwise fall back to legacy
            if self.retenu_service:
                all_retenus = self.retenu_service.get_all_retenus()
                print(f"[RETENU PAGE] Loaded {len(all_retenus)} retenus via RetenuService")
            else:
                all_retenus = self.retenu_service.get_all_retenus() if self.retenu_service else []
                print(f"[RETENU PAGE] Loaded {len(all_retenus)} retenus via legacy module")
            
            # Populate filters
            clients = sorted(set(r['client'] for r in all_retenus if r['client']))
            self.client_entry['values'] = clients
            factures = sorted(set(str(r['nfacture']) for r in all_retenus if r['nfacture']))
            self.facture_entry['values'] = factures
            
            # Filter
            filtered = all_retenus
            if self.client_var.get():
                filtered = [r for r in filtered if r['client'] == self.client_var.get()]
            if self.facture_var.get():
                filtered = [r for r in filtered if str(r['nfacture']) == self.facture_var.get()]
            
            for r in filtered:
                # Determine type preferring new party_type classification if available
                party_type = r.get('party_type')
                if party_type in ('client','fournisseur'):
                    is_fournisseur = party_type == 'fournisseur'
                else:
                    # Fallback legacy heuristic
                    source = r.get('source', 'vente')
                    is_fournisseur = source == 'achat'
                tag = 'fournisseur' if is_fournisseur else 'client'
                
                # Show retenu amount in correct column
                amount = r.get('retenu_amount', r.get('amount', 0.0)) or 0.0
                retenu_client = f"{amount:.3f}" if not is_fournisseur else ""
                retenu_fournisseur = f"{amount:.3f}" if is_fournisseur else ""
                
                # Get facture number
                num_facture = r.get('num_facture') or r.get('nfacture') or ""
                
                # Get payment method from the payment that created this retenu
                methode_paiement = ""
                try:
                    # Try to get payment method from retenu record itself first
                    if 'methode_paiement' in r and r['methode_paiement']:
                        methode_paiement = r['methode_paiement']
                    elif 'mode_paiement' in r and r['mode_paiement']:
                        methode_paiement = r['mode_paiement']
                    else:
                        # Fall back to getting from payments
                        if self.di_container:
                            payment_service = self.di_container.get('payment_service', None)
                            if payment_service:
                                paiements = payment_service.get_payments_for_invoice(r['nfacture'])
                                for p in paiements:
                                    if p.get('notes', '').startswith('[Retenu:') or 'retenu' in p.get('description', '').lower():
                                        methode_paiement = p.get('mode_paiement', '')
                                        if methode_paiement:
                                            # Format payment method for display
                                            method_mapping = {
                                                'carte': 'Carte',
                                                'cheque': 'Chèque', 
                                                'virement': 'Virement',
                                                'especes': 'Espèces',
                                                'traite': 'Traite'
                                            }
                                            methode_paiement = method_mapping.get(methode_paiement, methode_paiement)
                                        break
                except Exception as e:
                    print(f"[RETENU PAGE] Error getting payment method: {e}")
                    methode_paiement = "N/A"
                
                self.tree.insert("", "end", iid=r['id'], values=(
                    r['date'], r['client'], methode_paiement, num_facture, retenu_client, retenu_fournisseur, r['notes'] or ""
                ), tags=(tag,))
            
            # Summary
            if self.retenu_service:
                summary = self.retenu_service.get_summary()
            else:
                summary = self.retenu_service.get_summary() if self.retenu_service else {"total": 0, "by_client": {}}
            
            self.summary_label.config(text=f"Total retenu: {summary['total']:.3f} | Par client: {', '.join(f'{k}: {v:.3f}' for k,v in summary['by_client'].items())}")
            self.delete_btn.config(state="disabled")
            self.edit_btn.config(state="disabled")
            
        except Exception as e:
            print(f"[RETENU PAGE] Error loading data: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des données: {e}")

    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.delete_btn.config(state="normal")
            self.edit_btn.config(state="normal")
        else:
            self.delete_btn.config(state="disabled")
            self.edit_btn.config(state="disabled")

    def _delete_selected(self):
        sel = self.tree.selection()
        if sel:
            if messagebox.askyesno("Confirmer", "Supprimer cette retenue ?"):
                if self.retenu_service:
                    self.retenu_service.delete_retenu(int(sel[0]))
                self._load_data()

    def _edit_selected(self):
        sel = self.tree.selection()
        if sel:
            all_retenus = self.retenu_service.get_all_retenus() if self.retenu_service else []
            r = [x for x in all_retenus if x['id'] == int(sel[0])][0]
            dialog = RetenuDialog(self, preset=r, retenu_service=self.retenu_service)
            if dialog.result:
                self._load_data()

    def _add_retenu(self):
        dialog = RetenuDialog(self, retenu_service=self.retenu_service, di_container=self.di_container)
        if dialog.result:
            self._load_data()

    def _show_tooltip(self, widget, text):
        self._tooltip = tk.Toplevel(widget)
        self._tooltip.wm_overrideredirect(True)
        x = widget.winfo_rootx() + 20
        y = widget.winfo_rooty() + 20
        self._tooltip.wm_geometry(f"+{x}+{y}")
        label = tk.Label(self._tooltip, text=text, background="#ffffe0", relief="solid", borderwidth=1, font=("Arial", 10))
        label.pack()
    def _hide_tooltip(self):
        if hasattr(self, '_tooltip') and self._tooltip:
            self._tooltip.destroy()
            self._tooltip = None

class RetenuDialog:
    def __init__(self, parent, preset=None, retenu_service=None, di_container=None):
        self.parent = parent
        self.result = False
        self.preset = preset
        self.retenu_service = retenu_service
        self.di_container = di_container
        self.window = tk.Toplevel(parent)
        self.window.title("Ajouter une retenue" if not preset else "Modifier la retenue")
        self.window.geometry("420x520")
        self.window.resizable(True, True)
        self._create_ui()
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_force()
        parent.wait_window(self.window)
    def _create_ui(self):
        # --- Scrollable main content ---
        content_frame = ttk.Frame(self.window)
        content_frame.pack(fill="both", expand=True)
        canvas = tk.Canvas(content_frame, bg='white', highlightthickness=0)
        scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        # Date
        tk.Label(scrollable_frame, text="Date (JJ/MM/AAAA):").pack(pady=6)
        self.date_var = tk.StringVar(value=self.preset['date'] if self.preset else date.today().strftime("%d/%m/%Y"))
        self.date_entry = DateEntry(scrollable_frame, textvariable=self.date_var, date_pattern="dd/MM/yyyy", width=15)
        self.date_entry.pack(pady=4)
        # Radio buttons for Client/Fournisseur
        self.type_var = tk.StringVar(value="client" if (self.preset is None or (self.preset and self.preset.get('client'))) else "fournisseur")
        type_frame = tk.Frame(scrollable_frame)
        type_frame.pack(pady=6)
        tk.Label(type_frame, text="Type:").pack(side="left")
        tk.Radiobutton(type_frame, text="Client", variable=self.type_var, value="client", command=self._on_type_change).pack(side="left", padx=8)
        tk.Radiobutton(type_frame, text="Fournisseur", variable=self.type_var, value="fournisseur", command=self._on_type_change).pack(side="left", padx=8)
        # Client/Fournisseur fields
        self.client_frame = tk.Frame(scrollable_frame)
        self.fournisseur_frame = tk.Frame(scrollable_frame)
        # Client selection
        self.client_var = tk.StringVar(value=self.preset['client'] if self.preset and self.type_var.get()=="client" else "")
        self.client_entry = ttk.Combobox(self.client_frame, textvariable=self.client_var, width=30)
        self.client_entry.pack(pady=2)
        self.client_entry.bind("<<ComboboxSelected>>", self._on_client_selected)
        # Facture selection for client
        self.nfacture_var = tk.StringVar(value=str(self.preset['nfacture']) if self.preset and self.preset['nfacture'] else "")
        self.nfacture_entry = ttk.Combobox(self.client_frame, textvariable=self.nfacture_var, width=20)
        self.nfacture_entry.pack(pady=2)
        self.nfacture_entry.bind("<<ComboboxSelected>>", self._on_facture_selected)
        # Fournisseur entry
        self.fournisseur_var = tk.StringVar(value=self.preset['client'] if self.preset and self.type_var.get()=="fournisseur" else "")
        tk.Label(self.fournisseur_frame, text="Fournisseur:").pack()
        self.fournisseur_entry = tk.Entry(self.fournisseur_frame, textvariable=self.fournisseur_var, width=30)
        self.fournisseur_entry.pack(pady=2)
        # Facture entry for fournisseur
        self.nfacture_f_var = tk.StringVar(value=str(self.preset['nfacture']) if self.preset and self.preset['nfacture'] else "")
        tk.Label(self.fournisseur_frame, text="Facture (N°):").pack()
        self.nfacture_f_entry = tk.Entry(self.fournisseur_frame, textvariable=self.nfacture_f_var, width=20)
        self.nfacture_f_entry.pack(pady=2)
        # Populate initial values
        self._populate_clients_and_factures()
        # Show correct frame
        self._on_type_change()
        # Retenu fields
        tk.Label(scrollable_frame, text="Retenu (%):").pack(pady=6)
        
        # 🔧 Fix: Safely format retenu_percent (handle both string and float)
        if self.preset and 'retenu_percent' in self.preset:
            try:
                percent_value = float(self.preset['retenu_percent'])
                percent_str = f"{percent_value:.3f}"
            except (ValueError, TypeError):
                percent_str = str(self.preset['retenu_percent'])
        else:
            percent_str = ""
        
        self.percent_var = tk.StringVar(value=percent_str)
        tk.Entry(scrollable_frame, textvariable=self.percent_var, width=10).pack()
        
        tk.Label(scrollable_frame, text="Montant retenu:").pack(pady=6)
        
        # 🔧 Fix: Safely format retenu_amount (handle both string and float)
        if self.preset and 'retenu_amount' in self.preset:
            try:
                amount_value = float(self.preset['retenu_amount'])
                amount_str = f"{amount_value:.3f}"
            except (ValueError, TypeError):
                amount_str = str(self.preset['retenu_amount'])
        else:
            amount_str = ""
        
        self.amount_var = tk.StringVar(value=amount_str)
        tk.Entry(scrollable_frame, textvariable=self.amount_var, width=15).pack()
        tk.Label(scrollable_frame, text="Notes:").pack(pady=6)
        self.notes_text = tk.Text(scrollable_frame, height=3, width=30)
        if self.preset:
            self.notes_text.insert("1.0", self.preset.get('notes', ''))
        self.notes_text.pack()
        # --- Button section (always visible at bottom) ---
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill="x", pady=(10, 0), side="bottom")
        tk.Button(btn_frame, text="Enregistrer", bg="#28a745", fg="white", command=self._save).pack(side="right", padx=(0, 10))
        tk.Button(btn_frame, text="Annuler", command=self.window.destroy).pack(side="right")
    def _on_type_change(self):
        # Hide both, then show the right one in the correct place (after date/type)
        self.client_frame.pack_forget()
        self.fournisseur_frame.pack_forget()
        # Find the widget after which to insert
        # The first widgets are: date entry, type_frame
        # We'll always pack after type_frame
        children = list(self.window.children.values())
        type_frame = None
        for w in children:
            if isinstance(w, tk.Frame) and any(isinstance(c, tk.Radiobutton) for c in w.winfo_children()):
                type_frame = w
                break
        if self.type_var.get() == "client":
            if type_frame:
                self.client_frame.pack(pady=6, after=type_frame)
            else:
                self.client_frame.pack(pady=6)
        else:
            if type_frame:
                self.fournisseur_frame.pack(pady=6, after=type_frame)
            else:
                self.fournisseur_frame.pack(pady=6)
    def _populate_clients_and_factures(self):
        # Get sales data from sales service if available
        sales_service = self.di_container.get('sales_service') if self.di_container else None
        ventes = sales_service.get_all_sales() if sales_service else []
        clients = sorted(set(f['raison_sociale'] for f in ventes if f.get('raison_sociale')))
        self.client_entry['values'] = clients
        self.all_factures = ventes
        if self.client_var.get():
            self._update_facture_list_for_client(self.client_var.get())
        else:
            self.nfacture_entry['values'] = [str(f['nfacture']) for f in ventes]
    def _on_client_selected(self, event=None):
        client = self.client_var.get()
        self._update_facture_list_for_client(client)
    def _update_facture_list_for_client(self, client):
        factures = [f for f in self.all_factures if f.get('raison_sociale') == client]
        self.nfacture_entry['values'] = [str(f['nfacture']) for f in factures]
        if factures:
            self.nfacture_var.set(str(factures[0]['nfacture']))
    def _on_facture_selected(self, event=None):
        nfacture = self.nfacture_var.get()
        if nfacture:
            for f in self.all_factures:
                if str(f['nfacture']) == nfacture:
                    self.client_var.set(f.get('raison_sociale', ''))
                    break
    def _save(self):
        try:
            date_str = self.date_var.get().strip()
            if self.type_var.get() == "client":
                client = self.client_var.get().strip()
                nfacture = int(self.nfacture_var.get()) if self.nfacture_var.get().strip() else None
            else:
                client = self.fournisseur_var.get().strip()
                nfacture = int(self.nfacture_f_var.get()) if self.nfacture_f_var.get().strip() else None
            percent = float(self.percent_var.get().replace(",", ".")) if self.percent_var.get() else 0.0
            amount = float(self.amount_var.get().replace(",", ".")) if self.amount_var.get() else 0.0
            notes = self.notes_text.get("1.0", "end").strip()
            if not client or percent <= 0 or amount <= 0:
                messagebox.showerror("Erreur", "Champs obligatoires manquants ou invalides.")
                return
            party_type = self.type_var.get()
            if self.preset:
                if self.retenu_service:
                    self.retenu_service.update_retenu(self.preset['id'], date=date_str, client=client, nfacture=nfacture, retenu_percent=percent, retenu_amount=amount, notes=notes, party_type=party_type)
            else:
                if self.retenu_service:
                    self.retenu_service.add_retenu(date_str, client, nfacture, percent, amount, 'manuel', notes, party_type=party_type)
            self.result = True
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}") 