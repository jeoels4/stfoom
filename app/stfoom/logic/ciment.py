"""
Ciment logic backed by SQLite database
=====================================
Provides BL listing and creation based on tables bon_livraison and fournisseurs.
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
from datetime import date, datetime

from .secure_database import exec_read_all, exec_read_one, exec_read_dicts
from app.stfoom.logic.db_helpers import insert_row


@dataclass
class BonLivraison:
    numero: str
    date_livraison: date
    fournisseur_id: str  # stores code_fournisseur from fournisseurs
    quantite: float
    montant: float
    unite: str = "tonnes"
    description: Optional[str] = None
    id: Optional[int] = None
    facture_numero: Optional[str] = None
    fournisseur_nom: Optional[str] = None


def _parse_date(dt_val) -> date:
    if isinstance(dt_val, date):
        return dt_val
    if isinstance(dt_val, datetime):
        return dt_val.date()
    s = str(dt_val) if dt_val is not None else ''
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(s[:19], fmt).date()
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s).date()
    except Exception:
        return datetime.now().date()


def get_bls_with_facture_info() -> List[Dict]:
    """Return BLs enriched with supplier name; numero_facture left None for now.
    Uses code_fournisseur mapping, avoiding heavy joins that can fail on corrupted DBs.
    """
    # Prefer LEFT JOIN to resolve names; if it fails, fallback to two-step mapping
    try:
        rows = exec_read_dicts(
            """
            SELECT bl.id,
                   bl.numero,
                   bl.date_livraison,
                   bl.code_fournisseur AS fournisseur_id,
                   COALESCE(f.nom_fournisseur, '') AS fournisseur_nom,
                   bl.quantite,
                   COALESCE(bl.unite, 'T') AS unite,
                   bl.montant
            FROM bon_livraison bl
            LEFT JOIN fournisseurs f ON f.code_fournisseur = bl.code_fournisseur
            ORDER BY bl.date_livraison DESC, bl.id DESC
            """
        )
        result: List[Dict] = []
        for r in rows:
            result.append({
                'id': r['id'],
                'numero': r['numero'],
                'date_livraison': _parse_date(r['date_livraison']),
                'fournisseur_id': r['fournisseur_id'],
                'fournisseur_nom': r.get('fournisseur_nom') or '',
                'quantite': float(r['quantite']) if r['quantite'] is not None else 0.0,
                'unite': r.get('unite') or 'T',
                'montant': float(r['montant']) if r['montant'] is not None else 0.0,
                'numero_facture': None,
            })
        return result
    except Exception:
        # Fallback: get BLs and map supplier names with per-row lookup
        bl_rows = exec_read_dicts(
            """
            SELECT id, numero, date_livraison, code_fournisseur, quantite, COALESCE(unite,'T') AS unite, montant
            FROM bon_livraison
            ORDER BY date_livraison DESC, id DESC
            """
        )
        # Build a small cache of code -> name
        cache: Dict[str, str] = {}
        result: List[Dict] = []
        for r in bl_rows:
            code = r['code_fournisseur']
            name = cache.get(code)
            if name is None:
                row = exec_read_one("SELECT nom_fournisseur FROM fournisseurs WHERE code_fournisseur=?", (code,))
                name = row[0] if row else ''
                cache[code] = name
            result.append({
                'id': r['id'],
                'numero': r['numero'],
                'date_livraison': _parse_date(r['date_livraison']),
                'fournisseur_id': code,
                'fournisseur_nom': name,
                'quantite': float(r['quantite']) if r['quantite'] is not None else 0.0,
                'unite': r.get('unite') or 'T',
                'montant': float(r['montant']) if r['montant'] is not None else 0.0,
                'numero_facture': None,
            })
        return result


def create_bon_livraison(
    numero: str,
    date_livraison: date,
    fournisseur_id: str,
    quantite: float,
    montant: float,
    unite: str = 'T',
    description: Optional[str] = None,
    created_by: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """Create a BL record using code_fournisseur mapping. Returns (success, message, bl_id)."""
    # Validate fournisseur exists by code_fournisseur
    row = exec_read_one("SELECT 1 FROM fournisseurs WHERE code_fournisseur=?", (fournisseur_id,))
    if not row:
        return False, "Fournisseur introuvable", None

    try:
        data = {
            'numero': numero,
            'date_livraison': date_livraison.isoformat() if isinstance(date_livraison, (date, datetime)) else str(date_livraison),
            'code_fournisseur': fournisseur_id,
            'quantite': float(quantite),
            'montant': float(montant),
            'unite': unite or 'T',
            'description': description,
            'statut': 'en_attente',
            'created_by': created_by,
        }
        insert_row('bon_livraison', data)
        # Optionally, fetch the last inserted row id if needed
        return True, "BL créé avec succès", None
    except Exception as e:
        return False, f"Erreur lors de la création du BL: {e}", None


def get_bls_en_attente(fournisseur_code: str) -> List[BonLivraison]:
    """Return BLs en attente for a given supplier code."""
    rows = exec_read_all(
        """
        SELECT id, numero, date_livraison, code_fournisseur, quantite, COALESCE(unite,'T') as unite, montant
        FROM bon_livraison
        WHERE code_fournisseur=? AND statut='en_attente'
        ORDER BY date_livraison DESC, id DESC
        """,
        (fournisseur_code,)
    )
    result: List[BonLivraison] = []
    for r in rows:
        result.append(BonLivraison(
            id=r[0],
            numero=r[1],
            date_livraison=_parse_date(r[2]),
            fournisseur_id=r[3],
            quantite=float(r[4]) if r[4] is not None else 0.0,
            unite=r[5] or 'T',
            montant=float(r[6]) if r[6] is not None else 0.0,
        ))
    return result


# Placeholders for facture-related functions (not required for supplier filter)
def get_ciment_statistics():
    return {}

def create_facture_for_bls(bl_ids, facture_data):
    return None

def delete_ciment_facture(facture_id):
    return True

def get_ciment_facture(facture_id):
    return None

def update_ciment_facture(facture_id, data):
    return True
