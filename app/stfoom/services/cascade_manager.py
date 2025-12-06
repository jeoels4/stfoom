"""
CASCADE MANAGER - Data Relationship Integrity
=============================================
Ensures that all related records are properly maintained across modules.

RELATIONSHIPS MANAGED:
- Payment ↔ Retenu ↔ Bank ↔ Caisse
- Invoice → All related payment records
- Automatic cleanup when records are deleted/modified

This prevents the issues where:
- Deleting a payment leaves orphaned retenu/bank records
- Modifying a payment doesn't update related records  
- Deleting an invoice leaves orphaned payments/retenu/bank records
"""

import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.core.path_manager import get_db_path


class CascadeManager:
    """Manages cascading operations across all financial modules"""
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = get_db_path()
        self.db_path = db_path
    
    def get_connection(self):
        """Get database connection"""
        return sqlite3.connect(self.db_path)
    
    # ========================================
    # PAYMENT CASCADE OPERATIONS
    # ========================================
    
    def delete_payment_cascade(self, payment_id: int) -> Dict[str, Any]:
        """
        Delete a payment and ALL related records
        Returns details of what was deleted
        """
        deleted_items = {
            'payment': None,
            'retenu_records': [],
            'bank_transactions': [],
            'caisse_transactions': [],
            'calendar_events': []
        }
        
        try:
            with self.get_connection() as conn:
                # Get payment details before deletion
                cursor = conn.execute("""
                    SELECT nfacture, montant_paye, methode_paiement, notes
                    FROM paiements_factures WHERE id = ?
                """, (payment_id,))
                payment = cursor.fetchone()
                
                if not payment:
                    return {'error': f'Payment {payment_id} not found'}
                
                nfacture, montant, methode, notes = payment
                deleted_items['payment'] = {
                    'id': payment_id, 
                    'nfacture': nfacture, 
                    'montant': montant,
                    'methode': methode
                }

                # Determine whether this payment belongs to an achat (purchase) or vente (sale)
                is_achat = False
                try:
                    # Vente exists if found in ventes; achat exists if found in achats
                    v = conn.execute("SELECT 1 FROM ventes WHERE nfacture = ? LIMIT 1", (nfacture,)).fetchone()
                    if not v:
                        a = conn.execute("SELECT 1 FROM achats WHERE id = ? LIMIT 1", (nfacture,)).fetchone()
                        is_achat = bool(a)
                except Exception:
                    # If check fails, default remains False (vente)
                    pass
                
                # Detect MULTI batch reference if present
                multi_ref = None
                try:
                    import re
                    if notes:
                        # Capture references like MULTI-YYYYMMDD-HHMMSS-ffffff
                        m = re.search(r'(MULTI-\d{8}-\d{6}(?:-\d{6})?)', notes)
                        if m:
                            multi_ref = m.group(1)
                except Exception:
                    pass

                # 1. Delete related retenu records
                # Check for retenu records linked to this invoice
                if multi_ref:
                    # Delete retenus that reference the MULTI batch in notes or source
                    cursor = conn.execute("""
                        SELECT id, retenu_amount FROM retenus 
                        WHERE (notes LIKE ? OR source LIKE ?)
                    """, (f'%{multi_ref}%', f'%{multi_ref}%'))
                    retenus_to_delete = cursor.fetchall()
                    deleted_items['retenu_records'] = [{'id': r[0], 'amount': r[1]} for r in retenus_to_delete]
                    conn.execute("DELETE FROM retenus WHERE (notes LIKE ? OR source LIKE ?)", (f'%{multi_ref}%', f'%{multi_ref}%'))
                else:
                    cursor = conn.execute("""
                        SELECT id, retenu_amount FROM retenus WHERE nfacture = ?
                    """, (nfacture,))
                    retenus_to_delete = cursor.fetchall()
                    deleted_items['retenu_records'] = [
                        {'id': r[0], 'amount': r[1]} for r in retenus_to_delete
                    ]
                    conn.execute("DELETE FROM retenus WHERE nfacture = ?", (nfacture,))
                
                # 2. Delete related bank transactions
                if multi_ref:
                    cursor = conn.execute("""
                        SELECT id, montant FROM transactions_bancaires
                        WHERE description LIKE ?
                    """, (f'%{multi_ref}%',))
                else:
                    cursor = conn.execute("""
                        SELECT id, montant FROM transactions_bancaires 
                        WHERE nfacture = ? AND type_transaction = ?
                    """, (nfacture, 'decaissement' if is_achat else 'encaissement'))
                bank_txs_to_delete = cursor.fetchall()
                deleted_items['bank_transactions'] = [
                    {'id': tx[0], 'montant': tx[1]} for tx in bank_txs_to_delete
                ]
                
                if multi_ref:
                    conn.execute("DELETE FROM transactions_bancaires WHERE description LIKE ?", (f'%{multi_ref}%',))
                else:
                    conn.execute("""
                        DELETE FROM transactions_bancaires 
                        WHERE nfacture = ? AND type_transaction = ?
                    """, (nfacture, 'decaissement' if is_achat else 'encaissement'))
                
                # 3. Delete related caisse transactions
                if multi_ref:
                    cursor = conn.execute("""
                        SELECT id, montant FROM caisse_transactions
                        WHERE description LIKE ?
                    """, (f'%{multi_ref}%',))
                else:
                    cursor = conn.execute("""
                        SELECT id, montant FROM caisse_transactions 
                        WHERE nfacture = ? AND type = ?
                    """, (nfacture, 'decaissement' if is_achat else 'encaissement'))
                caisse_txs_to_delete = cursor.fetchall()
                deleted_items['caisse_transactions'] = [
                    {'id': tx[0], 'montant': tx[1]} for tx in caisse_txs_to_delete
                ]
                
                if multi_ref:
                    conn.execute("DELETE FROM caisse_transactions WHERE description LIKE ?", (f'%{multi_ref}%',))
                else:
                    conn.execute("""
                        DELETE FROM caisse_transactions 
                        WHERE nfacture = ? AND type = ?
                    """, (nfacture, 'decaissement' if is_achat else 'encaissement'))
                
                # 4. Delete related calendar events for traite payments
                if methode == 'traite':
                    calendar_result = self.delete_calendar_event_for_traite(payment_id)
                    if 'deleted_event_id' in calendar_result:
                        deleted_items['calendar_events'].append(calendar_result)
                
                # 5. For MULTI: also delete other payment records in the same batch
                if multi_ref:
                    # Delete only payments belonging to this exact MULTI reference
                    conn.execute("DELETE FROM paiements_factures WHERE notes LIKE ?", (f'%{multi_ref}%',))
                else:
                    # Finally, delete the payment itself
                    conn.execute("DELETE FROM paiements_factures WHERE id = ?", (payment_id,))
                
                conn.commit()
                
                print(f"[CASCADE] Deleted payment {payment_id} and all related records:")
                print(f"  - Retenu records: {len(deleted_items['retenu_records'])}")
                print(f"  - Bank transactions: {len(deleted_items['bank_transactions'])}")
                print(f"  - Caisse transactions: {len(deleted_items['caisse_transactions'])}")
                if deleted_items['calendar_events']:
                    print(f"  - Calendar events: {len(deleted_items['calendar_events'])}")
                
                return deleted_items
                
        except Exception as e:
            print(f"[CASCADE] Error deleting payment {payment_id}: {e}")
            return {'error': str(e)}
    
    def update_payment_cascade(self, payment_id: int, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a payment and ALL related records
        Returns details of what was updated
        """
        updated_items = {
            'payment': None,
            'retenu_records': [],
            'bank_transactions': [],
            'caisse_transactions': [],
            'calendar_events': []
        }
        
        try:
            with self.get_connection() as conn:
                # Get current payment details
                cursor = conn.execute("""
                    SELECT nfacture, montant_paye, methode_paiement, banque_id, notes
                    FROM paiements_factures WHERE id = ?
                """, (payment_id,))
                current_payment = cursor.fetchone()
                
                if not current_payment:
                    return {'error': f'Payment {payment_id} not found'}
                
                current_nfacture, current_montant, current_methode, current_banque_id, current_notes = current_payment
                
                # Update the payment record
                updates = []
                values = []
                
                if 'montant_paye' in new_data:
                    updates.append('montant_paye = ?')
                    values.append(new_data['montant_paye'])
                    
                if 'methode_paiement' in new_data:
                    updates.append('methode_paiement = ?')
                    values.append(new_data['methode_paiement'])
                    
                if 'date_paiement' in new_data:
                    updates.append('date_paiement = ?')
                    values.append(new_data['date_paiement'])
                    
                if 'banque_id' in new_data:
                    updates.append('banque_id = ?')
                    values.append(new_data['banque_id'])
                    
                if 'echeance' in new_data:
                    updates.append('echeance = ?')
                    values.append(new_data['echeance'])
                    
                if 'notes' in new_data:
                    updates.append('notes = ?')
                    values.append(new_data['notes'])
                
                updates.append('updated_at = ?')
                values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                values.append(payment_id)
                
                if updates:
                    conn.execute(f"""
                        UPDATE paiements_factures 
                        SET {', '.join(updates)} 
                        WHERE id = ?
                    """, values)
                
                updated_items['payment'] = {'id': payment_id, 'changes': new_data}
                
                # Update related records based on changes
                new_montant = new_data.get('montant_paye', current_montant)
                new_methode = new_data.get('methode_paiement', current_methode)
                new_banque_id = new_data.get('banque_id', current_banque_id)
                
                # Determine whether this payment belongs to an achat (purchase) or vente (sale)
                is_achat = False
                try:
                    v = conn.execute("SELECT 1 FROM ventes WHERE nfacture = ? LIMIT 1", (current_nfacture,)).fetchone()
                    if not v:
                        a = conn.execute("SELECT 1 FROM achats WHERE id = ? LIMIT 1", (current_nfacture,)).fetchone()
                        is_achat = bool(a)
                except Exception:
                    pass

                # Update bank transactions if amount or bank changed
                if 'montant_paye' in new_data or 'banque_id' in new_data:
                    conn.execute("""
                        UPDATE transactions_bancaires 
                        SET montant = ?, banque_id = ?, updated_at = ?
                        WHERE nfacture = ? AND type_transaction = ?
                    """, (new_montant, new_banque_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_nfacture, 'decaissement' if is_achat else 'encaissement'))
                    
                    cursor = conn.execute("""
                        SELECT id FROM transactions_bancaires 
                        WHERE nfacture = ? AND type_transaction = ?
                    """, (current_nfacture, 'decaissement' if is_achat else 'encaissement'))
                    updated_bank_ids = [row[0] for row in cursor.fetchall()]
                    updated_items['bank_transactions'] = updated_bank_ids
                
                # Update caisse transactions if amount changed
                if 'montant_paye' in new_data:
                    conn.execute("""
                        UPDATE caisse_transactions 
                        SET montant = ?, updated_at = ?
                        WHERE nfacture = ? AND type = ?
                    """, (new_montant, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_nfacture, 'decaissement' if is_achat else 'encaissement'))
                    
                    cursor = conn.execute("""
                        SELECT id FROM caisse_transactions 
                        WHERE nfacture = ? AND type = ?
                    """, (current_nfacture, 'decaissement' if is_achat else 'encaissement'))
                    updated_caisse_ids = [row[0] for row in cursor.fetchall()]
                    updated_items['caisse_transactions'] = updated_caisse_ids
                
                # Update retenu records if there are retenu-related changes in notes
                if 'notes' in new_data and '[Retenu:' in new_data['notes']:
                    # Extract retenu percentage and update retenu records
                    import re
                    retenu_match = re.search(r'\[Retenu:\s*([\d.]+)%\]', new_data['notes'])
                    if retenu_match:
                        new_retenu_percent = float(retenu_match.group(1))
                        
                        # Get invoice total to calculate new retenu amount
                        cursor = conn.execute("SELECT ttc, timbre FROM ventes WHERE nfacture = ?", (current_nfacture,))
                        vente_data = cursor.fetchone()
                        if vente_data:
                            ttc, timbre = vente_data
                            retenu_base = ttc - (timbre or 0)
                            new_retenu_amount = retenu_base * new_retenu_percent / 100.0
                            
                            conn.execute("""
                                UPDATE retenus 
                                SET retenu_percent = ?, retenu_amount = ?, updated_at = ?
                                WHERE nfacture = ?
                            """, (new_retenu_percent, new_retenu_amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), current_nfacture))
                            
                            cursor = conn.execute("SELECT id FROM retenus WHERE nfacture = ?", (current_nfacture,))
                            updated_retenu_ids = [row[0] for row in cursor.fetchall()]
                            updated_items['retenu_records'] = updated_retenu_ids
                
                # Update calendar events for traite payments
                if current_methode == 'traite' or new_data.get('mode_paiement') == 'traite':
                    calendar_updates = {}
                    if 'echeance' in new_data:
                        calendar_updates['new_echeance'] = new_data['echeance']
                    if 'montant_paye' in new_data:
                        calendar_updates['new_montant'] = new_data['montant_paye']
                    
                    if calendar_updates:
                        calendar_result = self.update_calendar_event_for_traite(
                            payment_id, **calendar_updates
                        )
                        if 'calendar_event_id' in calendar_result:
                            updated_items['calendar_events'].append(calendar_result)
                
                conn.commit()
                
                print(f"[CASCADE] Updated payment {payment_id} and related records")
                return updated_items
                
        except Exception as e:
            print(f"[CASCADE] Error updating payment {payment_id}: {e}")
            return {'error': str(e)}
    
    # ========================================
    # INVOICE CASCADE OPERATIONS  
    # ========================================
    
    def delete_invoice_cascade(self, nfacture: int) -> Dict[str, Any]:
        """
        Delete an invoice and ALL related records
        Returns details of what was deleted
        """
        deleted_items = {
            'invoice': None,
            'payments': [],
            'retenu_records': [],
            'bank_transactions': [],
            'caisse_transactions': []
        }
        
        try:
            with self.get_connection() as conn:
                # Get invoice details
                cursor = conn.execute("SELECT nfacture, ttc FROM ventes WHERE nfacture = ?", (nfacture,))
                invoice = cursor.fetchone()
                
                if not invoice:
                    return {'error': f'Invoice {nfacture} not found'}
                
                deleted_items['invoice'] = {'nfacture': nfacture, 'ttc': invoice[1]}
                
                # Get all related records before deletion
                cursor = conn.execute("SELECT id, montant_paye FROM paiements_factures WHERE nfacture = ?", (nfacture,))
                payments = cursor.fetchall()
                deleted_items['payments'] = [{'id': p[0], 'montant': p[1]} for p in payments]
                
                cursor = conn.execute("SELECT id, retenu_amount FROM retenus WHERE nfacture = ?", (nfacture,))
                retenus = cursor.fetchall()
                deleted_items['retenu_records'] = [{'id': r[0], 'amount': r[1]} for r in retenus]
                
                cursor = conn.execute("SELECT id, montant FROM transactions_bancaires WHERE nfacture = ?", (nfacture,))
                bank_txs = cursor.fetchall()
                deleted_items['bank_transactions'] = [{'id': tx[0], 'montant': tx[1]} for tx in bank_txs]
                
                cursor = conn.execute("SELECT id, montant FROM caisse_transactions WHERE nfacture = ?", (nfacture,))
                caisse_txs = cursor.fetchall()
                deleted_items['caisse_transactions'] = [{'id': tx[0], 'montant': tx[1]} for tx in caisse_txs]
                
                # SOFT DELETE: Mark all records as deleted (Option 3 - preserve audit trail)
                now = datetime.now().timestamp()
                
                # Delete in correct order (children first) - using soft delete
                conn.execute("UPDATE retenus SET deleted = 1, deleted_at = ?, updated_at = ? WHERE nfacture = ?", (now, now, nfacture))
                conn.execute("UPDATE transactions_bancaires SET deleted = 1, deleted_at = ?, updated_at = ? WHERE nfacture = ?", (now, now, nfacture))
                conn.execute("UPDATE caisse_transactions SET deleted = 1, deleted_at = ?, updated_at = ? WHERE nfacture = ?", (now, now, nfacture))
                conn.execute("UPDATE paiements_factures SET deleted = 1, deleted_at = ?, updated_at = ? WHERE nfacture = ?", (now, now, nfacture))
                conn.execute("UPDATE ventes SET deleted = 1, deleted_at = ?, updated_at = ? WHERE nfacture = ?", (now, now, nfacture))
                
                conn.commit()
                
                print(f"[CASCADE] Deleted invoice {nfacture} and all related records:")
                print(f"  - Payments: {len(deleted_items['payments'])}")
                print(f"  - Retenu records: {len(deleted_items['retenu_records'])}")
                print(f"  - Bank transactions: {len(deleted_items['bank_transactions'])}")
                print(f"  - Caisse transactions: {len(deleted_items['caisse_transactions'])}")
                
                return deleted_items
                
        except Exception as e:
            print(f"[CASCADE] Error deleting invoice {nfacture}: {e}")
            return {'error': str(e)}

    # ========================================
    # ACHAT (PURCHASE) CASCADE OPERATIONS
    # ========================================

    def delete_achat_cascade(self, achat_id: int) -> Dict[str, Any]:
        """
        Delete an achat (purchase) and ALL related records (payments, retenus, bank/caisse decaissements)
        Returns details of what was deleted
        """
        deleted_items = {
            'achat': None,
            'payments': [],
            'retenu_records': [],
            'bank_transactions': [],
            'caisse_transactions': []
        }
        try:
            with self.get_connection() as conn:
                # Get achat details
                cursor = conn.execute("SELECT id, ttc, num_facture FROM achats WHERE id = ?", (achat_id,))
                achat = cursor.fetchone()
                if not achat:
                    return {'error': f'Achat {achat_id} not found'}
                deleted_items['achat'] = {'id': achat[0], 'ttc': achat[1], 'num_facture': achat[2]}

                # Collect related payments
                cursor = conn.execute("SELECT id, montant_paye FROM paiements_factures WHERE nfacture = ?", (achat_id,))
                payments = cursor.fetchall()
                deleted_items['payments'] = [{'id': p[0], 'montant': p[1]} for p in payments]

                # Collect retenus by matching nfacture, also try by num_facture if numeric
                cursor = conn.execute("SELECT id, retenu_amount FROM retenus WHERE nfacture = ?", (achat_id,))
                retenus = cursor.fetchall()
                # Try by num_facture as int if present
                try:
                    if achat[2]:
                        nf_int = int(achat[2])
                        cursor = conn.execute("SELECT id, retenu_amount FROM retenus WHERE nfacture = ?", (nf_int,))
                        retenus += cursor.fetchall()
                except Exception:
                    pass
                # Deduplicate retenu ids
                seen = set()
                retenus_unique = []
                for r in retenus:
                    if r[0] not in seen:
                        seen.add(r[0])
                        retenus_unique.append(r)
                deleted_items['retenu_records'] = [{'id': r[0], 'amount': r[1]} for r in retenus_unique]

                # Collect related bank decaissements
                cursor = conn.execute("""
                    SELECT id, montant FROM transactions_bancaires
                    WHERE nfacture = ? AND type_transaction = 'decaissement'
                """, (achat_id,))
                bank_txs = cursor.fetchall()
                deleted_items['bank_transactions'] = [{'id': tx[0], 'montant': tx[1]} for tx in bank_txs]

                # Collect related caisse decaissements
                cursor = conn.execute("""
                    SELECT id, montant FROM caisse_transactions
                    WHERE nfacture = ? AND type = 'decaissement'
                """, (achat_id,))
                caisse_txs = cursor.fetchall()
                deleted_items['caisse_transactions'] = [{'id': tx[0], 'montant': tx[1]} for tx in caisse_txs]

                # Delete children first
                conn.execute("DELETE FROM retenus WHERE nfacture = ?", (achat_id,))
                # Also delete retenus by num_facture int if applicable
                try:
                    if achat[2]:
                        nf_int = int(achat[2])
                        conn.execute("DELETE FROM retenus WHERE nfacture = ?", (nf_int,))
                except Exception:
                    pass
                conn.execute("DELETE FROM transactions_bancaires WHERE nfacture = ? AND type_transaction = 'decaissement'", (achat_id,))
                conn.execute("DELETE FROM caisse_transactions WHERE nfacture = ? AND type = 'decaissement'", (achat_id,))
                conn.execute("DELETE FROM paiements_factures WHERE nfacture = ?", (achat_id,))

                # Finally delete the achat itself
                conn.execute("DELETE FROM achats WHERE id = ?", (achat_id,))
                conn.commit()

                print(f"[CASCADE] Deleted achat {achat_id} and all related records:")
                print(f"  - Payments: {len(deleted_items['payments'])}")
                print(f"  - Retenu records: {len(deleted_items['retenu_records'])}")
                print(f"  - Bank transactions: {len(deleted_items['bank_transactions'])}")
                print(f"  - Caisse transactions: {len(deleted_items['caisse_transactions'])}")
                return deleted_items
        except Exception as e:
            print(f"[CASCADE] Error deleting achat {achat_id}: {e}")
            return {'error': str(e)}
    
    # ========================================
    # REVERSE CASCADE OPERATIONS
    # ========================================
    
    def sync_retenu_with_payment_notes(self, nfacture: int) -> Dict[str, Any]:
        """
        Synchronize retenu records with payment notes for an invoice.
        This ensures consistency when retenu records are modified independently.
        """
        sync_result = {
            'updated_payments': [],
            'created_retenu': None,
            'updated_retenu': None
        }
        
        try:
            with self.get_connection() as conn:
                # Get payment with retenu notes
                cursor = conn.execute("""
                    SELECT id, notes FROM paiements_factures 
                    WHERE nfacture = ? AND notes LIKE '%Retenu:%'
                """, (nfacture,))
                payment_with_retenu = cursor.fetchone()
                
                if payment_with_retenu:
                    payment_id, notes = payment_with_retenu
                    
                    # Extract retenu info from notes
                    import re
                    retenu_match = re.search(r'\[Retenu:\s*([\d.]+)%\]', notes)
                    if retenu_match:
                        retenu_percent = float(retenu_match.group(1))
                        
                        # Calculate retenu amount
                        cursor = conn.execute("SELECT ttc, timbre FROM ventes WHERE nfacture = ?", (nfacture,))
                        vente_data = cursor.fetchone()
                        if vente_data:
                            ttc, timbre = vente_data
                            retenu_base = ttc - (timbre or 0)
                            retenu_amount = retenu_base * retenu_percent / 100.0
                            
                            # Check if retenu record exists
                            cursor = conn.execute("SELECT id FROM retenus WHERE nfacture = ?", (nfacture,))
                            existing_retenu = cursor.fetchone()
                            
                            if existing_retenu:
                                # Update existing retenu record
                                conn.execute("""
                                    UPDATE retenus 
                                    SET retenu_percent = ?, retenu_amount = ?, updated_at = ?
                                    WHERE nfacture = ?
                                """, (retenu_percent, retenu_amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), nfacture))
                                sync_result['updated_retenu'] = existing_retenu[0]
                            else:
                                # Create retenu record
                                cursor = conn.execute("SELECT raison_sociale FROM ventes WHERE nfacture = ?", (nfacture,))
                                client_name = cursor.fetchone()[0] if cursor.fetchone() else ""
                                
                                cursor = conn.execute("""
                                    INSERT INTO retenus (date, client, nfacture, retenu_percent, retenu_amount, source, notes, created_at)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    datetime.now().strftime('%Y-%m-%d'),
                                    client_name,
                                    nfacture,
                                    retenu_percent,
                                    retenu_amount,
                                    'payment_sync',
                                    f'Synced from payment {payment_id}',
                                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                                ))
                                sync_result['created_retenu'] = cursor.lastrowid
                
                conn.commit()
                return sync_result
                
        except Exception as e:
            print(f"[CASCADE] Error syncing retenu with payment notes: {e}")
            return {'error': str(e)}
    
    def sync_payment_notes_with_retenu(self, nfacture: int) -> Dict[str, Any]:
        """
        Update payment notes when retenu records are modified.
        This ensures payment notes reflect current retenu percentage.
        """
        sync_result = {
            'updated_payments': []
        }
        
        try:
            with self.get_connection() as conn:
                # Get retenu records for this invoice
                cursor = conn.execute("""
                    SELECT retenu_percent FROM retenus 
                    WHERE nfacture = ? 
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (nfacture,))
                retenu_record = cursor.fetchone()
                
                if retenu_record:
                    retenu_percent = retenu_record[0]
                    
                    # Find payments that need notes update
                    cursor = conn.execute("""
                        SELECT id, notes FROM paiements_factures 
                        WHERE nfacture = ? AND (notes LIKE '%Retenu:%' OR notes = '')
                    """, (nfacture,))
                    payments_to_update = cursor.fetchall()
                    
                    for payment_id, current_notes in payments_to_update:
                        # Update or add retenu info to notes
                        import re
                        if '[Retenu:' in current_notes:
                            # Replace existing retenu info
                            new_notes = re.sub(r'\[Retenu:\s*[\d.]+%\]', f'[Retenu: {retenu_percent}%]', current_notes)
                        else:
                            # Add retenu info
                            new_notes = f'[Retenu: {retenu_percent}%] {current_notes}'.strip()
                        
                        conn.execute("""
                            UPDATE paiements_factures 
                            SET notes = ?, updated_at = ?
                            WHERE id = ?
                        """, (new_notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id))
                        
                        sync_result['updated_payments'].append(payment_id)
                
                conn.commit()
                return sync_result
                
        except Exception as e:
            print(f"[CASCADE] Error syncing payment notes with retenu: {e}")
            return {'error': str(e)}

    # ========================================
    # CALENDAR CASCADE OPERATIONS
    # ========================================
    
    def create_calendar_event_for_traite(self, payment_id: int, nfacture: int, echeance: str, client_name: str, montant: float) -> Dict[str, Any]:
        """
        Create a calendar event for a traite payment with echeance date
        Returns details of the created calendar event
        """
        try:
            with self.get_connection() as conn:
                # Create calendar event for traite echeance
                title = f"Echeance traite - Facture {nfacture}"
                description = f"""Echeance traite pour facture {nfacture}
Client: {client_name}
Montant: {montant} TND
Paiement ID: {payment_id}
Type: Traite a encaisser"""
                
                cursor = conn.execute("""
                    INSERT INTO calendar_events (title, date, category, description, done, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    title,
                    echeance,
                    'payment',
                    description,
                    0,  # Not done
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                ))
                
                calendar_event_id = cursor.lastrowid
                
                # Link the calendar event to the payment by updating payment notes
                cursor = conn.execute("""
                    SELECT notes FROM paiements_factures WHERE id = ?
                """, (payment_id,))
                current_notes = cursor.fetchone()[0] or ""
                
                # Add calendar event reference to payment notes
                calendar_ref = f"[Calendar: {calendar_event_id}]"
                if calendar_ref not in current_notes:
                    updated_notes = f"{current_notes} {calendar_ref}".strip()
                    conn.execute("""
                        UPDATE paiements_factures 
                        SET notes = ?, updated_at = ?
                        WHERE id = ?
                    """, (updated_notes, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), payment_id))
                
                conn.commit()
                
                print(f"[CASCADE] Created calendar event {calendar_event_id} for traite payment {payment_id}")
                return {
                    'calendar_event_id': calendar_event_id,
                    'title': title,
                    'date': echeance,
                    'payment_id': payment_id,
                    'nfacture': nfacture
                }
                
        except Exception as e:
            print(f"[CASCADE] Error creating calendar event for traite payment {payment_id}: {e}")
            return {'error': str(e)}
    
    def update_calendar_event_for_traite(self, payment_id: int, old_echeance: str = None, new_echeance: str = None, 
                                       new_montant: float = None, new_client: str = None) -> Dict[str, Any]:
        """
        Update calendar event when traite payment is modified
        Returns details of the updated calendar event
        """
        try:
            with self.get_connection() as conn:
                # Find calendar event linked to this payment
                cursor = conn.execute("""
                    SELECT notes FROM paiements_factures WHERE id = ?
                """, (payment_id,))
                payment_notes = cursor.fetchone()
                
                if not payment_notes or not payment_notes[0]:
                    return {'error': f'No notes found for payment {payment_id}'}
                
                # Extract calendar event ID from notes
                import re
                calendar_match = re.search(r'\[Calendar:\s*(\d+)\]', payment_notes[0])
                if not calendar_match:
                    return {'error': f'No calendar event reference found in payment {payment_id}'}
                
                calendar_event_id = int(calendar_match.group(1))
                
                # Get current calendar event
                cursor = conn.execute("""
                    SELECT title, date, description FROM calendar_events WHERE id = ?
                """, (calendar_event_id,))
                current_event = cursor.fetchone()
                
                if not current_event:
                    return {'error': f'Calendar event {calendar_event_id} not found'}
                
                current_title, current_date, current_description = current_event
                
                # Update calendar event
                updates = []
                values = []
                
                if new_echeance and new_echeance != current_date:
                    updates.append('date = ?')
                    values.append(new_echeance)
                
                # Update description if montant or client changed
                if new_montant or new_client:
                    # Get current payment info
                    cursor = conn.execute("""
                        SELECT p.nfacture, v.raison_sociale, p.montant_paye
                        FROM paiements_factures p
                        JOIN ventes v ON p.nfacture = v.nfacture
                        WHERE p.id = ?
                    """, (payment_id,))
                    payment_info = cursor.fetchone()
                    
                    if payment_info:
                        nfacture, client_name, montant = payment_info
                        
                        # Use new values if provided, otherwise keep current
                        final_montant = new_montant or montant
                        final_client = new_client or client_name
                        
                        new_description = f"""Echeance traite pour facture {nfacture}
Client: {final_client}
Montant: {final_montant} TND
Paiement ID: {payment_id}
Type: Traite a encaisser"""
                        
                        updates.append('description = ?')
                        values.append(new_description)
                
                if updates:
                    updates.append('updated_at = ?')
                    values.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
                    values.append(calendar_event_id)
                    
                    conn.execute(f"""
                        UPDATE calendar_events 
                        SET {', '.join(updates)} 
                        WHERE id = ?
                    """, values)
                    
                    conn.commit()
                    
                    print(f"[CASCADE] Updated calendar event {calendar_event_id} for traite payment {payment_id}")
                    return {
                        'calendar_event_id': calendar_event_id,
                        'updated_fields': [u.split(' = ')[0] for u in updates[:-1]]
                    }
                else:
                    return {'message': 'No updates needed for calendar event'}
                
        except Exception as e:
            print(f"[CASCADE] Error updating calendar event for traite payment {payment_id}: {e}")
            return {'error': str(e)}
    
    def delete_calendar_event_for_traite(self, payment_id: int) -> Dict[str, Any]:
        """
        Delete calendar event when traite payment is deleted
        Returns details of the deleted calendar event
        """
        try:
            with self.get_connection() as conn:
                # Find calendar event linked to this payment
                cursor = conn.execute("""
                    SELECT notes FROM paiements_factures WHERE id = ?
                """, (payment_id,))
                payment_notes = cursor.fetchone()
                
                if not payment_notes or not payment_notes[0]:
                    return {'message': f'No notes found for payment {payment_id}'}
                
                # Extract calendar event ID from notes
                import re
                calendar_match = re.search(r'\[Calendar:\s*(\d+)\]', payment_notes[0])
                if not calendar_match:
                    return {'message': f'No calendar event reference found in payment {payment_id}'}
                
                calendar_event_id = int(calendar_match.group(1))
                
                # Get event details before deletion
                cursor = conn.execute("""
                    SELECT title, date, description FROM calendar_events WHERE id = ?
                """, (calendar_event_id,))
                event_details = cursor.fetchone()
                
                if event_details:
                    # Delete the calendar event
                    conn.execute("DELETE FROM calendar_events WHERE id = ?", (calendar_event_id,))
                    conn.commit()
                    
                    print(f"[CASCADE] Deleted calendar event {calendar_event_id} for traite payment {payment_id}")
                    return {
                        'deleted_event_id': calendar_event_id,
                        'title': event_details[0],
                        'date': event_details[1],
                        'payment_id': payment_id
                    }
                else:
                    return {'message': f'Calendar event {calendar_event_id} not found'}
                
        except Exception as e:
            print(f"[CASCADE] Error deleting calendar event for traite payment {payment_id}: {e}")
            return {'error': str(e)}
    
    def create_missing_calendar_events_for_traite_payments(self) -> Dict[str, Any]:
        """
        Create calendar events for all existing traite payments that don't have them
        Returns summary of created events
        """
        created_events = []
        skipped_payments = []
        
        try:
            with self.get_connection() as conn:
                # Find traite payments with echeance that don't have calendar events
                cursor = conn.execute("""
                    SELECT p.id, p.nfacture, p.montant_paye, p.echeance, p.notes, 
                           COALESCE(v.raison_sociale, 'Unknown Client') as client_name
                    FROM paiements_factures p
                    LEFT JOIN ventes v ON p.nfacture = v.nfacture
                    WHERE p.mode_paiement = 'traite' 
                    AND p.echeance IS NOT NULL 
                    AND p.echeance != ''
                    AND (p.notes IS NULL OR INSTR(p.notes, '[Calendar:') = 0)
                """)
                traite_payments = cursor.fetchall()
                
                print(f"[CASCADE] Found {len(traite_payments)} traite payments without calendar events")
                
                for payment in traite_payments:
                    payment_id, nfacture, montant, echeance, notes, client_name = payment
                    
                    # Check if a calendar event already exists for this echeance date and invoice
                    cursor = conn.execute("""
                        SELECT id FROM calendar_events 
                        WHERE date = ? AND description LIKE ?
                    """, (echeance, f"%{nfacture}%"))
                    existing_event = cursor.fetchone()
                    
                    if existing_event:
                        skipped_payments.append({
                            'payment_id': payment_id,
                            'nfacture': nfacture,
                            'reason': f'Calendar event {existing_event[0]} already exists'
                        })
                    else:
                        # Create calendar event
                        result = self.create_calendar_event_for_traite(
                            payment_id, nfacture, echeance, client_name, montant
                        )
                        if 'error' not in result:
                            created_events.append(result)
                        else:
                            skipped_payments.append({
                                'payment_id': payment_id,
                                'nfacture': nfacture,
                                'reason': result['error']
                            })
                
                return {
                    'created_events': created_events,
                    'skipped_payments': skipped_payments,
                    'summary': f'Created {len(created_events)} calendar events, skipped {len(skipped_payments)} payments'
                }
                
        except Exception as e:
            print(f"[CASCADE] Error creating missing calendar events: {e}")
            return {'error': str(e)}

    # ========================================
    # CLEANUP OPERATIONS
    # ========================================
    
    def cleanup_orphaned_records(self) -> Dict[str, int]:
        """Clean up all orphaned records across the system"""
        cleanup_stats = {
            'orphaned_payments': 0,
            'orphaned_retenus': 0,
            'orphaned_bank_transactions': 0,
            'orphaned_caisse_transactions': 0
        }
        
        try:
            with self.get_connection() as conn:
                # Clean orphaned payments (no matching invoice)
                cursor = conn.execute("""
                    DELETE FROM paiements_factures 
                    WHERE nfacture NOT IN (SELECT nfacture FROM ventes)
                      AND nfacture NOT IN (SELECT id FROM achats)
                      AND (notes IS NULL OR notes NOT LIKE '%MULTI-%')
                """)
                cleanup_stats['orphaned_payments'] = cursor.rowcount
                
                # Clean orphaned retenu records
                cursor = conn.execute("""
                    DELETE FROM retenus 
                    WHERE nfacture NOT IN (SELECT nfacture FROM ventes)
                      AND nfacture NOT IN (SELECT id FROM achats)
                """)
                cleanup_stats['orphaned_retenus'] = cursor.rowcount
                
                # Clean orphaned bank transactions
                cursor = conn.execute("""
                    DELETE FROM transactions_bancaires 
                    WHERE nfacture IS NOT NULL 
                      AND description NOT LIKE '%MULTI-PAIEMENT%'
                      AND (nfacture NOT IN (SELECT nfacture FROM ventes)
                           AND nfacture NOT IN (SELECT id FROM achats))
                """)
                cleanup_stats['orphaned_bank_transactions'] = cursor.rowcount
                
                # Clean orphaned caisse transactions
                cursor = conn.execute("""
                    DELETE FROM caisse_transactions 
                    WHERE nfacture IS NOT NULL 
                      AND description NOT LIKE '%Paiement multiple%'
                      AND (nfacture NOT IN (SELECT nfacture FROM ventes)
                           AND nfacture NOT IN (SELECT id FROM achats))
                """)
                cleanup_stats['orphaned_caisse_transactions'] = cursor.rowcount
                
                conn.commit()
                
                print("[CASCADE] Cleanup completed:")
                for key, count in cleanup_stats.items():
                    if count > 0:
                        print(f"  - {key}: {count} records removed")
                
                return cleanup_stats
                
        except Exception as e:
            print(f"[CASCADE] Error during cleanup: {e}")
            return {'error': str(e)}
    
    # ========================================
    # VALIDATION OPERATIONS
    # ========================================
    
    def validate_data_integrity(self) -> Dict[str, Any]:
        """Check data integrity across all financial modules"""
        issues = {
            'orphaned_payments': [],
            'orphaned_retenus': [],
            'orphaned_bank_transactions': [],
            'orphaned_caisse_transactions': [],
            'missing_retenu_for_payment': [],
            'missing_bank_tx_for_payment': []
        }
        
        try:
            with self.get_connection() as conn:
                # Find orphaned payments
                cursor = conn.execute("""
                    SELECT p.id, p.nfacture, p.montant_paye 
                    FROM paiements_factures p 
                    LEFT JOIN ventes v ON p.nfacture = v.nfacture
                    LEFT JOIN achats a ON p.nfacture = a.id
                    WHERE v.nfacture IS NULL AND a.id IS NULL
                """)
                issues['orphaned_payments'] = [
                    {'id': row[0], 'nfacture': row[1], 'montant': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                # Find orphaned retenu records
                cursor = conn.execute("""
                    SELECT r.id, r.nfacture, r.retenu_amount 
                    FROM retenus r 
                    LEFT JOIN ventes v ON r.nfacture = v.nfacture
                    LEFT JOIN achats a ON r.nfacture = a.id
                    WHERE v.nfacture IS NULL AND a.id IS NULL
                """)
                issues['orphaned_retenus'] = [
                    {'id': row[0], 'nfacture': row[1], 'amount': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                # Find payments with retenu notes but no retenu record
                cursor = conn.execute("""
                    SELECT p.id, p.nfacture, p.notes
                    FROM paiements_factures p
                    WHERE p.notes LIKE '%Retenu:%'
                    AND NOT EXISTS (SELECT 1 FROM retenus r WHERE r.nfacture = p.nfacture)
                """)
                issues['missing_retenu_for_payment'] = [
                    {'payment_id': row[0], 'nfacture': row[1], 'notes': row[2]} 
                    for row in cursor.fetchall()
                ]
                
                # Find bank payments with no bank transaction
                cursor = conn.execute("""
                    SELECT p.id, p.nfacture, p.montant_paye, p.banque_id
                    FROM paiements_factures p
                    WHERE p.methode_paiement = 'banque' AND p.banque_id IS NOT NULL
                    AND NOT EXISTS (
                        SELECT 1 FROM transactions_bancaires t 
                        WHERE (
                            -- Single payments link directly by nfacture
                            t.nfacture = p.nfacture 
                            OR 
                            -- Multiple payments: look for marker and same date
                            (t.description LIKE '%MULTI-PAIEMENT%' AND t.date_transaction = p.date_paiement)
                        )
                        AND t.banque_id = p.banque_id
                    )
                """)
                issues['missing_bank_tx_for_payment'] = [
                    {'payment_id': row[0], 'nfacture': row[1], 'montant': row[2], 'banque_id': row[3]} 
                    for row in cursor.fetchall()
                ]
                
                return issues
                
        except Exception as e:
            print(f"[CASCADE] Error validating data integrity: {e}")
            return {'error': str(e)}


# Global instance for easy access
cascade_manager = CascadeManager()