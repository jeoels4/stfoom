"""
Basic Permission Service

Standalone permission service that can be imported without triggering main.py execution.
This service provides both simple permission checking for UI and advanced JSON-based management.
"""

class BasicPermissionService:
    """
    Basic permission service that works in two modes:
    1. Simple mode: Uses hardcoded permission matrix for UI checks
    2. Advanced mode: Uses JSON files for full permission management
    """
    
    def __init__(self, use_json_files=False):
        self.use_json_files = use_json_files
        
        if use_json_files:
            import json
            import os
            self.ranks_file = "data/ranks.json"
            self.permissions_file = "data/permissions.json"
            self.assignments_file = "data/rank_permissions.json"
            
            # Ensure data directory exists
            os.makedirs("data", exist_ok=True)
            
            # Initialize files if they don't exist
            self._init_files()
        else:
            # Simple mode: hardcoded permission matrix for UI checks
            self._init_simple_permissions()
    
    def _init_simple_permissions(self):
        """Initialize simple hardcoded permission matrix for UI"""
        self.permission_matrix = {
            "admin": {
                # Factures
                "factures.view", "factures.create", "factures.update", "factures.delete",
                "factures.import", "factures.export", "factures.print",
                
                # Devis
                "devis.view", "devis.create", "devis.update", "devis.delete",
                "devis.import", "devis.export", "devis.print",
                
                # Ventes
                "vente.view", "vente.create", "vente.update", "vente.delete",
                "vente.import", "vente.export", "vente.print",
                
                # Achats
                "achat.view", "achat.create", "achat.update", "achat.delete",
                "achat.import", "achat.export", "achat.print",
                
                # Payments - NEW PERMISSIONS ADDED
                "payments.view", "payments.create", "payments.update", "payments.delete",
                
                # Banking & Financial
                "bank.view", "bank.create", "bank.update", "bank.delete",
                "caisse.view", "caisse.create", "caisse.update", "caisse.delete",
                "retenu.view", "retenu.create", "retenu.update", "retenu.delete",
                
                # Management
                "voiture.view", "voiture.create", "voiture.update", "voiture.delete",
                "calendar.view", "calendar.create", "calendar.update", "calendar.delete",
                "calculator.view",
                "ciment.view", "ciment.create", "ciment.update", "ciment.delete",
                
                # System
                "sync.view", "sync.execute",
                "backup.view", "backup.create", "backup.restore", "backup.delete",
                "documents.view", "documents.create", "documents.update", "documents.delete",
                "settings.view", "settings.update",
                "logs.view",  # User activity logs
                
                # User Management (Admin only)
                "users.view", "users.create", "users.update", "users.delete", "users.manage",
                "permissions.view", "permissions.create", "permissions.update", "permissions.delete", "permissions.manage"
            },
            "manager": {
                # Factures
                "factures.view", "factures.create", "factures.update", "factures.delete",
                "factures.import", "factures.export", "factures.print",
                
                # Devis
                "devis.view", "devis.create", "devis.update", "devis.delete",
                "devis.import", "devis.export", "devis.print",
                
                # Ventes
                "vente.view", "vente.create", "vente.update", "vente.delete",
                "vente.import", "vente.export", "vente.print",
                
                # Achats
                "achat.view", "achat.create", "achat.update", "achat.delete",
                "achat.import", "achat.export", "achat.print",
                
                # Payments - NEW PERMISSIONS ADDED
                "payments.view", "payments.create", "payments.update", "payments.delete",
                
                # Banking & Financial
                "bank.view", "bank.create", "bank.update", "bank.delete",
                "caisse.view", "caisse.create", "caisse.update", "caisse.delete",
                "retenu.view", "retenu.create", "retenu.update", "retenu.delete",
                
                # Management
                "voiture.view", "voiture.create", "voiture.update", "voiture.delete",
                "calendar.view", "calendar.create", "calendar.update", "calendar.delete",
                "calculator.view",
                "ciment.view", "ciment.create", "ciment.update", "ciment.delete",
                
                # System (limited)
                "sync.view",
                "backup.view", "backup.create",
                "documents.view", "documents.create", "documents.update", "documents.delete",
                "settings.view",
                "logs.view",  # User activity logs
                
                # NO user management for managers
            },
            "employee": {
                # Factures (limited)
                "factures.view", "factures.create", "factures.update",
                "factures.print",
                
                # Devis (limited)
                "devis.view", "devis.create", "devis.update",
                "devis.print",
                
                # Ventes (limited)
                "vente.view", "vente.create", "vente.update",
                "vente.print",
                
                # Achats (limited)
                "achat.view", "achat.create", "achat.update",
                "achat.print",
                
                # Payments (limited) - NEW PERMISSIONS ADDED
                "payments.view", "payments.create", "payments.update",
                
                # Banking & Financial (view only)
                "bank.view",
                "caisse.view",
                "retenu.view",
                
                # Management (view only)
                "voiture.view",
                "calendar.view", "calendar.create", "calendar.update",
                "calculator.view",
                "ciment.view",
                
                # Documents (limited)
                "documents.view", "documents.create",
                
                # Limited system access
                "logs.view",  # Can view activity logs
                
                # NO system access, NO user management
            },
            "viewer": {
                # View-only access to core business data
                "factures.view", "factures.print",
                "devis.view", "devis.print",
                "vente.view", "vente.print",
                "achat.view", "achat.print",
                "bank.view",
                "caisse.view", 
                "retenu.view",
                "voiture.view",
                "calendar.view",
                "calculator.view",
                "ciment.view",
                "documents.view",
                
                # NO create/update/delete access
                # NO system access
                # NO user management
            }
        }
    
    def _init_files(self):
        """Initialize JSON files with default data."""
        import json
        
        # Default ranks
        default_ranks = [
            {"name": "admin", "description": "Administrateur système avec tous les privilèges"},
            {"name": "manager", "description": "Gestionnaire avec privilèges étendus"},
            {"name": "operator", "description": "Opérateur avec privilèges standard"},
            {"name": "viewer", "description": "Utilisateur avec accès en lecture seule"},
        ]
        
        # Default permissions - COMPREHENSIVE LIST
        default_permissions = [
            # Page Access Permissions
            {"name": "factures.view", "category": "page", "description": "Voir la page Factures"},
            {"name": "devis.view", "category": "page", "description": "Voir la page Devis"},
            {"name": "vente.view", "category": "page", "description": "Voir la page Ventes"},
            {"name": "achat.view", "category": "page", "description": "Voir la page Achats"},
            {"name": "bank.view", "category": "page", "description": "Voir la page Banque"},
            {"name": "caisse.view", "category": "page", "description": "Voir la page Caisse"},
            {"name": "calendar.view", "category": "page", "description": "Voir le calendrier"},
            {"name": "calculator.view", "category": "page", "description": "Utiliser la calculatrice"},
            {"name": "ciment.view", "category": "page", "description": "Voir la page Ciment"},
            {"name": "documents.view", "category": "page", "description": "Voir les documents"},
            {"name": "voiture.view", "category": "page", "description": "Voir la page Véhicules"},
            {"name": "retenu.view", "category": "page", "description": "Voir la page Retenues"},
            {"name": "sync.view", "category": "page", "description": "Voir la page Synchronisation"},
            {"name": "backup.view", "category": "page", "description": "Voir la page Sauvegarde"},
            {"name": "settings.view", "category": "page", "description": "Voir les paramètres"},
            {"name": "users.view", "category": "page", "description": "Voir la gestion utilisateurs"},
            {"name": "permissions.view", "category": "page", "description": "Voir la gestion permissions"},
            
            # Data Creation Permissions
            {"name": "factures.create", "category": "data", "description": "Créer des factures"},
            {"name": "devis.create", "category": "data", "description": "Créer des devis"},
            {"name": "vente.create", "category": "data", "description": "Créer des ventes"},
            {"name": "achat.create", "category": "data", "description": "Créer des achats"},
            {"name": "bank.create", "category": "data", "description": "Créer des transactions bancaires"},
            {"name": "caisse.create", "category": "data", "description": "Créer des transactions caisse"},
            {"name": "calendar.create", "category": "data", "description": "Créer des événements calendrier"},
            {"name": "ciment.create", "category": "data", "description": "Créer des données ciment"},
            {"name": "documents.create", "category": "data", "description": "Créer/uploader des documents"},
            {"name": "voiture.create", "category": "data", "description": "Créer des véhicules"},
            {"name": "retenu.create", "category": "data", "description": "Créer des retenues"},
            {"name": "payments.create", "category": "data", "description": "Créer des paiements"},
            {"name": "users.create", "category": "system", "description": "Créer des utilisateurs"},
            {"name": "permissions.create", "category": "system", "description": "Créer des permissions"},
            
            # Data Modification Permissions
            {"name": "factures.update", "category": "data", "description": "Modifier des factures"},
            {"name": "devis.update", "category": "data", "description": "Modifier des devis"},
            {"name": "vente.update", "category": "data", "description": "Modifier des ventes"},
            {"name": "achat.update", "category": "data", "description": "Modifier des achats"},
            {"name": "bank.update", "category": "data", "description": "Modifier des transactions bancaires"},
            {"name": "caisse.update", "category": "data", "description": "Modifier des transactions caisse"},
            {"name": "calendar.update", "category": "data", "description": "Modifier des événements calendrier"},
            {"name": "ciment.update", "category": "data", "description": "Modifier des données ciment"},
            {"name": "documents.update", "category": "data", "description": "Modifier des documents"},
            {"name": "voiture.update", "category": "data", "description": "Modifier des véhicules"},
            {"name": "retenu.update", "category": "data", "description": "Modifier des retenues"},
            {"name": "payments.update", "category": "data", "description": "Modifier des paiements"},
            {"name": "settings.update", "category": "system", "description": "Modifier les paramètres"},
            {"name": "users.update", "category": "system", "description": "Modifier des utilisateurs"},
            {"name": "permissions.update", "category": "system", "description": "Modifier des permissions"},
            
            # Data Deletion Permissions
            {"name": "factures.delete", "category": "data", "description": "Supprimer des factures"},
            {"name": "devis.delete", "category": "data", "description": "Supprimer des devis"},
            {"name": "vente.delete", "category": "data", "description": "Supprimer des ventes"},
            {"name": "achat.delete", "category": "data", "description": "Supprimer des achats"},
            {"name": "bank.delete", "category": "data", "description": "Supprimer des transactions bancaires"},
            {"name": "caisse.delete", "category": "data", "description": "Supprimer des transactions caisse"},
            {"name": "calendar.delete", "category": "data", "description": "Supprimer des événements calendrier"},
            {"name": "ciment.delete", "category": "data", "description": "Supprimer des données ciment"},
            {"name": "documents.delete", "category": "data", "description": "Supprimer des documents"},
            {"name": "voiture.delete", "category": "data", "description": "Supprimer des véhicules"},
            {"name": "retenu.delete", "category": "data", "description": "Supprimer des retenues"},
            {"name": "payments.delete", "category": "data", "description": "Supprimer des paiements"},
            {"name": "users.delete", "category": "system", "description": "Supprimer des utilisateurs"},
            {"name": "permissions.delete", "category": "system", "description": "Supprimer des permissions"},
            
            # Import/Export Permissions
            {"name": "factures.import", "category": "action", "description": "Importer des factures"},
            {"name": "factures.export", "category": "action", "description": "Exporter des factures"},
            {"name": "devis.import", "category": "action", "description": "Importer des devis"},
            {"name": "devis.export", "category": "action", "description": "Exporter des devis"},
            {"name": "vente.import", "category": "action", "description": "Importer des ventes"},
            {"name": "vente.export", "category": "action", "description": "Exporter des ventes"},
            {"name": "achat.import", "category": "action", "description": "Importer des achats"},
            {"name": "achat.export", "category": "action", "description": "Exporter des achats"},
            
            # Print Permissions
            {"name": "factures.print", "category": "action", "description": "Imprimer des factures"},
            {"name": "devis.print", "category": "action", "description": "Imprimer des devis"},
            {"name": "vente.print", "category": "action", "description": "Imprimer des ventes"},
            {"name": "achat.print", "category": "action", "description": "Imprimer des achats"},
            
            # System Operations
            {"name": "sync.execute", "category": "system", "description": "Exécuter la synchronisation"},
            {"name": "backup.create", "category": "system", "description": "Créer des sauvegardes"},
            {"name": "backup.restore", "category": "system", "description": "Restaurer des sauvegardes"},
            {"name": "backup.delete", "category": "system", "description": "Supprimer des sauvegardes"},
            
            # Management Permissions
            {"name": "users.manage", "category": "system", "description": "Gérer les utilisateurs"},
            {"name": "permissions.manage", "category": "system", "description": "Gérer les permissions"},
        ]
        
        # Default assignments
        default_assignments = {
            "admin": [perm["name"] for perm in default_permissions],  # Admin gets all permissions
            "manager": ["factures.view", "factures.create", "factures.edit", "devis.view", "devis.create", "calendar.view"],
            "operator": ["factures.view", "devis.view", "calendar.view"],
            "viewer": ["factures.view", "calendar.view"]
        }
        
        # Create files if they don't exist
        import os
        if not os.path.exists(self.ranks_file):
            with open(self.ranks_file, 'w', encoding='utf-8') as f:
                json.dump(default_ranks, f, indent=2, ensure_ascii=False)
        
        if not os.path.exists(self.permissions_file):
            with open(self.permissions_file, 'w', encoding='utf-8') as f:
                json.dump(default_permissions, f, indent=2, ensure_ascii=False)
        
        if not os.path.exists(self.assignments_file):
            with open(self.assignments_file, 'w', encoding='utf-8') as f:
                json.dump(default_assignments, f, indent=2, ensure_ascii=False)
    
    # JSON file management methods (only work in JSON mode)
    def _load_json(self, file_path):
        """Load JSON file."""
        import json
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []
    
    def _save_json(self, file_path, data):
        """Save JSON file."""
        import json
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def create_rank(self, name, description):
        """Create a new rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        ranks = self._load_json(self.ranks_file)
        
        # Check if rank already exists
        if any(r['name'] == name for r in ranks):
            return False
        
        ranks.append({"name": name, "description": description})
        self._save_json(self.ranks_file, ranks)
        
        # Initialize empty permissions for this rank
        assignments = self._load_json(self.assignments_file)
        assignments[name] = []
        self._save_json(self.assignments_file, assignments)
        
        return True
    
    def delete_rank(self, name):
        """Delete a rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        ranks = self._load_json(self.ranks_file)
        ranks = [r for r in ranks if r['name'] != name]
        self._save_json(self.ranks_file, ranks)
        
        # Remove from assignments
        assignments = self._load_json(self.assignments_file)
        assignments.pop(name, None)
        self._save_json(self.assignments_file, assignments)
        
        return True
    
    def create_permission(self, name, category, description):
        """Create a new permission (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        permissions = self._load_json(self.permissions_file)
        
        # Check if permission already exists
        if any(p['name'] == name for p in permissions):
            return False
        
        permissions.append({"name": name, "category": category, "description": description})
        self._save_json(self.permissions_file, permissions)
        return True
    
    def delete_permission(self, name):
        """Delete a permission (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        permissions = self._load_json(self.permissions_file)
        permissions = [p for p in permissions if p['name'] != name]
        self._save_json(self.permissions_file, permissions)
        
        # Remove from all rank assignments
        assignments = self._load_json(self.assignments_file)
        for rank in assignments:
            if name in assignments[rank]:
                assignments[rank].remove(name)
        self._save_json(self.assignments_file, assignments)
        
        return True
    
    def get_all_ranks(self):
        """Get all ranks."""
        if self.use_json_files:
            return self._load_json(self.ranks_file)
        else:
            # Return simple ranks from permission matrix
            return [{"name": rank, "description": f"User rank: {rank}"} for rank in self.permission_matrix.keys()]
    
    def get_all_permissions(self):
        """Get all permissions."""
        if self.use_json_files:
            return self._load_json(self.permissions_file)
        else:
            # Extract all unique permissions from permission matrix
            all_perms = set()
            for perms in self.permission_matrix.values():
                all_perms.update(perms)
            return [{"name": perm, "category": "ui", "description": f"Permission: {perm}"} for perm in sorted(all_perms)]
    
    def get_rank_permissions(self, rank):
        """Get permissions for a rank."""
        if self.use_json_files:
            assignments = self._load_json(self.assignments_file)
            return assignments.get(rank, [])
        else:
            # Return permissions from simple matrix
            return list(self.permission_matrix.get(rank, set()))
    
    def grant_permission(self, rank, permission):
        """Grant permission to rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        assignments = self._load_json(self.assignments_file)
        if rank not in assignments:
            assignments[rank] = []
        
        if permission not in assignments[rank]:
            assignments[rank].append(permission)
            self._save_json(self.assignments_file, assignments)
        
        return True
    
    def revoke_permission(self, rank, permission):
        """Revoke permission from rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        assignments = self._load_json(self.assignments_file)
        if rank in assignments and permission in assignments[rank]:
            assignments[rank].remove(permission)
            self._save_json(self.assignments_file, assignments)
        
        return True
    
    def grant_all_permissions(self, rank):
        """Grant all permissions to rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        permissions = self.get_all_permissions()
        assignments = self._load_json(self.assignments_file)
        assignments[rank] = [p['name'] for p in permissions]
        self._save_json(self.assignments_file, assignments)
        return True
    
    def revoke_all_permissions(self, rank):
        """Revoke all permissions from rank (JSON mode only)."""
        if not self.use_json_files:
            return False
            
        assignments = self._load_json(self.assignments_file)
        assignments[rank] = []
        self._save_json(self.assignments_file, assignments)
        return True
    
    def get_rank_user_count(self, rank):
        """Get number of users with this rank."""
        # This would query the users table in a real implementation
        return 0
    
    def user_has_permission(self, user_rank: str, permission: str) -> bool:
        """Check if user rank has specific permission"""
        try:
            if self.use_json_files:
                # JSON mode: check file-based permissions
                rank_permissions = self.get_rank_permissions(user_rank)
                has_perm = permission in rank_permissions
            else:
                # Simple mode: check hardcoded matrix
                user_permissions = self.permission_matrix.get(user_rank, set())
                has_perm = permission in user_permissions
            
            print(f"[PERMISSION] Checking {user_rank} -> {permission}: {'✅ ALLOWED' if has_perm else '❌ DENIED'}")
            
            return has_perm
        except Exception as e:
            print(f"[PERMISSION] Error checking permission: {e}")
            # Fallback: deny permission on error (secure default)
            return False
    
    def get_user_permissions(self, user_rank: str) -> set:
        """Get all permissions for user rank"""
        if self.use_json_files:
            return set(self.get_rank_permissions(user_rank))
        else:
            return self.permission_matrix.get(user_rank, set())
