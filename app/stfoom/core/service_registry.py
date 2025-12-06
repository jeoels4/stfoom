"""
Service Registration
==================
Registers all services with the dependency injection container.
"""

from .container import container
from ..services.user_service import UserService
from ..services.sales_service import SalesService
from ..services.avoir_service import AvoirService
from ..services.payment_service import PaymentService
# Lightweight fallback permission service used when DB-backed service isn't available
try:
    from ..logic.basic_permission_service import BasicPermissionService
except Exception:
    BasicPermissionService = None

# Try importing additional service modules and repositories individually so a
# single ImportError doesn't disable all additional services. Collect import
# results in local variables and register only the modules that succeeded.
_mods = {}
def _try_import(path, name=None):
    try:
        mod = __import__(path, fromlist=['*'])
        return mod
    except Exception as e:
        print(f"[SERVICE REGISTRY] Could not import {path}: {e}")
        return None

# Services
_mods['PurchaseService'] = _try_import('app.stfoom.services.purchase_service')
_mods['BankService'] = _try_import('app.stfoom.services.bank_service')
_mods['CaisseService'] = _try_import('app.stfoom.services.caisse_service')
_mods['RetenuService'] = _try_import('app.stfoom.services.retenu_service')
_mods['VoitureService'] = _try_import('app.stfoom.services.voiture_service')
_mods['CalendarService'] = _try_import('app.stfoom.services.calendar_service')
_mods['DevisService'] = _try_import('app.stfoom.services.devis_service')
_mods['FactureService'] = _try_import('app.stfoom.services.facture_service')
_mods['DocumentService'] = _try_import('app.stfoom.services.document_service')
_mods['SettingsService'] = _try_import('app.stfoom.services.tax_service')
_mods['PermissionService'] = _try_import('app.stfoom.services.permission_service')
_mods['ChequeService'] = _try_import('app.stfoom.services.cheque_service')

# Repositories
_mods['AchatRepository'] = _try_import('app.stfoom.data.achat_repository')
_mods['BankRepository'] = _try_import('app.stfoom.data.bank_repository')
_mods['CaisseRepository'] = _try_import('app.stfoom.data.caisse_repository')
_mods['RetenuRepository'] = _try_import('app.stfoom.data.retenu_repository')
_mods['VoitureRepository'] = _try_import('app.stfoom.data.voiture_repository')
_mods['CalendarRepository'] = _try_import('app.stfoom.data.calendar_repository')
_mods['DevisRepository'] = _try_import('app.stfoom.data.devis_repository')
_mods['FactureRepository'] = _try_import('app.stfoom.data.facture_repository')
_mods['SettingsRepository'] = _try_import('app.stfoom.data.settings_repository_clean')
_mods['PermissionRepository'] = _try_import('app.stfoom.data.permission_repository')
_mods['ChequeRepository'] = _try_import('app.stfoom.data.cheque_repository')

# Determine availability based on at least one additional module present
ADDITIONAL_SERVICES_AVAILABLE = any(v is not None for v in _mods.values())

def register_all_services():
    """
    Register services with the DI container.
    
    Registers core services plus any additional services that are ready.
    
    Returns:
        DIContainer: Configured container instance
    """
    print("[SERVICE REGISTRY] Registering services...")
    
    # Core Services (always available)
    container.register('user_service', lambda: UserService())
    container.register('sales_service', lambda: SalesService())
    container.register('avoir_service', lambda: AvoirService())
    container.register('payment_service', lambda: PaymentService())
    
    services_count = 4
    
    # Additional Services (if repositories are clean)
    if ADDITIONAL_SERVICES_AVAILABLE:
        try:
            # Register repositories first (only when their modules imported)
            if _mods.get('AchatRepository'):
                container.register('achat_repository', lambda: _mods['AchatRepository'].AchatRepository())
                services_count += 1
            if _mods.get('BankRepository'):
                container.register('bank_repository', lambda: _mods['BankRepository'].BankRepository())
                services_count += 1
            if _mods.get('CaisseRepository'):
                container.register('caisse_repository', lambda: _mods['CaisseRepository'].CaisseRepository())
                services_count += 1
            if _mods.get('RetenuRepository'):
                container.register('retenu_repository', lambda: _mods['RetenuRepository'].RetenuRepository())
                services_count += 1
            if _mods.get('VoitureRepository'):
                container.register('voiture_repository', lambda: _mods['VoitureRepository'].VoitureRepository())
                services_count += 1
            if _mods.get('CalendarRepository'):
                container.register('calendar_repository', lambda: _mods['CalendarRepository'].CalendarRepository())
                services_count += 1
            if _mods.get('DevisRepository'):
                container.register('devis_repository', lambda: _mods['DevisRepository'].DevisRepository())
                services_count += 1
            if _mods.get('FactureRepository'):
                container.register('facture_repository', lambda: _mods['FactureRepository'].FactureRepository())
                services_count += 1
            if _mods.get('SettingsRepository'):
                container.register('settings_repository', lambda: _mods['SettingsRepository'].SettingsRepository())
                services_count += 1
            if _mods.get('PermissionRepository'):
                container.register('permission_repository', lambda: _mods['PermissionRepository'].PermissionRepository())
                services_count += 1
            if _mods.get('ChequeRepository'):
                container.register('cheque_repository', lambda: _mods['ChequeRepository'].ChequeRepository())
                services_count += 1

            # Register services with their repositories (only when module present)
            if _mods.get('PurchaseService') and _mods.get('AchatRepository'):
                container.register('purchase_service', lambda: _mods['PurchaseService'].PurchaseService(
                    container.get('achat_repository')
                ))
                services_count += 1
            if _mods.get('BankService') and _mods.get('BankRepository'):
                container.register('bank_service', lambda: _mods['BankService'].BankService(
                    container.get('bank_repository')
                ))
                services_count += 1
            if _mods.get('CaisseService') and _mods.get('CaisseRepository'):
                container.register('caisse_service', lambda: _mods['CaisseService'].CaisseService(
                    container.get('caisse_repository')
                ))
                services_count += 1
            if _mods.get('RetenuService') and _mods.get('RetenuRepository'):
                container.register('retenu_service', lambda: _mods['RetenuService'].RetenuService(
                    container.get('retenu_repository')
                ))
                services_count += 1
            if _mods.get('VoitureService') and _mods.get('VoitureRepository'):
                container.register('voiture_service', lambda: _mods['VoitureService'].VoitureService(
                    container.get('voiture_repository')
                ))
                services_count += 1
            if _mods.get('CalendarService') and _mods.get('CalendarRepository'):
                container.register('calendar_service', lambda: _mods['CalendarService'].CalendarService(
                    container.get('calendar_repository')
                ))
                services_count += 1
            if _mods.get('DevisService') and _mods.get('DevisRepository'):
                container.register('devis_service', lambda: _mods['DevisService'].DevisService(
                    container.get('devis_repository')
                ))
                services_count += 1
            if _mods.get('FactureService') and _mods.get('FactureRepository'):
                container.register('facture_service', lambda: _mods['FactureService'].FactureService(
                    container.get('facture_repository')
                ))
                services_count += 1
            if _mods.get('DocumentService'):
                container.register('document_service', lambda: _mods['DocumentService'].DocumentService())
                services_count += 1
            if _mods.get('SettingsService') and _mods.get('SettingsRepository'):
                container.register('settings_service', lambda: _mods['SettingsService'].SettingsService(
                    container.get('settings_repository')
                ))
                services_count += 1

            # Permission Service registration - try DB-backed, else fallback handled below
            if _mods.get('PermissionService') and _mods.get('PermissionRepository'):
                try:
                    container.register('permission_service', lambda: _mods['PermissionService'].PermissionService(
                        container.get('permission_repository')
                    ))
                    services_count += 1
                except Exception as e:
                    print(f"[SERVICE REGISTRY] DB-backed PermissionService registration failed: {e}. Using BasicPermissionService fallback.")
                    if BasicPermissionService:
                        container.register('permission_service', lambda: BasicPermissionService())
                        services_count += 1
            else:
                # Fallback: if DB-backed service can't be constructed, use BasicPermissionService
                if BasicPermissionService and 'permission_service' not in container._services:
                    container.register('permission_service', lambda: BasicPermissionService())
                    services_count += 1

            if _mods.get('ChequeService') and _mods.get('ChequeRepository'):
                container.register('cheque_service', lambda: _mods['ChequeService'].ChequeService(
                    container.get('cheque_repository')
                ))
                services_count += 1

            print("[SERVICE REGISTRY] Additional services registered where available")

        except Exception as e:
            print(f"[SERVICE REGISTRY] Some services couldn't be registered: {e}")
    else:
        print("[SERVICE REGISTRY] Additional services not available yet")
        # Register a safe fallback permission_service so UI components can function
        try:
            if BasicPermissionService and 'permission_service' not in container._services:
                container.register('permission_service', lambda: BasicPermissionService())
                services_count += 1
                print('[SERVICE REGISTRY] Registered fallback BasicPermissionService')
        except Exception as e:
            print(f"[SERVICE REGISTRY] Could not register fallback BasicPermissionService: {e}")
    
    print(f"[SERVICE REGISTRY] Registered {services_count} services total")
    print("  UserService - Authentication & session management")
    print("  SalesService - Sales operations")
    print("  AvoirService - Credit note operations")
    print("  PaymentService - Payment processing")
    
    if services_count > 4:
        print("  PurchaseService - Purchase management")
        print("  BankService - Bank operations")
        print("  CaisseService - Cash management")
        print("  RetenuService - Retention management")
        print("  VoitureService - Vehicle management")
        print("  CalendarService - Calendar operations")
        print("  DevisService - Quote operations")
        print("  FactureService - Invoice operations")
        print("  DocumentService - Document management")
        print("  SettingsService - Application settings & tax management")
        print("  PermissionService - Database-based permission management")
        print("  ChequeService - Cheque management & bank integration")
    
    return container

    # Ensure at least a minimal permission_service is available for UI fallbacks
    # (This code will not normally run because of the return above; keep for safety.)
    try:
        if 'permission_service' not in container._services and 'permission_service' not in container._singletons:
            if BasicPermissionService:
                print('[SERVICE REGISTRY] Registering BasicPermissionService as fallback (post-return safeguard)')
                container.register('permission_service', lambda: BasicPermissionService())
    except Exception:
        pass

def get_registered_services():
    """Get list of registered service names."""
    return list(container._services.keys()) + list(container._singletons.keys())

# ✅ FIXED: Remove auto-registration to prevent double initialization
# register_all_services()  # REMOVED: Only call manually from main.py
