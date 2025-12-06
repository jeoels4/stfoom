"""
Authentication Manager Wrapper
==============================
Provides a global auth_manager compatible with legacy code.
This wraps the UserService to provide the auth_manager interface.
"""

from typing import Optional
from ..data.models import User

class AuthManager:
    """Global authentication manager singleton."""
    
    def __init__(self):
        self._current_user: Optional[User] = None
        self._user_service = None
        
    def initialize(self, user_service):
        """Initialize with user service from DI container."""
        self._user_service = user_service
        
    @property
    def current_user(self) -> Optional[User]:
        """Get current logged-in user."""
        if self._user_service:
            return self._user_service.get_current_user()
        return self._current_user
    
    @current_user.setter
    def current_user(self, user: Optional[User]):
        """Set current user."""
        self._current_user = user
        if self._user_service:
            self._user_service.set_current_user(user)
    
    def login(self, username: str, password: str):
        """Login user."""
        if self._user_service:
            success, user, message = self._user_service.login(username, password)
            if success:
                self._current_user = user
            return success, user, message
        return False, None, "User service not initialized"
    
    def logout(self):
        """Logout current user."""
        self._current_user = None
        if self._user_service:
            self._user_service.logout()
        return True
    
    def is_admin(self) -> bool:
        """Check if current user is admin."""
        if self.current_user:
            return self.current_user.rank == "admin"
        return False
    
    def get_current_user(self):
        """Get current user (legacy method)."""
        return self.current_user

# Global singleton instance
auth_manager = AuthManager()

# Legacy classes for compatibility
class UserRank:
    ADMIN = "admin"
    MANAGER = "manager"
    OPERATOR = "operator"
    VIEWER = "viewer"
    GUEST = "guest"

class ActionType:
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    PRINT = "print"
    EXPORT = "export"
    IMPORT = "import"
