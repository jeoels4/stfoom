"""
Permission Management Page for STFOOM
=====================================
Admins/Managers can view and edit permissions for each rank/resource/action.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog

# Import from services layer (modern approach)
try:
    from app.stfoom.services.permission_service import PermissionService
    from app.stfoom.services.user_service import UserService
    from app.stfoom.data.permission_repository import PermissionRepository
    
    permission_service = PermissionService(PermissionRepository())
    user_service = UserService()  # UserService creates its own repository
    
    def get_all_permission_types():
        """Get all RANKS (not individual permissions) from the database."""
        ranks = permission_service.get_all_ranks()
        return [r['name'] for r in ranks]
    
    def add_permission_type(rank_name):
        """Add a new rank."""
        return permission_service.permission_repository.create_rank(rank_name, "", False)
    
    def remove_permission_type(rank_name):
        """Remove a rank."""
        return permission_service.permission_repository.delete_rank(rank_name)
    
    def get_all_users():
        """Get all users (id, username tuples)."""
        users = user_service.get_all_users()
        # User objects have attributes, not dict keys
        return [(getattr(u, 'id', 0), getattr(u, 'username', '')) for u in users]
    
    def get_user_permissions(user_id):
        """Get the rank (permission type) for a user."""
        # This function is misnamed - it actually gets the user's RANK, not individual permissions
        # Since we're showing ranks in the list, we need to return which rank this user has
        users = user_service.get_all_users()
        user = next((u for u in users if getattr(u, 'id', 0) == user_id), None)
        if user:
            rank = getattr(user, 'rank', 'operator')
            return [rank]  # Return as list for compatibility with set() in refresh_types
        return []
    
    def add_permission_to_user(user_id, perm_name):
        """Grant permission to user."""
        # This requires linking through ranks - simplified for now
        pass
    
    def remove_permission_from_user(user_id, perm_name):
        """Revoke permission from user."""
        # This requires unlinking through ranks - simplified for now
        pass
        
except ImportError as e:
    print(f"[PERMISSION_PAGE] Import error: {e}")
    # Fallback functions if services are not available
    def get_all_permission_types(): return []
    def add_permission_type(perm_type): pass
    def remove_permission_type(perm_type): pass
    def get_all_users(): return []
    def get_user_permissions(user): return []
    def add_permission_to_user(user, perm): pass
    def remove_permission_from_user(user, perm): pass

class PermissionManagementPage(ttk.Frame):
    """Permission Types Management UI (add/remove/rename/assign types, show usage count)."""
    def __init__(self, parent, go_back):
        super().__init__(parent)
        self.go_back = go_back
        self.setup_ui()
        self.refresh_types()

    def setup_ui(self):
        # Header
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=20)
        ttk.Button(header, text="← Retour", command=self.go_back).pack(side="left")
        ttk.Label(header, text="Gestion des types de permissions", font=("Segoe UI", 18, "bold")).pack(side="left", padx=20)
        # Add new type
        add_frame = ttk.Frame(self)
        add_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.new_type_var = tk.StringVar()
        ttk.Entry(add_frame, textvariable=self.new_type_var, width=30).pack(side="left")
        ttk.Button(add_frame, text="Ajouter", command=self.add_type).pack(side="left", padx=8)
        # Table
        self.table = ttk.Frame(self)
        self.table.pack(fill="both", expand=True, padx=20, pady=10)
        self.table.bind_all("<Double-1>", self._on_table_double_click)

    def refresh_types(self):
        for w in self.table.winfo_children():
            w.destroy()
        types = get_all_permission_types()
        users = get_all_users()
        user_perms = {u[0]: set(get_user_permissions(u[0])) for u in users}
        type_counts = {t: 0 for t in types}
        for perms in user_perms.values():
            for t in perms:
                if t in type_counts:
                    type_counts[t] += 1
        # Header
        ttk.Label(self.table, text="Type de permission", font=("Segoe UI", 10, "bold"), borderwidth=1, relief="solid", padding=4).grid(row=0, column=0, sticky="nsew")
        ttk.Label(self.table, text="Utilisateurs", font=("Segoe UI", 10, "bold"), borderwidth=1, relief="solid", padding=4).grid(row=0, column=1, sticky="nsew")
        self._type_labels = []
        for i, t in enumerate(types, start=1):
            row_frame = ttk.Frame(self.table)
            row_frame.grid(row=i, column=0, sticky="nsew")
            lbl = ttk.Label(row_frame, text=t, borderwidth=1, relief="solid", padding=4, cursor="hand2")
            lbl.pack(side="left")
            self._type_labels.append((lbl, t))
            # Add rename and delete buttons
            ttk.Button(row_frame, text="✏️", width=2, command=lambda name=t: self.rename_type(name)).pack(side="left", padx=2)
            ttk.Button(row_frame, text="🗑️", width=2, command=lambda name=t: self.delete_type(name)).pack(side="left", padx=2)
            ttk.Label(self.table, text=str(type_counts[t]), borderwidth=1, relief="solid", padding=4).grid(row=i, column=1, sticky="nsew")

    def _on_table_double_click(self, event):
        # Find which label was double-clicked
        widget = event.widget.winfo_containing(event.x_root, event.y_root)
        for lbl, t in getattr(self, '_type_labels', []):
            if widget == lbl:
                self.modify_type_users(t)
                break

    def add_type(self):
        name = self.new_type_var.get().strip()
        if not name:
            messagebox.showinfo("Info", "Veuillez entrer un nom de permission.")
            return
        try:
            add_permission_type(name)
            self.new_type_var.set("")
            self.refresh_types()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'ajout: {e}")

    def delete_type(self, name):
        if messagebox.askyesno("Confirmation", f"Supprimer le type de permission '{name}' ?\nCela ne supprimera pas les permissions déjà attribuées aux utilisateurs."):
            try:
                remove_permission_type(name)
                self.refresh_types()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")

    def rename_type(self, old_name):
        new_name = simpledialog.askstring("Renommer la permission", f"Nouveau nom pour '{old_name}':", initialvalue=old_name)
        if new_name and new_name.strip() and new_name != old_name:
            try:
                from stfoom.logic.access_control import exec_write
                # Update permission type name
                exec_write("UPDATE permission_types SET name = ? WHERE name = ?", (new_name.strip(), old_name))
                # Update all user permissions as well
                exec_write("UPDATE permissions SET permission = ? WHERE permission = ?", (new_name.strip(), old_name))
                # Update all users with this rank
                exec_write("UPDATE users SET rank = ? WHERE rank = ?", (new_name.strip(), old_name))
                messagebox.showinfo("Succès", f"Rang '{old_name}' renommé en '{new_name}'. Tous les utilisateurs avec ce rang ont été mis à jour.")
                self.refresh_types()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors du renommage: {e}")

    def modify_type_users(self, perm_name):
        """Show dialog to assign permissions to a rank - DYNAMIC from database."""
        rank = perm_name
        
        # Get all permissions from database dynamically
        try:
            all_permissions = permission_service.get_all_permissions()
            
            # Group permissions by category for better UI
            by_category = {}
            for perm in all_permissions:
                category = perm.get('category', 'OTHER')
                if category not in by_category:
                    by_category[category] = []
                by_category[category].append(perm['name'])
            
            # Get current rank permissions
            rank_id = permission_service.permission_repository.get_rank_id(rank)
            if not rank_id:
                messagebox.showerror("Erreur", f"Rang '{rank}' introuvable")
                return
            
            current_perms = permission_service.get_rank_permissions(rank)
            current_perm_names = set(current_perms)  # It's already a list of strings!
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des permissions: {e}")
            return
        
        # Create dialog window
        win = tk.Toplevel(self)
        win.title(f"Permissions pour le rang '{rank}'")
        win.geometry("900x700")
        
        # Center dialog on screen
        win.update_idletasks()
        x = (win.winfo_screenwidth() // 2) - (900 // 2)
        y = (win.winfo_screenheight() // 2) - (700 // 2)
        win.geometry(f"900x700+{x}+{y}")
        win.grab_set()
        
        # Header
        header_frame = ttk.Frame(win)
        header_frame.pack(fill="x", padx=20, pady=10)
        ttk.Label(header_frame, 
                 text=f"Gérer les permissions pour: {rank}",
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        ttk.Label(header_frame,
                 text=f"Total: {len(all_permissions)} permissions disponibles",
                 font=("Segoe UI", 10)).pack(anchor="w", pady=5)
        
        # Scrollable content
        content_frame = ttk.Frame(win)
        content_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
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
        
        # Permission checkboxes by category
        check_vars = {}
        row = 0
        
        for category in sorted(by_category.keys()):
            # Category header
            category_frame = ttk.LabelFrame(scrollable_frame, text=f"📁 {category}", padding=10)
            category_frame.pack(fill="x", padx=10, pady=5)
            
            perms = sorted(by_category[category])
            
            # Create checkboxes in a grid (3 columns)
            col = 0
            perm_row = 0
            for perm_name in perms:
                var = tk.BooleanVar(value=(perm_name in current_perm_names))
                cb = ttk.Checkbutton(category_frame, 
                                    text=perm_name,
                                    variable=var)
                cb.grid(row=perm_row, column=col, sticky="w", padx=5, pady=2)
                check_vars[perm_name] = var
                
                col += 1
                if col >= 3:  # 3 columns
                    col = 0
                    perm_row += 1
        
        # Buttons at bottom
        button_frame = ttk.Frame(win)
        button_frame.pack(fill="x", padx=20, pady=10)
        
        def save_permissions():
            """Save the selected permissions."""
            try:
                # Get selected permissions
                selected = [name for name, var in check_vars.items() if var.get()]
                
                # Get current permissions for comparison
                current_names = current_perm_names
                
                # Calculate what to add and remove
                to_add = set(selected) - current_names
                to_remove = current_names - set(selected)
                
                # Apply changes
                for perm_name in to_add:
                    permission_service.grant_permission(rank, perm_name)
                
                for perm_name in to_remove:
                    permission_service.revoke_permission(rank, perm_name)
                
                messagebox.showinfo("Succès", 
                                   f"Permissions mises à jour:\n"
                                   f"Ajoutées: {len(to_add)}\n"
                                   f"Retirées: {len(to_remove)}")
                win.destroy()
                self.refresh_types()
                
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
        
        def select_all():
            """Select all permissions."""
            for var in check_vars.values():
                var.set(True)
        
        def deselect_all():
            """Deselect all permissions."""
            for var in check_vars.values():
                var.set(False)
        
        ttk.Button(button_frame, text="✅ Tout sélectionner", command=select_all).pack(side="left", padx=5)
        ttk.Button(button_frame, text="❌ Tout désélectionner", command=deselect_all).pack(side="left", padx=5)
        ttk.Button(button_frame, text="💾 Enregistrer", command=save_permissions).pack(side="right", padx=5)
        ttk.Button(button_frame, text="Annuler", command=win.destroy).pack(side="right", padx=5) 