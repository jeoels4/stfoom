"""
Data Models
===========
Domain models for STFOOM entities.
"""
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class User:
    """User domain model."""
    id: int = 0
    username: str = ""
    full_name: str = ""
    rank: str = ""
    email: str = ""
    is_active: bool = True
    created_at: Optional[datetime] = None
    last_login: Optional[datetime] = None
    failed_attempts: int = 0
    locked_until: Optional[datetime] = None
    force_password_change: bool = False
    temporary_password: bool = False
    password_changed_at: Optional[datetime] = None

@dataclass
class Sale:
    """Sale/Vente domain model."""
    id: int = 0
    nfacture: str = ""
    date: str = ""
    client: str = ""
    tva: float = 0.0
    remise: float = 0.0
    total: float = 0.0
    payment_status: str = "non payé"
    
@dataclass  
class Purchase:
    """Purchase/Achat domain model."""
    id: int = 0
    date: str = ""
    fournisseur: str = ""
    num_facture: str = ""
    montant: float = 0.0
    tva: float = 0.0
    total: float = 0.0
