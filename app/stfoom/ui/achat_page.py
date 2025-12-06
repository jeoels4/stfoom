import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from datetime import date, datetime
from .shared_widgets import format_money  # Import centralized money formatting

# ✅ PHASE 3 ARCHITECTURE: Services-only architecture
# Legacy imports disabled - using services instead
LEGACY_AVAILABLE = False

from tkcalendar import Calendar, DateEntry

# -------------------------------------------------
# Performance / Debug Controls (safe, minimal risk)
# -------------------------------------------------
ACHAT_VERBOSE_LOG = False  # Set True only for deep troubleshooting

def achat_debug(msg: str):
    if ACHAT_VERBOSE_LOG:
        try:
            print(msg)
        except Exception:
            pass
# Imports
# Robust import for fournisseur_selector to survive frozen path differences
try:
    from stfoom.ui import fournisseur_selector  # primary (when package root is on path)
except Exception:
    try:
        from app.stfoom.ui import fournisseur_selector  # fallback when 'app' added to sys.path
    except Exception as e:  # final fallback: disable advanced selector gracefully
        print(f"[ACHAT_PAGE] WARNING: fournisseur_selector unavailable in this environment: {e}")
        fournisseur_selector = None  # type: ignore
from .permission_utils import check_ui_permission, require_ui_permission, disable_button_if_no_permission

# ✅ TEMPORARY WORKAROUND: Add mock objects to prevent crashes during migration
class MockPayments:
    @staticmethod
    def get_paiements_facture(achat_id): return []
    @staticmethod
    def supprimer_paiement(payment_id, is_achat=True): return True
    @staticmethod
    def formater_statut(statut): return statut or "Non payé"
    @staticmethod
    def formater_methode_paiement(methode, mode): return f"{methode or 'N/A'}"
    @staticmethod
    def modifier_paiement(*args, **kwargs): return True
    @staticmethod
    def marquer_facture_payee_banque(*args, **kwargs): return True
    @staticmethod
    def marquer_facture_payee_caisse(*args, **kwargs): return True

class MockBank:
    @staticmethod
    def get_payment_methods(): return [("especes", "Espèces"), ("cheque", "Chèque"), ("virement", "Virement")]

class MockTaxesLogic:
    @staticmethod
    def get_all_taxes(): return []

# Try to import real tax logic, fallback to mock if not available
try:
    from ..logic import taxes as taxes_logic
    achat_debug("[ACHAT_PAGE] Successfully connected to real tax system")
except ImportError as e:
    achat_debug(f"[ACHAT_PAGE] Using mock tax logic: {e}")
    taxes_logic = MockTaxesLogic()

# ✅ UNIFIED PAYMENT: Use PaymentService directly like vente (no wrapper)
try:
    from ..services.payment_service import PaymentService
    from ..services.bank_service import BankService
    from ..data.bank_repository import BankRepository
    
    # Create real services (to be used directly by AchatPage instances)
    _global_payment_service = PaymentService()
    _global_bank_repository = BankRepository()  
    _global_bank_service = BankService(_global_bank_repository)
    
    achat_debug("[ACHAT_PAGE] ✅ PaymentService and BankService ready for direct use")
    
except ImportError as e:
    print(f"[ACHAT_PAGE] ❌ Could not load real services: {e}")
    _global_payment_service = None
    _global_bank_service = None

class AchatPage(ttk.Frame):
    COLS = [
        ("date", "Date"),
        ("num_facture", "Numéro Facture"),
        ("fournisseur", "Fournisseur"),
        ("mt_ht", "Montant HT"),
        ("tva", "TVA 19%"),
        ("autres_taxes", "Autres Taxes"),
        ("timbre", "Timbre"),
        ("ttc", "Total TTC"),
        ("paiement_statut", "Statut Paiement"),
        ("paiement_methode", "Méthode Paiement"),
    ]

    def __init__(self, parent, container_or_go_home, go_home=None):
        super().__init__(parent, style="FactureMain.TFrame")
        
        # 🎯 Phase 2C: Handle both DI and legacy calling patterns
        if go_home is None:
            # Legacy pattern: AchatPage(parent, go_home)
            self.go_home = container_or_go_home
            self.purchase_service = None
            achat_debug("[ACHAT_PAGE] ⚠️  Using legacy mode (no dependency injection)")
        else:
            # DI pattern: AchatPage(parent, container, go_home)
            self.go_home = go_home
            container = container_or_go_home
            
            if hasattr(container, 'get'):
                try:
                    self.purchase_service = container.get('purchase_service')
                    achat_debug("[ACHAT_PAGE] 🚀 Using dependency injection with PurchaseService")
                except Exception as e:
                    achat_debug(f"[ACHAT_PAGE] ❌ Error getting purchase_service: {e}")
                    self.purchase_service = None
                    achat_debug("[ACHAT_PAGE] ⚠️  Falling back to legacy mode due to service error")
            else:
                achat_debug(f"[ACHAT_PAGE] ❌ Container has no 'get' method: {type(container)}")
                self.purchase_service = None
                achat_debug("[ACHAT_PAGE] ⚠️  Falling back to legacy mode due to invalid container")
        
        # Initialize PaymentService for unified status/color handling (same as vente)
        try:
            from ..services.payment_service import PaymentService
            self.payment_service = PaymentService()
            achat_debug("[ACHAT_PAGE] ✅ PaymentService initialized for status/color consistency")
        except Exception as e:
            achat_debug(f"[ACHAT_PAGE] ❌ Error initializing PaymentService: {e}")
            self.payment_service = None
        
        # Initialize BankService for proper bank selection
        try:
            if hasattr(container_or_go_home, 'get') and callable(container_or_go_home.get):
                # Try to get BankService from dependency injection
                try:
                    self.bank_service = container_or_go_home.get('bank_service')
                    achat_debug("[ACHAT_PAGE] ✅ BankService initialized from dependency injection")
                except:
                    self.bank_service = None
            
            if not self.bank_service:
                # Fallback to manual initialization
                from ..services.bank_service import BankService
                from ..data.bank_repository import BankRepository
                bank_repository = BankRepository()
                self.bank_service = BankService(bank_repository)
                achat_debug("[ACHAT_PAGE] ✅ BankService initialized manually")
        except Exception as e:
            achat_debug(f"[ACHAT_PAGE] ❌ Error initializing BankService: {e}")
            self.bank_service = None
            
        # Initialize RetenuService for retenu calculations
        try:
            if hasattr(container_or_go_home, 'get') and callable(container_or_go_home.get):
                # Try to get RetenuService from dependency injection
                try:
                    self.retenu_service = container_or_go_home.get('retenu_service')
                    achat_debug("[ACHAT_PAGE] ✅ RetenuService initialized from dependency injection")
                except:
                    self.retenu_service = None
            
            if not self.retenu_service:
                # Fallback to manual initialization
                from ..services.retenu_service import RetenuService
                from ..data.retenu_repository import RetenuRepository
                retenu_repository = RetenuRepository()
                self.retenu_service = RetenuService(retenu_repository)
                achat_debug("[ACHAT_PAGE] ✅ RetenuService initialized manually")
        except Exception as e:
            achat_debug(f"[ACHAT_PAGE] ❌ Error initializing RetenuService: {e}")
            self.retenu_service = None
        
        self.pack(fill="both", expand=True)
        
        # Initialize fournisseur refresh callbacks
        self._fournisseur_refresh_callbacks = []
        
        self._create_ui()
        self._load_rows()

    def _create_ui(self):
        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=self.go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Achats – Journal des Achats", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- smart search ----------
        self._setup_smart_search()

        # ---------- table section ----------
        table_frame = ttk.LabelFrame(self, text="Liste des Achats", style="FactureSection.TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10), ipadx=8, ipady=8)

        self.tree = ttk.Treeview(table_frame, columns=[c[0] for c in self.COLS], show="headings", height=16, style="Custom.Treeview")
        for key, title in self.COLS:
            self.tree.heading(key, text=title)
            self.tree.column(key, anchor="center", width=100)
        self.tree.column("fournisseur", anchor="w", width=200)
        self.tree.column("ttc", anchor="e", width=120)
        self.tree.column("paiement_statut", anchor="center", width=120)
        self.tree.column("paiement_methode", anchor="center", width=80)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

        # Configure tags for payment status colors - same as vente for consistency
        self.tree.tag_configure("payé", foreground="#155724", background="#d4edda")  # Darker green on light green for paid
        self.tree.tag_configure("partiellement payé", foreground="#b8860b", background="#fff3cd")  # Darker yellow on light yellow for partially paid
        self.tree.tag_configure("partiellement_payé", foreground="#b8860b", background="#fff3cd")  # Legacy underscore format
        self.tree.tag_configure("non payé", foreground="#721c24", background="#f8d7da")  # Dark red on light red for unpaid
        self.tree.tag_configure("non_payé", foreground="#721c24", background="#f8d7da")  # Legacy underscore format

        # ---------- action buttons ----------
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20)
        for i in range(5):
            btn_frame.columnconfigure(i, weight=1)
        
        # Add Achat button (green)
        add_btn = tk.Button(
            btn_frame,
            text="➕ Ajouter Achat",
            command=self._on_add,
            font=("Segoe UI", 12, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        add_btn.grid(row=0, column=0, padx=5, sticky="ew", ipadx=10, ipady=6)
        
        # Edit button (blue)
        edit_btn = tk.Button(
            btn_frame,
            text="✏️ Modifier",
            command=self._on_edit,
            font=("Segoe UI", 12, "bold"),
            bg="#0074d9",
            fg="#fff",
            activebackground="#005fa3",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        edit_btn.grid(row=0, column=1, padx=5, sticky="ew", ipadx=10, ipady=6)
        
        # Delete button (red)
        del_btn = tk.Button(
            btn_frame,
            text="❌ Supprimer",
            command=self._on_delete,
            font=("Segoe UI", 12, "bold"),
            bg="#dc3545",
            fg="#fff",
            activebackground="#c82333",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        del_btn.grid(row=0, column=2, padx=5, sticky="ew", ipadx=10, ipady=6)
        
        # Mark Paid button (orange)
        paid_btn = tk.Button(
            btn_frame,
            text="🪙 Marquer Payé",
            command=self._on_mark_paid,
            font=("Segoe UI", 12, "bold"),
            bg="#fd7e14",
            fg="#fff",
            activebackground="#e55a00",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        paid_btn.grid(row=0, column=3, padx=5, sticky="ew", ipadx=10, ipady=6)
        
        # Add Multiple Payment button (teal)
        multi_payment_btn = tk.Button(
            btn_frame,
            text="💳 Paiement Multiple",
            command=self._on_multiple_payment,
            font=("Segoe UI", 11, "bold"),
            bg="#20c997",
            fg="#fff",
            activebackground="#1ba085",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        multi_payment_btn.grid(row=1, column=3, padx=5, pady=2, sticky="ew", ipadx=10, ipady=6)

        # Add Retenu button (purple)
        retenu_btn = tk.Button(
            btn_frame,
            text="📋 Ajouter une retenue",
            command=self._on_add_retenu,
            font=("Segoe UI", 12, "bold"),
            bg="#6f42c1",
            fg="#fff",
            activebackground="#5a32a3",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        retenu_btn.grid(row=0, column=4, padx=5, sticky="ew", ipadx=10, ipady=6)

        # Apply permission-based button states
        disable_button_if_no_permission(add_btn, "achat", "create")
        disable_button_if_no_permission(edit_btn, "achat", "update")
        disable_button_if_no_permission(del_btn, "achat", "delete")
        disable_button_if_no_permission(paid_btn, "achat", "update")
        disable_button_if_no_permission(multi_payment_btn, "achat", "update")
        disable_button_if_no_permission(retenu_btn, "retenu", "create")

    def _setup_smart_search(self):
        """Setup page-specific search for achat page."""
        try:
            from .enhanced_search import create_page_search
            
            # Create achat-specific search function
            def search_achats_in_page(query):
                """Search only in current achat page data."""
                results = []
                try:
                    query_lower = query.lower()
                    
                    # Search in current treeview data (page-specific)
                    for item in self.tree.get_children():
                        values = self.tree.item(item)['values']
                        if len(values) >= len(self.COLS):
                            # Create searchable text from all columns
                            searchable_text = " ".join(str(val).lower() for val in values)
                            
                            # Check if query matches any field
                            if query_lower in searchable_text:
                                # Format result for display
                                fournisseur = values[2] if len(values) > 2 else "Fournisseur inconnu"
                                num_facture = values[1] if len(values) > 1 else "N/A"
                                ttc = values[5] if len(values) > 5 else "0"
                                date = values[0] if len(values) > 0 else "Date inconnue"
                                
                                results.append({
                                    'type': 'Achat',
                                    'content': f"#{num_facture} - {fournisseur}",
                                    'details': f"{ttc} TND - {date}",
                                    'icon': '🛒',
                                    'item_id': item,  # Store tree item ID for selection
                                    'relevance': self._calculate_achat_search_relevance(query_lower, values)
                                })
                                
                        if len(results) >= 20:  # Limit results
                            break
                    
                    # Sort by relevance
                    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
                    
                except Exception as e:
                    print(f"[ACHAT_SEARCH] Error: {e}")
                    
                return results
            
            # Create the page-specific search widget
            self.page_search = create_page_search(self, "Achats", search_achats_in_page)
            
            # Override the result selection to highlight in tree
            def on_achat_select(result):
                """Handle selection of achat search result."""
                try:
                    item_id = result.get('item_id')
                    if item_id and self.tree.exists(item_id):
                        # Clear current selection
                        self.tree.selection_remove(*self.tree.selection())
                        # Select the found item
                        self.tree.selection_set(item_id)
                        self.tree.see(item_id)
                        self.tree.focus(item_id)
                        
                        # Optionally show details
                        messagebox.showinfo(
                            "Achat trouvé", 
                            f"Achat sélectionné: {result['content']}\n{result['details']}"
                        )
                except Exception as e:
                    print(f"[ACHAT_SEARCH] Selection error: {e}")
            
            self.page_search.on_result_select = on_achat_select
            
            print("[ACHAT] Page-specific search setup complete")
            
        except Exception as e:
            print(f"[ACHAT_SEARCH] Setup error: {e}")
            # Fallback to simple label
            ttk.Label(self, text="🔍 Recherche Achats", font=('Segoe UI', 12, 'bold')).pack(pady=5)
    
    def _calculate_achat_search_relevance(self, query: str, values: list) -> int:
        """Calculate search relevance score for ranking achat results."""
        relevance = 0
        
        # Higher score for matches in important fields
        if len(values) > 2 and query in values[2].lower():  # Fournisseur name
            relevance += 15
        if len(values) > 1 and query in str(values[1]).lower():  # Facture number  
            relevance += 20
        if len(values) > 0 and query in values[0].lower():  # Date
            relevance += 10
        
        # Lower score for matches in other fields
        for i, val in enumerate(values):
            if i not in [0, 1, 2] and query in str(val).lower():
                relevance += 5
                
        return relevance

    def _load_achat_from_search(self, achat_data):
        """Load an achat from search results for editing."""
        try:
            print(f"[ACHAT] Loading achat from search: {achat_data}")
            # Here you would implement editing the achat
            # For now, just show it in a dialog
            self._on_edit_with_data(achat_data)
        except Exception as e:
            print(f"[ACHAT] Error loading achat from search: {e}")

    def _select_achat_from_search(self, item_id):
        """Select an achat from search results in the treeview."""
        try:
            # Select the item in the treeview
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            self.tree.focus(item_id)
            print(f"[ACHAT] Selected achat from search")
        except Exception as e:
            print(f"[ACHAT] Error selecting achat from search: {e}")

    def _on_edit_with_data(self, achat_data):
        """Open edit dialog with pre-filled data from search."""
        try:
            # Convert search data to the format expected by the edit dialog
            if self.purchase_service:
                # Use service-based editing
                dialog = AchatDialog(self, preset=achat_data, purchase_service=self.purchase_service)
            else:
                # Use legacy editing
                dialog = AchatDialog(self, preset=achat_data)
            
            # Set up refresh callback
            dialog.refresh_callback = self._load_rows
            
            # Show dialog
            if hasattr(dialog, 'show'):
                dialog.show()
            else:
                dialog.wait_window(dialog)
                
        except Exception as e:
            print(f"[ACHAT] Error opening edit dialog with data: {e}")
            messagebox.showerror("Erreur", f"Impossible d'ouvrir le dialogue d'édition: {e}")

    def _get_retenu_total_for_invoice(self, achat_id: int) -> float:
        """
        Get total retenu amount for an achat invoice - IDENTICAL TO VENTE
        Checks both:
        1. Explicit retenu records in retenu table
        2. Retenue embedded in payment notes (for 'marqué payé' payments)
        """
        try:
            # First, try to get explicit retenu records
            retenu_total = 0.0
            
            # Use dependency injection if available
            if self.retenu_service:
                retenus = self.retenu_service.get_retenus_by_facture(achat_id)
                retenu_total = sum(r.get('amount', 0) for r in retenus)
            else:
                # Fallback: create service manually with proper repository
                from app.stfoom.services.retenu_service import RetenuService
                from app.stfoom.data.retenu_repository import RetenuRepository
                
                retenu_repository = RetenuRepository()
                retenu_service = RetenuService(retenu_repository)
                retenus = retenu_service.get_retenus_by_facture(achat_id)
                retenu_total = sum(r.get('amount', 0) for r in retenus)
            
            # If no explicit retenu records found, check payment notes for embedded retenue
            if retenu_total == 0.0:
                retenu_total = self._extract_retenu_from_payment_notes(achat_id)
            
            return retenu_total
            
        except Exception as e:
            print(f"[ACHAT] Error getting retenu total: {e}")
            return 0.0

    def _extract_retenu_from_payment_notes(self, achat_id: int) -> float:
        """Extract retenue amount from payment notes for 'marqué payé' payments - IDENTICAL TO VENTE"""
        try:
            if not hasattr(self, 'payment_service') or not self.payment_service:
                return 0.0
                
            # Get all payments for this achat
            payments = self.payment_service.get_invoice_payments(achat_id, is_achat=True)
            
            total_embedded_retenu = 0.0
            
            for payment in payments:
                notes = payment.get('notes', '') or ''
                
                # Look for retenu pattern in notes: [Retenu: X.XX% = Y.YYY DT]
                import re
                retenu_pattern = r'\[Retenu: [\d\.]+% = ([\d\.]+) DT\]'
                matches = re.findall(retenu_pattern, notes)
                
                for match in matches:
                    try:
                        retenu_amount = float(match)
                        total_embedded_retenu += retenu_amount
                    except ValueError:
                        continue
                        
            return total_embedded_retenu
            
        except Exception as e:
            print(f"[ACHAT] Error extracting retenu from payment notes: {e}")
            return 0.0

    def _load_rows(self):
        import time
        start_time = time.perf_counter()
        self.tree.delete(*self.tree.get_children())
        
        # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
        if self.purchase_service:
            # Modern approach: Use dependency injection
            self._rows = self.purchase_service.get_all_purchases()
        else:
            # Legacy approach: Direct module access
            self._rows = self.purchase_service.get_all_purchases() if self.purchase_service else []
        
        # ⚡ PERFORMANCE: Cache payment status to avoid repeated expensive calculations
        print(f"[ACHAT] Loading {len(self._rows)} achats - using lazy payment status loading")
        self._payment_status_cache = {}  # Cache for payment statuses
        self._multi_avoir_cache = {}  # Cache for MULTI-PAIEMENT avoir totals
        
        processed = 0
        with_payments = 0
        for a in self._rows:
            taxes = a.get('taxes', [])
            
            # Parse taxes if it's a string (JSON)
            if isinstance(taxes, str):
                try:
                    import json
                    taxes = json.loads(taxes)
                except (json.JSONDecodeError, TypeError):
                    taxes = []
            elif not isinstance(taxes, list):
                taxes = []
            
            # Extract TVA 19% and other taxes
            tva_value = 0
            autres_taxes_list = []
            for t in taxes:
                if isinstance(t, dict):
                    if t.get('name', '').lower() == 'tva 19%':
                        tva_value = t.get('value', 0)
                    else:
                        autres_taxes_list.append(f"{t.get('name', '')}: {t.get('value', 0)}")
                elif isinstance(t, str):
                    # Handle string format
                    autres_taxes_list.append(str(t))
            autres_taxes_str = ", ".join(autres_taxes_list)

            # ⚡ PERFORMANCE OPTIMIZATION: Use lightweight payment check instead of full avoir calculation
            # Get payments but skip the expensive avoir-aware allocation calculation
            achat_id = a["id"]
            montant_total = float(a.get('ttc', 0))
            
            # Quick lightweight check: Get payment sum with retenu, avoir, and tolerance
            if hasattr(self, 'payment_service') and self.payment_service:
                # Get payments list (fast - just a SELECT query)
                paiements = self.payment_service.get_invoice_payments(achat_id, is_achat=True)
                
                if paiements:
                    # Sum actual payments
                    total_paye = sum(float(p.get('montant_paye', 0)) for p in paiements)
                    
                    # Extract retenu from payment notes
                    import re
                    total_retenu = 0.0
                    multi_ref = None
                    for p in paiements:
                        notes = p.get('notes', '') or ''
                        # Extract retenu - try both formats: absolute amount and percentage
                        # Format 1: [Retenu: X.XX% = Y.YYY DT]
                        matches = re.findall(r'\[Retenu:.*?=\s*([\d\.]+)\s*DT?\]', notes)
                        for match in matches:
                            try:
                                total_retenu += float(match)
                            except ValueError:
                                continue
                        # Format 2: [Retenu: X.X%] (percentage only - need to calculate)
                        if not matches:  # Only if Format 1 didn't match
                            percent_matches = re.findall(r'\[Retenu:\s*([\d\.]+)%\]', notes)
                            for percent_str in percent_matches:
                                try:
                                    percent = float(percent_str)
                                    # Calculate retenu from percentage of TTC
                                    retenu_amount = montant_total * (percent / 100.0)
                                    total_retenu += retenu_amount
                                except ValueError:
                                    continue
                        # Extract MULTI reference
                        if 'MULTI-' in notes and not multi_ref:
                            m = re.search(r'(MULTI-\d{8}-\d{6}-\d+)', notes)
                            if m:
                                multi_ref = m.group(1)
                    
                    # Check for avoir in MULTI-PAIEMENT batch (optimized with caching)
                    total_avoir = 0.0
                    if multi_ref:
                        # Check cache first to avoid repeated DB queries
                        if multi_ref in self._multi_avoir_cache:
                            total_avoir = self._multi_avoir_cache[multi_ref]
                        else:
                            # Query DB once for this MULTI batch and cache the result
                            try:
                                import sqlite3
                                from app.core.path_manager import path_manager
                                conn = sqlite3.connect(path_manager.get_database_path())
                                cursor = conn.cursor()
                                
                                # Get all nfacture IDs in this MULTI batch
                                cursor.execute("""
                                    SELECT DISTINCT nfacture 
                                    FROM paiements_factures 
                                    WHERE notes LIKE ?
                                """, (f'%{multi_ref}%',))
                                batch_ids = [row[0] for row in cursor.fetchall()]
                                
                                # Calculate total avoir for this batch
                                batch_avoir_total = 0.0
                                for batch_id in batch_ids:
                                    cursor.execute("SELECT ttc FROM achats WHERE id = ?", (batch_id,))
                                    achat_row = cursor.fetchone()
                                    if achat_row:
                                        batch_ttc = float(achat_row[0] or 0)
                                        if batch_ttc < 0:  # This is an avoir
                                            cursor.execute("""
                                                SELECT SUM(montant_paye) 
                                                FROM paiements_factures 
                                                WHERE nfacture = ?
                                            """, (batch_id,))
                                            avoir_sum = cursor.fetchone()[0]
                                            if avoir_sum:
                                                batch_avoir_total += float(avoir_sum)
                                
                                conn.close()
                                
                                # Cache the result
                                self._multi_avoir_cache[multi_ref] = batch_avoir_total
                                total_avoir = batch_avoir_total
                            except Exception as e:
                                # If avoir detection fails, cache 0 and continue
                                self._multi_avoir_cache[multi_ref] = 0.0
                                total_avoir = 0.0
                    
                    # Get tolerance from settings
                    tolerance = 0.01  # Default small tolerance
                    try:
                        from app.stfoom.services.settings_service import SettingsService
                        settings_service = SettingsService()
                        tolerance = settings_service.get_payment_tolerance()
                    except Exception:
                        tolerance = 40.0  # Default from original code
                    
                    # Calculate remaining: TTC - Paid - Retenu - Avoir
                    restant = montant_total - total_paye - total_retenu - total_avoir
                    
                    # Determine status with tolerance
                    if restant <= tolerance:  # Fully paid (within tolerance)
                        tag = 'payé'
                        statut_paiement = {'statut': 'payé', 'montant_paye': total_paye, 'montant_restant': 0}
                    elif total_paye > 0 or total_avoir > 0:  # Partially paid
                        tag = 'partiellement_payé'
                        statut_paiement = {'statut': 'partiellement_payé', 'montant_paye': total_paye + total_avoir, 'montant_restant': restant}
                    else:  # No payments
                        tag = 'non_payé'
                        statut_paiement = {'statut': 'non_payé', 'montant_paye': 0, 'montant_restant': montant_total}
                    
                    # Get payment method from most recent payment
                    payment_method = paiements[0].get('methode_paiement', '') if paiements else ''
                    methode_paiement = self.payment_service.format_payment_method(payment_method)
                else:
                    # No payments
                    tag = 'non_payé'
                    statut_paiement = {'statut': 'non_payé', 'montant_paye': 0, 'montant_restant': montant_total}
                    methode_paiement = ""
            else:
                # Fallback if no payment service
                tag = 'non_payé'
                statut_paiement = {'statut': 'non_payé', 'montant_paye': 0, 'montant_restant': montant_total}
                methode_paiement = ""

            # Compute display supplier name (alias if present)
            fournisseur_display = a.get('fournisseur', '')
            if a.get('fournisseur_alias'):
                fournisseur_display = f"{fournisseur_display} — {a.get('fournisseur_alias')}"

            self.tree.insert("", "end", iid=str(a["id"]), values=(
                a.get("date", ""),
                a.get("num_facture", ""),
                fournisseur_display,
                format_money(a.get('mt_ht', 0)),
                format_money(tva_value),
                autres_taxes_str,
                format_money(a.get('timbre', 0)),
                format_money(a.get('ttc', 0)),
                self.payment_service.format_payment_status(statut_paiement['statut']) if hasattr(self, 'payment_service') and self.payment_service else statut_paiement['statut'],
                methode_paiement,
            ), tags=(tag,))
            processed += 1
            if paiement_statut := statut_paiement.get('statut'):
                if paiement_statut in ("payé", "partiellement payé", "partiellement_payé"):
                    with_payments += 1
        duration = (time.perf_counter() - start_time) * 1000
        achat_debug(f"[ACHAT_PAGE] _load_rows loaded {processed} rows (with payments: {with_payments}) in {duration:.1f} ms")

    def _selected_achat_id(self):
        sel = self.tree.selection()
        if not sel:
            return None
        try:
            return int(sel[0])
        except Exception:
            return None

    def _on_add(self):
        # Check permission first
        if not check_ui_permission("achat", "create"):
            return
            
        dialog = AchatDialog(self, purchase_service=self.purchase_service)
        if dialog.result:
            self._load_rows()

    def _on_edit(self):
        # Check permission first
        if not check_ui_permission("achat", "update"):
            return
            
        achat_id = self._selected_achat_id()
        if achat_id is None:
            messagebox.showwarning("Sélection", "Choisissez un achat à modifier.")
            return
        
        # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
        if self.purchase_service:
            preset = self.purchase_service.get_purchase_by_id(achat_id)
        else:
            preset = self.purchase_service.get_purchase_by_id(achat_id) if self.purchase_service else None
        
        dialog = AchatDialog(self, preset=preset, purchase_service=self.purchase_service)
        if dialog.result:
            self._load_rows()

    def _on_delete(self):
        # Check permission first
        if not check_ui_permission("achat", "delete"):
            return
            
        achat_id = self._selected_achat_id()
        if achat_id is None:
            messagebox.showwarning("Sélection", "Choisissez un achat à supprimer.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer cet achat ?"):
            return
        # Cascade delete: delete all payments and linked retenu
        # ✅ FIXED: Disable legacy imports to prevent app restart
        # from stfoom.logicold import payments, retenu  # DISABLED
        # paiements = payments.get_paiements_facture(achat_id)  # DISABLED  
        # for p in paiements:
        #     payments.supprimer_paiement(p['id'], is_achat=True)  # DISABLED
        # Note: retenus will be automatically deleted by the delete_achat() function
        # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
        if self.purchase_service:
            success = self.purchase_service.delete_purchase(achat_id)
        else:
            success = self.purchase_service.delete_purchase(achat_id) if self.purchase_service else False
        
        if success:
            self._load_rows()
            messagebox.showinfo("Succès", "Achat supprimé.")
        else:
            messagebox.showerror("Erreur", "Erreur lors de la suppression.")

    def _on_mark_paid(self):
        # Check permission first
        if not check_ui_permission("achat", "update"):
            return
            
        achat_id = self._selected_achat_id()
        if achat_id is None:
            messagebox.showwarning("Sélection", "Choisissez un achat à marquer comme payé.")
            return
        
        # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
        if self.purchase_service:
            preset = self.purchase_service.get_purchase_by_id(achat_id)
        else:
            preset = self.purchase_service.get_purchase_by_id(achat_id) if self.purchase_service else None
        if not preset:
            messagebox.showerror("Erreur", "Achat introuvable.")
            return
            
        # Use enhanced original AchatPaymentDialog with timbre-aware retenu calculation
        payment_dialog = AchatPaymentDialog(
            parent=self, 
            achat_id=achat_id, 
            achat=preset
        )
        
        if payment_dialog.result:
            # Refresh the display to show updated payment status
            self._load_rows()
            messagebox.showinfo("Succès", "Paiement traité avec succès!")

    def _on_multiple_payment(self):
        """Handle multiple invoice payment"""
        if not check_ui_permission("achat", "update"):
            return
            
        # Get selected invoices or show selection dialog
        selected_items = self.tree.selection()
        
        if not selected_items:
            # No selection - show all unpaid invoices dialog
            self._show_multiple_payment_selection()
        else:
            # Use selected invoices
            invoice_list = []
            for item in selected_items:
                values = self.tree.item(item)['values']
                if len(values) >= 6:  # Ensure we have enough columns
                    achat_id = int(item)  # Use the iid which contains the actual ID
                    # Get achat details
                    if self.purchase_service:
                        achat_data = self.purchase_service.get_purchase_by_id(achat_id)
                    else:
                        achat_data = None
                        
                    if achat_data:
                            ttc = achat_data.get('ttc', 0)
                            # Get paid amount
                            status = self.purchase_service.get_payment_status(achat_id, ttc)
                            paid = status.get('paye', 0)
                            remaining = ttc - paid
                            
                            # Include both unpaid invoices and avoirs (negative remaining)
                            if remaining != 0:
                                # Build display fournisseur with alias
                                base_f = achat_data.get('fournisseur', '')
                                alias_f = achat_data.get('fournisseur_alias') or ''
                                display_f = f"{base_f} — {alias_f}" if alias_f else base_f
                                invoice_list.append({
                                    'id': achat_id,
                                    'fournisseur': display_f,
                                    'amount': ttc,
                                    'paid': paid,
                                    'remaining': remaining,
                                    'type': 'achat'
                                })
            
            if invoice_list:
                self._open_multiple_payment_dialog(invoice_list)
            else:
                messagebox.showinfo("Information", "Aucune facture impayée sélectionnée")

    def _show_multiple_payment_selection(self):
        """Show dialog to select invoices for multiple payment"""
        achat_debug("[ACHAT_PAGE] Starting multiple payment selection...")
        
        # Get all unpaid invoices
        unpaid_invoices = []
        
        if self.purchase_service:
            achat_debug("[ACHAT_PAGE] Using purchase_service to get all purchases")
            try:
                all_achats = self.purchase_service.get_all_purchases()
                achat_debug(f"[ACHAT_PAGE] Found {len(all_achats)} total achats")
            except Exception as e:
                achat_debug(f"[ACHAT_PAGE] Error getting all purchases: {e}")
                all_achats = []
            
            for i, achat in enumerate(all_achats):
                achat_id = achat.get('id')
                ttc = achat.get('ttc', 0)
                
                achat_debug(f"[ACHAT_PAGE] Processing achat {i+1}: ID={achat_id}, Total={ttc}")
                
                # Use PaymentService for consistent status calculation
                if hasattr(self, 'payment_service') and self.payment_service:
                    achat_debug(f"[ACHAT_PAGE] Using PaymentService for achat {achat_id}")
                    # ✅ IDENTICAL TO VENTE: Include retenu_total in payment status calculation
                    retenu_total = self._get_retenu_total_for_invoice(achat_id)
                    status = self.payment_service.get_payment_status(achat_id, ttc, retenu_total)
                    paid = status.get('total_paid', 0)
                    remaining = status.get('remaining', ttc)
                else:
                    achat_debug(f"[ACHAT_PAGE] Using PurchaseService fallback for achat {achat_id}")
                    # Fallback to purchase service
                    status = self.purchase_service.get_payment_status(achat_id, ttc)
                    paid = status.get('paye', 0)
                    remaining = ttc - paid
                
                achat_debug(f"[ACHAT_PAGE] Achat {achat_id}: Paid={paid}, Remaining={remaining}")
                
                # Include both unpaid invoices (remaining > 0) and avoir credits (remaining < 0)
                if remaining != 0:
                    achat_debug(f"[ACHAT_PAGE] Adding achat {achat_id} to selection list (remaining={remaining})")
                    # Build display fournisseur with alias
                    base_f = achat.get('fournisseur', '')
                    alias_f = achat.get('fournisseur_alias') or ''
                    display_f = f"{base_f} — {alias_f}" if alias_f else base_f
                    unpaid_invoices.append({
                        'id': achat_id,
                        'fournisseur': display_f,
                        'amount': ttc,
                        'paid': paid,
                        'remaining': remaining,
                        'timbre': achat.get('timbre', 1.0),  # Add timbre field
                        'type': 'achat'
                    })
        else:
            achat_debug("[ACHAT_PAGE] ERROR: purchase_service is None!")
            
        achat_debug(f"[ACHAT_PAGE] Final unpaid invoices count: {len(unpaid_invoices)}")
        
        if unpaid_invoices:
            self._open_multiple_payment_dialog(unpaid_invoices)
        else:
            messagebox.showinfo("Information", "Aucune facture impayée trouvée")

    def _open_multiple_payment_dialog(self, invoice_list):
        """Open the enhanced multiple payment dialog for achat with ALL normal payment features"""
        try:
            from .enhanced_multiple_payment_dialog import show_enhanced_multiple_payment_dialog
            
            # Prepare invoices data for unified system
            invoices_data = []
            for invoice in invoice_list:
                # Fix: Use correct field names from the invoice_list structure
                ttc_amount = invoice.get('amount', 0)  # Use 'amount' not 'ttc'
                invoice_data = {
                    'nfacture': invoice.get('id', ''),
                    'ttc': ttc_amount,
                    'timbre': invoice.get('timbre', 1.0),
                    'client': invoice.get('fournisseur', 'N/A'),  # Use 'fournisseur' not 'nom_fournisseur'
                    'remaining': invoice.get('remaining', ttc_amount)
                }
                invoices_data.append(invoice_data)
            
            result = show_enhanced_multiple_payment_dialog(self, invoices_data, is_achat=True,
                                                         payment_service=getattr(self, 'payment_service', None),
                                                         bank_service=getattr(self, 'bank_service', None),
                                                         retenu_service=getattr(self, 'retenu_service', None))
            
            if result:
                # Refresh the view after successful payment
                self._load_rows()
                
                # Show simple success message
                success_msg = f"Paiement multiple d'achat enregistré avec succès!\n\n"
                success_msg += f"✅ {len(invoices_data)} factures traitées\n"
                success_msg += f"🔄 La page a été actualisée automatiquement\n"
                
                messagebox.showinfo("Succès", success_msg)
                
        except ImportError:
            messagebox.showerror("Erreur", "Module de paiement multiple non disponible")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du paiement multiple: {e}")

    def _on_add_retenu(self):
        # Check permission first
        if not check_ui_permission("retenu", "create"):
            return
            
        achat_id = self._selected_achat_id()
        if achat_id is None:
            messagebox.showwarning("Sélection", "Choisissez un achat pour ajouter une retenue.")
            return
        
        # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
        if self.purchase_service:
            preset = self.purchase_service.get_purchase_by_id(achat_id)
        else:
            preset = self.purchase_service.get_purchase_by_id(achat_id) if self.purchase_service else None
        # ✅ FIXED: Disable retenu import to prevent issues
        # from stfoom.ui.retenu_page import RetenuDialog  # DISABLED
        # ✅ FIXED: Disable retenu functionality temporarily to prevent crashes
        # RetenuDialog functionality disabled - needs service migration
        messagebox.showwarning("Fonctionnalité en migration", "La création de retenu est temporairement désactivée pendant la migration vers les services.")
        return  # Skip retenu creation for now

class AchatDialog:
    def __init__(self, parent, preset=None, purchase_service=None):
        self.parent = parent
        self.result = False
        self.preset = preset
        
        # 🎯 Phase 2C: Store purchase service reference for modern approach
        self.purchase_service = purchase_service
        
        self.window = tk.Toplevel(parent)
        self.window.title("Ajouter Achat" if not preset else "Modifier Achat")
        self.window.geometry("520x600")
        self._create_ui()
        self._load_data()
        self.window.transient(parent)
        self.window.grab_set()
        self.window.focus_force()
        parent.wait_window(self.window)

    def _create_ui(self):
        # Fournisseur with auto-refresh functionality
        fournisseur_frame = tk.LabelFrame(self.window, text="Fournisseur")
        fournisseur_frame.pack(pady=2, fill="x", padx=10)
        
        # Initialize refresh system
        self._fournisseur_refresh_callbacks = []
        
        # Initialize fournisseur variable first
        self.fournisseur_var = tk.StringVar()
        # Initialize alias holder
        self.fournisseur_alias = ''
        
        self.selected_fournisseur = None
        def on_fournisseur_select(fournisseur_data):
            self.selected_fournisseur = fournisseur_data
            # Also update the fournisseur_var for compatibility with validation
            self.fournisseur_var.set(fournisseur_data.get('nom_fournisseur', ''))
            print(f"[ACHAT] Selected fournisseur: {fournisseur_data.get('nom_fournisseur', '')} via smart selector")
            # If the selected supplier is the generic 401000, prompt for alias
            try:
                code = fournisseur_data.get('code_fournisseur') or ''
                name = fournisseur_data.get('nom_fournisseur') or ''
                if str(code).strip() == '401000':
                    alias = simpledialog.askstring(
                        "Fournisseur Divers",
                        "Entrez le nom réel du fournisseur (sera affiché partout):",
                        parent=self.window
                    )
                    if alias:
                        # Store on the dialog instance for saving
                        self.fournisseur_alias = alias.strip()
                        # Also show it to the user next to base name
                        self.fournisseur_var.set(f"{name} — {self.fournisseur_alias}")
                        print(f"[ACHAT] Set fournisseur alias: {self.fournisseur_alias}")
                    else:
                        # Clear alias if user cancels/empty
                        self.fournisseur_alias = ''
            except Exception as e:
                print(f"[ACHAT] Alias prompt error: {e}")

        # Create advanced search fournisseur selector
        try:
            self.fournisseur_selector = fournisseur_selector.create_selector(fournisseur_frame, on_select=on_fournisseur_select)
            print("[ACHAT] ✓ Advanced fournisseur selector created with callback")
            
            # Dummy refresh function for compatibility
            def dummy_refresh():
                print("[ACHAT] Fournisseur refresh requested (handled by selector)")
            self._refresh_fournisseurs = dummy_refresh
            
        except Exception as e:
            print(f"[ACHAT] ❌ Error creating selector: {e}")
            # Fallback to old combo system
            self.fournisseur_combo, self._refresh_fournisseurs = self._create_auto_refresh_fournisseur_combo(fournisseur_frame)
            
            # Add fournisseur management button (only for fallback combo)
            button_frame = tk.Frame(fournisseur_frame)
            button_frame.pack(fill="x", pady=5)
            
            ttk.Button(
                button_frame,
                text="📋 Gérer Fournisseurs",
                command=self._open_fournisseur_manager
            ).pack(side="left", padx=5)
            
            ttk.Button(
                button_frame,
                text="🔄 Actualiser",
                command=self._refresh_fournisseurs
            ).pack(side="left", padx=5)
            
        # Numéro Facture
        tk.Label(self.window, text="Numéro Facture:").pack(pady=2)
        self.num_facture_var = tk.StringVar()
        tk.Entry(self.window, textvariable=self.num_facture_var, width=20).pack(pady=2)
        # Date
        tk.Label(self.window, text="Date (JJ/MM/AAAA):").pack(pady=2)
        self.date_var = tk.StringVar(value=date.today().strftime("%d/%m/%Y"))
        self.date_entry = DateEntry(self.window, textvariable=self.date_var, date_pattern="dd/MM/yyyy", width=15)
        self.date_entry.pack(pady=2)
        # Montant HT
        tk.Label(self.window, text="Montant HT:").pack(pady=2)
        self.mt_ht_var = tk.StringVar()
        tk.Entry(self.window, textvariable=self.mt_ht_var, width=15).pack(pady=1)
        # Timbre
        tk.Label(self.window, text="Timbre:").pack(pady=2)
        self.timbre_var = tk.StringVar()
        tk.Entry(self.window, textvariable=self.timbre_var, width=15).pack(pady=1)
        # Taxes
        tax_bar = tk.Frame(self.window)
        tax_bar.pack(pady=2)
        tk.Label(tax_bar, text="Taxes:").pack(side="left")
        tk.Label(tax_bar, text="(Gérer les taxes dans Paramètres)", font=("Arial", 8), fg="gray").pack(side="left", padx=8)
        self.taxes_frame = tk.Frame(self.window)
        self.taxes_frame.pack(pady=2)
        self.taxes_vars = []  # List of (tax_id_var, value_var, row_frame)
        self._add_tax_row("TVA DEDUCTIBLE", "0", is_default=True)
        tk.Button(self.window, text="+ Ajouter une taxe", command=self._add_tax_row).pack(pady=1)
        # Total TTC
        tk.Label(self.window, text="Total TTC:").pack(pady=2)
        self.ttc_var = tk.StringVar()
        tk.Entry(self.window, textvariable=self.ttc_var, width=15).pack(pady=1)
        # Notes (more compact)
        tk.Label(self.window, text="Notes:").pack(pady=2)
        self.notes_text = tk.Text(self.window, height=2, width=40)
        self.notes_text.pack(pady=1)
        # Buttons (compact spacing)
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(pady=8)
        tk.Button(btn_frame, text="Enregistrer", bg="#28a745", fg="white", command=self._save).pack(side="left", padx=8)
        tk.Button(btn_frame, text="Annuler", command=self.window.destroy).pack(side="left", padx=8)

    def _add_tax_row(self, name_val="", value_val="", is_default=False):
        row = tk.Frame(self.taxes_frame)
        if is_default:
            tk.Label(row, text="TVA DEDUCTIBLE", width=18).pack(side="left", padx=2)
            value_var = tk.StringVar(value=value_val)
            tk.Entry(row, textvariable=value_var, width=10).pack(side="left", padx=2)
            del_btn = tk.Label(row, text="(défaut)")
            del_btn.pack(side="left", padx=2)
            row.pack(pady=1)
            self.taxes_vars.append((None, value_var, row))
        else:
            # Get taxes from purchase service or use common tax names
            if self.purchase_service and hasattr(self.purchase_service, 'get_available_taxes'):
                taxes = self.purchase_service.get_available_taxes()
            else:
                # Fallback to common tax types
                taxes = [
                    {'name': 'TVA 7%'},
                    {'name': 'FODEC'},
                    {'name': 'Transport'},
                    {'name': 'Timbre'}
                ]
            tax_names = [t['name'] for t in taxes]
            tax_id_var = tk.StringVar()
            tax_combo = ttk.Combobox(row, textvariable=tax_id_var, values=tax_names, state="readonly", width=18)
            tax_combo.pack(side="left", padx=2)
            value_var = tk.StringVar(value=value_val)
            tk.Entry(row, textvariable=value_var, width=10).pack(side="left", padx=2)
            del_btn = tk.Button(row, text="Supprimer", command=lambda: self._remove_tax_row(row, tax_id_var))
            del_btn.pack(side="left", padx=2)
            row.pack(pady=1)
            self.taxes_vars.append((tax_id_var, value_var, row))

    def _remove_tax_row(self, row, tax_id_var):
        # Prevent removing TVA 19% default
        if tax_id_var is None:
            messagebox.showwarning("Action interdite", "TVA 19% ne peut pas être supprimée.")
            return
        for i, (n, _, r) in enumerate(self.taxes_vars):
            if r == row:
                r.destroy()
                self.taxes_vars.pop(i)
                break

    def _load_data(self):
        if not self.preset:
            return
        # Set fournisseur in combo
        fournisseur_name = self.preset.get('fournisseur', '')
        # Load existing alias if present
        self.fournisseur_alias = self.preset.get('fournisseur_alias', '')
        if fournisseur_name:
            display_name = fournisseur_name
            if self.fournisseur_alias:
                display_name = f"{fournisseur_name} — {self.fournisseur_alias}"
            self.fournisseur_var.set(display_name)
            # ✅ FIXED: Disable legacy fournisseur lookup to prevent crashes
            # Try to find the fournisseur in the database to set selected_fournisseur
            # from stfoom.logicold import fournisseur_selector as fs  # DISABLED
            # fournisseurs_df = fs.load_fournisseurs()  # DISABLED
            # matching = fournisseurs_df[fournisseurs_df['nom_fournisseur'] == fournisseur_name]  # DISABLED
            # if not matching.empty:
            #     self.selected_fournisseur = matching.iloc[0].to_dict()  # DISABLED
            self.selected_fournisseur = {'nom_fournisseur': fournisseur_name}  # Simple fallback
        self.num_facture_var.set(self.preset.get('num_facture', ''))
        self.date_var.set(self.preset.get('date', ''))
        self.mt_ht_var.set(str(self.preset.get('mt_ht', '')))
        self.timbre_var.set(str(self.preset.get('timbre', '')))
        self.ttc_var.set(str(self.preset.get('ttc', '')))
        self.notes_text.delete("1.0", tk.END)
        self.notes_text.insert("1.0", self.preset.get('notes', ''))
        # Remove all but TVA 19% default
        for _, _, r in self.taxes_vars[1:]:
            r.destroy()
        self.taxes_vars = self.taxes_vars[:1]
        # Find TVA 19% in taxes, set its value, and add all other taxes
        taxes = self.preset.get('taxes', [])
        tva19 = next((t for t in taxes if t.get('name', '').lower() == 'tva 19%'), None)
        tva_value = tva19.get('value', 0) if tva19 else 0
        self.taxes_vars[0][1].set(str(tva_value))
        for t in taxes:
            if t.get('name', '').lower() != 'tva 19%':
                self._add_tax_row(t.get('name', ''), str(t.get('value', '')))

    def _save(self):
        try:
            # Get fournisseur name from selected fournisseur or fallback to text entry
            fournisseur_name = ""
            if self.selected_fournisseur:
                fournisseur_name = self.selected_fournisseur.get('nom_fournisseur', '')
            else:
                fournisseur_name = self.fournisseur_var.get().strip()
            
            print(f"[ACHAT] Saving with fournisseur: '{fournisseur_name}' (from {'selected' if self.selected_fournisseur else 'fallback'})")
            
            # Always save TVA 19% as first tax, then all others
            taxes = []
            tva_value = float(self.taxes_vars[0][1].get().replace(",", ".")) if self.taxes_vars[0][1].get().strip() else 0
            taxes.append({'name': 'TVA 19%', 'value': tva_value})
            for n, v, _ in self.taxes_vars[1:]:
                if n and n.get():
                    value = float(v.get().replace(",", ".")) if v.get().strip() else 0
                    taxes.append({'name': n.get(), 'value': value})
            data = {
                'fournisseur': fournisseur_name,
                'fournisseur_alias': getattr(self, 'fournisseur_alias', '').strip() if hasattr(self, 'fournisseur_alias') else '',
                'num_facture': self.num_facture_var.get().strip(),
                'date': self.date_var.get().strip(),
                'mt_ht': float(self.mt_ht_var.get().replace(",", ".")) if self.mt_ht_var.get().strip() else 0,
                'timbre': float(self.timbre_var.get().replace(",", ".")) if self.timbre_var.get().strip() else 0,
                'ttc': float(self.ttc_var.get().replace(",", ".")) if self.ttc_var.get().strip() else 0,
                'notes': self.notes_text.get("1.0", "end").strip(),
                'paiement_statut': '',
                'paiement_methode': '',
                'taxes': taxes
            }
            if not data['fournisseur']:
                raise ValueError("Fournisseur obligatoire.")
            if not data['date']:
                raise ValueError("Date obligatoire.")
            
            # 🎯 Phase 2C: Use PurchaseService if available, fallback to achat module
            if self.purchase_service:
                # Modern approach: Use dependency injection
                if self.preset:
                    success = self.purchase_service.update_purchase(self.preset['id'], data)
                else:
                    success = self.purchase_service.create_purchase(data)
                
                if not success:
                    raise ValueError("Erreur lors de l'enregistrement de l'achat")
            else:
                # Legacy approach: Direct module access
                if self.preset:
                    self.purchase_service.update_purchase(self.preset["id"], data) if self.purchase_service else False
                else:
                    self.purchase_service.create_purchase(data) if self.purchase_service else False
            
            messagebox.showinfo("Succès", "Achat enregistré.")
            self.result = True
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def _create_auto_refresh_fournisseur_combo(self, parent):
        """Create fournisseur combobox with auto-refresh functionality"""
        # Create the combobox with proper textvariable
        combo = ttk.Combobox(parent, textvariable=self.fournisseur_var, state="readonly")
        combo.pack(fill="x", padx=5, pady=5)
        
        # Store fournisseur data for selection
        self.fournisseur_data = []
        
        def refresh_fournisseurs():
            """Refresh fournisseur list"""
            try:
                current_selection = combo.get()
                
                # Try to get fournisseur data from PurchaseService
                if hasattr(self, 'purchase_service') and self.purchase_service:
                    try:
                        fournisseurs = self.purchase_service.get_all_suppliers()
                        print(f"[ACHAT] Loaded {len(fournisseurs) if fournisseurs else 0} suppliers from service")
                        
                        # If we got data from service, use it
                        if fournisseurs:
                            self.fournisseur_data = fournisseurs
                            fournisseur_names = [f.get('nom_fournisseur', 'Inconnu') for f in fournisseurs]
                        else:
                            # Service returned empty list, use fallback
                            print("[ACHAT] Service returned empty list, using fallback data")
                            self.fournisseur_data = [
                                {"nom_fournisseur": "SOTACIB", "id": 1, "code_fournisseur": "411001"},
                                {"nom_fournisseur": "CARTHAGE CEMENT", "id": 2, "code_fournisseur": "411002"},
                                {"nom_fournisseur": "Les Ciments de Bizerte", "id": 3, "code_fournisseur": "411003"},
                                {"nom_fournisseur": "CIOK", "id": 4, "code_fournisseur": "411004"}
                            ]
                            fournisseur_names = [f.get('nom_fournisseur', 'Inconnu') for f in self.fournisseur_data]
                            
                    except Exception as service_error:
                        print(f"[ACHAT] Service error: {service_error}")
                        # Fallback data if service fails
                        self.fournisseur_data = [
                            {"nom_fournisseur": "SOTACIB", "id": 1, "code_fournisseur": "411001"},
                            {"nom_fournisseur": "CARTHAGE CEMENT", "id": 2, "code_fournisseur": "411002"},
                            {"nom_fournisseur": "Les Ciments de Bizerte", "id": 3, "code_fournisseur": "411003"},
                            {"nom_fournisseur": "CIOK", "id": 4, "code_fournisseur": "411004"}
                        ]
                        fournisseur_names = [f.get('nom_fournisseur', 'Inconnu') for f in self.fournisseur_data]
                else:
                    # No service available, use fallback
                    print("[ACHAT] No purchase service available, using fallback data")
                    self.fournisseur_data = [
                        {"nom_fournisseur": "SOTACIB", "id": 1, "code_fournisseur": "411001"},
                        {"nom_fournisseur": "CARTHAGE CEMENT", "id": 2, "code_fournisseur": "411002"},
                        {"nom_fournisseur": "Les Ciments de Bizerte", "id": 3, "code_fournisseur": "411003"},
                        {"nom_fournisseur": "CIOK", "id": 4, "code_fournisseur": "411004"}
                    ]
                    fournisseur_names = [f.get('nom_fournisseur', 'Inconnu') for f in self.fournisseur_data]
                
                # Update combo values
                combo['values'] = fournisseur_names
                
                # Maintain selection if it still exists
                if current_selection and current_selection in fournisseur_names:
                    combo.set(current_selection)
                    # Update selected_fournisseur
                    for fournisseur in self.fournisseur_data:
                        if fournisseur.get('nom_fournisseur', '') == current_selection:
                            self.selected_fournisseur = fournisseur
                            break
                else:
                    combo.set("")
                    self.selected_fournisseur = None
                    
                print(f"[ACHAT] Refreshed fournisseur list: {len(fournisseur_names)} fournisseurs")
                
            except Exception as e:
                print(f"[ACHAT] Error refreshing fournisseurs: {e}")
                combo['values'] = ["Erreur de chargement"]
                self.fournisseur_data = []
        
        def on_fournisseur_selected(event=None):
            """Handle fournisseur selection"""
            try:
                selected_name = combo.get()
                # Find the corresponding fournisseur data
                for fournisseur in self.fournisseur_data:
                    if fournisseur.get('nom_fournisseur', '') == selected_name:
                        self.selected_fournisseur = fournisseur
                        print(f"[ACHAT] Selected fournisseur: {selected_name} (ID: {fournisseur.get('id', 'N/A')})")
                        # Alias prompt for 401000 in fallback path
                        code = fournisseur.get('code_fournisseur') or ''
                        if str(code).strip() == '401000':
                            alias = simpledialog.askstring(
                                "Fournisseur Divers",
                                "Entrez le nom réel du fournisseur (sera affiché partout):",
                                parent=self.window
                            )
                            self.fournisseur_alias = (alias or '').strip()
                            if self.fournisseur_alias:
                                combo.set(f"{selected_name} — {self.fournisseur_alias}")
                        break
                else:
                    self.selected_fournisseur = None
            except Exception as e:
                print(f"[ACHAT] Error selecting fournisseur: {e}")
                self.selected_fournisseur = None
        
        # Bind selection event
        combo.bind("<<ComboboxSelected>>", on_fournisseur_selected)
        
        # Initial load
        refresh_fournisseurs()
        
        # Register callback for future refreshes
        if not hasattr(self, '_fournisseur_refresh_callbacks'):
            self._fournisseur_refresh_callbacks = []
        self._fournisseur_refresh_callbacks.append(refresh_fournisseurs)
        
        return combo, refresh_fournisseurs
    
    def _open_fournisseur_manager(self):
        """Open fournisseur management dialog."""
        try:
            from stfoom.ui.fournisseur_selector import _manager_dialog
            # Use self.window since AchatDialog has a window attribute, not winfo_toplevel()
            parent_window = self.window if hasattr(self, 'window') else self.parent
            _manager_dialog(parent_window, self._refresh_all_fournisseurs)
        except Exception as e:
            print(f"[ACHAT] Error opening fournisseur manager: {e}")
            from tkinter import messagebox
            messagebox.showerror(
                "Erreur", 
                f"Impossible d'ouvrir la gestion des fournisseurs: {e}"
            )
    
    def _refresh_all_fournisseurs(self):
        """Refresh all fournisseur components"""
        for callback in self._fournisseur_refresh_callbacks:
            try:
                callback()
            except Exception as e:
                print(f"[ACHAT] Error in refresh callback: {e}")

# The following PaymentDialog is a copy of Vente's, adapted for Achat (outgoing payments)
class AchatPaymentDialog:
    def __init__(self, parent, achat_id, achat):
        self.parent = parent
        self.achat_id = achat_id
        self.achat = achat
        self.result = None
        
        # ✅ Get payment_service from parent (like vente does)
        self.payment_service = getattr(parent, 'payment_service', None)
        self.bank_service = getattr(parent, 'bank_service', None)
        
        self.paiements = self.payment_service.get_invoice_payments(achat_id, is_achat=True) if self.payment_service else []
        self.montant_total = achat.get('ttc', 0)
        self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
        self.window = tk.Toplevel(parent)
        self.window.title(f"Paiements - Achat {achat_id}")
        self.window.geometry("650x700")
        self.window.grab_set()
        self.window.resizable(False, False)
        self._create_ui()
        self.window.transient(parent)
        self.window.grab_set()
        parent.wait_window(self.window)
    def _create_ui(self):
        info_frame = tk.LabelFrame(self.window, text="Informations Achat")
        info_frame.pack(fill="x", padx=10, pady=10)
        tk.Label(info_frame, text=f"Achat: {self.achat_id}").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Fournisseur: {self.achat.get('fournisseur', '')}").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Montant Total: {format_money(self.montant_total)}").pack(anchor="w", padx=5, pady=2)
        pay_frame = tk.LabelFrame(self.window, text="Paiements enregistrés")
        pay_frame.pack(fill="x", padx=10, pady=10)
        columns = ("montant", "type", "banque", "methode", "date", "echeance", "reference", "notes", "actions")
        self.tree = ttk.Treeview(pay_frame, columns=columns, show="headings", height=5)
        for col, label in zip(columns, ["Montant", "Type", "Banque", "Méthode", "Date", "Échéance", "Référence", "Notes", "Actions"]):
            self.tree.heading(col, text=label)
            self.tree.column(col, anchor="center", width=90)
        self.tree.column("notes", width=120)
        self.tree.column("actions", width=80)
        self.tree.pack(fill="x", padx=5, pady=5)
        self._refresh_tree()
        btns = tk.Frame(pay_frame)
        btns.pack(pady=4)
        tk.Button(btns, text="Ajouter un paiement", command=self._add_payment, bg="#007bff", fg="white").pack(side="left", padx=4)
        tk.Button(btns, text="Fermer", command=self._cancel).pack(side="left", padx=4)
        self.delete_btn = tk.Button(btns, text="Supprimer le paiement", command=self._delete_selected_payment, bg="#dc3545", fg="white", state="disabled")
        self.delete_btn.pack(side="left", padx=4)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        reste_frame = tk.Frame(self.window)
        reste_frame.pack(fill="x", padx=10, pady=6)
        tk.Label(reste_frame, text="Reste à payer (modifiable):").pack(side="left")
        self.reste_var = tk.StringVar(value=f"{self.reste:.3f}")
        self.reste_entry = tk.Entry(reste_frame, textvariable=self.reste_var, width=10)
        self.reste_entry.pack(side="left", padx=5)
        
        # ✅ MULTIPLE PAYMENT HISTORY SECTION - Same as vente_page.py
        self._create_multiple_payment_history_section()

    def _create_multiple_payment_history_section(self):
        """Create the multiple payment history section for this invoice"""
        try:
            history = self._get_multiple_payment_history()
            if history:
                # Create collapsible history frame
                history_frame = tk.LabelFrame(self.window, text=f"📋 Historique Paiements Multiples ({len(history)} trouvés)")
                history_frame.pack(fill="x", padx=10, pady=5)
                
                # Create scrollable frame for history
                canvas = tk.Canvas(history_frame, height=120)
                scrollbar = ttk.Scrollbar(history_frame, orient="vertical", command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Add history entries
                for i, payment in enumerate(history):
                    self._create_history_entry(scrollable_frame, payment, i)
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
        except Exception as e:
            print(f"[ACHAT_PAYMENT] Error creating multiple payment history: {e}")

    def _get_multiple_payment_history(self):
        """Get multiple payment history for this achat invoice"""
        try:
            # Use parent's service if available
            if hasattr(self.parent, 'payment_service') and self.parent.payment_service:
                payment_service = self.parent.payment_service
            else:
                return []
            
            # Get connection from payment service
            with payment_service.payment_repository.get_connection() as conn:
                cursor = conn.cursor()
                
                # Find all multiple payments that include this achat
                cursor.execute("""
                    SELECT DISTINCT 
                        p1.reference_paiement as check_number,
                        p1.date_paiement,
                        p1.methode_paiement,
                        GROUP_CONCAT(DISTINCT p2.nfacture) as all_invoices,
                        SUM(p2.montant_paye) as total_amount,
                        MAX(p1.notes) as notes
                    FROM paiements_factures p1
                    JOIN paiements_factures p2 ON p1.reference_paiement = p2.reference_paiement 
                    WHERE p1.notes LIKE '%MULTI-PAIEMENT%' 
                    AND p1.reference_paiement IN (
                        SELECT reference_paiement 
                        FROM paiements_factures 
                        WHERE nfacture = ? AND is_achat = 1
                        AND notes LIKE '%MULTI-PAIEMENT%'
                    )
                    AND p2.is_achat = 1
                    GROUP BY p1.reference_paiement, p1.date_paiement, p1.methode_paiement
                    ORDER BY p1.date_paiement DESC
                """, (self.achat_id,))
                
                results = cursor.fetchall()
                
                history = []
                for row in results:
                    check_number, date_paiement, methode, invoices_str, total_amount, notes = row
                    history.append({
                        'check_number': check_number,
                        'date': date_paiement,
                        'method': methode,
                        'invoices': invoices_str.split(',') if invoices_str else [],
                        'total_amount': total_amount,
                        'notes': notes
                    })
                
                return history
        except Exception as e:
            print(f"[ACHAT_PAYMENT] Error getting multiple payment history: {e}")
            return []

    def _create_history_entry(self, parent, payment, index):
        """Create a single history entry"""
        # Main entry frame
        entry_frame = tk.Frame(parent, relief="groove", bd=1)
        entry_frame.pack(fill="x", padx=5, pady=2)
        
        # Header with summary
        header_frame = tk.Frame(entry_frame)
        header_frame.pack(fill="x", padx=5, pady=2)
        
        # Payment method and check number
        method_text = f"💳 {payment['method'].title()}"
        if payment['check_number']:
            method_text += f" - Chèque: {payment['check_number']}"
        
        tk.Label(header_frame, text=method_text, font=("Arial", 9, "bold")).pack(side="left")
        tk.Label(header_frame, text=f"📅 {payment['date']}", font=("Arial", 9)).pack(side="right")
        
        # Details frame
        details_frame = tk.Frame(entry_frame)
        details_frame.pack(fill="x", padx=5, pady=2)
        
        # Invoices list
        invoices_text = f"🧾 Achats: {', '.join(payment['invoices'])}"
        tk.Label(details_frame, text=invoices_text, font=("Arial", 8)).pack(side="left")
        
        # Total amount
        total_text = f"💰 Total: {format_money(payment['total_amount'])}"
        tk.Label(details_frame, text=total_text, font=("Arial", 8, "bold"), fg="green").pack(side="right")
        
        # Action button
        action_frame = tk.Frame(entry_frame)
        action_frame.pack(fill="x", padx=5, pady=2)
        
        tk.Button(action_frame, text="🔍 Voir Détails", 
                 command=lambda: self._show_multiple_payment_details(payment),
                 font=("Arial", 7), bg="#f0f8ff").pack(side="right")

    def _show_multiple_payment_details(self, payment):
        """Show detailed information about the multiple payment"""
        details_window = tk.Toplevel(self.window)
        details_window.title(f"Détails Paiement Multiple - {payment['check_number']}")
        details_window.geometry("500x400")
        details_window.transient(self.window)
        details_window.grab_set()
        
        # Header
        header_frame = tk.Frame(details_window)
        header_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(header_frame, text="💳 Détails du Paiement Multiple", 
                font=("Arial", 14, "bold")).pack()
        
        # Summary
        summary_frame = tk.LabelFrame(details_window, text="Résumé")
        summary_frame.pack(fill="x", padx=10, pady=5)
        
        tk.Label(summary_frame, text=f"Méthode: {payment['method'].title()}", 
                font=("Arial", 10)).pack(anchor="w", padx=5, pady=2)
        
        if payment['check_number']:
            tk.Label(summary_frame, text=f"N° Chèque: {payment['check_number']}", 
                    font=("Arial", 10)).pack(anchor="w", padx=5, pady=2)
        
        tk.Label(summary_frame, text=f"Date: {payment['date']}", 
                font=("Arial", 10)).pack(anchor="w", padx=5, pady=2)
        
        tk.Label(summary_frame, text=f"Montant Total: {format_money(payment['total_amount'])}", 
                font=("Arial", 10, "bold")).pack(anchor="w", padx=5, pady=2)
        
        # Invoices list
        invoices_frame = tk.LabelFrame(details_window, text="Achats Inclus")
        invoices_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        # Create treeview for invoices
        columns = ("achat", "amount")
        tree = ttk.Treeview(invoices_frame, columns=columns, show="headings", height=8)
        
        tree.heading("achat", text="N° Achat")
        tree.heading("amount", text="Montant Payé")
        
        tree.column("achat", width=150, anchor="center")
        tree.column("amount", width=150, anchor="center")
        
        # Add invoices to tree (simplified - you may want to get actual amounts)
        for invoice in payment['invoices']:
            tree.insert("", "end", values=(invoice, "---"))
        
        tree.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Close button
        tk.Button(details_window, text="Fermer", 
                 command=details_window.destroy).pack(pady=10)
    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.paiements:
            banque_nom = ""
            if p['methode_paiement'] == 'banque' and p.get('banque_id'):
                # Use instance bank_service only (no global fallback)
                if hasattr(self, 'bank_service') and self.bank_service:
                    banques = self.bank_service.get_all_banks()
                else:
                    banques = []  # No fallback to removed global wrapper
                for b in banques:
                    if b['id'] == p['banque_id']:
                        # Handle both 'nom' and 'nom_banque' field names
                        banque_nom = b.get('nom_banque', b.get('nom', 'Unknown Bank'))
                        break
            # Check if this is a multiple payment for better display
            notes_display = p.get('notes', '')
            method_display = f"{p['methode_paiement'] or 'N/A'}"
            
            # Add visual indicator for multiple payments
            if notes_display and 'MULTI-' in notes_display:
                method_display = f"🔗 {method_display} (Multiple)"
            
            self.tree.insert("", "end", iid=p['id'], values=(
                f"{p['montant_paye']:.3f}",
                "Banque" if p['methode_paiement'] == 'banque' else "Caisse",
                banque_nom,
                method_display,
                p['date_paiement'],
                p.get('echeance', ''),
                p.get('reference_paiement', ''),
                notes_display,
                "Modifier | Supprimer"
            ))
        self.tree.bind("<Double-1>", self._on_tree_action)
    def _on_tree_action(self, event):
        item = self.tree.identify_row(event.y)
        col = self.tree.identify_column(event.x)
        if not item:
            return
        # Allow context menu on any column, not just Actions column
        menu = tk.Menu(self.window, tearoff=0)
        menu.add_command(label="Modifier", command=lambda: self._edit_payment(item))
        menu.add_command(label="Supprimer", command=lambda: self._delete_payment(item))
        menu.tk_popup(event.x_root, event.y_root)
    def _add_payment(self):
        # Check permission first
        if not check_ui_permission("payments", "create"):
            return
        self._payment_form()
    def _edit_payment(self, item_id):
        paiement = next((p for p in self.paiements if str(p['id']) == str(item_id)), None)
        if paiement:
            self._payment_form(paiement)
    def _delete_payment(self, item_id):
        # Check permission first
        if not check_ui_permission("payments", "delete"):
            return
            
        # Get payment details to check if it's part of multiple payment
        payment_details = None
        for p in self.paiements:
            if p['id'] == int(item_id):
                payment_details = p
                break
        
        # Check if this is a multiple payment
        is_multiple = payment_details and payment_details.get('notes', '') and 'MULTI-' in payment_details.get('notes', '')
        
        if is_multiple:
            # Enhanced confirmation for multiple payments
            confirm_msg = ("⚠️ ATTENTION: Paiement Multiple Détecté\n\n"
                         f"Ce paiement fait partie d'un paiement multiple.\n"
                         f"Supprimer ce paiement supprimera TOUS les paiements\n"
                         f"associés de cette transaction multiple.\n\n"
                         f"Êtes-vous sûr de vouloir continuer?")
            if not messagebox.askyesno("Confirmer - Paiement Multiple", confirm_msg):
                return
        else:
            # Standard confirmation
            if not messagebox.askyesno("Confirmer", "Supprimer ce paiement ?"):
                return
                
        try:
            self.payment_service.delete_payment(int(item_id), is_achat=True) if hasattr(self, 'payment_service') and self.payment_service else None
            self.paiements = self.payment_service.get_invoice_payments(self.achat_id, is_achat=True) if hasattr(self, 'payment_service') and self.payment_service else []
            self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
            self.reste_var.set(f"{self.reste:.3f}")
            self._refresh_tree()
            self.result = True
            
            # Show success message
            if is_multiple:
                messagebox.showinfo("Succès", "Paiement multiple supprimé avec succès!\nTous les paiements associés ont été supprimés.")
            else:
                messagebox.showinfo("Succès", "Paiement supprimé avec succès!")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
            print(f"[ACHAT_PAGE] Error deleting payment {item_id}: {e}")
    def _payment_form(self, preset=None):
        form = tk.Toplevel(self.window)
        form.title("Ajouter un paiement" if not preset else "Modifier le paiement")
        form.geometry("650x750")  # 🔧 Increased height and width like vente
        form.resizable(True, True)  # 🔧 Make resizable like vente
        form.grab_set()
        type_var = tk.StringVar(value=preset['methode_paiement'] if preset else "banque")
        tk.Label(form, text="Type de paiement:").pack(anchor="w", padx=10, pady=4)
        tk.Radiobutton(form, text="🏦 Banque", variable=type_var, value="banque", command=lambda: update_fields()).pack(anchor="w", padx=20)
        tk.Radiobutton(form, text="💰 Caisse", variable=type_var, value="caisse", command=lambda: update_fields()).pack(anchor="w", padx=20)
        bank_options_frame = tk.Frame(form)
        bank_options_frame.pack(anchor="w", fill="x", padx=10, pady=2)
        bank_var = tk.StringVar()
        method_var = tk.StringVar()
        # ✅ UNIFIED: Use bank_service only (no fallback to removed wrapper)
        banques = []
        if self.bank_service:
            banques = self.bank_service.get_all_banks()
        else:
            print("[ACHAT_PAYMENT] Warning: No bank_service available")
            banques = []
        banks_dict = {}
        for b in banques:
            # Handle both 'nom' and 'nom_banque' field names
            bank_name = b.get('nom_banque', b.get('nom', 'Unknown Bank'))
            # Handle missing 'numero_compte' field
            if 'numero_compte' in b and b['numero_compte']:
                display_name = f"{bank_name} ({b['numero_compte']})"
            else:
                display_name = bank_name
            banks_dict[display_name] = b['id']
        bank_combo = ttk.Combobox(bank_options_frame, textvariable=bank_var, state="readonly", width=35, values=list(banks_dict.keys()))
        
        # ✅ UNIFIED: Get payment methods from bank_service (like vente)  
        payment_methods = self.bank_service.get_payment_methods() if self.bank_service else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
        method_combo = ttk.Combobox(bank_options_frame, textvariable=method_var, state="readonly", width=30, values=[label for _, label in payment_methods])
        echeance_var = tk.StringVar(value="")
        echeance_label = tk.Label(bank_options_frame, text="Échéance (JJ/MM/AAAA, pour traite):")
        echeance_frame = tk.Frame(bank_options_frame)
        echeance_entry = tk.Entry(echeance_frame, textvariable=echeance_var, width=15)
        echeance_entry.pack(side="left")
        def pick_echeance():
            top = tk.Toplevel(form)
            top.title("Sélectionner une échéance")
            cal_widget = Calendar(top, date_pattern="dd/mm/yyyy")
            cal_widget.pack(padx=10, pady=10)
            def set_date():
                echeance_entry.delete(0, "end")
                echeance_entry.insert(0, cal_widget.get_date())
                top.destroy()
            tk.Button(top, text="OK", command=set_date).pack(pady=5)
        tk.Button(echeance_frame, text="📅", command=pick_echeance).pack(side="left", padx=4)
        numero_label = tk.Label(bank_options_frame, text="Numéro:")
        numero_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        numero_entry = tk.Entry(bank_options_frame, textvariable=numero_var, width=25)
        def update_fields():
            for widget in bank_options_frame.winfo_children():
                widget.pack_forget()
            if type_var.get() == "banque":
                bank_combo.pack(anchor="w", padx=0, pady=2)
                method_combo.pack(anchor="w", padx=0, pady=2)
                numero_label.pack(anchor="w", padx=0, pady=2)
                numero_entry.pack(anchor="w", padx=0, pady=2)
                # ✅ UNIFIED: Use bank_service payment methods (not global wrapper)
                method_idx = None
                payment_methods = self.bank_service.get_payment_methods() if self.bank_service else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                try:
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                except ValueError:
                    method_idx = None
                except Exception:
                    pass
                method_key = payment_methods[method_idx][0] if method_idx is not None else None
                if method_key == "traite":
                    echeance_label.pack(anchor="w", padx=0, pady=2)
                    echeance_frame.pack(anchor="w", padx=0, pady=2)
        method_combo.bind("<<ComboboxSelected>>", lambda e: update_fields())
        update_fields()
        tk.Label(form, text="Montant payé (TND):").pack(anchor="w", padx=10, pady=4)
        amount_var = tk.StringVar(value=f"{preset['montant_paye']:.3f}" if preset else f"{self.reste:.3f}")
        amount_entry = tk.Entry(form, textvariable=amount_var, width=15)
        amount_entry.pack(padx=10, pady=2)
        tk.Label(form, text="Date de paiement (JJ/MM/AAAA):").pack(anchor="w", padx=10, pady=4)
        date_frame = tk.Frame(form)
        date_frame.pack(padx=10, pady=2, anchor="w")
        date_var = tk.StringVar(value=datetime.now().strftime("%d/%m/%Y"))
        date_entry = tk.Entry(date_frame, textvariable=date_var, width=15)
        date_entry.pack(side="left")
        def pick_date():
            top = tk.Toplevel(form)
            top.title("Sélectionner une date")
            cal_widget = Calendar(top, date_pattern="dd/mm/yyyy")
            cal_widget.pack(padx=10, pady=10)
            def set_date():
                date_entry.delete(0, "end")
                date_entry.insert(0, cal_widget.get_date())
                top.destroy()
            tk.Button(top, text="OK", command=set_date).pack(pady=5)
        tk.Button(date_frame, text="📅", command=pick_date).pack(side="left", padx=4)
        tk.Label(form, text="Référence (optionnel):").pack(anchor="w", padx=10, pady=4)
        ref_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        ref_entry = tk.Entry(form, textvariable=ref_var, width=25)
        ref_entry.pack(padx=10, pady=2)
        tk.Label(form, text="Notes (optionnel):").pack(anchor="w", padx=10, pady=4)
        notes_text = tk.Text(form, height=3, width=35)
        if preset:
            notes_text.insert("1.0", preset.get('notes', ''))
        notes_text.pack(padx=10, pady=2)
        
        # 🔧 COMPLETE Retenu section - IDENTICAL to vente_page.py
        retenu_frame = tk.Frame(form)
        retenu_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        
        tk.Label(form, text="Retenu (%):").pack(anchor="w", padx=10, pady=4)
        retenu_var = tk.StringVar(value="0")
        retenu_entry = tk.Entry(retenu_frame, textvariable=retenu_var, width=10)
        retenu_entry.pack(side="left", padx=(0, 10))
        
        # 🔧 EDITABLE retenu amount (user can modify) - LIKE VENTE
        tk.Label(retenu_frame, text="Montant retenu:").pack(side="left", padx=(10, 5))
        retenu_amount_var = tk.StringVar(value="0.000")
        retenu_amount_entry = tk.Entry(retenu_frame, textvariable=retenu_amount_var, 
                                      width=12, bg="white")  # 🔧 WHITE = EDITABLE
        retenu_amount_entry.pack(side="left")
        
        # Add "TND" label
        tk.Label(retenu_frame, text="TND").pack(side="left", padx=(2, 0))
        
        # 🔧 COMPLETE Auto-calculation functions - IDENTICAL to vente
        def calculate_retenu_from_percent(*args):
            """Calculate retenu amount from percentage - IDENTICAL TO VENTE"""
            try:
                # ✅ IDENTICAL TO VENTE: Get the base amount (TTC - timbre for retenu calculation)
                ttc_amount = self.montant_total
                timbre_amount = self.achat.get('timbre', 1.0) if hasattr(self, 'achat') else 1.0
                
                # ✅ IDENTICAL TO VENTE: Calculate retenu base excluding timbre
                retenu_base = max(0, ttc_amount - timbre_amount)
                
                # ✅ IDENTICAL TO VENTE: Use remaining amount for actual payment calculation
                remaining_amount = self.reste  # THIS IS THE KEY FIX!
                
                # Get retenu percentage
                retenu_text = retenu_var.get().strip()
                if not retenu_text:
                    retenu_percent = 0.0
                else:
                    try:
                        retenu_percent = float(retenu_text.replace(",", "."))
                        if retenu_percent < 0:
                            retenu_percent = 0.0
                        elif retenu_percent > 100:
                            retenu_percent = 100.0
                    except ValueError:
                        retenu_percent = 0.0
                
                # ✅ IDENTICAL TO VENTE: Calculate retenu on timbre-excluded base
                # Retenu is calculated on (TTC - timbre) but payment is on remaining amount
                retenu_amount = retenu_base * retenu_percent / 100.0
                net_payment = remaining_amount - retenu_amount
                
                # ✅ IDENTICAL TO VENTE: Ensure net payment doesn't go negative
                if net_payment < 0:
                    net_payment = 0
                    retenu_amount = remaining_amount
                
                # ✅ IDENTICAL TO VENTE: Update display fields
                retenu_amount_var.set(f"{retenu_amount:.3f}")
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation: {e}")
                retenu_amount_var.set("0.000")
        
        def calculate_retenu_from_amount(*args):
            """Calculate retenu percentage from amount - IDENTICAL TO VENTE"""
            try:
                # Get the retenu amount
                retenu_amount_text = retenu_amount_var.get().strip()
                if not retenu_amount_text:
                    retenu_amount = 0.0
                else:
                    try:
                        retenu_amount = float(retenu_amount_text.replace(",", "."))
                        if retenu_amount < 0:
                            retenu_amount = 0.0
                    except ValueError:
                        retenu_amount = 0.0
                
                # ✅ IDENTICAL TO VENTE: Calculate retenu base excluding timbre
                ttc_amount = self.montant_total
                timbre_amount = self.achat.get('timbre', 1.0) if hasattr(self, 'achat') else 1.0
                retenu_base = max(0, ttc_amount - timbre_amount)
                
                # ✅ IDENTICAL TO VENTE: Calculate percentage
                if retenu_base > 0:
                    retenu_percent = (retenu_amount / retenu_base) * 100.0
                else:
                    retenu_percent = 0.0
                
                # ✅ IDENTICAL TO VENTE: Update percentage (but don't trigger the percentage callback)
                if hasattr(calculate_retenu_from_amount, 'percent_trace_id'):
                    retenu_var.trace_remove("write", calculate_retenu_from_amount.percent_trace_id)
                retenu_var.set(f"{retenu_percent:.2f}")
                calculate_retenu_from_amount.percent_trace_id = retenu_var.trace_add("write", calculate_retenu_from_percent)
                
                # ✅ IDENTICAL TO VENTE: Update net payment using self.reste (not current amount field!)
                remaining_amount = self.reste  # THIS IS THE KEY FIX!
                net_payment = remaining_amount - retenu_amount
                if net_payment < 0:
                    net_payment = 0
                
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation from amount: {e}")
        
        # 🔧 Bind the calculations to field changes - LIKE VENTE  
        calculate_retenu_from_amount.percent_trace_id = retenu_var.trace_add("write", calculate_retenu_from_percent)
        retenu_amount_var.trace_add("write", calculate_retenu_from_amount)
        def save_payment():
            try:
                # 🔧 IDENTICAL validation and calculation to vente_page.py
                
                # Validate amount
                amount_text = amount_var.get().strip()
                if not amount_text:
                    messagebox.showerror("Erreur", "Le montant est obligatoire.")
                    return
                    
                try:
                    montant = float(amount_text.replace(",", "."))
                    if montant <= 0:
                        messagebox.showerror("Erreur", "Le montant doit être positif.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Montant invalide.")
                    return
                
                # 🔧 Get retenu amount from the EDITABLE field (like vente)
                retenu_amount_text = retenu_amount_var.get().strip()
                if retenu_amount_text:
                    try:
                        retenu_amount = float(retenu_amount_text.replace(",", "."))
                        if retenu_amount < 0:
                            messagebox.showerror("Erreur", "Le montant de retenu ne peut pas être négatif.")
                            return
                    except ValueError:
                        messagebox.showerror("Erreur", "Montant de retenu invalide.")
                        return
                else:
                    retenu_amount = 0.0
                
                # 🔧 Get retenu percentage for records
                retenu_percent = float(retenu_var.get().replace(",", ".")) if retenu_var.get() else 0.0
                
                # 🔧 IDENTICAL to vente: The 'montant' field already contains the net payment amount
                montant_net = montant
                
                # DEBUG: Log the calculation (like vente)
                print(f"[ACHAT_PAYMENT_DIALOG] Fixed payment calculation:")
                print(f"  montant (already net): {montant}")
                print(f"  retenu_amount (for records): {retenu_amount}")  
                print(f"  montant_net (final): {montant_net}")
                
                # Validate that net payment is reasonable
                if montant_net < 0:
                    messagebox.showerror("Erreur", "Le montant net ne peut pas être négatif. Réduisez le montant de retenu.")
                    return
                
                # 🔧 IDENTICAL date validation to vente
                date_text = date_var.get().strip()
                if not date_text:
                    messagebox.showerror("Erreur", "La date de paiement est obligatoire.")
                    return
                    
                try:
                    date_str = datetime.strptime(date_text, "%d/%m/%Y").strftime("%Y-%m-%d")
                    # Check if date is not in the future (allow today)
                    payment_date = datetime.strptime(date_text, "%d/%m/%Y").date()
                    if payment_date > datetime.now().date():
                        messagebox.showerror("Erreur", "La date de paiement ne peut pas être dans le futur.")
                        return
                except ValueError:
                    messagebox.showerror("Erreur", "Format de date invalide (JJ/MM/AAAA).")
                    return
                
                # Handle echeance (due date) for traite
                echeance_db = ''
                echeance_str = echeance_var.get().strip()
                if echeance_str:
                    try:
                        echeance_db = datetime.strptime(echeance_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                        echeance_date = datetime.strptime(echeance_str, "%d/%m/%Y").date()
                        
                        # Get method key to check if it's traite
                        method_key = None
                        if type_var.get() == 'banque' and method_combo.get():
                            try:
                                payment_methods = [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                                method_idx = [label for _, label in payment_methods].index(method_combo.get())
                                method_key = payment_methods[method_idx][0] if method_idx is not None else None
                            except Exception:
                                pass
                        
                        # Only require future date for traite (bills of exchange)
                        if method_key == "traite" and echeance_date <= datetime.now().date():
                            messagebox.showerror("Erreur", "L'échéance pour une traite doit être dans le futur.")
                            return
                    except ValueError:
                        messagebox.showerror("Erreur", "Format d'échéance invalide (JJ/MM/AAAA).")
                        return
                
                # 🔧 IDENTICAL validation to vente
                # Validate bank selection for bank payments
                if type_var.get() == 'banque':
                    if not bank_var.get() or bank_var.get() not in banks_dict:
                        messagebox.showerror("Erreur", "Veuillez sélectionner une banque.")
                        return
                    if not method_combo.get():
                        messagebox.showerror("Erreur", "Veuillez sélectionner une méthode de paiement.")
                        return
                
                # Validate reference number for bank payments
                ref = numero_var.get().strip()
                if type_var.get() == 'banque' and not ref:
                    messagebox.showerror("Erreur", "Le numéro de référence est obligatoire pour les paiements bancaires.")
                    return
                
                # Get notes
                notes = notes_text.get("1.0", "end").strip()
                if retenu_amount > 0:
                    notes = f"[Retenu: {retenu_percent:.2f}% = {retenu_amount:.3f} DT] " + notes
                
                if preset:
                    # ✅ UNIFIED: Delete old payment and create new one (like vente)
                    # Delete old payment if editing  
                    if self.payment_service:
                        self.payment_service.delete_payment(preset['id'], is_achat=True)
                
                # ✅ UNIFIED: Save payment using PaymentService directly (like vente)
                if type_var.get() == 'banque':
                    if not bank_var.get() or bank_var.get() not in banks_dict:
                        messagebox.showerror("Erreur", "Veuillez sélectionner une banque.")
                        return
                    banque_id = banks_dict[bank_var.get()]
                    payment_methods = self.bank_service.get_payment_methods() if self.bank_service else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                    method_key = payment_methods[method_idx][0]
                    
                    if self.payment_service:
                        self.payment_service.marquer_facture_payee_banque(
                            self.achat_id, montant_net, date_str, ref, notes, 
                            banque_id=banque_id, mode_paiement=method_key, echeance=echeance_db,
                            retenu_percent=retenu_percent, retenu_amount=retenu_amount, is_achat=True
                        )
                else:
                    if self.payment_service:
                        self.payment_service.marquer_facture_payee_caisse(
                            self.achat_id, montant_net, date_str, ref, notes, 
                            mode_paiement='', echeance='',
                            retenu_percent=retenu_percent, retenu_amount=retenu_amount, is_achat=True
                        )
                
                # Update UI
                self.paiements = self.payment_service.get_invoice_payments(self.achat_id, is_achat=True) if self.payment_service else []
                self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
                self.reste_var.set(f"{self.reste:.3f}")
                self._refresh_tree()
                self.result = True
                form.destroy()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {e}")
        tk.Button(form, text="Enregistrer", command=save_payment, bg="#28a745", fg="white").pack(pady=12)
        if preset:
            # Load preset data for editing
            if preset.get('methode_paiement') == 'banque' and preset.get('banque_id'):
                for nom, bid in banks_dict.items():
                    if bid == preset['banque_id']:
                        bank_combo.set(nom)
                        break
            if preset.get('mode_paiement'):
                # ✅ UNIFIED: Use bank_service payment methods (like vente)
                payment_methods = self.bank_service.get_payment_methods() if self.bank_service else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                for k, label in payment_methods:
                    if k == preset['mode_paiement']:
                        method_combo.set(label)
                        break
            if preset.get('echeance'):
                echeance_var.set(datetime.strptime(preset['echeance'], "%Y-%m-%d").strftime("%d/%m/%Y"))
            date_var.set(datetime.strptime(preset['date_paiement'], "%Y-%m-%d").strftime("%d/%m/%Y"))
            ref_var.set(preset.get('reference_paiement', ''))
            update_fields()
            
            def delete_and_close():
                self._delete_payment(preset['id'])
                form.destroy()
            tk.Button(form, text="Supprimer", command=delete_and_close, bg="#dc3545", fg="white").pack(pady=6)
        tk.Button(form, text="Annuler", command=form.destroy).pack(pady=6)
    def _cancel(self):
        self.window.destroy()
    def _on_tree_select(self, event):
        sel = self.tree.selection()
        if sel:
            self.delete_btn.config(state="normal")
        else:
            self.delete_btn.config(state="disabled")
    def _delete_selected_payment(self):
        # Check permission first
        if not check_ui_permission("payments", "delete"):
            return
            
        sel = self.tree.selection()
        if sel:

            self._delete_payment(sel[0]) 