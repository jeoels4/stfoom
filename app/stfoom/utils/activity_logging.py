"""
Activity Logging Utilities for STFOOM Modules
=============================================
Convenience functions for modules to easily log user activities.
"""

from app.stfoom.services.user_activity_service import (
    activity_logger,
    log_user_action,
    log_data_operation,
    log_page_access,
    log_export_operation,
    log_import_operation,
    log_error,
    log_warning
)


# Specific logging functions for common STFOOM operations

def log_facture_operation(operation: str, facture_id: str = None, details: str = None):
    """Log facture-related operations"""
    log_data_operation(operation, "facture", "facture", facture_id, details)


def log_devis_operation(operation: str, devis_id: str = None, details: str = None):
    """Log devis-related operations"""
    log_data_operation(operation, "devis", "devis", devis_id, details)


def log_vente_operation(operation: str, vente_id: str = None, details: str = None):
    """Log vente-related operations"""
    log_data_operation(operation, "vente", "vente", vente_id, details)


def log_achat_operation(operation: str, achat_id: str = None, details: str = None):
    """Log achat-related operations"""
    log_data_operation(operation, "achat", "achat", achat_id, details)


def log_client_operation(operation: str, client_id: str = None, details: str = None):
    """Log client-related operations"""
    log_data_operation(operation, "client", "client", client_id, details)


def log_payment_operation(operation: str, payment_id: str = None, details: str = None, module: str = "payment"):
    """Log payment-related operations"""
    log_data_operation(operation, module, "payment", payment_id, details)


def log_document_operation(operation: str, document_name: str = None, details: str = None):
    """Log document-related operations"""
    log_data_operation(operation, "document", "document", document_name, details)


def log_backup_operation(operation: str, backup_name: str = None, details: str = None):
    """Log backup-related operations"""
    log_user_action(f"backup_{operation}", "backup", details or f"Backup {operation}")


def log_sync_operation(operation: str, details: str = None):
    """Log synchronization operations"""
    log_user_action(f"sync_{operation}", "sync", details or f"Sync {operation}")


def log_user_management_operation(operation: str, target_user: str = None, details: str = None):
    """Log user management operations"""
    log_data_operation(operation, "user_management", "user", target_user, details)


def log_permission_operation(operation: str, permission: str = None, details: str = None):
    """Log permission management operations"""
    log_data_operation(operation, "permission_management", "permission", permission, details)


def log_calendar_operation(operation: str, event_id: str = None, details: str = None):
    """Log calendar-related operations"""
    log_data_operation(operation, "calendar", "event", event_id, details)


def log_voiture_operation(operation: str, voiture_id: str = None, details: str = None):
    """Log voiture-related operations"""
    log_data_operation(operation, "voiture", "voiture", voiture_id, details)


def log_bank_operation(operation: str, transaction_id: str = None, details: str = None):
    """Log bank-related operations"""
    log_data_operation(operation, "bank", "transaction", transaction_id, details)


def log_caisse_operation(operation: str, entry_id: str = None, details: str = None):
    """Log caisse-related operations"""
    log_data_operation(operation, "caisse", "entry", entry_id, details)


def log_ciment_operation(operation: str, bl_id: str = None, details: str = None):
    """Log ciment/cement-related operations"""
    log_data_operation(operation, "ciment", "bl", bl_id, details)


def log_settings_operation(operation: str, setting_name: str = None, details: str = None):
    """Log settings-related operations"""
    log_data_operation(operation, "settings", "setting", setting_name, details)


def log_calculation_operation(details: str = None):
    """Log calculator usage"""
    log_user_action("calculation", "calculator", details or "Performed calculation")


def log_report_generation(report_type: str, module: str, details: str = None):
    """Log report generation"""
    log_user_action("generate_report", module, details or f"Generated {report_type} report")


def log_print_operation(document_type: str, module: str, details: str = None):
    """Log printing operations"""
    log_user_action("print", module, details or f"Printed {document_type}")


# Error logging helpers for specific modules

def log_facture_error(error_message: str, facture_id: str = None):
    """Log facture-related errors"""
    details = f"Facture error: {error_message}"
    if facture_id:
        details += f" (Facture ID: {facture_id})"
    log_error("facture", "facture_error", details)


def log_payment_error(error_message: str, module: str = "payment"):
    """Log payment-related errors"""
    log_error(module, "payment_error", f"Payment error: {error_message}")


def log_sync_error(error_message: str):
    """Log synchronization errors"""
    log_error("sync", "sync_error", f"Sync error: {error_message}")


def log_database_error(error_message: str, module: str = "database"):
    """Log database errors"""
    log_error(module, "database_error", f"Database error: {error_message}")


# Import/Export logging helpers

def log_excel_export(module: str, file_name: str = None, record_count: int = None):
    """Log Excel export operations"""
    details = f"Exported to Excel"
    if file_name:
        details += f" ({file_name})"
    if record_count:
        details += f" - {record_count} records"
    log_export_operation("excel", module, file_name)


def log_pdf_export(module: str, file_name: str = None):
    """Log PDF export operations"""
    log_export_operation("pdf", module, file_name)


def log_excel_import(module: str, file_name: str = None, record_count: int = None):
    """Log Excel import operations"""
    log_import_operation("excel", module, file_name, record_count)


# Search and filter logging

def log_search_operation(module: str, search_criteria: str, results_count: int = None):
    """Log search operations"""
    details = f"Search: {search_criteria}"
    if results_count is not None:
        details += f" ({results_count} results)"
    log_user_action("search", module, details)


def log_filter_operation(module: str, filter_criteria: str, results_count: int = None):
    """Log filter operations"""
    details = f"Filter: {filter_criteria}"
    if results_count is not None:
        details += f" ({results_count} results)"
    log_user_action("filter", module, details)


# Authentication and session logging

def log_login_attempt(username: str, success: bool, ip_address: str = "127.0.0.1"):
    """Log login attempts"""
    result = "success" if success else "error"
    details = f"Login attempt for user '{username}' - {'Success' if success else 'Failed'}"
    
    # Set IP for this specific log entry
    old_ip = activity_logger.current_ip
    activity_logger.current_ip = ip_address
    
    activity_logger.log_activity(
        action="login_attempt",
        module="authentication",
        details=details,
        result=result
    )
    
    # Restore old IP
    activity_logger.current_ip = old_ip


def log_logout(username: str):
    """Log logout events"""
    log_user_action("logout", "authentication", f"User '{username}' logged out")


def log_session_timeout(username: str):
    """Log session timeout events"""
    log_user_action("session_timeout", "authentication", f"Session timeout for user '{username}'")


# Performance and monitoring logging

def log_performance_issue(module: str, operation: str, execution_time_ms: int, details: str = None):
    """Log performance issues"""
    perf_details = f"Slow operation: {operation} took {execution_time_ms}ms"
    if details:
        perf_details += f" - {details}"
    
    activity_logger.log_activity(
        action="performance_warning",
        module=module,
        details=perf_details,
        result="warning",
        execution_time_ms=execution_time_ms
    )


def log_system_event(event_type: str, details: str = None):
    """Log system-level events"""
    log_user_action(event_type, "system", details or f"System event: {event_type}")