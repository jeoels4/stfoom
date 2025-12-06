import sqlite3
import os
import sys
from datetime import datetime
# Robust import for calendar_base (moved under stfoom.logic in the repo)
try:
    from stfoom.logic import calendar_base as cal  # primary location
except Exception:
    # Legacy fallback path (if present)
    from stfoom.logicold import calendar_base as cal  # type: ignore
from connection.sync_wrapper import insert_with_sync, update_with_sync, delete_with_sync
from .connection_pool import get_pooled_connection

def get_database_path():
    """Deprecated: DB path is now centrally managed; kept for compatibility."""
    try:
        from config.settings import get_db_path
        return get_db_path()
    except Exception:
        # Fallback to LOCALAPPDATA
        base = os.environ.get("LOCALAPPDATA") or os.getcwd()
        data_dir = os.path.join(base, "STFOOM", "data")
        os.makedirs(data_dir, exist_ok=True)
        return os.path.join(data_dir, "stfoom.db")

def _conn():
    """Get database connection from connection pool."""
    return get_pooled_connection()

def init_db():
    with _conn() as cn:
        cn.execute("""
            CREATE TABLE IF NOT EXISTS voitures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                genre TEXT,
                utilisateur TEXT,
                matricule TEXT,
                date_visite TEXT,
                date_assurance TEXT,
                date_vignette TEXT,
                date_premiere_mise TEXT
            )
        """)
        cn.commit()

# ───────────────────────────── CRUD ─────────────────────────────

def get_all_voitures():
    with _conn() as cn:
        cur = cn.execute("SELECT * FROM voitures ORDER BY id DESC")
        rows = cur.fetchall()
        return [dict(zip([col[0] for col in cur.description], row)) for row in rows]

def add_voiture(data: dict):
    success = insert_with_sync("voitures", data)
    if success:
        _push_to_calendar(data)
    return success

def update_voiture(vid: int, data: dict):
    # Remove old calendar events for this matricule
    _remove_from_calendar(data["matricule"])
    success = update_with_sync("voitures", str(vid), data)
    if success:
        _push_to_calendar(data)
    return success

def delete_voiture(vid: int):
    # Find matricule first to delete its calendar items
    with _conn() as cn:
        row = cn.execute("SELECT matricule FROM voitures WHERE id=?", (vid,)).fetchone()
    if row:
        _remove_from_calendar(row[0])
    return delete_with_sync("voitures", str(vid))

# ───────────────────────────── Helpers ─────────────────────────────

def compute_age(date_str: str) -> str:
    """Return car age in years (or empty)."""
    try:
        dt = datetime.strptime(date_str, "%Y-%m-%d")
        now = datetime.now()
        age = now.year - dt.year - ((now.month, now.day) < (dt.month, dt.day))
        return str(max(age, 0))
    except Exception:
        return ""

# ───────────────────────────── Calendar Integration ─────────────────────────────

def _push_to_calendar(data: dict):
    """
    Create calendar events for Visite, Assurance, Vignette.
    Uses positional parameters; `calendar_base.add_event(title, date_str, category, desc)`
    Title format: 'Voiture - <utilisateur> - <matricule> – <event type>'
    """
    utilisateur = data.get('utilisateur', '').strip()
    matricule = data.get('matricule', '').strip()
    for key, label in [
        ("date_visite",    "Visite technique"),
        ("date_assurance", "Assurance"),
        ("date_vignette",  "Vignette")
    ]:
        date_val = data.get(key)
        if date_val:
            # New format: Voiture - <utilisateur> - <matricule> – <event type>
            title = f"Voiture - {utilisateur} - {matricule} – {label}"
            cal.add_event(
                title,
                date_val,
                "Cars",
                f"{label} pour {utilisateur}"
            )

def _remove_from_calendar(matricule: str):
    """Delete all calendar events containing given matricule in title."""
    with cal._conn() as cn:
        cn.execute("""
            DELETE FROM calendar_events
            WHERE category='Cars' AND title LIKE ?
        """, (f"%{matricule}%",))
        cn.commit()
