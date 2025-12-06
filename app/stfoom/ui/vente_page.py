from __future__ import annotations
import json
import os
from typing import Optional, List, Dict
from datetime import datetime
from app.connection import sync

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# ✅ SERVICES-ONLY ARCHITECTURE: Use services instead of logic imports
# from stfoom.logic import vente  # REMOVED
# from stfoom.logic.invoice_gen import generate_invoice, load_client_from_db  # REMOVED
# from stfoom.logicold import payments  # MIGRATED TO PaymentService
# import stfoom.logicold.bank as bank  # MIGRATED TO BankService
from tkcalendar import Calendar, DateEntry
from .permission_utils import check_ui_permission, require_ui_permission, disable_button_if_no_permission

from .shared_widgets import format_money  # Import centralized money formatting
from app.core.path_manager import get_db_path
class VentePage(ttk.Frame):
    """Recapitulatif des ventes / factures UI page."""

    COLS: List[tuple[str, str]] = [
        ("date", "Date"),
        ("nfacture_seq", "N° Facture"),
        ("client", "Client"),
        ("mt_ht", "Montant HT"),
        ("fodec", "FODEC"),
        ("tva19", "TVA 19 %"),
        ("transport", "Transport"),
        ("tva7", "TVA 7 %"),
        ("timbre", "Timbre"),
        ("ttc", "Total TTC"),
        ("statut_paiement", "Statut Paiement"),
        ("methode_paiement", "Méthode"),
    ]

    def __init__(self, master: tk.Misc, container_or_go_home, go_home=None):
        """
        Initialize VentePage with dependency injection support.
        
        Args:
            master: Parent widget
            container_or_go_home: Either container (new style) or go_home callback (old style)
            go_home: Go home callback (when using new style)
        """
        super().__init__(master, style="FactureMain.TFrame")
        
        # ✅ PHASE 2B MIGRATION: Handle both old and new constructor patterns
        if hasattr(container_or_go_home, 'get'):  # It's a container
            self.container = container_or_go_home
            self.go_home = go_home
            # Get services from container with graceful fallbacks
            try:
                self.sales_service = self.container.get('sales_service')
                print(f"[VENTE] SalesService retrieved successfully: {self.sales_service is not None}")
            except Exception as e:
                print(f"[VENTE] Error getting SalesService: {e}")
                self.sales_service = None
            
            try:
                self.bank_service = self.container.get('bank_service')
            except Exception as e:
                print(f"[VENTE] BankService not available: {e}")
                self.bank_service = None
                
            try:
                self.payment_service = self.container.get('payment_service')
            except Exception as e:
                print(f"[VENTE] PaymentService not available: {e}")
                self.payment_service = None
                
            try:
                self.retenu_service = self.container.get('retenu_service')
            except Exception as e:
                print(f"[VENTE] RetenuService not available: {e}")
                self.retenu_service = None
                
            print("[VENTE] Using service-based architecture with dependency injection")
        else:  # It's the old go_home callback  
            self.go_home = container_or_go_home
            self.container = None
            self.sales_service = None
            self.bank_service = None
            self.payment_service = None
            self.retenu_service = None
            print("[VENTE] Using legacy logic layer (no container)")
        
        self.pack(fill="both", expand=True)

        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=self.go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Ventes – Journal des Factures", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- smart search ----------
        self._setup_smart_search()

        # ---------- table section ----------
        table_frame = ttk.LabelFrame(self, text="Liste des Factures", style="FactureSection.TLabelframe")
        table_frame.pack(fill="both", expand=True, padx=30, pady=(0, 10), ipadx=8, ipady=8)

        # Treeview table of ventes
        self.tree = ttk.Treeview(table_frame, columns=[c[0] for c in self.COLS], show="headings", height=16, style="Custom.Treeview")
        for key, title in self.COLS:
            self.tree.heading(key, text=title)
            self.tree.column(key, anchor="center", width=100)
        self.tree.column("client", anchor="w", width=250)
        self.tree.column("ttc", anchor="e", width=120)
        self.tree.column("statut_paiement", anchor="center", width=120)
        self.tree.column("methode_paiement", anchor="center", width=80)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

        # Configure tags for payment status colors - Subtle improvements
        # Support both space and underscore formats for compatibility
        self.tree.tag_configure("payé", foreground="#155724", background="#d4edda")  # Darker green on light green for paid
        self.tree.tag_configure("partiellement payé", foreground="#b8860b", background="#fff3cd")  # Darker yellow on light yellow for partially paid  
        self.tree.tag_configure("partiellement_payé", foreground="#b8860b", background="#fff3cd")  # Legacy underscore format
        self.tree.tag_configure("non payé", foreground="#721c24", background="#f8d7da")  # Dark red on light red for unpaid
        self.tree.tag_configure("non_payé", foreground="#721c24", background="#f8d7da")  # Legacy underscore format

        # ---------- action buttons ----------
        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=20, padx=30, fill="x")
        for i in range(3):
            btn_frame.columnconfigure(i, weight=1)
        
        # Enhanced button style with better appearance
        button_style = {
            "font": ("Segoe UI", 12, "bold"),
            "relief": "raised",
            "bd": 2,
            "cursor": "hand2",
            "borderwidth": 2,
            "padx": 20,
            "pady": 10
        }
        
        # Generate/Regenerate button (green with better styling)
        gen_btn = tk.Button(
            btn_frame,
            text="📄 Générer / Régénérer facture",
            command=self._on_generate,
            bg="#28a745",
            fg="white",
            activebackground="#218838",
            activeforeground="white",
            **button_style
        )
        gen_btn.grid(row=0, column=0, padx=10, sticky="ew", ipady=12)
        
        # Mark Paid button (blue with better styling)
        paid_btn = tk.Button(
            btn_frame,
            text="💳 Marquer Payé",
            command=self._on_mark_paid,
            bg="#007bff",
            fg="white",
            activebackground="#0056b3",
            activeforeground="white",
            **button_style
        )
        paid_btn.grid(row=0, column=1, padx=10, sticky="ew", ipady=12)
        
        # Delete button (red with better styling)
        del_btn = tk.Button(
            btn_frame,
            text="🗑️ Supprimer",
            command=self._on_delete,
            bg="#dc3545",
            fg="white",
            activebackground="#c82333",
            activeforeground="white",
            **button_style
        )
        del_btn.grid(row=0, column=2, padx=10, sticky="ew", ipadx=20, ipady=8)

        # Multiple Payment button (purple with better styling)
        multiple_payment_btn = tk.Button(
            btn_frame,
            text="💳 Paiement Multiple",
            command=self._on_multiple_payment,
            bg="#6f42c1",
            fg="white",
            activebackground="#5a32a3",
            activeforeground="white",
            **button_style
        )
        multiple_payment_btn.grid(row=0, column=3, padx=10, sticky="ew", ipadx=20, ipady=8)

        # TEMP FULL EDIT BUTTON (maintenance)
        try:
            temp_full_edit_btn = tk.Button(
                btn_frame,
                text="✏️ Edition Totale (Temp)",
                command=self._on_full_edit,
                bg="#17a2b8",
                fg="white",
                activebackground="#11707f",
                activeforeground="white",
                **button_style
            )
            temp_full_edit_btn.grid(row=0, column=4, padx=10, sticky="ew", ipadx=10, ipady=8)
            btn_frame.grid_columnconfigure(4, weight=1)
        except Exception as e:
            print(f"[VENTE] Could not add full edit temp button: {e}")

        # Configure column weights for better distribution
        btn_frame.grid_columnconfigure(0, weight=1)
        btn_frame.grid_columnconfigure(1, weight=1) 
        btn_frame.grid_columnconfigure(2, weight=1)
        btn_frame.grid_columnconfigure(3, weight=1)

        # Apply permission-based button states - FOR NOW: ALWAYS ENABLE FOR TESTING
        # disable_button_if_no_permission(gen_btn, "facture", "create")
        # disable_button_if_no_permission(paid_btn, "vente", "update")
        # disable_button_if_no_permission(del_btn, "vente", "delete")

        self._load_rows()

    def _setup_smart_search(self):
        """Setup page-specific search for vente page."""
        try:
            from .enhanced_search import create_page_search
            
            # Create vente-specific search function
            def search_ventes_in_page(query):
                """Search only in current vente page data."""
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
                                client = values[2] if len(values) > 2 else "Client inconnu"
                                nfacture = values[1] if len(values) > 1 else "N/A"
                                ttc = values[9] if len(values) > 9 else "0"
                                date = values[0] if len(values) > 0 else "Date inconnue"
                                
                                results.append({
                                    'type': 'Facture',
                                    'content': f"#{nfacture} - {client}",
                                    'details': f"{ttc} TND - {date}",
                                    'icon': '💰',
                                    'item_id': item,  # Store tree item ID for selection
                                    'relevance': self._calculate_search_relevance(query_lower, values)
                                })
                                
                        if len(results) >= 20:  # Limit results
                            break
                    
                    # Sort by relevance
                    results.sort(key=lambda x: x.get('relevance', 0), reverse=True)
                    
                except Exception as e:
                    print(f"[VENTE_SEARCH] Error: {e}")
                    
                return results
            
            # Create the page-specific search widget
            self.page_search = create_page_search(self, "Ventes", search_ventes_in_page)
            
            # Override the result selection to highlight in tree
            original_on_result_select = self.page_search.on_result_select
            
            def on_vente_select(result):
                """Handle selection of vente search result."""
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
                            "Facture trouvée", 
                            f"Facture sélectionnée: {result['content']}\n{result['details']}"
                        )
                except Exception as e:
                    print(f"[VENTE_SEARCH] Selection error: {e}")
            
            self.page_search.on_result_select = on_vente_select
            
        except Exception as e:
            print(f"[VENTE_SEARCH] Setup error: {e}")
            # Fallback to simple label
            ttk.Label(self, text="🔍 Recherche Ventes", font=('Segoe UI', 12, 'bold')).pack(pady=5)
    
    def _calculate_search_relevance(self, query: str, values: list) -> int:
        """Calculate search relevance score for ranking results."""
        relevance = 0
        
        # Higher score for matches in important fields
        if len(values) > 2 and query in values[2].lower():  # Client name
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

    def _load_vente_from_search(self, vente_data):
        """Load a vente from search results for editing."""
        try:
            print(f"[VENTE] Loading vente from search: {vente_data}")
            # For now, show the details
            from tkinter import messagebox
            messagebox.showinfo("Info", f"Chargement de la vente: Facture #{vente_data.get('nfacture_seq', 'N/A')}")
        except Exception as e:
            print(f"[VENTE] Error loading vente from search: {e}")

    def _select_vente_from_search(self, item_id):
        """Select a vente from search results in the treeview."""
        try:
            # Select the item in the treeview
            self.tree.selection_set(item_id)
            self.tree.see(item_id)
            self.tree.focus(item_id)
            print(f"[VENTE] Selected vente from search")
        except Exception as e:
            print(f"[VENTE] Error selecting vente from search: {e}")

    def _load_rows(self):
        """Load ventes from DB and populate the treeview."""
        try:
            # Check if treeview still exists before trying to access it
            if not hasattr(self, 'tree') or not self.tree.winfo_exists():
                return
                
            # Safely clear the treeview
            try:
                self.tree.delete(*self.tree.get_children())
            except Exception:
                return
                
            # ✅ PHASE 2B MIGRATION: Use service or fallback to logic
            if self.sales_service:
                print(f"[VENTE] Loading data using SalesService: {self.sales_service}")
                self._rows: List[Dict] = self.sales_service.get_all_sales()
                print(f"[VENTE] SalesService returned {len(self._rows)} sales records")
            else:
                # Service should always be available after Phase 2 
                print("[VENTE] Warning: SalesService not available, trying fallback")
                try:
                    from ..services.sales_service import SalesService
                    fallback_service = SalesService()
                    self._rows: List[Dict] = fallback_service.get_all_sales()
                    print(f"[VENTE] Fallback service retrieved {len(self._rows)} sales")
                except Exception as e:
                    print(f"[VENTE] Fallback service failed: {e}")
                    self._rows: List[Dict] = []
            
            print(f"[VENTE] Starting to populate treeview with {len(self._rows)} rows")
            
            for i, v in enumerate(self._rows):
                # Check again if treeview still exists
                if not self.tree.winfo_exists():
                    print("[VENTE] Treeview destroyed during loading, stopping")
                    return
                    
                # Get payment status for this invoice
                nfacture = v["nfacture"]
                montant_total = v.get('ttc', 0)
                
                # Use PaymentService if available, otherwise fallback to legacy
                if hasattr(self, 'payment_service') and self.payment_service:
                    retenu_total = self._get_retenu_total_for_invoice(nfacture)
                    payment_status = self.payment_service.get_payment_status(nfacture, montant_total, retenu_total)
                    # Convert service response to expected format
                    statut_paiement = {
                        'statut': payment_status['status'],
                        'montant_paye': payment_status['total_paid'],
                        'montant_restant': payment_status['remaining']
                    }
                    # Get payments for method info
                    paiements = self.payment_service.get_invoice_payments(nfacture)
                else:
                    # Fallback: create payment service if not available
                    from ..services.payment_service import PaymentService
                    self.payment_service = PaymentService()
                    retenu_total = self._get_retenu_total_for_invoice(nfacture)
                    payment_status = self.payment_service.get_payment_status(nfacture, montant_total, retenu_total)
                    statut_paiement = {
                        'statut': payment_status['status'],
                        'montant_paye': payment_status['total_paid'],
                        'montant_restant': payment_status['remaining']
                    }
                    paiements = self.payment_service.get_invoice_payments(nfacture)
                
                # Get payment method (most recent payment)
                methode_paiement = ""
                if paiements:
                    methode_paiement = self.payment_service.format_payment_method(paiements[0].get('methode_paiement', ''))
                # Determine tag for color coding
                tag = statut_paiement['statut']
                
                # Safely insert into treeview
                try:
                    self.tree.insert("", "end", iid=str(v["nfacture"]), values=(
                        v.get("date", ""),
                        v.get("nfacture_seq", ""),
                        v.get("client", ""),
                        f"{float(v.get('mt_ht', 0) or 0):.3f}",
                        f"{float(v.get('fodec', 0) or 0):.3f}",
                        f"{float(v.get('tva19', 0) or 0):.3f}",
                        f"{float(v.get('transport', 0) or 0):.3f}",
                        f"{float(v.get('tva7', 0) or 0):.3f}",
                        f"{float(v.get('timbre', 0) or 0):.3f}",
                        f"{float(v.get('ttc', 0) or 0):.3f}",
                        self.payment_service.format_payment_status(statut_paiement['statut']) if hasattr(self, 'payment_service') else statut_paiement['statut'],
                        methode_paiement,
                    ), tags=(tag,))
                    
                    if i < 5 or i % 10 == 0:  # Print first 5 and every 10th
                        print(f"[VENTE] Inserted row {i+1}/{len(self._rows)}: Invoice {nfacture} - {v.get('client', '')}")
                        
                except Exception as e:
                    print(f"[VENTE] Error inserting row {i+1} (nfacture {nfacture}): {e}")
                    continue
                    
            print(f"[VENTE] Finished populating treeview. Total items in tree: {len(self.tree.get_children())}")
                    
        except Exception as e:
            print(f"[VENTE] Error loading rows: {e}")
            import traceback
            traceback.print_exc()

    def _selected_nfacture_int(self) -> Optional[int]:
        """Return the selected facture number as int, or None if no selection."""
        try:
            # Check if widget still exists
            if not hasattr(self, 'tree') or not self.tree.winfo_exists():
                return None
            
            sel = self.tree.selection()
            if not sel:
                return None
            return int(sel[0])  # iid stores the facture number as string int
        except (ValueError, tk.TclError, AttributeError):
            return None

    def _on_delete(self):
        """Delete the selected facture after confirmation."""
        # Check permission first
        if not check_ui_permission("vente", "delete"):
            return
            
        nfacture = self._selected_nfacture_int()
        if nfacture is None:
            messagebox.showwarning("Sélection", "Choisissez une facture à supprimer.")
            return
            
        # Get invoice details for confirmation
        invoice = None
        for v in self._rows:
            if v["nfacture"] == nfacture:
                invoice = v
                break
                
        if not invoice:
            messagebox.showerror("Erreur", "Facture introuvable.")
            return
            
        # Show detailed confirmation
        montant = invoice.get('ttc', 0)
        client = invoice.get('client', 'Inconnu')
        date = invoice.get('date', '')
        
        confirmation_msg = f"""Êtes-vous sûr de vouloir supprimer cette facture ?

N° Facture: {nfacture}
Client: {client}
Date: {date}
Montant: {montant:.3f} DT

⚠️  ATTENTION: Cette action est irréversible !
   - Tous les paiements associés seront supprimés
   - Les transactions bancaires seront supprimées
   - Les retenues seront supprimées"""
        
        if not messagebox.askyesno("Confirmation de suppression", confirmation_msg):
            return
            
        # Double confirmation for high amounts
        if montant > 10000:  # 10,000 DT
            if not messagebox.askyesno("Confirmation finale", 
                f"Facture de {montant:.3f} DT - Confirmer la suppression ?"):
                return
        
        try:
            # ✅ PHASE 2B MIGRATION: Use service or fallback to logic
            if self.sales_service:
                print(f"[VENTE PAGE] Using SalesService to delete invoice {nfacture}")
                success = self.sales_service.delete_sale_by_invoice(nfacture)
            else:
                # Fallback to fixed vente_old logic
                print(f"[VENTE PAGE] Using legacy logic to delete invoice {nfacture}")
                from stfoom.logicold.old import vente_old
                success = vente_old.delete_vente(nfacture)
                
            if success:
                # ✅ SYNC INTEGRATION: Track the deletion for sync system
                try:
                    # Get sync service and track the change
                    from stfoom.services.sync_service import SyncService
                    sync_service = SyncService()
                    
                    # Track the change - use 'ventes' table which is the main invoice table
                    deletion_data = {
                        "deleted_at": datetime.now().isoformat(),
                        "deleted_by": "user",  # Could be enhanced to track actual user
                        "nfacture": nfacture
                    }
                    sync_service.add_sync_change("ventes", str(nfacture), deletion_data, "delete")
                    print(f"[SYNC] Tracked deletion of invoice {nfacture} for sync")
                except Exception as sync_error:
                    print(f"[SYNC] Warning - failed to track deletion: {sync_error}")
                    # Continue even if sync tracking fails
                
                # Remove from UI immediately
                try:
                    self.tree.delete(str(nfacture))
                except Exception:
                    pass  # Item might already be removed
                
                # Refresh the data to ensure consistency
                self._load_rows()
                
                messagebox.showinfo("Succès", f"Facture {nfacture} supprimée avec succès.")
            else:
                messagebox.showerror("Erreur", f"Échec de la suppression de la facture {nfacture}.\nVérifiez la console pour plus de détails.")
                
        except Exception as e:
            print(f"[VENTE PAGE] Error deleting invoice {nfacture}: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror("Erreur", f"Erreur lors de la suppression:\n{str(e)}")
            
        # Always refresh to show current state
        try:
            self._load_rows()
        except Exception as e:
            print(f"[VENTE PAGE] Error refreshing after delete: {e}")

    def _get_retenu_total_for_invoice(self, nfacture: int) -> float:
        """Get total retenu amount for a specific invoice, respecting minimum threshold
        
        This method now handles both:
        1. Explicit retenu records from retenu_service
        2. Retenue embedded in payment notes (for 'marqué payé' payments)
        """
        try:
            # First, try to get explicit retenu records
            retenu_total = 0.0
            
            # Use dependency injection if available
            if self.retenu_service:
                retenus = self.retenu_service.get_retenus_by_facture(nfacture)
                retenu_total = sum(r.get('amount', 0) for r in retenus)
            else:
                # Fallback: create service manually with proper repository
                from app.stfoom.services.retenu_service import RetenuService
                from app.stfoom.data.retenu_repository import RetenuRepository
                
                retenu_repository = RetenuRepository()
                retenu_service = RetenuService(retenu_repository)
                retenus = retenu_service.get_retenus_by_facture(nfacture)
                retenu_total = sum(r.get('amount', 0) for r in retenus)
            
            # If no explicit retenu records found, check payment notes for embedded retenue
            if retenu_total == 0.0:
                retenu_total = self._extract_retenu_from_payment_notes(nfacture)
            
            return retenu_total
            
        except Exception as e:
            print(f"[VENTE] Error getting retenu total: {e}")
            return 0.0

    def _extract_retenu_from_payment_notes(self, nfacture: int) -> float:
        """Extract retenue amount from payment notes for 'marqué payé' payments"""
        try:
            import sqlite3
            import re
            
            with sqlite3.connect(get_db_path()) as conn:
                # Get payment notes that contain retenu information
                cursor = conn.execute("""
                    SELECT notes FROM paiements_factures 
                    WHERE nfacture = ? AND notes LIKE '%Retenu:%'
                """, (nfacture,))
                
                total_retenu = 0.0
                for (notes,) in cursor.fetchall():
                    if notes:
                        # Extract retenu percentage from notes like "[Retenu: 1.0%]"
                        retenu_match = re.search(r'\[Retenu:\s*([\d.]+)%\]', notes)
                        if retenu_match:
                            retenu_percent = float(retenu_match.group(1))
                            
                            # Calculate retenu amount based on invoice TTC (excluding timbre)
                            cursor2 = conn.execute("""
                                SELECT ttc, timbre FROM ventes WHERE nfacture = ?
                            """, (nfacture,))
                            vente_data = cursor2.fetchone()
                            if vente_data:
                                ttc, timbre = vente_data
                                retenu_base = ttc - (timbre or 0)  # Exclude timbre from retenu calculation
                                retenu_amount = retenu_base * retenu_percent / 100.0
                                total_retenu += retenu_amount
                
                return total_retenu
                
        except Exception as e:
            print(f"[VENTE] Error extracting retenu from payment notes: {e}")
            return 0.0

    def _on_mark_paid(self):
        """Open payment dialog for the selected invoice."""
        # Check permission first
        if not check_ui_permission("vente", "update"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de modifier les paiements.")
            return
            
        nfacture = self._selected_nfacture_int()
        if nfacture is None:
            messagebox.showwarning("Sélection", "Choisissez une facture pour gérer les paiements.")
            return
        
        # Find the invoice data
        invoice = None
        for v in self._rows:
            if v["nfacture"] == nfacture:
                invoice = v
                break
        
        if not invoice:
            messagebox.showerror("Erreur", "Facture introuvable dans les données.")
            return
        
        # Show invoice details before opening payment dialog
        try:
            montant = float(invoice.get('ttc', 0))
            client = invoice.get('client', 'Inconnu')
            date = invoice.get('date', '')
            
            info_msg = f"💳 Gestion des paiements\n\n" \
                      f"📄 Facture: {nfacture}\n" \
                      f"👤 Client: {client}\n" \
                      f"📅 Date: {date}\n" \
                      f"💰 Montant total: {montant:.3f} DT"
            
            messagebox.showinfo("Information facture", info_msg)
            
            # 🔧 UNIFIED PAYMENT SYSTEM: Use enhanced original PaymentDialog
            # Open enhanced payment dialog with timbre-aware retenu calculation
            payment_dialog = PaymentDialog(
                parent=self, 
                nfacture=nfacture, 
                invoice=invoice,
                payment_service=getattr(self, 'payment_service', None),
                bank_service=getattr(self, 'bank_service', None)
            )
            
            if payment_dialog.result:
                # Refresh the display to show updated payment status
                self._load_rows()
                messagebox.showinfo("Succès", "Paiement traité avec succès!")
                
        except Exception as e:
            print(f"[VENTE] Error in mark paid: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de l'ouverture du dialogue de paiement:\n{e}")

    def _on_multiple_payment(self):
        """Handle multiple invoice payment"""
        if not check_ui_permission("vente", "update"):
            return
            
        # Get selected invoices or show selection dialog
        selected_items = self.tree.selection()
        
        if not selected_items:
            # No selection - show all unpaid invoices dialog
            self._show_multiple_payment_selection()
        else:
            # Special case: if exactly one facture is selected and it belongs to a MULTI batch,
            # load ALL invoices in that batch so the dialog shows the group, not only one.
            try:
                if len(selected_items) == 1 and hasattr(self, 'payment_service') and self.payment_service:
                    sel_nfacture = int(selected_items[0])
                    import re
                    with self.payment_service.payment_repository.get_connection() as conn:
                        # Find a MULTI reference from any payment on this invoice
                        cur = conn.execute(
                            """
                            SELECT notes FROM paiements_factures
                            WHERE nfacture = ? AND notes LIKE '%MULTI-%'
                            ORDER BY created_at DESC LIMIT 1
                            """,
                            (sel_nfacture,)
                        )
                        row = cur.fetchone()
                        multi_ref = None
                        if row and row[0]:
                            m = re.search(r'MULTI-\d{8}-\d{6}(?:-\d{6})?', row[0])
                            if m:
                                multi_ref = m.group(0)
                        
                        if multi_ref:
                            # Get all DISTINCT invoices participating in this MULTI batch
                            cur2 = conn.execute(
                                """
                                SELECT DISTINCT nfacture FROM paiements_factures
                                WHERE notes LIKE ? ORDER BY nfacture
                                """,
                                (f'%{multi_ref}%',)
                            )
                            related_ids = [r[0] for r in cur2.fetchall() if r and r[0] is not None]
                        else:
                            related_ids = []
                else:
                    related_ids = []
            except Exception as e:
                print(f"[VENTE] Error detecting MULTI batch: {e}")
                related_ids = []

            invoice_list = []
            if related_ids:
                # Build invoice list for ALL related invoices (show all, even if fully paid)
                try:
                    for inv_id in related_ids:
                        # Find invoice data in loaded rows first
                        invoice_data = next((v for v in self._rows if v.get('nfacture') == inv_id), None)
                        if not invoice_data:
                            # Fallback: query ventes directly for essentials
                            try:
                                import sqlite3
                                with sqlite3.connect(get_db_path()) as conn2:
                                    vcur = conn2.execute("SELECT raison_sociale, ttc, timbre FROM ventes WHERE nfacture = ?", (inv_id,))
                                    vrow = vcur.fetchone()
                                    if vrow:
                                        invoice_data = {
                                            'nfacture': inv_id,
                                            'client': vrow[0] or '',
                                            'ttc': float(vrow[1] or 0),
                                            'timbre': float(vrow[2] or 1.0)
                                        }
                            except Exception as _e:
                                invoice_data = None
                        if not invoice_data:
                            continue

                        ttc = float(invoice_data.get('ttc', 0))
                        retenu_total = self._get_retenu_total_for_invoice(inv_id)
                        status = self.payment_service.get_payment_status(inv_id, ttc, retenu_total)
                        paid = status.get('total_paid', status.get('paye', 0))
                        remaining = max(0.0, ttc - float(paid or 0))

                        invoice_list.append({
                            'id': inv_id,
                            'fournisseur': invoice_data.get('client', ''),
                            'amount': ttc,
                            'paid': paid or 0.0,
                            'remaining': remaining,
                            'type': 'vente',
                            'timbre': invoice_data.get('timbre', 1.0)
                        })
                except Exception as e:
                    print(f"[VENTE] Error building related MULTI invoice list: {e}")

                if invoice_list:
                    self._open_multiple_payment_dialog(invoice_list)
                    return

            # Default behavior: use selected invoices (only unpaid)
            for item_id in selected_items:
                nfacture = int(item_id)
                # Find invoice data
                invoice_data = None
                for v in self._rows:
                    if v["nfacture"] == nfacture:
                        invoice_data = v
                        break
                if invoice_data:
                    ttc = float(invoice_data.get('ttc', 0))
                    # Get payment status
                    retenu_total = self._get_retenu_total_for_invoice(nfacture)
                    status = self.payment_service.get_payment_status(nfacture, ttc, retenu_total)
                    paid = status.get('total_paid', status.get('paye', 0))
                    remaining = ttc - float(paid or 0)
                    if remaining > 0:  # Only include unpaid invoices
                        invoice_list.append({
                            'id': nfacture,
                            'fournisseur': invoice_data.get('client', ''),  # Use client for vente
                            'amount': ttc,
                            'paid': paid or 0.0,
                            'remaining': remaining,
                            'type': 'vente'
                        })
            if invoice_list:
                self._open_multiple_payment_dialog(invoice_list)
            else:
                messagebox.showinfo("Information", "Aucune facture impayée sélectionnée")

    def _show_multiple_payment_selection(self):
        """Show dialog to select invoices for multiple payment"""
        unpaid_invoices = []
        
        for invoice in self._rows:
            nfacture = invoice.get('nfacture')
            ttc = float(invoice.get('ttc', 0))
            retenu_total = self._get_retenu_total_for_invoice(nfacture)
            status = self.payment_service.get_payment_status(nfacture, ttc, retenu_total)
            paid = status.get('paye', 0)
            remaining = ttc - paid
            
            if remaining > 0:
                unpaid_invoices.append({
                    'id': nfacture,
                    'fournisseur': invoice.get('client', ''),  # Use client for vente
                    'amount': ttc,
                    'paid': paid,
                    'remaining': remaining,
                    'type': 'vente'
                })
        
        if unpaid_invoices:
            self._open_multiple_payment_dialog(unpaid_invoices)
        else:
            messagebox.showinfo("Information", "Aucune facture impayée trouvée")

    def _open_multiple_payment_dialog(self, invoice_list):
        """Open the enhanced multiple payment dialog with ALL normal payment features"""
        try:
            from .enhanced_multiple_payment_dialog import show_enhanced_multiple_payment_dialog
            
            # Prepare invoices data for unified system with proper field mapping
            invoices_data = []
            for invoice in invoice_list:
                # Get proper remaining amount (this is already calculated in invoice_list)
                remaining = invoice.get('remaining', invoice.get('ttc', 0))
                
                invoice_data = {
                    'nfacture': invoice.get('id', invoice.get('nfacture', '')),
                    'ttc': invoice.get('amount', invoice.get('ttc', 0)),
                    'timbre': invoice.get('timbre', 1.0),
                    'client': invoice.get('fournisseur', invoice.get('client', 'N/A')),
                    'remaining': remaining,
                    'paid': invoice.get('paid', 0)
                }
                invoices_data.append(invoice_data)
            
            result = show_enhanced_multiple_payment_dialog(self, invoices_data, is_achat=False,
                                                         payment_service=getattr(self, 'payment_service', None),
                                                         bank_service=getattr(self, 'bank_service', None),
                                                         retenu_service=getattr(self, 'retenu_service', None))
            
            if result:
                # Refresh the view after successful payment
                self._load_rows()
                
                # Show simple success message
                success_msg = f"Paiement multiple enregistré avec succès!\n\n"
                success_msg += f"✅ {len(invoices_data)} factures traitées\n"
                success_msg += f"� La page a été actualisée automatiquement\n"
                
                messagebox.showinfo("Succès", success_msg)
                
        except ImportError:
            messagebox.showerror("Erreur", "Module de paiement multiple non disponible")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du paiement multiple: {e}")

    def _on_generate(self):
        """
        Generate or regenerate facture.
        - If a row is selected, regenerate that facture.
        - Otherwise, ask user for facture number and try to generate it.
        """
        # Check permission first
        if not check_ui_permission("factures", "create"):
            messagebox.showerror("Permission refusée", "Vous n'avez pas la permission de générer des factures.")
            return
            
        nfacture = self._selected_nfacture_int()
        if nfacture is None:
            s = simpledialog.askstring("N° Facture",
                                       "Entrer le N° facture complet (ex : 202500031) :")
            if not s:
                return
            try:
                nfacture = int(s)
            except ValueError:
                messagebox.showerror("Erreur", "Format du numéro invalide.")
                return

        try:
            path = None
            
            # ✅ PHASE 2I MIGRATION: Use FactureService for invoice regeneration
            if hasattr(self, 'container') and self.container:
                try:
                    facture_service = self.container.get('facture_service')
                    if facture_service and hasattr(facture_service, 'regenerate_invoice'):
                        path = facture_service.regenerate_invoice(nfacture)
                        print(f"[VENTE] FactureService regeneration result: {path}")
                    else:
                        print("[VENTE] FactureService not available or missing regenerate_invoice method")
                        path = None
                except Exception as service_error:
                    print(f"[VENTE] FactureService regeneration failed: {service_error}")
                    path = None
            
            # Fallback to SalesService if FactureService failed
            if path is None and self.sales_service:
                try:
                    if hasattr(self.sales_service, 'regenerate_invoice'):
                        path = self.sales_service.regenerate_invoice(str(nfacture))
                        print(f"[VENTE] SalesService regeneration result: {path}")
                    else:
                        print("[VENTE] SalesService doesn't have regenerate_invoice method")
                except Exception as e:
                    print(f"[VENTE] SalesService regeneration failed: {e}")
                    path = None
                        
        except Exception as e:
            print(f"[VENTE] General regeneration error: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la génération: {e}")
            return

        if path and os.path.exists(path):
            messagebox.showinfo("Succès", f"Facture générée avec succès !\n\nFichier: {os.path.basename(path)}")
            # Try to open the generated file
            try:
                import subprocess
                subprocess.Popen(['start', '', path], shell=True)
            except Exception:
                pass
            self._load_rows()
        else:
            messagebox.showerror("Erreur", "Erreur lors de la génération de la facture.\nVérifiez les données de la facture et réessayez.")

    # ============ TEMP FULL EDIT FEATURE ============
    def _on_full_edit(self):
        """Open a temporary full-edit dialog for selected vente (all columns)."""
        nfacture = self._selected_nfacture_int()
        if nfacture is None:
            messagebox.showwarning("Sélection", "Choisissez une facture à modifier (Edition Totale).")
            return
        try:
            import sqlite3
            with sqlite3.connect(get_db_path()) as conn:
                conn.row_factory = sqlite3.Row
                row = conn.execute("SELECT * FROM ventes WHERE nfacture = ? LIMIT 1", (nfacture,)).fetchone()
                if not row:
                    messagebox.showerror("Erreur", "Facture introuvable.")
                    return
                data = dict(row)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lecture DB: {e}")
            return
        FullEditDialog(self, nfacture, data)
        try:
            self._load_rows()
        except Exception:
            pass

class FullEditDialog:
    """Temporary dialog to edit all vente columns directly (maintenance tool)."""
    IMMUTABLE = {"nfacture"}

    def __init__(self, parent: VentePage, nfacture: int, data: Dict):
        self.parent = parent
        self.nfacture = nfacture
        self.data = data
        self.window = tk.Toplevel(parent)
        self.window.title(f"Edition Totale Facture {nfacture}")
        self.window.geometry("860x600")
        self.window.grab_set()
        self._build()
        self.window.transient(parent)
        parent.wait_window(self.window)

    def _build(self):
        tk.Label(self.window, text="Mode maintenance TEMPORAIRE – Modifier avec prudence. Sauvegarde DB recommandée.", fg="#dc3545").pack(pady=6)
        container = tk.Frame(self.window)
        container.pack(fill="both", expand=True)
        canvas = tk.Canvas(container, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        inner = tk.Frame(canvas)
        inner.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=inner, anchor="nw")
        canvas.configure(yscrollcommand=vsb.set)
        canvas.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")
        self.entries: Dict[str, tk.Entry] = {}
        row_idx = 0
        for col, value in sorted(self.data.items()):
            tk.Label(inner, text=col, anchor="w").grid(row=row_idx, column=0, sticky="w", padx=6, pady=3)
            state = "disabled" if col in self.IMMUTABLE else "normal"
            ent = tk.Entry(inner, width=42, state=state)
            if isinstance(value, (int, float)):
                try:
                    ent.insert(0, f"{float(value):.3f}")
                except Exception:
                    ent.insert(0, str(value))
            else:
                ent.insert(0, "" if value is None else str(value))
            ent.grid(row=row_idx, column=1, sticky="w", padx=6, pady=3)
            self.entries[col] = ent
            row_idx += 1
        btn_frame = tk.Frame(self.window)
        btn_frame.pack(fill="x", pady=8)
        tk.Button(btn_frame, text="Enregistrer", bg="#28a745", fg="white", command=self._save).pack(side="right", padx=8)
        tk.Button(btn_frame, text="Fermer", command=self.window.destroy).pack(side="right")

    def _save(self):
        updated = {}
        for col, ent in self.entries.items():
            if col in self.IMMUTABLE:
                continue
            val = ent.get().strip()
            orig = self.data.get(col)
            if isinstance(orig, (int, float)):
                # attempt float conversion
                try:
                    if val == "":
                        val = 0
                    val = float(val.replace(",", "."))
                except Exception:
                    pass
            updated[col] = val
        if not updated:
            messagebox.showinfo("Info", "Aucun changement.")
            return
        try:
            import sqlite3
            with sqlite3.connect(get_db_path()) as conn:
                cur = conn.cursor()
                set_clause = ", ".join(f"{k} = ?" for k in updated.keys())
                params = list(updated.values())
                # ensure updated_at tracking
                set_clause += ", updated_at = ?"
                params.append(datetime.now().isoformat())
                params.append(self.nfacture)
                cur.execute(f"UPDATE ventes SET {set_clause} WHERE nfacture = ?", params)
                conn.commit()
            # sync tracking (best-effort)
            try:
                from app.stfoom.services.sync_service import SyncService
                SyncService().add_sync_change("ventes", str(self.nfacture), {"mode": "temp_full_edit", "fields": list(updated.keys()), "updated_at": datetime.now().isoformat()}, "update")
            except Exception as se:
                print(f"[VENTE_FULL_EDIT] Sync warn: {se}")
            messagebox.showinfo("Succès", "Facture mise à jour (Edition Totale).")
            self.window.destroy()
        except Exception as e:
            messagebox.showerror("Erreur", f"Echec mise à jour: {e}")

class PaymentDialog:
    """Dialog for managing all payments for an invoice."""
    def __init__(self, parent, nfacture: int, invoice: Dict, payment_service=None, bank_service=None):
        self.parent = parent
        self.payment_service = payment_service
        self.bank_service = bank_service
        self.nfacture = nfacture
        self.invoice = invoice
        self.result = None
        self.paiements = self.payment_service.get_paiements_facture(nfacture) if hasattr(self, 'payment_service') else []
        self.montant_total = invoice.get('ttc', 0)
        self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
        self.window = tk.Toplevel(parent)
        self.window.title(f"Paiements - Facture {nfacture}")
        self.window.geometry("650x700")
        self.window.grab_set()
        self.window.resizable(True, True)
        self._create_ui()
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
        # --- Info Facture ---
        info_frame = tk.LabelFrame(scrollable_frame, text="Informations Facture")
        info_frame.pack(fill="x", padx=10, pady=10)
        
        tk.Label(info_frame, text=f"Facture: {self.nfacture}").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Client: {self.invoice.get('client', '')}").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Montant Total (TTC): {self.montant_total:.3f} TND").pack(anchor="w", padx=5, pady=2)
        
        # 🔧 UNIFIED PAYMENT SYSTEM: Show timbre and retenu base info
        timbre_amount = self.invoice.get('timbre', 1.0)
        retenu_base = max(0, self.montant_total - timbre_amount)
        tk.Label(info_frame, text=f"Timbre: {timbre_amount:.3f} TND").pack(anchor="w", padx=5, pady=2)
        tk.Label(info_frame, text=f"Base Retenu (TTC - Timbre): {retenu_base:.3f} TND", 
                font=('Arial', 9, 'bold'), fg='#2E7D32').pack(anchor="w", padx=5, pady=2)
        # --- Paiements existants ---
        pay_frame = tk.LabelFrame(scrollable_frame, text="Paiements enregistrés")
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
        
        # ADD MULTIPLE PAYMENT HISTORY SECTION
        self._create_multiple_payment_history_section(scrollable_frame)
        
        btns = tk.Frame(pay_frame)
        btns.pack(pady=4)
        tk.Button(btns, text="Ajouter un paiement", command=self._add_payment, bg="#007bff", fg="white").pack(side="left", padx=4)
        tk.Button(btns, text="Fermer", command=self._cancel).pack(side="left", padx=4)
        # Add a visible delete button for selected payment
        self.delete_btn = tk.Button(btns, text="Supprimer le paiement", command=self._delete_selected_payment, bg="#dc3545", fg="white", state="disabled")
        self.delete_btn.pack(side="left", padx=4)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        reste_frame = tk.Frame(scrollable_frame)
        reste_frame.pack(fill="x", padx=10, pady=6)
        tk.Label(reste_frame, text="Reste à payer (modifiable):").pack(side="left")
        self.reste_var = tk.StringVar(value=f"{self.reste:.3f}")
        self.reste_entry = tk.Entry(reste_frame, textvariable=self.reste_var, width=10)
        self.reste_entry.pack(side="left", padx=5)
        # --- Button section (always visible at bottom) ---
        btn_frame = ttk.Frame(self.window)
        btn_frame.pack(fill="x", pady=(10, 0), side="bottom")
        close_btn = tk.Button(btn_frame, text="Fermer", command=self._cancel,
                              bg="#9E9E9E", fg="white", font=('Arial', 10),
                              relief="flat", padx=30, pady=8)
        close_btn.pack(side="right", padx=(0, 10))
    def _refresh_tree(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        for p in self.paiements:
            banque_nom = ""
            if p['methode_paiement'] == 'banque' and p.get('banque_id'):
                banques = self.bank_service.get_banques() if hasattr(self, 'bank_service') else []
                for b in banques:
                    if b['id'] == p['banque_id']:
                        # Handle both 'nom' and 'nom_banque' field names
                        banque_nom = b.get('nom_banque', b.get('nom', 'Unknown Bank'))
                        break
            # Check if this is a multiple payment for better display
            notes_display = p.get('notes', '')
            method_display = self.payment_service.format_payment_method(p['methode_paiement'], p.get('mode_paiement', '')) if hasattr(self, 'payment_service') else f"{p['methode_paiement']} - {p.get('mode_paiement', '')}"
            
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
        if col == "#9":  # Actions column
            menu = tk.Menu(self.window, tearoff=0)
            menu.add_command(label="Modifier", command=lambda: self._edit_payment(item))
            menu.add_command(label="Supprimer", command=lambda: self._delete_payment(item))
            menu.tk_popup(event.x_root, event.y_root)

    def _create_multiple_payment_history_section(self, parent):
        """Create section to show multiple payment history for this invoice"""
        try:
            # Query for multiple payments involving this invoice
            multiple_payments = self._get_multiple_payment_history()
            
            if multiple_payments:
                history_frame = tk.LabelFrame(parent, text="Historique des Paiements Multiples")
                history_frame.pack(fill="x", padx=10, pady=5)
                
                tk.Label(history_frame, text=f"Cette facture a été incluse dans {len(multiple_payments)} paiement(s) multiple(s):", 
                        font=('Arial', 9, 'bold')).pack(anchor="w", padx=5, pady=2)
                
                # Create a small treeview for multiple payment history
                hist_columns = ("date", "total_amount", "invoices", "bank_transaction", "check_number")
                self.history_tree = ttk.Treeview(history_frame, columns=hist_columns, show="headings", height=3)
                
                self.history_tree.heading("date", text="Date")
                self.history_tree.heading("total_amount", text="Montant Total")
                self.history_tree.heading("invoices", text="Factures Incluses")
                self.history_tree.heading("bank_transaction", text="Transaction Banque")
                self.history_tree.heading("check_number", text="N° Chèque")
                
                self.history_tree.column("date", width=100, anchor="center")
                self.history_tree.column("total_amount", width=120, anchor="center")
                self.history_tree.column("invoices", width=150, anchor="w")
                self.history_tree.column("bank_transaction", width=100, anchor="center")
                self.history_tree.column("check_number", width=100, anchor="center")
                
                self.history_tree.pack(fill="x", padx=5, pady=2)
                
                # Populate history
                for mp in multiple_payments:
                    self.history_tree.insert("", "end", values=(
                        mp['date'],
                        f"{mp['total_amount']:.3f} DT",
                        mp['invoices_list'],
                        f"ID: {mp['bank_id']}" if mp['bank_id'] else "N/A",
                        mp['check_number'] or "N/A"
                    ))
                
                # Add info label
                tk.Label(history_frame, text="Double-cliquez sur une ligne pour voir les détails", 
                        font=('Arial', 8), fg='gray').pack(anchor="w", padx=5, pady=2)
                
                self.history_tree.bind("<Double-1>", self._show_multiple_payment_details)
                
        except Exception as e:
            print(f"[PAYMENT_DIALOG] Error creating multiple payment history section: {e}")

    def _get_multiple_payment_history(self):
        """Get multiple payment history involving this invoice"""
        try:
            multiple_payments = []
            
            if not hasattr(self, 'payment_service'):
                return multiple_payments
                
            with self.payment_service.payment_repository.get_connection() as conn:
                # Find all multiple payment references that include this invoice
                cursor = conn.execute("""
                    SELECT DISTINCT notes, created_at, date_paiement
                    FROM paiements_factures 
                    WHERE nfacture = ? AND notes LIKE '%MULTI-%'
                    ORDER BY created_at DESC
                """, (self.nfacture,))
                
                multi_refs = cursor.fetchall()
                
                for ref_data in multi_refs:
                    notes = ref_data[0]
                    created_at = ref_data[1]
                    date_paiement = ref_data[2]
                    
                    # Extract reference from notes (e.g., MULTI-20250926-105517 or MULTI-20250926-105517-123456)
                    import re
                    ref_match = re.search(r'MULTI-\d{8}-\d{6}(?:-\d{6})?', notes)
                    if not ref_match:
                        continue
                        
                    multi_ref = ref_match.group(0)
                    
                    # Get all payments with this reference
                    cursor.execute("""
                        SELECT nfacture, montant_paye, notes
                        FROM paiements_factures 
                        WHERE notes LIKE ?
                        ORDER BY nfacture
                    """, (f"%{multi_ref}%",))
                    
                    related_payments = cursor.fetchall()
                    
                    if related_payments:
                        # Calculate totals
                        total_amount = sum(p[1] for p in related_payments)
                        invoice_list = [str(p[0]).replace('202500', '') for p in related_payments]  # Remove prefix for display
                        invoices_display = "/".join(invoice_list)
                        
                        # Find related bank transaction
                        cursor.execute("""
                            SELECT id, numero_cheque
                            FROM transactions_bancaires 
                            WHERE ABS(montant - ?) < 0.01 
                            AND date_transaction = ?
                            AND description LIKE '%MULTI-PAIEMENT%'
                            ORDER BY created_at DESC
                            LIMIT 1
                        """, (total_amount, date_paiement))
                        
                        bank_result = cursor.fetchone()
                        bank_id = bank_result[0] if bank_result else None
                        check_number = bank_result[1] if bank_result else None
                        
                        multiple_payments.append({
                            'reference': multi_ref,
                            'date': date_paiement,
                            'total_amount': total_amount,
                            'invoices_list': invoices_display,
                            'bank_id': bank_id,
                            'check_number': check_number,
                            'created_at': created_at
                        })
            
            return multiple_payments
            
        except Exception as e:
            print(f"[PAYMENT_DIALOG] Error getting multiple payment history: {e}")
            return []

    def _show_multiple_payment_details(self, event):
        """Show details of a selected multiple payment"""
        try:
            selection = self.history_tree.selection()
            if not selection:
                return
                
            item = self.history_tree.item(selection[0])
            values = item['values']
            
            # Extract details
            date = values[0]
            total_amount = values[1]
            invoices = values[2]
            bank_transaction = values[3]
            check_number = values[4]
            
            # Show detailed info dialog
            detail_msg = (f"Détails du Paiement Multiple\n"
                        f"==========================\n\n"
                        f"Date: {date}\n"
                        f"Montant Total: {total_amount}\n"
                        f"Factures Incluses: {invoices}\n"
                        f"Transaction Bancaire: {bank_transaction}\n"
                        f"Numéro de Chèque: {check_number}\n\n"
                        f"Cette transaction a regroupé plusieurs factures\n"
                        f"en un seul paiement pour simplifier la gestion.")
            
            messagebox.showinfo("Détails du Paiement Multiple", detail_msg)
            
        except Exception as e:
            print(f"[PAYMENT_DIALOG] Error showing multiple payment details: {e}")
            messagebox.showerror("Erreur", f"Impossible d'afficher les détails: {e}")
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
        payment_details = next((p for p in self.paiements if str(p['id']) == str(item_id)), None)
        
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
            # Remove corresponding bank transaction if exists
            paiement = payment_details
            if paiement and paiement['methode_paiement'] == 'banque' and 'reference_paiement' in paiement:
                # Bank operations now handled by BankService
                # Try to find and delete the bank transaction by reference and amount
                transactions = self.bank_service.get_transactions() if hasattr(self, 'bank_service') else []
                for t in transactions:
                    if t.get('nfacture') == self.nfacture and t.get('numero_cheque') == paiement['reference_paiement'] and abs(t.get('montant', 0) - paiement['montant_paye']) < 0.01:
                        if hasattr(self, 'bank_service'):
                            self.bank_service.delete_transaction(t['id'])
                        break
            if hasattr(self, 'payment_service'):
                self.payment_service.supprimer_paiement(int(item_id))
            self.paiements = self.payment_service.get_paiements_facture(self.nfacture) if hasattr(self, 'payment_service') else []
            self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
            self.reste_var.set(f"{self.reste:.3f}")
            self._refresh_tree()
            self.result = True
            # Force refresh the parent vente page
            if hasattr(self.parent, '_load_rows'):
                self.parent._load_rows()
                
            # Show success message
            if is_multiple:
                messagebox.showinfo("Succès", "Paiement multiple supprimé avec succès!\nTous les paiements associés ont été supprimés.")
            else:
                messagebox.showinfo("Succès", "Paiement supprimé avec succès!")
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
            print(f"[VENTE_PAGE] Error deleting payment {item_id}: {e}")
    def _payment_form(self, preset=None):
        form = tk.Toplevel(self.window)
        form.title("Ajouter un paiement" if not preset else "Modifier le paiement")
        form.geometry("500x650")
        form.grab_set()
        # Step 1: Caisse or Banque
        type_var = tk.StringVar(value=preset['methode_paiement'] if preset else "banque")
        tk.Label(form, text="Type de paiement:").pack(anchor="w", padx=10, pady=4)
        tk.Radiobutton(form, text="🏦 Banque", variable=type_var, value="banque", command=lambda: update_fields()).pack(anchor="w", padx=20)
        tk.Radiobutton(form, text="💰 Caisse", variable=type_var, value="caisse", command=lambda: update_fields()).pack(anchor="w", padx=20)
        # Dedicated frame for bank/method widgets
        bank_options_frame = tk.Frame(form)
        bank_options_frame.pack(anchor="w", fill="x", padx=10, pady=2)
        bank_var = tk.StringVar()
        method_var = tk.StringVar()
        banques = self.bank_service.get_banques() if hasattr(self, 'bank_service') else []
        # Fix: Use consistent field names and handle missing fields safely
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
        payment_methods = self.bank_service.get_payment_methods() if hasattr(self, 'bank_service') else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
        method_combo = ttk.Combobox(bank_options_frame, textvariable=method_var, state="readonly", width=30, values=[label for _, label in payment_methods])
        echeance_var = tk.StringVar(value=datetime.strptime(preset['echeance'], "%Y-%m-%d").strftime("%d/%m/%Y") if preset and preset.get('echeance') else "")
        echeance_label = tk.Label(bank_options_frame, text="Échéance (JJ/MM/AAAA, pour traite):")
        echeance_frame = tk.Frame(bank_options_frame)
        echeance_entry = DateEntry(echeance_frame, textvariable=echeance_var, date_pattern="dd/MM/yyyy", width=15)
        echeance_entry.pack(side="left")
        # Numéro field for cheque/traite/virement
        numero_label = tk.Label(bank_options_frame, text="Numéro:")
        numero_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        numero_entry = tk.Entry(bank_options_frame, textvariable=numero_var, width=25)
        # Dynamic field update
        def update_fields():
            for widget in bank_options_frame.winfo_children():
                widget.pack_forget()
            if type_var.get() == "banque":
                bank_combo.pack(anchor="w", padx=0, pady=2)
                method_combo.pack(anchor="w", padx=0, pady=2)
                # Always show numero field
                numero_label.pack(anchor="w", padx=0, pady=2)
                numero_entry.pack(anchor="w", padx=0, pady=2)
                method_idx = None
                try:
                    payment_methods = self.bank_service.get_payment_methods() if hasattr(self, 'bank_service') else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                except Exception:
                    pass
                method_key = payment_methods[method_idx][0] if method_idx is not None and hasattr(self, 'bank_service') else None
                if method_key == "traite":
                    echeance_label.pack(anchor="w", padx=0, pady=2)
                    echeance_frame.pack(anchor="w", padx=0, pady=2)
            # else: nothing in frame
        method_combo.bind("<<ComboboxSelected>>", lambda e: update_fields())
        update_fields()
        # Prefill selections when modifying an existing payment
        if preset:
            try:
                # Set bank/method based on existing payment
                if preset.get('methode_paiement') == 'banque':
                    # Select bank by banque_id
                    if preset.get('banque_id'):
                        preset_bank_id = preset['banque_id']
                        for display_name, bid in banks_dict.items():
                            if bid == preset_bank_id:
                                bank_combo.set(display_name)
                                break
                    # Select method by mode_paiement
                    if preset.get('mode_paiement'):
                        pm_list = self.bank_service.get_payment_methods() if hasattr(self, 'bank_service') else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                        label_map = {k: lbl for k, lbl in pm_list}
                        if preset['mode_paiement'] in label_map:
                            method_combo.set(label_map[preset['mode_paiement']])
                    # Ensure echeance field visibility is correct
                    update_fields()
            except Exception as _e:
                # Safe to ignore prefill issues and keep defaults
                pass
        # Montant
        tk.Label(form, text="Montant payé (TND):").pack(anchor="w", padx=10, pady=4)
        amount_var = tk.StringVar(value=f"{preset['montant_paye']:.3f}" if preset else f"{self.reste:.3f}")
        amount_entry = tk.Entry(form, textvariable=amount_var, width=15)
        amount_entry.pack(padx=10, pady=2)
        # Date paiement
        tk.Label(form, text="Date de paiement (JJ/MM/AAAA):").pack(anchor="w", padx=10, pady=4)
        date_frame = tk.Frame(form)
        date_frame.pack(padx=10, pady=2, anchor="w")
        date_var = tk.StringVar(value=datetime.strptime(preset['date_paiement'], "%Y-%m-%d").strftime("%d/%m/%Y") if preset else datetime.now().strftime("%d/%m/%Y"))
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
            tk.Button(top, text="Valider", command=set_date).pack(pady=5)
        tk.Button(date_frame, text="📅", command=pick_date).pack(side="left", padx=4)
        # Référence (optional, fallback)
        tk.Label(form, text="Référence (optionnel):").pack(anchor="w", padx=10, pady=4)
        ref_var = tk.StringVar(value=preset.get('reference_paiement', '') if preset else "")
        ref_entry = tk.Entry(form, textvariable=ref_var, width=25)
        ref_entry.pack(padx=10, pady=2)
        # Notes
        tk.Label(form, text="Notes (optionnel):").pack(anchor="w", padx=10, pady=4)
        notes_text = tk.Text(form, height=3, width=35)
        if preset:
            notes_text.insert("1.0", preset.get('notes', ''))
        notes_text.pack(padx=10, pady=2)
        # Retenu field with auto-calculation
        retenu_frame = tk.Frame(form)
        retenu_frame.pack(anchor="w", padx=10, pady=2, fill="x")
        
        tk.Label(form, text="Retenu (%):").pack(anchor="w", padx=10, pady=4)
        retenu_var = tk.StringVar(value="0")
        retenu_entry = tk.Entry(retenu_frame, textvariable=retenu_var, width=10)
        retenu_entry.pack(side="left", padx=(0, 10))
        
        # 🔧 EDITABLE retenu amount (user can modify)
        tk.Label(retenu_frame, text="Montant retenu:").pack(side="left", padx=(10, 5))
        retenu_amount_var = tk.StringVar(value="0.000")
        retenu_amount_entry = tk.Entry(retenu_frame, textvariable=retenu_amount_var, 
                                      width=12, bg="white")
        retenu_amount_entry.pack(side="left")
        
        # Add "TND" label
        tk.Label(retenu_frame, text="TND").pack(side="left", padx=(2, 0))
        
        # Auto-calculation function
        def calculate_retenu_from_percent(*args):
            """Calculate retenu amount from percentage"""
            try:
                # 🔧 UNIFIED PAYMENT SYSTEM: Use timbre-excluded retenu base
                # Get the base amount (TTC - timbre for retenu calculation)
                ttc_amount = self.montant_total
                timbre_amount = self.invoice.get('timbre', 1.0)  # Get timbre from invoice
                
                # Calculate retenu base excluding timbre (like unified system)
                retenu_base = max(0, ttc_amount - timbre_amount)
                
                # Use remaining amount for actual payment calculation
                remaining_amount = self.reste
                
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
                
                # 🔧 UNIFIED PAYMENT SYSTEM: Calculate retenu on timbre-excluded base
                # Retenu is calculated on (TTC - timbre) but payment is on remaining amount
                retenu_amount = retenu_base * retenu_percent / 100.0
                net_payment = remaining_amount - retenu_amount
                
                # Ensure net payment doesn't go negative
                if net_payment < 0:
                    net_payment = 0
                    retenu_amount = remaining_amount
                
                # Update display fields
                retenu_amount_var.set(f"{retenu_amount:.3f}")
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation: {e}")
                retenu_amount_var.set("0.000")
        
        def calculate_retenu_from_amount(*args):
            """Calculate retenu percentage from amount"""
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
                
                # Calculate retenu base excluding timbre
                ttc_amount = self.montant_total
                timbre_amount = self.invoice.get('timbre', 1.0)
                retenu_base = max(0, ttc_amount - timbre_amount)
                
                # Calculate percentage
                if retenu_base > 0:
                    retenu_percent = (retenu_amount / retenu_base) * 100.0
                else:
                    retenu_percent = 0.0
                
                # Update percentage (but don't trigger the percentage callback)
                retenu_var.trace_remove("write", percent_trace_id)
                retenu_var.set(f"{retenu_percent:.2f}")
                retenu_var.trace_add("write", calculate_retenu_from_percent)
                
                # Update net payment
                remaining_amount = self.reste
                net_payment = remaining_amount - retenu_amount
                if net_payment < 0:
                    net_payment = 0
                
                amount_var.set(f"{net_payment:.3f}")
                
            except Exception as e:
                print(f"Error in retenu calculation from amount: {e}")
        
        # Bind the calculations to field changes
        percent_trace_id = retenu_var.trace_add("write", calculate_retenu_from_percent)
        retenu_amount_var.trace_add("write", calculate_retenu_from_amount)
        # Save button
        def save_payment():
            try:
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
                    if montant > 1000000:  # 1 million DT
                        if not messagebox.askyesno("Confirmation", 
                            f"Le montant est élevé ({montant:.3f} DT). Continuer ?"):
                            return
                except ValueError:
                    messagebox.showerror("Erreur", "Montant invalide (doit être un nombre).")
                    return
                
                # Validate retenu percentage
                retenu_text = retenu_var.get().strip()
                if not retenu_text:
                    retenu_percent = 0.0
                else:
                    try:
                        retenu_percent = float(retenu_text.replace(",", "."))
                        if retenu_percent < 0 or retenu_percent > 100:
                            messagebox.showerror("Erreur", "Le pourcentage de retenu doit être entre 0 et 100.")
                            return
                    except ValueError:
                        messagebox.showerror("Erreur", "Pourcentage de retenu invalide.")
                        return
                # Validate retenu amount (user-editable)
                retenu_amount_text = retenu_amount_var.get().strip()
                if not retenu_amount_text:
                    retenu_amount = 0.0
                else:
                    try:
                        retenu_amount = float(retenu_amount_text.replace(",", "."))
                        if retenu_amount < 0:
                            messagebox.showerror("Erreur", "Le montant de retenu ne peut pas être négatif.")
                            return
                    except ValueError:
                        messagebox.showerror("Erreur", "Montant de retenu invalide.")
                        return
                
                # ✅ FIX: The 'montant' field already contains the net payment amount
                # (calculated as remaining_amount - retenu_amount in the UI)
                # So we should use it directly, not subtract retenu_amount again!
                montant_net = montant
                
                # DEBUG: Log the fixed calculation
                print(f"[PAYMENT_DIALOG] Fixed payment calculation:")
                print(f"  montant (already net): {montant}")
                print(f"  retenu_amount (for records): {retenu_amount}")  
                print(f"  montant_net (final): {montant_net}")
                
                # Validate that net payment is reasonable
                if montant_net < 0:
                    messagebox.showerror("Erreur", "Le montant net ne peut pas être négatif. Réduisez le montant de retenu.")
                    return
                
                # Validate payment date
                date_text = date_var.get().strip()
                if not date_text:
                    messagebox.showerror("Erreur", "La date de paiement est obligatoire.")
                    return
                    
                try:
                    date_str = datetime.strptime(date_text, "%d/%m/%Y").strftime("%Y-%m-%d")
                    # Check if date is not in the future (allow today)
                    payment_date = datetime.strptime(date_text, "%d/%m/%Y").date()
                    if payment_date > datetime.now().date():
                        if not messagebox.askyesno("Confirmation", 
                            "La date de paiement est dans le futur. Continuer ?"):
                            return
                except ValueError:
                    messagebox.showerror("Erreur", "Format de date invalide (JJ/MM/AAAA).")
                    return
                
                # Validate échéance if provided
                echeance_str = echeance_var.get().strip()
                echeance_db = ''
                if echeance_str:
                    try:
                        echeance_db = datetime.strptime(echeance_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                        # For traite, échéance should be in the future
                        # For chèque, échéance can be any date (past, present, or future)
                        echeance_date = datetime.strptime(echeance_str, "%d/%m/%Y").date()
                        method_key = None
                        try:
                            payment_methods = self.bank_service.get_payment_methods() if hasattr(self, 'bank_service') else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                            method_idx = [label for _, label in payment_methods].index(method_var.get())
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
                
                # Check if payment amount exceeds remaining amount
                if montant_net > self.reste:
                    if not messagebox.askyesno("Confirmation", 
                        f"Le montant ({montant_net:.3f} DT) dépasse le reste à payer ({self.reste:.3f} DT). Continuer ?"):
                        return
                
                # Prepare data
                notes = notes_text.get("1.0", "end").strip()
                
                # Calculate retenu percentage for display/notes (timbre-excluded base)
                ttc_amount = self.montant_total
                timbre_amount = self.invoice.get('timbre', 1.0)
                retenu_base = max(0, ttc_amount - timbre_amount)
                
                if retenu_amount > 0 and retenu_base > 0:
                    retenu_percent = (retenu_amount / retenu_base) * 100.0
                    notes = f"[Retenu: {retenu_percent:.1f}%] " + notes
                else:
                    retenu_percent = 0.0
                
                # Delete old payment if editing
                if preset:
                    self._delete_payment(preset['id'])
                
                # Save payment
                if type_var.get() == 'banque':
                    banque_id = banks_dict[bank_var.get()]
                    payment_methods = self.bank_service.get_payment_methods() if hasattr(self, 'bank_service') else [('virement', 'Virement'), ('cheque', 'Chèque'), ('traite', 'Traite')]
                    method_idx = [label for _, label in payment_methods].index(method_combo.get())
                    method_key = payment_methods[method_idx][0]
                    if hasattr(self, 'payment_service'):
                        self.payment_service.marquer_facture_payee_banque(
                            self.nfacture, montant_net, date_str, ref, notes, 
                            banque_id=banque_id, mode_paiement=method_key, echeance=echeance_db,
                            retenu_percent=retenu_percent, retenu_amount=retenu_amount
                        )
                else:
                    if hasattr(self, 'payment_service'):
                        self.payment_service.marquer_facture_payee_caisse(
                            self.nfacture, montant_net, date_str, ref, notes, 
                            mode_paiement='', echeance='',
                            retenu_percent=retenu_percent, retenu_amount=retenu_amount
                        )
                
                # Update UI
                self.paiements = self.payment_service.get_paiements_facture(self.nfacture) if hasattr(self, 'payment_service') else []
                self.reste = self.montant_total - sum(p['montant_paye'] for p in self.paiements)
                self.reste_var.set(f"{self.reste:.3f}")
                self._refresh_tree()
                self.result = True
                
                # Force refresh the parent vente page
                if hasattr(self.parent, '_load_rows'):
                    self.parent._load_rows()
                    
                form.destroy()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement:\n{str(e)}")
                
        tk.Button(form, text="Enregistrer", command=save_payment, bg="#28a745", fg="white").pack(pady=12)
        # Add a visible delete button if editing an existing payment
        if preset:
            def delete_and_close():
                self._delete_payment(preset['id'])
                form.destroy()
            tk.Button(form, text="Supprimer", command=delete_and_close, bg="#dc3545", fg="white").pack(pady=2)
        tk.Button(form, text="Annuler", command=form.destroy).pack()
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

