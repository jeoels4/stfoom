"""
Permission Repository - Database Access Layer
===========================================
Repository for managing permissions, ranks and their assignments in the database.
"""

from typing import List, Dict, Optional, Any
from .base_repository import BaseRepository


class PermissionRepository(BaseRepository):
    """Repository for permission data access operations."""
    
    def __init__(self):
        """Initialize permission repository."""
        super().__init__("system_permissions")
        self._ensure_permission_tables()
    
    def get_entity_name(self) -> str:
        """Return the entity name for logging purposes."""
        return "permission"
    
    def _ensure_permission_tables(self):
        """Ensure all permission-related tables exist."""
        try:
            # System Permissions table (different from user permissions)
            self.execute_command('''
                CREATE TABLE IF NOT EXISTS system_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    category TEXT NOT NULL,
                    description TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Ranks table already exists with correct structure, just ensure it exists
            self.execute_command('''
                CREATE TABLE IF NOT EXISTS ranks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    description TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # System Rank permissions assignment table
            self.execute_command('''
                CREATE TABLE IF NOT EXISTS system_rank_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    rank_id INTEGER NOT NULL,
                    permission_id INTEGER NOT NULL,
                    granted_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    granted_by TEXT,
                    FOREIGN KEY (rank_id) REFERENCES ranks(id) ON DELETE CASCADE,
                    FOREIGN KEY (permission_id) REFERENCES system_permissions(id) ON DELETE CASCADE,
                    UNIQUE(rank_id, permission_id)
                )
            ''')
            
            # Indexes for better performance
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_system_permissions_name
                ON system_permissions(name)
            ''')
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_system_permissions_category
                ON system_permissions(category)
            ''')
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_ranks_name
                ON ranks(name)
            ''')
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_system_rank_permissions_rank
                ON system_rank_permissions(rank_id)
            ''')
            self.execute_command('''
                CREATE INDEX IF NOT EXISTS idx_system_rank_permissions_permission
                ON system_rank_permissions(permission_id)
            ''')
            
            # Create default permissions and ranks
            self._ensure_default_permissions()
            
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Table initialization error: {e}")
    
    def _ensure_default_permissions(self):
        """Ensure default permissions and ranks exist."""
        try:
            # Default permissions - comprehensive list
            default_permissions = [
                # Factures
                ("factures.view", "page", "Voir la page Factures"),
                ("factures.create", "data", "Créer des factures"),
                ("factures.edit", "data", "Modifier des factures"),
                ("factures.delete", "data", "Supprimer des factures"),
                
                # Devis
                ("devis.view", "page", "Voir la page Devis"),
                ("devis.create", "data", "Créer des devis"),
                ("devis.edit", "data", "Modifier des devis"),
                ("devis.delete", "data", "Supprimer des devis"),
                
                # Ventes
                ("vente.view", "page", "Voir la page Ventes"),
                ("vente.create", "data", "Créer des ventes"),
                ("vente.edit", "data", "Modifier des ventes"),
                ("vente.update", "data", "Mettre à jour des ventes"),  # Alias for compatibility
                ("vente.delete", "data", "Supprimer des ventes"),
                
                # Achats
                ("achat.view", "page", "Voir la page Achats"),
                ("achat.create", "data", "Créer des achats"),
                ("achat.edit", "data", "Modifier des achats"),
                ("achat.update", "data", "Mettre à jour des achats"),  # Alias for compatibility
                ("achat.delete", "data", "Supprimer des achats"),
                
                # Bank
                ("bank.view", "page", "Voir la page Banque"),
                ("bank.create", "data", "Créer des transactions bancaires"),
                ("bank.edit", "data", "Modifier des transactions bancaires"),
                ("bank.update", "data", "Mettre à jour des transactions bancaires"),  # Alias
                ("bank.delete", "data", "Supprimer des transactions bancaires"),
                ("bank.verify", "data", "Vérifier des transactions bancaires"),
                
                # Calendar
                ("calendar.view", "page", "Voir le calendrier"),
                ("calendar.create", "data", "Créer des événements"),
                ("calendar.edit", "data", "Modifier des événements"),
                ("calendar.delete", "data", "Supprimer des événements"),
                
                # Clients
                ("clients.view", "page", "Voir les clients"),
                ("clients.create", "data", "Créer des clients"),
                ("clients.edit", "data", "Modifier des clients"),
                ("clients.delete", "data", "Supprimer des clients"),
                
                # Fournisseurs
                ("fournisseurs.view", "page", "Voir les fournisseurs"),
                ("fournisseurs.create", "data", "Créer des fournisseurs"),
                ("fournisseurs.edit", "data", "Modifier des fournisseurs"),
                ("fournisseurs.delete", "data", "Supprimer des fournisseurs"),
                
                # Stock
                ("stock.view", "page", "Voir le stock"),
                ("stock.create", "data", "Créer des articles"),
                ("stock.edit", "data", "Modifier des articles"),
                ("stock.delete", "data", "Supprimer des articles"),
                
                # Loyer
                ("loyer.view", "page", "Voir la page Loyer"),
                ("loyer.create", "data", "Créer des loyers"),
                ("loyer.edit", "data", "Modifier des loyers"),
                ("loyer.delete", "data", "Supprimer des loyers"),
                ("loyer.export", "data", "Exporter des loyers"),
                
                # System
                ("users.manage", "system", "Gérer les utilisateurs"),
                ("permissions.manage", "system", "Gérer les permissions"),
                ("backup.create", "system", "Créer des sauvegardes"),
                ("settings.view", "system", "Voir les paramètres"),
                ("settings.update", "system", "Modifier les paramètres"),
            ]
            
            for name, category, description in default_permissions:
                if not self.permission_exists(name):
                    self.create_permission(name, category, description)
            
            # Default ranks
            default_ranks = [
                ("admin", "Administrateur système avec tous les privilèges", True),
                ("manager", "Gestionnaire avec privilèges étendus", True),
                ("operator", "Opérateur avec privilèges standard", True),
                ("viewer", "Utilisateur avec accès en lecture seule", True),
            ]
            
            for name, description, is_system in default_ranks:
                if not self.rank_exists(name):
                    self.create_rank(name, description, is_system)
            
            # Default assignments
            self._ensure_default_assignments()
            
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Default data creation error: {e}")
    
    def _ensure_default_assignments(self):
        """Ensure default rank-permission assignments."""
        try:
            # Admin gets all permissions
            admin_rank_id = self.get_rank_id("admin")
            if admin_rank_id:
                all_permissions = self.get_all_permissions()
                for permission in all_permissions:
                    if not self.has_permission(admin_rank_id, permission['id']):
                        self.grant_permission(admin_rank_id, permission['id'])
            
            # Manager gets most permissions except system management
            manager_rank_id = self.get_rank_id("manager")
            if manager_rank_id:
                manager_permissions = [
                    "factures.view", "factures.create", "factures.edit",
                    "devis.view", "devis.create", "calendar.view", "settings.view"
                ]
                for perm_name in manager_permissions:
                    perm_id = self.get_permission_id(perm_name)
                    if perm_id and not self.has_permission(manager_rank_id, perm_id):
                        self.grant_permission(manager_rank_id, perm_id)
            
            # Operator gets basic permissions
            operator_rank_id = self.get_rank_id("operator")
            if operator_rank_id:
                operator_permissions = ["factures.view", "devis.view", "calendar.view"]
                for perm_name in operator_permissions:
                    perm_id = self.get_permission_id(perm_name)
                    if perm_id and not self.has_permission(operator_rank_id, perm_id):
                        self.grant_permission(operator_rank_id, perm_id)
            
            # Viewer gets read-only permissions
            viewer_rank_id = self.get_rank_id("viewer")
            if viewer_rank_id:
                viewer_permissions = ["factures.view", "calendar.view"]
                for perm_name in viewer_permissions:
                    perm_id = self.get_permission_id(perm_name)
                    if perm_id and not self.has_permission(viewer_rank_id, perm_id):
                        self.grant_permission(viewer_rank_id, perm_id)
                        
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Default assignments error: {e}")
    
    # Permission CRUD operations
    def create_permission(self, name: str, category: str, description: str = None) -> bool:
        """Create a new permission."""
        try:
            return self.execute_command('''
                INSERT INTO system_permissions (name, category, description)
                VALUES (?, ?, ?)
            ''', (name, category, description))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Create permission error: {e}")
            return False
    
    def permission_exists(self, name: str) -> bool:
        """Check if a permission exists."""
        try:
            rows = self.execute_query('SELECT 1 FROM system_permissions WHERE name = ? LIMIT 1', (name,))
            return len(rows) > 0
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Permission exists error: {e}")
            return False
    
    def get_permission_id(self, name: str) -> Optional[int]:
        """Get permission ID by name."""
        try:
            rows = self.execute_query('SELECT id FROM system_permissions WHERE name = ? LIMIT 1', (name,))
            return rows[0][0] if rows else None
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Get permission ID error: {e}")
            return None
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Get all permissions."""
        try:
            rows = self.execute_query('''
                SELECT id, name, category, description, created_at, updated_at
                FROM system_permissions
                ORDER BY category, name
            ''')
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Get all permissions error: {e}")
            return []
    
    def delete_permission(self, name: str) -> bool:
        """Delete a permission."""
        try:
            return self.execute_command('DELETE FROM system_permissions WHERE name = ?', (name,))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Delete permission error: {e}")
            return False
    
    # Rank CRUD operations
    def create_rank(self, name: str, description: str = None, is_system: bool = False) -> bool:
        """Create a new rank."""
        try:
            return self.execute_command('''
                INSERT INTO ranks (name, description, is_system)
                VALUES (?, ?, ?)
            ''', (name, description, is_system))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Create rank error: {e}")
            return False
    
    def rank_exists(self, name: str) -> bool:
        """Check if a rank exists."""
        try:
            rows = self.execute_query('SELECT 1 FROM ranks WHERE name = ? LIMIT 1', (name,))
            return len(rows) > 0
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Rank exists error: {e}")
            return False
    
    def get_rank_id(self, name: str) -> Optional[int]:
        """Get rank ID by name."""
        try:
            rows = self.execute_query('SELECT id FROM ranks WHERE name = ? LIMIT 1', (name,))
            return rows[0][0] if rows else None
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Get rank ID error: {e}")
            return None
    
    def get_all_ranks(self) -> List[Dict[str, Any]]:
        """Get all ranks."""
        try:
            rows = self.execute_query('''
                SELECT id, name, description, is_system, created_at, updated_at
                FROM ranks
                ORDER BY is_system DESC, name
            ''')
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Get all ranks error: {e}")
            return []
    
    def delete_rank(self, name: str) -> bool:
        """Delete a rank (and its permissions)."""
        try:
            return self.execute_command('DELETE FROM ranks WHERE name = ?', (name,))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Delete rank error: {e}")
            return False
    
    # Permission assignment operations
    def grant_permission(self, rank_id: int, permission_id: int, granted_by: str = None) -> bool:
        """Grant permission to rank."""
        try:
            return self.execute_command('''
                INSERT OR IGNORE INTO system_rank_permissions (rank_id, permission_id, granted_by)
                VALUES (?, ?, ?)
            ''', (rank_id, permission_id, granted_by))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Grant permission error: {e}")
            return False
    
    def revoke_permission(self, rank_id: int, permission_id: int) -> bool:
        """Revoke permission from rank."""
        try:
            return self.execute_command('''
                DELETE FROM system_rank_permissions
                WHERE rank_id = ? AND permission_id = ?
            ''', (rank_id, permission_id))
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Revoke permission error: {e}")
            return False
    
    def has_permission(self, rank_id: int, permission_id: int) -> bool:
        """Check if rank has permission."""
        try:
            rows = self.execute_query('''
                SELECT 1 FROM system_rank_permissions
                WHERE rank_id = ? AND permission_id = ?
                LIMIT 1
            ''', (rank_id, permission_id))
            return len(rows) > 0
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Has permission error: {e}")
            return False
    
    def get_rank_permissions(self, rank_name: str) -> List[str]:
        """Get all permission names for a rank."""
        try:
            rows = self.execute_query('''
                SELECT p.name
                FROM system_permissions p
                JOIN system_rank_permissions rp ON p.id = rp.permission_id
                JOIN ranks r ON r.id = rp.rank_id
                WHERE r.name = ?
                ORDER BY p.category, p.name
            ''', (rank_name,))
            return [row[0] for row in rows]
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] Get rank permissions error: {e}")
            return []
    
    def get_rank_user_count(self, rank_name: str) -> int:
        """Get number of users with this rank."""
        try:
            # Query the users table (assuming it exists)
            rows = self.execute_query('''
                SELECT COUNT(*) FROM users WHERE rank = ?
            ''', (rank_name,))
            return rows[0][0] if rows else 0
        except Exception as e:
            # Table might not exist yet or no users table
            print(f"[PERMISSION_REPOSITORY] Get rank user count error: {e}")
            return 0
    
    def user_has_permission(self, user_rank: str, permission_name: str) -> bool:
        """Check if user's rank has a specific permission."""
        try:
            rows = self.execute_query('''
                SELECT 1
                FROM system_permissions p
                JOIN system_rank_permissions rp ON p.id = rp.permission_id
                JOIN ranks r ON r.id = rp.rank_id
                WHERE r.name = ? AND p.name = ?
                LIMIT 1
            ''', (user_rank, permission_name))
            return len(rows) > 0
        except Exception as e:
            print(f"[PERMISSION_REPOSITORY] User has permission error: {e}")
            return False
