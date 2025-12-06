"""
Tk‑inter Fournisseur selector + manager dialog
------------------------    # Search frame with label
    search_frame = ttk.Frame(parent)
    search_frame.pack(fill="x", pady=4)
    
    # Add hint label
    hint_label = ttk.Label(search_frame, text="🔍 Rechercher fournisseur:", font=('Arial', 9))
    hint_label.pack(side="left", padx=(0, 5))

    var = tk.StringVar()
    search_entry = ttk.Entry(search_frame, textvariable=var, width=40, font=('Arial', 10), state='normal')
    search_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
    
    # Simple placeholder approach - just show empty initially
    placeholder_text = "Tapez pour rechercher un fournisseur..."
    
    # Set focus and make sure it's editable
    search_entry.focus_set()
    search_entry.icursor(0)-------
 • Auto‑filtering drop‑down.
 • Manager dialog with Add / Edit / Delete.
 • "Ajouter" pre‑fills the next 411xxx.
 • Buttons always visible (scrollable form).
"""

from __future__ import annotations
import tkinter as tk
from tkinter import ttk, messagebox
# Try multiple legacy paths (app package first, then top-level stfoom package when present in dev)
_fournisseur_import_error = None
try:
    from app.stfoom.logicold import fournisseurs_selector as db  # preferred packaged path
except Exception as e1:
    _fournisseur_import_error = e1
    try:
        from stfoom.logicold import fournisseurs_selector as db  # dev/alt path
    except Exception as e2:
        _fournisseur_import_error = e2
        print(f"[FOURNISSEUR_UI] Legacy fournisseurs_selector unavailable: {e2} - using minimal fallback")
    # Minimal fallback stub so the UI still renders without crashing
    class _FallbackDB:
        def load_fournisseurs(self):
            import pandas as _pd
            return _pd.DataFrame(columns=[
                'id','code_fournisseur','nom_fournisseur','adresse','telephone','email','created_at','updated_at'
            ])
        def basic_cols(self): return ["code_fournisseur", "nom_fournisseur"]
        def contact_cols(self): return ["adresse", "telephone", "email"]
        def all_cols(self): return self.basic_cols() + self.contact_cols()
        def add_fournisseur(self, data): return False
        def update_fournisseur(self, code, data): return False
        def delete_fournisseur(self, code): return False
        def next_fournisseur_code(self): return "411000"
    db = _FallbackDB()
    # Provide module-level function wrappers expected by code below
    load_fournisseurs = db.load_fournisseurs
    basic_cols = db.basic_cols
    contact_cols = db.contact_cols
    all_cols = db.all_cols
else:
    # Successful import
    try:
        load_fournisseurs = db.load_fournisseurs
        basic_cols = db.basic_cols
        contact_cols = db.contact_cols
        all_cols = db.all_cols
        print("[FOURNISSEUR_UI] Loaded legacy fournisseurs_selector successfully")
    except Exception as _bind_err:
        print(f"[FOURNISSEUR_UI][WARN] Legacy fournisseurs_selector imported but binding failed: {_bind_err}")

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
    contact_fields = db.contact_cols()
    
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
    
    # Contact information section
    if contact_fields:
        contact_frame = ttk.LabelFrame(parent, text="Informations de contact", padding=15)
        contact_frame.pack(fill="x", pady=(0, 10))
        
        for col in contact_fields:
            ttk.Label(contact_frame, text=col).pack(anchor="w")
            e = ttk.Entry(contact_frame, width=50)
            e.pack(fill="x", pady=(0, 10))
            if preset and col in preset:
                e.insert(0, str(preset[col]))
            ents[col] = e
    
    return ents

# ────────────────────────────────────────────────────────────────────
# PUBLIC API
# ────────────────────────────────────────────────────────────────────

def create_selector(parent: tk.Misc, on_select=None):
    """Insert a compact search-enabled fournisseur selector."""

    # Main container with compact layout
    main_frame = ttk.Frame(parent)
    main_frame.pack(fill="x", pady=2)
    
    # Single row layout: Label + Search + Clear + Manage
    row_frame = ttk.Frame(main_frame)
    row_frame.pack(fill="x")
    
    # Label (compact)
    ttk.Label(row_frame, text="Fournisseur:", font=('Arial', 9, 'bold')).pack(side="left", padx=(0, 8))
    
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

    # Compact selected fournisseur display
    selected_label = ttk.Label(main_frame, text="Aucun fournisseur sélectionné", 
                              font=('Arial', 8), foreground='gray')
    selected_label.pack(pady=(2, 0), anchor="w")

    # Current selection data
    selected_fournisseur = {"data": None}

    # ------------------ search functionality -------------------------
    def _perform_search():
        query = var.get().strip().lower()
        
        try:
            fournisseurs_df = db.load_fournisseurs()
            
            if query:
                # Search in both name and code
                mask = (fournisseurs_df["nom_fournisseur"].str.lower().str.contains(query, na=False) |
                       fournisseurs_df["code_fournisseur"].astype(str).str.lower().str.contains(query, na=False))
                filtered_df = fournisseurs_df[mask].head(50)  # Limit to 50 results for performance
            else:
                # Show all fournisseurs when no search query
                filtered_df = fournisseurs_df.head(50)  # Show first 50 when empty
            
            # Clear and populate results
            results_listbox.delete(0, tk.END)
            
            if len(filtered_df) > 0:
                for _, row in filtered_df.iterrows():
                    # More compact display format
                    display_text = f"{row['code_fournisseur']} • {row['nom_fournisseur']}"
                    results_listbox.insert(tk.END, display_text)
                
                # Show results with compact spacing
                results_frame.pack(fill="x", pady=(1, 0))
                
                # Update status with count
                if query:
                    count_text = f"🔍 {len(filtered_df)} trouvé(s)"
                    if len(filtered_df) == 50:
                        count_text += " (max 50)"
                else:
                    count_text = f"📋 {len(filtered_df)} fournisseurs"
                
                selected_label.configure(text=count_text, foreground='blue')
                search_entry.configure(foreground='black')
            else:
                # No results found
                results_listbox.insert(tk.END, "❌ Aucun fournisseur trouvé")
                results_frame.pack(fill="x", pady=(1, 0))
                selected_label.configure(text="Aucun résultat", foreground='red')
                search_entry.configure(foreground='red')
                
        except Exception as e:
            print(f"[FOURNISSEUR_SEARCH] Error: {e}")
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
                    
                    # Get full fournisseur data
                    fournisseurs_df = db.load_fournisseurs()
                    picked = fournisseurs_df.query("code_fournisseur == @code_part", 
                                                  local_dict={"code_part": code_part})
                    
                    if not picked.empty:
                        fournisseur_data = picked.iloc[0].to_dict()
                        selected_fournisseur["data"] = fournisseur_data
                        
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
                            on_select(fournisseur_data)

    # ------------------ event bindings -------------------------------
    search_debounce_id = None
    
    def _on_search_change(*args):
        nonlocal search_debounce_id
        if search_debounce_id is not None:
            search_entry.after_cancel(search_debounce_id)
        
        # Reset selection on new search
        selected_fournisseur["data"] = None
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
        selected_fournisseur["data"] = None
        selected_label.configure(text="Aucun fournisseur sélectionné", foreground='gray')
        search_entry.focus_set()
    
    # Update button commands now that functions are defined
    clear_btn.configure(command=_clear_search)
    
    # Helper function for external refresh
    def _refresh_search():
        if var.get().strip():
            _perform_search()

    # Update manage button command
    manage_btn.configure(command=lambda: _manager_dialog(main_frame, _refresh_search))

    # Load initial results (first 50 fournisseurs) and ensure focus
    search_entry.after_idle(_perform_search)
    search_entry.after_idle(lambda: search_entry.focus_set())

    # Return the search entry (instead of combo) for compatibility
    return search_entry

# ────────────────────────────────────────────────────────────────────
# MANAGER DIALOG
# ────────────────────────────────────────────────────────────────────

def _manager_dialog(root: tk.Misc, on_db_change):
    win = tk.Toplevel(root)
    win.title("Gestion Fournisseurs")
    win.geometry("800x500")
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
        df = db.load_fournisseurs()
        
        # Apply search filter if there's a search query
        search_query = search_var.get().strip().lower()
        if search_query:
            # Filter by code or name
            mask = (df['code_fournisseur'].astype(str).str.lower().str.contains(search_query, na=False) |
                   df['nom_fournisseur'].astype(str).str.lower().str.contains(search_query, na=False))
            df = df[mask]
        
        tree["columns"] = list(df.columns)
        for c in df.columns:
            tree.heading(c, text=c)
            tree.column(c, width=200, anchor="center")
        for _, r in df.iterrows():
            tree.insert("", "end", values=list(r))
        
        # Update status
        total_count = len(db.load_fournisseurs())
        filtered_count = len(df)
        if search_query:
            win.title(f"Gestion Fournisseurs - {filtered_count}/{total_count} fournisseurs trouvés")
        else:
            win.title(f"Gestion Fournisseurs - {total_count} fournisseurs")

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

        fields = db.all_cols()

        top = tk.Toplevel(win)
        top.title("Fournisseur")
        top.geometry("500x300")
        top.resizable(False, False)
        top.configure(bg='white')

        # Main container
        main_container = ttk.Frame(top)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Create scrollable frame
        canvas = tk.Canvas(main_container, bg='white')
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
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

        # auto‑fill next code for new fournisseur
        if mode == "add":
            ents["code_fournisseur"].delete(0, tk.END)
            ents["code_fournisseur"].insert(0, db.next_fournisseur_code())

        # ---------------- save / cancel buttons ----------------------
        btn_frame = ttk.Frame(main_container)
        btn_frame.pack(fill="x", pady=(10, 0))

        def _save():
            data = {f: ents[f].get().strip() for f in fields}

            # basic validation
            if not all(data[c] for c in db.basic_cols()):
                messagebox.showwarning("Champs", "Remplissez les champs de base")
                return

            if mode == "add":
                if db.add_fournisseur(data):
                    messagebox.showinfo("Succès", "Fournisseur ajouté.")
                    # Data saved locally, sync will happen in background
                    _load_tree()
                    on_db_change()
                    # Clear form for next entry
                    for field in fields:
                        if field != "code_fournisseur":  # Keep code field for reference
                            ents[field].delete(0, tk.END)
                    # Auto-fill next code for new fournisseur
                    ents["code_fournisseur"].delete(0, tk.END)
                    ents["code_fournisseur"].insert(0, db.next_fournisseur_code())
                else:
                    messagebox.showerror("Erreur", "Échec de l'ajout.")
            else:
                if db.update_fournisseur(str(preset["code_fournisseur"]), data):
                    messagebox.showinfo("Succès", "Fournisseur modifié.")
                    # Data saved locally, sync will happen in background
                    _load_tree()
                    on_db_change()
                    top.destroy()  # Close modify dialog after successful update
                else:
                    messagebox.showerror("Erreur", "Échec de la modification.")

        def _cancel():
            top.destroy()

        ttk.Button(btn_frame, text="Enregistrer", command=_save).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Annuler", command=_cancel).pack(side="right")

    # ---------------- action buttons -------------------------------
    btn_frame = ttk.Frame(main_frame)
    btn_frame.pack(fill="x")

    def _add():
        _open_form("add")

    def _edit():
        _open_form("edit")

    def _delete():
        if not tree.selection():
            messagebox.showinfo("Info", "Sélectionnez une ligne.")
            return
        if not messagebox.askyesno("Confirmer", "Supprimer ce fournisseur ?"):
            return
        
        values = tree.item(tree.selection()[0])["values"]
        nom_fournisseur = values[1]  # nom_fournisseur is second column (index 1)
        
        if messagebox.askyesno("Supprimer", f"Supprimer '{nom_fournisseur}' ?"):
            if db.delete_fournisseur(nom_fournisseur):
                messagebox.showinfo("Succès", "Fournisseur supprimé.")
                # Data saved locally, sync will happen in background
                _load_tree()
                on_db_change()
            else:
                messagebox.showerror("Erreur", "Échec de la suppression. Le fournisseur est peut-être utilisé dans des achats.")

    ttk.Button(btn_frame, text="➕ Ajouter", command=_add).pack(side="left", padx=(0, 5))
    ttk.Button(btn_frame, text="✏️ Modifier", command=_edit).pack(side="left", padx=(0, 5))
    ttk.Button(btn_frame, text="❌ Supprimer", command=_delete).pack(side="left") 