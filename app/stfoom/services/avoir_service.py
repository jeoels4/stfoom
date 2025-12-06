"""
Avoir Service
============
Business logic service for avoir (credit note) management.
"""
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, date, timedelta
from decimal import Decimal

from ..data.avoir_repository import AvoirRepository

class AvoirService:
    """Service for avoir management business logic."""
    
    def __init__(self):
        self.avoir_repo = AvoirRepository()
    
    def create_avoir(self, client_nom: str, montant: float, type_avoir: str, 
                    reference_originale: str, createur: str = "", **kwargs) -> Tuple[bool, str, Optional[int]]:
        """
        Create a new avoir.
        
        Args:
            client_nom: Client name
            montant: Amount
            type_avoir: Type of avoir
            reference_originale: Original reference
            createur: Creator of the avoir
            **kwargs: Additional avoir fields
            
        Returns:
            Tuple of (success, message, avoir_id)
        """
        # Validate business rules
        if montant <= 0:
            return False, "Amount must be greater than 0", None
        
        valid_types = ["retour", "defaut", "remise", "erreur", "autre"]
        if type_avoir not in valid_types:
            return False, f"Invalid avoir type. Must be one of: {', '.join(valid_types)}", None
        
        # Generate avoir number if not provided
        if "numero_avoir" not in kwargs or not kwargs["numero_avoir"]:
            kwargs["numero_avoir"] = self._generate_avoir_number()
        
        # Set default expiration date if not provided (1 year from now)
        if "date_expiration" not in kwargs:
            kwargs["date_expiration"] = date.today() + timedelta(days=365)
        
        # Create the avoir
        avoir_id = self.avoir_repo.create_avoir(
            client_nom=client_nom,
            montant=montant,
            type_avoir=type_avoir,
            reference_originale=reference_originale,
            createur=createur,
            **kwargs
        )
        
        if avoir_id:
            return True, f"Avoir created successfully with ID: {avoir_id}", avoir_id
        else:
            return False, "Failed to create avoir", None
    
    def use_avoir_credit(self, client_nom: str, amount_requested: float, 
                        used_by: str = "") -> Tuple[bool, str, List[Dict[str, Any]]]:
        """
        Use credit from client's avoirs.
        
        Args:
            client_nom: Client name
            amount_requested: Amount to use
            used_by: Who is using the credit
            
        Returns:
            Tuple of (success, message, list_of_used_avoirs)
        """
        if amount_requested <= 0:
            return False, "Amount must be greater than 0", []
        
        # Get available credit balance
        available_credit = self.get_client_credit_balance(client_nom)
        if available_credit < amount_requested:
            return False, f"Insufficient credit. Available: {available_credit:.3f}, Requested: {amount_requested:.3f}", []
        
        # Get active avoirs for the client, sorted by creation date (FIFO)
        active_avoirs = self.avoir_repo.get_active_avoirs_by_client(client_nom)
        
        # Filter out expired avoirs and sort by creation date
        valid_avoirs = []
        today = date.today()
        
        for avoir in active_avoirs:
            # Check expiration
            if avoir.get("date_expiration"):
                exp_date = avoir["date_expiration"]
                if isinstance(exp_date, datetime):
                    exp_date = exp_date.date()
                if exp_date < today:
                    continue  # Skip expired
            
            # Check available amount
            available = avoir["montant"] - avoir.get("montant_utilise", 0.0)
            if available > 0:
                valid_avoirs.append(avoir)
        
        # Sort by creation date (FIFO)
        valid_avoirs.sort(key=lambda x: x["date_creation"])
        
        # Use avoirs in FIFO order
        remaining_amount = amount_requested
        used_avoirs = []
        
        for avoir in valid_avoirs:
            if remaining_amount <= 0:
                break
            
            available = avoir["montant"] - avoir.get("montant_utilise", 0.0)
            amount_to_use = min(remaining_amount, available)
            
            success = self.avoir_repo.use_avoir_credit(avoir["id"], amount_to_use)
            if success:
                used_avoirs.append({
                    "avoir_id": avoir["id"],
                    "numero_avoir": avoir.get("numero_avoir", ""),
                    "amount_used": amount_to_use,
                    "remaining_credit": available - amount_to_use
                })
                remaining_amount -= amount_to_use
            else:
                # If we fail to use an avoir, rollback previous uses
                self._rollback_avoir_usage(used_avoirs)
                return False, f"Failed to use avoir {avoir['id']}", []
        
        if remaining_amount > 0:
            # Shouldn't happen due to earlier check, but safety net
            self._rollback_avoir_usage(used_avoirs)
            return False, "Unable to complete credit usage", []
        
        return True, f"Successfully used {amount_requested:.3f} credit from {len(used_avoirs)} avoir(s)", used_avoirs
    
    def get_client_credit_balance(self, client_nom: str) -> float:
        """Get total available credit balance for a client."""
        return self.avoir_repo.get_client_credit_balance(client_nom)
    
    def get_client_avoirs(self, client_nom: str, include_inactive: bool = False) -> List[Dict[str, Any]]:
        """Get avoirs for a client."""
        if include_inactive:
            return self.avoir_repo.get_avoirs_by_client(client_nom)
        else:
            return self.avoir_repo.get_active_avoirs_by_client(client_nom)
    
    def get_expiring_avoirs(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get avoirs expiring within specified days."""
        return self.avoir_repo.get_expiring_avoirs(days_ahead)
    
    def cancel_avoir(self, avoir_id: int, reason: str, cancelled_by: str = "") -> Tuple[bool, str]:
        """Cancel an avoir."""
        avoir = self.avoir_repo.get_by_id(avoir_id)
        if not avoir:
            return False, "Avoir not found"
        
        if avoir.get("statut") != "actif":
            return False, f"Cannot cancel avoir with status '{avoir.get('statut')}'"
        
        # Check if any amount has been used
        montant_utilise = avoir.get("montant_utilise", 0.0)
        if montant_utilise > 0:
            return False, f"Cannot cancel avoir that has been partially used (used: {montant_utilise:.3f})"
        
        # Cancel the avoir
        cancel_reason = f"Cancelled by {cancelled_by}: {reason}" if cancelled_by else reason
        success = self.avoir_repo.cancel_avoir(avoir_id, cancel_reason)
        
        if success:
            return True, "Avoir cancelled successfully"
        else:
            return False, "Failed to cancel avoir"
    
    def search_avoirs(self, search_term: str) -> List[Dict[str, Any]]:
        """Search avoirs by various criteria."""
        return self.avoir_repo.search_avoirs(search_term)
    
    def get_avoir_statistics(self) -> Dict[str, Any]:
        """Get comprehensive avoir statistics."""
        stats = self.avoir_repo.get_avoir_statistics()
        
        # Add business insights
        today = date.today()
        
        # Get expiring avoirs
        expiring_soon = self.get_expiring_avoirs(30)
        expiring_this_week = self.get_expiring_avoirs(7)
        
        stats.update({
            "expiring_soon_count": len(expiring_soon),
            "expiring_this_week_count": len(expiring_this_week),
            "available_credit": stats["total_amount"] - stats["total_used"]
        })
        
        return stats
    
    def validate_avoir_data(self, avoir_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate avoir data and return any errors."""
        errors = []
        
        # Required fields
        required_fields = ["client_nom", "montant", "type_avoir", "reference_originale"]
        for field in required_fields:
            if field not in avoir_data or not avoir_data[field]:
                errors.append(f"Missing required field: {field}")
        
        # Amount validation
        try:
            montant = float(avoir_data.get("montant", 0))
            if montant <= 0:
                errors.append("Amount must be greater than 0")
        except (ValueError, TypeError):
            errors.append("Invalid amount format")
        
        # Type validation
        valid_types = ["retour", "defaut", "remise", "erreur", "autre"]
        if avoir_data.get("type_avoir") not in valid_types:
            errors.append(f"Invalid avoir type. Must be one of: {', '.join(valid_types)}")
        
        # Date validation
        if "date_expiration" in avoir_data and avoir_data["date_expiration"]:
            try:
                exp_date = avoir_data["date_expiration"]
                if isinstance(exp_date, str):
                    exp_date = datetime.strptime(exp_date, "%Y-%m-%d").date()
                
                if exp_date <= date.today():
                    errors.append("Expiration date must be in the future")
            except ValueError:
                errors.append("Invalid expiration date format (use YYYY-MM-DD)")
        
        return len(errors) == 0, errors
    
    def update_avoir(self, avoir_id: int, update_data: Dict[str, Any], updated_by: str = "") -> Tuple[bool, str]:
        """Update avoir information."""
        # Get current avoir
        avoir = self.avoir_repo.get_by_id(avoir_id)
        if not avoir:
            return False, "Avoir not found"
        
        # Check if avoir can be modified
        if avoir.get("statut") not in ["actif"]:
            return False, f"Cannot modify avoir with status '{avoir.get('statut')}'"
        
        # Don't allow modification of amount if already used
        if "montant" in update_data:
            montant_utilise = avoir.get("montant_utilise", 0.0)
            if montant_utilise > 0:
                return False, "Cannot modify amount of avoir that has been used"
        
        # Validate update data
        is_valid, errors = self.validate_avoir_data({**avoir, **update_data})
        if not is_valid:
            return False, f"Validation errors: {'; '.join(errors)}"
        
        # Add audit trail
        if updated_by:
            notes = avoir.get("notes", "")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
            audit_note = f"\n[{timestamp}] Updated by {updated_by}"
            update_data["notes"] = notes + audit_note
        
        update_data["updated_at"] = datetime.now().isoformat()
        
        # Update the avoir
        success = self.avoir_repo.update(avoir_id, update_data)
        
        if success:
            return True, "Avoir updated successfully"
        else:
            return False, "Failed to update avoir"
    
    def get_client_credit_history(self, client_nom: str, days: int = 90) -> Dict[str, Any]:
        """Get credit history for a client."""
        avoirs = self.get_client_avoirs(client_nom, include_inactive=True)
        
        # Filter by date range
        cutoff_date = date.today() - timedelta(days=days)
        recent_avoirs = []
        
        for avoir in avoirs:
            creation_date = avoir["date_creation"]
            if isinstance(creation_date, datetime):
                creation_date = creation_date.date()
            
            if creation_date >= cutoff_date:
                recent_avoirs.append(avoir)
        
        # Calculate summary
        total_created = sum(avoir["montant"] for avoir in recent_avoirs)
        total_used = sum(avoir.get("montant_utilise", 0.0) for avoir in recent_avoirs)
        current_balance = self.get_client_credit_balance(client_nom)
        
        return {
            "client_nom": client_nom,
            "period_days": days,
            "avoirs_created": len(recent_avoirs),
            "total_credit_created": total_created,
            "total_credit_used": total_used,
            "current_balance": current_balance,
            "avoirs": recent_avoirs
        }
    
    def _generate_avoir_number(self) -> str:
        """Generate a unique avoir number."""
        today = date.today()
        prefix = f"AV{today.strftime('%Y%m')}"
        
        # Get count of avoirs created today (simple approach)
        # In production, you might want a more sophisticated numbering system
        timestamp = datetime.now().strftime("%d%H%M")
        return f"{prefix}{timestamp}"
    
    def _rollback_avoir_usage(self, used_avoirs: List[Dict[str, Any]]) -> None:
        """Rollback avoir usage in case of failure."""
        for usage in used_avoirs:
            avoir_id = usage["avoir_id"]
            amount_used = usage["amount_used"]
            
            # Get current avoir
            avoir = self.avoir_repo.get_by_id(avoir_id)
            if avoir:
                current_used = avoir.get("montant_utilise", 0.0)
                new_used = max(0.0, current_used - amount_used)
                
                update_data = {"montant_utilise": new_used}
                
                # If it was marked as fully used, reactivate it
                if avoir.get("statut") == "utilise" and new_used < avoir["montant"]:
                    update_data["statut"] = "actif"
                
                self.avoir_repo.update(avoir_id, update_data)
