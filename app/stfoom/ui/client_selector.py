"""
Tk‑inter Client selector + manager dialog
----------------------------------------
 • Auto‑filtering drop‑down.
 • Manager dialog with Add / Edit / Delete.
 • "Ajouter" pre‑fills the next 411xxx.
 • Buttons always visible (scrollable form).
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
from app.stfoom.logicold import clients_selector as db

# optional LAN‑sync ---------------------------------------------------
try:
    from app.connection import sync
except Exception:  # offline / stand‑alone fallback
    class sync:
        @staticmethod
        def insert_with_sync(*args, **kwargs): pass
        @staticmethod
        def update_with_sync(*args, **kwargs): pass

# ────────────────────────────────────────────────────────────────────
# INTERNAL HELPERS
# ────────────────────────────────────────────────────────────────────

def _build_form(parent: tk.Widget, fields: list[str], preset: dict | None):
    """Builds a form and returns a {col: Entry} mapping."""
    ents: dict[str, tk.Entry] = {}
    
    # Create sections for better organization
    basic_fields = db.basic_cols()
    remise_fields = db.remise_cols()
    specific_fields = db.specific_cols()
    
    # Basic information section
    if basic_fields:
        basic_frame = ttk.LabelFrame(parent, text="Informations de base", padding=15)
        basic_frame.pack(fill="x", pady=(0, 10))
        
        for col in basic_fields:
            ttk.Label(basic_frame, text=f"{col} *").pack(anchor="w")
            e = ttk.Entry(basic_frame, width=50)
            e.pack(fill="x", pady=(0, 10))
            if preset and col in preset:
                e.insert(0, str(preset[col]))
            ents[col] = e
    
    # Remise section
    if remise_fields:
        remise_frame = ttk.LabelFrame(parent, text="Remises", padding=15)
        remise_frame.pack(fill="x", pady=(0, 10))
        
        for col in remise_fields:
            ttk.Label(remise_frame, text=col).pack(anchor="w")
            e = ttk.Entry(remise_frame, width=50)
            e.pack(fill="x", pady=(0, 10))
            if preset and col in preset:
                e.insert(0, str(preset[col]))
            ents[col] = e
    
    # Specific section
    if specific_fields:
        specific_frame = ttk.LabelFrame(parent, text="Informations spécifiques", padding=15)
        specific_frame.pack(fill="x", pady=(0, 10))
        
        for col in specific_fields:
            ttk.Label(specific_frame, text=col).pack(anchor="w")
            e = ttk.Entry(specific_frame, width=50)
            e.pack(fill="x", pady=(0, 10))
            if preset and col in preset:
                e.insert(0, str(preset[col]))
            ents[col] = e
    
    return ents

# ────────────────────────────────────────────────────────────────────
# PUBLIC API
# ────────────────────────────────────────────────────────────────────

def create_selector(parent: tk.Misc, on_select=None):
    """Insert a compact search-enabled client selector."""

    # Main container with compact layout
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="x", pady=2)
    
    # Single row layout: Label + Search + Clear + Manage
    row_frame = ttk.Frame(main_frame)
    row_frame.pack(fill="x")
    
    # Label (compact)
    ttk.Label(row_frame, text="Client:", font=('Arial', 9, 'bold')).pack(side="left", padx=(0, 8))
    
    # Search entry (main component)
    var = tk.StringVar()
    search_entry = ttk.Entry(row_frame, textvariable=var, font=('Arial', 9), width=25)
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    
    # Clear button (compact)
    clear_btn = ttk.Button(row_frame, text="✕", width=2, command=lambda: None)  # Will be defined later
    clear_btn.pack(side="right", padx=(2, 0))
    
    # Manage button (compact)
    manage_btn = ttk.Button(row_frame, text="📋", width=3, command=lambda: None)  # Will be defined later
    manage_btn.pack(side="right", padx=(2, 2))
    
    # Set focus and make sure it's editable
    search_entry.focus_set()
    search_entry.icursor(0)

    # Compact results listbox (initially hidden, smaller height)
    results_frame = ttk.Frame(main_frame)
    results_listbox = tk.Listbox(results_frame, height=4, font=('Arial', 8), selectmode='single')
    scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=results_listbox.yview)
    results_listbox.configure(yscrollcommand=scrollbar.set)
    
    results_listbox.pack(side="left", fill="both", expand=True)
    scrollbar.pack(side="right", fill="y")

    # Compact selected client display
    selected_label = ttk.Label(main_frame, text="Aucun client sélectionné", 
                              font=('Arial', 8), foreground='gray')
    selected_label.pack(pady=(2, 0), anchor="w")

    # Current selection data
    selected_client = {"data": None}

    # ------------------ search functionality -------------------------
    def _perform_search():
        query = var.get().strip().lower()
        
        try:
            clients_df = db.load_clients()
            
            if query:
                # Search in both raison_sociale and code_client
                mask = (clients_df["raison_sociale"].str.lower().str.contains(query, na=False) |
                       clients_df["code_client"].astype(str).str.lower().str.contains(query, na=False))
                filtered_df = clients_df[mask].head(50)  # Limit to 50 results for performance
            else:
                # Show all clients when no search query
                filtered_df = clients_df.head(50)  # Show first 50 when empty
            
            # Clear and populate results
            results_listbox.delete(0, tk.END)
            
            if len(filtered_df) > 0:
                for _, row in filtered_df.iterrows():
                    # More compact display format
                    display_text = f"{row['code_client']} • {row['raison_sociale']}"
                    results_listbox.insert(tk.END, display_text)
                
                # Show results with compact spacing
                results_frame.pack(fill="x", pady=(1, 0))
                
                # Update status with count
                if query:
                    count_text = f"🔍 {len(filtered_df)} trouvé(s)"
                    if len(filtered_df) == 50:
                        count_text += " (max 50)"
                else:
                    count_text = f"📋 {len(filtered_df)} clients"
                
                selected_label.configure(text=count_text, foreground='blue')
                search_entry.configure(foreground='black')
            else:
                # No results found
                results_listbox.insert(tk.END, "❌ Aucun client trouvé")
                results_frame.pack(fill="x", pady=(1, 0))
                selected_label.configure(text="Aucun résultat", foreground='red')
                search_entry.configure(foreground='red')
                
        except Exception as e:
            print(f"[CLIENT_SEARCH] Error: {e}")
            results_listbox.insert(tk.END, f"Erreur: {e}")
            results_frame.pack(fill="x", pady=(2, 0))

    # ------------------ selection handling ---------------------------
    def _on_listbox_select(event):
        selection = results_listbox.curselection()
        if selection:
            selected_text = results_listbox.get(selection[0])
            
            if "❌" not in selected_text:  # Not the "no results" message
                # Parse "Code • Name" format (updated format)
                if " • " in selected_text:
                    code_part = selected_text.split(" • ")[0].strip()
                    name_part = selected_text.split(" • ")[1].strip()
                    
                    # Get full client data
                    clients_df = db.load_clients()
                    picked = clients_df.query("code_client == @code_part", 
                                            local_dict={"code_part": code_part})
                    
                    if not picked.empty:
                        client_data = picked.iloc[0].to_dict()
                        selected_client["data"] = client_data
                        
                        # Compact selection display
                        display_name = f"✅ {name_part}"
                        selected_label.configure(text=display_name, foreground='green')
                        
                        # Update search entry to show selection
                        var.set(name_part)
                        
                        # Hide results
                        results_frame.pack_forget()
                        search_entry.configure(foreground='green')
                        
                        # Callback
                        if on_select:
                            on_select(client_data)

    # ------------------ event bindings -------------------------------
    search_debounce_id = None
    
    def _on_search_change(*args):
        nonlocal search_debounce_id
        if search_debounce_id is not None:
            search_entry.after_cancel(search_debounce_id)
        
        # Reset selection on new search
        selected_client["data"] = None
        selected_label.configure(text="Tapez pour rechercher...", foreground='gray')
        search_entry.configure(foreground='black')
        
        search_debounce_id = search_entry.after(300, _perform_search)
    
    # Simple focus handling - ensure Entry is always editable
    def _on_entry_click(event):
        search_entry.focus_set()
        return "break"  # Prevent other bindings
    
    def _on_key_press(event):
        # Ensure typing always works
        search_entry.configure(foreground='black')

    # Bind events
    var.trace('w', _on_search_change)
    results_listbox.bind('<<ListboxSelect>>', _on_listbox_select)
    results_listbox.bind('<Double-Button-1>', _on_listbox_select)
    search_entry.bind('<Return>', lambda e: _perform_search())
    search_entry.bind('<Button-1>', _on_entry_click)
    search_entry.bind('<KeyPress>', _on_key_press)
    
    # Clear search functionality
    def _clear_search():
        search_entry.delete(0, tk.END)
        search_entry.configure(foreground='black')
        results_frame.pack_forget()
        selected_client["data"] = None
        selected_label.configure(text="Aucun client sélectionné", foreground='gray')
        search_entry.focus_set()
    
    # Update button commands now that functions are defined
    clear_btn.configure(command=_clear_search)
    
    # Helper function for external refresh
    def _refresh_search():
        if var.get().strip():
            _perform_search()

    # Update manage button command
    manage_btn.configure(command=lambda: _manager_dialog(main_frame, _refresh_search))

    # Load initial results (first 50 clients) and ensure focus
    search_entry.after_idle(_perform_search)
    search_entry.after_idle(lambda: search_entry.focus_set())

    # Return the search entry (instead of combo) for compatibility
    return search_entry

# ────────────────────────────────────────────────────────────────────
# MANAGER DIALOG
# ────────────────────────────────────────────────────────────────────

def _manager_dialog(root: tk.Misc, on_db_change):
    win = tk.Toplevel(root)
    win.title("Gestion Clients")
    win.geometry("1200x700")
    win.configure(bg='white')

    # Main container
    main_frame = ttk.Frame(win)
    main_frame.pack(fill="both", expand=True, padx=10, pady=10)

    # Search frame
    search_frame = ttk.Frame(main_frame)
    search_frame.pack(fill="x", pady=(0, 10))
    
    ttk.Label(search_frame, text="🔍 Rechercher:", font=('Arial', 10, 'bold')).pack(side="left", padx=(0, 5))
    
    search_var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=search_var, width=40)
    search_entry.pack(side="left", padx=(0, 10))
    
    # Clear search button
    def _clear_search():
        search_var.set("")
        _load_tree()
    
    ttk.Button(search_frame, text="❌ Effacer", command=_clear_search).pack(side="left")

    # Treeview with scrollbar
    tree_frame = ttk.Frame(main_frame)
    tree_frame.pack(fill="both", expand=True, pady=(0, 10))

    tree = ttk.Treeview(tree_frame, show="headings", height=20)
    
    # Add scrollbar
    tree_scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=tree_scrollbar.set)
    
    tree.pack(side="left", fill="both", expand=True)
    tree_scrollbar.pack(side="right", fill="y")

    def _load_tree():
        tree.delete(*tree.get_children())
        df = db.load_clients()
        
        # Apply search filter if there's a search query
        search_query = search_var.get().strip().lower()
        if search_query:
            # Filter by code or raison_sociale
            mask = (df['code_client'].astype(str).str.lower().str.contains(search_query, na=False) |
                   df['raison_sociale'].astype(str).str.lower().str.contains(search_query, na=False))
            df = df[mask]
        
        tree["columns"] = list(df.columns)
        for c in df.columns:
            tree.heading(c, text=c)
            tree.column(c, width=120, anchor="center")
        for _, r in df.iterrows():
            tree.insert("", "end", values=list(r))
        
        # Update status
        total_count = len(db.load_clients())
        filtered_count = len(df)
        if search_query:
            win.title(f"Gestion Clients - {filtered_count}/{total_count} clients trouvés")
        else:
            win.title(f"Gestion Clients - {total_count} clients")

    _load_tree()

    # ---------------- search functionality ------------------------
    search_debounce_id = None
    
    def _on_search_change(*args):
        nonlocal search_debounce_id
        if search_debounce_id is not None:
            win.after_cancel(search_debounce_id)
        
        # Debounce search to avoid too frequent filtering
        search_debounce_id = win.after(300, _load_tree)
    
    # Bind search functionality
    search_var.trace('w', _on_search_change)
    search_entry.bind('<Return>', lambda e: _load_tree())

    # ---------------- add / edit form -------------------------------
    def _open_form(mode: str):
        if mode != "add" and not tree.selection():
            messagebox.showinfo("Info", "Sélectionnez une ligne.")
            return

        preset: dict[str, str | float] = {}
        if mode == "edit":
            preset = dict(zip(tree["columns"], tree.item(tree.selection()[0])["values"]))

        fields = db.basic_cols() + db.remise_cols() + db.specific_cols()

        top = tk.Toplevel(win)
        top.title("Client")
        top.geometry("650x750")
        top.resizable(True, True)
        top.configure(bg='white')

        # --- Scrollable main content ---
        content_frame = ttk.Frame(top)
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

        ents = _build_form(scrollable_frame, fields, preset)

        # auto‑fill next code for new client
        if mode == "add":
            ents["code_client"].delete(0, tk.END)
            ents["code_client"].insert(0, db.next_client_code())

        # --- Button section (always visible at bottom) ---
        btn_frame = ttk.Frame(top)
        btn_frame.pack(fill="x", pady=(10, 0), side="bottom")

        def _save():
            data = {f: ents[f].get().strip() for f in fields}

            # basic validation
            if not all(data[c] for c in db.basic_cols()):
                messagebox.showwarning("Champs", "Remplissez les champs de base")
                return

            # duplicate check
            clients_df = db.load_clients()
            if mode == "add":
                if not clients_df.empty:
                    if data["code_client"] in clients_df["code_client"].values:
                        messagebox.showerror("Erreur", f"Un client avec le code '{data['code_client']}' existe déjà.")
                        return
                    if data["raison_sociale"].lower() in [x.lower() for x in clients_df["raison_sociale"].values]:
                        messagebox.showerror("Erreur", f"Un client avec le nom '{data['nom']}' existe déjà.")
                        return
            else:
                # For edit, prevent changing to a code/name that already exists (except for self)
                if not clients_df.empty:
                    for _, row in clients_df.iterrows():
                        if row["code_client"] == data["code_client"] and row["raison_sociale"] != preset["raison_sociale"]:
                            messagebox.showerror("Erreur", f"Un client avec le code '{data['code_client']}' existe déjà.")
                            return
                        if row["raison_sociale"].lower() == data["raison_sociale"].lower() and row["raison_sociale"] != preset["raison_sociale"]:
                            messagebox.showerror("Erreur", f"Un client avec le nom '{data['nom']}' existe déjà.")
                            return

            # numeric conversion
            for f in db.remise_cols() + db.specific_cols():
                try:
                    data[f] = str(float(data[f] or 0))
                except ValueError:
                    messagebox.showerror("Erreur", f"{f} doit être un nombre")
                    return

            if mode == "add":
                db.add_client(data)
            else:
                db.update_client(str(preset["raison_sociale"]), data)

            # Data saved locally, sync will happen in background
            top.destroy()
            _load_tree()
            on_db_change()

        save_btn = tk.Button(
            btn_frame,
            text="Enregistrer",
            bg="#4CAF50",
            fg="white",
            font=('Arial', 10, 'bold'),
            relief="flat",
            padx=30,
            pady=8,
            command=_save,
        )
        save_btn.pack(side="right")

        cancel_btn = tk.Button(
            btn_frame,
            text="Annuler",
            bg="#9E9E9E",
            fg="white",
            font=('Arial', 10),
            relief="flat",
            padx=30,
            pady=8,
            command=top.destroy,
        )
        cancel_btn.pack(side="right", padx=(0, 10))

    # ---------------- delete ----------------------------------------
    def _delete():
        if not tree.selection():
            return
        raison = tree.item(tree.selection()[0])["values"][1]
        if messagebox.askyesno("Supprimer", f"Supprimer '{raison}' ?"):
            db.delete_client(raison)
            # Data saved locally, sync will happen in background
            _load_tree()
            on_db_change()

    # action bar buttons
    btnbar = ttk.Frame(main_frame)
    btnbar.pack(pady=10, fill="x")

    add_btn = tk.Button(btnbar, text="➕ Ajouter", command=lambda: _open_form("add"),
                       bg="#4CAF50", fg="white", font=('Arial', 9, 'bold'),
                       relief="flat", padx=15, pady=5)
    add_btn.pack(side="left", padx=5)
    
    edit_btn = tk.Button(btnbar, text="✏️ Modifier", command=lambda: _open_form("edit"),
                        bg="#2196F3", fg="white", font=('Arial', 9, 'bold'),
                        relief="flat", padx=15, pady=5)
    edit_btn.pack(side="left", padx=5)
    
    delete_btn = tk.Button(btnbar, text="❌ Supprimer", command=_delete,
                          bg="#F44336", fg="white", font=('Arial', 9, 'bold'),
                          relief="flat", padx=15, pady=5)
    delete_btn.pack(side="left", padx=5)
