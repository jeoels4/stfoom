"""
Dependency Injection Container
=============================
Simple dependency injection container for STFOOM.
"""
from typing import Dict, Any, Callable, TypeVar, Type

T = TypeVar('T')

class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
    
    def register(self, name: str, factory: Callable[[], T], singleton: bool = True) -> None:
        """
        Register a service with the container.
        
        Args:
            name: Service name
            factory: Factory function to create the service
            singleton: Whether to create only one instance
        """
        self._services[name] = factory
        if not singleton and name in self._singletons:
            del self._singletons[name]
    
    def register_instance(self, name: str, instance: T) -> None:
        """Register a pre-created instance."""
        self._singletons[name] = instance
        if name in self._services:
            del self._services[name]
    
    def get(self, name: str) -> Any:
        """
        Get a service instance.
        
        Args:
            name: Service name
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service is not registered
        """
        # Check if we have a singleton instance
        if name in self._singletons:
            return self._singletons[name]
        
        # Check if we have a factory
        if name in self._services:
            factory = self._services[name]
            instance = factory()
            
            # Store as singleton by default
            self._singletons[name] = instance
            return instance
        
        raise KeyError(f"Service '{name}' is not registered")
    
    def has(self, name: str) -> bool:
        """Check if a service is registered."""
        return name in self._services or name in self._singletons
    
    def clear(self) -> None:
        """Clear all registered services."""
        self._services.clear()
        self._singletons.clear()

# Global container instance
container = DIContainer()
