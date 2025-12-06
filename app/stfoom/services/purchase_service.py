"""
STFOOM Purchase Service Layer

This service provides business logic for purchase management operations,
abstracting away direct database access and providing a clean interface for the UI layer.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class PurchaseService:
    """Service for managing purchase operations."""
    
    def __init__(self, achat_repository):
        """
        Initialize the purchase service.
        
        Args:
            achat_repository: Repository for achat data access
        """
        self.achat_repository = achat_repository
        logger.info("PurchaseService initialized")
    
    def get_all_purchases(self) -> List[Dict]:
        """
        Get all purchase records with proper data formatting.
        
        Returns:
            List of purchase dictionaries with properly parsed taxes
        """
        try:
            purchases = self.achat_repository.fetch_all_achats()
            logger.info(f"Retrieved {len(purchases)} purchases")
            return purchases
        except Exception as e:
            logger.error(f"Error getting all purchases: {e}")
            return []
    
    def get_purchase_by_id(self, purchase_id: int) -> Optional[Dict]:
        """
        Get a single purchase by ID.
        
        Args:
            purchase_id: The ID of the purchase to retrieve
            
        Returns:
            Purchase dictionary or None if not found
        """
        try:
            purchase = self.achat_repository.fetch_achat_by_id(purchase_id)
            if purchase:
                logger.info(f"Retrieved purchase {purchase_id}")
            else:
                logger.warning(f"Purchase {purchase_id} not found")
            return purchase
        except Exception as e:
            logger.error(f"Error getting purchase {purchase_id}: {e}")
            return None
    
    def create_purchase(self, purchase_data: Dict) -> bool:
        """
        Create a new purchase record.
        
        Args:
            purchase_data: Dictionary containing purchase information
            
        Returns:
            True if created successfully, False otherwise
        """
        try:
            # Validate required fields
            if not purchase_data.get('fournisseur'):
                logger.error("Fournisseur is required for purchase creation")
                return False
            
            if not purchase_data.get('date'):
                purchase_data['date'] = datetime.now().strftime('%Y-%m-%d')
            
            # Ensure taxes is a list
            if 'taxes' not in purchase_data:
                purchase_data['taxes'] = []
            
            # Ensure optional alias key exists for consistency
            if 'fournisseur_alias' not in purchase_data:
                purchase_data['fournisseur_alias'] = ''
            success = self.achat_repository.insert_achat(purchase_data)
            if success:
                logger.info(f"Created purchase for fournisseur: {purchase_data.get('fournisseur')}")
            else:
                logger.error("Failed to create purchase")
            return success
        except Exception as e:
            logger.error(f"Error creating purchase: {e}")
            return False
    
    def update_purchase(self, purchase_id: int, purchase_data: Dict) -> bool:
        """
        Update an existing purchase record.
        
        Args:
            purchase_id: The ID of the purchase to update
            purchase_data: Dictionary containing updated purchase information
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            # Ensure taxes is a list
            if 'taxes' in purchase_data and isinstance(purchase_data['taxes'], str):
                try:
                    purchase_data['taxes'] = json.loads(purchase_data['taxes'])
                except:
                    purchase_data['taxes'] = []
            # Ensure alias key exists
            if 'fournisseur_alias' not in purchase_data:
                purchase_data['fournisseur_alias'] = ''
            
            success = self.achat_repository.update_achat(purchase_id, purchase_data)
            if success:
                logger.info(f"Updated purchase {purchase_id}")
            else:
                logger.error(f"Failed to update purchase {purchase_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating purchase {purchase_id}: {e}")
            return False
    
    def delete_purchase(self, purchase_id: int) -> bool:
        """
        Delete a purchase record and clean up related data.
        
        Args:
            purchase_id: The ID of the purchase to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            success = self.achat_repository.delete_achat(purchase_id)
            if success:
                logger.info(f"Deleted purchase {purchase_id}")
            else:
                logger.error(f"Failed to delete purchase {purchase_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting purchase {purchase_id}: {e}")
            return False
    
    def get_purchase_statistics(self) -> Dict:
        """
        Get statistics about purchases.
        
        Returns:
            Dictionary containing purchase statistics
        """
        try:
            purchases = self.get_all_purchases()
            total_count = len(purchases)
            total_amount = sum(float(p.get('ttc', 0)) for p in purchases if p.get('ttc'))
            
            paid_purchases = [p for p in purchases if p.get('paiement_statut') == 'payé']
            pending_purchases = [p for p in purchases if p.get('paiement_statut') != 'payé']
            
            return {
                'total_count': total_count,
                'total_amount': total_amount,
                'paid_count': len(paid_purchases),
                'pending_count': len(pending_purchases),
                'paid_amount': sum(float(p.get('ttc', 0)) for p in paid_purchases if p.get('ttc')),
                'pending_amount': sum(float(p.get('ttc', 0)) for p in pending_purchases if p.get('ttc'))
            }
        except Exception as e:
            logger.error(f"Error getting purchase statistics: {e}")
            return {
                'total_count': 0,
                'total_amount': 0,
                'paid_count': 0,
                'pending_count': 0,
                'paid_amount': 0,
                'pending_amount': 0
            }
    
    def get_payment_status(self, achat_id: int, montant_total: float) -> Dict:
        """
        Get payment status for a purchase.
        
        Args:
            achat_id: Purchase ID
            montant_total: Total amount
            
        Returns:
            Dictionary with payment status information
        """
        try:
            # TODO: Implement proper payment status logic
            # For now, return default status to prevent crashes
            return {
                'statut': 'non_payé',
                'montant_paye': 0
            }
        except Exception as e:
            logger.error(f"Error getting payment status for achat {achat_id}: {e}")
            return {
                'statut': 'inconnu',
                'montant_paye': 0
            }
    
    def get_payments(self, achat_id: int) -> List[Dict]:
        """
        Get payments for a purchase.
        
        Args:
            achat_id: Purchase ID
            
        Returns:
            List of payment dictionaries
        """
        try:
            # TODO: Implement proper payment retrieval logic
            # For now, return empty list to prevent crashes
            return []
        except Exception as e:
            logger.error(f"Error getting payments for achat {achat_id}: {e}")
            return []
    
    # ===== SUPPLIER MANAGEMENT METHODS =====
    
    def get_all_suppliers(self) -> List[Dict]:
        """
        Get all supplier records.
        
        Returns:
            List of supplier dictionaries
        """
        try:
            suppliers = self.achat_repository.get_all_suppliers()
            logger.info(f"Retrieved {len(suppliers)} suppliers")
            return suppliers
        except Exception as e:
            logger.error(f"Error getting all suppliers: {e}")
            return []
    
    def create_supplier(self, supplier_data: Dict) -> bool:
        """
        Create a new supplier.
        
        Args:
            supplier_data: Dictionary containing supplier information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.achat_repository.create_supplier(supplier_data)
            if success:
                logger.info(f"Created supplier: {supplier_data.get('nom_fournisseur', 'Unknown')}")
            return success
        except Exception as e:
            logger.error(f"Error creating supplier: {e}")
            return False
    
    def update_supplier(self, supplier_id: int, supplier_data: Dict) -> bool:
        """
        Update an existing supplier.
        
        Args:
            supplier_id: ID of the supplier to update
            supplier_data: Dictionary containing updated supplier information
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.achat_repository.update_supplier(supplier_id, supplier_data)
            if success:
                logger.info(f"Updated supplier ID {supplier_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating supplier {supplier_id}: {e}")
            return False
    
    def delete_supplier(self, supplier_id: int) -> bool:
        """
        Delete a supplier.
        
        Args:
            supplier_id: ID of the supplier to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.achat_repository.delete_supplier(supplier_id)
            if success:
                logger.info(f"Deleted supplier ID {supplier_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting supplier {supplier_id}: {e}")
            return False
    
    def get_next_supplier_code(self) -> str:
        """
        Get the next available supplier code (411xxx format).
        
        Returns:
            Next available supplier code
        """
        try:
            next_code = self.achat_repository.get_next_supplier_code()
            logger.info(f"Generated next supplier code: {next_code}")
            return next_code
        except Exception as e:
            logger.error(f"Error generating next supplier code: {e}")
            return "411001"  # Default fallback

    def get_available_taxes(self) -> List[Dict]:
        """
        Get all available taxes for purchase management.
        
        Returns:
            List of tax dictionaries with name, value, type, etc.
        """
        try:
            from ..logic import taxes as tax_system
            taxes = tax_system.get_all_taxes()
            logger.info(f"Retrieved {len(taxes)} available taxes for purchases")
            return taxes
        except ImportError as e:
            logger.warning(f"Tax system not available: {e}")
            # Fallback to common tax types
            return [
                {'name': 'TVA 7%', 'value': 7.0, 'type': 'percentage'},
                {'name': 'TVA 19%', 'value': 19.0, 'type': 'percentage'},
                {'name': 'TVA DEDUCTIBLE', 'value': 19.0, 'type': 'percentage'},
                {'name': 'FODEC', 'value': 1.0, 'type': 'percentage'},
                {'name': 'Transport', 'value': 0.0, 'type': 'fixed'},
                {'name': 'Droit de Timbre', 'value': 1.0, 'type': 'fixed'}
            ]
        except Exception as e:
            logger.error(f"Error getting available taxes: {e}")
            return []
