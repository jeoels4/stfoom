"""
STFOOM Caisse Service Layer

This service provides business logic for cash management operations,
abstracting away direct database access and providing a clean interface for the UI layer.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class CaisseService:
    """Service for managing cash transactions and financial operations."""
    
    def __init__(self, caisse_repository):
        """
        Initialize the caisse service.
        
        Args:
            caisse_repository: Repository for caisse data access
        """
        self.caisse_repository = caisse_repository
        logger.info("CaisseService initialized")
    
    # ========================== Transaction Management ==========================
    
    def get_all_transactions(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict]:
        """
        Get all cash transactions with optional date filtering.
        
        Args:
            start_date: Start date filter (YYYY-MM-DD)
            end_date: End date filter (YYYY-MM-DD)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            return self.caisse_repository.get_transactions(start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def create_transaction(self, montant: float, date_str: str, type_: str, 
                          description: str = "", nfacture: Optional[int] = None, 
                          num_facture: Optional[str] = None) -> bool:
        """
        Create a new cash transaction.
        
        Args:
            montant: Transaction amount
            date_str: Transaction date (YYYY-MM-DD)
            type_: Transaction type ('encaissement' or 'decaissement')
            description: Transaction description
            nfacture: Invoice number
            num_facture: Invoice number as string
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.caisse_repository.ajouter_transaction(
                montant, date_str, type_, description, nfacture, num_facture
            )
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return False
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a cash transaction with cascading operations to related payments.
        
        Args:
            transaction_id: ID of transaction to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # First get transaction details before deleting
            transaction_details = None
            transactions = self.get_all_transactions()
            for transaction in transactions:
                if transaction.get('id') == transaction_id:
                    transaction_details = transaction
                    break
            
            if not transaction_details:
                logger.error(f"Caisse transaction {transaction_id} not found")
                return False
            
            logger.info(f"Deleting caisse transaction {transaction_id} with cascading operations")
            
            # Check if this is a multiple payment transaction
            is_multiple_payment = False
            transaction_reference = None
            if transaction_details.get('description') and 'MULTI-' in transaction_details.get('description', ''):
                is_multiple_payment = True
                # Extract transaction reference from description
                import re
                match = re.search(r'MULTI-\d{8}-\d{6}', transaction_details.get('description', ''))
                if match:
                    transaction_reference = match.group(0)
                    logger.info(f"Detected multiple payment transaction: {transaction_reference}")
            
            # Delete related payment records
            try:
                from app.stfoom.services.payment_service import PaymentService, PaymentRepository
                payment_repository = PaymentRepository()
                payment_service = PaymentService(payment_repository)
                
                if is_multiple_payment and transaction_reference:
                    # For multiple payments, find all payments with this transaction reference
                    with payment_repository.get_connection() as conn:
                        cursor = conn.execute("""
                            SELECT id FROM paiements_factures 
                            WHERE notes LIKE ?
                        """, (f'%{transaction_reference}%',))
                        payment_ids = [row[0] for row in cursor.fetchall()]
                        
                    # Delete all related payments (but skip their own cascading to avoid recursion)
                    for payment_id in payment_ids:
                        with payment_repository.get_connection() as conn:
                            cursor = conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                            conn.commit()
                            if cursor.rowcount > 0:
                                logger.info(f"Deleted related payment record {payment_id}")
                else:
                    # For single payments, find payment by invoice number and amount
                    nfacture = transaction_details.get('nfacture')
                    montant = transaction_details.get('montant', 0)
                    
                    if nfacture:
                        with payment_repository.get_connection() as conn:
                            cursor = conn.execute("""
                                SELECT id FROM paiements_factures 
                                WHERE nfacture = ? AND ABS(montant_paye - ?) < 0.01 
                                AND methode_paiement = 'caisse'
                            """, (nfacture, montant))
                            payment_ids = [row[0] for row in cursor.fetchall()]
                            
                            # Delete matching payment records
                            for payment_id in payment_ids:
                                cursor = conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                                conn.commit()
                                if cursor.rowcount > 0:
                                    logger.info(f"Deleted related payment record {payment_id}")
                
            except Exception as e:
                logger.error(f"Error deleting related payment records: {e}")
            
            # Delete the caisse transaction itself
            success = self.caisse_repository.supprimer_transaction(transaction_id)
            if success:
                logger.info(f"Deleted caisse transaction {transaction_id}")
            else:
                logger.error(f"Failed to delete caisse transaction {transaction_id}")

            # Also delete retenu for single transactions if any
            try:
                if not is_multiple_payment:
                    from app.stfoom.services.retenu_service import RetenuService
                    from app.stfoom.data.retenu_repository import RetenuRepository
                    retenu_repository = RetenuRepository()
                    retenu_service = RetenuService(retenu_repository)
                    nfacture = transaction_details.get('nfacture')
                    if nfacture:
                        retenus = retenu_service.get_retenus_by_facture(nfacture)
                        for r in retenus:
                            retenu_service.delete_retenu(r.get('id'))
            except Exception as e:
                logger.error(f"Error deleting retenu after caisse delete: {e}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting caisse transaction {transaction_id}: {e}")
            return False
    
    def update_transaction(self, transaction_id: int, type_transaction: str, 
                          montant: float, date_transaction: str, 
                          nfacture: Optional[int] = None, nom_client: str = "",
                          numero_recu: str = "", description: str = "",
                          mode_paiement: str = "", echeance: str = "") -> bool:
        """
        Update an existing cash transaction.
        
        Args:
            transaction_id: ID of transaction to update
            type_transaction: Transaction type
            montant: Transaction amount
            date_transaction: Transaction date
            nfacture: Invoice number
            nom_client: Client/supplier name
            numero_recu: Receipt number
            description: Transaction description
            mode_paiement: Payment method
            echeance: Due date
            
        Returns:
            True if successful, False otherwise
        """
        try:
            return self.caisse_repository.modifier_transaction(
                transaction_id, type_transaction, montant, date_transaction,
                nfacture, nom_client, numero_recu, description, mode_paiement, echeance
            )
        except Exception as e:
            logger.error(f"Error updating transaction: {e}")
            return False
    
    # ========================== Financial Calculations ==========================
    
    def get_balance(self) -> float:
        """
        Get current cash balance.
        
        Returns:
            Current balance (encaissements - decaissements)
        """
        try:
            return self.caisse_repository.get_solde()
        except Exception as e:
            logger.error(f"Error getting balance: {e}")
            return 0.0
    
    def get_period_summary(self, start_date: Optional[str] = None, end_date: Optional[str] = None) -> Dict:
        """
        Get period summary with encaissements and decaissements.
        
        Args:
            start_date: Start date for summary (YYYY-MM-DD)
            end_date: End date for summary (YYYY-MM-DD)
            
        Returns:
            Dictionary with encaissements, decaissements, and balance
        """
        try:
            return self.caisse_repository.get_resume_periode(start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting period summary: {e}")
            return {
                'encaissements': {'nombre': 0, 'total': 0.0},
                'decaissements': {'nombre': 0, 'total': 0.0},
                'solde': 0.0
            }
    
    # ========================== Formatting Utilities ==========================
    
    def format_amount(self, amount: float) -> str:
        """
        Format amount for display.
        
        Args:
            amount: Amount to format
            
        Returns:
            Formatted amount string
        """
        try:
            return self.caisse_repository.formater_montant(amount)
        except Exception as e:
            logger.error(f"Error formatting amount: {e}")
            return f"{amount:.3f}"
    
    def format_date(self, date_str: str) -> str:
        """
        Format date for display.
        
        Args:
            date_str: Date string to format
            
        Returns:
            Formatted date string
        """
        try:
            return self.caisse_repository.formater_date(date_str)
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date_str
    
    # ========================== Validation ==========================
    
    def validate_transaction(self, montant: float, type_: str, date_str: str) -> tuple[bool, str]:
        """
        Validate transaction data.
        
        Args:
            montant: Transaction amount
            type_: Transaction type
            date_str: Transaction date
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if montant <= 0:
                return False, "Le montant doit être positif"
            
            if type_ not in ['encaissement', 'decaissement']:
                return False, "Le type doit être 'encaissement' ou 'decaissement'"
            
            # Validate date format
            try:
                datetime.strptime(date_str, "%Y-%m-%d")
            except ValueError:
                return False, "Format de date invalide (YYYY-MM-DD attendu)"
            
            return True, ""
        except Exception as e:
            logger.error(f"Error validating transaction: {e}")
            return False, f"Erreur de validation: {e}"
    
    # ========================== Statistics ==========================
    
    def get_statistics(self) -> Dict:
        """
        Get cash flow statistics.
        
        Returns:
            Dictionary with various statistics
        """
        try:
            transactions = self.get_all_transactions()
            summary = self.get_period_summary()
            
            return {
                'total_transactions': len(transactions),
                'total_encaissements': summary['encaissements']['total'],
                'total_decaissements': summary['decaissements']['total'],
                'current_balance': self.get_balance(),
                'average_encaissement': (
                    summary['encaissements']['total'] / summary['encaissements']['nombre']
                    if summary['encaissements']['nombre'] > 0 else 0
                ),
                'average_decaissement': (
                    summary['decaissements']['total'] / summary['decaissements']['nombre']
                    if summary['decaissements']['nombre'] > 0 else 0
                )
            }
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {
                'total_transactions': 0,
                'total_encaissements': 0.0,
                'total_decaissements': 0.0,
                'current_balance': 0.0,
                'average_encaissement': 0.0,
                'average_decaissement': 0.0
            }
