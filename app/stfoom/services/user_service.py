"""
User Service
===========
Business logic service for user management.
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import secrets
import string

from ..data.user_repository import UserRepository
from ..data.models import User

class UserService:
    """Service for user management business logic."""
    
    def __init__(self):
        self.user_repo = UserRepository()
        self._current_user = None  # Session management
    
    def authenticate_user(self, username: str, password: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Authenticate a user.
        
        Args:
            username: Username
            password: Password
            
        Returns:
            Tuple of (success, user_data, message)
        """
        if not username or not password:
            return False, None, "Username and password are required"
        
        # Check if user exists
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, None, "Invalid username or password"
        
        # Check if account is locked
        if self.user_repo.is_user_locked(username):
            return False, None, "Account is locked. Please try again later or contact administrator."
        
        # Verify password
        if not self.user_repo.verify_password(username, password):
            # Increment failed attempts
            self.user_repo.increment_failed_attempts(username)
            return False, None, "Invalid username or password"
        
        # Reset failed attempts on successful login
        self.user_repo.reset_failed_attempts(username)
        
        # Remove sensitive data before returning
        safe_user_data = {k: v for k, v in user.items() if k != "password_hash"}
        
        return True, safe_user_data, "Authentication successful"
    
    def create_user(self, username: str, password: str, full_name: str, rank: str, 
                   email: str = "", **kwargs) -> Tuple[bool, str]:
        """
        Create a new user.
        
        Args:
            username: Username
            password: Password  
            full_name: Full name
            rank: User rank
            email: Email address
            **kwargs: Additional user fields
            
        Returns:
            Tuple of (success, message)
        """
        # Check if username already exists
        existing_user = self.user_repo.get_by_username(username)
        if existing_user:
            return False, "Username already exists"
        
        # Validate password strength
        if not self._validate_password_strength(password):
            return False, "Password does not meet security requirements (minimum 8 characters, must contain letters and numbers)"
        
        # Create the user
        success = self.user_repo.create_user(
            username=username,
            password=password,
            full_name=full_name,
            rank=rank,
            email=email,
            **kwargs
        )
        
        if success:
            return True, "User created successfully"
        else:
            return False, "Failed to create user"
    
    def update_user_password(self, username: str, new_password: str, 
                            current_password: str = None) -> Tuple[bool, str]:
        """
        Update user password.
        
        Args:
            username: Username
            new_password: New password
            current_password: Current password (for verification)
            
        Returns:
            Tuple of (success, message)
        """
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found"
        
        # Verify current password if provided
        if current_password:
            if not self.user_repo.verify_password(username, current_password):
                return False, "Current password is incorrect"
        
        # Validate new password strength
        if not self._validate_password_strength(new_password):
            return False, "New password does not meet security requirements"
        
        # Update password
        success = self.user_repo.update_password(user["id"], new_password)
        
        if success:
            return True, "Password updated successfully"
        else:
            return False, "Failed to update password"
    
    def generate_temporary_password(self, username: str) -> Tuple[bool, str, Optional[str]]:
        """
        Generate a temporary password for a user.
        
        Args:
            username: Username
            
        Returns:
            Tuple of (success, message, temporary_password)
        """
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found", None
        
        # Generate temporary password
        temp_password = self._generate_random_password()
        
        # Update user with temporary password
        success = self.user_repo.update_password(user["id"], temp_password)
        if success:
            # Mark as temporary and force change
            update_data = {
                "temporary_password": True,
                "force_password_change": True,
                "failed_attempts": 0
            }
            self.user_repo.update(user["id"], update_data)
            
            return True, "Temporary password generated", temp_password
        else:
            return False, "Failed to generate temporary password", None
    
    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username (without password hash)."""
        user = self.user_repo.get_by_username(username)
        if user:
            # Remove sensitive data
            return {k: v for k, v in user.items() if k != "password_hash"}
        return None
    
    def get_all_users(self) -> List[User]:
        """Get all users (without password hashes)."""
        users = self.user_repo.get_all()
        user_objects = []
        for user in users:
            # Remove password hash before converting
            safe_user_data = {k: v for k, v in user.items() if k != "password_hash"}
            user_objects.append(self._dict_to_user(safe_user_data))
        return user_objects
    
    def get_active_users(self) -> List[User]:
        """Get all active users."""
        users = self.user_repo.get_active_users()
        user_objects = []
        for user in users:
            # Remove password hash before converting
            safe_user_data = {k: v for k, v in user.items() if k != "password_hash"}
            user_objects.append(self._dict_to_user(safe_user_data))
        return user_objects
    
    def get_users_by_rank(self, rank: str) -> List[User]:
        """Get users by rank."""
        users = self.user_repo.get_users_by_rank(rank)
        user_objects = []
        for user in users:
            # Remove password hash before converting
            safe_user_data = {k: v for k, v in user.items() if k != "password_hash"}
            user_objects.append(self._dict_to_user(safe_user_data))
        return user_objects
    
    def activate_user(self, username: str) -> Tuple[bool, str]:
        """Activate a user account."""
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found"
        
        update_data = {
            "is_active": True,
            "failed_attempts": 0,
            "locked_until": None
        }
        
        success = self.user_repo.update(user["id"], update_data)
        if success:
            return True, "User activated successfully"
        else:
            return False, "Failed to activate user"
    
    def deactivate_user(self, username: str) -> Tuple[bool, str]:
        """Deactivate a user account."""
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found"
        
        update_data = {"is_active": False}
        
        success = self.user_repo.update(user["id"], update_data)
        if success:
            return True, "User deactivated successfully"
        else:
            return False, "Failed to deactivate user"
    
    def update_user_info(self, username: str, **kwargs) -> Tuple[bool, str]:
        """Update user information (non-password fields)."""
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found"
        
        # Remove sensitive fields that shouldn't be updated this way
        update_data = {k: v for k, v in kwargs.items() 
                      if k not in ["password_hash", "id", "username"]}
        
        if not update_data:
            return False, "No valid fields to update"
        
        success = self.user_repo.update(user["id"], update_data)
        if success:
            return True, "User information updated successfully"
        else:
            return False, "Failed to update user information"
    
    def unlock_user(self, username: str) -> Tuple[bool, str]:
        """Unlock a locked user account."""
        user = self.user_repo.get_by_username(username)
        if not user:
            return False, "User not found"
        
        update_data = {
            "failed_attempts": 0,
            "locked_until": None
        }
        
        success = self.user_repo.update(user["id"], update_data)
        if success:
            return True, "User unlocked successfully"
        else:
            return False, "Failed to unlock user"
    
    def check_user_permissions(self, username: str, required_rank: str) -> bool:
        """
        Check if user has sufficient permissions.
        
        Rank hierarchy: admin > manager > operator > viewer > guest
        """
        user = self.user_repo.get_by_username(username)
        if not user or not user.get("is_active"):
            return False
        
        rank_hierarchy = {
            "guest": 1,
            "viewer": 2, 
            "operator": 3,
            "manager": 4,
            "admin": 5
        }
        
        user_rank_level = rank_hierarchy.get(user.get("rank", "guest"), 1)
        required_rank_level = rank_hierarchy.get(required_rank, 5)
        
        return user_rank_level >= required_rank_level
    
    def _validate_password_strength(self, password: str) -> bool:
        """Validate password meets security requirements."""
        if len(password) < 8:
            return False
        
        has_letter = any(c.isalpha() for c in password)
        has_number = any(c.isdigit() for c in password)
        
        return has_letter and has_number
    
    def _generate_random_password(self, length: int = 12) -> str:
        """Generate a random password."""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))

    # ✅ PHASE 2A MIGRATION: Compatibility methods for user_management_page
    def update_user(self, user_id: int, **kwargs) -> Tuple[bool, str]:
        """
        Update user by ID (compatibility method for user_management_page).
        
        Args:
            user_id: User ID
            **kwargs: Fields to update (full_name, rank, email, is_active, failed_attempts, locked_until)
            
        Returns:
            Tuple of (success, message)
        """
        # First get the user by ID to find username
        users = self.user_repo.get_all()
        user = next((u for u in users if u.get('id') == user_id), None)
        
        if not user:
            return False, f"User with ID {user_id} not found"
        
        username = user['username']
        
        # Handle special cases
        if 'is_active' in kwargs:
            if kwargs['is_active']:
                return self.activate_user(username)
            else:
                return self.deactivate_user(username)
        
        if 'failed_attempts' in kwargs and kwargs['failed_attempts'] == 0:
            return self.unlock_user(username)
        
        # For other fields, use update_user_info
        return self.update_user_info(username, **kwargs)
    
    def change_password(self, user_id: int, new_password: str) -> Tuple[bool, str]:
        """
        Change user password by ID (compatibility method for user_management_page).
        
        Args:
            user_id: User ID
            new_password: New password
            
        Returns:
            Tuple of (success, message)
        """
        # First get the user by ID to find username
        users = self.user_repo.get_all()
        user = next((u for u in users if u.get('id') == user_id), None)
        
        if not user:
            return False, f"User with ID {user_id} not found"
        
        return self.update_user_password(user['username'], new_password)

    def _dict_to_user(self, user_dict: Dict[str, Any]) -> User:
        """Convert dictionary to User object."""
        # Helper function to parse datetime strings
        def parse_datetime(value):
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                try:
                    # Try common datetime formats
                    formats = [
                        "%Y-%m-%d %H:%M:%S",           # Standard SQL datetime
                        "%Y-%m-%d %H:%M:%S.%f",        # With microseconds  
                        "%Y-%m-%dT%H:%M:%S.%f",        # ISO format with microseconds
                        "%Y-%m-%dT%H:%M:%S",           # ISO format without microseconds
                        "%Y-%m-%d"                     # Date only
                    ]
                    for fmt in formats:
                        try:
                            return datetime.strptime(value, fmt)
                        except ValueError:
                            continue
                    # If no format matches, return None
                    return None
                except:
                    return None
            return value
        
        return User(
            id=user_dict.get('id', 0),
            username=user_dict.get('username', ''),
            full_name=user_dict.get('full_name', ''),
            rank=user_dict.get('rank', ''),
            email=user_dict.get('email', ''),
            is_active=bool(user_dict.get('is_active', True)),  # Convert to boolean
            created_at=parse_datetime(user_dict.get('created_at')) or datetime.now(),
            last_login=parse_datetime(user_dict.get('last_login')),
            failed_attempts=user_dict.get('failed_attempts', 0),
            locked_until=parse_datetime(user_dict.get('locked_until')),
            force_password_change=bool(user_dict.get('force_password_change', False)),  # Convert to boolean
            temporary_password=bool(user_dict.get('temporary_password', False)),  # Convert to boolean
            password_changed_at=parse_datetime(user_dict.get('password_changed_at'))
        )

    # Session management - replaces auth_manager functionality
    
    def get_current_user(self) -> Optional[User]:
        """Get the currently logged-in user."""
        return self._current_user
    
    def set_current_user(self, user: Optional[User]) -> None:
        """Set the current user (for login/logout)."""
        self._current_user = user
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[User], str]:
        """
        Login user and set current session.
        
        Returns:
            Tuple of (success, user, message)
        """
        success, user_data, message = self.authenticate_user(username, password)
        if success and user_data:
            # Convert dict to User object and set as current user
            user_obj = self._dict_to_user(user_data)
            self.set_current_user(user_obj)
            return True, user_obj, message
        return False, None, message
    
    def logout(self) -> None:
        """Logout current user."""
        self._current_user = None
    
    def is_admin_or_manager(self, user: User) -> bool:
        """Check if user is admin or manager."""
        if not user:
            return False
        return user.rank in ["admin", "manager"]
    
    def check_permission(self, resource: str, action: str) -> bool:
        """Check if current user has permission for resource.action."""
        if not self._current_user:
            return False
        
        # Admin has all permissions
        if self._current_user.rank == "admin":
            return True
            
        # Manager permissions (subset of admin)
        if self._current_user.rank == "manager":
            manager_permissions = {
                "users": ["view"],  # Can't create/delete users
                "bank": ["view", "edit"],
                "sync": ["view"],
                # Add other manager permissions as needed
            }
            return action in manager_permissions.get(resource, [])
        
        # User permissions (very limited)
        user_permissions = {
            "profile": ["view", "edit"],
            "facture": ["view", "create"],
            "devis": ["view", "create"],
            # Add other user permissions as needed
        }
        return action in user_permissions.get(resource, [])
    
    def create_user(self, username: str, password: str, user_data: dict) -> bool:
        """Create a new user account."""
        try:
            # Check if username already exists
            if self.user_repo.get_by_username(username):
                return False
            
            # Create user data dict
            create_data = {
                'username': username,
                'password': password,  # UserRepository will hash it
                'full_name': user_data.get('full_name', ''),
                'rank': user_data.get('rank', 'user'),
                'email': user_data.get('email', ''),
                'is_active': user_data.get('is_active', True)
            }
            
            # Create the user
            success = self.user_repo.create_user(**create_data)
            return success
            
        except Exception as e:
            print(f"[USER_SERVICE] Error creating user: {e}")
            return False
    
    def update_user(self, username: str, user_data: dict) -> bool:
        """Update user information (non-password fields)."""
        try:
            user = self.user_repo.get_by_username(username)
            if not user:
                return False
            
            # Filter out fields that shouldn't be updated via this method
            update_data = {k: v for k, v in user_data.items() 
                          if k not in ['id', 'username', 'password', 'password_hash']}
            
            if not update_data:
                return False
            
            success = self.user_repo.update(user['id'], update_data)
            return success
            
        except Exception as e:
            print(f"[USER_SERVICE] Error updating user: {e}")
            return False
    
    def delete_user(self, username: str) -> bool:
        """Delete a user account (actually deactivates it for safety)."""
        try:
            # For safety, we deactivate rather than delete
            return self.update_user(username, {'is_active': False})
        except Exception as e:
            print(f"[USER_SERVICE] Error deleting user: {e}")
            return False
    
    def reset_password(self, username: str, new_password: str) -> bool:
        """Reset user password (admin function - bypasses password validation)."""
        try:
            user = self.user_repo.get_by_username(username)
            if not user:
                print(f"[USER_SERVICE] User not found: {username}")
                return False
            
            # Admin reset - bypass password strength validation
            success = self.user_repo.update_password(user["id"], new_password)
            
            if success:
                print(f"[USER_SERVICE] Password reset successful for: {username}")
                return True
            else:
                print(f"[USER_SERVICE] Failed to update password for: {username}")
                return False
                
        except Exception as e:
            print(f"[USER_SERVICE] Error resetting password: {e}")
            return False
        # Basic permission logic - extend as needed
        if self._current_user.rank == "manager":
            return True  # Manager has most permissions
            
        # Regular users have limited permissions
        return action in ["view", "read"]
    
    def initialize_system(self) -> None:
        """Initialize the user system - replaces initialize_access_control."""
        try:
            # Ensure admin user exists
            admin_user = self.get_user_by_username("admin")
            if not admin_user:
                # Create default admin user
                success, msg = self.create_user(
                    username="admin",
                    password="admin123",  # Should be changed on first login
                    full_name="Administrator",
                    rank="admin",
                    email="admin@stfoom.com"
                )
                if success:
                    print("[USER SERVICE] Default admin user created")
                else:
                    print(f"[USER SERVICE] Failed to create admin user: {msg}")
            
            print("[USER SERVICE] User system initialized")
        except Exception as e:
            print(f"[USER SERVICE] Initialization error: {e}")
            raise
