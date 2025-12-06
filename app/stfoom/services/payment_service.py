"""
Payment Service - Business Logic Layer
====================================
Handles all payment-related operations with clean service architecture.
Migrated from app.stfoom.logic.payments
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple, Any
from app.stfoom.data.base_repository import BaseRepository
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_payment_action
)

class PaymentRepository(BaseRepository):
    """Data access layer for payment operations"""
    
    def __init__(self):
        super().__init__("paiements_factures")
    
    def get_entity_name(self) -> str:
        """Return the name of the entity this repository manages."""
        return "paiements_factures"
    
    def init_tables(self) -> None:
        """Initialize payment tables"""
        with self.get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS paiements_factures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nfacture INTEGER NOT NULL,
                    montant_paye REAL NOT NULL,
                    methode_paiement TEXT NOT NULL,  -- 'banque' ou 'caisse'
                    date_paiement TEXT NOT NULL,     -- YYYY-MM-DD
                    reference_paiement TEXT,         -- Référence bancaire ou numéro de reçu
                    notes TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_payment(self, payment_data: Dict[str, Any], is_achat: bool = False) -> int:
        """Add a new payment record for vente (sale) or achat (purchase)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO paiements_factures 
                (nfacture, montant_paye, methode_paiement, date_paiement, 
                 reference_paiement, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                payment_data['nfacture'],
                payment_data['montant_paye'], 
                payment_data['methode_paiement'],
                payment_data['date_paiement'],
                payment_data.get('reference_paiement'),
                payment_data.get('notes')
            ))
            conn.commit()
            payment_id = cursor.lastrowid
            
            # Log the payment creation with detailed information
            log_payment_action(
                action="add",
                payment_id=payment_id,
                invoice_id=payment_data['nfacture'],
                amount=payment_data['montant_paye'],
                method=payment_data['methode_paiement'],
                bank_id=payment_data.get('banque_id')
            )
            
            return payment_id

    def get_payments_by_invoice(self, nfacture: int, is_achat: bool = False) -> List[Dict[str, Any]]:
        """Get all payments for a specific invoice (vente or achat)"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM paiements_factures 
                WHERE nfacture = ? 
                ORDER BY date_paiement DESC
            """, (nfacture,))
            
            columns = [col[0] for col in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]

    def get_payment_by_id(self, payment_id: int) -> Optional[Dict[str, Any]]:
        """Get payment by ID"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM paiements_factures WHERE id = ?
            """, (payment_id,))
            
            row = cursor.fetchone()
            if row:
                columns = [col[0] for col in cursor.description]
                return dict(zip(columns, row))
            return None

    def update_payment(self, payment_id: int, payment_data: Dict[str, Any]) -> bool:
        """Update an existing payment"""
        # Get old data for logging
        old_payment = self.get_payment_by_id(payment_id)
        
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE paiements_factures 
                SET montant_paye = ?, methode_paiement = ?, 
                    date_paiement = ?, reference_paiement = ?, notes = ?
                WHERE id = ?
            """, (
                payment_data['montant_paye'],
                payment_data['methode_paiement'], 
                payment_data['date_paiement'],
                payment_data.get('reference_paiement'),
                payment_data.get('notes'),
                payment_id
            ))
            conn.commit()
            success = conn.changes > 0
            
            # Log the update with changes
            if success and old_payment:
                changes = {}
                if old_payment.get('montant_paye') != payment_data['montant_paye']:
                    changes['montant'] = (old_payment.get('montant_paye'), payment_data['montant_paye'])
                if old_payment.get('methode_paiement') != payment_data['methode_paiement']:
                    changes['methode'] = (old_payment.get('methode_paiement'), payment_data['methode_paiement'])
                
                if changes:
                    log_update_action(
                        module="payment",
                        resource_type="payment",
                        resource_id=payment_id,
                        changes=changes
                    )
            
            return success

    def delete_payment(self, payment_id: int, is_achat: bool = False) -> bool:
        """Delete a payment record with cascading operations to bank and retenu"""
        try:
            # First get payment details before deleting
            payment_details = None
            with self.get_connection() as conn:
                cursor = conn.execute("""
                    SELECT nfacture, montant_paye, methode_paiement, reference_paiement, 
                           date_paiement, notes, banque_id, mode_paiement
                    FROM paiements_factures 
                    WHERE id = ?
                """, (payment_id,))
                result = cursor.fetchone()
                if result:
                    payment_details = {
                        'nfacture': result[0],
                        'montant_paye': result[1],
                        'methode_paiement': result[2],
                        'reference_paiement': result[3],
                        'date_paiement': result[4],
                        'notes': result[5],
                        'banque_id': result[6] if len(result) > 6 else None,
                        'mode_paiement': result[7] if len(result) > 7 else None
                    }
            
            if not payment_details:
                print(f"[PAYMENT] Payment {payment_id} not found")
                return False
            
            print(f"[PAYMENT] Deleting payment {payment_id} with cascading operations (is_achat={is_achat})")
            
            # Check if this is part of a multiple payment transaction
            is_multiple_payment = False
            transaction_reference = None
            if payment_details['notes'] and 'MULTI-' in payment_details['notes']:
                is_multiple_payment = True
                # Extract transaction reference from notes - improved pattern
                import re
                match = re.search(r'MULTI-\d{8}-\d{6}', payment_details['notes'])
                if match:
                    transaction_reference = match.group(0)
                    print(f"[PAYMENT] Detected multiple payment transaction: {transaction_reference}")
            
            # Step 1: Delete from bank transactions if it's a bank payment
            if payment_details['methode_paiement'] == 'banque':
                try:
                    from app.stfoom.data.bank_repository import BankRepository
                    from app.stfoom.services.bank_service import BankService
                    bank_repository = BankRepository()
                    bank_service = BankService(bank_repository)
                    
                    # Find bank transactions related to this payment
                    transactions = bank_service.get_transactions()
                    for transaction in transactions:
                        transaction_matches = False
                        
                        if is_multiple_payment and transaction_reference:
                            # For multiple payments, match by transaction reference in description
                            if (transaction.get('description') and 
                                transaction_reference in transaction.get('description', '')):
                                transaction_matches = True
                                print(f"[PAYMENT] Found bank transaction by reference: {transaction_reference}")
                        else:
                            # For single payments, match by invoice number and amount and reference
                            if (transaction.get('nfacture') == payment_details['nfacture'] and 
                                abs(transaction.get('montant', 0) - payment_details['montant_paye']) < 0.01 and
                                transaction.get('numero_cheque') == payment_details['reference_paiement']):
                                transaction_matches = True
                        
                        if transaction_matches:
                            result = bank_service.delete_transaction(transaction['id'])
                            if result:
                                print(f"[PAYMENT] Deleted related bank transaction {transaction['id']}")
                            else:
                                print(f"[PAYMENT] Failed to delete bank transaction {transaction['id']}")
                            
                            # For multiple payments, only delete one combined transaction
                            if is_multiple_payment:
                                break
                    
                except Exception as e:
                    print(f"[PAYMENT] Error deleting bank transaction: {e}")
            
            # Step 2: Delete from caisse transactions if it's a cash payment
            elif payment_details['methode_paiement'] == 'caisse':
                try:
                    from app.stfoom.data.caisse_repository import CaisseRepository
                    from app.stfoom.services.caisse_service import CaisseService
                    caisse_repository = CaisseRepository()
                    caisse_service = CaisseService(caisse_repository)
                    
                    # Find caisse transactions related to this payment
                    transactions = caisse_service.get_all_transactions()
                    for transaction in transactions:
                        transaction_matches = False
                        
                        if is_multiple_payment and transaction_reference:
                            # For multiple payments, match by transaction reference in description
                            if (transaction.get('description') and 
                                transaction_reference in transaction.get('description', '')):
                                transaction_matches = True
                                print(f"[PAYMENT] Found caisse transaction by reference: {transaction_reference}")
                        else:
                            # For single payments, match by invoice number and amount and type
                            transaction_montant = float(transaction.get('montant', 0))
                            payment_montant = float(payment_details['montant_paye'])
                            
                            # For achat (purchases), caisse transactions should be negative (outgoing)
                            # For vente (sales), caisse transactions should be positive (incoming)
                            expected_type = 'decaissement' if is_achat else 'encaissement'
                            actual_type = transaction.get('type', '').lower()
                            
                            # Check if amounts match (considering sign for achat)
                            amount_matches = False
                            if is_achat:
                                # For achat, transaction should be negative, so compare absolute values
                                amount_matches = abs(abs(transaction_montant) - payment_montant) < 0.01
                            else:
                                # For vente, transaction should be positive
                                amount_matches = abs(transaction_montant - payment_montant) < 0.01
                            
                            if (transaction.get('nfacture') == payment_details['nfacture'] and 
                                amount_matches and
                                actual_type == expected_type):
                                transaction_matches = True
                                print(f"[PAYMENT] Found matching caisse transaction: {transaction['id']} (type={actual_type}, amount={transaction_montant}, is_achat={is_achat})")
                        
                        if transaction_matches:
                            result = caisse_service.delete_transaction(transaction['id'])
                            if result:
                                print(f"[PAYMENT] Deleted related caisse transaction {transaction['id']}")
                            else:
                                print(f"[PAYMENT] Failed to delete caisse transaction {transaction['id']}")
                            
                            # For multiple payments, only delete one combined transaction
                            if is_multiple_payment:
                                break
                            
                except Exception as e:
                    print(f"[PAYMENT] Error deleting caisse transaction: {e}")
            
            # Step 3: Delete from retenu records
            try:
                from app.stfoom.data.retenu_repository import RetenuRepository
                from app.stfoom.services.retenu_service import RetenuService
                
                retenu_repository = RetenuRepository()
                retenu_service = RetenuService(retenu_repository)
                
                # Find retenu records related to this payment
                retenus = retenu_service.get_all_retenus()
                for retenu in retenus:
                    retenu_matches = False
                    
                    if is_multiple_payment and transaction_reference:
                        # For multiple payments, match by transaction reference in notes or source
                        if ((retenu.get('notes') and transaction_reference in retenu.get('notes', '')) or
                            (retenu.get('source') and transaction_reference in retenu.get('source', ''))):
                            retenu_matches = True
                            print(f"[PAYMENT] Found retenu by reference: {transaction_reference}")
                    else:
                        # For single payments, match by invoice number and source containing payment reference
                        if (retenu.get('nfacture') == payment_details['nfacture'] and
                            retenu.get('source') and 
                            str(payment_details['nfacture']) in str(retenu.get('source', ''))):
                            retenu_matches = True
                    
                    if retenu_matches:
                        result = retenu_repository.delete_retenu(retenu['id'])
                        if result:
                            print(f"[PAYMENT] Deleted related retenu record {retenu['id']}")
                        else:
                            print(f"[PAYMENT] Failed to delete retenu record {retenu['id']}")
                        
                        # For multiple payments, only delete one combined retenu
                        if is_multiple_payment:
                            break
                        
            except Exception as e:
                print(f"[PAYMENT] Error deleting retenu record: {e}")
            
            # Step 4: If this is a multiple payment, also delete other payment records with the same reference
            if is_multiple_payment and transaction_reference:
                try:
                    print(f"[PAYMENT] Deleting other payments in multiple payment transaction: {transaction_reference}")
                    with self.get_connection() as conn:
                        cursor = conn.execute("""
                            DELETE FROM paiements_factures 
                            WHERE notes LIKE ? AND id != ?
                        """, (f'%{transaction_reference}%', payment_id))
                        conn.commit()
                        deleted_count = cursor.rowcount
                        if deleted_count > 0:
                            print(f"[PAYMENT] Deleted {deleted_count} related payment records")
                            
                except Exception as e:
                    print(f"[PAYMENT] Error deleting related payment records: {e}")
            
            # Step 5: Finally delete the main payment record itself
            with self.get_connection() as conn:
                cursor = conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                conn.commit()
                deleted = cursor.rowcount > 0
                
                if deleted:
                    print(f"[PAYMENT] Successfully deleted payment {payment_id}")
                    
                    # Log the deletion with detailed information
                    log_delete_action(
                        module="payment",
                        resource_type="payment",
                        resource_id=payment_id,
                        deleted_data={
                            "invoice": payment_details['nfacture'],
                            "montant": payment_details['montant_paye'],
                            "methode": payment_details['methode_paiement'],
                            "date": payment_details['date_paiement']
                        }
                    )
                else:
                    print(f"[PAYMENT] Failed to delete payment {payment_id}")
                
                return deleted
                
        except Exception as e:
            print(f"[PAYMENT] Error deleting payment {payment_id}: {e}")
            return False

    def get_invoice_payment_status(self, nfacture: int, invoice_total: float, retenu_amount: float = 0.0) -> Dict[str, Any]:
        """Get payment status for an invoice with retenu consideration and avoir-aware netting.

        When the invoice is part of a multiple payment transaction that includes avoirs (credits),
        we allocate the total credit pool (sum of avoir TTC without timbre) proportionally across the
        positive invoices in that MULTI batch and treat the allocated portion as effectively paid.
        """
        # Defensive coercion: handle None or non-numeric invoice_total/retenu_amount
        try:
            invoice_total = float(invoice_total or 0.0)
        except Exception:
            invoice_total = 0.0
        try:
            retenu_amount = float(retenu_amount or 0.0)
        except Exception:
            retenu_amount = 0.0

        with self.get_connection() as conn:
            cursor = conn.execute("""
                SELECT SUM(montant_paye) as total_paid, COUNT(*) as payment_count
                FROM paiements_factures 
                WHERE nfacture = ?
            """, (nfacture,))
            
            result = cursor.fetchone()
            total_paid = result[0] or 0.0
            payment_count = result[1] or 0
            
            # Get configurable tolerance from settings
            try:
                from app.stfoom.services.settings_service import SettingsService
                settings_service = SettingsService()
                tolerance = settings_service.get_payment_tolerance()
                include_retenu = settings_service.should_include_retenu_in_payment_calculation()
            except Exception as e:
                print(f"[PAYMENT] Could not load settings, using defaults: {e}")
                tolerance = 40.0  # Default tolerance
                include_retenu = True
            
            # Calculate expected payment amount with null safety
            retenu_amount = retenu_amount or 0.0  # Handle None values
            
            if include_retenu:
                expected_payment = invoice_total - retenu_amount
            else:
                expected_payment = invoice_total

            # --- AVOIR-AWARE ADJUSTMENT (MULTI-PAIEMENT) ---
            # If this invoice participated in a MULTI- payment that applied credits,
            # subtract its allocated share of the avoir pool (TTC sans timbre) from expected
            # OR equivalently treat it as additional effective payment.
            effective_paid = total_paid
            try:
                import re
                # Find a MULTI reference from any payments on this invoice
                ref_cur = conn.execute(
                    """
                    SELECT notes FROM paiements_factures
                    WHERE nfacture = ? AND notes LIKE '%MULTI-%'
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (nfacture,)
                )
                ref_row = ref_cur.fetchone()
                multi_ref = None
                if ref_row and ref_row[0]:
                    m = re.search(r'(MULTI-\d{8}-\d{6})', ref_row[0])
                    if m:
                        multi_ref = m.group(1)

                if multi_ref:
                    # Get all payments in this MULTI batch
                    batch_cur = conn.execute(
                        """
                        SELECT DISTINCT nfacture FROM paiements_factures
                        WHERE notes LIKE ?
                        """,
                        (f'%{multi_ref}%',)
                    )
                    batch_invoices = [row[0] for row in batch_cur.fetchall() if row and row[0] is not None]
                    if batch_invoices:
                        total_positive_excl_timbre = 0.0
                        total_credit_pool = 0.0
                        invoice_excl_timbre = 0.0

                        for inv_id in batch_invoices:
                            # Try ventes first, then achats
                            ttc = None
                            timbre = 0.0
                            try:
                                vcur = conn.execute("SELECT ttc, timbre FROM ventes WHERE nfacture = ?", (inv_id,))
                                vrow = vcur.fetchone()
                                if vrow:
                                    ttc = float(vrow[0] or 0)
                                    timbre = float(vrow[1] or 0)
                            except Exception:
                                ttc = None
                            if ttc is None:
                                try:
                                    acur = conn.execute("SELECT ttc, timbre FROM achats WHERE id = ?", (inv_id,))
                                    arow = acur.fetchone()
                                    if arow:
                                        ttc = float(arow[0] or 0)
                                        timbre = float(arow[1] or 0)
                                except Exception:
                                    ttc = 0.0
                                    timbre = 0.0

                            if ttc is None:
                                ttc = 0.0

                            if ttc >= 0:
                                # Positive invoice contributes to denominator
                                excl_timbre = max(0.0, ttc - timbre)
                                total_positive_excl_timbre += excl_timbre
                                if inv_id == nfacture:
                                    invoice_excl_timbre = excl_timbre
                            else:
                                # Avoir: contributes to credit pool (use TTC sans timbre)
                                excl_timbre_credit = max(0.0, abs(ttc) - timbre)
                                total_credit_pool += excl_timbre_credit

                        if total_positive_excl_timbre > 0 and invoice_excl_timbre > 0 and total_credit_pool > 0:
                            # Allocate credit proportionally
                            allocated_credit = total_credit_pool * (invoice_excl_timbre / total_positive_excl_timbre)
                            # Cap by remaining after actual payments
                            remaining_after_paid = max(0.0, expected_payment - total_paid)
                            credit_applied = min(allocated_credit, remaining_after_paid)
                            effective_paid += credit_applied
                            # Also reduce expected by allocated credit to keep remaining coherent
                            expected_payment = max(0.0, expected_payment - allocated_credit)
                            print(f"[PAYMENT] Avoir-aware allocation for {nfacture}: pool={total_credit_pool:.3f}, share={allocated_credit:.3f}, applied={credit_applied:.3f}")
            except Exception as e:
                print(f"[PAYMENT] Avoir-aware status adjustment skipped: {e}")
            
            # --- MULTI-BATCH UNIFIED STATUS RULE ---
            # If part of a MULTI transaction, compute batch-level status so all invoices share the same status.
            try:
                if 'multi_ref' not in locals():
                    # Ensure multi_ref detection ran earlier
                    multi_ref = None
                    ref_cur2 = conn.execute(
                        """
                        SELECT notes FROM paiements_factures
                        WHERE nfacture = ? AND notes LIKE '%MULTI-%'
                        ORDER BY created_at DESC LIMIT 1
                        """,
                        (nfacture,)
                    )
                    ref_row2 = ref_cur2.fetchone()
                    if ref_row2 and ref_row2[0]:
                        import re as _re
                        m2 = _re.search(r'(MULTI-\d{8}-\d{6})', ref_row2[0])
                        if m2:
                            multi_ref = m2.group(1)

                if multi_ref:
                    # Get all invoices in this MULTI batch
                    batch_cur2 = conn.execute(
                        """
                        SELECT DISTINCT nfacture FROM paiements_factures
                        WHERE notes LIKE ?
                        """,
                        (f'%{multi_ref}%',)
                    )
                    batch_invoices2 = [row[0] for row in batch_cur2.fetchall() if row and row[0] is not None]
                    # Compute total positive TTC and credit pool (avoir sans timbre)
                    total_positive_ttc = 0.0
                    total_credit_pool_batch = 0.0
                    positive_ids = []
                    for inv_id in batch_invoices2:
                        ttc2 = None
                        timbre2 = 0.0
                        try:
                            vcur2 = conn.execute("SELECT ttc, timbre FROM ventes WHERE nfacture = ?", (inv_id,))
                            vrow2 = vcur2.fetchone()
                            if vrow2:
                                ttc2 = float(vrow2[0] or 0)
                                timbre2 = float(vrow2[1] or 0)
                        except Exception:
                            ttc2 = None
                        if ttc2 is None:
                            try:
                                acur2 = conn.execute("SELECT ttc, timbre FROM achats WHERE id = ?", (inv_id,))
                                arow2 = acur2.fetchone()
                                if arow2:
                                    ttc2 = float(arow2[0] or 0)
                                    timbre2 = float(arow2[1] or 0)
                            except Exception:
                                ttc2 = 0.0
                                timbre2 = 0.0

                        if (ttc2 or 0.0) >= 0:
                            total_positive_ttc += (ttc2 or 0.0)
                            positive_ids.append(inv_id)
                        else:
                            # Avoir: add TTC sans timbre to credit pool
                            total_credit_pool_batch += max(0.0, abs(ttc2 or 0.0) - (timbre2 or 0.0))

                    # Compute total retenu for this MULTI if settings allow retenu
                    total_retenu_batch = 0.0
                    if include_retenu:
                        try:
                            # Prefer combined retenu created by multiple payment flow (source='paiement_multiple')
                            rcur = conn.execute(
                                """
                                SELECT SUM(retenu_amount) FROM retenus
                                WHERE source = 'paiement_multiple' AND notes LIKE ?
                                """,
                                (f'%{multi_ref}%',)
                            )
                            rsum = rcur.fetchone()
                            if rsum and rsum[0]:
                                total_retenu_batch = float(rsum[0] or 0)
                        except Exception:
                            total_retenu_batch = 0.0

                    # Expected at batch level: total TTC (positives) - retenu - avoir(sans timbre)
                    expected_batch = max(0.0, total_positive_ttc - total_retenu_batch - total_credit_pool_batch)

                    # Total paid at batch level: sum payments across positive invoices in this batch
                    if positive_ids:
                        placeholders = ",".join(["?"] * len(positive_ids))
                        query = (
                            f"""
                            SELECT SUM(montant_paye) FROM paiements_factures
                            WHERE notes LIKE ? AND nfacture IN ({placeholders})
                            """
                        )
                        params = [f'%{multi_ref}%'] + positive_ids
                        paid_cur = conn.execute(query, params)
                        paid_row = paid_cur.fetchone()
                        total_paid_batch = float(paid_row[0] or 0.0)
                    else:
                        total_paid_batch = 0.0

                    # Decide unified status for the batch
                    if total_paid_batch >= (expected_batch - tolerance) and expected_batch > 0:
                        status = "payé"
                    elif total_paid_batch > 0:
                        status = "partiellement payé"
                    else:
                        status = "non payé"
            except Exception as _batch_e:
                # If batch logic fails, fall back to per-invoice logic
                pass

            # Calculate payment status with configurable tolerance (per-invoice fallback or already unified above)
            if 'status' not in locals():
                if (payment_count > 0 or effective_paid > 0) and effective_paid >= (expected_payment - tolerance):
                    status = "payé"
                elif effective_paid > 0:
                    status = "partiellement payé"
                else:
                    status = "non payé"
            
            return {
                'total_paid': total_paid,
                'effective_paid': effective_paid,
                'expected_payment': expected_payment,
                'retenu_amount': retenu_amount,
                'remaining': max(0, expected_payment - effective_paid),
                'status': status,
                'payment_count': payment_count,
                'tolerance_used': tolerance
            }

class PaymentService:
    """Service layer for payment operations"""
    
    def __init__(self, payment_repository: Optional[PaymentRepository] = None):
        self.payment_repository = payment_repository or PaymentRepository()
        # Initialize tables on service creation
        self.payment_repository.init_tables()

    def add_payment(self, nfacture: int, montant_paye: float, 
                   methode_paiement: str, date_paiement: Optional[str] = None,
                   reference_paiement: Optional[str] = None, 
                   notes: Optional[str] = None, is_achat: bool = False) -> int:
        """Add a new payment for vente (sale) or achat (purchase)"""
        # Validate method
        if methode_paiement not in ['banque', 'caisse']:
            raise ValueError("Payment method must be 'banque' or 'caisse'")
        
        # Use current date if not provided
        if not date_paiement:
            date_paiement = date.today().strftime('%Y-%m-%d')
        
        # Validate amount
        if montant_paye <= 0:
            raise ValueError("Payment amount must be positive")
        
        payment_data = {
            'nfacture': nfacture,
            'montant_paye': montant_paye,
            'methode_paiement': methode_paiement,
            'date_paiement': date_paiement,
            'reference_paiement': reference_paiement,
            'notes': notes
        }
        
        return self.payment_repository.add_payment(payment_data, is_achat)

    def get_invoice_payments(self, nfacture: int, is_achat: bool = False) -> List[Dict[str, Any]]:
        """Get all payments for an invoice (vente or achat)"""
        return self.payment_repository.get_payments_by_invoice(nfacture, is_achat)

    def get_paiements_facture(self, nfacture: int, is_achat: bool = False) -> List[Dict[str, Any]]:
        """Legacy method name - same as get_invoice_payments"""
        return self.get_invoice_payments(nfacture, is_achat)

    def get_payment_status(self, nfacture: int, invoice_total: float, retenu_amount: float = 0.0) -> Dict[str, Any]:
        """Get payment status for an invoice with retenu consideration"""
        return self.payment_repository.get_invoice_payment_status(nfacture, invoice_total, retenu_amount)
    
    # ========== SMART AVOIR HANDLING FOR PAYMENTSERVICE ==========
    
    def get_invoice_payment_status_formatted(self, nfacture: int, invoice_total: float, 
                                           retenu_amount: float = 0.0, is_achat: bool = False) -> str:
        """Get formatted payment status with smart avoir handling"""
        status_info = self.get_smart_payment_status(nfacture, invoice_total, retenu_amount, is_achat)
        return status_info['display']  # Return the formatted display text
    
    def classify_invoice_type(self, ttc_amount: float) -> Dict[str, any]:
        """Classify invoice as regular facture or avoir (credit note)"""
        if ttc_amount > 0:
            return {
                'type': 'FACTURE',
                'display_name': 'Facture',
                'icon': '📄',
                'status_logic': 'regular',
                'color': 'normal'
            }
        elif ttc_amount < 0:
            return {
                'type': 'AVOIR',
                'display_name': 'Avoir (Crédit)',
                'icon': '🏷️', 
                'status_logic': 'credit',
                'color': 'credit'
            }
        else:
            return {
                'type': 'ZERO',
                'display_name': 'Zéro',
                'icon': '⭕',
                'status_logic': 'neutral',
                'color': 'neutral'
            }
    
    def get_smart_payment_status(self, nfacture: int, invoice_total: float, 
                                retenu_amount: float = 0.0, is_achat: bool = False) -> Dict[str, Any]:
        """Get payment status with smart avoir handling"""
        classification = self.classify_invoice_type(invoice_total)
        
        # Get payments for this invoice
        payments = self.get_invoice_payments(nfacture, is_achat)
        total_paid = sum(p.get('montant_paye', 0) for p in payments)
        payment_count = len(payments)
        
        if classification['status_logic'] == 'credit':
            # Special logic for avoir (credit notes)
            credit_amount = abs(invoice_total)
            
            if total_paid == 0:
                status = "crédit disponible"
                display = f"💳 Crédit de {credit_amount:.3f} DT disponible"
            elif abs(total_paid) >= credit_amount:
                status = "crédit appliqué"
                display = f"✅ Crédit de {credit_amount:.3f} DT appliqué"
            else:
                status = "crédit partiel"
                display = f"🔄 Crédit partiel: {abs(total_paid):.3f} / {credit_amount:.3f} DT"
            
            return {
                'total_paid': total_paid,
                'expected_payment': 0,  # No payment expected for credits
                'retenu_amount': 0,     # No retenu for credits
                'remaining': 0,         # No remaining amount for credits
                'status': status,
                'display': display,
                'payment_count': payment_count,
                'credit_amount': credit_amount,
                'is_credit': True,
                'classification': classification
            }
        else:
            # Use regular payment status logic
            regular_status = self.get_payment_status(nfacture, invoice_total, retenu_amount)
            regular_status['is_credit'] = False
            regular_status['classification'] = classification
            regular_status['display'] = self.format_payment_status_detailed(regular_status)
            return regular_status
    
    def format_payment_status_detailed(self, status_info: Dict[str, Any]) -> str:
        """Format detailed payment status for display"""
        status = status_info['status']
        total_paid = status_info.get('total_paid', 0)
        expected = status_info.get('expected_payment', 0)
        
        if status == 'payé':
            return f"✅ Payé: {total_paid:.3f} DT"
        elif status == 'partiellement payé':
            return f"🔄 Partiel: {total_paid:.3f} / {expected:.3f} DT"
        else:
            return f"❌ Non payé: 0 / {expected:.3f} DT"

    def update_payment(self, payment_id: int, montant_paye: float,
                      methode_paiement: str, date_paiement: str,
                      reference_paiement: Optional[str] = None,
                      notes: Optional[str] = None,
                      banque_id: Optional[int] = None,
                      echeance: Optional[str] = None) -> bool:
        """Update an existing payment and ALL related records using cascade manager"""
        # Validate method
        if methode_paiement not in ['banque', 'caisse', 'traite']:
            raise ValueError("Payment method must be 'banque', 'caisse', or 'traite'")
        
        # Validate amount
        if montant_paye <= 0:
            raise ValueError("Payment amount must be positive")
        
        try:
            # Use cascade manager for complete update
            from app.stfoom.services.cascade_manager import cascade_manager
            
            update_data = {
                'montant_paye': montant_paye,
                'methode_paiement': methode_paiement,
                'date_paiement': date_paiement,
                'reference_paiement': reference_paiement,
                'notes': notes
            }
            
            if banque_id is not None:
                update_data['banque_id'] = banque_id
                
            if echeance is not None:
                update_data['echeance'] = echeance
            
            result = cascade_manager.update_payment_cascade(payment_id, update_data)
            
            if 'error' in result:
                print(f"[PAYMENT_SERVICE] Failed to update payment {payment_id}: {result['error']}")
                return False
            
            print(f"[PAYMENT_SERVICE] Successfully updated payment {payment_id} with cascades")
            return True
            
        except Exception as e:
            print(f"[PAYMENT_SERVICE] Error updating payment {payment_id}: {e}")
            # Fallback to basic update
            payment_data = {
                'montant_paye': montant_paye,
                'methode_paiement': methode_paiement,
                'date_paiement': date_paiement,
                'reference_paiement': reference_paiement,
                'notes': notes
            }
            return self.payment_repository.update_payment(payment_id, payment_data)

    def delete_payment(self, payment_id: int, is_achat: bool = False) -> bool:
        """Delete a payment and ALL related records (retenu, bank, caisse) using cascade manager"""
        try:
            # Use cascade manager for complete deletion
            from app.stfoom.services.cascade_manager import cascade_manager
            result = cascade_manager.delete_payment_cascade(payment_id)
            
            if 'error' in result:
                print(f"[PAYMENT_SERVICE] Failed to delete payment {payment_id}: {result['error']}")
                return False
            
            print(f"[PAYMENT_SERVICE] Successfully deleted payment {payment_id} with cascades")
            return True
            
        except Exception as e:
            print(f"[PAYMENT_SERVICE] Error deleting payment {payment_id}: {e}")
            # Fallback to basic deletion
            return self.payment_repository.delete_payment(payment_id, is_achat=is_achat)

    def supprimer_paiement(self, payment_id: int, is_achat: bool = False) -> bool:
        """Delete a payment (French alias)"""
        return self.delete_payment(payment_id, is_achat=is_achat)

    def mark_invoice_paid_bank(self, nfacture: int, montant: float, date_paiement: str, 
                             reference: str, notes: str = '', banque_id: int = None, 
                             mode_paiement: str = '', echeance: str = '') -> int:
        """Mark an invoice as paid via bank with full parameters"""
        # Create the payment record
        payment_id = self.add_payment(
            nfacture=nfacture,
            montant_paye=montant,
            methode_paiement='banque',
            date_paiement=date_paiement,
            reference_paiement=reference,
            notes=notes
        )
        
        # Also create bank transaction record if bank_id provided
        # If no bank provided, try to resolve default bank to ensure offline safety
        if not banque_id:
            try:
                from app.stfoom.data.bank_repository import BankRepository as _BR__
                from app.stfoom.services.bank_service import BankService as _BS__
                _br__ = _BR__()
                _bs__ = _BS__(_br__)
                _default_bank__ = _bs__.get_default_bank()
                if _default_bank__ and _default_bank__.get('id'):
                    banque_id = _default_bank__['id']
                    print(f"[PAYMENT] Using default bank {banque_id} for invoice {nfacture}")
            except Exception as _e__:
                print(f"[PAYMENT] Could not resolve default bank: {_e__}")

        if banque_id and payment_id:
            try:
                from app.stfoom.services.bank_service import BankService
                bank_service = BankService()
                
                # Get client name from vente record
                client_name = ""
                try:
                    with self.get_connection() as conn:
                        cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE nfacture = ?", (nfacture,))
                        row = cursor.fetchone()
                        if row:
                            client_name = row[0] or ""
                except Exception as e:
                    print(f"[PAYMENT] Could not get client name: {e}")
                
                # Create bank transaction record
                bank_success = bank_service.create_transaction(
                    banque_id=banque_id,
                    type_transaction='encaissement',
                    montant=montant,
                    date_transaction=date_paiement,
                    description=f"Paiement facture {nfacture} - {notes}" if notes else f"Paiement facture {nfacture}",
                    numero_cheque=reference,
                    nfacture=nfacture,
                    nom_client=client_name,
                    mode_paiement=mode_paiement,
                    echeance=echeance
                )
                
                if not bank_success:
                    print(f"[PAYMENT] Warning: Payment recorded but bank transaction failed for invoice {nfacture}")
                    
            except Exception as e:
                print(f"[PAYMENT] Error creating bank transaction: {e}")
        
        return payment_id

    def mark_invoice_paid_cash(self, nfacture: int, montant: float, date_paiement: str,
                             reference: str = '', notes: str = '', mode_paiement: str = '', 
                             echeance: str = '') -> int:
        """Mark an invoice as paid via cash with full parameters"""
        return self.add_payment(
            nfacture=nfacture,
            montant_paye=montant,
            methode_paiement='caisse',
            date_paiement=date_paiement,
            reference_paiement=reference,
            notes=notes
        )

    def marquer_facture_payee_banque(self, nfacture: int, montant: float, date_paiement: str,
                                   reference: str, notes: str = '', banque_id: int = None,
                                   mode_paiement: str = '', echeance: str = '', retenu_percent: float = 0.0,
                                   retenu_amount: float = 0.0, is_achat: bool = False) -> int:
        """French alias for mark_invoice_paid_bank with retenu support"""
        return self._create_payment_with_integrations(
            nfacture, montant, date_paiement, reference, 'banque', notes, 
            banque_id, mode_paiement, echeance, retenu_percent, retenu_amount, is_achat
        )

    def marquer_facture_payee_caisse(self, nfacture: int, montant: float, date_paiement: str,
                                    reference: str = '', notes: str = '', mode_paiement: str = '',
                                    echeance: str = '', retenu_percent: float = 0.0,
                                    retenu_amount: float = 0.0, is_achat: bool = False) -> int:
        """French alias for mark_invoice_paid_cash with retenu support"""
        return self._create_payment_with_integrations(
            nfacture, montant, date_paiement, reference, 'caisse', notes,
            None, mode_paiement, echeance, retenu_percent, retenu_amount, is_achat
        )
    
    def _create_payment_with_integrations(self, nfacture: int, montant: float, date_paiement: str,
                                        reference: str, methode: str, notes: str = '',
                                        banque_id: int = None, mode_paiement: str = '', echeance: str = '',
                                        retenu_percent: float = 0.0, retenu_amount: float = 0.0, is_achat: bool = False) -> int:
        """Create payment with bank and retenu integrations"""
        
        # Auto-calculate retenu_amount if only percent is provided
        if retenu_percent > 0 and retenu_amount == 0.0:
            # Get the original invoice amount to calculate retenu
            try:
                with self.payment_repository.get_connection() as conn:
                    if is_achat:
                        cursor = conn.execute("SELECT ttc, timbre FROM achats WHERE id = ?", (nfacture,))
                    else:
                        cursor = conn.execute("SELECT ttc, timbre FROM ventes WHERE nfacture = ?", (nfacture,))
                    row = cursor.fetchone()
                    if row:
                        invoice_total = float(row[0] or 0)
                        invoice_timbre = float(row[1] or 1.0)
                        
                        # 🔧 FIX: Calculate retenu on (TTC - timbre) to exclude timbre from retenu base
                        retenu_base = max(0, invoice_total - invoice_timbre)
                        retenu_amount = retenu_base * (retenu_percent / 100.0)
                        
                        print(f"[PAYMENT] Retenu calculation: TTC={invoice_total} DT, Timbre={invoice_timbre} DT")
                        print(f"[PAYMENT] Retenu base (TTC-Timbre): {retenu_base} DT")
                        print(f"[PAYMENT] Calculated retenu: {retenu_amount} DT ({retenu_percent}% of {retenu_base} DT)")
            except Exception as e:
                print(f"[PAYMENT] Could not auto-calculate retenu amount: {e}")
        
        # Create the main payment record
        payment_id = self.add_payment(
            nfacture=nfacture,
            montant_paye=montant,
            methode_paiement=methode,
            date_paiement=date_paiement,
            reference_paiement=reference,
            notes=notes,
            is_achat=is_achat
        )
        
        if not payment_id:
            return 0
        
        # Get client information for integrations (use alias for achat when available)
        client_name = ""
        try:
            with self.payment_repository.get_connection() as conn:
                if is_achat:
                    cursor = conn.execute("SELECT fournisseur, fournisseur_alias FROM achats WHERE id = ?", (nfacture,))
                else:
                    cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE nfacture = ?", (nfacture,))
                row = cursor.fetchone()
                if row:
                    if is_achat:
                        base = row[0] or ""
                        alias = row[1] if len(row) > 1 else None
                        client_name = (alias or base)
                    else:
                        client_name = row[0] or ""
        except Exception as e:
            print(f"[PAYMENT] Could not get client/supplier name: {e}")
        
        # Ensure we have a bank id for bank payments; fall back to default bank if needed
        if methode == 'banque' and not banque_id:
            try:
                from app.stfoom.data.bank_repository import BankRepository
                from app.stfoom.services.bank_service import BankService
                _br = BankRepository()
                _bs = BankService(_br)
                _default = _bs.get_default_bank()
                if _default and _default.get('id'):
                    banque_id = _default['id']
                    print(f"[PAYMENT] Using default bank {banque_id} for invoice {nfacture}")
            except Exception as _e:
                print(f"[PAYMENT] Could not resolve default bank: {_e}")

        # Create bank transaction if it's a bank payment
        if methode == 'banque' and banque_id:
            try:
                from app.stfoom.services.bank_service import BankService
                from app.stfoom.data.bank_repository import BankRepository
                bank_repository = BankRepository()
                bank_service = BankService(bank_repository)
                
                # For achat, use decaissement (outgoing), for vente, use encaissement (incoming)
                transaction_type = 'decaissement' if is_achat else 'encaissement'
                description_prefix = "Paiement achat" if is_achat else "Paiement facture"
                
                bank_success = bank_service.create_transaction(
                    banque_id=banque_id,
                    type_transaction=transaction_type,
                    montant=montant,
                    date_transaction=date_paiement,
                    description=f"{description_prefix} {nfacture} - {notes}" if notes else f"{description_prefix} {nfacture}",
                    numero_cheque=reference,
                    nfacture=nfacture,
                    nom_client=client_name or "Inconnu",
                    mode_paiement=mode_paiement,
                    echeance=echeance
                )
                
                # Create calendar event for traite payments with échéance using cascade manager
                if mode_paiement == 'traite' and echeance:
                    try:
                        from app.stfoom.services.cascade_manager import cascade_manager
                        calendar_result = cascade_manager.create_calendar_event_for_traite(
                            payment_id, nfacture, echeance, client_name, montant
                        )
                        if 'error' not in calendar_result:
                            print(f"[PAYMENT] Calendar event {calendar_result['calendar_event_id']} created for traite payment {payment_id}")
                        else:
                            print(f"[PAYMENT] Warning: Could not create calendar event for traite: {calendar_result['error']}")
                        
                    except Exception as calendar_error:
                        print(f"[PAYMENT] Warning: Could not create calendar event for traite: {calendar_error}")
                
                if not bank_success:
                    print(f"[PAYMENT] Warning: Payment recorded but bank transaction failed for invoice {nfacture}")
                    
            except Exception as e:
                print(f"[PAYMENT] Error creating bank transaction: {e}")
        
        # Create caisse transaction if it's a cash payment
        elif methode == 'caisse':
            try:
                from app.stfoom.services.caisse_service import CaisseService
                from app.stfoom.data.caisse_repository import CaisseRepository
                caisse_repository = CaisseRepository()
                caisse_service = CaisseService(caisse_repository)
                
                # For achat, use decaissement (outgoing), for vente, use encaissement (incoming)
                transaction_type = 'decaissement' if is_achat else 'encaissement'
                description_prefix = "Paiement achat" if is_achat else "Paiement facture"
                
                caisse_success = caisse_service.create_transaction(
                    montant=montant,
                    date_str=date_paiement,
                    type_=transaction_type,
                    description=f"{description_prefix} {nfacture} - {client_name}" + (f" - {notes}" if notes else ""),
                    nfacture=nfacture
                )
                
                if not caisse_success:
                    print(f"[PAYMENT] Warning: Payment recorded but caisse transaction failed for invoice {nfacture}")
                    
            except Exception as e:
                print(f"[PAYMENT] Error creating caisse transaction: {e}")
        
        # Create retenu record if retenu amount > 0
        if retenu_amount > 0:
            try:
                from app.stfoom.services.retenu_service import RetenuService
                from app.stfoom.data.retenu_repository import RetenuRepository
                retenu_repository = RetenuRepository()
                retenu_service = RetenuService(retenu_repository)
                
                retenu_success = retenu_service.create_retenu(
                    date=date_paiement,
                    client=client_name or f"Client facture {nfacture}",
                    nfacture=nfacture,
                    percent=retenu_percent,
                    amount=retenu_amount,
                    source=f"Paiement facture {nfacture}",
                    notes=f"Retenu {retenu_percent}% sur paiement",
                    party_type=('fournisseur' if is_achat else 'client')
                )
                
                if not retenu_success:
                    print(f"[PAYMENT] Warning: Payment recorded but retenu record failed for invoice {nfacture}")
                    
            except Exception as e:
                print(f"[PAYMENT] Error creating retenu record: {e}")
        
        return payment_id

    def format_payment_method(self, method: str, mode_paiement: str = '') -> str:
        """Format payment method for display with optional mode"""
        base_format = {
            'banque': 'Banque',
            'caisse': 'Caisse'
        }.get(method, method)
        
        if mode_paiement:
            mode_display = {
                'virement': 'Virement',
                'cheque': 'Chèque', 
                'traite': 'Traite'
            }.get(mode_paiement, mode_paiement)
            return f"{base_format} - {mode_display}"
        
        return base_format

    def format_payment_status(self, status: str) -> str:
        """Format payment status for display"""
        status_map = {
            'payé': '✅ Payé',
            'partiellement payé': '🔄 Partiellement payé', 
            'non payé': '❌ Non payé',
            # Smart avoir status formatting
            'crédit disponible': '💳 Crédit disponible',
            'crédit appliqué': '✅ Crédit appliqué',
            'crédit partiel': '🔄 Crédit partiel'
        }
        return status_map.get(status, status)
    
    # ========== SMART AVOIR METHODS (Essential only) ==========
    
    def classify_invoice_type(self, ttc_amount: float) -> Dict[str, any]:
        """Classify invoice as regular facture or avoir (credit note)"""
        if ttc_amount > 0:
            return {'type': 'FACTURE', 'display_name': 'Facture', 'icon': '📄', 'status_logic': 'regular', 'color': 'normal'}
        elif ttc_amount < 0:
            return {'type': 'AVOIR', 'display_name': 'Avoir (Crédit)', 'icon': '🏷️', 'status_logic': 'credit', 'color': 'credit'}
        else:
            return {'type': 'ZERO', 'display_name': 'Zéro', 'icon': '⭕', 'status_logic': 'neutral', 'color': 'neutral'}
    
    def get_smart_invoice_status(self, nfacture: int, invoice_total: float, retenu_amount: float = 0.0, is_achat: bool = False) -> str:
        """Get formatted payment status with smart avoir handling - for UI display"""
        classification = self.classify_invoice_type(invoice_total)
        
        if classification['status_logic'] == 'credit':
            # Special logic for avoir (credit notes)
            payments = self.get_invoice_payments(nfacture, is_achat)
            total_paid = sum(p.get('montant_paye', 0) for p in payments)
            credit_amount = abs(invoice_total)
            
            if total_paid == 0:
                return f"💳 Crédit de {credit_amount:.3f} DT disponible"
            elif abs(total_paid) >= credit_amount:
                return f"✅ Crédit de {credit_amount:.3f} DT appliqué"
            else:
                return f"🔄 Crédit partiel: {abs(total_paid):.3f} / {credit_amount:.3f} DT"
        else:
            # Use regular payment status for normal invoices (preserves retenu functionality)
            status_info = self.get_payment_status(nfacture, invoice_total, retenu_amount)
            status = status_info['status']
            return self.format_payment_status(status)


# Legacy compatibility functions for backward compatibility
    
    def get_smart_payment_status(self, nfacture: int, invoice_total: float, 
                                retenu_amount: float = 0.0, is_achat: bool = False) -> Dict[str, Any]:
        """Get payment status with smart avoir handling"""
        classification = self.classify_invoice_type(invoice_total)
        
        # Get payments for this invoice
        payments = self.get_invoice_payments(nfacture, is_achat)
        total_paid = sum(p.get('montant_paye', 0) for p in payments)
        payment_count = len(payments)
        
        if classification['status_logic'] == 'credit':
            # Special logic for avoir (credit notes)
            credit_amount = abs(invoice_total)
            
            if total_paid == 0:
                status = "crédit disponible"
                display = f"💳 Crédit de {credit_amount:.3f} DT disponible"
            elif abs(total_paid) >= credit_amount:
                status = "crédit appliqué"
                display = f"✅ Crédit de {credit_amount:.3f} DT appliqué"
            else:
                status = "crédit partiel"
                display = f"🔄 Crédit partiel: {abs(total_paid):.3f} / {credit_amount:.3f} DT"
            
            return {
                'total_paid': total_paid,
                'expected_payment': 0,  # No payment expected for credits
                'retenu_amount': 0,     # No retenu for credits
                'remaining': 0,         # No remaining amount for credits
                'status': status,
                'display': display,
                'payment_count': payment_count,
                'credit_amount': credit_amount,
                'is_credit': True,
                'classification': classification
            }
        else:
            # Use regular payment status logic
            regular_status = self.get_payment_status(nfacture, invoice_total, retenu_amount)
            regular_status['is_credit'] = False
            regular_status['classification'] = classification
            return regular_status
    
    def calculate_smart_multiple_payment(self, invoices: List[Dict]) -> Dict[str, any]:
        """Calculate smart net payment amount for multiple invoices with avoir handling"""
        invoice_total = 0.0
        credit_total = 0.0
        invoice_count = 0
        credit_count = 0
        
        breakdown = []
        
        for invoice in invoices:
            ttc = float(invoice.get('ttc', 0))
            nfacture = invoice.get('nfacture', 'Unknown')
            raison_sociale = invoice.get('raison_sociale', invoice.get('client', ''))
            classification = self.classify_invoice_type(ttc)
            
            if classification['type'] == 'FACTURE':
                invoice_total += ttc
                invoice_count += 1
                breakdown.append({
                    'type': 'invoice',
                    'nfacture': nfacture,
                    'client': raison_sociale,
                    'amount': ttc,
                    'display': f"#{nfacture}: +{ttc:.3f} DT",
                    'classification': classification
                })
            elif classification['type'] == 'AVOIR':
                credit_total += abs(ttc)  # Keep as positive for display
                credit_count += 1
                breakdown.append({
                    'type': 'credit',
                    'nfacture': nfacture,
                    'client': raison_sociale, 
                    'amount': ttc,
                    'display': f"#{nfacture}: -{abs(ttc):.3f} DT",
                    'classification': classification
                })
        
        net_amount = invoice_total - credit_total
        
        return {
            'invoice_total': invoice_total,
            'credit_total': credit_total,
            'net_amount': max(0, net_amount),  # Never negative payment
            'invoice_count': invoice_count,
            'credit_count': credit_count,
            'breakdown': breakdown,
            'display_summary': f"Factures: +{invoice_total:.3f} DT, Crédits: -{credit_total:.3f} DT = Net: {net_amount:.3f} DT",
            'has_credits': credit_count > 0,
            'payment_required': net_amount > 0,
            'auto_credit_application': credit_count > 0
        }
    
    def create_smart_multiple_payments(self, invoices: List[Dict], payment_info: Dict,
                                     transaction_ref: str, is_achat: bool = False) -> List[Dict]:
        """Create intelligent payment entries handling avoir automatically"""
        payment_results = []
        net_calc = self.calculate_smart_multiple_payment(invoices)
        
        # If no payment required (credits >= invoices), auto-apply credits
        if not net_calc['payment_required']:
            return self._auto_apply_credits(invoices, transaction_ref, is_achat)
        
        # Calculate proportional payments for invoices only
        invoice_invoices = [inv for inv in invoices if float(inv.get('ttc', 0)) > 0]
        total_invoice_amount = sum(float(inv.get('ttc', 0)) for inv in invoice_invoices)
        
        if total_invoice_amount <= 0:
            return []
        
        # Create payment entries for invoices
        for invoice in invoice_invoices:
            ttc = float(invoice.get('ttc', 0))
            nfacture = invoice.get('nfacture')
            
            # Proportional payment
            proportion = ttc / total_invoice_amount
            payment_amount = net_calc['net_amount'] * proportion
            
            # Create actual payment record
            payment_id = self.add_payment(
                nfacture=nfacture,
                montant_paye=payment_amount,
                methode_paiement=payment_info.get('method', 'banque'),
                date_paiement=payment_info.get('date'),
                reference_paiement=payment_info.get('reference', transaction_ref),
                notes=f"[SMART-MULTI] {transaction_ref} - Proportional payment",
                is_achat=is_achat
            )
            
            payment_results.append({
                'nfacture': nfacture,
                'payment_id': payment_id,
                'amount': payment_amount,
                'type': 'regular_payment',
                'success': payment_id > 0
            })
        
        # Create auto-application entries for avoir
        avoir_invoices = [inv for inv in invoices if float(inv.get('ttc', 0)) < 0]
        for avoir in avoir_invoices:
            ttc = float(avoir.get('ttc', 0))
            nfacture = avoir.get('nfacture')
            
            # Create offsetting payment for the avoir amount
            payment_id = self.add_payment(
                nfacture=nfacture,
                montant_paye=abs(ttc),  # Positive amount to "pay" the negative invoice
                methode_paiement='caisse',  # Use caisse for automatic credit applications
                date_paiement=payment_info.get('date'),
                reference_paiement=f"AUTO-CREDIT-{transaction_ref}",
                notes=f"[SMART-MULTI] {transaction_ref} - Auto-application of credit",
                is_achat=is_achat
            )
            
            payment_results.append({
                'nfacture': nfacture,
                'payment_id': payment_id,
                'amount': abs(ttc),
                'type': 'credit_application',
                'success': payment_id > 0
            })
        
        return payment_results
    
    def _auto_apply_credits(self, invoices: List[Dict], transaction_ref: str, is_achat: bool = False) -> List[Dict]:
        """Auto-apply credits when no payment required"""
        results = []
        
        for invoice in invoices:
            ttc = float(invoice.get('ttc', 0))
            nfacture = invoice.get('nfacture')
            
            if ttc < 0:
                # Auto-apply avoir
                payment_id = self.add_payment(
                    nfacture=nfacture,
                    montant_paye=abs(ttc),
                    methode_paiement='caisse',
                    date_paiement=datetime.now().strftime('%Y-%m-%d'),
                    reference_paiement=f"AUTO-FULL-CREDIT-{transaction_ref}",
                    notes=f"[SMART-MULTI] {transaction_ref} - Automatic full credit application",
                    is_achat=is_achat
                )
                
                results.append({
                    'nfacture': nfacture,
                    'payment_id': payment_id,
                    'amount': abs(ttc),
                    'type': 'credit_auto_application',
                    'success': payment_id > 0
                })
            else:
                # Mark invoice as offset by credits
                payment_id = self.add_payment(
                    nfacture=nfacture,
                    montant_paye=ttc,
                    methode_paiement='caisse',
                    date_paiement=datetime.now().strftime('%Y-%m-%d'),
                    reference_paiement=f"CREDIT-OFFSET-{transaction_ref}",
                    notes=f"[SMART-MULTI] {transaction_ref} - Invoice offset by available credits",
                    is_achat=is_achat
                )
                
                results.append({
                    'nfacture': nfacture,
                    'payment_id': payment_id,
                    'amount': ttc,
                    'type': 'credit_offset',
                    'success': payment_id > 0
                })
        
        return results

# Legacy compatibility functions for backward compatibility
def ajouter_paiement(*args, **kwargs):
    """Legacy function - use PaymentService.add_payment instead"""
    service = PaymentService()
    return service.add_payment(*args, **kwargs)

def get_paiements_facture(nfacture: int):
    """Legacy function - use PaymentService.get_invoice_payments instead"""
    service = PaymentService()
    return service.get_invoice_payments(nfacture)

def supprimer_paiement(payment_id: int, is_achat: bool = False):
    """Legacy function - use PaymentService.delete_payment instead"""
    service = PaymentService()
    return service.delete_payment(payment_id, is_achat=is_achat)

def get_statut_paiement_facture(nfacture: int, invoice_total: float = 0.0, retenu_amount: float = 0.0):
    """Legacy function - use PaymentService.get_payment_status instead"""
    service = PaymentService()
    return service.get_payment_status(nfacture, invoice_total, retenu_amount)

def marquer_facture_payee_banque(nfacture: int, montant: float, date_paiement: str,
                                reference: str, notes: str = '', banque_id: int = None,
                                mode_paiement: str = '', echeance: str = '', 
                                retenu_percent: float = 0.0, retenu_amount: float = 0.0):
    """Legacy function - use PaymentService.marquer_facture_payee_banque instead"""
    service = PaymentService()
    return service.marquer_facture_payee_banque(nfacture, montant, date_paiement, reference,
                                              notes, banque_id, mode_paiement, echeance,
                                              retenu_percent, retenu_amount)

def marquer_facture_payee_caisse(nfacture: int, montant: float, date_paiement: str,
                                reference: str = '', notes: str = '', mode_paiement: str = '',
                                echeance: str = '', retenu_percent: float = 0.0, retenu_amount: float = 0.0):
    """Legacy function - use PaymentService.marquer_facture_payee_caisse instead"""
    service = PaymentService()
    return service.marquer_facture_payee_caisse(nfacture, montant, date_paiement, reference,
                                              notes, mode_paiement, echeance,
                                              retenu_percent, retenu_amount)
