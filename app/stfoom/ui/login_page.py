"""
Login Page for STFOOM Access Control
===================================
Provides user authentication interface.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
from typing import Callable, Optional

from ..services.auth_manager import auth_manager, UserRank, ActionType
from .language_manager import language_manager
from .theme_manager import theme_manager

class LoginPage(ttk.Frame):
    """Login page with authentication form."""
    
    def __init__(self, parent, on_login_success: Callable, on_cancel: Callable):
        super().__init__(parent)
        self.on_login_success = on_login_success
        self.on_cancel = on_cancel
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the login UI."""
        # Main container
        main_frame = ttk.Frame(self, style="Main.TFrame")
        main_frame.pack(fill="both", expand=True, padx=50, pady=50)
        
        # Title
        title_label = ttk.Label(
            main_frame,
            text="STFOOM - Connexion",
            font=("Segoe UI", 24, "bold"),
            style="Title.TLabel"
        )
        title_label.pack(pady=(0, 30))
        
        # Login form frame
        form_frame = ttk.Frame(main_frame, style="Card.TFrame")
        form_frame.pack(pady=20, padx=20, fill="x")
        
        # Username field
        username_frame = ttk.Frame(form_frame)
        username_frame.pack(fill="x", padx=20, pady=10)
        
        username_label = ttk.Label(
            username_frame,
            text="Nom d'utilisateur:",
            font=("Segoe UI", 12),
            style="FormLabel.TLabel"
        )
        username_label.pack(anchor="w")
        
        self.username_entry = ttk.Entry(
            username_frame,
            font=("Segoe UI", 12),
            style="FormEntry.TEntry"
        )
        self.username_entry.pack(fill="x", pady=(5, 0))
        
        # Password field
        password_frame = ttk.Frame(form_frame)
        password_frame.pack(fill="x", padx=20, pady=10)
        
        password_label = ttk.Label(
            password_frame,
            text="Mot de passe:",
            font=("Segoe UI", 12),
            style="FormLabel.TLabel"
        )
        password_label.pack(anchor="w")
        
        self.password_entry = ttk.Entry(
            password_frame,
            font=("Segoe UI", 12),
            show="*",
            style="FormEntry.TEntry"
        )
        self.password_entry.pack(fill="x", pady=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(
            form_frame,
            text="",
            font=("Segoe UI", 10),
            style="Status.TLabel"
        )
        self.status_label.pack(pady=10)
        
        # Buttons frame
        buttons_frame = ttk.Frame(form_frame)
        buttons_frame.pack(fill="x", padx=20, pady=20)
        
        # Login button
        self.login_button = ttk.Button(
            buttons_frame,
            text="Se connecter",
            command=self.handle_login,
            style="Primary.TButton"
        )
        self.login_button.pack(side="left", padx=(0, 10))
        
        # Cancel button
        cancel_button = ttk.Button(
            buttons_frame,
            text="Annuler",
            command=self.handle_cancel,
            style="Secondary.TButton"
        )
        cancel_button.pack(side="left")
        
        # Bind Enter key to login
        self.bind('<Return>', lambda e: self.handle_login())
        self.username_entry.bind('<Return>', lambda e: self.handle_login())
        self.password_entry.bind('<Return>', lambda e: self.handle_login())
        
        # Focus on username field
        self.username_entry.focus()
        
    def handle_login(self):
        """Handle login button click."""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            self.show_status("Veuillez saisir le nom d'utilisateur et le mot de passe", "error")
            return
        
        # Disable login button during authentication
        self.login_button.config(state="disabled")
        self.show_status("Connexion en cours...", "info")
        
        # Run authentication in background thread
        threading.Thread(target=self.authenticate_user, args=(username, password), daemon=True).start()
        
    def authenticate_user(self, username: str, password: str):
        """Authenticate user in background thread."""
        try:
            success, message = auth_manager.login(username, password)
            
            # Update UI in main thread
            self.after(0, self.handle_auth_result, success, message)
            
        except Exception as e:
            self.after(0, self.handle_auth_result, False, f"Erreur de connexion: {str(e)}")
    
    def handle_auth_result(self, success: bool, message: str):
        """Handle authentication result in main thread."""
        self.login_button.config(state="normal")
        
        if success:
            self.show_status("Connexion réussie! Redirection...", "success")
            # Call success callback after short delay
            self.after(1000, self.on_login_success)
        else:
            self.show_status(message, "error")
            # Clear password field on failure
            self.password_entry.delete(0, tk.END)
            self.password_entry.focus()
    
    def handle_cancel(self):
        """Handle cancel button click."""
        self.on_cancel()
    
    def show_status(self, message: str, status_type: str = "info"):
        """Show status message."""
        self.status_label.config(text=message)
        
        # Update status label style based on type
        if status_type == "error":
            self.status_label.config(foreground="red")
        elif status_type == "success":
            self.status_label.config(foreground="green")
        elif status_type == "info":
            self.status_label.config(foreground="blue")
        else:
            self.status_label.config(foreground="black")

class UserProfilePage(ttk.Frame):
    """User profile and account management page."""
    def __init__(self, parent, go_back: Callable, on_logout: Optional[Callable] = None):
        super().__init__(parent)
        self.go_back = go_back
        self.on_logout = on_logout
        self.setup_ui()
    def setup_ui(self):
        """Setup the user profile UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        back_button = ttk.Button(
            header_frame,
            text="← Retour",
            command=self.go_back,
            style="Secondary.TButton"
        )
        back_button.pack(side="left")
        title_label = ttk.Label(
            header_frame,
            text="Profil Utilisateur",
            font=("Segoe UI", 18, "bold"),
            style="Title.TLabel"
        )
        title_label.pack(side="left", padx=20)
        # Logout button (right side)
        logout_btn = ttk.Button(
            header_frame,
            text="Déconnexion",
            command=self.handle_logout,
            style="Danger.TButton"
        )
        logout_btn.pack(side="right")
        # Main content
        content_frame = ttk.Frame(self)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        # User info section
        self.create_user_info_section(content_frame)
        # Change password section
        self.create_password_section(content_frame)
        # Activity log section
        self.create_activity_section(content_frame)
    def handle_logout(self):
        from stfoom.logic.access_control import auth_manager
        from app.connection import sync
        try:
            # Check for pending sync changes first
            pending_count = sync.get_pending_changes_count()
            if pending_count > 0:
                # Show sync progress
                self.show_logout_status(f"Synchronisation de {pending_count} changements en cours...")
                # Perform sync in background
                def sync_and_logout():
                    try:
                        sync_result = sync.force_sync()
                        # Sync successful or failed, proceed with logout anyway
                        self.after(0, lambda: self.complete_logout(auth_manager))
                    except Exception as e:
                        # Sync error, proceed with logout anyway
                        self.after(0, lambda: self.complete_logout(auth_manager))
                import threading
                threading.Thread(target=sync_and_logout, daemon=True).start()
                return
            # No pending changes, proceed with logout
            self.complete_logout(auth_manager)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la déconnexion: {str(e)}")
    
    def complete_logout(self, auth_manager):
        """Complete the logout process."""
        try:
            success = auth_manager.logout()
            if success:
                # Use the on_logout callback instead of importing from main
                if self.on_logout:
                    self.on_logout()
                messagebox.showinfo("Déconnexion", "Vous avez été déconnecté.")
            else:
                messagebox.showerror("Erreur", "La déconnexion a échoué.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la déconnexion: {str(e)}")
    

    
    def show_logout_status(self, message):
        """Show logout status message."""
        # This could be enhanced to show a status label in the UI
        print(f"[LOGOUT] {message}")
    
    def create_user_info_section(self, parent):
        """Create user information section."""
        info_frame = ttk.LabelFrame(parent, text="Informations du compte", padding=20)
        info_frame.pack(fill="x", pady=(0, 20))
        
        if auth_manager.current_user:
            user = auth_manager.current_user
            
            # Username (read-only)
            ttk.Label(info_frame, text="Nom d'utilisateur:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
            ttk.Label(info_frame, text=user.username, font=("Segoe UI", 12)).pack(anchor="w", pady=(0,10))
            
            # Full name (editable)
            ttk.Label(info_frame, text="Nom complet:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
            self.full_name_entry = ttk.Entry(info_frame, font=("Segoe UI", 12))
            self.full_name_entry.insert(0, user.full_name)
            self.full_name_entry.pack(fill="x", pady=(0,10))
            
            # Email (editable)
            ttk.Label(info_frame, text="Email:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
            self.email_entry = ttk.Entry(info_frame, font=("Segoe UI", 12))
            self.email_entry.insert(0, user.email or "")
            self.email_entry.pack(fill="x", pady=(0,10))
            
            # Rank (read-only)
            rank_names = {
                "admin": "Administrateur",
                "manager": "Gestionnaire",
                "operator": "Opérateur",
                "viewer": "Lecteur",
                "guest": "Invité"
            }
            ttk.Label(info_frame, text="Rang:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
            ttk.Label(info_frame, text=rank_names.get(user.rank, user.rank), font=("Segoe UI", 12)).pack(anchor="w", pady=(0,10))
            
            # Last login (read-only)
            if user.last_login:
                ttk.Label(info_frame, text="Dernière connexion:", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=2)
                ttk.Label(info_frame, text=user.last_login.strftime('%d/%m/%Y %H:%M'), font=("Segoe UI", 12)).pack(anchor="w", pady=(0,10))
            
            # Save profile button
            ttk.Button(
                info_frame,
                text="💾 Enregistrer les modifications",
                command=self.save_profile,
                style="Primary.TButton"
            ).pack(pady=(10, 0))
            
            # Status label
            self.profile_status_label = ttk.Label(info_frame, text="", font=("Segoe UI", 10))
            self.profile_status_label.pack(pady=5)
    
    def save_profile(self):
        """Save profile changes."""
        if auth_manager.current_user is None:
            messagebox.showerror("Erreur", "Utilisateur non connecté")
            return
        
        full_name = self.full_name_entry.get().strip()
        email = self.email_entry.get().strip()
        
        if not full_name:
            self.show_profile_status("Le nom complet est obligatoire", "error")
            return
        
        try:
            # Import UserService from services
            from ..core.container import container
            user_service = container.get('user_service')
            
            success, message = user_service.update_user(
                auth_manager.current_user.id,
                full_name=full_name,
                email=email
            )
            
            if success:
                self.show_profile_status("Profil mis à jour avec succès", "success")
                # Update the current user object
                auth_manager.current_user.full_name = full_name
                auth_manager.current_user.email = email
            else:
                self.show_profile_status(message, "error")
                
        except Exception as e:
            self.show_profile_status(f"Erreur: {str(e)}", "error")
    
    def show_profile_status(self, message: str, status_type: str = "info"):
        """Show profile update status."""
        self.profile_status_label.config(text=message)
        
        if status_type == "error":
            self.profile_status_label.config(foreground="red")
        elif status_type == "success":
            self.profile_status_label.config(foreground="green")
        else:
            self.profile_status_label.config(foreground="black")
    
    def create_password_section(self, parent):
        """Create password change section."""
        password_frame = ttk.LabelFrame(parent, text="Changer le mot de passe", padding=20)
        password_frame.pack(fill="x", pady=(0, 20))
        
        # Current password
        current_frame = ttk.Frame(password_frame)
        current_frame.pack(fill="x", pady=5)
        ttk.Label(current_frame, text="Mot de passe actuel:").pack(anchor="w")
        self.current_password_entry = ttk.Entry(current_frame, show="*")
        self.current_password_entry.pack(fill="x", pady=(5, 0))
        
        # New password
        new_frame = ttk.Frame(password_frame)
        new_frame.pack(fill="x", pady=5)
        ttk.Label(new_frame, text="Nouveau mot de passe:").pack(anchor="w")
        self.new_password_entry = ttk.Entry(new_frame, show="*")
        self.new_password_entry.pack(fill="x", pady=(5, 0))
        
        # Confirm new password
        confirm_frame = ttk.Frame(password_frame)
        confirm_frame.pack(fill="x", pady=5)
        ttk.Label(confirm_frame, text="Confirmer le nouveau mot de passe:").pack(anchor="w")
        self.confirm_password_entry = ttk.Entry(confirm_frame, show="*")
        self.confirm_password_entry.pack(fill="x", pady=(5, 0))
        
        # Change password button
        change_button = ttk.Button(
            password_frame,
            text="Changer le mot de passe",
            command=self.change_password,
            style="Primary.TButton"
        )
        change_button.pack(pady=(10, 0))
        
        # Status label
        self.password_status_label = ttk.Label(password_frame, text="", font=("Segoe UI", 10))
        self.password_status_label.pack(pady=5)
    
    def create_activity_section(self, parent):
        """Create activity log section."""
        activity_frame = ttk.LabelFrame(parent, text="Activité récente", padding=20)
        activity_frame.pack(fill="both", expand=True)
        
        # Activity list
        self.activity_tree = ttk.Treeview(
            activity_frame,
            columns=("timestamp", "action", "resource", "details", "success"),
            show="headings",
            height=10
        )
        
        # Configure columns
        self.activity_tree.heading("timestamp", text="Date/Heure")
        self.activity_tree.heading("action", text="Action")
        self.activity_tree.heading("resource", text="Ressource")
        self.activity_tree.heading("details", text="Détails")
        self.activity_tree.heading("success", text="Statut")
        
        self.activity_tree.column("timestamp", width=150)
        self.activity_tree.column("action", width=100)
        self.activity_tree.column("resource", width=100)
        self.activity_tree.column("details", width=200)
        self.activity_tree.column("success", width=80)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(activity_frame, orient="vertical", command=self.activity_tree.yview)
        self.activity_tree.configure(yscrollcommand=scrollbar.set)
        
        # Pack widgets
        self.activity_tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Load activity data
        self.load_activity_data()
    
    def change_password(self):
        """Handle password change."""
        current_password = self.current_password_entry.get()
        new_password = self.new_password_entry.get()
        confirm_password = self.confirm_password_entry.get()
        
        if not current_password or not new_password or not confirm_password:
            self.show_password_status("Veuillez remplir tous les champs", "error")
            return
        
        if new_password != confirm_password:
            self.show_password_status("Les mots de passe ne correspondent pas", "error")
            return
        
        if len(new_password) < 6:
            self.show_password_status("Le mot de passe doit contenir au moins 6 caractères", "error")
            return
        
        # Verify current password
        if auth_manager.current_user is None:
            self.show_password_status("Utilisateur non connecté", "error")
            return
        success, message = auth_manager.login(auth_manager.current_user.username, current_password)
        if not success:
            self.show_password_status("Mot de passe actuel incorrect", "error")
            return
        
        # Change password
        try:
            # Import UserService from services
            from ..core.container import container
            user_service = container.get('user_service')
            
            success, message = user_service.update_user_password(
                auth_manager.current_user.username,
                new_password,
                current_password
            )
            
            if success:
                self.show_password_status("Mot de passe modifié avec succès", "success")
                # Clear fields
                self.current_password_entry.delete(0, tk.END)
                self.new_password_entry.delete(0, tk.END)
                self.confirm_password_entry.delete(0, tk.END)
            else:
                self.show_password_status(message, "error")
                
        except Exception as e:
            self.show_password_status(f"Erreur: {str(e)}", "error")
    
    def show_password_status(self, message: str, status_type: str = "info"):
        """Show password change status."""
        self.password_status_label.config(text=message)
        
        if status_type == "error":
            self.password_status_label.config(foreground="red")
        elif status_type == "success":
            self.password_status_label.config(foreground="green")
        else:
            self.password_status_label.config(foreground="black")
    
    def load_activity_data(self):
        """Load user activity data."""
        try:
            # Import activity logger from services
            from ..services.user_activity_service import activity_logger
            
            # Clear existing items
            for item in self.activity_tree.get_children():
                self.activity_tree.delete(item)
            
            # Get user activity
            if auth_manager.current_user is None:
                activities = []
            else:
                activities = activity_logger.get_user_activity(auth_manager.current_user.id, limit=50)
            
            # Add activities to tree
            for activity in activities:
                status = "✓" if activity.success else "✗"
                self.activity_tree.insert("", "end", values=(
                    activity.timestamp.strftime("%d/%m/%Y %H:%M"),
                    activity.action.value,
                    activity.resource,
                    activity.details[:50] + "..." if len(activity.details) > 50 else activity.details,
                    status
                ))
                
        except Exception as e:
            print(f"[ERROR] Failed to load activity data: {e}")
            print(f"[PROFILE] Error loading activity data: {e}") 