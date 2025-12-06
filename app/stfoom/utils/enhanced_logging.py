"""
Enhanced Activity Logging Utilities
===================================
Comprehensive logging helpers that capture detailed action information
including specific record IDs and operation details.
"""

from typing import Optional, Dict, Any
from app.stfoom.services.detailed_activity_service import detailed_logger
from app.stfoom.services.user_activity_service import activity_logger


def log_create_action(module: str, resource_type: str, resource_id: Any, data: Dict[str, Any] = None, **kwargs):
    """
    Log a CREATE action with detailed information.
    
    Example:
        log_create_action("facture", "facture", 96, {"client": "ABC Corp", "montant": 1500})
        -> "Created facture #96 for client ABC Corp with amount 1500.00 DT"
    """
    # Build descriptive message
    description_parts = [f"Created {resource_type} #{resource_id}"]
    
    if data:
        # Extract key fields for description
        if 'client' in data or 'raison_sociale' in data:
            client = data.get('client') or data.get('raison_sociale')
            description_parts.append(f"for client '{client}'")
        
        if 'fournisseur' in data:
            description_parts.append(f"for supplier '{data['fournisseur']}'")
        
        if 'montant' in data or 'ttc' in data or 'montant_paye' in data:
            amount = data.get('montant') or data.get('ttc') or data.get('montant_paye')
            description_parts.append(f"with amount {amount:.2f} DT")
        
        if 'date' in data or 'date_facture' in data:
            date = data.get('date') or data.get('date_facture')
            description_parts.append(f"dated {date}")
    
    description = " ".join(description_parts)
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="create",
        action_category="data",
        action_name=f"create_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        operation_parameters=data,
        after_state=data,
        **kwargs
    )
    
    # Also log to old logger for compatibility
    activity_logger.log_activity(
        action="create",
        module=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=description
    )


def log_update_action(module: str, resource_type: str, resource_id: Any, 
                     before: Dict[str, Any] = None, after: Dict[str, Any] = None,
                     changes: Dict[str, tuple] = None, **kwargs):
    """
    Log an UPDATE action with before/after states.
    
    Example:
        log_update_action("facture", "facture", 96, 
                         changes={"montant": (1500, 1600), "status": ("draft", "validated")})
        -> "Updated facture #96: changed montant from 1500 to 1600, status from draft to validated"
    """
    description_parts = [f"Updated {resource_type} #{resource_id}"]
    
    if changes:
        change_descriptions = []
        for field, (old_val, new_val) in changes.items():
            change_descriptions.append(f"{field} from {old_val} to {new_val}")
        
        if change_descriptions:
            description_parts.append(": " + ", ".join(change_descriptions))
    elif before and after:
        # Detect changes automatically
        changes_list = []
        for key in after.keys():
            if key in before and before[key] != after[key]:
                changes_list.append(f"{key} from {before[key]} to {after[key]}")
        
        if changes_list:
            description_parts.append(": " + ", ".join(changes_list))
    
    description = "".join(description_parts)
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="update",
        action_category="data",
        action_name=f"update_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        before_state=before,
        after_state=after,
        changes_made=list(changes.keys()) if changes else None,
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="update",
        module=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=description
    )


def log_delete_action(module: str, resource_type: str, resource_id: Any, 
                     deleted_data: Dict[str, Any] = None, **kwargs):
    """
    Log a DELETE action with information about what was deleted.
    
    Example:
        log_delete_action("achat", "achat", 89, {"fournisseur": "XYZ Ltd", "montant": 2500})
        -> "Deleted achat #89 (fournisseur: XYZ Ltd, montant: 2500.00 DT)"
    """
    description_parts = [f"Deleted {resource_type} #{resource_id}"]
    
    if deleted_data:
        detail_parts = []
        
        if 'client' in deleted_data or 'raison_sociale' in deleted_data:
            client = deleted_data.get('client') or deleted_data.get('raison_sociale')
            detail_parts.append(f"client: {client}")
        
        if 'fournisseur' in deleted_data:
            detail_parts.append(f"fournisseur: {deleted_data['fournisseur']}")
        
        if 'montant' in deleted_data or 'ttc' in deleted_data:
            amount = deleted_data.get('montant') or deleted_data.get('ttc')
            detail_parts.append(f"montant: {amount:.2f} DT")
        
        if detail_parts:
            description_parts.append(f" ({', '.join(detail_parts)})")
    
    description = "".join(description_parts)
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="delete",
        action_category="data",
        action_name=f"delete_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        before_state=deleted_data,
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="delete",
        module=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=description
    )


def log_payment_action(action: str, payment_id: Any, invoice_id: Any, amount: float,
                      method: str = None, bank_id: Any = None, **kwargs):
    """
    Log payment-related actions with full details.
    
    Example:
        log_payment_action("add", 85, 96, 1500.00, method="banque", bank_id=3)
        -> "Added payment #85 for invoice #96: 1500.00 DT via banque (Bank #3)"
    """
    description_parts = [f"{action.capitalize()} payment #{payment_id} for invoice #{invoice_id}"]
    description_parts.append(f": {amount:.2f} DT")
    
    if method:
        description_parts.append(f" via {method}")
    
    if bank_id:
        description_parts.append(f" (Bank #{bank_id})")
    
    description = "".join(description_parts)
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type=action,
        action_category="payment",
        action_name=f"{action}_payment",
        action_description=description,
        module_name="payment",
        resource_type="payment",
        resource_id=str(payment_id),
        parent_resource_type="invoice",
        parent_resource_id=str(invoice_id),
        operation_parameters={
            "amount": amount,
            "method": method,
            "bank_id": bank_id
        },
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action=f"{action}_payment",
        module="payment",
        resource_type="payment",
        resource_id=str(payment_id),
        details=description
    )


def log_verification_action(module: str, resource_type: str, resource_id: Any, 
                           verified: bool = True, **kwargs):
    """
    Log verification actions (e.g., bank transaction verification).
    
    Example:
        log_verification_action("bank", "transaction", 123, verified=True)
        -> "Verified bank transaction #123"
    """
    status = "Verified" if verified else "Unverified"
    description = f"{status} {resource_type} #{resource_id}"
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="verify" if verified else "unverify",
        action_category="data",
        action_name=f"verify_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="verify" if verified else "unverify",
        module=module,
        resource_type=resource_type,
        resource_id=str(resource_id),
        details=description
    )


def log_export_action(module: str, resource_type: str, format: str, count: int = None,
                     filename: str = None, **kwargs):
    """
    Log export actions with details.
    
    Example:
        log_export_action("facture", "factures", "excel", count=25, filename="factures_2025.xlsx")
        -> "Exported 25 factures to Excel (factures_2025.xlsx)"
    """
    description_parts = ["Exported"]
    
    if count:
        description_parts.append(f" {count}")
    
    description_parts.append(f" {resource_type} to {format.upper()}")
    
    if filename:
        description_parts.append(f" ({filename})")
    
    description = "".join(description_parts)
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="export",
        action_category="data",
        action_name=f"export_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        operation_parameters={
            "format": format,
            "count": count,
            "filename": filename
        },
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="export",
        module=module,
        resource_type=resource_type,
        details=description
    )


def log_print_action(module: str, resource_type: str, resource_id: Any = None,
                    count: int = 1, **kwargs):
    """
    Log print actions.
    
    Example:
        log_print_action("cheque", "cheque", 456)
        -> "Printed cheque #456"
    """
    if resource_id:
        description = f"Printed {resource_type} #{resource_id}"
    else:
        description = f"Printed {count} {resource_type}(s)"
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="print",
        action_category="action",
        action_name=f"print_{resource_type}",
        action_description=description,
        module_name=module,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        operation_parameters={"count": count},
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="print",
        module=module,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=description
    )


def log_search_action(module: str, query: str, results_count: int = None, **kwargs):
    """
    Log search actions.
    
    Example:
        log_search_action("vente", "ABC Corp", results_count=5)
        -> "Searched ventes for 'ABC Corp' (5 results)"
    """
    description = f"Searched {module} for '{query}'"
    
    if results_count is not None:
        description += f" ({results_count} result{'s' if results_count != 1 else ''})"
    
    # Log to detailed logger
    detailed_logger.log_detailed_activity(
        action_type="search",
        action_category="query",
        action_name=f"search_{module}",
        action_description=description,
        module_name=module,
        operation_parameters={
            "query": query,
            "results_count": results_count
        },
        **kwargs
    )
    
    # Also log to old logger
    activity_logger.log_activity(
        action="search",
        module=module,
        details=description
    )
