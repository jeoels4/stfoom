"""
STFOOM Bank Service Layer

This service provides business logic for bank and transaction management operations,
abstracting away direct database access and providing a clean interface for the UI layer.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class BankService:
    """Service for managing bank and transaction operations."""
    
    def __init__(self, bank_repository):
        """
        Initialize the bank service.
        
        Args:
            bank_repository: Repository for bank data access
        """
        self.bank_repository = bank_repository
        logger.info("BankService initialized")
    
    # ========================== Bank Management ==========================
    
    def get_all_banks(self) -> List[Dict]:
        """
        Get all bank accounts.
        
        Returns:
            List of bank dictionaries
        """
        try:
            banks = self.bank_repository.get_banques()
            logger.info(f"Retrieved {len(banks)} bank accounts")
            return banks
        except Exception as e:
            logger.error(f"Error getting all banks: {e}")
            return []
    
    def get_banques(self) -> List[Dict]:
        """
        Legacy compatibility method for get_all_banks.
        
        Returns:
            List of bank dictionaries
        """
        return self.get_all_banks()
    
    def create_bank(self, nom_banque: str, numero_compte: str = "", solde_initial: float = 0) -> bool:
        """
        Create a new bank account.
        
        Args:
            nom_banque: Bank name
            numero_compte: Account number (optional)
            solde_initial: Initial balance (default 0)
            
        Returns:
            True if created successfully, False otherwise
        """
        try:
            if not nom_banque or not nom_banque.strip():
                logger.error("Bank name is required")
                return False
            
            success = self.bank_repository.ajouter_banque(nom_banque, numero_compte, solde_initial)
            if success:
                logger.info(f"Created bank account: {nom_banque}")
            else:
                logger.error("Failed to create bank account")
            return success
        except Exception as e:
            logger.error(f"Error creating bank: {e}")
            return False
    
    def get_bank_by_id(self, banque_id: int) -> Optional[Dict]:
        """
        Get a bank account by ID.
        
        Args:
            banque_id: The ID of the bank
            
        Returns:
            Bank dictionary or None if not found
        """
        try:
            bank = self.bank_repository.get_banque_by_id(banque_id)
            if bank:
                logger.info(f"Retrieved bank {banque_id}")
            else:
                logger.warning(f"Bank {banque_id} not found")
            return bank
        except Exception as e:
            logger.error(f"Error getting bank {banque_id}: {e}")
            return None
    
    def update_bank(self, banque_id: int, nom_banque: str, numero_compte: str = "", solde_initial: float = 0) -> bool:
        """
        Update a bank account.
        
        Args:
            banque_id: The ID of the bank to update
            nom_banque: Bank name
            numero_compte: Account number
            solde_initial: Initial balance
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            success = self.bank_repository.modifier_banque(banque_id, nom_banque, numero_compte, solde_initial)
            if success:
                logger.info(f"Updated bank {banque_id}")
            else:
                logger.error(f"Failed to update bank {banque_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating bank {banque_id}: {e}")
            return False
    
    def delete_bank(self, banque_id: int) -> bool:
        """
        Delete a bank account.
        
        Args:
            banque_id: The ID of the bank to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            success = self.bank_repository.supprimer_banque(banque_id)
            if success:
                logger.info(f"Deleted bank {banque_id}")
            else:
                logger.error(f"Failed to delete bank {banque_id}")
            return success
        except Exception as e:
            logger.error(f"Error deleting bank {banque_id}: {e}")
            return False
    
    def get_default_bank(self) -> Optional[Dict]:
        """
        Get the default bank account.
        
        Returns:
            Default bank dictionary or None if not set
        """
        try:
            bank = self.bank_repository.get_banque_defaut()
            return bank
        except Exception as e:
            logger.error(f"Error getting default bank: {e}")
            return None
    
    def set_default_bank(self, banque_id: int) -> bool:
        """
        Set the default bank account.
        
        Args:
            banque_id: The ID of the bank to set as default
            
        Returns:
            True if set successfully, False otherwise
        """
        try:
            success = self.bank_repository.definir_banque_defaut(banque_id)
            if success:
                logger.info(f"Set bank {banque_id} as default")
            else:
                logger.error(f"Failed to set bank {banque_id} as default")
            return success
        except Exception as e:
            logger.error(f"Error setting default bank: {e}")
            return False
    
    # ========================== Transaction Management ==========================
    
    def get_transactions(self, banque_id: int = None, date_debut: str = None, date_fin: str = None) -> List[Dict]:
        """
        Get bank transactions with optional filtering.
        
        Args:
            banque_id: Bank ID to filter by (optional)
            date_debut: Start date for filtering (optional)
            date_fin: End date for filtering (optional)
            
        Returns:
            List of transaction dictionaries
        """
        try:
            transactions = self.bank_repository.get_transactions(banque_id, date_debut, date_fin)
            logger.info(f"Retrieved {len(transactions)} transactions")
            return transactions
        except Exception as e:
            logger.error(f"Error getting transactions: {e}")
            return []
    
    def create_transaction(self, **kwargs) -> bool:
        """
        Create a new bank transaction.
        
        Returns:
            True if created successfully, False otherwise
        """
        try:
            success = self.bank_repository.ajouter_transaction(**kwargs)
            if success:
                logger.info("Created bank transaction")
            else:
                logger.error("Failed to create bank transaction")
            return success
        except Exception as e:
            logger.error(f"Error creating transaction: {e}")
            return False
    
    def get_transaction_by_id(self, transaction_id: int) -> Optional[Dict]:
        """
        Get a transaction by ID.
        
        Args:
            transaction_id: The ID of the transaction
            
        Returns:
            Transaction dictionary or None if not found
        """
        try:
            transaction = self.bank_repository.get_transaction_by_id(transaction_id)
            if transaction:
                logger.info(f"Retrieved transaction {transaction_id}")
            else:
                logger.warning(f"Transaction {transaction_id} not found")
            return transaction
        except Exception as e:
            logger.error(f"Error getting transaction {transaction_id}: {e}")
            return None
    
    def update_transaction(self, transaction_id: int, **kwargs) -> bool:
        """
        Update a bank transaction.
        
        Args:
            transaction_id: The ID of the transaction to update
            **kwargs: Transaction data to update
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            success = self.bank_repository.modifier_transaction(transaction_id, **kwargs)
            if success:
                logger.info(f"Updated transaction {transaction_id}")
            else:
                logger.error(f"Failed to update transaction {transaction_id}")
            return success
        except Exception as e:
            logger.error(f"Error updating transaction {transaction_id}: {e}")
            return False
    
    def delete_transaction(self, transaction_id: int) -> bool:
        """
        Delete a bank transaction with cascading operations to related payments.
        
        Args:
            transaction_id: The ID of the transaction to delete
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # First get transaction details before deleting
            transaction_details = None
            transactions = self.bank_repository.get_transactions()
            for transaction in transactions:
                if transaction.get('id') == transaction_id:
                    transaction_details = transaction
                    break
            
            if not transaction_details:
                logger.error(f"Transaction {transaction_id} not found")
                return False
            
            logger.info(f"Deleting bank transaction {transaction_id} with cascading operations")
            
            # Check if this is a multiple payment transaction
            is_multiple_payment = False
            transaction_reference = None
            if transaction_details.get('description') and 'MULTI-' in transaction_details.get('description', ''):
                is_multiple_payment = True
                # Extract transaction reference from description
                import re
                # Try the full timestamp pattern (optionally with microseconds)
                match = re.search(r'MULTI-\d{8}-\d{6}(?:-\d{6})?', transaction_details.get('description', ''))
                if match:
                    transaction_reference = match.group(0)
                    logger.info(f"Detected multiple payment transaction: {transaction_reference}")
                else:
                    # No explicit reference found; treat as multiple but do not perform broad deletes
                    logger.info("Detected MULTI marker without explicit reference; will avoid broad deletions")
            
            # Delete related payment records
            try:
                from app.stfoom.services.payment_service import PaymentService, PaymentRepository
                payment_repository = PaymentRepository()
                payment_service = PaymentService(payment_repository)
                
                if is_multiple_payment and transaction_reference:
                    # For multiple payments, find all payments with this transaction reference
                    with payment_repository.get_connection() as conn:
                        # Specific transaction reference: delete only exact batch payments
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
                    reference = transaction_details.get('numero_cheque', '')
                    
                    if nfacture:
                        with payment_repository.get_connection() as conn:
                            cursor = conn.execute("""
                                SELECT id FROM paiements_factures 
                                WHERE nfacture = ? AND ABS(montant_paye - ?) < 0.01 
                                AND methode_paiement = 'banque' 
                                AND (reference_paiement = ? OR reference_paiement IS NULL)
                            """, (nfacture, montant, reference))
                            payment_ids = [row[0] for row in cursor.fetchall()]
                            
                            # Delete matching payment records
                            for payment_id in payment_ids:
                                cursor = conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                                conn.commit()
                                if cursor.rowcount > 0:
                                    logger.info(f"Deleted related payment record {payment_id}")
                
            except Exception as e:
                logger.error(f"Error deleting related payment records: {e}")
            
            # Delete related retenu records
            if is_multiple_payment and transaction_reference:
                try:
                    from app.stfoom.services.retenu_service import RetenuService
                    from app.stfoom.data.retenu_repository import RetenuRepository
                    retenu_repository = RetenuRepository()
                    retenu_service = RetenuService(retenu_repository)
                    
                    # Find retenu records by transaction reference in notes
                    all_retenus = retenu_service.get_all_retenus()
                    for retenu in all_retenus:
                        if retenu.get('notes') and transaction_reference in retenu.get('notes', ''):
                            retenu_id = retenu.get('id')
                            if retenu_id:
                                # Use service method to delete retenu record properly
                                if retenu_service.delete_retenu(retenu_id):
                                    logger.info(f"Deleted related retenu record {retenu_id}")
                                else:
                                    logger.error(f"Failed to delete retenu record {retenu_id}")
                except Exception as e:
                    logger.error(f"Error deleting related retenu records: {e}")
            else:
                # For single transactions, remove retenu linked to this achat/vente if any
                try:
                    from app.stfoom.services.retenu_service import RetenuService
                    from app.stfoom.data.retenu_repository import RetenuRepository
                    retenu_repository = RetenuRepository()
                    retenu_service = RetenuService(retenu_repository)
                    nfacture = transaction_details.get('nfacture')
                    if nfacture:
                        # Find retenus by invoice id
                        retenus = retenu_service.get_retenus_by_facture(nfacture)
                        for r in retenus:
                            retenu_service.delete_retenu(r.get('id'))
                except Exception as e:
                    logger.error(f"Error deleting single retenu records: {e}")
            
            # Delete related calendar entries (traite) for multiple payments
            if is_multiple_payment and transaction_reference:
                try:
                    # Check if this is a traite payment
                    if transaction_details.get('mode_paiement') == 'traite':
                        # Find and delete calendar entries
                        with self.bank_repository.get_connection() as conn:
                            cursor = conn.execute("""
                                DELETE FROM calendar_fait 
                                WHERE titre LIKE ? OR description LIKE ?
                            """, (f'%{transaction_reference}%', f'%{transaction_reference}%'))
                            conn.commit()
                            if cursor.rowcount > 0:
                                logger.info(f"Deleted {cursor.rowcount} related calendar entries for traite payment")
                except Exception as e:
                    logger.error(f"Error deleting related calendar entries: {e}")
            
            # Delete the bank transaction itself
            success = self.bank_repository.supprimer_transaction(transaction_id)
            if success:
                logger.info(f"Deleted bank transaction {transaction_id}")
            else:
                logger.error(f"Failed to delete bank transaction {transaction_id}")
            return success
            
        except Exception as e:
            logger.error(f"Error deleting transaction {transaction_id}: {e}")
            return False
    
    def verify_transaction(self, transaction_id: int) -> bool:
        """
        Verify/check a bank transaction.
        
        Args:
            transaction_id: The ID of the transaction to verify
            
        Returns:
            True if verified successfully, False otherwise
        """
        try:
            success = self.bank_repository.verifier_transaction(transaction_id)
            if success:
                logger.info(f"Verified transaction {transaction_id}")
            else:
                logger.error(f"Failed to verify transaction {transaction_id}")
            return success
        except Exception as e:
            logger.error(f"Error verifying transaction {transaction_id}: {e}")
            return False
    
    # ========================== Balance & Summary ==========================
    
    def get_bank_balance(self, banque_id: int, date_calcul: str = None, verifie_seulement: bool = True) -> float:
        """
        Get bank balance.
        
        Args:
            banque_id: Bank ID
            date_calcul: Date for calculation (optional)
            verifie_seulement: Only include verified transactions
            
        Returns:
            Bank balance
        """
        try:
            balance = self.bank_repository.get_solde_banque(banque_id, date_calcul, verifie_seulement)
            logger.info(f"Retrieved balance for bank {banque_id}: {balance}")
            return balance
        except Exception as e:
            logger.error(f"Error getting bank balance: {e}")
            return 0.0
    
    def get_period_summary(self, banque_id: int, date_debut: str, date_fin: str) -> Dict:
        """
        Get period summary for a bank.
        
        Args:
            banque_id: Bank ID
            date_debut: Start date
            date_fin: End date
            
        Returns:
            Summary dictionary with encaissements and decaissements
        """
        try:
            summary = self.bank_repository.get_resume_periode(banque_id, date_debut, date_fin)
            logger.info(f"Retrieved period summary for bank {banque_id}")
            return summary
        except Exception as e:
            logger.error(f"Error getting period summary: {e}")
            return {'encaissements': {'total': 0}, 'decaissements': {'total': 0}}
    
    # ========================== Payment Methods ==========================
    
    def get_payment_methods(self) -> List[tuple]:
        """
        Get available payment methods.
        
        Returns:
            List of (key, label) tuples
        """
        try:
            methods = self.bank_repository.get_payment_methods()
            return methods
        except Exception as e:
            logger.error(f"Error getting payment methods: {e}")
            return []
    
    def add_payment_method(self, key: str, label: str) -> bool:
        """
        Add a new payment method.
        
        Args:
            key: Payment method key
            label: Payment method label
            
        Returns:
            True if added successfully
        """
        try:
            success = self.bank_repository.add_payment_method(key, label)
            if success:
                logger.info(f"Added payment method: {key} - {label}")
            return success
        except Exception as e:
            logger.error(f"Error adding payment method: {e}")
            return False
    
    def remove_payment_method(self, key: str) -> bool:
        """
        Remove a payment method.
        
        Args:
            key: Payment method key to remove
            
        Returns:
            True if removed successfully
        """
        try:
            success = self.bank_repository.remove_payment_method(key)
            if success:
                logger.info(f"Removed payment method: {key}")
            return success
        except Exception as e:
            logger.error(f"Error removing payment method: {e}")
            return False
    
    # ========================== Utilities ==========================
    
    def format_amount(self, amount: float) -> str:
        """
        Format amount for display.
        
        Args:
            amount: Amount to format
            
        Returns:
            Formatted amount string
        """
        try:
            return self.bank_repository.formater_montant(amount)
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
            return self.bank_repository.formater_date(date_str)
        except Exception as e:
            logger.error(f"Error formatting date: {e}")
            return date_str
    
    # ========================== Business Logic Methods ==========================
    
    def get_bank_statistics(self) -> Dict:
        """
        Get statistics about all banks.
        
        Returns:
            Dictionary containing bank statistics
        """
        try:
            banks = self.get_all_banks()
            total_banks = len(banks)
            total_balance = sum(self.get_bank_balance(bank['id'], verifie_seulement=False) for bank in banks)
            verified_balance = sum(self.get_bank_balance(bank['id'], verifie_seulement=True) for bank in banks)
            
            return {
                'total_banks': total_banks,
                'total_balance': total_balance,
                'verified_balance': verified_balance,
                'unverified_balance': total_balance - verified_balance
            }
        except Exception as e:
            logger.error(f"Error getting bank statistics: {e}")
            return {
                'total_banks': 0,
                'total_balance': 0,
                'verified_balance': 0,
                'unverified_balance': 0
            }
