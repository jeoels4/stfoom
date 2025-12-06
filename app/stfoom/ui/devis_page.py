import tkinter as tk
from tkinter import messagebox, ttk

class DevisPage(ttk.Frame):
    def __init__(self, parent, di_container, go_home):
        super().__init__(parent, style="FactureMain.TFrame")
        self.pack(fill="both", expand=True)
        self.go_home = go_home
        
        # ✅ PHASE 2J MIGRATION: Use dependency injection with fallback
        try:
            self.devis_service = di_container.get('devis_service')
        except KeyError:
            print("[DEVIS_PAGE] DevisService not available - using placeholder")
            # Create a placeholder service with proper method signatures
            class MockDevisService:
                def get_products(self, *args, **kwargs):
                    return []
                def generate_devis(self, *args, **kwargs):
                    return {'success': False, 'message': 'Service not available'}
                def save_devis(self, *args, **kwargs):
                    return {'success': False, 'message': 'Service not available'}
            self.devis_service = MockDevisService()

        # ---------- header ----------
        header_frame = ttk.Frame(self, style="FactureHeader.TFrame")
        header_frame.pack(fill="x", pady=(0, 10))
        ttk.Button(header_frame, text="⬅️ Retour", command=go_home, style="FactureBack.TButton").pack(side="left", padx=(10, 20), pady=18)
        ttk.Label(header_frame, text="Devis – Générateur", font=("Segoe UI", 22, "bold"), style="FactureHeader.TLabel").pack(side="left", pady=18)

        # ---------- smart search ----------
        self._setup_smart_search()

        # ✅ PHASE 2J MIGRATION: Load products through service layer
        self.products_df = self.devis_service.get_products()

        # UI variables
        self.client_name_var = tk.StringVar()
        self.grand_tunis_var = tk.BooleanVar()
        self.hors_grand_tunis_var = tk.BooleanVar()

        # ---------- client info ----------
        client_frame = ttk.LabelFrame(self, text="Client", style="FactureSection.TLabelframe")
        client_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        inner_client = ttk.Frame(client_frame)
        inner_client.pack(fill="x", padx=10, pady=5)
        ttk.Label(inner_client, text="Nom du client :", font=("Segoe UI", 12)).pack(side="left")
        ttk.Entry(inner_client, textvariable=self.client_name_var, width=60).pack(side="left", padx=10)

        # Grand Tunis / Hors Grand Tunis
        chk = ttk.Frame(client_frame)
        chk.pack(pady=10)
        ttk.Checkbutton(chk, text="Grand Tunis (base devis.xlsx)", variable=self.grand_tunis_var).pack(side="left", padx=10)
        ttk.Checkbutton(chk, text="Hors Grand Tunis (base devis hors tunis.xlsx)", variable=self.hors_grand_tunis_var).pack(side="left", padx=10)

        # ---------- product list ----------
        products_frame = ttk.LabelFrame(self, text="Produits", style="FactureSection.TLabelframe")
        products_frame.pack(fill="x", padx=30, pady=(0, 10), ipadx=8, ipady=8)
        if not self.products_df:  # Check if list is empty
            ttk.Label(products_frame, text="Aucun produit disponible.", font=("Segoe UI", 12, "italic"), foreground="#c82333").pack(pady=20)
        else:
            canvas = tk.Canvas(products_frame, borderwidth=0, height=220, background="#ffffff", highlightthickness=0)
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
            self.price_vars = {}
            # Header row
            hdr = ttk.Frame(plist, style="FactureProducts.TFrame")
            hdr.grid(row=0, column=0, sticky="ew", pady=(0, 5))
            ttk.Label(hdr, text="✔", width=5).pack(side="left", padx=15)
            ttk.Label(hdr, text="Produit", width=60, anchor="w").pack(side="left")
            ttk.Label(hdr, text="Prix personnalisé (optionnel)", width=20, anchor="w").pack(side="left")
            # Product lines
            for idx, prod in enumerate(self.products_df, start=1):
                code = prod["code"]
                designation = prod["designation"]  # Correct column name
                prix_ht = prod["prix_ht"]          # Correct column name
                f = ttk.Frame(plist, style="FactureProducts.TFrame")
                f.grid(row=idx, column=0, sticky="ew", pady=2)
                var = tk.BooleanVar()
                ttk.Checkbutton(f, variable=var, style="FactureCheck.TCheckbutton", width=5).pack(side="left", padx=5)
                self.product_vars[code] = var
                ttk.Label(f, text=str(designation), width=60, anchor="w").pack(side="left")
                pvar = tk.StringVar()
                ttk.Entry(f, textvariable=pvar, width=20).pack(side="left", padx=5)
                self.price_vars[code] = pvar

        # ---------- generate ----------
        gen_btn = tk.Button(
            self,
            text="✅ Générer Devis",
            command=self.on_generate,
            font=("Segoe UI", 18, "bold"),
            bg="#27ae60",
            fg="#fff",
            activebackground="#219150",
            activeforeground="#fff",
            relief="flat",
            bd=0,
            cursor="hand2"
        )
        gen_btn.pack(side="bottom", pady=30, ipadx=30, ipady=12)

    def on_generate(self):
        client_name = self.client_name_var.get().strip()
        grand = self.grand_tunis_var.get()
        hors_grand = self.hors_grand_tunis_var.get()

        # ✅ PHASE 2J MIGRATION: Basic validation moved to service layer
        if not client_name:
            messagebox.showerror("Erreur", "Veuillez entrer le nom du client.")
            return
        if not (grand or hors_grand):
            messagebox.showerror("Erreur", "Choisissez Grand Tunis ou Hors Grand Tunis.")
            return

        # ✅ PHASE 2J MIGRATION: Collect selected products for service layer
        selected_products = []
        for _, prod in self.products_df.iterrows():
            code = prod["code"]
            designation = prod["designation"]
            prix_ht = prod["prix_ht"]

            if self.product_vars[code].get():
                price_str = self.price_vars[code].get().strip()
                custom_price = None
                
                # Validate custom price if provided
                if price_str:
                    try:
                        custom_price = float(price_str)
                    except ValueError:
                        messagebox.showerror("Erreur", f"Prix invalide pour {designation}")
                        return
                
                selected_products.append({
                    "code": code, 
                    "name": designation, 
                    "price": custom_price  # None will use default price from DB
                })

        if not selected_products:
            messagebox.showerror("Erreur", "Aucun produit sélectionné.")
            return

        try:
            # ✅ PHASE 2J MIGRATION: Use service layer instead of direct logic
            result = self.devis_service.create_devis(
                client_name=client_name,
                products=selected_products,
                is_grand_tunis=grand
            )
            
            if result["success"]:
                message = f"Devis {result['devis_number']} créé avec succès!\n\n"
                message += f"Fichier sauvegardé: {result['file_path']}\n"
                message += f"Total HT: {result['total_ht']:.3f} TND\n"
                message += f"Total TTC: {result['total_ttc']:.3f} TND"
                messagebox.showinfo("Succès", message)
                
                # Clear form after successful generation
                self.clear_form()
            else:
                error_message = "Erreurs:\n" + "\n".join(result["errors"])
                messagebox.showerror("Erreur", error_message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur inattendue: {str(e)}")
    
    def clear_form(self):
        """Clear the form after successful generation."""
        self.client_name_var.set("")
        self.grand_tunis_var.set(False)
        self.hors_grand_tunis_var.set(False)
        
        # Clear all product selections and custom prices
        for code in self.product_vars:
            self.product_vars[code].set(False)
            self.price_vars[code].set("")

    def _setup_smart_search(self):
        """Setup the smart search widget for the devis page."""
        try:
            from .smart_search import create_smart_search
            
            # Create devis-specific search providers
            def search_devis(query):
                """Search in devis database."""
                results = []
                try:
                    # Placeholder for devis search
                    results.append({
                        'type': 'Devis',
                        'content': f"Recherche de devis: '{query}'",
                        'details': "Recherche dans la base de données des devis",
                        'data': {'query': query, 'type': 'devis_search'}
                    })
                except Exception as e:
                    print(f"[SMART_SEARCH] Error searching devis: {e}")
                return results
            
            def search_products(query):
                """Search in products for devis."""
                results = []
                try:
                    if hasattr(self, 'products_df') and not self.products_df.empty:
                        query_lower = query.lower()
                        # Search in product designation
                        for _, product in self.products_df.iterrows():
                            if query_lower in product.get('designation', '').lower():
                                results.append({
                                    'type': 'Produit',
                                    'content': f"{product.get('reference', 'N/A')} - {product.get('designation', 'N/A')}",
                                    'details': f"Prix: {product.get('prix_unitaire', 0):.3f} TND",
                                    'data': product.to_dict(),
                                    'callback': lambda p=product: self._select_product_from_search(p)
                                })
                            if len(results) >= 15:  # Limit results
                                break
                except Exception as e:
                    print(f"[SMART_SEARCH] Error searching devis products: {e}")
                return results
            
            # Additional search providers specific to devis
            additional_providers = {
                'devis': search_devis,
                'products': search_products
            }
            
            # Create smart search widget
            self.smart_search = create_smart_search(self, additional_providers)
            
            print("[DEVIS] Smart search setup complete")
            
        except Exception as e:
            print(f"[DEVIS] Error setting up smart search: {e}")
            # Create placeholder label if smart search fails
            placeholder = ttk.Label(self, text="🔍 Recherche intelligente temporairement indisponible", foreground='gray')
            placeholder.pack(pady=10)

    def _select_product_from_search(self, product):
        """Select a product from search results."""
        try:
            code = product.get('reference', '')
            if code and code in self.product_vars:
                # Select the product checkbox
                self.product_vars[code].set(True)
                print(f"[DEVIS] Selected product from search: {product.get('designation', 'N/A')}")
                from tkinter import messagebox
                messagebox.showinfo("Info", f"Produit sélectionné: {product.get('designation', 'N/A')}")
            else:
                print(f"[DEVIS] Product code {code} not found in available products")
        except Exception as e:
            print(f"[DEVIS] Error selecting product from search: {e}")
