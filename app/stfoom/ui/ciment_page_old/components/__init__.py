"""
Component Registry
=================
Central registry for all Ciment page components

This module provides a centralized way to manage and access
all components in the Ciment page architecture.
"""

from typing import Dict, Type, Any
from ..services.ciment_service import CimentService, get_ciment_service
from .bl_manager import BLManager, create_bl_manager
from .facture_manager import FactureManager, create_facture_manager
from .avoir_manager import AvoirManager, create_avoir_manager

# Component factory registry
COMPONENT_FACTORIES = {
    'bl_manager': create_bl_manager,
    'facture_manager': create_facture_manager,
    'avoir_manager': create_avoir_manager,
}

# Component type registry
COMPONENT_TYPES = {
    'bl_manager': BLManager,
    'facture_manager': FactureManager,
    'avoir_manager': AvoirManager,
}

def get_component_factory(component_name: str):
    """Get factory function for a component."""
    return COMPONENT_FACTORIES.get(component_name)

def get_component_type(component_name: str) -> Type:
    """Get type class for a component."""
    return COMPONENT_TYPES.get(component_name)

def create_component(component_name: str, parent, service: CimentService):
    """Create a component instance."""
    factory = get_component_factory(component_name)
    if factory:
        return factory(parent, service)
    raise ValueError(f"Unknown component: {component_name}")

# Export all for easy access
__all__ = [
    'COMPONENT_FACTORIES',
    'COMPONENT_TYPES', 
    'get_component_factory',
    'get_component_type',
    'create_component',
    'CimentService',
    'get_ciment_service',
    'BLManager',
    'FactureManager', 
    'AvoirManager',
    'create_bl_manager',
    'create_facture_manager',
    'create_avoir_manager'
]
