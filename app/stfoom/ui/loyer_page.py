import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date

class LoyerPage(ttk.Frame):
    """Temporary Rent (Loyer) Invoices Page - lightweight separate module.
    Creates simple vente-like records flagged as LOYER for later migration.
    """

    COLS = [
        ("date", "Date"),
        ("client", "Locataire"),
        ("description", "Description"),
        ("montant", "Montant"),
        ("statut", "Statut"),
    ]

    def __init__(self, parent, container, go_home):
        super().__init__(parent, style="FactureMain.TFrame")
        self.container = container
        self.go_home = go_home
        try:
            self.sales_service = container.get('sales_service')
        except Exception:
            self.sales_service = None
        try:
            self.payment_service = container.get('payment_service')
        except Exception:
            self.payment_service = None

        self.pack(fill="both", expand=True)
        self._build_ui()
        self._load_rows()

    def _build_ui(self):
        header = ttk.Frame(self, style="FactureHeader.TFrame")
        header.pack(fill="x", pady=(0,10))
        ttk.Button(header, text="⬅️ Retour", command=self.go_home, style="FactureBack.TButton").pack(side="left", padx=(10,20), pady=18)
        ttk.Label(header, text="Loyers – Factures Temporaires", font=("Segoe UI",22,"bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # Table
        frame = ttk.LabelFrame(self, text="Liste des Loyers", style="FactureSection.TLabelframe")
        frame.pack(fill="both", expand=True, padx=30, pady=(0,10))
        self.tree = ttk.Treeview(frame, columns=[c[0] for c in self.COLS], show='headings', height=15, style="Custom.Treeview")
        for key,title in self.COLS:
            self.tree.heading(key,text=title)
            self.tree.column(key,anchor='center',width=120)
        self.tree.column('client',anchor='w',width=200)
        self.tree.column('description',anchor='w',width=220)
        self.tree.pack(fill='both', expand=True, padx=8, pady=6)

        # Buttons
        btnf = ttk.Frame(self)
        btnf.pack(pady=15)
        ttk.Button(btnf, text="➕ Ajouter Loyer", command=self._on_add).grid(row=0,column=0,padx=6,ipadx=12,ipady=6)
        ttk.Button(btnf, text="💳 Marquer Payé", command=self._on_mark_paid).grid(row=0,column=1,padx=6,ipadx=12,ipady=6)
        ttk.Button(btnf, text="🗑 Supprimer", command=self._on_delete).grid(row=0,column=2,padx=6,ipadx=12,ipady=6)

    def _load_rows(self):
        self.tree.delete(*self.tree.get_children())
        rows = []
        if self.sales_service:
            # Pull all sales, filter those with produit == 'LOYER'
            try:
                for sale in self.sales_service.get_all_sales():
                    if str(sale.get('produit','')).upper() == 'LOYER':
                        # Basic mapping
                        nfacture = sale.get('nfacture')
                        montant = sale.get('ttc') or sale.get('total') or sale.get('prix_unitaire') or 0
                        statut = 'inconnu'
                        # Optional payment status
                        if self.payment_service and nfacture:
                            try:
                                ps = self.payment_service.get_payment_status(nfacture, montant, 0)
                                statut = ps.get('status','inconnu')
                            except Exception:
                                pass
                        self.tree.insert('', 'end', iid=str(nfacture) if nfacture else '', values=(
                            sale.get('date', ''),
                            sale.get('client',''),
                            (sale.get('notes','') or '').split('\n')[0][:40],
                            f"{montant:.3f}",
                            statut
                        ))
            except Exception as e:
                print(f"[LOYER] Error loading loyer rows: {e}")
        self.tree.tag_configure('payé', foreground="#155724", background="#d4edda")
        self.tree.tag_configure('partiellement payé', foreground="#b8860b", background="#fff3cd")
        self.tree.tag_configure('non payé', foreground="#721c24", background="#f8d7da")

    def _selected_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _on_add(self):
        if not self.sales_service:
            messagebox.showerror("Service", "SalesService indisponible")
            return
        dialog = LoyerDialog(self, self.sales_service)
        if dialog.result_id:
            self._load_rows()

    def _on_mark_paid(self):
        if not self.payment_service:
            messagebox.showerror("Paiement", "PaymentService indisponible")
            return
        nfacture = self._selected_id()
        if not nfacture:
            messagebox.showinfo("Sélection", "Choisissez un loyer.")
            return
        montant = 0
        try:
            for sale in self.sales_service.get_all_sales():
                if sale.get('nfacture') == nfacture:
                    montant = sale.get('ttc') or sale.get('total') or sale.get('prix_unitaire') or 0
                    break
            if montant <= 0:
                messagebox.showerror("Montant", "Montant invalide")
                return
            # Mark payment (simple full payment in bank/cash unspecified -> use cash default)
            self.payment_service.add_payment(nfacture, montant, 'especes', is_achat=False, notes='Paiement loyer temp')
            messagebox.showinfo("Succès", "Loyer marqué payé")
            self._load_rows()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur paiement: {e}")

    def _on_delete(self):
        nfacture = self._selected_id()
        if not nfacture:
            messagebox.showinfo("Sélection", "Choisissez un loyer.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer ce loyer ?"):
            return
        try:
            # reuse deletion cascade
            from app.stfoom.services.sales_service import SalesService
            # sales_service already there
            # invoice stored in main invoices table; call delete_sale_by_invoice
            self.sales_service.delete_sale_by_invoice(nfacture)
            self._load_rows()
            messagebox.showinfo("Supprimé", "Loyer supprimé")
        except Exception as e:
            messagebox.showerror("Erreur", f"Suppression impossible: {e}")

class LoyerDialog:
    def __init__(self, parent, sales_service):
        self.parent = parent
        self.sales_service = sales_service
        self.result_id = None
        self.win = tk.Toplevel(parent)
        self.win.title("Ajouter Loyer Temporaire")
        self.win.geometry("420x340")
        self._build()
        self.win.transient(parent)
        self.win.grab_set()
        self.win.focus_force()
        parent.wait_window(self.win)

    def _build(self):
        frm = ttk.Frame(self.win)
        frm.pack(fill='both', expand=True, padx=14, pady=14)
        ttk.Label(frm, text="Date:").grid(row=0,column=0,sticky='w',pady=4)
        self.date_var = tk.StringVar(value=date.today().strftime('%Y-%m-%d'))
        ttk.Entry(frm, textvariable=self.date_var, width=16).grid(row=0,column=1,sticky='w')
        ttk.Label(frm, text="Locataire (client):").grid(row=1,column=0,sticky='w',pady=4)
        self.client_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.client_var, width=30).grid(row=1,column=1,sticky='w')
        ttk.Label(frm, text="Montant TTC:").grid(row=2,column=0,sticky='w',pady=4)
        self.montant_var = tk.StringVar()
        ttk.Entry(frm, textvariable=self.montant_var, width=16).grid(row=2,column=1,sticky='w')
        ttk.Label(frm, text="Description:").grid(row=3,column=0,sticky='nw',pady=4)
        self.desc_text = tk.Text(frm, height=4, width=32)
        self.desc_text.grid(row=3,column=1,sticky='w')
        ttk.Button(frm, text="Enregistrer", command=self._save).grid(row=10,column=0,pady=18,sticky='w')
        ttk.Button(frm, text="Annuler", command=self.win.destroy).grid(row=10,column=1,pady=18,sticky='e')

    def _save(self):
        try:
            client = self.client_var.get().strip()
            montant = float(self.montant_var.get().replace(',','.'))
            if not client or montant <= 0:
                messagebox.showerror("Validation", "Client et montant requis")
                return
            notes = ('[LOYER_TEMP] ' + self.desc_text.get('1.0','end').strip()).strip()
            ok, msg, vid = self.sales_service.create_sale(
                client_nom=client,
                produit='LOYER',
                quantite=1,
                prix_unitaire=montant,
                date_vente=self.date_var.get(),
                notes=notes
            )
            if ok:
                self.result_id = vid
                messagebox.showinfo("Succès", f"Loyer créé (ID facture: {vid})")
                self.win.destroy()
            else:
                messagebox.showerror("Erreur", msg)
        except Exception as e:
            messagebox.showerror("Erreur", f"Impossible d'enregistrer: {e}")
