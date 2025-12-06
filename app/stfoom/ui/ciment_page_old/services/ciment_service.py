"""
Ciment Business Logic Service
============================
Extracted from the monolithic ciment_page_simple.py

This service handles all business logic for cement/raw materials operations:
- Bon de Livraison creation and management
- Facture generation and processing
- Avoir calculations and monthly tracking
- Data validation and business rules
- Statistics and reporting calculations

Separating this from UI improves:
- Testability (can unit test business logic independently)
- Reusability (can be used by different UI components)
- Maintainability (single responsibility principle)
- Performance (lighter UI components)
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
import sys
import os

# Add path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from stfoom.logicold.ciment import (
    BonLivraison, CimentFacture, create_bon_livraison, get_all_bons_livraison,
    create_ciment_facture, get_all_ciment_factures, get_bls_en_attente,
    get_next_bl_numero, get_next_facture_numero, delete_bon_livraison
)
from app.stfoom.logicold.old.secure_database import exec_read_all

# Import unified logger
try:
    from unified_logger import log_service_error, log_service_info
except ImportError:
    def log_service_error(service, message, context=None, exception=None):
        print(f"[SERVICE ERROR] {service}: {message}")
    def log_service_info(service, message, context=None):
        print(f"[SERVICE INFO] {service}: {message}")

@dataclass
class BLData:
    """Data structure for Bon de Livraison."""
    numero: str
    date_livraison: date
    fournisseur_id: str
    quantite: float
    montant: float
    unite: str = "tonnes"
    description: Optional[str] = None
    
    # Legacy compatibility fields
    chauffeur: Optional[str] = None
    produit: Optional[str] = None
    prix_unitaire: Optional[float] = None
    client: Optional[str] = None
    chantier: Optional[str] = None

@dataclass
class FactureData:
    """Data structure for Facture."""
    numero: str
    date: date
    client: str
    bls: List[str]
    montant_total: float

class CimentService:
    """Service for cement/raw materials business operations."""
    
    def __init__(self):
        """Initialize the ciment service."""
        self.current_user_id = None
        log_service_info("CimentService", "Service initialized")
    
    def set_current_user(self, user_id: Optional[str]):
        """Set the current user for operations."""
        self.current_user_id = user_id
        log_service_info("CimentService", f"Current user set to: {user_id}")
    
    # ==================== BON DE LIVRAISON OPERATIONS ====================
    
    def create_bon_livraison(self, bl_data: BLData) -> bool:
        """Create a new Bon de Livraison."""
        try:
            log_service_info("CimentService", f"Creating BL: {bl_data.numero}")
            
            # Validate data
            validation_result = self._validate_bl_data(bl_data)
            if not validation_result['valid']:
                log_service_error("CimentService", f"BL validation failed: {validation_result['message']}")
                return False
            
            # Create BL using existing logic
            success, message, bl_id = create_bon_livraison(
                numero=bl_data.numero,
                date_livraison=bl_data.date_livraison,
                fournisseur_id=bl_data.fournisseur_id,
                quantite=bl_data.quantite,
                montant=bl_data.montant,
                unite=bl_data.unite,
                description=bl_data.description,
                created_by=self.current_user_id
            )
            
            if success:
                log_service_info("CimentService", f"BL created successfully: {bl_data.numero} (ID: {bl_id})")
            else:
                log_service_error("CimentService", f"Failed to create BL: {bl_data.numero} - {message}")
            
            return success
            
        except Exception as e:
            log_service_error("CimentService", f"Error creating BL", {"bl_numero": bl_data.numero}, e)
            return False
    
    def get_all_bons_livraison(self) -> List[BonLivraison]:
        """Get all Bons de Livraison."""
        try:
            bls = get_all_bons_livraison()
            log_service_info("CimentService", f"Retrieved {len(bls)} BLs")
            return bls
        except Exception as e:
            log_service_error("CimentService", "Error retrieving BLs", None, e)
            return []
    
    def delete_bon_livraison(self, bl_id: int) -> bool:
        """Delete a Bon de Livraison."""
        try:
            success, message = delete_bon_livraison(bl_id)
            if success:
                log_service_info("CimentService", f"BL deleted: ID {bl_id}")
            else:
                log_service_error("CimentService", f"Failed to delete BL ID {bl_id}: {message}")
            return success
        except Exception as e:
            log_service_error("CimentService", f"Error deleting BL: ID {bl_id}", None, e)
            return False
    
    def get_next_bl_numero(self) -> str:
        """Get the next BL numero."""
        try:
            numero = get_next_bl_numero()
            log_service_info("CimentService", f"Next BL numero: {numero}")
            return numero
        except Exception as e:
            log_service_error("CimentService", "Error getting next BL numero", None, e)
            return "BL001"
    
    # ==================== FACTURE OPERATIONS ====================
    
    def create_facture(self, facture_data: FactureData) -> bool:
        """Create a new facture from BLs."""
        try:
            log_service_info("CimentService", f"Creating facture: {facture_data.numero}")
            
            # Validate facture data
            validation_result = self._validate_facture_data(facture_data)
            if not validation_result['valid']:
                log_service_error("CimentService", f"Facture validation failed: {validation_result['message']}")
                return False
            
            # Create facture using existing logic
            facture = CimentFacture(
                numero=facture_data.numero,
                date=facture_data.date,
                client=facture_data.client,
                bls=facture_data.bls,
                montant_total=facture_data.montant_total
            )
            
            success = create_ciment_facture(facture)
            
            if success:
                log_service_info("CimentService", f"Facture created successfully: {facture_data.numero}")
            else:
                log_service_error("CimentService", f"Failed to create facture: {facture_data.numero}")
            
            return success
            
        except Exception as e:
            log_service_error("CimentService", f"Error creating facture", {"facture_numero": facture_data.numero}, e)
            return False
    
    def get_all_factures(self) -> List[CimentFacture]:
        """Get all factures."""
        try:
            factures = get_all_ciment_factures()
            log_service_info("CimentService", f"Retrieved {len(factures)} factures")
            return factures
        except Exception as e:
            log_service_error("CimentService", "Error retrieving factures", None, e)
            return []
    
    def get_bls_en_attente(self) -> List[BonLivraison]:
        """Get BLs waiting for facturing."""
        try:
            bls = get_bls_en_attente()
            log_service_info("CimentService", f"Retrieved {len(bls)} BLs en attente")
            return bls
        except Exception as e:
            log_service_error("CimentService", "Error retrieving BLs en attente", None, e)
            return []
    
    def get_next_facture_numero(self) -> str:
        """Get the next facture numero."""
        try:
            numero = get_next_facture_numero()
            log_service_info("CimentService", f"Next facture numero: {numero}")
            return numero
        except Exception as e:
            log_service_error("CimentService", "Error getting next facture numero", None, e)
            return "F001"
    
    # ==================== STATISTICS AND REPORTING ====================
    
    def calculate_monthly_statistics(self, month: int, year: int) -> Dict[str, Any]:
        """Calculate monthly statistics."""
        try:
            # Get BLs for the specified month
            all_bls = self.get_all_bons_livraison()
            monthly_bls = [bl for bl in all_bls 
                          if bl.date_livraison.month == month and bl.date_livraison.year == year]
            
            # Calculate statistics
            stats = {
                'total_bls': len(monthly_bls),
                'total_quantity': sum(bl.quantite for bl in monthly_bls),
                'total_value': sum(bl.montant for bl in monthly_bls),
                'fournisseurs': {}
            }
            
            # Group by fournisseurs
            for bl in monthly_bls:
                fournisseur = bl.fournisseur_nom or bl.fournisseur_id
                if fournisseur not in stats['fournisseurs']:
                    stats['fournisseurs'][fournisseur] = {'quantity': 0, 'value': 0}
                stats['fournisseurs'][fournisseur]['quantity'] += bl.quantite
                stats['fournisseurs'][fournisseur]['value'] += bl.montant
            
            log_service_info("CimentService", f"Calculated statistics for {month}/{year}")
            return stats
            
        except Exception as e:
            log_service_error("CimentService", f"Error calculating monthly statistics", 
                            {"month": month, "year": year}, e)
            return {}
    
    # ==================== VALIDATION METHODS ====================
    
    def _validate_bl_data(self, bl_data: BLData) -> Dict[str, Any]:
        """Validate BL data."""
        try:
            # Basic validation
            if not bl_data.numero:
                return {'valid': False, 'message': 'Numero is required'}
            
            if not bl_data.fournisseur_id:
                return {'valid': False, 'message': 'Fournisseur is required'}
            
            if bl_data.quantite <= 0:
                return {'valid': False, 'message': 'Quantité must be positive'}
            
            if bl_data.montant <= 0:
                return {'valid': False, 'message': 'Montant must be positive'}
            
            return {'valid': True, 'message': 'Valid'}
            
        except Exception as e:
            log_service_error("CimentService", "Error validating BL data", None, e)
            return {'valid': False, 'message': f'Validation error: {e}'}
    
    def _validate_facture_data(self, facture_data: FactureData) -> Dict[str, Any]:
        """Validate facture data."""
        try:
            # Basic validation
            if not facture_data.numero:
                return {'valid': False, 'message': 'Numero is required'}
            
            if not facture_data.client:
                return {'valid': False, 'message': 'Client is required'}
            
            if not facture_data.bls:
                return {'valid': False, 'message': 'At least one BL is required'}
            
            if facture_data.montant_total <= 0:
                return {'valid': False, 'message': 'Montant total must be positive'}
            
            return {'valid': True, 'message': 'Valid'}
            
        except Exception as e:
            log_service_error("CimentService", "Error validating facture data", None, e)
            return {'valid': False, 'message': f'Validation error: {e}'}

# Global service instance
ciment_service = CimentService()

# Convenience functions for backwards compatibility
def get_ciment_service() -> CimentService:
    """Get the global ciment service instance."""
    return ciment_service
