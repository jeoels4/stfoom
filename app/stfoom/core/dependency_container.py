"""
Dependency Injection Container
=============================
Simple DI container for loose coupling between components.
"""
from typing import Dict, Any, Callable, Type
import threading

class DIContainer:
    """Simple dependency injection container."""
    
    def __init__(self):
        self._services: Dict[str, Any] = {}
        self._factories: Dict[str, Callable] = {}
        self._singletons: Dict[str, Any] = {}
        self._lock = threading.Lock()
    
    def register_singleton(self, interface: str, implementation: Any):
        """Register a singleton service."""
        with self._lock:
            self._singletons[interface] = implementation
    
    def register_factory(self, interface: str, factory: Callable):
        """Register a factory function for a service."""
        with self._lock:
            self._factories[interface] = factory
    
    def register(self, interface: str, implementation: Type):
        """Register a service class."""
        with self._lock:
            self._services[interface] = implementation
    
    def resolve(self, interface: str) -> Any:
        """Resolve a service instance."""
        with self._lock:
            # Check singletons first
            if interface in self._singletons:
                return self._singletons[interface]
            
            # Check factories
            if interface in self._factories:
                return self._factories[interface]()
            
            # Check registered services
            if interface in self._services:
                service_class = self._services[interface]
                return service_class()
            
            raise ValueError(f"Service {interface} not registered")
    
    def is_registered(self, interface: str) -> bool:
        """Check if a service is registered."""
        with self._lock:
            return (interface in self._singletons or 
                   interface in self._factories or 
                   interface in self._services)
    
    def list_services(self) -> list:
        """List all registered services."""
        with self._lock:
            return list(self._singletons.keys()) + list(self._factories.keys()) + list(self._services.keys())

# Global container instance
container = DIContainer()
