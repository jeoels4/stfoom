# stfoom/ui/language_manager.py
import json
import os
from typing import Dict, Any

class LanguageManager:
    """Manages application translations and language switching."""
    
    def __init__(self):
        self.current_language = "fr"
        self.translations = {}
        self.load_translations()
    
    def load_translations(self):
        """Load all translation files."""
        self.translations = {
            "fr": self._get_french_translations(),
            "en": self._get_english_translations()
        }
    
    def _get_french_translations(self) -> Dict[str, str]:
        """Get French translations."""
        return {
            # Main app
            "app_title": "STFOOM - Gestion Commerciale",
            "menu_vente": "Vente",
            "menu_achat": "Achat",
            "menu_facture": "Facture",
            "menu_devis": "Devis",
            "menu_caisse": "Caisse",
            "menu_bank": "Banque",
            "menu_calendar": "Calendrier",
            "menu_voiture": "Voitures",
            "menu_retenu": "Retenus",
            "menu_calculator": "Calculateur",
            "menu_backup": "Sauvegarde",
            "menu_sync": "Synchronisation",
            "menu_settings": "Paramètres",
            
            # Settings page
            "settings_title": "⚙️ Paramètres",
            "back_to_menu": "← Retour au menu",
            "tab_general": "Général",
            "tab_database": "Base de données",
            "tab_sync": "Synchronisation",
            "tab_backup": "Sauvegarde",
            "tab_advanced": "Avancé",
            
            # Language and Interface
            "language_interface": "Langue et Interface",
            "interface_language": "Langue de l'interface:",
            "theme": "Thème:",
            "light_theme": "Clair",
            "dark_theme": "Sombre",
            
            # Auto-save
            "auto_save": "Sauvegarde automatique",
            "enable_auto_save": "Activer la sauvegarde automatique",
            "save_interval": "Intervalle de sauvegarde (minutes):",
            
            # Database
            "database_info": "Informations de la base de données",
            "table_count": "Nombre de tables:",
            "total_records": "Total des enregistrements:",
            "database_error": "Erreur lors de la lecture de la base:",
            "maintenance": "Maintenance",
            "optimize_database": "Optimiser la base de données",
            "check_integrity": "Vérifier l'intégrité",
            "clean_temp_data": "Nettoyer les données temporaires",
            
            # Sync
            "sync_settings": "Paramètres de synchronisation",
            "auto_sync": "Synchronisation automatique",
            "sync_interval": "Intervalle de sync (secondes):",
            "sync_status": "Statut de synchronisation",
            "manual_sync": "Synchronisation manuelle",
            "sync_now": "Synchroniser maintenant",
            "checking": "Vérification...",
            "sync_online": "Serveur en ligne",
            "sync_offline": "Serveur hors ligne",
            
            # Backup
            "backup_settings": "Paramètres de sauvegarde",
            "auto_backup": "Sauvegarde automatique",
            "backup_interval": "Intervalle de sauvegarde (heures):",
            "backup_info": "Informations de sauvegarde",
            "last_backup": "Dernière sauvegarde:",
            "backup_size": "Taille:",
            "backup_count": "Nombre de sauvegardes:",
            "backup_actions": "Actions de sauvegarde",
            "create_backup": "Créer une sauvegarde",
            "restore_backup": "Restaurer une sauvegarde",
            "no_backups": "Aucune sauvegarde trouvée",
            
            # Advanced
            "advanced_settings": "Paramètres avancés",
            "debug_mode": "Mode debug",
            "enable_debug": "Activer le mode debug",
            "system_info": "Informations système",
            "view_logs": "Voir les logs",
            "import_export": "Import/Export",
            "export_settings": "Exporter les paramètres",
            "import_settings": "Importer les paramètres",
            "reset_settings": "Réinitialiser les paramètres",
            
            # Messages
            "settings_saved": "Paramètres sauvegardés avec succès!",
            "settings_reset": "Paramètres réinitialisés!",
            "backup_created": "Sauvegarde créée avec succès!",
            "backup_restored": "Sauvegarde restaurée avec succès!",
            "sync_success": "Synchronisation réussie!",
            "database_optimized": "Base de données optimisée!",
            "integrity_ok": "Intégrité de la base vérifiée - OK",
            "temp_data_cleaned": "Données temporaires nettoyées!",
            
            # Errors
            "error_saving": "Erreur lors de la sauvegarde des paramètres",
            "error_loading": "Erreur lors du chargement des paramètres",
            "error_backup": "Erreur lors de la création de la sauvegarde",
            "error_restore": "Erreur lors de la restauration",
            "error_sync": "Erreur lors de la synchronisation",
            "error_database": "Erreur lors de l'opération sur la base de données",
            
            # Common
            "save": "Sauvegarder",
            "cancel": "Annuler",
            "ok": "OK",
            "yes": "Oui",
            "no": "Non",
            "close": "Fermer",
            "refresh": "Actualiser",
            "loading": "Chargement...",
            "success": "Succès",
            "error": "Erreur",
            "warning": "Attention",
            "info": "Information",
            
            # Vente page
            "vente_title": "Gestion des Ventes",
            "add_vente": "Ajouter une vente",
            "edit_vente": "Modifier la vente",
            "delete_vente": "Supprimer la vente",
            "vente_date": "Date de vente",
            "vente_client": "Client",
            "vente_products": "Produits",
            "vente_total": "Total",
            "vente_status": "Statut",
            
            # Achat page
            "achat_title": "Gestion des Achats",
            "add_achat": "Ajouter un achat",
            "edit_achat": "Modifier l'achat",
            "delete_achat": "Supprimer l'achat",
            "achat_date": "Date d'achat",
            "achat_fournisseur": "Fournisseur",
            "achat_products": "Produits",
            "achat_total": "Total",
            "achat_status": "Statut",
            
            # Facture page
            "facture_title": "Gestion des Factures",
            "generate_facture": "Générer une facture",
            "facture_number": "Numéro de facture",
            "facture_date": "Date de facture",
            "facture_client": "Client",
            "facture_amount": "Montant",
            "facture_status": "Statut",
            
            # Devis page
            "devis_title": "Gestion des Devis",
            "generate_devis": "Générer un devis",
            "devis_number": "Numéro de devis",
            "devis_date": "Date de devis",
            "devis_client": "Client",
            "devis_amount": "Montant",
            "devis_status": "Statut",
            
            # Caisse page
            "caisse_title": "Gestion de Caisse",
            "caisse_balance": "Solde de caisse",
            "caisse_income": "Entrées",
            "caisse_expenses": "Sorties",
            "add_transaction": "Ajouter une transaction",
            "transaction_type": "Type de transaction",
            "transaction_amount": "Montant",
            "transaction_description": "Description",
            
            # Bank page
            "bank_title": "Gestion Bancaire",
            "bank_balance": "Solde bancaire",
            "bank_accounts": "Comptes bancaires",
            "add_account": "Ajouter un compte",
            "account_name": "Nom du compte",
            "account_number": "Numéro de compte",
            "account_balance": "Solde",
            
            # Calendar page
            "calendar_title": "Calendrier",
            "add_event": "Ajouter un événement",
            "event_title": "Titre de l'événement",
            "event_date": "Date",
            "event_time": "Heure",
            "event_description": "Description",
            
            # Voiture page
            "voiture_title": "Gestion des Voitures",
            "add_voiture": "Ajouter une voiture",
            "voiture_marque": "Marque",
            "voiture_modele": "Modèle",
            "voiture_annee": "Année",
            "voiture_prix": "Prix",
            "voiture_status": "Statut",
            
            # Retenu page
            "retenu_title": "Gestion des Retenus",
            "add_retenu": "Ajouter un retenu",
            "retenu_type": "Type de retenu",
            "retenu_amount": "Montant",
            "retenu_date": "Date",
            "retenu_description": "Description",
            
            # Calculator page
            "calculator_title": "Calculateur",
            "calculator_result": "Résultat",
            "calculator_clear": "Effacer",
            "calculator_equals": "=",
            
            # Backup page
            "backup_title": "Sauvegarde",
            "backup_create": "Créer une sauvegarde",
            "backup_restore": "Restaurer une sauvegarde",
            "backup_delete": "Supprimer une sauvegarde",
            "backup_download": "Télécharger",
            "backup_upload": "Téléverser",
            
            # Sync page
            "sync_title": "Synchronisation",
            "sync_status_online": "En ligne",
            "sync_status_offline": "Hors ligne",
            "sync_manual": "Synchronisation manuelle",
            "sync_auto": "Synchronisation automatique",
            "sync_settings": "Paramètres de sync",
        }
    
    def _get_english_translations(self) -> Dict[str, str]:
        """Get English translations."""
        return {
            # Main app
            "app_title": "STFOOM - Commercial Management",
            "menu_vente": "Sales",
            "menu_achat": "Purchase",
            "menu_facture": "Invoice",
            "menu_devis": "Quote",
            "menu_caisse": "Cash Register",
            "menu_bank": "Bank",
            "menu_calendar": "Calendar",
            "menu_voiture": "Cars",
            "menu_retenu": "Deductions",
            "menu_calculator": "Calculator",
            "menu_backup": "Backup",
            "menu_sync": "Sync",
            "menu_settings": "Settings",
            
            # Settings page
            "settings_title": "⚙️ Settings",
            "back_to_menu": "← Back to Menu",
            "tab_general": "General",
            "tab_database": "Database",
            "tab_sync": "Synchronization",
            "tab_backup": "Backup",
            "tab_advanced": "Advanced",
            
            # Language and Interface
            "language_interface": "Language and Interface",
            "interface_language": "Interface language:",
            "theme": "Theme:",
            "light_theme": "Light",
            "dark_theme": "Dark",
            
            # Auto-save
            "auto_save": "Auto-save",
            "enable_auto_save": "Enable auto-save",
            "save_interval": "Save interval (minutes):",
            
            # Database
            "database_info": "Database Information",
            "table_count": "Number of tables:",
            "total_records": "Total records:",
            "database_error": "Error reading database:",
            "maintenance": "Maintenance",
            "optimize_database": "Optimize database",
            "check_integrity": "Check integrity",
            "clean_temp_data": "Clean temporary data",
            
            # Sync
            "sync_settings": "Synchronization settings",
            "auto_sync": "Auto synchronization",
            "sync_interval": "Sync interval (seconds):",
            "sync_status": "Sync status",
            "manual_sync": "Manual synchronization",
            "sync_now": "Sync now",
            "checking": "Checking...",
            "sync_online": "Server online",
            "sync_offline": "Server offline",
            
            # Backup
            "backup_settings": "Backup settings",
            "auto_backup": "Auto backup",
            "backup_interval": "Backup interval (hours):",
            "backup_info": "Backup information",
            "last_backup": "Last backup:",
            "backup_size": "Size:",
            "backup_count": "Number of backups:",
            "backup_actions": "Backup actions",
            "create_backup": "Create backup",
            "restore_backup": "Restore backup",
            "no_backups": "No backups found",
            
            # Advanced
            "advanced_settings": "Advanced settings",
            "debug_mode": "Debug mode",
            "enable_debug": "Enable debug mode",
            "system_info": "System information",
            "view_logs": "View logs",
            "import_export": "Import/Export",
            "export_settings": "Export settings",
            "import_settings": "Import settings",
            "reset_settings": "Reset settings",
            
            # Messages
            "settings_saved": "Settings saved successfully!",
            "settings_reset": "Settings reset!",
            "backup_created": "Backup created successfully!",
            "backup_restored": "Backup restored successfully!",
            "sync_success": "Synchronization successful!",
            "database_optimized": "Database optimized!",
            "integrity_ok": "Database integrity verified - OK",
            "temp_data_cleaned": "Temporary data cleaned!",
            
            # Errors
            "error_saving": "Error saving settings",
            "error_loading": "Error loading settings",
            "error_backup": "Error creating backup",
            "error_restore": "Error restoring backup",
            "error_sync": "Error during synchronization",
            "error_database": "Error during database operation",
            
            # Common
            "save": "Save",
            "cancel": "Cancel",
            "ok": "OK",
            "yes": "Yes",
            "no": "No",
            "close": "Close",
            "refresh": "Refresh",
            "loading": "Loading...",
            "success": "Success",
            "error": "Error",
            "warning": "Warning",
            "info": "Information",
            
            # Vente page
            "vente_title": "Sales Management",
            "add_vente": "Add sale",
            "edit_vente": "Edit sale",
            "delete_vente": "Delete sale",
            "vente_date": "Sale date",
            "vente_client": "Client",
            "vente_products": "Products",
            "vente_total": "Total",
            "vente_status": "Status",
            
            # Achat page
            "achat_title": "Purchase Management",
            "add_achat": "Add purchase",
            "edit_achat": "Edit purchase",
            "delete_achat": "Delete purchase",
            "achat_date": "Purchase date",
            "achat_fournisseur": "Supplier",
            "achat_products": "Products",
            "achat_total": "Total",
            "achat_status": "Status",
            
            # Facture page
            "facture_title": "Invoice Management",
            "generate_facture": "Generate invoice",
            "facture_number": "Invoice number",
            "facture_date": "Invoice date",
            "facture_client": "Client",
            "facture_amount": "Amount",
            "facture_status": "Status",
            
            # Devis page
            "devis_title": "Quote Management",
            "generate_devis": "Generate quote",
            "devis_number": "Quote number",
            "devis_date": "Quote date",
            "devis_client": "Client",
            "devis_amount": "Amount",
            "devis_status": "Status",
            
            # Caisse page
            "caisse_title": "Cash Register Management",
            "caisse_balance": "Cash balance",
            "caisse_income": "Income",
            "caisse_expenses": "Expenses",
            "add_transaction": "Add transaction",
            "transaction_type": "Transaction type",
            "transaction_amount": "Amount",
            "transaction_description": "Description",
            
            # Bank page
            "bank_title": "Bank Management",
            "bank_balance": "Bank balance",
            "bank_accounts": "Bank accounts",
            "add_account": "Add account",
            "account_name": "Account name",
            "account_number": "Account number",
            "account_balance": "Balance",
            
            # Calendar page
            "calendar_title": "Calendar",
            "add_event": "Add event",
            "event_title": "Event title",
            "event_date": "Date",
            "event_time": "Time",
            "event_description": "Description",
            
            # Voiture page
            "voiture_title": "Car Management",
            "add_voiture": "Add car",
            "voiture_marque": "Brand",
            "voiture_modele": "Model",
            "voiture_annee": "Year",
            "voiture_prix": "Price",
            "voiture_status": "Status",
            
            # Retenu page
            "retenu_title": "Deduction Management",
            "add_retenu": "Add deduction",
            "retenu_type": "Deduction type",
            "retenu_amount": "Amount",
            "retenu_date": "Date",
            "retenu_description": "Description",
            
            # Calculator page
            "calculator_title": "Calculator",
            "calculator_result": "Result",
            "calculator_clear": "Clear",
            "calculator_equals": "=",
            
            # Backup page
            "backup_title": "Backup",
            "backup_create": "Create backup",
            "backup_restore": "Restore backup",
            "backup_delete": "Delete backup",
            "backup_download": "Download",
            "backup_upload": "Upload",
            
            # Sync page
            "sync_title": "Synchronization",
            "sync_status_online": "Online",
            "sync_status_offline": "Offline",
            "sync_manual": "Manual sync",
            "sync_auto": "Auto sync",
            "sync_settings": "Sync settings",
        }
    
    def get_text(self, key: str) -> str:
        """Get translated text for the given key."""
        return self.translations.get(self.current_language, {}).get(key, key)
    
    def set_language(self, language: str):
        """Set the current language."""
        if language in self.translations:
            self.current_language = language
            return True
        return False
    
    def get_available_languages(self) -> list:
        """Get list of available languages."""
        return list(self.translations.keys())
    
    def get_language_names(self) -> Dict[str, str]:
        """Get language names for display."""
        return {
            "fr": "Français",
            "en": "English"
        }

# Global instance
language_manager = LanguageManager() 