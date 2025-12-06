"""
Permission Service - Business Logic Layer
========================================
Service layer for permission and rank management operations.
Provides a clean interface for the UI and handles business logic.
"""

from typing import List, Dict, Optional, Any
from ..data.permission_repository import PermissionRepository


class PermissionService:
    """Service for managing permissions, ranks, and assignments."""
    
    def __init__(self, permission_repository: PermissionRepository):
        """Initialize permission service with repository dependency."""
        self.permission_repository = permission_repository
        print("[PERMISSION_SERVICE] Initialized with repository dependency")
    
    # Permission management
    def create_permission(self, name: str, category: str, description: str = None) -> bool:
        """Create a new permission."""
        try:
            # Validate input
            if not name or not category:
                print(f"[PERMISSION_SERVICE] Invalid input: name='{name}', category='{category}'")
                return False
            
            if self.permission_repository.permission_exists(name):
                print(f"[PERMISSION_SERVICE] Permission already exists: {name}")
                return False
            
            success = self.permission_repository.create_permission(name, category, description)
            if success:
                print(f"[PERMISSION_SERVICE] Created permission: {name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to create permission: {name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Create permission error: {e}")
            return False
    
    def delete_permission(self, name: str) -> bool:
        """Delete a permission."""
        try:
            if not name:
                return False
            
            success = self.permission_repository.delete_permission(name)
            if success:
                print(f"[PERMISSION_SERVICE] Deleted permission: {name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to delete permission: {name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Delete permission error: {e}")
            return False
    
    def get_all_permissions(self) -> List[Dict[str, Any]]:
        """Get all permissions."""
        try:
            permissions = self.permission_repository.get_all_permissions()
            print(f"[PERMISSION_SERVICE] Retrieved {len(permissions)} permissions")
            return permissions
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Get all permissions error: {e}")
            return []
    
    # Rank management
    def create_rank(self, name: str, description: str = None) -> bool:
        """Create a new rank."""
        try:
            # Validate input
            if not name:
                print(f"[PERMISSION_SERVICE] Invalid rank name: '{name}'")
                return False
            
            if self.permission_repository.rank_exists(name):
                print(f"[PERMISSION_SERVICE] Rank already exists: {name}")
                return False
            
            # User-created ranks are not system ranks
            success = self.permission_repository.create_rank(name, description, is_system=False)
            if success:
                print(f"[PERMISSION_SERVICE] Created rank: {name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to create rank: {name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Create rank error: {e}")
            return False
    
    def delete_rank(self, name: str) -> bool:
        """Delete a rank."""
        try:
            if not name:
                return False
            
            # Check if it's a system rank - you might want to prevent deletion
            ranks = self.get_all_ranks()
            system_rank = next((r for r in ranks if r['name'] == name and r.get('is_system')), None)
            if system_rank:
                print(f"[PERMISSION_SERVICE] Cannot delete system rank: {name}")
                return False
            
            success = self.permission_repository.delete_rank(name)
            if success:
                print(f"[PERMISSION_SERVICE] Deleted rank: {name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to delete rank: {name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Delete rank error: {e}")
            return False
    
    def get_all_ranks(self) -> List[Dict[str, Any]]:
        """Get all ranks."""
        try:
            ranks = self.permission_repository.get_all_ranks()
            print(f"[PERMISSION_SERVICE] Retrieved {len(ranks)} ranks")
            return ranks
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Get all ranks error: {e}")
            return []
    
    # Permission assignment
    def grant_permission(self, rank_name: str, permission_name: str, granted_by: str = None) -> bool:
        """Grant permission to rank."""
        try:
            rank_id = self.permission_repository.get_rank_id(rank_name)
            permission_id = self.permission_repository.get_permission_id(permission_name)
            
            if not rank_id:
                print(f"[PERMISSION_SERVICE] Rank not found: {rank_name}")
                return False
            
            if not permission_id:
                print(f"[PERMISSION_SERVICE] Permission not found: {permission_name}")
                return False
            
            if self.permission_repository.has_permission(rank_id, permission_id):
                print(f"[PERMISSION_SERVICE] Rank already has permission: {rank_name} -> {permission_name}")
                return True  # Already granted, consider it success
            
            success = self.permission_repository.grant_permission(rank_id, permission_id, granted_by)
            if success:
                print(f"[PERMISSION_SERVICE] Granted permission: {rank_name} -> {permission_name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to grant permission: {rank_name} -> {permission_name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Grant permission error: {e}")
            return False
    
    def revoke_permission(self, rank_name: str, permission_name: str) -> bool:
        """Revoke permission from rank."""
        try:
            rank_id = self.permission_repository.get_rank_id(rank_name)
            permission_id = self.permission_repository.get_permission_id(permission_name)
            
            if not rank_id:
                print(f"[PERMISSION_SERVICE] Rank not found: {rank_name}")
                return False
            
            if not permission_id:
                print(f"[PERMISSION_SERVICE] Permission not found: {permission_name}")
                return False
            
            success = self.permission_repository.revoke_permission(rank_id, permission_id)
            if success:
                print(f"[PERMISSION_SERVICE] Revoked permission: {rank_name} -> {permission_name}")
            else:
                print(f"[PERMISSION_SERVICE] Failed to revoke permission: {rank_name} -> {permission_name}")
            
            return success
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Revoke permission error: {e}")
            return False
    
    def grant_all_permissions(self, rank_name: str, granted_by: str = None) -> bool:
        """Grant all permissions to rank."""
        try:
            rank_id = self.permission_repository.get_rank_id(rank_name)
            if not rank_id:
                print(f"[PERMISSION_SERVICE] Rank not found: {rank_name}")
                return False
            
            permissions = self.get_all_permissions()
            granted_count = 0
            
            for permission in permissions:
                if not self.permission_repository.has_permission(rank_id, permission['id']):
                    if self.permission_repository.grant_permission(rank_id, permission['id'], granted_by):
                        granted_count += 1
            
            print(f"[PERMISSION_SERVICE] Granted {granted_count} permissions to rank: {rank_name}")
            return True
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Grant all permissions error: {e}")
            return False
    
    def revoke_all_permissions(self, rank_name: str) -> bool:
        """Revoke all permissions from rank."""
        try:
            rank_id = self.permission_repository.get_rank_id(rank_name)
            if not rank_id:
                print(f"[PERMISSION_SERVICE] Rank not found: {rank_name}")
                return False
            
            # Get current permissions and revoke each one
            current_permissions = self.get_rank_permissions(rank_name)
            revoked_count = 0
            
            for permission_name in current_permissions:
                permission_id = self.permission_repository.get_permission_id(permission_name)
                if permission_id and self.permission_repository.revoke_permission(rank_id, permission_id):
                    revoked_count += 1
            
            print(f"[PERMISSION_SERVICE] Revoked {revoked_count} permissions from rank: {rank_name}")
            return True
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Revoke all permissions error: {e}")
            return False
    
    def get_rank_permissions(self, rank_name: str) -> List[str]:
        """Get all permission names for a rank."""
        try:
            permissions = self.permission_repository.get_rank_permissions(rank_name)
            print(f"[PERMISSION_SERVICE] Retrieved {len(permissions)} permissions for rank: {rank_name}")
            return permissions
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Get rank permissions error: {e}")
            return []
    
    def get_rank_user_count(self, rank_name: str) -> int:
        """Get number of users with this rank."""
        try:
            count = self.permission_repository.get_rank_user_count(rank_name)
            return count
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Get rank user count error: {e}")
            return 0
    
    def user_has_permission(self, user_rank: str, permission_name: str) -> bool:
        """Check if user's rank has a specific permission."""
        try:
            has_perm = self.permission_repository.user_has_permission(user_rank, permission_name)
            return has_perm
        except Exception as e:
            print(f"[PERMISSION_SERVICE] User has permission error: {e}")
            return False
    
    # Migration and import functionality
    def import_from_json(self, json_data: Dict[str, Any]) -> bool:
        """Import permissions and ranks from JSON data (for migration)."""
        try:
            imported_count = 0
            
            # Import ranks
            if 'ranks' in json_data:
                for rank_data in json_data['ranks']:
                    name = rank_data.get('name')
                    description = rank_data.get('description', '')
                    
                    if name and not self.permission_repository.rank_exists(name):
                        if self.create_rank(name, description):
                            imported_count += 1
            
            # Import permissions
            if 'permissions' in json_data:
                for perm_data in json_data['permissions']:
                    name = perm_data.get('name')
                    category = perm_data.get('category', 'general')
                    description = perm_data.get('description', '')
                    
                    if name and not self.permission_repository.permission_exists(name):
                        if self.create_permission(name, category, description):
                            imported_count += 1
            
            # Import assignments
            if 'assignments' in json_data:
                for rank_name, permission_names in json_data['assignments'].items():
                    for permission_name in permission_names:
                        self.grant_permission(rank_name, permission_name, granted_by="json_import")
                        imported_count += 1
            
            print(f"[PERMISSION_SERVICE] Imported {imported_count} items from JSON")
            return True
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] JSON import error: {e}")
            return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get permission system statistics."""
        try:
            stats = {
                'total_permissions': len(self.get_all_permissions()),
                'total_ranks': len(self.get_all_ranks()),
                'system_ranks': len([r for r in self.get_all_ranks() if r.get('is_system')]),
                'custom_ranks': len([r for r in self.get_all_ranks() if not r.get('is_system')]),
            }
            
            # Add per-rank permission counts
            stats['rank_permissions'] = {}
            for rank in self.get_all_ranks():
                rank_name = rank['name']
                perm_count = len(self.get_rank_permissions(rank_name))
                user_count = self.get_rank_user_count(rank_name)
                stats['rank_permissions'][rank_name] = {
                    'permission_count': perm_count,
                    'user_count': user_count
                }
            
            return stats
            
        except Exception as e:
            print(f"[PERMISSION_SERVICE] Get statistics error: {e}")
            return {}
