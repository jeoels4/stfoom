"""
Sales Service
============
Business logic service for sales (ventes) management.
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..data.vente_repository import VenteRepository

class SalesService:
    """Service for sales management business logic."""
    
    def __init__(self):
        self.vente_repo = VenteRepository()
    
    def create_sale(self, client_nom: str, produit: str, quantite: float, 
                   prix_unitaire: float, vendeur: str = "", **kwargs) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new sale.
        
        Args:
            client_nom: Client name
            produit: Product name
            quantite: Quantity
            prix_unitaire: Unit price
            vendeur: Salesperson
            **kwargs: Additional sale fields
            
        Returns:
            Tuple of (success, message, sale_id)
        """
        # Validate business rules
        if quantite <= 0:
            return False, "Quantity must be greater than 0", None
        
        if prix_unitaire <= 0:
            return False, "Unit price must be greater than 0", None
        
        # Calculate total
        total = quantite * prix_unitaire
        
        # Create the sale
        sale_id = self.vente_repo.create_vente(
            client_nom=client_nom,
            produit=produit,
            quantite=quantite,
            prix_unitaire=prix_unitaire,
            vendeur=vendeur,
            **kwargs
        )
        
        if sale_id:
            # ✅ SYNC INTEGRATION: Track the creation for sync system
            try:
                from .sync_service import SyncService
                from datetime import datetime
                
                sync_service = SyncService()
                
                creation_data = {
                    "created_at": datetime.now().isoformat(),
                    "client_nom": client_nom,
                    "produit": produit,
                    "quantite": quantite,
                    "prix_unitaire": prix_unitaire,
                    "total": total,
                    "vendeur": vendeur,
                    "created_by": "sales_service"
                }
                sync_service.add_sync_change("ventes", str(sale_id), creation_data, "insert")
                print(f"[SYNC] Tracked creation of sale {sale_id} for sync")
            except Exception as sync_error:
                print(f"[SYNC] Warning - failed to track creation: {sync_error}")
                # Continue even if sync tracking fails
            
            return True, f"Sale created successfully with ID: {sale_id}", sale_id
        else:
            return False, "Failed to create sale", None
    
    def update_sale_status(self, sale_id: int, new_status: str, updated_by: str = "") -> Tuple[bool, str]:
        """Update the status of a sale."""
        valid_statuses = ["en_cours", "confirmee", "livree", "payee", "annulee"]
        
        if new_status not in valid_statuses:
            return False, f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        
        # Get current sale to check business rules
        sale = self.vente_repo.get_by_id(sale_id)
        if not sale:
            return False, "Sale not found"
        
        current_status = sale.get("statut", "en_cours")
        
        # Business rule: Can't modify paid or cancelled sales
        if current_status in ["payee", "annulee"] and current_status != new_status:
            return False, f"Cannot modify sale with status '{current_status}'"
        
        # Update the status
        success = self.vente_repo.update_vente_status(sale_id, new_status)
        
        if success:
            # ✅ SYNC INTEGRATION: Track the status update for sync system
            try:
                from .sync_service import SyncService
                from datetime import datetime
                
                sync_service = SyncService()
                
                update_data = {
                    "updated_at": datetime.now().isoformat(),
                    "old_status": current_status,
                    "new_status": new_status,
                    "updated_by": updated_by or "system",
                    "operation": "status_update"
                }
                sync_service.add_sync_change("ventes", str(sale_id), update_data, "update")
                print(f"[SYNC] Tracked status update of sale {sale_id} for sync")
            except Exception as sync_error:
                print(f"[SYNC] Warning - failed to track status update: {sync_error}")
                # Continue even if sync tracking fails
            
            # Add audit note if updated_by is provided
            if updated_by:
                notes = sale.get("notes", "")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
                audit_note = f"\n[{timestamp}] Status changed to '{new_status}' by {updated_by}"
                
                self.vente_repo.update(sale_id, {"notes": notes + audit_note})
            
            return True, f"Sale status updated to '{new_status}'"
        else:
            return False, "Failed to update sale status"
    
    def get_sales_by_client(self, client_nom: str) -> List[Dict[str, Any]]:
        """Get all sales for a specific client."""
        return self.vente_repo.get_ventes_by_client(client_nom)
    
    def get_sales_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get sales within a date range."""
        return self.vente_repo.get_ventes_by_date_range(start_date, end_date)
    
    def get_sales_by_product(self, produit: str) -> List[Dict[str, Any]]:
        """Get all sales for a specific product."""
        return self.vente_repo.get_ventes_by_product(produit)
    
    def get_monthly_sales_report(self, year: int, month: int) -> Dict[str, Any]:
        """Get comprehensive monthly sales report."""
        summary = self.vente_repo.get_monthly_sales_summary(year, month)
        
        # Add additional business insights
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        sales = self.get_sales_by_date_range(start_date, end_date)
        
        # Product analysis
        product_analysis = {}
        for sale in sales:
            product = sale["produit"]
            if product not in product_analysis:
                product_analysis[product] = {
                    "total_quantity": 0.0,
                    "total_amount": 0.0,
                    "sale_count": 0
                }
            
            product_analysis[product]["total_quantity"] += sale["quantite"]
            product_analysis[product]["total_amount"] += sale["total"]
            product_analysis[product]["sale_count"] += 1
        
        # Client analysis
        client_analysis = {}
        for sale in sales:
            client = sale["client_nom"]
            if client not in client_analysis:
                client_analysis[client] = {
                    "total_amount": 0.0,
                    "sale_count": 0
                }
            
            client_analysis[client]["total_amount"] += sale["total"]
            client_analysis[client]["sale_count"] += 1
        
        # Status analysis
        status_counts = {}
        for sale in sales:
            status = sale.get("statut", "en_cours")
            status_counts[status] = status_counts.get(status, 0) + 1
        
        summary.update({
            "product_analysis": product_analysis,
            "client_analysis": client_analysis,
            "status_breakdown": status_counts,
            "period": f"{year}-{month:02d}"
        })
        
        return summary
    
    def search_sales(self, search_term: str) -> List[Dict[str, Any]]:
        """Search sales by various criteria."""
        return self.vente_repo.search_ventes(search_term)
    
    def get_pending_sales(self) -> List[Dict[str, Any]]:
        """Get all pending/in-progress sales."""
        return self.vente_repo.get_pending_ventes()
    
    def calculate_sale_totals(self, sales: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate totals for a list of sales."""
        if not sales:
            return {
                "total_sales": 0,
                "total_amount": 0.0,
                "total_quantity": 0.0,
                "average_sale": 0.0
            }
        
        total_amount = sum(sale["total"] for sale in sales)
        total_quantity = sum(sale["quantite"] for sale in sales)
        
        return {
            "total_sales": len(sales),
            "total_amount": total_amount,
            "total_quantity": total_quantity,
            "average_sale": total_amount / len(sales) if sales else 0.0
        }
    
    def get_top_clients(self, limit: int = 10, period_days: int = 30) -> List[Dict[str, Any]]:
        """Get top clients by sales amount in specified period."""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        sales = self.get_sales_by_date_range(start_date, end_date)
        
        client_totals = {}
        for sale in sales:
            client = sale["client_nom"]
            if client not in client_totals:
                client_totals[client] = {
                    "client_nom": client,
                    "total_amount": 0.0,
                    "sale_count": 0,
                    "total_quantity": 0.0
                }
            
            client_totals[client]["total_amount"] += sale["total"]
            client_totals[client]["sale_count"] += 1
            client_totals[client]["total_quantity"] += sale["quantite"]
        
        # Sort by total amount and limit
        top_clients = sorted(client_totals.values(), 
                           key=lambda x: x["total_amount"], 
                           reverse=True)[:limit]
        
        return top_clients
    
    def get_top_products(self, limit: int = 10, period_days: int = 30) -> List[Dict[str, Any]]:
        """Get top products by sales amount in specified period."""
        end_date = date.today()
        start_date = end_date - timedelta(days=period_days)
        
        sales = self.get_sales_by_date_range(start_date, end_date)
        
        product_totals = {}
        for sale in sales:
            product = sale["produit"]
            if product not in product_totals:
                product_totals[product] = {
                    "produit": product,
                    "total_amount": 0.0,
                    "sale_count": 0,
                    "total_quantity": 0.0
                }
            
            product_totals[product]["total_amount"] += sale["total"]
            product_totals[product]["sale_count"] += 1
            product_totals[product]["total_quantity"] += sale["quantite"]
        
        # Sort by total amount and limit
        top_products = sorted(product_totals.values(), 
                            key=lambda x: x["total_amount"], 
                            reverse=True)[:limit]
        
        return top_products
    
    def validate_sale_data(self, sale_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate sale data and return any errors."""
        errors = []
        
        # Required fields
        required_fields = ["client_nom", "produit", "quantite", "prix_unitaire"]
        for field in required_fields:
            if field not in sale_data or not sale_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Numeric validations
        try:
            quantite = float(sale_data.get("quantite", 0))
            if quantite <= 0:
                errors.append("Quantity must be greater than 0")
        except (ValueError, TypeError):
            errors.append("Invalid quantity format")
        
        try:
            prix_unitaire = float(sale_data.get("prix_unitaire", 0))
            if prix_unitaire <= 0:
                errors.append("Unit price must be greater than 0")
        except (ValueError, TypeError):
            errors.append("Invalid unit price format")
        
        # Date validation
        if "date_vente" in sale_data and sale_data["date_vente"]:
            try:
                if isinstance(sale_data["date_vente"], str):
                    datetime.strptime(sale_data["date_vente"], "%Y-%m-%d")
            except ValueError:
                errors.append("Invalid date format (use YYYY-MM-DD)")
        
        return len(errors) == 0, errors
    
    def update_sale(self, sale_id: int, update_data: Dict[str, Any], updated_by: str = "") -> Tuple[bool, str]:
        """Update sale information."""
        # Get current sale
        sale = self.vente_repo.get_by_id(sale_id)
        if not sale:
            return False, "Sale not found"
        
        # Check if sale can be modified
        current_status = sale.get("statut", "en_cours")
        if current_status in ["payee", "annulee"]:
            return False, f"Cannot modify sale with status '{current_status}'"
        
        # Validate update data
        is_valid, errors = self.validate_sale_data({**sale, **update_data})
        if not is_valid:
            return False, f"Validation errors: {'; '.join(errors)}"
        
        # Recalculate total if quantity or price changed
        if "quantite" in update_data or "prix_unitaire" in update_data:
            quantite = float(update_data.get("quantite", sale["quantite"]))
            prix_unitaire = float(update_data.get("prix_unitaire", sale["prix_unitaire"]))
            update_data["total"] = quantite * prix_unitaire
        
        # Add audit trail
        if updated_by:
            notes = sale.get("notes", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_note = f"\n[{timestamp}] Updated by {updated_by}"
            update_data["notes"] = notes + audit_note
        
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Update the sale
        success = self.vente_repo.update(sale_id, update_data)
        
        if success:
            # ✅ SYNC INTEGRATION: Track the update for sync system
            try:
                from .sync_service import SyncService
                from datetime import datetime
                
                sync_service = SyncService()
                
                sync_data = {
                    "updated_at": datetime.now().isoformat(),
                    "updated_fields": list(update_data.keys()),
                    "updated_by": updated_by or "system",
                    "operation": "full_update"
                }
                # Include the actual updated values (but be careful not to include sensitive data)
                safe_fields = ["quantite", "prix_unitaire", "total", "client_nom", "produit", "statut"]
                for field in safe_fields:
                    if field in update_data:
                        sync_data[f"new_{field}"] = update_data[field]
                
                sync_service.add_sync_change("ventes", str(sale_id), sync_data, "update")
                print(f"[SYNC] Tracked update of sale {sale_id} for sync")
            except Exception as sync_error:
                print(f"[SYNC] Warning - failed to track update: {sync_error}")
                # Continue even if sync tracking fails
            
            return True, "Sale updated successfully"
        else:
            return False, "Failed to update sale"

    # ✅ PHASE 2B MIGRATION: Compatibility methods for vente_page
    def get_all_sales(self) -> List[Dict[str, Any]]:
        """
        Get all sales records (compatibility method for vente_page).
        Equivalent to vente.fetch_all_ventes()
        
        Returns data in the exact format expected by VentePage UI.
        """
        # Use the exact same SQL query as the original vente.fetch_all_ventes()
        try:
            # Use VenteRepository instead of secure_database to avoid authentication issues
            rows = self.vente_repo.get_all()

            out = []
            for row in rows:
                d = dict(row)
                
                # Calculate nfacture_seq (same logic as original)
                try:
                    n_int = int(d["nfacture"])
                    d["nfacture_seq"] = f"{int(str(n_int)[4:]):04d}"
                except Exception:
                    d["nfacture_seq"] = "----"

                # ✅ FIX: Handle client data properly - get from clients table if raison_sociale is empty
                code_client = d.get('code_client', '')
                raison_sociale = d.get('raison_sociale', '')
                
                # If raison_sociale is empty, try to get it from clients table
                if not raison_sociale or raison_sociale.strip() == '':
                    try:
                        # Query the clients table to get the actual client name
                        import sqlite3
                        from app.core.path_manager import get_db_path
                        conn = sqlite3.connect(get_db_path())
                        conn.row_factory = sqlite3.Row
                        cursor = conn.cursor()
                        cursor.execute("SELECT raison_sociale FROM clients WHERE code_client = ?", (code_client,))
                        client_row = cursor.fetchone()
                        if client_row:
                            raison_sociale = dict(client_row)['raison_sociale']
                        conn.close()
                    except Exception as e:
                        print(f"[SALES_SERVICE] Could not fetch client name for {code_client}: {e}")
                        raison_sociale = "Client Inconnu"
                
                # Ensure code_client is properly formatted as integer (remove .0 suffix)
                if isinstance(code_client, float) and code_client.is_integer():
                    code_client = int(code_client)
                
                d["client"] = f"{code_client} – {raison_sociale}"
                
                # Map date field (same logic as original)
                d["date"] = d.get("date_facture", "")
                
                # ✅ FIX: Handle NULL/None values in amounts properly
                d["mt_ht"] = (
                    float(d.get("mt_ht_p001") or 0)
                    + float(d.get("mt_ht_p002") or 0)
                    + float(d.get("mt_ht_p003") or 0)
                )
                
                # ✅ FIX: Ensure all numeric fields have proper values (not None)
                d["transport"] = float(d.get("transport_p004") or 0)
                d["fodec"] = float(d.get("fodec") or 0)
                d["tva19"] = float(d.get("tva19") or 0)
                d["tva7"] = float(d.get("tva7") or 0)
                d["timbre"] = float(d.get("timbre") or 0)
                d["ttc"] = float(d.get("ttc") or 0)

                out.append(d)
            
            return out
            
        except Exception as e:
            print(f"[SALES_SERVICE] Error in get_all_sales: {e}")
            import traceback
            traceback.print_exc()
            # Fallback to empty list if query fails
            return []
    
    def delete_sale_by_invoice(self, nfacture) -> bool:
        """
        Delete a sale by invoice number AND ALL related records using cascade manager.
        This ensures payments, retenu, bank transactions, and caisse records are also deleted.
        
        Args:
            nfacture: Invoice number (can be int or str)
            
        Returns:
            bool: True if deletion successful
        """
        try:
            # Convert nfacture to int for cascade operations
            nfacture_int = int(nfacture) if isinstance(nfacture, str) else nfacture
            
            print(f"[SALES SERVICE] Attempting to delete invoice {nfacture_int} with full cascade")
            
            # Use cascade manager for complete deletion
            from app.stfoom.services.cascade_manager import cascade_manager
            result = cascade_manager.delete_invoice_cascade(nfacture_int)
            
            if 'error' in result:
                print(f"[SALES SERVICE] Cascade deletion failed: {result['error']}")
                return False
            
            print(f"[SALES SERVICE] Successfully deleted invoice {nfacture_int} and all related records:")
            print(f"  - Payments: {len(result.get('payments', []))}")
            print(f"  - Retenu records: {len(result.get('retenu_records', []))}")
            print(f"  - Bank transactions: {len(result.get('bank_transactions', []))}")
            print(f"  - Caisse transactions: {len(result.get('caisse_transactions', []))}")
            
            # ✅ SYNC INTEGRATION: Track the deletion for sync system
            try:
                from .sync_service import SyncService
                from datetime import datetime
                
                sync_service = SyncService()
                
                # Track the main deletion with details of related deletions
                deletion_data = {
                    "deleted_at": datetime.now().isoformat(),
                    "deleted_by": "cascade_operation",
                    "nfacture": nfacture_int,
                    "cascade_deleted": {
                        "payments": len(result.get('payments', [])),
                        "retenu_records": len(result.get('retenu_records', [])),
                        "bank_transactions": len(result.get('bank_transactions', [])),
                        "caisse_transactions": len(result.get('caisse_transactions', []))
                    }
                }
                sync_service.add_sync_change("ventes", str(nfacture_int), deletion_data, "delete")
                print(f"[SYNC] Tracked cascade deletion of invoice {nfacture_int} for sync")
            except Exception as sync_error:
                print(f"[SYNC] Warning - failed to track deletion: {sync_error}")
                # Continue even if sync tracking fails
            
            return True
            
        except Exception as e:
            print(f"[SALES SERVICE] Error during cascade deletion of invoice {nfacture}: {e}")
            
            # Fallback to original logic if cascade fails
            print(f"[SALES SERVICE] Falling back to original deletion logic...")
            return self._delete_sale_by_invoice_fallback(nfacture)
    
    def _delete_sale_by_invoice_fallback(self, nfacture) -> bool:
        """
        Original delete logic as fallback (without cascades).
        This is kept for compatibility if cascade operations fail.
        """
        try:
            # Convert nfacture to both int and string for comparison
            nfacture_int = int(nfacture) if isinstance(nfacture, str) else nfacture
            nfacture_str = str(nfacture)
            
            print(f"[SALES SERVICE] Attempting to delete sale with invoice: {nfacture} (int: {nfacture_int}, str: {nfacture_str})")
            
            # Find the sale by invoice number
            all_sales = self.vente_repo.get_all()
            target_sale = None
            
            print(f"[SALES SERVICE] Searching through {len(all_sales)} sales records")
            
            for i, sale in enumerate(all_sales):
                # Debug: print first few sales to understand structure
                if i < 3:
                    print(f"[SALES SERVICE] Sale {i}: {sale}")
                
                # Try multiple comparison strategies
                nfacture_seq = sale.get('nfacture_seq')
                nfacture_field = sale.get('nfacture')
                
                # Convert sale invoice fields for comparison
                if nfacture_seq is not None:
                    try:
                        nfacture_seq_int = int(nfacture_seq)
                        nfacture_seq_str = str(nfacture_seq)
                        if nfacture_seq_int == nfacture_int or nfacture_seq_str == nfacture_str:
                            target_sale = sale
                            print(f"[SALES SERVICE] Found sale by nfacture_seq: {nfacture_seq}")
                            break
                    except (ValueError, TypeError):
                        pass
                
                if nfacture_field is not None:
                    try:
                        nfacture_field_int = int(nfacture_field)
                        nfacture_field_str = str(nfacture_field)
                        if nfacture_field_int == nfacture_int or nfacture_field_str == nfacture_str:
                            target_sale = sale
                            print(f"[SALES SERVICE] Found sale by nfacture: {nfacture_field}")
                            break
                    except (ValueError, TypeError):
                        pass
            
            if not target_sale:
                print(f"[SALES SERVICE] No sale found with invoice number: {nfacture}")
                return False
            
            # Check if the sale has an ID
            sale_id = target_sale.get('id')
            if sale_id is None:
                print(f"[SALES SERVICE] Sale found but missing 'id' field: {target_sale}")
                # For vente table, nfacture is likely the primary key
                nfacture_val = target_sale.get('nfacture')
                if nfacture_val is not None:
                    print(f"[SALES SERVICE] Using nfacture as ID for deletion: {nfacture_val}")
                    # Use nfacture as the ID and specify the column name
                    success = self.vente_repo.delete(nfacture_val, id_column="nfacture")
                    
                    if success:
                        print(f"[SALES SERVICE] Successfully deleted sale with invoice {nfacture}")
                        
                        # ✅ SYNC INTEGRATION: Track the deletion for sync system (fallback path)
                        try:
                            from .sync_service import SyncService
                            from datetime import datetime
                            
                            sync_service = SyncService()
                            
                            deletion_data = {
                                "deleted_at": datetime.now().isoformat(),
                                "deleted_by": "fallback_operation",
                                "nfacture": nfacture_val,
                                "fallback": True
                            }
                            sync_service.add_sync_change("ventes", str(nfacture_val), deletion_data, "delete")
                            print(f"[SYNC] Tracked fallback deletion of invoice {nfacture_val} for sync")
                        except Exception as sync_error:
                            print(f"[SYNC] Warning - failed to track fallback deletion: {sync_error}")
                            # Continue even if sync tracking fails
                    else:
                        print(f"[SALES SERVICE] Failed to delete sale with invoice {nfacture}")
                    
                    return success
                else:
                    print(f"[SALES SERVICE] Cannot delete sale - no valid ID or nfacture found")
                    return False
            
            print(f"[SALES SERVICE] Attempting to delete sale with ID: {sale_id}")
            
            # Delete the sale using standard ID
            success = self.vente_repo.delete(sale_id)
            
            if success:
                print(f"[SALES SERVICE] Successfully deleted sale with invoice {nfacture}")
                
                # ✅ SYNC INTEGRATION: Track the deletion for sync system (fallback path with ID)
                try:
                    from .sync_service import SyncService
                    from datetime import datetime
                    
                    sync_service = SyncService()
                    
                    deletion_data = {
                        "deleted_at": datetime.now().isoformat(),
                        "deleted_by": "fallback_id_operation",
                        "nfacture": nfacture_int,
                        "sale_id": sale_id,
                        "fallback": True
                    }
                    sync_service.add_sync_change("ventes", str(nfacture_int), deletion_data, "delete")
                    print(f"[SYNC] Tracked fallback ID deletion of invoice {nfacture} for sync")
                except Exception as sync_error:
                    print(f"[SYNC] Warning - failed to track fallback ID deletion: {sync_error}")
                    # Continue even if sync tracking fails
            else:
                print(f"[SALES SERVICE] Failed to delete sale with invoice {nfacture}")
            
            return success
            
        except Exception as e:
            print(f"[SALES SERVICE] Error in delete_sale_by_invoice: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def regenerate_invoice(self, nfacture: str, output_path: str = None) -> Optional[str]:
        """
        Regenerate an invoice (compatibility method for vente_page).
        Equivalent to vente.regenerate_invoice(...)
        
        Args:
            nfacture: Invoice number
            output_path: Optional output path for invoice
            
        Returns:
            Optional[str]: Path to generated invoice or None if failed
        """
        # Find the sale by invoice number
        all_sales = self.vente_repo.get_all()
        target_sale = None
        
        for sale in all_sales:
            if sale.get('nfacture_seq') == nfacture or sale.get('nfacture') == nfacture:
                target_sale = sale
                break
        
        if not target_sale:
            return None
        
        try:
            # Use existing invoice generation logic
            from stfoom.logicold import invoice_gen
            
            # Prepare sale data for invoice generation
            sale_data = {
                'client': target_sale.get('client', ''),
                'produit': target_sale.get('produit', ''),
                'quantite': target_sale.get('quantite', 0),
                'prix_unitaire': target_sale.get('prix_unitaire', 0),
                'mt_ht': target_sale.get('mt_ht', 0),
                'fodec': target_sale.get('fodec', 0),
                'tva19': target_sale.get('tva19', 0),
                'transport': target_sale.get('transport', 0),
                'tva7': target_sale.get('tva7', 0),
                'timbre': target_sale.get('timbre', 0),
                'ttc': target_sale.get('ttc', 0),
                'nfacture_seq': target_sale.get('nfacture_seq', nfacture),
                'date': target_sale.get('date', datetime.now().strftime('%Y-%m-%d'))
            }
            
            # Generate the invoice
            invoice_path = invoice_gen.generate_invoice(sale_data, output_path)
            return invoice_path
            
        except Exception as e:
            print(f"[SALES_SERVICE] Error regenerating invoice: {e}")
            return None
