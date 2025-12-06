# stfoom/ui/facture_page.py
import tkinter as tk
from tkinter import ttk, messagebox
# from stfoom.logicold import secure_database as db  # DISABLED: migrated to services
# from stfoom.ui.client_selector import create_selector  # DISABLED: has dependency issues
import sys
import os
import traceback
from datetime import datetime
from .shared_widgets import format_money  # Import centralized money formatting

# Import calendar widget
try:
    from tkcalendar import DateEntry
    CALENDAR_AVAILABLE = True
except ImportError:
    print("[FACTURE] tkcalendar not available, using standard date entry")
    CALENDAR_AVAILABLE = False

# ✅ ERROR LOGGING: Comprehensive error catching and logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
try:
    from unified_logger import log_facture_error, log_facture_debug, log_facture_info
    LOGGING_AVAILABLE = True
except ImportError:
    # Try fallback to old logger
    try:
        from facture_error_logger import log_facture_error, log_facture_debug, log_facture_info
        LOGGING_AVAILABLE = True
    except ImportError:
        # Final fallback logging functions
        def log_facture_error(error_type, error_message, context=None, exception=None):
            print(f"🚨 FACTURE ERROR: {error_type} - {error_message}")
            if exception:
                print(f"🚨 Exception: {exception}")
                traceback.print_exc()
            # Also write to error.log directly
            try:
                with open("error.log", "a", encoding="utf-8") as f:
                    f.write(f"\n[FACTURE ERROR] {error_type}: {error_message}\n")
                    if exception:
                        traceback.print_exception(type(exception), exception, exception.__traceback__, file=f)
            except:
                pass
        
        def log_facture_debug(message, context=None):
            print(f"🔍 FACTURE DEBUG: {message}")
        
        def log_facture_info(message, context=None):
            print(f"ℹ️ FACTURE INFO: {message}")
        
        LOGGING_AVAILABLE = False

# ✅ PHASE 2I MIGRATION: Legacy invoice_gen moved to old/facture/
# Service layer handles all invoice generation now

class FacturePage(ttk.Frame):
    """Tkinter page for invoice generation (uses db & logic layers)."""

    def __init__(self, master, container_or_go_home, go_home=None):
        super().__init__(master, style="FactureMain.TFrame")
        self.pack(fill="both", expand=True)
        
        # Create main scrollable canvas for the entire page
        self.main_canvas = tk.Canvas(self, highlightthickness=0)
        self.scrollable_frame = ttk.Frame(self.main_canvas)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.main_canvas.yview)
        self.main_canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.scrollbar.pack(side="right", fill="y")
        self.main_canvas.pack(side="left", fill="both", expand=True)
        self.canvas_window = self.main_canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        
        # Configure scrolling
        def configure_scroll_region(event):
            self.main_canvas.configure(scrollregion=self.main_canvas.bbox("all"))
        self.scrollable_frame.bind("<Configure>", configure_scroll_region)
        
        # Make canvas responsive
        def configure_canvas_width(event):
            canvas_width = event.width
            self.main_canvas.itemconfig(self.canvas_window, width=canvas_width)
        self.main_canvas.bind("<Configure>", configure_canvas_width)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            self.main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.main_canvas.bind("<MouseWheel>", on_mousewheel)
        
        # ✅ PHASE 2I MIGRATION: Support dependency injection following Phase 2H pattern
        if go_home is not None:
            # New signature: FacturePage(parent, di_container, go_home)
            self.di_container = container_or_go_home
            self.go_home = go_home
            self.facture_service = None
            
            # Try to get service from container
            try:
                self.facture_service = self.di_container.get('facture_service')
                print("[FACTURE PAGE] Using FactureService from DI container")
            except Exception as e:
                print(f"[FACTURE PAGE] Could not get FactureService from DI container: {e}")
                self.facture_service = None
        else:
            # Legacy signature: FacturePage(parent, go_home)
            self.go_home = container_or_go_home
            self.facture_service = None
            self.di_container = None
            print("[FACTURE PAGE] Using legacy mode without dependency injection")
        
        # Initialize selected chantier
        self.selected_chantier = ""
        self.chantier_remise_service = None
        
        # ✅ PHASE 2I MIGRATION: Load data via service or fallback to legacy
        if self.facture_service:
            self.clients_df = self.facture_service.get_clients_dataframe()
            self.products_df = self.facture_service.get_products_dataframe()
        else:
            # Legacy fallback with error handling
            try:
                # Simple placeholder data for now using pandas DataFrame
                import pandas as pd
                self.clients_df = pd.DataFrame()  # TODO: Use DocumentService
                self.products_df = pd.DataFrame()  # TODO: Use ProductService
            except Exception as e:
                print(f"[FACTURE PAGE] Legacy data loading failed: {e}")
                # Initialize empty dataframes to prevent errors
                import pandas as pd
                self.clients_df = pd.DataFrame()
                self.products_df = pd.DataFrame()
            
        self.selected_client = {}

        # ---------- header ----------
        header_frame = ttk.Frame(self.scrollable_frame, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Facture – Générateur", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- smart search ----------
        self._setup_smart_search()

        # ---------- client selector ----------
        client_frame = ttk.LabelFrame(self.scrollable_frame, text="Client", style="FactureSection.TLabelframe")
        client_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        
        # ✅ FIXED: Proper client selector with real data loading
        self._setup_client_selector(client_frame)
        
        self.remise_notice = ttk.Label(client_frame, foreground="#c82333", style="FactureRemise.TLabel", justify="left")
        self.remise_notice.pack(pady=5, anchor="w")

        # ---------- chantier ----------
        chantier_frame = ttk.LabelFrame(self.scrollable_frame, text="Chantier & Remises", style="FactureSection.TLabelframe")
        chantier_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        chantier_inner = ttk.Frame(chantier_frame)
        chantier_inner.pack(fill="x", padx=10, pady=5)
        
        # Chantier selection (affects remises)
        ttk.Label(chantier_inner, text="Chantier:", font=("Segoe UI", 12)).pack(side="left")
        
        # Chantier dropdown with existing chantiers
        self._setup_chantier_selector(chantier_inner)
        
        # Button to manage chantier remises
        chantier_manage_btn = ttk.Button(
            chantier_inner,
            text="📋 Gérer Remises",
            command=self._open_chantier_remise_manager
        )
        chantier_manage_btn.pack(side="right", padx=(10, 0))
        
        # Chantier remises notice
        self.chantier_remise_notice = ttk.Label(chantier_frame, foreground="#28a745", style="FactureRemise.TLabel", justify="left")
        self.chantier_remise_notice.pack(pady=5, anchor="w")
        
        # Show next invoice number
        next_invoice_frame = ttk.Frame(chantier_frame)
        next_invoice_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(next_invoice_frame, text="Prochain N° Facture:", font=("Segoe UI", 12)).pack(side="left")
        self.next_invoice_label = ttk.Label(next_invoice_frame, text="", font=("Segoe UI", 12, "bold"), foreground="#27ae60")
        self.next_invoice_label.pack(side="left", padx=10)
        self._update_next_invoice_number()

        # Date selection for invoice
        date_frame = ttk.Frame(chantier_frame)
        date_frame.pack(fill="x", padx=10, pady=5)
        ttk.Label(date_frame, text="Date Facture:", font=("Segoe UI", 12)).pack(side="left")
        
        if CALENDAR_AVAILABLE:
            # Use tkcalendar DateEntry widget with calendar popup
            self.date_entry = DateEntry(
                date_frame,
                width=12,
                background='darkblue',
                foreground='white',
                borderwidth=2,
                date_pattern='dd/mm/yyyy',
                font=("Segoe UI", 10)
            )
            self.date_entry.set_date(datetime.now().date())  # Set to today by default
        else:
            # Fallback to regular Entry with today's date
            self.date_entry = ttk.Entry(date_frame, width=12, font=("Segoe UI", 10))
            self.date_entry.insert(0, datetime.now().strftime('%d/%m/%Y'))
        
        self.date_entry.pack(side="left", padx=10)
        
        # Add a small help text
        ttk.Label(date_frame, text="(dd/mm/yyyy)", font=("Segoe UI", 9), foreground="#666").pack(side="left", padx=5)

        # ---------- product list ----------
        products_frame = ttk.LabelFrame(self.scrollable_frame, text="Produits", style="FactureSection.TLabelframe")
        products_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        if self.products_df.empty:
            ttk.Label(products_frame, text="Aucun produit disponible.", font=("Segoe UI", 12, "italic"), foreground="#c82333").pack(pady=20)
        else:
            # Limit initial render to avoid UI overflow with very large product sets
            MAX_RENDER = 200
            total_products = len(self.products_df)
            if total_products > MAX_RENDER:
                ttk.Label(
                    products_frame,
                    text=f"{total_products} produits trouvés. Affichage limité à {MAX_RENDER}. Utilisez la recherche en haut pour filtrer.",
                    foreground="#555"
                ).pack(pady=(0, 8), anchor="w")
                render_df = self.products_df.head(MAX_RENDER)
            else:
                render_df = self.products_df
            # Scrollable product list
            canvas = tk.Canvas(products_frame, borderwidth=0, height=150, background="#f7f7fa", highlightthickness=0)
            plist = ttk.Frame(canvas, style="FactureProducts.TFrame")
            vsb = ttk.Scrollbar(products_frame, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vsb.set)
            vsb.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            canvas.create_window((0, 0), window=plist, anchor="nw")
            def on_configure(event):
                canvas.configure(scrollregion=canvas.bbox("all"))
            plist.bind("<Configure>", on_configure)
            self.product_vars = {}
            self.qty_entries  = {}
            for idx, (_, row) in enumerate(render_df.iterrows()):
                fr = ttk.Frame(plist, style="FactureProducts.TFrame")
                fr.grid(row=idx, column=0, sticky="ew", pady=2, padx=2)
                code = row["code"]
                var  = tk.IntVar()
                cb = ttk.Checkbutton(fr, text=f"{row['designation']} — {format_money(row['prix_ht'])}", variable=var, style="FactureCheck.TCheckbutton")
                cb.pack(side="left", padx=(0, 8))
                ttk.Label(fr, text="Qté").pack(side="left", padx=4)
                qty = ttk.Entry(fr, width=4)
                qty.insert(0, "1")
                qty.pack(side="left")
                self.product_vars[code] = var
                self.qty_entries[code]  = qty

        # ---------- generate ----------
        # Simple, direct button placement at the bottom
        gen_btn = tk.Button(
            self.scrollable_frame,
            text="✅ GÉNÉRER FACTURE",
            command=self._generate,
            font=("Segoe UI", 22, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2",
            height=2
        )
        gen_btn.pack(side="bottom", pady=30, ipadx=40, ipady=15)

    # ─────────────── client selector setup ───────────────
    def _setup_client_selector(self, parent_frame):
        """Setup the client selection UI with real data."""
        try:
            # Load client data
            if self.facture_service:
                # Use service layer
                all_clients = self.facture_service.get_all_clients()
            else:
                # Fallback to repository layer
                from app.stfoom.data.facture_repository import FactureRepository
                repo = FactureRepository()
                all_clients = repo.get_all_clients()
            
            print(f"[FACTURE] Loaded {len(all_clients)} clients")
            
            # Create client selector UI
            ttk.Label(parent_frame, text="Sélectionner un client:", font=("Segoe UI", 12)).pack(anchor="w", pady=5)
            
            # Client combobox with real data
            client_names = []
            self.clients_data = {}  # Store client data for lookup
            
            for client in all_clients:
                # Build display name (use raison_sociale or nom_client)
                display_name = client.get('raison_sociale', client.get('nom_client', 'Client Sans Nom'))
                client_code = client.get('code_client', '')
                # Fix .0 suffix in client codes
                if isinstance(client_code, float) and client_code.is_integer():
                    client_code = int(client_code)
                full_display = f"{client_code} - {display_name}"
                
                client_names.append(full_display)
                self.clients_data[full_display] = client
            
            # Sort client names
            client_names.sort()
            
            # Create searchable combobox for client selection
            self.client_combo = ttk.Combobox(parent_frame, values=client_names, width=70)
            self.client_combo.pack(pady=5, fill="x", padx=10)
            
            # Enable real-time search functionality
            self.client_combo.configure(state="normal")  # Allow typing
            self.client_combo.bind('<KeyRelease>', self._on_client_search)
            self.client_combo.bind("<<ComboboxSelected>>", self._on_client_combo_selected)
            
            # Store original client list for filtering
            self.all_client_names = client_names.copy()
            
            print(f"[FACTURE] Client selector with real-time search enabled")
            
            # Add client management button
            ttk.Button(
                parent_frame, 
                text="📋 Gérer Clients", 
                command=self._open_client_manager
            ).pack(pady=5)
            
            # Show count
            ttk.Label(
                parent_frame, 
                text=f"{len(all_clients)} client(s) disponible(s)", 
                font=("Segoe UI", 10),
                foreground="#666"
            ).pack(anchor="w", pady=2)
            
        except Exception as e:
            print(f"[FACTURE] Error setting up client selector: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback UI
            ttk.Label(parent_frame, text="Erreur de chargement des clients", foreground="red").pack(pady=10)
            self.client_combo = ttk.Combobox(parent_frame, values=["Erreur de chargement"])
            self.client_combo.pack(pady=5)
            self.clients_data = {}

    def _on_client_combo_selected(self, event=None):
        """Handle client selection from combobox."""
        try:
            selected_display = self.client_combo.get()
            if selected_display and selected_display in self.clients_data:
                client_data = self.clients_data[selected_display]
                self._on_client_selected(client_data)
                print(f"[FACTURE] Selected client: {client_data.get('raison_sociale', 'Unknown')}")
            else:
                self.selected_client = {}
                self._update_remise_notice()
        except Exception as e:
            print(f"[FACTURE] Error in client selection: {e}")
            self.selected_client = {}
            self._update_remise_notice()

    def _on_client_search(self, event=None):
        """Handle real-time client search as user types."""
        try:
            if not hasattr(self, 'all_client_names'):
                return
                
            search_text = self.client_combo.get().lower()
            
            if not search_text:
                # If empty, show all clients
                filtered_clients = self.all_client_names
            else:
                # Filter clients based on search text
                filtered_clients = [
                    client for client in self.all_client_names 
                    if search_text in client.lower()
                ]
            
            # Update combobox values
            self.client_combo.configure(values=filtered_clients)
            
            # Keep the dropdown open if there are results
            if filtered_clients and len(search_text) > 0:
                self.client_combo.event_generate('<Down>')
                
        except Exception as e:
            print(f"[FACTURE] Error in client search: {e}")

    def _open_client_manager(self):
        """Open client management dialog."""
        try:
            from app.stfoom.ui.client_selector import _manager_dialog
            _manager_dialog(self.winfo_toplevel(), self._refresh_client_selector)
        except Exception as e:
            print(f"[FACTURE] Error opening client manager: {e}")
            import traceback
            traceback.print_exc()
            messagebox.showerror(
                "Erreur", 
                f"Impossible d'ouvrir la gestion des clients: {e}"
            )

    def _refresh_client_selector(self):
        """Refresh the client selector dropdown after client data changes."""
        try:
            # Reload client data
            if self.facture_service:
                # Use service layer
                all_clients = self.facture_service.get_all_clients()
            else:
                # Fallback to repository layer
                from app.stfoom.data.facture_repository import FactureRepository
                repo = FactureRepository()
                all_clients = repo.get_all_clients()
            
            print(f"[FACTURE] Refreshed client list: {len(all_clients)} clients")
            
            # Update client dropdown values
            client_names = []
            self.clients_data = {}  # Reset client data lookup
            
            for client in all_clients:
                # Build display name (use raison_sociale or nom_client)
                display_name = client.get('raison_sociale', client.get('nom_client', 'Client Sans Nom'))
                client_code = client.get('code_client', '')
                # Fix .0 suffix in client codes
                if isinstance(client_code, float) and client_code.is_integer():
                    client_code = int(client_code)
                full_display = f"{client_code} - {display_name}"
                
                client_names.append(full_display)
                self.clients_data[full_display] = client
            
            # Update combobox values
            if hasattr(self, 'client_combo') and self.client_combo:
                current_selection = self.client_combo.get()
                self.client_combo['values'] = client_names
                
                # Try to maintain selection if it still exists
                if current_selection not in client_names:
                    self.client_combo.set("")
                    self.selected_client = {}
                    self._update_remise_notice()
                
        except Exception as e:
            print(f"[FACTURE] Error refreshing client selector: {e}")

    def _setup_chantier_selector(self, parent_frame):
        """Setup the chantier selection dropdown."""
        try:
            # Initialize chantier remise service
            from stfoom.services.chantier_remise_service import ChantierRemiseService
            self.chantier_remise_service = ChantierRemiseService()
            
            # Create chantier dropdown (initially empty - will be populated when client is selected)
            self.chantier_combo = ttk.Combobox(parent_frame, values=[], width=60, state="disabled")
            self.chantier_combo.pack(side="left", padx=10)
            
            # Bind selection event
            self.chantier_combo.bind("<<ComboboxSelected>>", self._on_chantier_selected)
            
            # Add placeholder text
            self.chantier_combo.set("Sélectionnez d'abord un client...")
            
            print("[FACTURE] Chantier selector setup complete (client-specific)")
            
        except Exception as e:
            print(f"[FACTURE] Error setting up chantier selector: {e}")
            # Fallback to simple entry
            self.chantier_combo = ttk.Entry(parent_frame, width=60)
            self.chantier_combo.pack(side="left", padx=10)

    def _on_chantier_selected(self, event=None):
        """Handle chantier selection and update remise information."""
        try:
            selected_chantier = self.chantier_combo.get()
            self.selected_chantier = selected_chantier
            
            if self.chantier_remise_service and selected_chantier:
                # Update chantier remise notice
                discount_messages = self.chantier_remise_service.calculate_chantier_discounts(
                    selected_chantier, self.products_df
                )
                
                if discount_messages:
                    self.chantier_remise_notice.config(
                        text=f"Remises chantier '{selected_chantier}':\n" + "\n".join(discount_messages)
                    )
                else:
                    self.chantier_remise_notice.config(
                        text=f"Chantier '{selected_chantier}' - Aucune remise configurée"
                    )
            else:
                self.chantier_remise_notice.config(text="")
                
        except Exception as e:
            print(f"[FACTURE] Error handling chantier selection: {e}")

    def _open_chantier_remise_manager(self):
        """Open chantier remise management dialog."""
        try:
            if not self.selected_client:
                from tkinter import messagebox
                messagebox.showwarning("Attention", "Veuillez sélectionner un client d'abord")
                return
                
            # Define refresh callback to update chantier selector
            def refresh_chantiers():
                if hasattr(self, 'chantier_combo') and self.selected_client:
                    self._update_chantier_selector_for_client(self.selected_client)
                
            from stfoom.ui.chantier_remise_dialog import ChantierRemiseDialog
            dialog = ChantierRemiseDialog(self.winfo_toplevel(), 
                                        client_data=self.selected_client,
                                        refresh_callback=refresh_chantiers)
            dialog.show()
                
        except Exception as e:
            print(f"[FACTURE] Error opening chantier remise manager: {e}")
            messagebox.showerror(
                "Erreur", 
                f"Impossible d'ouvrir la gestion des remises: {e}"
            )

    # ─────────────── helper callbacks ───────────────

    def _setup_smart_search(self):
        """Setup the smart search widget for the facture page."""
        try:
            from .smart_search import create_smart_search
            
            # Create facture-specific search providers
            def search_factures(query):
                """Search in factures database."""
                results = []
                try:
                    if self.facture_service:
                        # Use service to search factures
                        factures = self.facture_service.search_factures(query)
                        for facture in factures[:20]:  # Limit results
                            results.append({
                                'type': 'Facture',
                                'content': f"Facture #{facture.get('numero', 'N/A')} - {facture.get('client', 'Client inconnu')}",
                                'details': f"Montant: {facture.get('total_ttc', 0):.3f} TND - {facture.get('date', 'Date inconnue')}",
                                'data': facture,
                                'callback': lambda f=facture: self._load_facture_from_search(f)
                            })
                    else:
                        # Fallback search (placeholder)
                        results.append({
                            'type': 'Facture',
                            'content': f"Recherche de factures: '{query}'",
                            'details': "Service facture non disponible",
                            'data': {'query': query}
                        })
                except Exception as e:
                    print(f"[SMART_SEARCH] Error searching factures: {e}")
                return results
            
            def search_products(query):
                """Search in products database."""
                results = []
                try:
                    if not self.products_df.empty:
                        query_lower = query.lower()
                        # Search in product name and reference
                        mask = (
                            self.products_df['designation'].str.lower().str.contains(query_lower, na=False) |
                            self.products_df['reference'].astype(str).str.lower().str.contains(query_lower, na=False)
                        )
                        
                        for _, product in self.products_df[mask].head(15).iterrows():
                            results.append({
                                'type': 'Produit',
                                'content': f"{product['reference']} - {product['designation']}",
                                'details': f"Prix: {product.get('prix_unitaire', 0):.3f} TND - Stock: {product.get('stock', 'N/A')}",
                                'data': product.to_dict(),
                                'callback': lambda p=product.to_dict(): self._add_product_from_search(p)
                            })
                except Exception as e:
                    print(f"[SMART_SEARCH] Error searching products: {e}")
                return results
            
            # Additional search providers specific to facture
            additional_providers = {
                'factures': search_factures,
                'products': search_products
            }
            
            # Create smart search widget
            self.smart_search = create_smart_search(self.scrollable_frame, additional_providers)
            
            print("[FACTURE] Smart search setup complete")
            
        except Exception as e:
            print(f"[FACTURE] Error setting up smart search: {e}")
            # Create placeholder label if smart search fails
            placeholder = ttk.Label(self.scrollable_frame, text="🔍 Recherche intelligente temporairement indisponible", foreground='gray')
            placeholder.pack(pady=10)

    def _load_facture_from_search(self, facture_data):
        """Load a facture from search results."""
        try:
            print(f"[FACTURE] Loading facture from search: {facture_data}")
            # Here you would implement loading the facture data into the form
            # This is a placeholder for now
            from tkinter import messagebox
            messagebox.showinfo("Info", f"Chargement de la facture: {facture_data.get('numero', 'N/A')}")
        except Exception as e:
            print(f"[FACTURE] Error loading facture from search: {e}")

    def _add_product_from_search(self, product_data):
        """Add a product from search results to the current facture."""
        try:
            print(f"[FACTURE] Adding product from search: {product_data.get('designation', 'N/A')}")
            # Here you would implement adding the product to the current facture
            # This is a placeholder for now
            from tkinter import messagebox
            messagebox.showinfo("Info", f"Ajout du produit: {product_data.get('designation', 'N/A')}")
        except Exception as e:
            print(f"[FACTURE] Error adding product from search: {e}")

    def _on_client_selected(self, client_data: dict):
        self.selected_client = client_data
        self._update_remise_notice()
        self._update_chantier_selector_for_client(client_data)

    def _update_chantier_selector_for_client(self, client_data: dict):
        """Update chantier selector with client-specific chantiers."""
        try:
            if not hasattr(self, 'chantier_combo') or not hasattr(self, 'chantier_remise_service'):
                return
                
            client_code = client_data.get('code_client')
            if not client_code:
                return
                
            # Get chantiers for this specific client
            client_chantiers = self.chantier_remise_service.get_client_chantiers(client_code)
            
            # Update combobox values
            self.chantier_combo.configure(values=client_chantiers, state="readonly")
            
            if client_chantiers:
                # If client has only one chantier, auto-select it
                if len(client_chantiers) == 1:
                    self.chantier_combo.set(client_chantiers[0])
                    self._on_chantier_selected()  # Trigger selection event
                else:
                    self.chantier_combo.set("Choisir un chantier...")
                print(f"[FACTURE] Loaded {len(client_chantiers)} chantiers for client {client_code}")
            else:
                # No chantiers for this client
                self.chantier_combo.configure(values=[], state="disabled")
                self.chantier_combo.set("Aucun chantier pour ce client")
                print(f"[FACTURE] No chantiers found for client {client_code}")
                
        except Exception as e:
            print(f"[FACTURE] Error updating chantier selector: {e}")
            if hasattr(self, 'chantier_combo'):
                self.chantier_combo.configure(values=[], state="disabled")
                self.chantier_combo.set("Erreur chargement chantiers")

    def _update_remise_notice(self):
        if not self.selected_client:
            self.remise_notice.config(text="")
            return
        
        # Show client-based remises (legacy) as information only
        legacy_messages = []
        
        # ✅ PHASE 2I MIGRATION: Use service or fallback to legacy logic
        if self.facture_service:
            discount_messages = self.facture_service.calculate_client_discount(
                self.selected_client, self.products_df
            )
            if discount_messages:
                legacy_messages = [f"[Client] {msg}" for msg in discount_messages]
        else:
            # Legacy logic fallback
            msgs = []
            for _, p in self.products_df.iterrows():
                code_val = p['code']
                # If code_val is a numpy scalar/array, get the Python value
                try:
                    code_str = str(code_val.item())
                except AttributeError:
                    code_str = str(code_val)
                col = f"remise_{code_str.lower()}"
                if col in self.selected_client and self.selected_client[col] and self.selected_client[col] > 0:
                    legacy_messages.append(f"[Client] - {p['designation']}: {int(self.selected_client[col])}%")
        
        # Display warning about legacy client remises
        if legacy_messages:
            legacy_text = "\n".join(legacy_messages) + "\n\n⚠️ Note: Les remises clients sont obsolètes. Utilisez les remises par chantier."
            self.remise_notice.config(text=legacy_text, foreground="#ff6600")  # Orange warning
        else:
            self.remise_notice.config(text="Aucune remise client (système obsolète)", foreground="#888888")  # Gray info
    
    def _update_next_invoice_number(self):
        """Update the display of the next available invoice number."""
        try:
            # Check if the label still exists
            if hasattr(self, 'next_invoice_label') and self.next_invoice_label.winfo_exists():
                # ✅ PHASE 2I MIGRATION: Use service layer
                if self.facture_service:
                    next_number = self.facture_service.get_next_invoice_number()
                    info = self.facture_service.get_invoice_number_info(next_number)
                else:
                    # Service not available - show error message
                    self.next_invoice_label.config(text="Service non disponible")
                    return
                
                if info:
                    self.next_invoice_label.config(text=info["display"])
                else:
                    self.next_invoice_label.config(text="Erreur")
        except Exception as e:
            print(f"[FACTURE] Error getting next invoice number: {e}")
            try:
                if hasattr(self, 'next_invoice_label') and self.next_invoice_label.winfo_exists():
                    self.next_invoice_label.config(text="Erreur")
            except Exception:
                pass

    # ─────────────── generation ───────────────
    def _generate(self):
        """Main invoice generation entry point with comprehensive error logging."""
        try:
            log_facture_info("Invoice generation started", {
                "products_df_empty": self.products_df.empty,
                "clients_df_empty": self.clients_df.empty,
                "selected_client": bool(self.selected_client),
                "facture_service_available": bool(self.facture_service)
            })
            
            # ✅ PHASE 2I MIGRATION: Use service or fallback to legacy logic
            if self.facture_service:
                log_facture_debug("Using FactureService for generation")
                self._generate_with_service()
            else:
                log_facture_debug("Using legacy generation method")
                self._generate_legacy()
                
            log_facture_info("Invoice generation completed successfully")
            
        except Exception as e:
            log_facture_error("GENERATION_FAILED", "Invoice generation failed completely", 
                            {
                                "products_df_empty": self.products_df.empty,
                                "product_vars_count": len(getattr(self, 'product_vars', {})),
                                "qty_entries_count": len(getattr(self, 'qty_entries', {})),
                                "facture_service": bool(getattr(self, 'facture_service', None))
                            }, e)
            
            # Show user-friendly error
            messagebox.showerror("Erreur", 
                f"Erreur lors de la génération de la facture.\n\n"
                f"Détails: {str(e)}\n\n"
                f"Vérifiez le fichier error.log pour plus d'informations.")
            # Do not re-raise here; keep UI responsive and let user correct inputs
            return
    
    def _generate_with_service(self):
        """Generate invoice using FactureService."""
        
        print("[FACTURE DEBUG] === STARTING INVOICE GENERATION ===")
        print(f"[FACTURE DEBUG] Selected client: {self.selected_client}")
        print(f"[FACTURE DEBUG] Products DF shape: {self.products_df.shape}")
        print(f"[FACTURE DEBUG] Products DF empty: {self.products_df.empty}")
        
        # Validate client selection
        if not self.selected_client:
            print("[FACTURE DEBUG] ERROR: No client selected")
            messagebox.showerror("Erreur", "Sélectionnez un client.")
            return
            
        # Get chantier (project)
        chantier = self.chantier_combo.get().strip()
        print(f"[FACTURE DEBUG] Chantier: '{chantier}'")
        
        # Build product selection - handle empty data gracefully
        selection = []
        
        print("[FACTURE DEBUG] Starting product processing...")
        print(f"[FACTURE DEBUG] Product vars available: {hasattr(self, 'product_vars')}")
        print(f"[FACTURE DEBUG] Qty entries available: {hasattr(self, 'qty_entries')}")
        
        if hasattr(self, 'product_vars'):
            print(f"[FACTURE DEBUG] Product vars count: {len(self.product_vars)}")
        if hasattr(self, 'qty_entries'):
            print(f"[FACTURE DEBUG] Qty entries count: {len(self.qty_entries)}")
        
        # Check if we have any products loaded
        if self.products_df.empty:
            print("[FACTURE DEBUG] Products DF is empty!")
            # Try to reload data or show helpful message
            try:
                # from stfoom.logicold.access_control import auth_manager  # DISABLED: migrated
                # Simple auth placeholder
                class auth_manager:
                    @staticmethod
                    def get_current_user(): 
                        return type('User', (), {"username": "admin"})()
                    current_user = type('User', (), {"username": "admin"})()
                if not auth_manager.current_user:
                    # User not logged in - try guest mode or prompt login
                    response = messagebox.askyesno("Connexion Requise", 
                        "Aucun produit chargé. Voulez-vous vous connecter maintenant?")
                    if response:
                        # Trigger login - you might need to call your login function here
                        messagebox.showinfo("Information", "Veuillez vous connecter via le menu principal.")
                    return
                else:
                    # User is logged in but no products - database issue
                    messagebox.showerror("Erreur", "Aucun produit trouvé dans la base de données.")
                    return
            except Exception as e:
                print(f"[FACTURE DEBUG] Error checking auth: {e}")
                messagebox.showerror("Erreur", "Impossible de charger les produits.")
                return
        
        print(f"[FACTURE DEBUG] Processing {len(self.products_df)} products...")
        
        # Process products safely
        for idx, row in self.products_df.iterrows():
            try:
                print(f"[FACTURE DEBUG] Processing product {idx}: {row.to_dict()}")
                
                code = row.get("code", "")
                print(f"[FACTURE DEBUG] Product code: '{code}'")
                
                if not code:
                    print(f"[FACTURE DEBUG] Skipping product with empty code")
                    continue
                    
                # Check if UI controls exist for this product
                if hasattr(self, 'product_vars') and code in self.product_vars:
                    is_selected = self.product_vars[code].get()
                    print(f"[FACTURE DEBUG] Product {code} selected: {is_selected}")
                    if not is_selected:
                        continue
                else:
                    print(f"[FACTURE DEBUG] No UI control for product {code}")
                    continue
                
                # Check quantity entry
                if hasattr(self, 'qty_entries') and code in self.qty_entries:
                    qty_text = self.qty_entries[code].get().strip()
                    print(f"[FACTURE DEBUG] Product {code} qty text: '{qty_text}'")
                    
                    if not qty_text:
                        print(f"[FACTURE DEBUG] Empty quantity for {code}")
                        continue
                        
                    try:
                        qty = int(qty_text)
                        print(f"[FACTURE DEBUG] Product {code} qty: {qty}")
                        if qty <= 0:
                            print(f"[FACTURE DEBUG] Invalid quantity {qty} for {code}")
                            continue
                    except ValueError as ve:
                        print(f"[FACTURE DEBUG] ValueError parsing qty for {code}: {ve}")
                        continue
                else:
                    print(f"[FACTURE DEBUG] No quantity control for product {code}")
                    continue
                
                # Add product to selection
                product_data = {
                    "code": code, 
                    "qty": qty,
                    "prix_ht": row.get('prix_ht', 0),
                    "nom": row.get('nom', ''),
                    "prix_unitaire": row.get('prix_unitaire', 0)
                }
                
                print(f"[FACTURE DEBUG] Adding product to selection: {product_data}")
                selection.append(product_data)
                
            except Exception as e:
                print(f"[FACTURE DEBUG] ERROR processing product {idx}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        print(f"[FACTURE DEBUG] Final selection: {len(selection)} products")
        for i, item in enumerate(selection):
            print(f"[FACTURE DEBUG] Selection {i}: {item}")
        
        # Check if we have any products selected
        if not selection:
            print("[FACTURE DEBUG] No products selected")
            messagebox.showwarning("Aucun Produit", "Veuillez sélectionner au moins un produit avec une quantité.")
            return
        
        # Generate invoice with service
        try:
            print("[FACTURE DEBUG] Calling facture_service.generate_invoice...")
            print(f"[FACTURE DEBUG] Service: {self.facture_service}")
            print(f"[FACTURE DEBUG] Client: {self.selected_client}")
            print(f"[FACTURE DEBUG] Chantier: '{chantier}'")
            print(f"[FACTURE DEBUG] Selection: {selection}")
            
            # Get the selected date from the date entry
            invoice_date = None
            try:
                if CALENDAR_AVAILABLE and hasattr(self.date_entry, 'get_date'):
                    # DateEntry widget - get date object and format it
                    date_obj = self.date_entry.get_date()
                    invoice_date = date_obj.strftime('%d/%m/%Y')
                else:
                    # Regular entry - get the text directly
                    invoice_date = self.date_entry.get().strip()
                    # Validate date format
                    try:
                        datetime.strptime(invoice_date, '%d/%m/%Y')
                    except ValueError:
                        messagebox.showerror("Erreur", "Format de date invalide. Utilisez dd/mm/yyyy")
                        return
                        
                print(f"[FACTURE DEBUG] Invoice date: {invoice_date}")
            except Exception as date_error:
                print(f"[FACTURE DEBUG] Error getting date: {date_error}")
                invoice_date = None  # Use default date
            
            out_path = self.facture_service.generate_invoice(
                self.selected_client, 
                chantier, 
                selection, 
                date_facture=invoice_date
            )
            print(f"[FACTURE DEBUG] SUCCESS: Invoice generated at {out_path}")
            
            messagebox.showinfo("Succès", f"Facture enregistrée :\n{out_path}")
            
            # Update next invoice number after successful generation
            try:
                print("[FACTURE DEBUG] Updating invoice number...")
                self._update_next_invoice_number()
            except Exception as update_error:
                print(f"[FACTURE DEBUG] Error updating invoice number: {update_error}")
                
        except Exception as e:
            print(f"[FACTURE DEBUG] CRITICAL ERROR in generate_invoice: {e}")
            import traceback
            traceback.print_exc()
            
            # Log using unified logger
            log_facture_error("CRITICAL_ERROR", "Critical error in generate_invoice", {
                "client": self.selected_client,
                "chantier": chantier,
                "selection": selection,
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }, e)
            
            # Also write to error.log directly as fallback
            try:
                with open("error.log", "a", encoding="utf-8") as f:
                    f.write(f"\n=== CRITICAL FACTURE ERROR ===\n")
                    f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Error: {e}\n")
                    f.write(f"Client: {self.selected_client}\n")
                    f.write(f"Chantier: {chantier}\n")
                    f.write(f"Selection: {selection}\n")
                    f.write("Traceback:\n")
                    traceback.print_exception(type(e), e, e.__traceback__, file=f)
                    f.write("\n" + "="*50 + "\n")
            except Exception as log_error:
                print(f"[ERROR] Could not write to error.log: {log_error}")
            
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la facture:\n{str(e)}")
            print(f"[FACTURE] Generation error: {e}")
            
        print("[FACTURE DEBUG] === END INVOICE GENERATION ===")
    
    def _generate_legacy(self):
        """Generate invoice using legacy logic (fallback)."""
    def _generate_legacy(self):
        """Generate invoice using legacy logic (fallback)."""
        # Validate client selection
        if not self.selected_client:
            messagebox.showerror("Erreur", "Sélectionnez un client.")
            return
        
        # ✅ AUTHENTICATION FIX: Check if products are loaded  
        if self.products_df.empty:
            messagebox.showerror("Erreur", "Aucun produit disponible. Veuillez vous connecter et réessayer.")
            return
            
        # Validate chantier (project)
        chantier = self.chantier_combo.get().strip()
        if not chantier:
            messagebox.showerror("Erreur", "Choisissez un chantier.")
            return
        if chantier in ["Choisir un chantier...", "Aucun chantier pour ce client"]:
            messagebox.showerror("Erreur", "Veuillez sélectionner un chantier valide.")
            return

        # Validate product selection and quantities
        selection = []
        total_amount = 0.0
        
        for _, p in self.products_df.iterrows():
            try:
                code = p["code"]
                
                # ✅ AUTHENTICATION FIX: Check if product controls exist
                if code not in self.product_vars:
                    print(f"[FACTURE LEGACY] Warning: Product {code} not found in UI controls")
                    continue
                
                if not self.product_vars[code].get():
                    continue
                
                # ✅ AUTHENTICATION FIX: Check if qty controls exist
                if code not in self.qty_entries:
                    print(f"[FACTURE LEGACY] Warning: Quantity control for {code} not found")
                    continue
                    
                # Validate quantity
                qty_text = self.qty_entries[code].get().strip()
                if not qty_text:
                    messagebox.showerror("Erreur", f"Quantité manquante pour {p['designation']}")
                    return
                    
            except KeyError as e:
                print(f"[FACTURE LEGACY] ERROR: Product missing key {e}")
                continue
            except Exception as e:
                print(f"[FACTURE LEGACY] ERROR processing product: {e}")
                continue
                return
                
            try:
                qty = int(qty_text)
                if qty < 1:
                    messagebox.showerror("Erreur", f"Quantité invalide pour {p['designation']} (minimum: 1)")
                    return
                if qty > 9999:
                    messagebox.showerror("Erreur", f"Quantité trop élevée pour {p['designation']} (maximum: 9999)")
                    return
            except ValueError:
                messagebox.showerror("Erreur", f"Quantité invalide pour {p['designation']} (doit être un nombre entier)")
                return
                
            # Calculate total for validation
            prix = p['prix_ht']
            total_amount += qty * prix
            
            selection.append({"code": code, "qty": qty})

        # Validate that at least one product is selected
        if not selection:
            messagebox.showerror("Erreur", "Aucun produit sélectionné.")
            return
            
        # Validate total amount (prevent extremely large invoices)
        if total_amount > 1000000:  # 1 million DT
            if not messagebox.askyesno("Confirmation", 
                f"Le montant total est élevé ({format_money(total_amount)}). Continuer ?"):
                return

        # Generate invoice with error handling
        try:
            # ✅ PHASE 2I MIGRATION: Use service layer
            if self.facture_service:
                out_path = self.facture_service.generate_invoice(self.selected_client, chantier, selection)
            else:
                # Service not available - show clear error message
                raise RuntimeError("Service de génération de factures non disponible. Veuillez redémarrer l'application.")
            
            messagebox.showinfo("Succès", f"Facture enregistrée :\n{out_path}")
            # Update next invoice number after successful generation
            try:
                self._update_next_invoice_number()
            except Exception as update_error:
                print(f"[FACTURE] Error updating invoice number display: {update_error}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération de la facture:\n{str(e)}")
            print(f"[FACTURE] Generation error: {e}")