# -*- coding: utf-8 -*-
"""Permission Management Page - 3-TAB System"""

import tkinter as tk
from tkinter import ttk, messagebox

class PermissionManagementPage(ttk.Frame):
    def __init__(self, ui_container, di_container, show_main_menu):
        super().__init__(ui_container)
        self.di_container = di_container
        self.go_back = show_main_menu
        # Use DATABASE permission service from DI container (NOT BasicPermissionService!)
        self.permission_service = di_container.get('permission_service')
        self.user_service = di_container.get('user_service')
        self.setup_ui()
        self.refresh_data()
    
    def setup_ui(self):
        """Setup the dynamic permission management UI."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        
        if self.go_back:
            ttk.Button(header_frame, text="← Retour", command=self.go_back).pack(side="left")
        
        ttk.Label(header_frame, text="Gestion Dynamique des Permissions", font=("Segoe UI", 18, "bold")).pack(side="left", padx=20)
        
        # Create notebook for different sections
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Tab 1: Manage Ranks
        self.ranks_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.ranks_frame, text="Gestion des Rangs")
        self.setup_ranks_tab()
        
        # Tab 2: Manage Permissions
        self.permissions_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.permissions_frame, text="Gestion des Permissions")
        self.setup_permissions_tab()
        
        # Tab 3: Assign Permissions to Ranks
        self.assignments_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.assignments_frame, text="Attribution Permissions")
        self.setup_assignments_tab()
    
    def setup_ranks_tab(self):
        """Setup the ranks management tab."""
        # Header
        header = ttk.Label(self.ranks_frame, text="Créer et Gérer les Rangs Personnalisés", font=("Segoe UI", 14, "bold"))
        header.pack(pady=10)
        
        # Add rank section
        add_frame = ttk.LabelFrame(self.ranks_frame, text="Ajouter un Nouveau Rang", padding=10)
        add_frame.pack(fill="x", padx=20, pady=10)
        
        ttk.Label(add_frame, text="Nom du Rang:").pack(anchor="w")
        self.rank_name_entry = ttk.Entry(add_frame, width=30)
        self.rank_name_entry.pack(pady=5)
        
        ttk.Label(add_frame, text="Description:").pack(anchor="w", pady=(10, 0))
        self.rank_desc_entry = ttk.Entry(add_frame, width=50)
        self.rank_desc_entry.pack(pady=5)
        
        ttk.Button(add_frame, text="+ Créer Rang", command=self.add_rank).pack(pady=10)
        
        # Existing ranks list
        list_frame = ttk.LabelFrame(self.ranks_frame, text="Rangs Existants", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Ranks treeview
        columns = ("name", "description", "users_count")
        self.ranks_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=12)
        
        self.ranks_tree.heading("name", text="Nom du Rang")
        self.ranks_tree.heading("description", text="Description")
        self.ranks_tree.heading("users_count", text="Nb Utilisateurs")
        
        self.ranks_tree.column("name", width=150)
        self.ranks_tree.column("description", width=300)
        self.ranks_tree.column("users_count", width=100)
        
        ranks_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.ranks_tree.yview)
        self.ranks_tree.configure(yscrollcommand=ranks_scrollbar.set)
        
        self.ranks_tree.pack(side="left", fill="both", expand=True)
        ranks_scrollbar.pack(side="right", fill="y")
        
        # Rank management buttons
        rank_btn_frame = ttk.Frame(list_frame)
        rank_btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(rank_btn_frame, text="Supprimer Rang", command=self.delete_rank).pack(side="left", padx=5)
        ttk.Button(rank_btn_frame, text="Actualiser", command=self.refresh_ranks).pack(side="right", padx=5)
    
    def setup_permissions_tab(self):
        """Setup Tab 2: Permission Management - VIEW ONLY (permissions are seeded in database)."""
        # Header
        header = ttk.Label(self.permissions_frame, text="Toutes les Permissions Disponibles (89 permissions)", font=("Segoe UI", 14, "bold"))
        header.pack(pady=10)
        
        # Info label
        info_label = ttk.Label(self.permissions_frame, 
                              text="Ces permissions sont définies dans la base de données et chargées automatiquement.",
                              font=("Segoe UI", 10, "italic"))
        info_label.pack(pady=5)
        
        # Permissions list
        list_frame = ttk.LabelFrame(self.permissions_frame, text="Liste des Permissions", padding=10)
        list_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Permissions treeview
        columns = ("name", "category", "description")
        self.perms_tree = ttk.Treeview(list_frame, columns=columns, show="headings", height=20)
        
        self.perms_tree.heading("name", text="Nom de la Permission")
        self.perms_tree.heading("category", text="Catégorie")
        self.perms_tree.heading("description", text="Description")
        
        self.perms_tree.column("name", width=200)
        self.perms_tree.column("category", width=100)
        self.perms_tree.column("description", width=300)
        
        perms_scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.perms_tree.yview)
        self.perms_tree.configure(yscrollcommand=perms_scrollbar.set)
        
        self.perms_tree.pack(side="left", fill="both", expand=True)
        perms_scrollbar.pack(side="right", fill="y")
        
        # Refresh button
        btn_frame = ttk.Frame(list_frame)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="🔄 Actualiser", command=self.refresh_permissions).pack(side="right", padx=5)
    
    def setup_assignments_tab(self):
        """Setup the permission assignments tab."""
        # Header
        header = ttk.Label(self.assignments_frame, text="Attribuer des Permissions aux Rangs", font=("Segoe UI", 14, "bold"))
        header.pack(pady=10)
        
        # Selection frame
        select_frame = ttk.Frame(self.assignments_frame)
        select_frame.pack(fill="x", padx=20, pady=10)
        
        # Rank selection
        ttk.Label(select_frame, text="Sélectionner un Rang:").pack(side="left")
        self.selected_rank_var = tk.StringVar()
        self.rank_combo = ttk.Combobox(select_frame, textvariable=self.selected_rank_var, width=20)
        self.rank_combo.pack(side="left", padx=10)
        self.rank_combo.bind("<<ComboboxSelected>>", self.on_rank_selected)
        
        ttk.Button(select_frame, text="Charger Permissions", command=self.load_rank_permissions).pack(side="left", padx=10)
        
        # Permissions assignment frame
        assign_frame = ttk.LabelFrame(self.assignments_frame, text="Permissions pour le Rang Sélectionné", padding=10)
        assign_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Permission assignment treeview
        columns = ("permission", "category", "granted", "description")
        self.assign_tree = ttk.Treeview(assign_frame, columns=columns, show="headings", height=15)
        
        self.assign_tree.heading("permission", text="Permission")
        self.assign_tree.heading("category", text="Catégorie")
        self.assign_tree.heading("granted", text="Accordée")
        self.assign_tree.heading("description", text="Description")
        
        self.assign_tree.column("permission", width=200)
        self.assign_tree.column("category", width=100)
        self.assign_tree.column("granted", width=80)
        self.assign_tree.column("description", width=300)
        
        assign_scrollbar = ttk.Scrollbar(assign_frame, orient="vertical", command=self.assign_tree.yview)
        self.assign_tree.configure(yscrollcommand=assign_scrollbar.set)
        
        self.assign_tree.pack(side="left", fill="both", expand=True)
        assign_scrollbar.pack(side="right", fill="y")
        
        # Bind double-click to toggle permission
        self.assign_tree.bind("<Double-1>", self.toggle_permission)
        
        # Assignment buttons
        assign_btn_frame = ttk.Frame(assign_frame)
        assign_btn_frame.pack(fill="x", pady=10)
        
        ttk.Button(assign_btn_frame, text="✓ Accorder Permission", command=self.grant_permission).pack(side="left", padx=5)
        ttk.Button(assign_btn_frame, text="✗ Révoquer Permission", command=self.revoke_permission).pack(side="left", padx=5)
        ttk.Button(assign_btn_frame, text="Tout Accorder", command=self.grant_all_permissions).pack(side="left", padx=10)
        ttk.Button(assign_btn_frame, text="Tout Révoquer", command=self.revoke_all_permissions).pack(side="left", padx=5)
    
    def add_rank(self):
        """Add a new rank."""
        name = self.rank_name_entry.get().strip()
        description = self.rank_desc_entry.get().strip()
        
        if not name:
            messagebox.showerror("Erreur", "Le nom du rang est requis.")
            return
        
        try:
            # Use permission_repository to create rank
            self.permission_service.permission_repository.create_rank(name, description, False)
            messagebox.showinfo("Succès", f"Rang '{name}' créé avec succès.")
            self.rank_name_entry.delete(0, tk.END)
            self.rank_desc_entry.delete(0, tk.END)
            self.refresh_ranks()
            self.refresh_rank_combo()
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la création du rang: {e}")
    
    def delete_rank(self):
        """Delete selected rank."""
        selection = self.ranks_tree.selection()
        if not selection:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un rang à supprimer.")
            return
        
        item = self.ranks_tree.item(selection[0])
        rank_name = item['values'][0]
        
        if messagebox.askyesno("Confirmer", f"Êtes-vous sûr de vouloir supprimer le rang '{rank_name}' ?"):
            try:
                # Use permission_repository to delete rank
                self.permission_service.permission_repository.delete_rank(rank_name)
                messagebox.showinfo("Succès", "Rang supprimé avec succès.")
                self.refresh_ranks()
                self.refresh_rank_combo()
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
    
    def refresh_ranks(self):
        """Refresh the ranks treeview."""
        # Clear existing items
        for item in self.ranks_tree.get_children():
            self.ranks_tree.delete(item)
        
        try:
            # Get all ranks from database
            ranks = self.permission_service.get_all_ranks()
            
            # Get user counts for each rank
            users = self.user_service.get_all_users()
            user_counts = {}
            for user in users:
                rank = getattr(user, 'rank', 'operator')
                user_counts[rank] = user_counts.get(rank, 0) + 1
            
            # Populate treeview
            for rank in ranks:
                rank_name = rank['name']
                description = rank.get('description', '')
                user_count = user_counts.get(rank_name, 0)
                
                self.ranks_tree.insert("", "end", values=(
                    rank_name,
                    description,
                    user_count
                ))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des rangs: {e}")
    
    def refresh_permissions(self):
        """Refresh the permissions treeview."""
        # Clear existing items
        for item in self.perms_tree.get_children():
            self.perms_tree.delete(item)
        
        try:
            # Get all permissions from database
            all_perms = self.permission_service.get_all_permissions()
            
            # Populate treeview
            for perm in all_perms:
                self.perms_tree.insert("", "end", values=(
                    perm['name'],
                    perm.get('category', 'OTHER'),
                    perm.get('description', '')
                ))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des permissions: {e}")
    
    def on_rank_selected(self, event):
        """Handle rank selection."""
        self.load_rank_permissions()
    
    def load_rank_permissions(self):
        """Load permissions for the selected rank."""
        rank = self.selected_rank_var.get()
        if not rank:
            return
        
        try:
            # Clear current items
            for item in self.assign_tree.get_children():
                self.assign_tree.delete(item)
            
            # Get all permissions
            all_permissions = self.permission_service.get_all_permissions()
            rank_permissions = self.permission_service.get_rank_permissions(rank)
            
            # Add permissions to tree
            for perm in all_permissions:
                granted = perm['name'] in rank_permissions
                self.assign_tree.insert("", "end", values=(
                    perm['name'],
                    perm['category'],
                    "✓" if granted else "✗",
                    perm['description']
                ))
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors du chargement des permissions: {e}")
    
    def toggle_permission(self, event):
        """Toggle permission on double-click."""
        selection = self.assign_tree.selection()
        if not selection:
            return
        
        item = self.assign_tree.item(selection[0])
        permission = item['values'][0]
        currently_granted = item['values'][2] == "✓"
        
        if currently_granted:
            self.revoke_permission()
        else:
            self.grant_permission()
    
    def grant_permission(self):
        """Grant selected permission to selected rank."""
        rank = self.selected_rank_var.get()
        selection = self.assign_tree.selection()
        
        if not rank or not selection:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un rang et une permission.")
            return
        
        item = self.assign_tree.item(selection[0])
        permission = item['values'][0]
        
        try:
            success = self.permission_service.grant_permission(rank, permission)
            if success:
                self.load_rank_permissions()  # Refresh
            else:
                messagebox.showerror("Erreur", "Impossible d'accorder la permission.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'attribution: {e}")
    
    def revoke_permission(self):
        """Revoke selected permission from selected rank."""
        rank = self.selected_rank_var.get()
        selection = self.assign_tree.selection()
        
        if not rank or not selection:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un rang et une permission.")
            return
        
        item = self.assign_tree.item(selection[0])
        permission = item['values'][0]
        
        try:
            success = self.permission_service.revoke_permission(rank, permission)
            if success:
                self.load_rank_permissions()  # Refresh
            else:
                messagebox.showerror("Erreur", "Impossible de révoquer la permission.")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la révocation: {e}")
    
    def grant_all_permissions(self):
        """Grant all permissions to selected rank."""
        rank = self.selected_rank_var.get()
        if not rank:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un rang.")
            return
        
        if messagebox.askyesno("Confirmer", f"Accorder TOUTES les permissions au rang '{rank}' ?"):
            try:
                # Get all permissions
                all_perms = self.permission_service.get_all_permissions()
                for perm in all_perms:
                    self.permission_service.grant_permission(rank, perm['name'])
                self.load_rank_permissions()  # Refresh
                messagebox.showinfo("Succès", f"Toutes les {len(all_perms)} permissions accordées.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def revoke_all_permissions(self):
        """Revoke all permissions from selected rank."""
        rank = self.selected_rank_var.get()
        if not rank:
            messagebox.showwarning("Sélection requise", "Veuillez sélectionner un rang.")
            return
        
        if messagebox.askyesno("Confirmer", f"Révoquer TOUTES les permissions du rang '{rank}' ?"):
            try:
                rank_perms = self.permission_service.get_rank_permissions(rank)
                for perm_name in rank_perms:
                    self.permission_service.revoke_permission(rank, perm_name)
                self.load_rank_permissions()  # Refresh
                messagebox.showinfo("Succès", "Toutes les permissions révoquées.")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur: {e}")
    
    def refresh_data(self):
        """Refresh all data in all tabs."""
        self.refresh_ranks()
        self.refresh_permissions()
        self.refresh_rank_combo()
    
    def refresh_rank_combo(self):
        """Refresh the rank dropdown in assignments tab."""
        try:
            ranks = self.permission_service.get_all_ranks()
            rank_names = [r['name'] for r in ranks]
            self.rank_combo['values'] = rank_names
            if rank_names and not self.selected_rank_var.get():
                self.rank_combo.current(0)
        except Exception as e:
            print(f"Error refreshing rank combo: {e}")

