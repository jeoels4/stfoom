"""
User Repository
==============
Repository for user data access operations.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import bcrypt
import json

from .base_repository import BaseRepository

class UserRepository(BaseRepository):
    """Repository for user data access operations."""
    
    def __init__(self):
        super().__init__("users")
    
    def get_entity_name(self) -> str:
        return "User"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate user data before database operations."""
        required_fields = ["username", "full_name", "rank"]
        
        # Check required fields
        for field in required_fields:
            if field not in data or not data[field]:
                print(f"[USER_REPO] Missing required field: {field}")
                return False
        
        # Validate username format
        username = data["username"]
        if len(username) < 3:
            print(f"[USER_REPO] Username too short: {username}")
            return False
        
        # Validate rank - use dynamic ranks from permission system
        try:
            # Import BasicPermissionService to get dynamic ranks
            import sys
            import os
            
            # Add main directory to path to access BasicPermissionService
            main_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            if main_dir not in sys.path:
                sys.path.insert(0, main_dir)
            
            from main import BasicPermissionService
            permission_service = BasicPermissionService()
            valid_ranks = [rank['name'] for rank in permission_service.get_all_ranks()]
        except Exception as e:
            # Fallback to default ranks if permission service is not available
            print(f"[USER_REPO] Warning: Could not load dynamic ranks ({e}), using fallback")
            valid_ranks = ["admin", "manager", "operator", "viewer", "guest"]
        
        if data["rank"] not in valid_ranks:
            print(f"[USER_REPO] Invalid rank: {data['rank']} (valid: {valid_ranks})")
            return False
        
        return True
    
    def transform_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user data before storing in database."""
        transformed = data.copy()
        
        # Ensure boolean fields are properly set
        transformed["is_active"] = bool(transformed.get("is_active", True))
        transformed["force_password_change"] = bool(transformed.get("force_password_change", False))
        transformed["temporary_password"] = bool(transformed.get("temporary_password", False))
        
        # Set timestamps
        if "created_at" not in transformed:
            transformed["created_at"] = datetime.now().isoformat()
        
        # Ensure numeric fields
        transformed["failed_attempts"] = int(transformed.get("failed_attempts", 0))
        
        return transformed
    
    def transform_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform user data after retrieving from database."""
        transformed = data.copy()
        
        # Parse datetime fields
        for field in ["created_at", "last_login", "locked_until", "password_changed_at", "password_reset_expires"]:
            if field in transformed and transformed[field]:
                try:
                    transformed[field] = datetime.fromisoformat(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = None
        
        # Ensure boolean fields
        for field in ["is_active", "force_password_change", "temporary_password"]:
            if field in transformed:
                transformed[field] = bool(transformed[field])
        
        return transformed
    
    def get_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username."""
        users = self.find_by(username=username)
        if users:
            return self.transform_from_storage(users[0])
        return None
    
    def create_user(self, username: str, password: str, full_name: str, rank: str, **kwargs) -> bool:
        """
        Create a new user with hashed password.
        
        Args:
            username: Username
            password: Plain text password
            full_name: Full name
            rank: User rank
            **kwargs: Additional user fields
            
        Returns:
            True if successful, False otherwise
        """
        # Hash the password
        password_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        
        user_data = {
            "username": username,
            "password_hash": password_hash.decode('utf-8'),
            "full_name": full_name,
            "rank": rank,
            "email": kwargs.get("email", ""),
            "is_active": kwargs.get("is_active", True),
            "failed_attempts": 0,
            "force_password_change": kwargs.get("force_password_change", False),
            "temporary_password": kwargs.get("temporary_password", False),
            "password_changed_at": datetime.now().isoformat()
        }
        
        # Add any additional fields
        user_data.update(kwargs)
        
        if not self.validate_data(user_data):
            return False
        
        user_data = self.transform_for_storage(user_data)
        return self.create(user_data)
    
    def update_password(self, user_id: int, new_password: str) -> bool:
        """Update user password with proper hashing."""
        password_hash = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt(rounds=12))
        
        update_data = {
            "password_hash": password_hash.decode('utf-8'),
            "password_changed_at": datetime.now().isoformat(),
            "force_password_change": False,
            "temporary_password": False,
            "failed_attempts": 0
        }
        
        return self.update(user_id, update_data)
    
    def verify_password(self, username: str, password: str) -> bool:
        """Verify user password."""
        user = self.get_by_username(username)
        if not user or not user.get("password_hash"):
            return False
        
        stored = user["password_hash"]
        # Support emergency plaintext format: PLAINTEXT:<pass>
        if stored.startswith("PLAINTEXT:"):
            expected = stored.split(":", 1)[1]
            return password == expected
        try:
            return bcrypt.checkpw(password.encode('utf-8'), stored.encode('utf-8'))
        except Exception as e:
            print(f"[USER_REPO] Password verification error: {e}")
            # As last resort, direct compare (legacy unhashed scenarios)
            return password == stored
    
    def increment_failed_attempts(self, username: str) -> bool:
        """Increment failed login attempts for user (lockout disabled)."""
        user = self.get_by_username(username)
        if not user:
            return False
        # Keep a counter for diagnostics, but do NOT lock accounts
        failed_attempts = user.get("failed_attempts", 0) + 1
        update_data = {
            "failed_attempts": failed_attempts,
            "locked_until": None,  # ensure no lock persists
        }
        return self.update(user["id"], update_data)
    
    def reset_failed_attempts(self, username: str) -> bool:
        """Reset failed login attempts for user."""
        user = self.get_by_username(username)
        if not user:
            return False
        
        update_data = {
            "failed_attempts": 0,
            "locked_until": None,
            "last_login": datetime.now().isoformat()
        }
        
        return self.update(user["id"], update_data)
    
    def is_user_locked(self, username: str) -> bool:
        """Lockout disabled: only inactive users are considered locked."""
        user = self.get_by_username(username)
        if not user:
            return False  # Do not treat unknown as locked
        # Only respect is_active; ignore locked_until
        return not bool(user.get("is_active", True))
    
    def get_active_users(self) -> List[Dict[str, Any]]:
        """Get all active users."""
        users = self.find_by(is_active=True)
        return [self.transform_from_storage(user) for user in users]
    
    def get_users_by_rank(self, rank: str) -> List[Dict[str, Any]]:
        """Get users by rank."""
        users = self.find_by(rank=rank)
        return [self.transform_from_storage(user) for user in users]
