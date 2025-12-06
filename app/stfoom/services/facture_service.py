"""
FactureService - Phase 2I Migration
===================================
Service layer for invoice generation business logic.
Migrated from direct logic dependencies in FacturePage.
"""

from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime

class FactureService:
    """Service for invoice generation business logic."""
    
    def __init__(self, facture_repository):
        """
        Initialize FactureService with dependency injection.
        
        Args:
            facture_repository: Repository for facture data access
        """
        self.facture_repo = facture_repository
        
    def get_clients_dataframe(self) -> pd.DataFrame:
        """
        Get clients as pandas DataFrame for FacturePage compatibility.
        
        Returns:
            pd.DataFrame: Clients data
        """
        clients_data = self.facture_repo.get_all_clients()
        return pd.DataFrame(clients_data) if clients_data else pd.DataFrame()
    
    def get_all_clients(self) -> List[Dict]:
        """
        Get all clients as a list of dictionaries.
        
        Returns:
            List[Dict]: All clients data
        """
        return self.facture_repo.get_all_clients()
    
    def get_products_dataframe(self) -> pd.DataFrame:
        """
        Get products as pandas DataFrame for FacturePage compatibility.
        
        Returns:
            pd.DataFrame: Products data
        """
        products_data = self.facture_repo.get_all_products()
        return pd.DataFrame(products_data) if products_data else pd.DataFrame()
    
    def get_next_invoice_number(self) -> int:
        """
        Get the next available invoice number for the current year.
        
        Returns:
            int: Next invoice number (format: YYYY00001)
        """
        try:
            year = datetime.today().year
            last_number = self.facture_repo.get_last_invoice_number_for_year(year)
            
            if last_number == 0:
                # No invoices for this year, start with 00001
                return int(f"{year}00001")
            else:
                # Get next sequence number
                last_sequence = int(str(last_number)[4:])  # Extract sequence part
                next_sequence = last_sequence + 1
                
                # Validate sequence number
                if next_sequence > 99999:
                    raise ValueError(f"Numéro de séquence maximum atteint pour l'année {year}")
                
                return int(f"{year}{next_sequence:05d}")
                
        except Exception as e:
            print(f"[FACTURE SERVICE] Error getting next invoice number: {e}")
            # Fallback: use current timestamp as base
            timestamp = int(datetime.now().timestamp())
            return int(f"{year}{timestamp % 100000:05d}")
    
    def get_invoice_number_info(self, nfacture_int: int) -> Optional[Dict[str, Any]]:
        """
        Get information about an invoice number.
        
        Args:
            nfacture_int: Invoice number to analyze
            
        Returns:
            Dict with year, sequence, formatted display, exists flag
        """
        try:
            nfacture_str = str(nfacture_int)
            year = nfacture_str[:4]
            sequence = nfacture_str[4:]
            
            return {
                "nfacture": nfacture_int,
                "year": int(year),
                "sequence": int(sequence),
                "display": f"Facture {int(sequence):04d}-{year}",
                "exists": self.check_invoice_exists(nfacture_int)
            }
        except Exception as e:
            print(f"[FACTURE SERVICE] Error getting invoice info: {e}")
            return None
    
    def check_invoice_exists(self, nfacture_int: int) -> bool:
        """
        Check if an invoice number already exists.
        
        Args:
            nfacture_int: Invoice number to check
            
        Returns:
            bool: True if exists, False otherwise
        """
        return self.facture_repo.invoice_exists(nfacture_int)
    
    def validate_invoice_number(self, nfacture_int: int) -> tuple[bool, str]:
        """
        Validate an invoice number format and uniqueness.
        
        Args:
            nfacture_int: Invoice number to validate
            
        Returns:
            tuple: (is_valid, error_message)
        """
        try:
            # Check if it's a positive integer
            if not isinstance(nfacture_int, int) or nfacture_int <= 0:
                return False, "Le numéro de facture doit être un nombre entier positif."
            
            # Check format: should be YYYY00001 format
            nfacture_str = str(nfacture_int)
            if len(nfacture_str) != 9:
                return False, "Le numéro de facture doit avoir 9 chiffres (YYYY00001)."
            
            # Check year part (first 4 digits)
            year_part = nfacture_str[:4]
            current_year = datetime.today().year
            try:
                year = int(year_part)
                if year < 2020 or year > current_year + 1:  # Allow next year for planning
                    return False, f"L'année dans le numéro de facture ({year}) n'est pas valide."
            except ValueError:
                return False, "L'année dans le numéro de facture n'est pas un nombre valide."
            
            # Check sequence part (last 5 digits)
            sequence_part = nfacture_str[4:]
            try:
                sequence = int(sequence_part)
                if sequence < 1 or sequence > 99999:
                    return False, "Le numéro de séquence doit être entre 00001 et 99999."
            except ValueError:
                return False, "Le numéro de séquence n'est pas un nombre valide."
            
            # Check if invoice already exists
            if self.check_invoice_exists(nfacture_int):
                return False, f"La facture {nfacture_int} existe déjà."
            
            return True, ""
            
        except Exception as e:
            return False, f"Erreur lors de la validation: {str(e)}"
    
    def validate_invoice_generation(self, client: Dict, chantier: str, selection: List[Dict]) -> tuple[bool, str]:
        """
        Validate invoice generation parameters.
        
        Args:
            client: Client data dictionary
            chantier: Project/site name
            selection: List of selected products with quantities
            
        Returns:
            tuple: (is_valid, error_message)
        """
        # Validate client
        if not client:
            return False, "Sélectionnez un client."
        
        # Validate chantier (project)
        if not chantier or len(chantier.strip()) < 3:
            return False, "Le chantier doit contenir au moins 3 caractères."
        
        # Validate product selection
        if not selection or len(selection) == 0:
            return False, "Aucun produit sélectionné."
        
        # Validate each product in selection
        total_amount = 0.0
        for item in selection:
            # Validate quantity
            qty = item.get('qty', 0)
            if not isinstance(qty, (int, float)) or qty < 1:
                return False, f"Quantité invalide pour le produit {item.get('code', 'inconnu')} (minimum: 1)"
            if qty > 9999:
                return False, f"Quantité trop élevée pour le produit {item.get('code', 'inconnu')} (maximum: 9999)"
            
            # Calculate total for validation (if price available)
            if 'prix_ht' in item:
                total_amount += qty * item['prix_ht']
        
        # Validate total amount (prevent extremely large invoices)
        if total_amount > 1000000:  # 1 million DT
            return False, f"Le montant total est trop élevé ({total_amount:.3f} DT). Maximum: 1,000,000 DT"
        
        return True, ""
    
    def generate_invoice(self, client: Dict, chantier: str, selection: List[Dict], 
                        nfacture_int: Optional[int] = None, date_facture: Optional[str] = None) -> str:
        """
        Generate an invoice and return the file path.
        
        Args:
            client: Client data dictionary
            chantier: Project/site name
            selection: List of selected products with quantities
            nfacture_int: Optional specific invoice number
            date_facture: Optional specific invoice date
            
        Returns:
            str: Path to generated invoice file
            
        Raises:
            ValueError: If validation fails
        """
        # Validate inputs
        is_valid, error_msg = self.validate_invoice_generation(client, chantier, selection)
        if not is_valid:
            raise ValueError(error_msg)
        
        # Validate invoice number if provided
        if nfacture_int is not None:
            is_valid, error_msg = self.validate_invoice_number(nfacture_int)
            if not is_valid:
                raise ValueError(f"Numéro de facture invalide: {error_msg}")
        
        # Get next invoice number if not provided
        if nfacture_int is None:
            nfacture_int = self.get_next_invoice_number()
            print(f"[FACTURE SERVICE] Using auto-generated invoice number: {nfacture_int}")
        
        # Delegate to invoice generation logic
        try:
            file_path = self.facture_repo.generate_invoice_file(
                client, chantier, selection, nfacture_int, date_facture
            )
            print(f"[FACTURE SERVICE] Invoice generated successfully: {file_path}")
            return file_path
            
        except Exception as e:
            print(f"[FACTURE SERVICE] Error generating invoice: {e}")
            raise ValueError(f"Erreur lors de la génération de la facture: {str(e)}")
    
    def load_client_by_code(self, code_client: str) -> Optional[Dict]:
        """
        Load a client by their code.
        
        Args:
            code_client: Client code to search for
            
        Returns:
            Optional[Dict]: Client data or None if not found
        """
        return self.facture_repo.get_client_by_code(code_client)
    
    def calculate_client_discount(self, client: Dict, products_df: pd.DataFrame) -> List[str]:
        """
        Calculate and format client-specific discount information.
        Now includes chantier-based remises (preferred) and legacy client remises.
        
        Args:
            client: Client data dictionary
            products_df: Products DataFrame
            
        Returns:
            List[str]: Formatted discount messages
        """
        if not client:
            return []
        
        discount_messages = []
        
        # Check for chantier remises if client has a chantier
        client_name = client.get('nom_client', '')
        if client_name:
            try:
                # Import here to avoid circular imports
                from ..services.chantier_remise_service import ChantierRemiseService
                chantier_service = ChantierRemiseService(self.facture_repo.db_path)
                
                chantier_remises = chantier_service.get_chantier_remises(client_name)
                if chantier_remises:
                    discount_messages.append(f"[Chantier {client_name}] Remises disponibles:")
                    for product_code, remise_data in chantier_remises.items():
                        if remise_data['remise_percentage'] and remise_data['remise_percentage'] > 0:
                            discount_messages.append(f"  - {product_code}: {remise_data['remise_percentage']}%")
                        if remise_data['prix_specifique'] and remise_data['prix_specifique'] > 0:
                            discount_messages.append(f"  - {product_code}: Prix spécifique {remise_data['prix_specifique']:.3f}")
            except Exception as e:
                print(f"[FACTURE SERVICE] Error getting chantier remises: {e}")
        
        # Legacy client remises (deprecated but still shown for compatibility)
        legacy_remises = []
        for _, product in products_df.iterrows():
            code_val = product['code']
            # Handle numpy scalar/array values
            try:
                code_str = str(code_val.item())
            except AttributeError:
                code_str = str(code_val)
            
            discount_col = f"remise_{code_str.lower()}"
            if discount_col in client and client[discount_col] and client[discount_col] > 0:
                legacy_remises.append(f"  - {product['designation']}: {int(client[discount_col])}%")
        
        if legacy_remises:
            discount_messages.append("[Client - Obsolète] Remises client:")
            discount_messages.extend(legacy_remises)
        
        return discount_messages

    def regenerate_invoice(self, nfacture_int: int) -> Optional[str]:
        """
        Regenerate an existing invoice using stored details.
        
        Args:
            nfacture_int: Invoice number to regenerate
            
        Returns:
            Optional[str]: Path to regenerated file or None if failed
        """
        try:
            # Use the invoice generation engine for regeneration
            from .invoice_generation_engine import InvoiceGenerator
            
            # Create invoice generator with repository dependency
            invoice_gen = InvoiceGenerator(self.facture_repo)
            
            # Regenerate invoice
            file_path = invoice_gen.regenerate_invoice(nfacture_int)
            
            if file_path:
                print(f"[FACTURE SERVICE] Invoice {nfacture_int} regenerated successfully: {file_path}")
            else:
                print(f"[FACTURE SERVICE] Failed to regenerate invoice {nfacture_int}")
            
            return file_path
            
        except Exception as e:
            print(f"[FACTURE SERVICE] Error regenerating invoice {nfacture_int}: {e}")
            return None
