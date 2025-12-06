"""
Vente Repository
===============
Repository for sales (ventes) data access operations.
"""
from typing import List, Dict, Optional, Any
from datetime import datetime, date, timedelta
from decimal import Decimal

from .base_repository import BaseRepository
from app.stfoom.utils.enhanced_logging import (
    log_create_action,
    log_update_action,
    log_delete_action,
    log_verification_action
)

class VenteRepository(BaseRepository):
    """Repository for sales data access operations."""
    
    def __init__(self):
        super().__init__("ventes")
    
    def get_entity_name(self) -> str:
        return "Vente"
    
    def validate_data(self, data: Dict[str, Any]) -> bool:
        """Validate vente data before database operations."""
        required_fields = ["client_nom", "produit", "quantite", "prix_unitaire", "total"]
        
        # Check required fields
        for field in required_fields:
            if field not in data or data[field] is None:
                print(f"[VENTE_REPO] Missing required field: {field}")
                return False
        
        # Validate numeric fields
        try:
            quantite = float(data["quantite"])
            prix_unitaire = float(data["prix_unitaire"])
            total = float(data["total"])
            
            if quantite <= 0:
                print(f"[VENTE_REPO] Invalid quantity: {quantite}")
                return False
            
            if prix_unitaire <= 0:
                print(f"[VENTE_REPO] Invalid unit price: {prix_unitaire}")
                return False
            
            if total <= 0:
                print(f"[VENTE_REPO] Invalid total: {total}")
                return False
                
        except (ValueError, TypeError) as e:
            print(f"[VENTE_REPO] Invalid numeric values: {e}")
            return False
        
        return True
    
    def get_all(self, limit: Optional[int] = None, offset: int = 0, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """
        Get all vente records ordered by nfacture (latest first).
        
        Args:
            limit: Maximum number of records to return
            offset: Number of records to skip
            include_deleted: If True, include soft-deleted records (default False)
            
        Returns:
            List of vente records ordered by nfacture DESC (latest first)
        """
        # Filter out soft-deleted records unless explicitly requested
        if include_deleted:
            sql = f"SELECT * FROM {self.table_name} ORDER BY nfacture DESC"
        else:
            sql = f"SELECT * FROM {self.table_name} WHERE (deleted IS NULL OR deleted = 0) ORDER BY nfacture DESC"
        
        if limit is not None:
            sql += f" LIMIT {limit} OFFSET {offset}"
        
        rows = self.execute_query(sql)
        return [dict(row) for row in rows]
    
    def transform_for_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform vente data before storing in database."""
        transformed = data.copy()
        
        # Ensure numeric fields are properly formatted
        if "quantite" in transformed:
            transformed["quantite"] = float(transformed["quantite"])
        
        if "prix_unitaire" in transformed:
            transformed["prix_unitaire"] = float(transformed["prix_unitaire"])
        
        if "total" in transformed:
            transformed["total"] = float(transformed["total"])
        
        # Handle date fields
        if "date_vente" in transformed and isinstance(transformed["date_vente"], date):
            transformed["date_vente"] = transformed["date_vente"].isoformat()
        elif "date_vente" not in transformed:
            transformed["date_vente"] = date.today().isoformat()
        
        # Set creation timestamp
        if "created_at" not in transformed:
            transformed["created_at"] = datetime.now().isoformat()
        
        # Default values
        transformed["statut"] = transformed.get("statut", "en_cours")
        transformed["notes"] = transformed.get("notes", "")
        
        return transformed
    
    def transform_from_storage(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform vente data after retrieving from database."""
        transformed = data.copy()
        
        # Parse date fields
        for field in ["date_vente", "created_at", "updated_at"]:
            if field in transformed and transformed[field]:
                try:
                    if "T" in str(transformed[field]):  # Datetime
                        transformed[field] = datetime.fromisoformat(transformed[field])
                    else:  # Date only
                        transformed[field] = date.fromisoformat(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = None
        
        # Ensure numeric fields are proper types
        for field in ["quantite", "prix_unitaire", "total"]:
            if field in transformed and transformed[field] is not None:
                try:
                    transformed[field] = float(transformed[field])
                except (ValueError, TypeError):
                    transformed[field] = 0.0
        
        return transformed
    
    def create_vente(self, client_nom: str, produit: str, quantite: float, 
                     prix_unitaire: float, **kwargs) -> Optional[int]:
        """
        Create a new vente.
        
        Args:
            client_nom: Client name
            produit: Product name
            quantite: Quantity
            prix_unitaire: Unit price
            **kwargs: Additional vente fields
            
        Returns:
            ID of created vente or None if failed
        """
        total = quantite * prix_unitaire
        
        vente_data = {
            "client_nom": client_nom,
            "produit": produit,
            "quantite": quantite,
            "prix_unitaire": prix_unitaire,
            "total": total,
            "date_vente": kwargs.get("date_vente", date.today()),
            "statut": kwargs.get("statut", "en_cours"),
            "notes": kwargs.get("notes", ""),
            "vendeur": kwargs.get("vendeur", ""),
            "mode_paiement": kwargs.get("mode_paiement", ""),
            "reference": kwargs.get("reference", "")
        }
        
        # Add any additional fields
        vente_data.update({k: v for k, v in kwargs.items() 
                          if k not in vente_data})
        
        if not self.validate_data(vente_data):
            return None
        
        vente_data = self.transform_for_storage(vente_data)
        if self.create(vente_data):
            # Get the last inserted ID
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT last_insert_rowid()")
            vente_id = cursor.fetchone()[0]
            
            # Log the vente creation
            log_create_action(
                module="vente",
                resource_type="vente",
                resource_id=vente_id,
                data={
                    "client": client_nom,
                    "produit": produit,
                    "quantite": quantite,
                    "montant": total,
                    "date": str(kwargs.get("date_vente", date.today()))
                }
            )
            
            return vente_id
        
        return None
    
    def get_ventes_by_client(self, client_nom: str) -> List[Dict[str, Any]]:
        """Get all ventes for a specific client."""
        ventes = self.find_by(client_nom=client_nom)
        return [self.transform_from_storage(vente) for vente in ventes]
    
    def get_ventes_by_date_range(self, start_date: date, end_date: date) -> List[Dict[str, Any]]:
        """Get ventes within a date range."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE date_vente BETWEEN ? AND ?
        ORDER BY date_vente DESC
        """
        
        try:
            cursor.execute(query, (start_date.isoformat(), end_date.isoformat()))
            results = cursor.fetchall()
            
            if results:
                columns = [description[0] for description in cursor.description]
                ventes = [dict(zip(columns, row)) for row in results]
                return [self.transform_from_storage(vente) for vente in ventes]
            
            return []
            
        except Exception as e:
            print(f"[VENTE_REPO] Error getting ventes by date range: {e}")
            return []
    
    def get_ventes_by_product(self, produit: str) -> List[Dict[str, Any]]:
        """Get all ventes for a specific product."""
        ventes = self.find_by(produit=produit)
        return [self.transform_from_storage(vente) for vente in ventes]
    
    def get_monthly_sales_summary(self, year: int, month: int) -> Dict[str, Any]:
        """Get sales summary for a specific month."""
        start_date = date(year, month, 1)
        if month == 12:
            end_date = date(year + 1, 1, 1)
        else:
            end_date = date(year, month + 1, 1)
        
        ventes = self.get_ventes_by_date_range(start_date, end_date)
        
        if not ventes:
            return {
                "total_ventes": 0,
                "total_amount": 0.0,
                "average_sale": 0.0,
                "top_client": None,
                "top_product": None
            }
        
        total_amount = sum(vente["total"] for vente in ventes)
        
        # Count by client
        client_totals = {}
        for vente in ventes:
            client = vente["client_nom"]
            client_totals[client] = client_totals.get(client, 0) + vente["total"]
        
        # Count by product
        product_totals = {}
        for vente in ventes:
            product = vente["produit"]
            product_totals[product] = product_totals.get(product, 0) + vente["total"]
        
        return {
            "total_ventes": len(ventes),
            "total_amount": total_amount,
            "average_sale": total_amount / len(ventes),
            "top_client": max(client_totals.items(), key=lambda x: x[1])[0] if client_totals else None,
            "top_product": max(product_totals.items(), key=lambda x: x[1])[0] if product_totals else None
        }
    
    def update_vente_status(self, vente_id: int, new_status: str) -> bool:
        """Update the status of a vente."""
        valid_statuses = ["en_cours", "confirmee", "livree", "payee", "annulee"]
        
        if new_status not in valid_statuses:
            print(f"[VENTE_REPO] Invalid status: {new_status}")
            return False
        
        update_data = {
            "statut": new_status,
            "updated_at": datetime.now().isoformat()
        }
        
        return self.update(vente_id, update_data)
    
    def search_ventes(self, search_term: str) -> List[Dict[str, Any]]:
        """Search ventes by client name, product, or reference."""
        conn = self._get_connection()
        cursor = conn.cursor()
        
        search_pattern = f"%{search_term}%"
        query = f"""
        SELECT * FROM {self.table_name} 
        WHERE client_nom LIKE ? 
           OR produit LIKE ? 
           OR reference LIKE ?
           OR notes LIKE ?
        ORDER BY date_vente DESC
        """
        
        try:
            cursor.execute(query, (search_pattern, search_pattern, search_pattern, search_pattern))
            results = cursor.fetchall()
            
            if results:
                columns = [description[0] for description in cursor.description]
                ventes = [dict(zip(columns, row)) for row in results]
                return [self.transform_from_storage(vente) for vente in ventes]
            
            return []
            
        except Exception as e:
            print(f"[VENTE_REPO] Error searching ventes: {e}")
            return []
    
    def get_pending_ventes(self) -> List[Dict[str, Any]]:
        """Get all pending/in-progress ventes."""
        ventes = self.find_by(statut="en_cours")
        return [self.transform_from_storage(vente) for vente in ventes]
