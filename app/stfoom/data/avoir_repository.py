"""
Avoir Repository
===============
Repository for avoir (credit note) data access operations.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date
from decimal import Decimal

from .base_repository import BaseRepository
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)

class AvoirRepository(BaseRepository):
    """Repository for avoir data access operations."""
    
    def __init__(self):
        super().__init__("avoirs")
    
    def get_entity_name(self) -> str:
        return "Avoir"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate avoir data before database operations."""
        required_fields = ["client_nom", "montant", "type_avoir", "reference_originale"]
        
        # Check required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                print(f"[AVOIR_REPO] Missing required field: {field}")
                return False
        
        # Validate numeric fields
        try:
            montant = float(data["montant"])
            if montant <= 0:
                print(f"[AVOIR_REPO] Invalid amount: {montant}")
                return False
                
        except (ValueError, TypeError) as e:
            print(f"[AVOIR_REPO] Invalid amount: {e}")
            return False
        
        # Validate type_avoir
        valid_types = ["retour", "defaut", "remise", "erreur", "autre"]
        if data["type_avoir"] not in valid_types:
            print(f"[AVOIR_REPO] Invalid avoir type: {data['type_avoir']}")
            return False
        
        return True
    
    def transform_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform avoir data before storing in database."""
        transformed = data.copy()
        
        # Ensure numeric fields are properly formatted
        if "montant" in transformed:
            transformed["montant"] = float(transformed["montant"])
        
        if "montant_utilise" in transformed:
            transformed["montant_utilise"] = float(transformed["montant_utilise"])
        else:
            transformed["montant_utilise"] = 0.0
        
        # Handle date fields
        if "date_creation" in transformed and isinstance(transformed["date_creation"], date):
            transformed["date_creation"] = transformed["date_creation"].isoformat()
        elif "date_creation" not in transformed:
            transformed["date_creation"] = date.today().isoformat()
        
        if "date_expiration" in transformed and isinstance(transformed["date_expiration"], date):
            transformed["date_expiration"] = transformed["date_expiration"].isoformat()
        
        # Set creation timestamp
        if "created_at" not in transformed:
            transformed["created_at"] = datetime.now().isoformat()
        
        # Default values
        transformed["statut"] = transformed.get("statut", "actif")
        transformed["notes"] = transformed.get("notes", "")
        
        return transformed
    
    def transform_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform avoir data after retrieving from database."""
        transformed = data.copy()
        
        # Parse date fields
        for field in ["date_creation", "date_expiration", "created_at", "updated_at"]:
            if field in transformed and transformed[field]:
                try:
                    if "T" in str(transformed[field]):  # Datetime
                        transformed[field] = datetime.fromisoformat(transformed[field])
                    else:  # Date only
                        transformed[field] = date.fromisoformat(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = None
        
        # Ensure numeric fields are proper types
        for field in ["montant", "montant_utilise"]:
            if field in transformed and transformed[field] is not None:
                try:
                    transformed[field] = float(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = 0.0
        
        return transformed
    
    def create_avoir(self, client_nom: str, montant: float, type_avoir: str, 
                     reference_originale: str, **kwargs) -> Optional[int]:
        """
        Create a new avoir.
        
        Args:
            client_nom: Client name
            montant: Amount
            type_avoir: Type of avoir
            reference_originale: Original reference
            **kwargs: Additional avoir fields
            
        Returns:
            ID of created avoir or None if failed
        """
        avoir_data = {
            "client_nom": client_nom,
            "montant": montant,
            "montant_utilise": 0.0,
            "type_avoir": type_avoir,
            "reference_originale": reference_originale,
            "date_creation": kwargs.get("date_creation", date.today()),
            "date_expiration": kwargs.get("date_expiration"),
            "statut": kwargs.get("statut", "actif"),
            "notes": kwargs.get("notes", ""),
            "createur": kwargs.get("createur", ""),
            "numero_avoir": kwargs.get("numero_avoir", "")
        }
        
        # Add any additional fields
        avoir_data.update({k: v for k, v in kwargs.items() 
                          if k not in avoir_data})
        
        if not self.validate_data(avoir_data):
            return None
        
        avoir_data = self.transform_for_storage(avoir_data)
        if self.create(avoir_data):
            # Get the last inserted ID
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT last_insert_rowid()")
            return cursor.fetchone()[0]
        
        return None
    
    def get_avoirs_by_client(self, client_nom: str) -> List[Dict[str, Any]]:
        """Get all avoirs for a specific client."""
        avoirs = self.find_by(client_nom=client_nom)
        return [self.transform_from_storage(avoir) for avoir in avoirs]
    
    def get_active_avoirs_by_client(self, client_nom: str) -> List[Dict[str, Any]]:
        """Get active avoirs for a specific client."""
        avoirs = self.find_by(client_nom=client_nom, statut="actif")
        return [self.transform_from_storage(avoir) for avoir in avoirs]
    
    def get_client_credit_balance(self, client_nom: str) -> float:
        """Get total available credit balance for a client."""
        active_avoirs = self.get_active_avoirs_by_client(client_nom)
        
        total_credit = 0.0
        for avoir in active_avoirs:
            # Check if not expired
            if avoir.get("date_expiration"):
                if isinstance(avoir["date_expiration"], date):
                    if avoir["date_expiration"] < date.today():
                        continue
                elif isinstance(avoir["date_expiration"], datetime):
                    if avoir["date_expiration"].date() < date.today():
                        continue
            
            available = avoir["montant"] - avoir.get("montant_utilise", 0.0)
            if available > 0:
                total_credit += available
        
        return total_credit
    
    def use_avoir_credit(self, avoir_id: int, amount_to_use: float) -> bool:
        """
        Use credit from an avoir.
        
        Args:
            avoir_id: ID of the avoir
            amount_to_use: Amount to use from the avoir
            
        Returns:
            True if successful, False otherwise
        """
        avoir = self.get_by_id(avoir_id)
        if not avoir:
            print(f"[AVOIR_REPO] Avoir not found: {avoir_id}")
            return False
        
        # Check if avoir is active
        if avoir.get("statut") != "actif":
            print(f"[AVOIR_REPO] Avoir not active: {avoir_id}")
            return False
        
        # Check expiration
        if avoir.get("date_expiration"):
            exp_date = avoir["date_expiration"]
            if isinstance(exp_date, datetime):
                exp_date = exp_date.date()
            if exp_date < date.today():
                print(f"[AVOIR_REPO] Avoir expired: {avoir_id}")
                return False
        
        # Check available amount
        montant_utilise = avoir.get("montant_utilise", 0.0)
        available = avoir["montant"] - montant_utilise
        
        if amount_to_use > available:
            print(f"[AVOIR_REPO] Insufficient credit. Available: {available}, Requested: {amount_to_use}")
            return False
        
        # Update the avoir
        new_montant_utilise = montant_utilise + amount_to_use
        update_data = {
            "montant_utilise": new_montant_utilise,
            "updated_at": datetime.now().isoformat()
        }
        
        # If fully used, mark as used
        if new_montant_utilise >= avoir["montant"]:
            update_data["statut"] = "utilise"
        
        return self.update(avoir_id, update_data)
    
    def cancel_avoir(self, avoir_id: int, reason: str = "") -> bool:
        """Cancel an avoir."""
        update_data = {
            "statut": "annule",
            "updated_at": datetime.now().isoformat()
        }
        
        if reason:
            avoir = self.get_by_id(avoir_id)
            if avoir:
                existing_notes = avoir.get("notes", "")
                update_data["notes"] = f"{existing_notes}\nAnnulé: {reason}".strip()
        
        return self.update(avoir_id, update_data)
    
    def get_expiring_avoirs(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get avoirs expiring within specified days."""
        from datetime import timedelta
        
        cutoff_date = date.today() + timedelta(days=days_ahead)
        
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE statut = 'actif' 
          AND date_expiration IS NOT NULL 
          AND date_expiration <= ?
        ORDER BY date_expiration ASC
        """
        
        try:
            cursor.execute(query, (cutoff_date.isoformat(),))
            results = cursor.fetchall()
            
            if results:
                columns = [description[0] for description in cursor.description]
                avoirs = [dict(zip(columns, row)) for row in results]
                return [self.transform_from_storage(avoir) for avoir in avoirs]
            
            return []
            
        except Exception as e:
            print(f"[AVOIR_REPO] Error getting expiring avoirs: {e}")
            return []
    
    def get_avoir_usage_history(self, avoir_id: int) -> List[Dict[str, Any]]:
        """Get usage history for an avoir (if implemented in separate table)."""
        # This would require a separate avoir_usage table
        # For now, return empty list
        return []
    
    def search_avoirs(self, search_term: str) -> List[Dict[str, Any]]:
        """Search avoirs by client name, reference, or numero."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE client_nom LIKE ? 
           OR reference_originale LIKE ? 
           OR numero_avoir LIKE ?
           OR notes LIKE ?
        ORDER BY date_creation DESC
        """
        
        try:
            cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
            results = cursor.fetchall()
            
            if results:
                columns = [description[0] for description in cursor.description]
                avoirs = [dict(zip(columns, row)) for row in results]
                return [self.transform_from_storage(avoir) for avoir in avoirs]
            
            return []
            
        except Exception as e:
            print(f"[AVOIR_REPO] Error searching avoirs: {e}")
            return []
    
    def get_avoir_statistics(self) -> Dict[str, Any]:
        """Get general avoir statistics."""
        all_avoirs = self.get_all()
        if not all_avoirs:
            return {
                "total_avoirs": 0,
                "total_amount": 0.0,
                "total_used": 0.0,
                "active_count": 0,
                "expired_count": 0
            }
        
        total_amount = sum(avoir["montant"] for avoir in all_avoirs)
        total_used = sum(avoir.get("montant_utilise", 0.0) for avoir in all_avoirs)
        active_count = len([a for a in all_avoirs if a.get("statut") == "actif"])
        
        # Count expired
        today = date.today()
        expired_count = 0
        for avoir in all_avoirs:
            if avoir.get("date_expiration"):
                exp_date = avoir["date_expiration"]
                if isinstance(exp_date, datetime):
                    exp_date = exp_date.date()
                if exp_date < today:
                    expired_count += 1
        
        return {
            "total_avoirs": len(all_avoirs),
            "total_amount": total_amount,
            "total_used": total_used,
            "active_count": active_count,
            "expired_count": expired_count,
            "utilization_rate": (total_used / total_amount * 100) if total_amount > 0 else 0
        }
