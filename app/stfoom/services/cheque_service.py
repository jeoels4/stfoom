"""
Cheque Service
==============
Business logic for cheque management operations.
"""
from typing import List, Dict, Optional
from datetime import datetime, date
import logging
from ..data.cheque_repository import ChequeRepository

logger = logging.getLogger(__name__)

class ChequeService:
    """Service for cheque management business logic"""
    
    def __init__(self, cheque_repository: ChequeRepository = None):
        self.cheque_repository = cheque_repository or ChequeRepository()
        logger.info("ChequeService initialized")
    
    def get_all_cheques(self, banque_id: Optional[int] = None) -> List[Dict]:
        """Get all cheques with formatted data"""
        cheques = self.cheque_repository.get_all_cheques(banque_id)
        
        # Format dates and amounts for display
        for cheque in cheques:
            try:
                statut = cheque.get('statut')
                montant = cheque.get('montant')
                if statut == 'encours':
                    cheque['montant_formatted'] = "-"
                else:
                    cheque['montant_formatted'] = f"{(montant or 0):,.3f} TND"
            except Exception:
                cheque['montant_formatted'] = f"{cheque.get('montant', 0):,.3f} TND"
            cheque['date_formatted'] = self._format_date(cheque['date_cheque'])
            cheque['statut_formatted'] = self._format_status(cheque['statut'])
            cheque['color_tag'] = self._get_status_color(cheque['statut'])
        
        return cheques
    
    def create_cheque(self, numero_cheque: int, banque_id: int, date_cheque: str,
                     montant: float, fournisseur: str, beneficiaire: str = '',
                     notes: str = '') -> Dict:
        """Create a new cheque with validation"""
        try:
            # Validate cheque number availability
            availability = self.check_cheque_availability(banque_id)
            if availability.get('needs_config'):
                return {
                    'success': False,
                    'error': 'Configuration du carnet de chèques requise pour cette banque'
                }
            
            # Check if cheque number is already used
            existing_cheques = self.cheque_repository.get_all_cheques(banque_id)
            used_numbers = [c['numero_cheque'] for c in existing_cheques 
                           if c['statut'] != 'annule']
            
            if numero_cheque in used_numbers:
                return {
                    'success': False,
                    'error': f'Le numéro de chèque {numero_cheque} est déjà utilisé'
                }
            
            # Validate cheque number doesn't exceed carnet limit
            config = self.cheque_repository.get_cheque_config(banque_id)
            if config and numero_cheque > config['carne_dernier_numero']:
                return {
                    'success': False,
                    'error': f'Le numéro {numero_cheque} dépasse la limite du carnet ({config["carne_dernier_numero"]})'
                }
            
            # Validate amount
            if montant <= 0:
                return {
                    'success': False,
                    'error': 'Le montant doit être supérieur à 0'
                }
            
            # Create cheque
            cheque_data = {
                'numero_cheque': numero_cheque,
                'banque_id': banque_id,
                'date_cheque': date_cheque,
                'montant': montant,
                'fournisseur': fournisseur.strip(),
                'beneficiaire': beneficiaire.strip(),
                'statut': 'emis',
                'notes': notes.strip()
            }
            
            cheque_id = self.cheque_repository.create_cheque(cheque_data)
            
            return {
                'success': True,
                'cheque_id': cheque_id,
                'message': f'Chèque #{numero_cheque} créé avec succès'
            }
            
        except Exception as e:
            logger.error(f"Error creating cheque: {e}")
            return {
                'success': False,
                'error': f'Erreur lors de la création du chèque: {str(e)}'
            }
    
    def annuler_cheque(self, cheque_id: int, motif: str = '') -> Dict:
        """Cancel a cheque"""
        try:
            success = self.cheque_repository.annuler_cheque(cheque_id, motif)
            
            if success:
                return {
                    'success': True,
                    'message': 'Chèque annulé avec succès'
                }
            else:
                return {
                    'success': False,
                    'error': 'Impossible d\'annuler le chèque'
                }
                
        except Exception as e:
            logger.error(f"Error cancelling cheque {cheque_id}: {e}")
            return {
                'success': False,
                'error': f'Erreur lors de l\'annulation: {str(e)}'
            }

    def marquer_encaisse(self, cheque_id: int) -> Dict:
        """Mark a cheque as cashed"""
        try:
            success = self.cheque_repository.update_cheque(cheque_id, {'statut': 'encaisse'})
            if success:
                return {'success': True, 'message': 'Chèque marqué comme encaissé'}
            return {'success': False, 'error': "Impossible de marquer le chèque comme encaissé"}
        except Exception as e:
            logger.error(f"Error marking cheque {cheque_id} cashed: {e}")
            return {'success': False, 'error': f"Erreur: {str(e)}"}
    
    def configure_cheque_carnet(self, banque_id: int, carne_dernier_numero: int, 
                               mini_cheque_alert: int = 10) -> Dict:
        """Configure cheque carnet for a bank"""
        try:
            if carne_dernier_numero <= 0:
                return {
                    'success': False,
                    'error': 'Le dernier numéro du carnet doit être supérieur à 0'
                }
            
            if mini_cheque_alert < 1 or mini_cheque_alert > 50:
                return {
                    'success': False,
                    'error': 'L\'alerte mini chèque doit être entre 1 et 50'
                }
            
            success = self.cheque_repository.set_cheque_config(
                banque_id, carne_dernier_numero, mini_cheque_alert
            )
            
            if success:
                return {
                    'success': True,
                    'message': 'Configuration du carnet mise à jour'
                }
            else:
                return {
                    'success': False,
                    'error': 'Erreur lors de la configuration'
                }
                
        except Exception as e:
            logger.error(f"Error configuring cheque carnet: {e}")
            return {
                'success': False,
                'error': f'Erreur: {str(e)}'
            }
    
    def check_cheque_availability(self, banque_id: int) -> Dict:
        """Check cheque availability and generate alerts"""
        availability = self.cheque_repository.check_cheque_availability(banque_id)
        
        if availability.get('need_alert'):
            remaining = availability['cheques_remaining']
            availability['alert_message'] = (
                f"⚠️ Attention: Il ne reste que {remaining} chèques dans votre carnet. "
                f"Pensez à commander un nouveau carnet."
            )
        
        return availability
    
    def get_cheque_statistics(self, banque_id: int) -> Dict:
        """Get cheque statistics for a bank"""
        all_cheques = self.cheque_repository.get_all_cheques(banque_id)
        
        stats = {
            'total_cheques': len(all_cheques),
            'cheques_emis': len([c for c in all_cheques if c['statut'] == 'emis']),
            'cheques_annules': len([c for c in all_cheques if c['statut'] == 'annule']),
            'cheques_encaisses': len([c for c in all_cheques if c['statut'] == 'encaisse']),
            'montant_total': sum(c['montant'] for c in all_cheques if c['statut'] != 'annule'),
            'montant_annule': sum(c['montant'] for c in all_cheques if c['statut'] == 'annule')
        }
        
        # Format amounts
        stats['montant_total_formatted'] = f"{stats['montant_total']:,.3f} TND"
        stats['montant_annule_formatted'] = f"{stats['montant_annule']:,.3f} TND"
        
        # Get missing numbers
        stats['missing_numbers'] = self.cheque_repository.get_missing_cheque_numbers(banque_id)
        stats['has_missing_numbers'] = len(stats['missing_numbers']) > 0
        
        return stats
    
    def get_next_cheque_suggestion(self, banque_id: int) -> Dict:
        """Get suggested next cheque number"""
        availability = self.check_cheque_availability(banque_id)
        
        if availability.get('needs_config'):
            return {
                'needs_config': True,
                'message': 'Configuration du carnet requise'
            }
        
        # Check for missing numbers first (to fill gaps)
        missing_numbers = self.cheque_repository.get_missing_cheque_numbers(banque_id)
        
        if missing_numbers:
            suggested_number = min(missing_numbers)
            return {
                'needs_config': False,
                'suggested_number': suggested_number,
                'is_filling_gap': True,
                'message': f'Numéro suggéré: {suggested_number} (comble un trou dans la séquence)'
            }
        else:
            suggested_number = availability['next_number']
            return {
                'needs_config': False,
                'suggested_number': suggested_number,
                'is_filling_gap': False,
                'message': f'Numéro suggéré: {suggested_number} (séquence normale)'
            }
    
    def _format_date(self, date_str: str) -> str:
        """Format date for display"""
        try:
            if isinstance(date_str, str):
                date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            else:
                date_obj = date_str
            return date_obj.strftime('%d/%m/%Y')
        except:
            return str(date_str)
    
    def _format_status(self, statut: str) -> str:
        """Format status for display"""
        status_map = {
            'emis': 'Émis',
            'annule': 'Annulé',
            'encaisse': 'Encaissé',
            'encours': 'En cours'
        }
        return status_map.get(statut, statut.capitalize())
    
    def _get_status_color(self, statut: str) -> str:
        """Get color tag for status"""
        color_map = {
            'emis': 'normal',
            'annule': 'cancelled',
            'encaisse': 'paid',
            'encours': 'pending'
        }
        return color_map.get(statut, 'normal')
    
    def import_outgoing_cheques_from_bank(self, banque_id: Optional[int] = None) -> Dict:
        """Import outgoing cheques from bank transactions automatically"""
        try:
            logger.info("Starting automatic import of outgoing cheques from bank")
            
            # Get outgoing cheques from bank data
            bank_cheques = self.cheque_repository.get_outgoing_cheques_from_bank(banque_id)
            
            if not bank_cheques:
                return {
                    'success': True,
                    'imported': 0,
                    'message': 'Aucun chèque sortant trouvé dans les transactions bancaires'
                }
            
            # Get existing cheques to avoid duplicates
            existing_cheques = self.cheque_repository.get_all_cheques(banque_id)
            existing_numbers = {}
            
            for cheque in existing_cheques:
                bank_id = cheque['banque_id']
                cheque_num = cheque['numero_cheque']
                if bank_id not in existing_numbers:
                    existing_numbers[bank_id] = set()
                existing_numbers[bank_id].add(cheque_num)
            
            imported_count = 0
            skipped_count = 0
            errors = []
            
            for bank_cheque in bank_cheques:
                try:
                    bank_id = bank_cheque['banque_id']
                    cheque_num = bank_cheque['numero_cheque']
                    
                    # Skip if cheque number is empty or already exists
                    if not cheque_num or cheque_num in ['.', '', 'None']:
                        skipped_count += 1
                        continue
                    
                    # Convert cheque number to int if possible
                    try:
                        cheque_num = int(cheque_num)
                    except (ValueError, TypeError):
                        skipped_count += 1
                        continue
                    
                    # Check if already exists
                    if bank_id in existing_numbers and cheque_num in existing_numbers[bank_id]:
                        skipped_count += 1
                        continue
                    
                    # Import the cheque
                    cheque_data = {
                        'numero_cheque': cheque_num,
                        'banque_id': bank_id,
                        'date_cheque': self._normalize_bank_date(bank_cheque['date_transaction']),
                        'montant': abs(float(bank_cheque['montant'])),  # Make sure it's positive
                        'fournisseur': bank_cheque['nom_client'] or 'Importé de la banque',
                        'beneficiaire': bank_cheque['nom_client'] or '',
                        'statut': 'emis',  # Default status
                        'notes': f"Importé automatiquement depuis transaction bancaire #{bank_cheque['transaction_id']}",
                        'bank_transaction_id': bank_cheque['transaction_id']
                    }
                    
                    cheque_id = self.cheque_repository.create_cheque(cheque_data)
                    
                    if cheque_id:
                        imported_count += 1
                        # Add to existing numbers to avoid duplicates in same batch
                        if bank_id not in existing_numbers:
                            existing_numbers[bank_id] = set()
                        existing_numbers[bank_id].add(cheque_num)
                        
                        logger.info(f"Imported cheque #{cheque_num} from bank transaction #{bank_cheque['transaction_id']}")
                    else:
                        errors.append(f"Failed to create cheque #{cheque_num}")
                        
                except Exception as cheque_error:
                    errors.append(f"Error importing cheque #{cheque_num}: {str(cheque_error)}")
                    logger.error(f"Error importing cheque: {cheque_error}")
            
            # Prepare result message
            message_parts = []
            if imported_count > 0:
                message_parts.append(f"{imported_count} chèques importés avec succès")
            if skipped_count > 0:
                message_parts.append(f"{skipped_count} chèques ignorés (déjà existants ou numéro invalide)")
            if errors:
                message_parts.append(f"{len(errors)} erreurs")
            
            result_message = " - ".join(message_parts) if message_parts else "Aucun chèque à importer"
            
            return {
                'success': True,
                'imported': imported_count,
                'skipped': skipped_count,
                'errors': errors,
                'message': result_message,
                'details': {
                    'total_found': len(bank_cheques),
                    'imported': imported_count,
                    'skipped': skipped_count,
                    'errors': len(errors)
                }
            }
            
        except Exception as e:
            logger.error(f"Error in automatic cheque import: {e}")
            return {
                'success': False,
                'imported': 0,
                'error': f'Erreur lors de l\'importation automatique: {str(e)}'
            }

    def creer_cheque_encours(self, numero_cheque: int, banque_id: int, date_cheque: str, fournisseur: str, notes: str = '') -> Dict:
        """Create a cheque with unknown amount (encours)"""
        try:
            cheque_data = {
                'numero_cheque': numero_cheque,
                'banque_id': banque_id,
                'date_cheque': date_cheque,
                'montant': 0.0,
                'fournisseur': fournisseur.strip(),
                'beneficiaire': '',
                'statut': 'encours',
                'notes': notes.strip()
            }
            cheque_id = self.cheque_repository.create_cheque(cheque_data)
            return {'success': True, 'cheque_id': cheque_id, 'message': f'Chèque #{numero_cheque} créé en cours'}
        except Exception as e:
            logger.error(f"Error creating encours cheque: {e}")
            return {'success': False, 'error': f"Erreur: {str(e)}"}

    def sync_with_bank(self, banque_id: Optional[int] = None) -> Dict:
        """Synchronize cheque data with bank transactions."""
        try:
            return self.cheque_repository.sync_with_bank_transactions(banque_id)
        except Exception as e:
            logger.error(f"Error syncing cheques with bank: {e}")
            return {'updated': 0, 'linked': 0, 'annule_from_delete': 0, 'imported': 0}
    
    def _normalize_bank_date(self, date_str: str) -> str:
        """Normalize bank transaction date to YYYY-MM-DD format"""
        try:
            # Handle different date formats from bank data
            if '/' in date_str:
                # Format: DD/MM/YYYY or MM/DD/YYYY
                parts = date_str.split('/')
                if len(parts) == 3:
                    if int(parts[2]) > 2000:  # YYYY at the end
                        if int(parts[0]) > 12:  # DD/MM/YYYY
                            return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
                        else:  # MM/DD/YYYY
                            return f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"
            
            # Already in YYYY-MM-DD format
            if '-' in date_str and len(date_str) == 10:
                return date_str
            
            # Default fallback
            return datetime.now().strftime('%Y-%m-%d')
            
        except Exception:
            return datetime.now().strftime('%Y-%m-%d')