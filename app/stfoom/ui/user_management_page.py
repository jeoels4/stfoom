"""
User Management Page for STFOOM
===============================
Provides user account management interface for administrators.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from typing import Callable, Optional
import threading

# ✅ PHASE 3 MIGRATION: Services-only architecture
from ..core.container import container
from ..core import service_registry  # Auto-registers all services
from ..data.models import User  # ✅ Import User from data models
from ..services.auth_manager import auth_manager  # ✅ Import auth_manager
from .language_manager import language_manager
from .theme_manager import theme_manager

# Helper functions for permission management
def get_all_permission_types():
    """Get all available permission types (ranks)."""
    return ["admin", "manager", "operator", "viewer", "guest"]

def get_user_permissions(user_id: int):
    """Get permissions for a user."""
    # For now, return empty list as permissions are managed via ranks
    return []

def add_permission_to_user(user_id: int, permission: str):
    """Add a permission to a user."""
    # Placeholder - permissions managed via ranks for now
    pass

def remove_permission_from_user(user_id: int, permission: str):
    """Remove a permission from a user."""
    # Placeholder - permissions managed via ranks for now
    pass

# NOTE: This file should not be run directly. Run the app from main.py.
class UserManagementPage(ttk.Frame):
    """User management page for administrators."""
    
    def __init__(self, parent, di_container, go_back: Callable):
        super().__init__(parent)
        self.go_back = go_back
        self.di_container = di_container
        self.users = []
        
        # ✅ PHASE 2A MIGRATION: Get UserService from dependency injection container
        self.user_service = di_container.get('user_service')
        
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        """Setup the user management UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        back_button = ttk.Button(header_frame, text="← Retour", command=self.go_back, style="Secondary.TButton")
        back_button.pack(side="left")
        
        title_label = ttk.Label(header_frame, text="👥 Gestion des Utilisateurs", font=("Segoe UI", 18, "bold"), style="Title.TLabel")
        title_label.pack(side="left", padx=20)
        
        # Add user button
        add_button = ttk.Button(header_frame, text="➕ Ajouter Utilisateur", command=self.show_add_user_dialog, style="Primary.TButton")
        add_button.pack(side="right")
        
        # Stats frame
        stats_frame = ttk.LabelFrame(self, text="📊 Statistiques", padding=10)
        stats_frame.pack(fill="x", padx=20, pady=10)
        
        self.stats_label = ttk.Label(stats_frame, text="Chargement...", font=("Segoe UI", 10))
        self.stats_label.pack()
        
        # Main content
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Users table
        self.create_users_table(content_frame)
        
    def create_users_table(self, parent):
        """Create users table."""
        # Table frame
        table_frame = ttk.Frame(parent)
        table_frame.pack(fill="both", expand=True)
        
        # Create treeview
        columns = ("username", "full_name", "rank", "email", "status", "last_login", "failed_attempts")
        self.users_tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            height=15
        )
        
        # Configure columns
        self.users_tree.heading("username", text="👤 Nom d'utilisateur")
        self.users_tree.heading("full_name", text="📝 Nom complet")
        self.users_tree.heading("rank", text="⭐ Rang")
        self.users_tree.heading("email", text="📧 Email")
        self.users_tree.heading("status", text="🔒 Statut")
        self.users_tree.heading("last_login", text="🕒 Dernière connexion")
        self.users_tree.heading("failed_attempts", text="❌ Tentatives échouées")
        
        self.users_tree.column("username", width=150)
        self.users_tree.column("full_name", width=200)
        self.users_tree.column("rank", width=120)
        self.users_tree.column("email", width=200)
        self.users_tree.column("status", width=100)
        self.users_tree.column("last_login", width=150)
        self.users_tree.column("failed_attempts", width=120)
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.users_tree.yview)
        h_scrollbar = ttk.Scrollbar(table_frame, orient="horizontal", command=self.users_tree.xview)
        self.users_tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Pack widgets
        self.users_tree.pack(side="left", fill="both", expand=True)
        v_scrollbar.pack(side="right", fill="y")
        h_scrollbar.pack(side="bottom", fill="x")
        
        # Bind double-click to edit user
        self.users_tree.bind("<Double-1>", self.edit_selected_user)
        
        # Context menu
        self.create_context_menu()
        
    def create_context_menu(self):
        """Create context menu for user actions."""
        self.context_menu = tk.Menu(self, tearoff=0)
        self.context_menu.add_command(label="✏️ Modifier", command=self.edit_selected_user)
        self.context_menu.add_command(label="🔑 Changer mot de passe", command=self.change_user_password)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🔓 Activer/Désactiver", command=self.toggle_user_status)
        self.context_menu.add_command(label="🔄 Réinitialiser tentatives", command=self.reset_failed_attempts)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="🗑️ Supprimer", command=self.delete_selected_user)
        
        # Bind right-click
        self.users_tree.bind("<Button-3>", self.show_context_menu)
    
    def show_context_menu(self, event):
        """Show context menu on right-click."""
        try:
            item = self.users_tree.identify_row(event.y)
            if item:
                self.users_tree.selection_set(item)
                self.context_menu.post(event.x_root, event.y_root)
        except Exception as e:
            print(f"[USER_MGMT] Error showing context menu: {e}")
    
    def load_users(self):
        """Load users from database."""
        try:
            # Clear existing items
            for item in self.users_tree.get_children():
                self.users_tree.delete(item)
            
            # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
            self.users = self.user_service.get_all_users()
            
            # Add users to tree
            active_count = 0
            for user in self.users:
                status = "✅ Actif" if user.is_active else "❌ Inactif"
                if user.is_active:
                    active_count += 1
                last_login = user.last_login.strftime("%d/%m/%Y %H:%M") if user.last_login else "Jamais"
                rank_name = user.rank  # Use rank as string
                
                self.users_tree.insert("", "end", values=(
                    user.username,
                    user.full_name,
                    rank_name,
                    user.email or "",
                    status,
                    last_login,
                    user.failed_attempts
                ), tags=(str(user.id),))
            
            # Update stats
            total_users = len(self.users)
            self.stats_label.config(text=f"Total: {total_users} | Actifs: {active_count} | Inactifs: {total_users - active_count}")
                
        except Exception as e:
            print(f"[USER_MGMT] Error loading users: {e}")
            messagebox.showerror("Erreur", f"Erreur lors du chargement des utilisateurs: {str(e)}")
    
    def get_selected_user(self) -> Optional['User']:
        """Get the currently selected user."""
        selection = self.users_tree.selection()
        if not selection:
            return None
        item = selection[0]
        tags = self.users_tree.item(item, "tags")
        if not tags:
            return None
        user_id = tags[0]
        try:
            user_id = int(user_id)
        except (ValueError, TypeError):
            print(f"[USER_MGMT] Invalid user ID in tags: {user_id}")
            return None
        for user in self.users:
            if user is not None and hasattr(user, 'id') and user.id == user_id:
                return user
        print(f"[USER_MGMT] User with ID {user_id} not found in users list")
        return None
    
    def show_add_user_dialog(self):
        """Show dialog to add new user."""
        root = self.winfo_toplevel()
        dialog = AddUserDialog(root, self.on_user_added)
    
    def edit_selected_user(self, event=None):
        """Edit selected user."""
        user = self.get_selected_user()
        if not user:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur")
            return
        root = self.winfo_toplevel()
        dialog = EditUserDialog(root, user, self.on_user_updated)
        dialog.grab_set()
    
    def change_user_password(self):
        """Change password for selected user."""
        user = self.get_selected_user()
        if not user:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur")
            return
        
        dialog = ChangePasswordDialog(self, user)
        dialog.grab_set()
    
    def toggle_user_status(self):
        """Toggle user active/inactive status."""
        user = self.get_selected_user()
        if not user:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur")
            return
        
        new_status = not user.is_active
        status_text = "activer" if new_status else "désactiver"
        
        if messagebox.askyesno("Confirmation", f"Voulez-vous {status_text} l'utilisateur {user.username}?"):
            try:
                # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
                success, message = self.user_service.update_user(user.id, is_active=new_status)
                if success:
                    messagebox.showinfo("Succès", message)
                    self.load_users()
                else:
                    messagebox.showerror("Erreur", message)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la modification: {str(e)}")
    
    def reset_failed_attempts(self):
        """Reset failed login attempts for selected user."""
        user = self.get_selected_user()
        if not user:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur")
            return
        
        if messagebox.askyesno("Confirmation", f"Voulez-vous réinitialiser les tentatives échouées pour {user.username}?"):
            try:
                # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
                success, message = self.user_service.update_user(user.id, failed_attempts=0, locked_until=None)
                if success:
                    messagebox.showinfo("Succès", "Tentatives échouées réinitialisées")
                    self.load_users()
                else:
                    messagebox.showerror("Erreur", message)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la réinitialisation: {str(e)}")
    
    def delete_selected_user(self):
        """Delete selected user."""
        user = self.get_selected_user()
        if not user:
            messagebox.showwarning("Attention", "Veuillez sélectionner un utilisateur")
            return
        # FIX: Check that auth_manager.current_user is not None before accessing .id
        if user and auth_manager.current_user is not None and user.id == auth_manager.current_user.id:
            messagebox.showerror("Erreur", "Vous ne pouvez pas supprimer votre propre compte")
            return
        if messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer l'utilisateur {user.username}?\nCette action est irréversible."):
            try:
                # For now, we'll just deactivate the user
                # In a real implementation, you might want to actually delete
                # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
                success, message = self.user_service.update_user(user.id, is_active=False)
                if success:
                    messagebox.showinfo("Succès", f"Utilisateur {user.username} désactivé")
                    self.load_users()
                else:
                    messagebox.showerror("Erreur", message)
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {str(e)}")
    
    def on_user_added(self):
        """Callback when user is added."""
        self.load_users()
    
    def on_user_updated(self):
        """Callback when user is updated."""
        self.load_users()

class AddUserDialog(tk.Toplevel):
    """Dialog for adding new user."""
    
    def __init__(self, parent, callback):
        super().__init__(parent)
        self.callback = callback
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.title("➕ Ajouter un utilisateur")
        self.geometry("500x500")
        self.resizable(False, False)
        
        # Center dialog on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (500 // 2)
        self.geometry(f"500x500+{x}+{y}")
        
        # Make dialog modal
        self.grab_set()
        
        # Main frame with scrollbar
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Title
        title_label = ttk.Label(scrollable_frame, text="➕ Nouvel utilisateur", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Form fields
        # Username
        ttk.Label(scrollable_frame, text="👤 Nom d'utilisateur *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.username_entry = ttk.Entry(scrollable_frame, width=50)
        self.username_entry.pack(fill="x", pady=(5, 15))
        
        # Password
        ttk.Label(scrollable_frame, text="🔑 Mot de passe *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.password_entry = ttk.Entry(scrollable_frame, show="*", width=50)
        self.password_entry.pack(fill="x", pady=(5, 15))
        
        # Confirm password
        ttk.Label(scrollable_frame, text="🔐 Confirmer le mot de passe *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.confirm_password_entry = ttk.Entry(scrollable_frame, show="*", width=50)
        self.confirm_password_entry.pack(fill="x", pady=(5, 15))
        
        # Full name
        ttk.Label(scrollable_frame, text="📝 Nom complet *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.full_name_entry = ttk.Entry(scrollable_frame, width=50)
        self.full_name_entry.pack(fill="x", pady=(5, 15))
        
        # Email
        ttk.Label(scrollable_frame, text="📧 Email:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.email_entry = ttk.Entry(scrollable_frame, width=50)
        self.email_entry.pack(fill="x", pady=(5, 15))
        
        # Rank selection
        ttk.Label(scrollable_frame, text="⭐ Rang *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.rank_var = tk.StringVar()
        # Get all permission types (ranks)
        rank_options = get_all_permission_types()
        if "admin" not in rank_options:
            rank_options = ["admin"] + rank_options
        self.rank_combo = ttk.Combobox(scrollable_frame, textvariable=self.rank_var, values=rank_options, state="readonly")
        self.rank_combo.pack(fill="x", pady=(5, 15))
        if rank_options:
            self.rank_var.set(rank_options[0])
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame (OUTSIDE scrollable area, always visible)
        buttons_frame = ttk.Frame(main_container)
        buttons_frame.pack(fill="x", pady=(10, 0), side="bottom")
        
        ttk.Button(
            buttons_frame,
            text="✅ Ajouter",
            command=self.add_user,
            style="Primary.TButton"
        ).pack(side="right", padx=(10, 0))
        
        ttk.Button(
            buttons_frame,
            text="❌ Annuler",
            command=self.destroy,
            style="Secondary.TButton"
        ).pack(side="right")
        
        # Focus on username
        self.username_entry.focus()
    
    def add_user(self):
        """Add the new user."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        full_name = self.full_name_entry.get().strip()
        email = self.email_entry.get().strip()
        rank_value = self.rank_var.get()
        
        # Validation
        if not username or not password or not full_name:
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs obligatoires (*)")
            return
        
        if password != confirm_password:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas")
            return
        
        if len(password) < 6:
            messagebox.showerror("Erreur", "Le mot de passe doit contenir au moins 6 caractères")
            return
        
        try:
            # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
            success, message = self.parent.user_service.create_user(username, password, full_name, rank_value, email)
            
            if success:
                messagebox.showinfo("Succès", message)
                self.callback()
                self.destroy()
            else:
                messagebox.showerror("Erreur", message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création: {str(e)}")

class EditUserDialog(tk.Toplevel):
    """Dialog for editing user."""
    
    def __init__(self, parent, user: 'User', callback):
        super().__init__(parent)
        self.user = user
        self.callback = callback
        self.transient(parent)  # Set transient to the root window
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.title(f"✏️ Modifier {self.user.username}")
        self.geometry("500x700")
        self.resizable(False, False)
        
        # Center dialog on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.winfo_screenheight() // 2) - (700 // 2)
        self.geometry(f"500x700+{x}+{y}")
        
        # Make dialog modal
        self.grab_set()
        # Main frame with scrollbar
        main_container = ttk.Frame(self)
        main_container.pack(fill="both", expand=True, padx=20, pady=20)
        # Canvas for scrolling
        canvas = tk.Canvas(main_container)
        scrollbar = ttk.Scrollbar(main_container, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        # Title
        title_label = ttk.Label(scrollable_frame, text=f"✏️ Modifier {self.user.username}", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        # Username (read-only)
        ttk.Label(scrollable_frame, text="👤 Nom d'utilisateur:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        username_label = ttk.Label(scrollable_frame, text=self.user.username, font=("Segoe UI", 10))
        username_label.pack(anchor="w", pady=(5, 15))
        # Form fields
        # Full name
        ttk.Label(scrollable_frame, text="📝 Nom complet *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.full_name_entry = ttk.Entry(scrollable_frame, width=50)
        self.full_name_entry.insert(0, self.user.full_name)
        self.full_name_entry.pack(fill="x", pady=(5, 15))
        # Email
        ttk.Label(scrollable_frame, text="📧 Email:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.email_entry = ttk.Entry(scrollable_frame, width=50)
        self.email_entry.insert(0, self.user.email or "")
        self.email_entry.pack(fill="x", pady=(5, 15))
        # Rank selection
        ttk.Label(scrollable_frame, text="⭐ Rang *:", font=("Segoe UI", 10, "bold")).pack(anchor="w")
        self.rank_var = tk.StringVar(value=self.user.rank)
        rank_options = get_all_permission_types()
        if "admin" not in rank_options:
            rank_options = ["admin"] + rank_options
        self.rank_combo = ttk.Combobox(scrollable_frame, textvariable=self.rank_var, values=rank_options, state="readonly")
        self.rank_combo.pack(fill="x", pady=(5, 15))
        if self.user.rank in rank_options:
            self.rank_var.set(self.user.rank)
        else:
            self.rank_var.set(rank_options[0])
        # Active status
        self.active_var = tk.BooleanVar(value=self.user.is_active)
        active_check = ttk.Checkbutton(
            scrollable_frame,
            text="✅ Compte actif",
            variable=self.active_var
        )
        active_check.pack(anchor="w", pady=(0, 20))
        # --- Permissions Section ---
        ttk.Label(scrollable_frame, text="🔑 Permissions:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 0))
        self.perm_frame = ttk.Frame(scrollable_frame)
        self.perm_frame.pack(fill="x", pady=(0, 10))
        self._refresh_permissions_ui()
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame (outside scrollable area, always visible)
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 20), side="bottom")
        
        ttk.Button(
            buttons_frame,
            text="💾 Enregistrer",
            command=self.save_user,
            style="Primary.TButton"
        ).pack(side="right", padx=(10, 0))
        
        ttk.Button(
            buttons_frame,
            text="❌ Annuler",
            command=self.destroy,
            style="Secondary.TButton"
        ).pack(side="right")
    
    def _refresh_permissions_ui(self):
        frame = self.perm_frame
        for w in frame.winfo_children():
            w.destroy()
        perms = set(get_user_permissions(self.user.id))
        all_types = get_all_permission_types()
        # Show current permissions as tags
        tag_frame = ttk.Frame(frame)
        tag_frame.pack(anchor="w", pady=(0, 5))
        for p in perms:
            tag = ttk.Frame(tag_frame, style="Tag.TFrame")
            tag.pack(side="left", padx=3, pady=2)
            ttk.Label(tag, text=p, style="Tag.TLabel").pack(side="left")
            btn = ttk.Button(tag, text="✖", width=2, command=lambda perm=p: self._remove_permission(perm))
            btn.pack(side="left")
        # Dropdown to add new permission
        add_frame = ttk.Frame(frame)
        add_frame.pack(anchor="w")
        available = [p for p in all_types if p not in perms]
        self.add_perm_var = tk.StringVar()
        if available:
            perm_combo = ttk.Combobox(add_frame, textvariable=self.add_perm_var, values=available, state="readonly", width=30)
            perm_combo.pack(side="left")
            ttk.Button(add_frame, text="Ajouter", command=self._add_permission).pack(side="left", padx=5)
        else:
            ttk.Label(add_frame, text="Aucune permission à ajouter.").pack(side="left")

    def _add_permission(self):
        perm = self.add_perm_var.get()
        if perm:
            add_permission_to_user(self.user.id, perm)
            self._refresh_permissions_ui()

    def _remove_permission(self, perm):
        remove_permission_from_user(self.user.id, perm)
        self._refresh_permissions_ui()
        
    def save_user(self):
        """Save user changes."""
        full_name = self.full_name_entry.get().strip()
        email = self.email_entry.get().strip()
        rank_value = self.rank_var.get()
        is_active = self.active_var.get()
        
        if not full_name:
            messagebox.showerror("Erreur", "Le nom complet est obligatoire")
            return
        
        try:
            # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
            success, message = self.parent.user_service.update_user(
                self.user.id,
                full_name=full_name,
                rank=rank_value,
                email=email,
                is_active=is_active
            )
            
            if success:
                messagebox.showinfo("Succès", message)
                self.callback()
                self.destroy()
            else:
                messagebox.showerror("Erreur", message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la modification: {str(e)}")

class ChangePasswordDialog(tk.Toplevel):
    """Dialog for changing user password."""
    
    def __init__(self, parent, user):
        super().__init__(parent)
        self.user = user
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the dialog UI."""
        self.title(f"🔑 Changer le mot de passe - {self.user.username}")
        self.geometry("400x250")
        self.resizable(False, False)
        
        # Center dialog on screen
        self.update_idletasks()
        x = (self.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.winfo_screenheight() // 2) - (250 // 2)
        self.geometry(f"400x250+{x}+{y}")
        
        # Make dialog modal
        self.grab_set()
        
        # Main frame
        main_frame = ttk.Frame(self, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text=f"🔑 Changer le mot de passe de {self.user.username}", font=("Segoe UI", 12, "bold"))
        title_label.pack(pady=(0, 20))
        
        # New password
        ttk.Label(main_frame, text="🔑 Nouveau mot de passe:").pack(anchor="w")
        self.password_entry = ttk.Entry(main_frame, show="*", width=40)
        self.password_entry.pack(fill="x", pady=(5, 15))
        
        # Confirm password
        ttk.Label(main_frame, text="🔐 Confirmer le mot de passe:").pack(anchor="w")
        self.confirm_password_entry = ttk.Entry(main_frame, show="*", width=40)
        self.confirm_password_entry.pack(fill="x", pady=(5, 20))
        
        # Buttons
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill="x")
        
        ttk.Button(
            buttons_frame,
            text="💾 Changer",
            command=self.change_password,
            style="Primary.TButton"
        ).pack(side="right", padx=(10, 0))
        
        ttk.Button(
            buttons_frame,
            text="❌ Annuler",
            command=self.destroy,
            style="Secondary.TButton"
        ).pack(side="right")
        
        # Focus on password
        self.password_entry.focus()
    
    def change_password(self):
        """Change the user password."""
        password = self.password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        
        if not password:
            messagebox.showerror("Erreur", "Veuillez saisir un mot de passe")
            return
        
        if password != confirm_password:
            messagebox.showerror("Erreur", "Les mots de passe ne correspondent pas")
            return
        
        if len(password) < 6:
            messagebox.showerror("Erreur", "Le mot de passe doit contenir au moins 6 caractères")
            return
        
        try:
            # ✅ PHASE 2A MIGRATION: Using service instead of direct logic call
            success, message = self.parent.user_service.change_password(self.user.id, password)
            
            if success:
                messagebox.showinfo("Succès", message)
                self.destroy()
            else:
                messagebox.showerror("Erreur", message)
                
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du changement de mot de passe: {str(e)}") 