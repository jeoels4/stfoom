"""
PHASE 2F MIGRATION - RETENU SERVICE
==================================
Service layer for retenu (retention/withholding) management operations.

This service provides business logic for managing retenu records,
including creation, retrieval, updates, and reporting functionality.
"""

from typing import List, Dict, Optional, Any
from datetime import datetime, date
import os

# Verbosity control for retenu logs: set env STFOOM_DEBUG_RETENU=1 to enable
DEBUG_RETENU = os.environ.get("STFOOM_DEBUG_RETENU", "0") == "1"

def _ret_debug(msg: str):
    if DEBUG_RETENU:
        try:
            print(msg)
        except Exception:
            pass


class RetenuService:
    """
    Service layer for retenu management operations.
    
    Provides business logic for managing client and supplier retentions,
    including CRUD operations, filtering, and summary reporting.
    """
    
    def __init__(self, retenu_repository):
        """
        Initialize RetenuService with repository dependency.
        
        Args:
            retenu_repository: Repository for retenu data access operations
        """
        self.repository = retenu_repository
        _ret_debug("[RETENU SERVICE] Initialized with repository")
    
    def get_all_retenus(self) -> List[Dict[str, Any]]:
        """
        Get all retenu records ordered by date (newest first).
        
        Returns:
            List of retenu dictionaries with all fields
        """
        try:
            retenus = self.repository.get_all_retenus()
            _ret_debug(f"[RETENU SERVICE] Retrieved {len(retenus)} retenu records")
            return retenus
        except Exception as e:
            print(f"[RETENU SERVICE] Error retrieving all retenus: {e}")
            return []
    
    def get_retenus_by_client(self, client: str) -> List[Dict[str, Any]]:
        """
        Get all retenu records for a specific client.
        
        Args:
            client: Client name to filter by
            
        Returns:
            List of retenu dictionaries for the specified client
        """
        try:
            if not client or not client.strip():
                return []
            
            retenus = self.repository.get_retenus_by_client(client.strip())
            _ret_debug(f"[RETENU SERVICE] Retrieved {len(retenus)} retenus for client: {client}")
            return retenus
        except Exception as e:
            print(f"[RETENU SERVICE] Error retrieving retenus for client {client}: {e}")
            return []
    
    def get_retenus_by_facture(self, nfacture: int) -> List[Dict[str, Any]]:
        """
        Get all retenu records for a specific invoice number.
        
        Args:
            nfacture: Invoice number to filter by
            
        Returns:
            List of retenu dictionaries for the specified invoice
        """
        try:
            if not isinstance(nfacture, int) or nfacture <= 0:
                return []
            
            retenus = self.repository.get_retenus_by_facture(nfacture)
            _ret_debug(f"[RETENU SERVICE] Retrieved {len(retenus)} retenus for invoice: {nfacture}")
            return retenus
        except Exception as e:
            print(f"[RETENU SERVICE] Error retrieving retenus for invoice {nfacture}: {e}")
            return []
    
    def create_retenu(self, date: str, client: str, nfacture: Optional[int] = None,
                     percent: float = 0.0, amount: float = 0.0, source: str = "",
                     notes: str = "", party_type: Optional[str] = None) -> bool:
        """
        Create a new retenu record.
        
        Args:
            date: Date in YYYY-MM-DD format
            client: Client name
            nfacture: Optional invoice number
            percent: Retention percentage
            amount: Retention amount
            source: Source of the retention (e.g., 'client', 'supplier')
            notes: Additional notes
            
        Returns:
            True if retenu created successfully, False otherwise
        """
        try:
            # Validate required fields
            if not self.validate_retenu_data(date, client, percent, amount, source):
                return False
            # Optional party_type validation
            if party_type and party_type not in ("client", "fournisseur"):
                print("[RETENU SERVICE] Invalid party_type; expected 'client' or 'fournisseur'")
                # Normalize to None to avoid bad data
                party_type = None
            
            # Format the data
            formatted_date = self.format_date(date)
            if not formatted_date:
                print("[RETENU SERVICE] Invalid date format")
                return False
            
            result = self.repository.add_retenu(
                date=formatted_date,
                client=client.strip(),
                nfacture=nfacture,
                percent=percent,
                amount=amount,
                source=source.strip(),
                notes=notes.strip(),
                party_type=party_type
            )
            if result:
                _ret_debug(f"[RETENU SERVICE] Created retenu for client {client}, amount: {amount}")
            else:
                print(f"[RETENU SERVICE] Failed to create retenu for client {client}")
            return result
        
        except Exception as e:
            print(f"[RETENU SERVICE] Error creating retenu: {e}")
            return False

    # Backward compatibility alias for UI
    def add_retenu(self, date: str, client: str, nfacture: Optional[int],
                   percent: float, amount: float, source: str, notes: str = "",
                   party_type: Optional[str] = None) -> bool:
        return self.create_retenu(date, client, nfacture, percent, amount, source, notes, party_type)
    
    def update_retenu(self, retenu_id: int, **fields) -> bool:
        """
        Update an existing retenu record.
        
        Args:
            retenu_id: ID of the retenu to update
            **fields: Fields to update
            
        Returns:
            True if update successful, False otherwise
        """
        try:
            if not isinstance(retenu_id, int) or retenu_id <= 0:
                print("[RETENU SERVICE] Invalid retenu ID")
                return False
            
            if not fields:
                print("[RETENU SERVICE] No fields provided for update")
                return False
            
            # Validate and format fields if needed
            if 'date' in fields:
                formatted_date = self.format_date(fields['date'])
                if formatted_date:
                    fields['date'] = formatted_date
                else:
                    print("[RETENU SERVICE] Invalid date format in update")
                    return False
            
            # Strip string fields
            for field in ['client', 'source', 'notes']:
                if field in fields and isinstance(fields[field], str):
                    fields[field] = fields[field].strip()
            # Validate party_type if present
            if 'party_type' in fields and fields['party_type'] not in (None, 'client', 'fournisseur'):
                print("[RETENU SERVICE] Invalid party_type in update; removing field")
                fields.pop('party_type', None)
            
            result = self.repository.update_retenu(retenu_id, **fields)
            
            if result:
                _ret_debug(f"[RETENU SERVICE] Updated retenu {retenu_id}")
            else:
                print(f"[RETENU SERVICE] Failed to update retenu {retenu_id}")
            
            return result
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error updating retenu {retenu_id}: {e}")
            return False
    
    def delete_retenu(self, retenu_id: int) -> bool:
        """
        Delete a retenu record with cascading operations to related payments.
        
        Args:
            retenu_id: ID of the retenu to delete
            
        Returns:
            True if deletion successful, False otherwise
        """
        try:
            if not isinstance(retenu_id, int) or retenu_id <= 0:
                print("[RETENU SERVICE] Invalid retenu ID for deletion")
                return False
            
            # First get retenu details before deleting
            retenu_details = None
            all_retenus = self.get_all_retenus()
            for retenu in all_retenus:
                if retenu.get('id') == retenu_id:
                    retenu_details = retenu
                    break
            
            if not retenu_details:
                print(f"[RETENU SERVICE] Retenu {retenu_id} not found")
                return False
            
            print(f"[RETENU SERVICE] Deleting retenu {retenu_id} with cascading operations")
            
            # Check if this is a multiple payment retenu
            is_multiple_payment = False
            transaction_reference = None
            if ((retenu_details.get('notes') and 'MULTI-' in retenu_details.get('notes', '')) or
                (retenu_details.get('source') and 'MULTI-' in retenu_details.get('source', ''))):
                is_multiple_payment = True
                # Extract transaction reference from notes or source
                import re
                notes_or_source = retenu_details.get('notes', '') + ' ' + retenu_details.get('source', '')
                match = re.search(r'MULTI-\d{8}-\d{6}', notes_or_source)
                if match:
                    transaction_reference = match.group(0)
                    print(f"[RETENU SERVICE] Detected multiple payment transaction: {transaction_reference}")
            
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
                                _ret_debug(f"[RETENU SERVICE] Deleted related payment record {payment_id}")
                else:
                    # For single retenu, find payment by invoice number
                    nfacture = retenu_details.get('nfacture')
                    if nfacture:
                        with payment_repository.get_connection() as conn:
                            cursor = conn.execute("""
                                SELECT id FROM paiements_factures 
                                WHERE nfacture = ? AND (notes LIKE '%retenu%' OR notes LIKE '%Retenu%')
                            """, (nfacture,))
                            payment_ids = [row[0] for row in cursor.fetchall()]
                            
                            # Delete matching payment records
                            for payment_id in payment_ids:
                                cursor = conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                                conn.commit()
                                if cursor.rowcount > 0:
                                    _ret_debug(f"[RETENU SERVICE] Deleted related payment record {payment_id}")
                
            except Exception as e:
                print(f"[RETENU SERVICE] Error deleting related payment records: {e}")
            
            # Delete the retenu record itself
            result = self.repository.delete_retenu(retenu_id)
            
            if result:
                _ret_debug(f"[RETENU SERVICE] Deleted retenu {retenu_id}")
            else:
                print(f"[RETENU SERVICE] Failed to delete retenu {retenu_id}")
            
            return result
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error deleting retenu {retenu_id}: {e}")
            return False
    
    def get_summary(self) -> Dict[str, Any]:
        """
        Get comprehensive summary of retenu data.
        
        Returns:
            Dictionary containing total amounts, breakdowns by client and month
        """
        try:
            summary = self.repository.get_summary()
            
            # Enhance summary with formatted values
            enhanced_summary = {
                'total': summary.get('total', 0),
                'total_formatted': self.format_amount(summary.get('total', 0)),
                'by_client': summary.get('by_client', {}),
                'by_month': summary.get('by_month', {}),
                'client_count': len(summary.get('by_client', {})),
                'month_count': len(summary.get('by_month', {}))
            }
            
            _ret_debug(f"[RETENU SERVICE] Generated summary: {enhanced_summary['total_formatted']} total")
            return enhanced_summary
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error generating summary: {e}")
            return {
                'total': 0,
                'total_formatted': '0.00 DZD',
                'by_client': {},
                'by_month': {},
                'client_count': 0,
                'month_count': 0
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get comprehensive statistics about retenu data.
        
        Returns:
            Dictionary with various statistics and analytics
        """
        try:
            all_retenus = self.get_all_retenus()
            
            if not all_retenus:
                return {
                    'total_records': 0,
                    'total_amount': 0,
                    'average_amount': 0,
                    'highest_amount': 0,
                    'lowest_amount': 0
                }
            
            amounts = [float(r.get('retenu_amount', 0)) for r in all_retenus]
            
            stats = {
                'total_records': len(all_retenus),
                'total_amount': sum(amounts),
                'average_amount': sum(amounts) / len(amounts) if amounts else 0,
                'highest_amount': max(amounts) if amounts else 0,
                'lowest_amount': min(amounts) if amounts else 0,
                'unique_clients': len(set(r.get('client', '') for r in all_retenus)),
                'with_invoices': len([r for r in all_retenus if r.get('nfacture')])
            }
            
            _ret_debug(f"[RETENU SERVICE] Generated statistics: {stats['total_records']} records")
            return stats
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error generating statistics: {e}")
            return {}
    
    def validate_retenu_data(self, date: str, client: str, percent: float, 
                           amount: float, source: str) -> bool:
        """
        Validate retenu data before creation/update.
        
        Args:
            date: Date string
            client: Client name
            percent: Retention percentage
            amount: Retention amount
            source: Source of retention
            
        Returns:
            True if all data is valid, False otherwise
        """
        try:
            # Check required fields
            if not date or not date.strip():
                print("[RETENU SERVICE] Date is required")
                return False
            
            if not client or not client.strip():
                print("[RETENU SERVICE] Client name is required")
                return False
            
            if not source or not source.strip():
                print("[RETENU SERVICE] Source is required")
                return False
            
            # Validate numeric fields
            if not isinstance(percent, (int, float)) or percent < 0:
                print("[RETENU SERVICE] Percentage must be a non-negative number")
                return False
            
            if not isinstance(amount, (int, float)) or amount < 0:
                print("[RETENU SERVICE] Amount must be a non-negative number")
                return False
            
            # At least one of percent or amount should be greater than 0
            if percent == 0 and amount == 0:
                print("[RETENU SERVICE] Either percentage or amount must be greater than 0")
                return False
            
            return True
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error validating retenu data: {e}")
            return False
    
    def format_date(self, date_input: str) -> Optional[str]:
        """
        Format date string to YYYY-MM-DD format.
        
        Args:
            date_input: Date string in various formats
            
        Returns:
            Formatted date string or None if invalid
        """
        try:
            if not date_input:
                return None
            
            # Try different date formats
            formats = ['%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y']
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_input.strip(), fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            print(f"[RETENU SERVICE] Unable to parse date: {date_input}")
            return None
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error formatting date: {e}")
            return None
    
    def format_amount(self, amount: float) -> str:
        """
        Format amount with currency and thousand separators.
        
        Args:
            amount: Numeric amount
            
        Returns:
            Formatted amount string
        """
        try:
            if not isinstance(amount, (int, float)):
                return "0.00 DZD"
            
            # Format with thousand separators and 3 decimal places
            formatted = f"{amount:,.3f}".replace(',', ' ')
            return f"{formatted} DZD"
            
        except Exception as e:
            print(f"[RETENU SERVICE] Error formatting amount: {e}")
            return "0.00 DZD"
