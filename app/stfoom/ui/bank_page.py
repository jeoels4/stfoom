"""
Page de gestion bancaire – Interface utilisateur
Affiche les transactions bancaires avec encaissements/décaissements.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import datetime, date
from typing import Optional, Dict

# Legacy bank module compatibility
LEGACY_BANK_AVAILABLE = False  # Using BankService through DI instead

# Create a minimal compatibility object for legacy code paths
class _BankModuleCompat:
    """Compatibility shim for legacy bank module references"""
    @staticmethod
    def get_banques():
        return []
    @staticmethod
    def get_banque_defaut():
        return None
    @staticmethod
    def get_payment_methods():
        return []
    @staticmethod
    def formater_montant(val):
        return f"{float(val):.2f}" if val else "0.00"
    @staticmethod
    def formater_date(val):
        return str(val) if val else ""
    @staticmethod
    def get_transactions(*args, **kwargs):
        return []
    @staticmethod
    def get_transaction_by_id(tid):
        return None
    @staticmethod
    def verifier_transaction(tid):
        return False
    @staticmethod
    def supprimer_transaction(tid):
        return False
    @staticmethod
    def definir_banque_defaut(bid):
        return False
    @staticmethod
    def supprimer_banque(bid):
        return False
    @staticmethod
    def unverify_transaction(tid):
        return False
    @staticmethod
    def modifier_transaction(*args, **kwargs):
        return False
    @staticmethod
    def ajouter_transaction(*args, **kwargs):
        return False
    @staticmethod
    def get_banque_by_id(bid):
        return None
    @staticmethod
    def modifier_banque(*args, **kwargs):
        return False
    @staticmethod
    def ajouter_banque(*args, **kwargs):
        return False
    @staticmethod
    def add_payment_method(*args, **kwargs):
        return False
    @staticmethod
    def remove_payment_method(*args, **kwargs):
        return False

bank = _BankModuleCompat()  # Compatibility shim

# from stfoom.logic import bank  # Now use BankService through DI
from tkcalendar import Calendar, DateEntry
from typing import Any

# Removed reconciliation import per request to avoid accidental migrations/auto-adds
_run_bank_recon = None

class MockBankService:
    """Mock bank service for when legacy bank module is unavailable."""
    
    def get_all_banks(self):
        return [{'id': 1, 'nom_banque': 'Banque Test', 'numero_compte': '12345', 'solde_initial': 0.0}]
    
    def get_default_bank(self):
        return {'id': 1, 'nom_banque': 'Banque Test', 'numero_compte': '12345'}
    
    def create_bank(self, nom, numero, solde):
        return True
    
    def get_transactions(self, banque_id=None, date_debut=None, date_fin=None):
        return []
    
    def get_bank_balance(self, banque_id, verifie_seulement=False):
        return 0.0
    
    def get_period_summary(self, banque_id, date_debut, date_fin):
        return {'encaissements': {'total': 0.0, 'count': 0}, 'decaissements': {'total': 0.0, 'count': 0}}
    
    def verify_transaction(self, transaction_id):
        return True
    
    def get_transaction_by_id(self, transaction_id):
        return None
    
    def delete_transaction(self, transaction_id):
        return True
    
    def set_default_bank(self, banque_id):
        return True
    
    def delete_bank(self, banque_id):
        return True
    
    def get_payment_methods(self):
        return [('carte', 'Carte bancaire'), ('cheque', 'Chèque'), ('virement', 'Virement'), ('especes', 'Espèces')]
    
    def unverify_transaction(self, transaction_id):
        return True
    
    def update_transaction(self, *args, **kwargs):
        return True
    
    def add_transaction(self, *args, **kwargs):
        return True
    
    def get_bank_by_id(self, banque_id):
        return {'id': 1, 'nom_banque': 'Banque Test', 'numero_compte': '12345', 'solde_initial': 0.0}
    
    def add_payment_method(self, key, label):
        return True
    
    def remove_payment_method(self, key):
        return True
    
    def format_amount(self, amount):
        return f"{amount:.3f}"
    
    def format_date(self, date_val):
        if isinstance(date_val, str):
            return date_val
        return date_val.strftime('%d/%m/%Y') if date_val else ""

class BankPage(ttk.Frame):
    """Page de gestion des transactions bancaires."""

    def __init__(self, parent, container=None, go_home=None):
        super().__init__(parent)
        # ✅ PHASE 2D MIGRATION: Support both DI and legacy patterns
        if go_home is None:
            # New pattern: (parent, container, go_home)
            self.go_home = container  # In new pattern, second param is go_home
            self.container = None
        else:
            # Could be either pattern, check if container has 'get' method
            if hasattr(container, 'get'):
                # New pattern: (parent, container, go_home)
                self.container = container
                self.go_home = go_home
                print("[BANK_PAGE] 🚀 Using dependency injection with BankService")
            else:
                # Legacy pattern: (parent, go_home) - container is actually go_home
                self.go_home = container
                self.container = None
                print("[BANK_PAGE] ❌ Container has no 'get' method: " + str(type(container)))
        
        # Initialize service layer
        if self.container:
            try:
                self.bank_service = self.container.get('bank_service')
                self.use_service_layer = True
                print("[BANK_PAGE] ✅ BankService loaded via dependency injection")
            except Exception as e:
                print(f"[BANK_PAGE] ⚠️  Failed to load BankService: {e}")
                print("[BANK_PAGE] ⚠️  Falling back to legacy mode due to service error")
                self.use_service_layer = False
        else:
            print("[BANK_PAGE] ⚠️  Falling back to legacy mode due to invalid container")
            self.use_service_layer = False
        
        # Force service layer mode if legacy bank module not available
        if not LEGACY_BANK_AVAILABLE:
            if not self.use_service_layer:
                # Try to create a real BankService with BankRepository when DI not available
                print("[BANK_PAGE] 🔄 DI unavailable, attempting direct BankService wiring…")
                try:
                    from app.stfoom.services.bank_service import BankService as _BS
                    from app.stfoom.data.bank_repository import BankRepository as _BR
                    self.bank_service = _BS(_BR())
                    self.use_service_layer = True
                    print("[BANK_PAGE] ✅ BankService wired directly (no DI)")
                except Exception as e:
                    # Create mock service as last resort
                    print(f"[BANK_PAGE] ⚠️  Direct BankService wiring failed: {e}")
                    print("[BANK_PAGE] 🔄 Falling back to MockBankService")
                    self.use_service_layer = True
                    self.bank_service = MockBankService()
        
        self.selected_banque_id = None
        self.pack(fill="both", expand=True)

        # Configure style for this page
        style = ttk.Style()
        style.configure('BankPage.TFrame', background='white')
        style.configure('BankHeader.TLabel', font=('Arial', 20, 'bold'), background='white')
        style.configure('BankSummary.TLabelframe', background='white')
        style.configure('BankSummary.TLabelframe.Label', font=('Arial', 12, 'bold'), background='white')
        style.configure('BankSummary.TLabel', font=('Arial', 14, 'bold'), background='white')
        style.configure('BankDetails.TLabel', font=('Arial', 10), background='white')
        
        self.configure(style='BankPage.TFrame')

        # Créer l'interface
        self._create_ui()
        # Initialiser et charger les banques
        self._init_banques()
        self._load_banques()
        self._load_data()

    def _safe_bank_call(self, method_name, *args, **kwargs):
        """Safely call a bank module method with fallback."""
        if not LEGACY_BANK_AVAILABLE:
            return None
        try:
            method = getattr(bank, method_name)
            return method(*args, **kwargs)
        except Exception as e:
            print(f"[BANK_PAGE] Error calling bank.{method_name}: {e}")
            return None

    def _init_banques(self):
        """Initialiser les banques si aucune n'existe."""
        if self.use_service_layer:
            banques = self.bank_service.get_all_banks()
            if not banques:
                # Créer une banque par défaut
                self.bank_service.create_bank("Banque Principale", "Compte Principal", 0.0)
        else:
            # Legacy fallback with error handling
            if LEGACY_BANK_AVAILABLE:
                banques = bank.get_banques()
                if not banques:
                    # Créer une banque par défaut
                    bank.ajouter_banque("Banque Principale", "Compte Principal", 0.0)
            else:
                print("[BANK_PAGE] Legacy bank module not available, skipping initialization")
                return

    def _create_ui(self):
        """Créer l'interface utilisateur."""
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=15)
        header.columnconfigure(1, weight=1)

        # Return button
        return_btn = tk.Button(header, text="🏠 Retour", command=self.go_home,
                              bg="#9C27B0", fg="white", font=('Arial', 9, 'bold'),
                              relief="flat", padx=15, pady=5)
        return_btn.grid(row=0, column=0, sticky="w", padx=(0, 15))
        
        # Title
        title_label = ttk.Label(header, text="Gestion Bancaire", style='BankHeader.TLabel')
        title_label.grid(row=0, column=1, sticky="w")

        # Sélecteur de banque
        banque_frame = ttk.Frame(header)
        banque_frame.grid(row=0, column=2, sticky="e")
        ttk.Label(banque_frame, text="Banque:").pack(side="left", padx=(0, 5))
        self.banque_var = tk.StringVar()
        self.banque_combo = ttk.Combobox(banque_frame, textvariable=self.banque_var, state="readonly", width=22)
        self.banque_combo.pack(side="left")
        self.banque_combo.bind("<<ComboboxSelected>>", self._on_banque_change)

        # Main panel with left and right
        main_panel = ttk.Frame(self)
        main_panel.pack(fill="both", expand=True, padx=20, pady=10)
        main_panel.columnconfigure(0, weight=3)
        main_panel.columnconfigure(1, weight=1)

        # ──────────── Panneau gauche (transactions) ────────────
        left_frame = ttk.Frame(main_panel)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 15))
        left_frame.columnconfigure(0, weight=1)

        # Filtres
        filter_frame = ttk.LabelFrame(left_frame, text="Filtres", style='BankSummary.TLabelframe')
        filter_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10), padx=0, ipadx=10, ipady=10)

        # Dates
        date_frame = ttk.Frame(filter_frame)
        date_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(date_frame, text="Du:").pack(side="left")
        self.date_debut = DateEntry(date_frame, width=12, date_pattern="dd/MM/yyyy")
        self.date_debut.pack(side="left", padx=5)
        self.date_debut.set_date(date.today().replace(month=1, day=1))
        ttk.Label(date_frame, text="Au:").pack(side="left", padx=(10, 0))
        self.date_fin = DateEntry(date_frame, width=12, date_pattern="dd/MM/yyyy")
        self.date_fin.pack(side="left", padx=5)
        self.date_fin.set_date(date.today())
        
        refresh_btn = tk.Button(date_frame, text="🔄 Actualiser", command=self._load_data,
                               bg="#2196F3", fg="white", font=('Arial', 9, 'bold'),
                               relief="flat", padx=10, pady=3)
        refresh_btn.pack(side="left", padx=10)

        # Type de transaction
        type_frame = ttk.Frame(filter_frame)
        type_frame.pack(fill="x", padx=10, pady=5)
        self.type_var = tk.StringVar(value="tous")
        ttk.Radiobutton(type_frame, text="Tous", variable=self.type_var, value="tous", command=self._load_data).pack(side="left")
        ttk.Radiobutton(type_frame, text="Encaissements", variable=self.type_var, value="encaissement", command=self._load_data).pack(side="left", padx=10)
        ttk.Radiobutton(type_frame, text="Décaissements", variable=self.type_var, value="decaissement", command=self._load_data).pack(side="left", padx=10)

        # Table des transactions
        table_frame = ttk.Frame(left_frame)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        left_frame.rowconfigure(1, weight=1)

        columns = ("date", "nfacture", "nom_client", "numero_cheque", "encaissement", "decaissement", "verifie")
        self.tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=16)
        self.tree.heading("date", text="Date")
        self.tree.heading("nfacture", text="N° Facture")
        self.tree.heading("nom_client", text="Client/Fournisseur")
        self.tree.heading("numero_cheque", text="N° Chèque")
        self.tree.heading("encaissement", text="Encaissement")
        self.tree.heading("decaissement", text="Décaissement")
        self.tree.heading("verifie", text="Vérifié")
        self.tree.column("date", width=90, anchor="center")
        self.tree.column("nfacture", width=100, anchor="center")
        self.tree.column("nom_client", width=210, anchor="w")
        self.tree.column("numero_cheque", width=110, anchor="center")
        self.tree.column("encaissement", width=120, anchor="e")
        self.tree.column("decaissement", width=120, anchor="e")
        self.tree.column("verifie", width=70, anchor="center")
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Tags for style
        self.tree.tag_configure("non_verifie", background="#fffbe6", foreground="#b8860b")
        self.tree.tag_configure("encaissement", foreground="#218838")
        self.tree.tag_configure("decaissement", foreground="#c82333")

        # Action buttons
        btn_frame = ttk.Frame(left_frame)
        btn_frame.grid(row=2, column=0, sticky="ew", pady=(0, 5))
        for i in range(4):
            btn_frame.columnconfigure(i, weight=1)
        
        add_btn = tk.Button(btn_frame, text="➕ Nouvelle Transaction", command=self._nouvelle_transaction,
                           bg="#4CAF50", fg="white", font=('Arial', 9, 'bold'),
                           relief="flat", padx=10, pady=5)
        add_btn.grid(row=0, column=0, padx=5, sticky="ew")
        
        edit_btn = tk.Button(btn_frame, text="✏️ Modifier Transaction", command=self._modifier_transaction,
                            bg="#2196F3", fg="white", font=('Arial', 9, 'bold'),
                            relief="flat", padx=10, pady=5)
        edit_btn.grid(row=0, column=1, padx=5, sticky="ew")
        
        verify_btn = tk.Button(btn_frame, text="✅ Marquer Vérifié", command=self._verifier_transaction,
                              bg="#FF9800", fg="white", font=('Arial', 9, 'bold'),
                              relief="flat", padx=10, pady=5)
        verify_btn.grid(row=0, column=2, padx=5, sticky="ew")
        
        delete_btn = tk.Button(btn_frame, text="❌ Supprimer", command=self._supprimer_transaction,
                              bg="#F44336", fg="white", font=('Arial', 9, 'bold'),
                              relief="flat", padx=10, pady=5)
        delete_btn.grid(row=0, column=3, padx=5, sticky="ew")

        # ──────────── Panneau droit (résumé) ────────────
        right_frame = ttk.Frame(main_panel)
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_frame.columnconfigure(0, weight=1)

        # Résumé
        resume_frame = ttk.LabelFrame(right_frame, text="Résumé", style='BankSummary.TLabelframe')
        resume_frame.pack(fill="x", pady=(0, 15), padx=0, ipadx=10, ipady=10)
        
        self.solde_verifie_label = ttk.Label(resume_frame, text="Solde vérifié: 0,00 TND", 
                                            style='BankSummary.TLabel', foreground="#218838")
        self.solde_verifie_label.pack(pady=(10, 5))
        
        self.solde_total_label = ttk.Label(resume_frame, text="Solde total: 0,00 TND", 
                                          style='BankDetails.TLabel', foreground="#6c757d")
        self.solde_total_label.pack(pady=(0, 10))
        
        details_frame = ttk.Frame(resume_frame)
        details_frame.pack(fill="x", padx=10, pady=5)
        
        self.encaissements_label = ttk.Label(details_frame, text="Encaissements: 0,00 TND", 
                                            style='BankDetails.TLabel', foreground="#218838")
        self.encaissements_label.pack(anchor="w", pady=2)
        
        self.decaissements_label = ttk.Label(details_frame, text="Décaissements: 0,00 TND", 
                                            style='BankDetails.TLabel', foreground="#c82333")
        self.decaissements_label.pack(anchor="w", pady=2)
        
        self.non_verifies_label = ttk.Label(details_frame, text="Non vérifiés: 0", 
                                           style='BankDetails.TLabel', foreground="#b8860b")
        self.non_verifies_label.pack(anchor="w", pady=2)

        # Boutons de gestion des banques
        banque_btn_frame = ttk.Frame(right_frame)
        banque_btn_frame.pack(fill="x", pady=10)
        
        manage_banks_btn = tk.Button(banque_btn_frame, text="🏦 Gérer les Banques", command=self._gerer_banques,
                                    bg="#2196F3", fg="white", font=('Arial', 9, 'bold'),
                                    relief="flat", padx=15, pady=8)
        manage_banks_btn.pack(fill="x", pady=2)
        
        default_btn = tk.Button(banque_btn_frame, text="⭐ Définir comme Défaut", command=self._definir_defaut,
                               bg="#FF9800", fg="white", font=('Arial', 9, 'bold'),
                               relief="flat", padx=15, pady=8)
        default_btn.pack(fill="x", pady=2)
        
        payment_btn = tk.Button(banque_btn_frame, text="💳 Gérer les modes de paiement", command=self._gerer_payment_methods,
                               bg="#9C27B0", fg="white", font=('Arial', 9, 'bold'),
                               relief="flat", padx=15, pady=8)
        payment_btn.pack(fill="x", pady=2)

        # Repair missing entries
    # Disabled repair/migration actions per request

    def _load_banques(self):
        """Charger la liste des banques."""
        if self.use_service_layer:
            banques = self.bank_service.get_all_banks()
        else:
            if not LEGACY_BANK_AVAILABLE:
                banques = []
            else:
                banques = bank.get_banques()
        
        self.banques_dict = {f"{b['nom_banque']} ({b['numero_compte']})": b['id'] for b in banques}
        
        self.banque_combo['values'] = list(self.banques_dict.keys())
        if self.banques_dict:
            # Sélectionner la banque par défaut ou la première
            if self.use_service_layer:
                banque_defaut = self.bank_service.get_default_bank()
            else:
                banque_defaut = bank.get_banque_defaut() if LEGACY_BANK_AVAILABLE else None
            
            if banque_defaut:
                # Trouver la banque par défaut dans la liste
                for nom, banque_id in self.banques_dict.items():
                    if banque_id == banque_defaut['id']:
                        self.banque_combo.set(nom)
                        self.selected_banque_id = banque_id
                        break
            else:
                # Pas de banque par défaut, prendre la première
                premiere_banque = list(self.banques_dict.keys())[0]
                self.banque_combo.set(premiere_banque)
                self.selected_banque_id = self.banques_dict[premiere_banque]
        else:
            self.selected_banque_id = None

    def _on_banque_change(self, event=None):
        """Changement de banque sélectionnée."""
        if self.banque_var.get() in self.banques_dict:
            self.selected_banque_id = self.banques_dict[self.banque_var.get()]
            self._load_data()

    def _load_data(self):
        """Charger les données."""
        if not self.selected_banque_id:
            return

        # Charger les banques si pas encore fait
        if not hasattr(self, 'banques_dict'):
            self._load_banques()

        # Vider la table
        try:
            self.tree.delete(*self.tree.get_children())
        except Exception:
            pass  # Widget may have been destroyed

        # Convertir les dates
        try:
            date_debut = datetime.strptime(self.date_debut.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            date_fin = datetime.strptime(self.date_fin.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Erreur", "Format de date invalide (JJ/MM/AAAA)")
            return

        # Filtrer par type
        type_filter = None
        if self.type_var.get() != "tous":
            type_filter = self.type_var.get()

        # Récupérer les transactions
        if self.use_service_layer:
            transactions = self.bank_service.get_transactions(
                banque_id=self.selected_banque_id,
                date_debut=date_debut,
                date_fin=date_fin
            )
            # Filter by type if needed (service doesn't support type filter yet)
            if type_filter:
                transactions = [t for t in transactions if t['type_transaction'] == type_filter]
        else:
            if not LEGACY_BANK_AVAILABLE:
                transactions = []
            else:
                transactions = bank.get_transactions(
                    banque_id=self.selected_banque_id,
                    type_transaction=type_filter,
                    start_date=date_debut,
                    end_date=date_fin
                )

        # Afficher les transactions
        for trans in transactions:
            tags = []
            if not trans['verifie']:
                tags.append("non_verifie")
            tags.append(trans['type_transaction'])
            if self.use_service_layer:
                enc = self.bank_service.format_amount(trans['montant']) if trans['type_transaction'] == 'encaissement' else ""
                dec = self.bank_service.format_amount(trans['montant']) if trans['type_transaction'] == 'decaissement' else ""
                formatted_date = self.bank_service.format_date(trans['date_transaction'])
            else:
                enc = bank.formater_montant(trans['montant']) if trans['type_transaction'] == 'encaissement' else ""
                dec = bank.formater_montant(trans['montant']) if trans['type_transaction'] == 'decaissement' else ""
                formatted_date = bank.formater_date(trans['date_transaction'])
            # Try to show num_facture if available (for achat payments)
            num_facture = trans.get('num_facture') or trans.get('nfacture') or ""
            numero_cheque = trans.get('numero_cheque') or ""
            
            # FIX: Handle display of check numbers vs invoice numbers
            # If we have a proper invoice number in nfacture, always show numero_cheque as check number
            # Only treat numero_cheque as invoice numbers if it's clearly in invoice format AND no proper invoice exists
            if (numero_cheque and '/' in numero_cheque and 
                (not num_facture or num_facture == 0 or num_facture == '0') and
                len(numero_cheque.split('/')) == 2 and 
                all(part.isdigit() and len(part) <= 3 for part in numero_cheque.split('/'))):
                # This looks like invoice numbers (format like "075/074") stored in wrong field
                actual_invoice = numero_cheque
                actual_cheque = ""  # Clear check number since it contains invoice data
            else:
                # Normal case OR ambiguous case: treat numero_cheque as check number
                actual_invoice = num_facture
                actual_cheque = numero_cheque
            
            # Format invoice numbers for display (short format: 74 instead of 202500074)
            if actual_invoice and isinstance(actual_invoice, str) and len(actual_invoice) >= 7:
                # Remove common prefix for current year invoices
                current_year = str(datetime.now().year)
                if actual_invoice.startswith(current_year + '00'):
                    actual_invoice = actual_invoice[len(current_year + '00'):].lstrip('0') or '0'
            elif actual_invoice and isinstance(actual_invoice, int) and actual_invoice >= 202500001:  # FIXED: Correct threshold
                # Handle integer invoice numbers
                num_str = str(actual_invoice)
                if num_str.startswith('202500'):
                    actual_invoice = num_str[6:].lstrip('0') or '0'
            
            self.tree.insert("", "end", iid=str(trans['id']), values=(
                formatted_date,
                actual_invoice,  # N° Facture column - corrected
                trans['nom_client'] or "",
                actual_cheque,   # N° Chèque column - corrected  
                enc,
                dec,
                "✅" if trans['verifie'] else "⏳"
            ), tags=tags)

        # Mettre à jour le résumé
        self._update_resume(date_debut, date_fin)

    def _update_resume(self, date_debut: str, date_fin: str):
        """Mettre à jour le résumé."""
        if not self.selected_banque_id:
            return
        # NEW PERIOD-ONLY LOGIC
        # We compute encaissements / decaissements within the selected period and derive balances.
        from datetime import datetime as _dt
        year_start_flag = False
        try:
            start_dt = _dt.strptime(date_debut, "%Y-%m-%d")
            year_start_flag = (start_dt.month == 1 and start_dt.day == 1)
        except Exception:
            pass

        if self.use_service_layer:
            # Get period summary (service already groups)
            period_summary = self.bank_service.get_period_summary(self.selected_banque_id, date_debut, date_fin)
            enc_total = period_summary['encaissements']['total']
            dec_total = period_summary['decaissements']['total']

            # Fetch initial balance and all-time if needed
            initial_balance = 0.0
            try:
                # Bank record contains solde_initial
                bank_info = self.bank_service.get_bank_by_id(self.selected_banque_id)
                if bank_info:
                    initial_balance = bank_info.get('solde_initial', 0.0) or 0.0
            except Exception:
                pass

            # Period balances: include initial balance only if start date is Jan 1
            period_base = initial_balance if year_start_flag else 0.0
            period_total_balance = period_base + enc_total - dec_total

            # Verified subset: we approximate by filtering transactions again (could optimize inside service)
            try:
                transactions = self.bank_service.get_transactions(banque_id=self.selected_banque_id, date_debut=date_debut, date_fin=date_fin)
                enc_ver = sum(t['montant'] for t in transactions if t['type_transaction'] == 'encaissement' and t['verifie'])
                dec_ver = sum(t['montant'] for t in transactions if t['type_transaction'] == 'decaissement' and t['verifie'])
                period_verified_balance = (initial_balance if year_start_flag else 0.0) + enc_ver - dec_ver
            except Exception:
                period_verified_balance = period_total_balance  # fallback

            self.solde_verifie_label.config(text=f"Solde vérifié: {self.bank_service.format_amount(period_verified_balance)}")
            self.solde_total_label.config(text=f"Solde total: {self.bank_service.format_amount(period_total_balance)}")
            self.encaissements_label.config(text=f"Encaissements: {self.bank_service.format_amount(enc_total)}")
            self.decaissements_label.config(text=f"Décaissements: {self.bank_service.format_amount(dec_total)}")
            total_transactions = period_summary['encaissements']['count'] + period_summary['decaissements']['count']
            suffix = " (incl. solde initial)" if year_start_flag else ""
            self.non_verifies_label.config(text=f"Transactions: {total_transactions}{suffix}")
        else:
            # Legacy path: compute manually from raw transactions
            transactions = bank.get_transactions(
                banque_id=self.selected_banque_id,
                type_transaction=None,
                start_date=date_debut,
                end_date=date_fin
            ) if LEGACY_BANK_AVAILABLE else []
            enc_total = sum(t['montant'] for t in transactions if t['type_transaction'] == 'encaissement')
            dec_total = sum(t['montant'] for t in transactions if t['type_transaction'] == 'decaissement')
            enc_ver = sum(t['montant'] for t in transactions if t['type_transaction'] == 'encaissement' and t['verifie'])
            dec_ver = sum(t['montant'] for t in transactions if t['type_transaction'] == 'decaissement' and t['verifie'])
            # Initial balance retrieval
            try:
                banque_info = next((b for b in bank.get_banques() if b['id'] == self.selected_banque_id), None) if LEGACY_BANK_AVAILABLE else None
                initial_balance = banque_info.get('solde_initial', 0.0) if banque_info else 0.0
            except Exception:
                initial_balance = 0.0
            period_total_balance = (initial_balance if year_start_flag else 0.0) + enc_total - dec_total
            period_verified_balance = (initial_balance if year_start_flag else 0.0) + enc_ver - dec_ver
            self.solde_verifie_label.config(text=f"Solde vérifié: {bank.formater_montant(period_verified_balance)}")
            self.solde_total_label.config(text=f"Solde total: {bank.formater_montant(period_total_balance)}")
            self.encaissements_label.config(text=f"Encaissements: {bank.formater_montant(enc_total)}")
            self.decaissements_label.config(text=f"Décaissements: {bank.formater_montant(dec_total)}")
            suffix = " (incl. solde initial)" if year_start_flag else ""
            non_verifies = sum(1 for t in transactions if not t['verifie'])
            self.non_verifies_label.config(text=f"Non vérifiés: {non_verifies}{suffix}")

    def _nouvelle_transaction(self):
        """Ouvrir le dialogue de nouvelle transaction."""
        if not self.selected_banque_id:
            messagebox.showwarning("Attention", "Sélectionnez une banque d'abord.")
            return

        dialog = TransactionDialog(self, self.selected_banque_id, None, self.use_service_layer, self.bank_service if self.use_service_layer else None)
        if dialog.result:
            self._load_data()

    def _verifier_transaction(self):
        """Marquer la transaction sélectionnée comme vérifiée."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Sélectionnez une transaction à vérifier.")
            return

        transaction_id = int(selection[0])
        if self.use_service_layer:
            success = self.bank_service.verify_transaction(transaction_id)
        else:
            success = bank.verifier_transaction(transaction_id)
            
        if success:
            messagebox.showinfo("Succès", "Transaction marquée comme vérifiée.")
            self._load_data()
        else:
            messagebox.showerror("Erreur", "Erreur lors de la vérification.")

    def _modifier_transaction(self):
        """Modifier la transaction sélectionnée."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Sélectionnez une transaction à modifier.")
            return

        transaction_id = int(selection[0])
        # Récupérer les données de la transaction
        if self.use_service_layer:
            transaction = self.bank_service.get_transaction_by_id(transaction_id)
        else:
            transaction = bank.get_transaction_by_id(transaction_id)
            
        if not transaction:
            messagebox.showerror("Erreur", "Transaction introuvable.")
            return

        if self.selected_banque_id:
            dialog = TransactionDialog(self, self.selected_banque_id, transaction, self.use_service_layer, self.bank_service if self.use_service_layer else None)
            if dialog.result:
                self._load_data()

    def _supprimer_transaction(self):
        """Supprimer la transaction sélectionnée."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Sélectionnez une transaction à supprimer.")
            return

        if not messagebox.askyesno("Confirmer", "Supprimer cette transaction ?"):
            return

        transaction_id = int(selection[0])
        if self.use_service_layer:
            success = self.bank_service.delete_transaction(transaction_id)
            if success:
                messagebox.showinfo("Succès", "Transaction supprimée.")
                self._load_data()
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression.")
        else:
            if bank.supprimer_transaction(transaction_id):
                messagebox.showinfo("Succès", "Transaction supprimée.")
                self._load_data()
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression.")

    def _definir_defaut(self):
        """Définir la banque sélectionnée comme défaut."""
        if not self.selected_banque_id:
            messagebox.showinfo("Information", "Sélectionnez une banque d'abord.")
            return
            
        if self.use_service_layer:
            success = self.bank_service.set_default_bank(self.selected_banque_id)
            if success:
                messagebox.showinfo("Succès", "Banque définie comme défaut.")
                self._load_banques()  # Recharger pour mettre à jour l'ordre
            else:
                messagebox.showerror("Erreur", "Erreur lors de la définition de la banque par défaut.")
        else:
            if bank.definir_banque_defaut(self.selected_banque_id):
                messagebox.showinfo("Succès", "Banque définie comme défaut.")
                self._load_banques()  # Recharger pour mettre à jour l'ordre
            else:
                messagebox.showerror("Erreur", "Erreur lors de la définition de la banque par défaut.")

    def _gerer_banques(self):
        """Ouvrir le dialogue de gestion des banques."""
        dialog = BanquesDialog(self, self.use_service_layer, self.bank_service if self.use_service_layer else None)
        if dialog.result:
            self._load_banques()
            self._load_data()

    def _gerer_payment_methods(self):
        dialog = PaymentMethodsDialog(self)
        if dialog.result:
            # Optionally refresh UI if needed
            pass

    # Removed _reparer_transactions and _migrer_vers_wifak to prevent unintended data changes

class TransactionDialog:
    def __init__(self, parent, banque_id: int, transaction: Optional[Dict] = None, use_service_layer: bool = False, bank_service = None):
        self.parent = parent
        self.banque_id = banque_id
        self.transaction = transaction
        self.use_service_layer = use_service_layer
        self.bank_service = bank_service
        self.result = None
        self.window = tk.Toplevel(parent)
        self.window.title("Modifier Transaction" if transaction else "Nouvelle Transaction")
        self.window.geometry("550x700")
        self.window.grab_set()
        self.window.resizable(True, True)
        self.window.configure(bg='white')
        # Configure style
        style = ttk.Style()
        style.configure('TransactionDialog.TFrame', background='white')
        style.configure('TransactionDialog.TLabelframe', background='white')
        style.configure('TransactionDialog.TLabelframe.Label', font=('Arial', 10, 'bold'), background='white')
        self.transaction_type_var = tk.StringVar(value="encaissement")  # Default to encaissement
        self._create_ui()
        self._load_data()
        self.window.transient(parent)
        self.window.grab_set()
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
        # --- Transaction form content ---
        main_frame = ttk.Frame(scrollable_frame, style='TransactionDialog.TFrame')
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Type de transaction (encaissement/décaissement)
        type_frame = ttk.LabelFrame(main_frame, text="Type de transaction", style='TransactionDialog.TLabelframe')
        type_frame.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)
        
        ttk.Radiobutton(type_frame, text="Encaissement", variable=self.transaction_type_var, value="encaissement").pack(anchor="w", padx=10, pady=2)
        ttk.Radiobutton(type_frame, text="Décaissement", variable=self.transaction_type_var, value="decaissement").pack(anchor="w", padx=10, pady=2)
        
        # Type de paiement
        payment_frame = ttk.LabelFrame(main_frame, text="Type de paiement", style='TransactionDialog.TLabelframe')
        payment_frame.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)
        
        self.type_var = tk.StringVar(value="banque")
        ttk.Radiobutton(payment_frame, text="🏦 Banque", variable=self.type_var, value="banque", command=self._update_fields).pack(anchor="w", padx=10, pady=2)
        
        # Dedicated frame for bank/method widgets
        self.bank_options_frame = ttk.Frame(main_frame)
        self.bank_options_frame.pack(fill="x", pady=(0, 10))
        self.bank_var = tk.StringVar()
        self.method_var = tk.StringVar()
        if self.use_service_layer:
            banques = self.bank_service.get_all_banks()
        else:
            banques = bank.get_banques()
        self.banks_dict = {f"{b['nom_banque']} ({b['numero_compte']})" if b['numero_compte'] else b['nom_banque']: b['id'] for b in banques}
        self.bank_combo = ttk.Combobox(self.bank_options_frame, textvariable=self.bank_var, state="readonly", width=35, values=list(self.banks_dict.keys()))
        if self.use_service_layer:
            payment_methods = self.bank_service.get_payment_methods()
        else:
            payment_methods = bank.get_payment_methods()
        self.method_combo = ttk.Combobox(self.bank_options_frame, textvariable=self.method_var, state="readonly", width=30, values=[label for _, label in payment_methods])
        self.echeance_var = tk.StringVar()
        self.echeance_label = tk.Label(self.bank_options_frame, text="Échéance (JJ/MM/AAAA, pour traite):")
        self.echeance_frame = tk.Frame(self.bank_options_frame)
        self.echeance_entry = DateEntry(self.echeance_frame, textvariable=self.echeance_var, date_pattern="dd/MM/yyyy", width=15)
        self.echeance_entry.pack(side="left")
        # Numéro field for cheque/traite/virement
        self.numero_label = ttk.Label(main_frame, text="Numéro:")
        self.numero_var = tk.StringVar()
        self.numero_entry = ttk.Entry(main_frame, textvariable=self.numero_var, width=35)
        
        # Dynamic field update
        def update_fields():
            for widget in self.bank_options_frame.winfo_children():
                widget.pack_forget()
            self.bank_combo.pack(anchor="w", padx=10, pady=2)
            self.method_combo.pack(anchor="w", padx=10, pady=2)
            # Always show numero field
            self.numero_label.pack(anchor="w", padx=10, pady=2)
            self.numero_entry.pack(anchor="w", padx=10, pady=2)
            method_idx = None
            try:
                if self.use_service_layer:
                    payment_methods = self.bank_service.get_payment_methods()
                else:
                    payment_methods = bank.get_payment_methods()
                method_idx = [label for _, label in payment_methods].index(self.method_combo.get())
            except Exception:
                pass
            if self.use_service_layer:
                payment_methods = self.bank_service.get_payment_methods()
            else:
                payment_methods = bank.get_payment_methods()
            method_key = payment_methods[method_idx][0] if method_idx is not None else None
            if method_key == "traite":
                self.echeance_label.pack(anchor="w", padx=10, pady=2)
                self.echeance_frame.pack(anchor="w", padx=10, pady=2)
            else:
                self.echeance_label.pack_forget()
                self.echeance_frame.pack_forget()
        self.method_combo.bind("<<ComboboxSelected>>", lambda e: update_fields())
        update_fields()
        
        # Transaction details section
        details_frame = ttk.LabelFrame(main_frame, text="Détails de la transaction", style='TransactionDialog.TLabelframe')
        details_frame.pack(fill="x", pady=(0, 10), ipadx=10, ipady=10)
        
        # Date
        ttk.Label(details_frame, text="Date (JJ/MM/AAAA):").pack(anchor="w", padx=10, pady=2)
        date_frame = ttk.Frame(details_frame)
        date_frame.pack(fill="x", padx=10, pady=2)
        self.date_entry = DateEntry(date_frame, width=20, date_pattern="dd/MM/yyyy")
        self.date_entry.pack(side="left")
        
        # Montant
        ttk.Label(details_frame, text="Montant (TND):").pack(anchor="w", padx=10, pady=2)
        self.montant_entry = ttk.Entry(details_frame, width=20)
        self.montant_entry.pack(anchor="w", padx=10, pady=2)
        
        # Numéro de facture
        ttk.Label(details_frame, text="Numéro de facture (optionnel):").pack(anchor="w", padx=10, pady=2)
        self.nfacture_entry = ttk.Entry(details_frame, width=20)
        self.nfacture_entry.pack(anchor="w", padx=10, pady=2)
        
        # Nom client/fournisseur
        ttk.Label(details_frame, text="Client/Fournisseur:").pack(anchor="w", padx=10, pady=2)
        self.nom_entry = ttk.Entry(details_frame, width=35)
        self.nom_entry.pack(anchor="w", padx=10, pady=2)
        
        # Description
        ttk.Label(details_frame, text="Description:").pack(anchor="w", padx=10, pady=2)
        self.desc_text = tk.Text(details_frame, height=4, width=45, font=('Arial', 9))
        self.desc_text.pack(anchor="w", padx=10, pady=2)
        
        # Boutons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x", pady=(10, 0))
        
        save_btn = tk.Button(btn_frame, text="Enregistrer", command=self._save,
                            bg="#4CAF50", fg="white", font=('Arial', 10, 'bold'),
                            relief="flat", padx=30, pady=8)
        save_btn.pack(side="right")
        
        cancel_btn = tk.Button(btn_frame, text="Annuler", command=self._cancel,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        cancel_btn.pack(side="right", padx=(0, 10))
        # Add Unverify button if transaction is verified
        transaction = self.transaction if isinstance(self.transaction, dict) else None
        if transaction and isinstance(transaction.get('id'), int) and transaction.get('verifie', 0) == 1:
            def unverify():
                # from stfoom.logic import bank  # Now use BankService through DI
                transaction_id = transaction.get('id')
                if isinstance(transaction_id, int):
                    if self.use_service_layer:
                        success = self.bank_service.unverify_transaction(transaction_id)
                        if success:
                            messagebox.showinfo("Succès", "Transaction dévérifiée.")
                            self.result = True
                            self.window.destroy()
                        else:
                            messagebox.showerror("Erreur", "Erreur lors de la dévérification.")
                    else:
                        bank.unverify_transaction(transaction_id)
                        messagebox.showinfo("Succès", "Transaction dévérifiée.")
                        self.result = True
                        self.window.destroy()
            unverify_btn = tk.Button(btn_frame, text="Déverifier", command=unverify,
                                    bg="#FF9800", fg="white", font=('Arial', 10, 'bold'),
                                    relief="flat", padx=30, pady=8)
            unverify_btn.pack(side="right", padx=(0, 10))
        self._update_fields = update_fields
    def _update_fields(self):
        if self.type_var.get() == "banque":
            self.bank_combo.pack(anchor="w", padx=30, pady=2)
            self.method_combo.pack(anchor="w", padx=30, pady=2)
            # Update numero field visibility
            method_idx = None
            try:
                if self.use_service_layer:
                    payment_methods = self.bank_service.get_payment_methods()
                else:
                    payment_methods = bank.get_payment_methods()
                method_idx = [label for _, label in payment_methods].index(self.method_combo.get())
            except Exception:
                pass
            if self.use_service_layer:
                payment_methods = self.bank_service.get_payment_methods()
            else:
                payment_methods = bank.get_payment_methods()
            method_key = payment_methods[method_idx][0] if method_idx is not None else None
            if method_key in ("cheque", "traite", "virement"):
                self.numero_label.pack(anchor="w", padx=30, pady=2)
                self.numero_entry.pack(anchor="w", padx=30, pady=2)
            else:
                self.numero_label.pack_forget()
                self.numero_entry.pack_forget()
            # Update echeance field visibility
            if method_key == "traite":
                self.echeance_label.pack(anchor="w", padx=30, pady=2)
                self.echeance_frame.pack(anchor="w", padx=30, pady=2)
            else:
                self.echeance_label.pack_forget()
                self.echeance_frame.pack_forget()
        else:
            self.bank_combo.pack_forget()
            self.method_combo.pack_forget()
            self.echeance_label.pack_forget()
            self.echeance_frame.pack_forget()
            self.numero_label.pack_forget()
            self.numero_entry.pack_forget()
    def _load_data(self):
        if not self.transaction:
            return
        self.type_var.set("banque" if self.transaction.get('methode_paiement', 'banque') == 'banque' else 'caisse')
        # Set transaction type (encaissement/decaissement)
        if self.transaction.get('type_transaction') in ("encaissement", "decaissement"):
            self.transaction_type_var.set(self.transaction['type_transaction'])
        if self.transaction.get('banque_id'):
            for nom, bid in self.banks_dict.items():
                if bid == self.transaction['banque_id']:
                    self.bank_combo.set(nom)
                    break
        if self.transaction.get('mode_paiement'):
            if self.use_service_layer:
                payment_methods = self.bank_service.get_payment_methods()
            else:
                payment_methods = bank.get_payment_methods()
            for k, label in payment_methods:
                if k == self.transaction['mode_paiement']:
                    self.method_combo.set(label)
                    break
        if self.transaction.get('echeance'):
            if self.use_service_layer:
                formatted_date = self.bank_service.format_date(self.transaction['echeance'])
            else:
                formatted_date = bank.formater_date(self.transaction['echeance'])
            self.echeance_var.set(formatted_date)
        self.date_entry.delete(0, tk.END)
        if self.use_service_layer:
            formatted_date = self.bank_service.format_date(self.transaction['date_transaction'])
        else:
            formatted_date = bank.formater_date(self.transaction['date_transaction'])
        self.date_entry.insert(0, formatted_date)
        self.montant_entry.delete(0, tk.END)
        self.montant_entry.insert(0, str(self.transaction['montant']))
        if self.transaction['nfacture']:
            self.nfacture_entry.delete(0, tk.END)
            self.nfacture_entry.insert(0, str(self.transaction['nfacture']))
        self.nom_entry.delete(0, tk.END)
        self.nom_entry.insert(0, self.transaction['nom_client'] or "")
        # Set numero_var if cheque/traite/virement
        method_key = None
        if self.transaction.get('mode_paiement'):
            if self.use_service_layer:
                payment_methods = self.bank_service.get_payment_methods()
            else:
                payment_methods = bank.get_payment_methods()
            for k, label in payment_methods:
                if k == self.transaction['mode_paiement']:
                    method_key = k
                    break
        if method_key in ("cheque", "traite", "virement"):
            self.numero_var.set(self.transaction.get('numero_cheque', '') or "")
        self.desc_text.delete("1.0", tk.END)
        self.desc_text.insert("1.0", self.transaction['description'] or "")
        self._update_fields()
    def _save(self):
        try:
            montant = float(self.montant_entry.get().replace(",", "."))
            if montant <= 0:
                raise ValueError("Montant invalide")
            date_str = datetime.strptime(self.date_entry.get(), "%d/%m/%Y").strftime("%Y-%m-%d")
            nfacture = None
            if self.nfacture_entry.get().strip():
                nfacture = int(self.nfacture_entry.get().strip())
            method_label = self.method_var.get()
            if self.use_service_layer:
                payment_methods = self.bank_service.get_payment_methods()
            else:
                payment_methods = bank.get_payment_methods()
            method_idx = [label for _, label in payment_methods].index(method_label) if method_label in [label for _, label in payment_methods] else 0
            method_key = payment_methods[method_idx][0] if self.type_var.get() == 'banque' else ''
            echeance_db = ''
            if self.type_var.get() == 'banque' and method_key == "traite":
                echeance_str = self.echeance_var.get()
                echeance_db = datetime.strptime(echeance_str, "%d/%m/%Y").strftime("%Y-%m-%d") if echeance_str else ''
            # Use numero_var if visible, else blank
            numero_val = self.numero_var.get().strip()
            desc = self.desc_text.get("1.0", "end").strip()
            # Gentle validation for empty client/supplier name
            nom_val = self.nom_entry.get().strip()
            if not nom_val:
                if messagebox.askyesno("Nom manquant", "Le nom du client/fournisseur est vide. Voulez-vous utiliser 'Inconnu' ?"):
                    nom_val = "Inconnu"
                else:
                    messagebox.showinfo("Saisie requise", "Veuillez saisir le nom du client ou fournisseur.")
                    return
            transaction_type = self.transaction_type_var.get()  # Get encaissement/decaissement
            if self.transaction:
                if self.use_service_layer:
                    success = self.bank_service.update_transaction(
                        transaction_id=self.transaction['id'],
                        type_transaction=transaction_type,
                        montant=montant,
                        date_transaction=date_str,
                        nfacture=nfacture,
                        nom_client=nom_val,
                        numero_cheque=numero_val,
                        description=desc,
                        mode_paiement=method_key,
                        echeance=echeance_db
                    )
                else:
                    success = bank.modifier_transaction(
                        transaction_id=self.transaction['id'],
                        type_transaction=transaction_type,
                        montant=montant,
                        date_transaction=date_str,
                        nfacture=nfacture,
                        nom_client=nom_val,
                        numero_cheque=numero_val,
                        description=desc,
                        mode_paiement=method_key,
                        echeance=echeance_db
                    )
                message_success = "Transaction modifiée avec succès."
                message_error = "Erreur lors de la modification de la transaction."
            else:
                if self.use_service_layer:
                    success = self.bank_service.create_transaction(
                        banque_id=self.banque_id,
                        type_transaction=transaction_type,
                        montant=montant,
                        date_transaction=date_str,
                        nfacture=nfacture,
                        nom_client=nom_val,
                        numero_cheque=numero_val,
                        description=desc,
                        mode_paiement=method_key,
                        echeance=echeance_db
                    )
                else:
                    success = bank.ajouter_transaction(
                        banque_id=self.banque_id,
                        type_transaction=transaction_type,
                        montant=montant,
                        date_transaction=date_str,
                        nfacture=nfacture,
                        nom_client=nom_val,
                        numero_cheque=numero_val,
                        description=desc,
                        mode_paiement=method_key,
                        echeance=echeance_db
                    )
                message_success = "Transaction ajoutée avec succès."
                message_error = "Erreur lors de l'ajout de la transaction."
            if success:
                messagebox.showinfo("Succès", message_success)
                self.result = True
                self.window.destroy()
            else:
                messagebox.showerror("Erreur", message_error)
        except ValueError as e:
            messagebox.showerror("Erreur", f"Données invalides: {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}")
    def _cancel(self):
        self.window.destroy()

class BanquesDialog:
    """Dialogue de gestion des banques."""
    
    def __init__(self, parent, use_service_layer: bool = False, bank_service = None):
        self.parent = parent
        self.use_service_layer = use_service_layer
        self.bank_service = bank_service
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Gestion des Banques")
        self.window.geometry("500x400")
        self.window.grab_set()
        
        self._create_ui()
        self._load_banques()
        
        # Centrer la fenêtre
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)

    def _create_ui(self):
        """Créer l'interface."""
        # Liste des banques
        tk.Label(self.window, text="Banques existantes:", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Treeview pour les banques
        columns = ("nom", "compte", "solde")
        self.tree = ttk.Treeview(self.window, columns=columns, show="headings", height=8)
        
        self.tree.heading("nom", text="Nom de la banque")
        self.tree.heading("compte", text="Numéro de compte")
        self.tree.heading("solde", text="Solde initial")
        
        self.tree.column("nom", width=200)
        self.tree.column("compte", width=150)
        self.tree.column("solde", width=100, anchor="e")
        
        self.tree.pack(pady=10, padx=10, fill="both", expand=True)

        # Boutons
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="➕ Ajouter", command=self._ajouter_banque).pack(side="left", padx=5)
        tk.Button(btn_frame, text="✏️ Modifier", command=self._modifier_banque).pack(side="left", padx=5)
        tk.Button(btn_frame, text="❌ Supprimer", command=self._supprimer_banque).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Fermer", command=self.window.destroy).pack(side="left", padx=20)

    def _load_banques(self):
        """Charger la liste des banques."""
        self.tree.delete(*self.tree.get_children())
        if self.use_service_layer:
            banques = self.bank_service.get_all_banks()
        else:
            banques = bank.get_banques()
        
        for b in banques:
            if self.use_service_layer:
                formatted_amount = self.bank_service.format_amount(b['solde_initial'])
            else:
                formatted_amount = bank.formater_montant(b['solde_initial'])
            self.tree.insert("", "end", iid=str(b['id']), values=(
                b['nom_banque'],
                b['numero_compte'] or "",
                formatted_amount
            ))

    def _ajouter_banque(self):
        """Ajouter une nouvelle banque."""
        dialog = BanqueDialog(self.window, None, self.use_service_layer, self.bank_service if self.use_service_layer else None)
        if dialog.result:
            self._load_banques()
            self.result = True

    def _modifier_banque(self):
        """Modifier la banque sélectionnée."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Sélectionnez une banque à modifier.")
            return

        banque_id = int(selection[0])
        if self.use_service_layer:
            banque = self.bank_service.get_bank_by_id(banque_id)
        else:
            banque = bank.get_banque_by_id(banque_id)
        if not banque:
            messagebox.showerror("Erreur", "Banque introuvable.")
            return

        dialog = BanqueDialog(self.window, banque, self.use_service_layer, self.bank_service if self.use_service_layer else None)
        if dialog.result:
            self._load_banques()
            self.result = True

    def _supprimer_banque(self):
        """Supprimer une banque."""
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("Information", "Sélectionnez une banque à supprimer.")
            return

        if not messagebox.askyesno("Confirmer", "Supprimer cette banque ?\nToutes les transactions associées seront également supprimées."):
            return

        banque_id = int(selection[0])
        if self.use_service_layer:
            success = self.bank_service.delete_bank(banque_id)
            if success:
                messagebox.showinfo("Succès", "Banque supprimée avec succès.")
                self._load_banques()
                self.result = True
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression de la banque.")
        else:
            if bank.supprimer_banque(banque_id):
                messagebox.showinfo("Succès", "Banque supprimée avec succès.")
                self._load_banques()
                self.result = True
            else:
                messagebox.showerror("Erreur", "Erreur lors de la suppression de la banque.")

class BanqueDialog:
    """Dialogue pour ajouter/modifier une banque."""
    
    def __init__(self, parent, banque: Optional[Dict] = None, use_service_layer: bool = False, bank_service = None):
        self.parent = parent
        self.banque = banque  # None pour nouvelle banque
        self.use_service_layer = use_service_layer
        self.bank_service = bank_service
        self.result = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("Modifier Banque" if banque else "Nouvelle Banque")
        self.window.geometry("350x250")
        self.window.grab_set()
        self.window.resizable(False, False)
        
        self._create_ui()
        self._load_data()
        
        # Centrer la fenêtre
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)

    def _create_ui(self):
        """Créer l'interface."""
        # Nom de la banque
        tk.Label(self.window, text="Nom de la banque:").pack(pady=(10, 0))
        self.nom_entry = tk.Entry(self.window, width=30)
        self.nom_entry.pack()

        # Numéro de compte
        tk.Label(self.window, text="Numéro de compte (optionnel):").pack(pady=(10, 0))
        self.compte_entry = tk.Entry(self.window, width=30)
        self.compte_entry.pack()

        # Solde initial
        tk.Label(self.window, text="Solde initial (TND):").pack(pady=(10, 0))
        self.solde_entry = tk.Entry(self.window, width=20)
        self.solde_entry.pack()
        self.solde_entry.insert(0, "0.00")

        # Boutons
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=20)
        
        tk.Button(btn_frame, text="Enregistrer", command=self._save, bg="#28a745", fg="white").pack(side="left", padx=5)
        tk.Button(btn_frame, text="Annuler", command=self._cancel).pack(side="left", padx=5)

    def _load_data(self):
        """Charger les données existantes si en mode édition."""
        if not self.banque:
            return
            
        self.nom_entry.delete(0, tk.END)
        self.nom_entry.insert(0, self.banque['nom_banque'])
        
        self.compte_entry.delete(0, tk.END)
        self.compte_entry.insert(0, self.banque['numero_compte'] or "")
        
        self.solde_entry.delete(0, tk.END)
        self.solde_entry.insert(0, str(self.banque['solde_initial']))

    def _save(self):
        """Sauvegarder la banque."""
        try:
            nom = self.nom_entry.get().strip()
            if not nom:
                messagebox.showerror("Erreur", "Nom de banque obligatoire.")
                return

            compte = self.compte_entry.get().strip()
            
            solde = float(self.solde_entry.get().replace(",", "."))

            if self.banque:
                # Mode édition
                if self.use_service_layer:
                    success = self.bank_service.update_bank(self.banque['id'], nom, compte, solde)
                    if success:
                        messagebox.showinfo("Succès", "Banque modifiée avec succès.")
                        self.result = True
                        self.window.destroy()
                    else:
                        messagebox.showerror("Erreur", "Erreur lors de la modification de la banque.")
                else:
                    if LEGACY_BANK_AVAILABLE:
                        if bank.modifier_banque(self.banque['id'], nom, compte, solde):
                            messagebox.showinfo("Succès", "Banque modifiée avec succès.")
                            self.result = True
                            self.window.destroy()
                        else:
                            messagebox.showerror("Erreur", "Erreur lors de la modification de la banque.")
                    else:
                        messagebox.showerror("Erreur", "Service bancaire non disponible.")
            else:
                # Mode ajout
                if self.use_service_layer:
                    success = self.bank_service.create_bank(nom, compte, solde)
                    if success:
                        messagebox.showinfo("Succès", "Banque ajoutée avec succès.")
                        self.result = True
                        self.window.destroy()
                    else:
                        messagebox.showerror("Erreur", "Erreur lors de l'ajout de la banque.")
                else:
                    if LEGACY_BANK_AVAILABLE:
                        if bank.ajouter_banque(nom, compte, solde):
                            messagebox.showinfo("Succès", "Banque ajoutée avec succès.")
                            self.result = True
                            self.window.destroy()
                        else:
                            messagebox.showerror("Erreur", "Erreur lors de l'ajout de la banque.")
                    else:
                        messagebox.showerror("Erreur", "Service bancaire non disponible.")

        except ValueError:
            messagebox.showerror("Erreur", "Solde invalide.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}")

    def _cancel(self):
        """Annuler."""
        self.window.destroy() 

class PaymentMethodsDialog:
    def __init__(self, parent, use_service_layer: bool = False, bank_service = None):
        self.parent = parent
        self.use_service_layer = use_service_layer
        self.bank_service = bank_service
        self.result = False
        self.window = tk.Toplevel(parent)
        self.window.title("Gérer les modes de paiement")
        self.window.geometry("400x350")
        self.window.grab_set()
        self._create_ui()
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    def _create_ui(self):
        tk.Label(self.window, text="Modes de paiement:", font=("Arial", 12, "bold")).pack(pady=10)
        self.listbox = tk.Listbox(self.window, height=10)
        self._reload_methods()
        self.listbox.pack(padx=10, pady=5, fill="both", expand=True)
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="Ajouter", command=self._add_method).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Supprimer", command=self._remove_method).pack(side="left", padx=5)
        tk.Button(btn_frame, text="Fermer", command=self._close).pack(side="left", padx=20)
    def _reload_methods(self):
        self.listbox.delete(0, tk.END)
        if self.use_service_layer:
            self.methods = self.bank_service.get_payment_methods()
        else:
            self.methods = bank.get_payment_methods()
        for k, label in self.methods:
            self.listbox.insert(tk.END, f"{label} ({k})")
    def _add_method(self):
        key = simpledialog.askstring("Clé du mode", "Entrez la clé (ex: cheque):", parent=self.window)
        if not key:
            return
        label = simpledialog.askstring("Nom du mode", "Entrez le nom (ex: 🧾 Chèque):", parent=self.window)
        if not label:
            return
        if self.use_service_layer:
            self.bank_service.add_payment_method(key, label)
        else:
            bank.add_payment_method(key, label)
        self._reload_methods()
        self.result = True
    def _remove_method(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        key = self.methods[idx][0]
        if self.use_service_layer:
            self.bank_service.remove_payment_method(key)
        else:
            bank.remove_payment_method(key)
        self._reload_methods()
        self.result = True
    def _close(self):
        self.window.destroy() 