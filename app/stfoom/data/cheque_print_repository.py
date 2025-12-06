"""
Cheque Print Repository
=======================
Persist and retrieve cheque print layout configuration.
Stores positions (in millimeters) for 5 fields on an 8 x 17.5 cm cheque.
"""
from __future__ import annotations
import os
import sqlite3
from typing import Dict, Optional
import json
from pathlib import Path

try:
    # Prefer centralized DB path
    from app.core.path_manager import get_db_path as _get_db_path
except Exception:
    from config.settings import get_db_path as _get_db_path  # type: ignore


# Default layout (mm) baked from user's current configuration on 2025-10-11
# positions relative to top-left in millimeters with default widths/heights
DEFAULT_LAYOUT = {
    "montant_number": {"x": 132.8, "y": 1.4, "w": 40.0, "h": 10.0},
    # Two lines for amount in letters: tuned sizes/positions to avoid cutting words
    "montant_letters_1": {"x": 66.2, "y": 14.2, "w": 76.8, "h": 8.4},
    "montant_letters_2": {"x": 20.0, "y": 20.8, "w": 148.2, "h": 9.8},
    "beneficiaire": {"x": 34.8, "y": 26.4, "w": 133.2, "h": 9.0},
    "date": {"x": 86.8, "y": 53.6, "w": 40.0, "h": 10.0},
    "lieu": {"x": 66.6, "y": 53.6, "w": 60.0, "h": 10.0},
}


class ChequePrintRepository:
    TABLE = "cheque_print_layout"

    def __init__(self) -> None:
        self.db_path = _get_db_path()
        # Persistent user config (dev and frozen) under %LOCALAPPDATA%/STFOOM/config
        try:
            base = Path(os.environ.get('LOCALAPPDATA') or Path.cwd()) / 'STFOOM' / 'config'
            base.mkdir(parents=True, exist_ok=True)
            self._json_path = base / 'cheque_print_settings.json'
        except Exception:
            # Fallback: store next to DB
            p = Path(self.db_path).parent / 'cheque_print_settings.json'
            self._json_path = p
        self._init_table()
        # If JSON missing, seed it from current DB so EXE takes same settings
        self._bootstrap_json_from_db_if_missing()
        # If JSON exists but missing critical keys, enrich it from DB one-time
        try:
            j = self._read_json()
            if isinstance(j, dict):
                changed = False
                # Ensure page size is present at top-level
                if not isinstance(j.get('page_width_mm'), (int, float)) or not isinstance(j.get('page_height_mm'), (int, float)):
                    w, h = self.get_page_size_mm()
                    j['page_width_mm'], j['page_height_mm'] = float(w), float(h)
                    changed = True
                # Ensure settings dict exists
                if 'settings' not in j or not isinstance(j.get('settings'), dict):
                    j['settings'] = {}
                    changed = True
                if changed:
                    self._write_json(j)
        except Exception:
            pass

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_table(self) -> None:
        with self._conn() as conn:
            conn.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {self.TABLE} (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    page_width_mm REAL NOT NULL DEFAULT 175.0,
                    page_height_mm REAL NOT NULL DEFAULT 80.0,
                    montant_number_x REAL, montant_number_y REAL,
                    montant_letters_x REAL, montant_letters_y REAL,
                    beneficiaire_x REAL, beneficiaire_y REAL,
                    date_x REAL, date_y REAL,
                    lieu_x REAL, lieu_y REAL,
                    settings_json TEXT
                )
                """
            )
            # Ensure settings_json column exists (older installs)
            try:
                cur = conn.execute(f"PRAGMA table_info({self.TABLE})")
                cols = [r[1] for r in cur.fetchall()]
                if 'settings_json' not in cols:
                    conn.execute(f"ALTER TABLE {self.TABLE} ADD COLUMN settings_json TEXT")
            except Exception:
                pass
            # Ensure a single row exists
            cur = conn.execute(f"SELECT COUNT(*) FROM {self.TABLE}")
            count = cur.fetchone()[0]
            if count == 0:
                # Initialize single row and persist enriched layout into settings_json
                self.save_layout(DEFAULT_LAYOUT)
                # Also persist baked default print settings so first-run EXE matches user's current config
                baked = self.get_default_settings()
                # Save settings writes both DB and mirrors JSON
                self.save_settings(baked)

    # ---- JSON persistence helpers ----
    def _read_json(self) -> Dict[str, object]:
        try:
            if self._json_path.exists():
                return json.loads(self._json_path.read_text(encoding='utf-8') or '{}') or {}
        except Exception:
            pass
        return {}

    def _write_json(self, data: Dict[str, object]) -> None:
        try:
            # Avoid writing non-serializable content
            self._json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
        except Exception:
            pass

    def _bootstrap_json_from_db_if_missing(self) -> None:
        """If the user JSON doesn't exist yet, export current DB layout/settings to it."""
        try:
            if self._json_path.exists():
                return
            # Build from DB values directly to avoid JSON overlay recursion
            with self._conn() as conn:
                cur = conn.execute(f"SELECT * FROM {self.TABLE} WHERE id = 1")
                row = cur.fetchone()
            # Layout payload
            layout_payload: Dict[str, Dict[str, float]] = {}
            base_layout = {k: v.copy() for k, v in DEFAULT_LAYOUT.items()}
            if row:
                def _val_key(key: str, default: float) -> float:
                    try:
                        if key in row.keys():
                            v = row[key]
                            return default if v is None else float(v)
                    except Exception:
                        pass
                    return default
                base_layout["montant_number"].update({
                    "x": _val_key("montant_number_x", base_layout["montant_number"]["x"]),
                    "y": _val_key("montant_number_y", base_layout["montant_number"]["y"]),
                })
                mlx = _val_key("montant_letters_x", base_layout["montant_letters_1"]["x"]) if "montant_letters_x" in row.keys() else base_layout["montant_letters_1"]["x"]
                mly = _val_key("montant_letters_y", base_layout["montant_letters_1"]["y"]) if "montant_letters_y" in row.keys() else base_layout["montant_letters_1"]["y"]
                base_layout["montant_letters_1"].update({"x": mlx, "y": mly})
                base_layout["beneficiaire"].update({
                    "x": _val_key("beneficiaire_x", base_layout["beneficiaire"]["x"]),
                    "y": _val_key("beneficiaire_y", base_layout["beneficiaire"]["y"]),
                })
                base_layout["date"].update({
                    "x": _val_key("date_x", base_layout["date"]["x"]),
                    "y": _val_key("date_y", base_layout["date"]["y"]),
                })
                base_layout["lieu"].update({
                    "x": _val_key("lieu_x", base_layout["lieu"]["x"]),
                    "y": _val_key("lieu_y", base_layout["lieu"]["y"]),
                })
                try:
                    if "settings_json" in row.keys() and row["settings_json"]:
                        sj = json.loads(row["settings_json"])
                        if isinstance(sj, dict) and isinstance(sj.get("layout"), dict):
                            for k, v in sj["layout"].items():
                                if isinstance(v, dict):
                                    base_layout.setdefault(k, {})
                                    for key2 in ("x","y","w","h"):
                                        if key2 in v:
                                            base_layout[k][key2] = float(v[key2])
                except Exception:
                    pass
            # Only x,y,w,h per box
            for k, v in base_layout.items():
                vv = {}
                for key2 in ("x","y","w","h"):
                    if key2 in v:
                        vv[key2] = float(v[key2])
                if vv:
                    layout_payload[k] = vv
            # Settings payload from DB JSON
            settings_payload: Dict[str, object] = {}
            w, h = self.get_page_size_mm()
            if row and ("settings_json" in row.keys()) and row["settings_json"]:
                try:
                    sj = json.loads(row["settings_json"])
                    if isinstance(sj, dict):
                        settings_payload.update({k: sj[k] for k in sj if k != 'layout'})
                except Exception:
                    pass
            data = {
                "layout": layout_payload,
                "settings": settings_payload,
                "page_width_mm": float(w),
                "page_height_mm": float(h),
            }
            self._write_json(data)
        except Exception:
            # Non-fatal
            pass

    # ---- Emergency restore helpers ----
    def restore_user_json_from_db(self, backup_existing: bool = True) -> Optional[Path]:
        """Overwrite user JSON from current DB row 1, optionally backing up existing JSON.

        Returns the path to the written JSON on success, or None on failure.
        """
        try:
            # Backup current JSON if requested
            if backup_existing and self._json_path.exists():
                try:
                    ts = __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S')
                    bak = self._json_path.with_suffix(self._json_path.suffix + f'.bak_{ts}')
                    bak.write_text(self._json_path.read_text(encoding='utf-8'), encoding='utf-8')
                except Exception:
                    pass
            # Read DB row
            with self._conn() as conn:
                cur = conn.execute(f"SELECT * FROM {self.TABLE} WHERE id = 1")
                row = cur.fetchone()
            layout_payload: Dict[str, Dict[str, float]] = {}
            base_layout = {k: v.copy() for k, v in DEFAULT_LAYOUT.items()}
            if row:
                def _val_key(key: str, default: float) -> float:
                    try:
                        if key in row.keys():
                            v = row[key]
                            return default if v is None else float(v)
                    except Exception:
                        pass
                    return default
                base_layout["montant_number"].update({
                    "x": _val_key("montant_number_x", base_layout["montant_number"]["x"]),
                    "y": _val_key("montant_number_y", base_layout["montant_number"]["y"]),
                })
                mlx = _val_key("montant_letters_x", base_layout["montant_letters_1"]["x"]) if "montant_letters_x" in row.keys() else base_layout["montant_letters_1"]["x"]
                mly = _val_key("montant_letters_y", base_layout["montant_letters_1"]["y"]) if "montant_letters_y" in row.keys() else base_layout["montant_letters_1"]["y"]
                base_layout["montant_letters_1"].update({"x": mlx, "y": mly})
                base_layout["beneficiaire"].update({
                    "x": _val_key("beneficiaire_x", base_layout["beneficiaire"]["x"]),
                    "y": _val_key("beneficiaire_y", base_layout["beneficiaire"]["y"]),
                })
                base_layout["date"].update({
                    "x": _val_key("date_x", base_layout["date"]["x"]),
                    "y": _val_key("date_y", base_layout["date"]["y"]),
                })
                base_layout["lieu"].update({
                    "x": _val_key("lieu_x", base_layout["lieu"]["x"]),
                    "y": _val_key("lieu_y", base_layout["lieu"]["y"]),
                })
                try:
                    if "settings_json" in row.keys() and row["settings_json"]:
                        sj = json.loads(row["settings_json"])
                        if isinstance(sj, dict) and isinstance(sj.get("layout"), dict):
                            for k, v in sj["layout"].items():
                                if isinstance(v, dict):
                                    base_layout.setdefault(k, {})
                                    for key2 in ("x","y","w","h"):
                                        if key2 in v:
                                            base_layout[k][key2] = float(v[key2])
                except Exception:
                    pass
            # Compose layout payload
            for k, v in base_layout.items():
                vv = {}
                for key2 in ("x","y","w","h"):
                    if key2 in v:
                        try:
                            vv[key2] = float(v[key2])
                        except Exception:
                            pass
                if vv:
                    layout_payload[k] = vv
            # Settings payload from DB JSON
            settings_payload: Dict[str, object] = {}
            w, h = self.get_page_size_mm()
            if row and ("settings_json" in row.keys()) and row["settings_json"]:
                try:
                    sj = json.loads(row["settings_json"])
                    if isinstance(sj, dict):
                        settings_payload.update({k: sj[k] for k in sj if k != 'layout'})
                except Exception:
                    pass
            data = {
                "layout": layout_payload,
                "settings": settings_payload,
                "page_width_mm": float(w),
                "page_height_mm": float(h),
            }
            self._write_json(data)
            return self._json_path
        except Exception:
            return None

    def get_layout(self) -> Dict[str, Dict[str, float]]:
        with self._conn() as conn:
            cur = conn.execute(f"SELECT * FROM {self.TABLE} WHERE id = 1")
            row = cur.fetchone()
            layout = {k: v.copy() for k, v in DEFAULT_LAYOUT.items()}
            if not row:
                # Even if DB row missing, try JSON overlay
                try:
                    j = self._read_json()
                    if isinstance(j, dict) and isinstance(j.get('layout'), dict):
                        for k, v in j['layout'].items():
                            if isinstance(v, dict):
                                layout.setdefault(k, {})
                                for key2 in ("x","y","w","h"):
                                    if key2 in v:
                                        layout[k][key2] = float(v[key2])
                except Exception:
                    pass
                return layout
            def _val(v, default):
                return default if v is None else float(v)
            # Merge legacy column positions
            layout["montant_number"].update({"x": _val(row["montant_number_x"], layout["montant_number"]["x"]),
                                              "y": _val(row["montant_number_y"], layout["montant_number"]["y"])})
            # Legacy had single montant_letters; map to first box
            ml_x = _val(row["montant_letters_x"], layout["montant_letters_1"]["x"]) if "montant_letters_x" in row.keys() else layout["montant_letters_1"]["x"]
            ml_y = _val(row["montant_letters_y"], layout["montant_letters_1"]["y"]) if "montant_letters_y" in row.keys() else layout["montant_letters_1"]["y"]
            layout["montant_letters_1"].update({"x": ml_x, "y": ml_y})
            layout["beneficiaire"].update({"x": _val(row["beneficiaire_x"], layout["beneficiaire"]["x"]),
                                            "y": _val(row["beneficiaire_y"], layout["beneficiaire"]["y"])})
            layout["date"].update({"x": _val(row["date_x"], layout["date"]["x"]),
                                     "y": _val(row["date_y"], layout["date"]["y"])})
            layout["lieu"].update({"x": _val(row["lieu_x"], layout["lieu"]["x"]),
                                     "y": _val(row["lieu_y"], layout["lieu"]["y"])})
            # Merge enriched layout from settings_json if present
            try:
                sj = row["settings_json"]
                if sj:
                    data = json.loads(sj)
                    if isinstance(data, dict) and isinstance(data.get("layout"), dict):
                        # Trust all provided keys/values
                        for k, v in data["layout"].items():
                            if isinstance(v, dict):
                                if k not in layout:
                                    layout[k] = {}
                                # Copy only numeric x,y,w,h if present
                                for key2 in ("x","y","w","h"):
                                    if key2 in v:
                                        try:
                                            layout[k][key2] = float(v[key2])
                                        except Exception:
                                            pass
            except Exception:
                pass
            # Overlay user JSON file last (highest priority)
            try:
                j = self._read_json()
                if isinstance(j, dict) and isinstance(j.get('layout'), dict):
                    for k, v in j['layout'].items():
                        if isinstance(v, dict):
                            layout.setdefault(k, {})
                            for key2 in ("x","y","w","h"):
                                if key2 in v:
                                    layout[k][key2] = float(v[key2])
            except Exception:
                pass
            return layout

    def get_page_size_mm(self) -> tuple[float, float]:
        """Return (width_mm, height_mm) preferring user JSON, falling back to DB, default 175x80."""
        # 1) Prefer user JSON top-level if present
        try:
            j = self._read_json()
            if isinstance(j, dict):
                if isinstance(j.get("page_width_mm"), (int, float)) and isinstance(j.get("page_height_mm"), (int, float)):
                    return float(j["page_width_mm"]), float(j["page_height_mm"])
                # Sometimes page size may reside under 'settings'
                s = j.get('settings')
                if isinstance(s, dict) and isinstance(s.get("page_width_mm"), (int, float)) and isinstance(s.get("page_height_mm"), (int, float)):
                    return float(s["page_width_mm"]), float(s["page_height_mm"])
        except Exception:
            pass
        # 2) Fallback to DB columns
        with self._conn() as conn:
            cur = conn.execute(f"SELECT page_width_mm, page_height_mm FROM {self.TABLE} WHERE id = 1")
            row = cur.fetchone()
            if row:
                try:
                    w = float(row["page_width_mm"]) if row["page_width_mm"] is not None else 175.0
                    h = float(row["page_height_mm"]) if row["page_height_mm"] is not None else 80.0
                    return w, h
                except Exception:
                    pass
        # 3) Default
        return 175.0, 80.0

    def save_layout(self, layout: Dict[str, Dict[str, float]]) -> None:
        """Persist layout positions to legacy columns and full enriched layout (x,y,w,h) into settings_json."""
        # upsert single row with id = 1
        with self._conn() as conn:
            # Preserve existing page size and settings_json
            cur0 = conn.execute(f"SELECT page_width_mm, page_height_mm, settings_json FROM {self.TABLE} WHERE id = 1")
            row0 = cur0.fetchone()
            page_w = float(row0[0]) if row0 and row0[0] is not None else 175.0
            page_h = float(row0[1]) if row0 and row0[1] is not None else 80.0
            # Merge 'layout' into settings_json payload
            try:
                base = json.loads(row0[2]) if row0 and row0[2] else {}
                if not isinstance(base, dict):
                    base = {}
            except Exception:
                base = {}
            # Only include numeric x,y,w,h
            lay_payload = {}
            for k, v in layout.items():
                if isinstance(v, dict):
                    vv = {}
                    for key2 in ("x","y","w","h"):
                        if key2 in v:
                            try:
                                vv[key2] = float(v[key2])
                            except Exception:
                                pass
                    if vv:
                        lay_payload[k] = vv
            base["layout"] = lay_payload
            settings_json = json.dumps(base)
            conn.execute(
                f"""
                INSERT INTO {self.TABLE} (
                    id, page_width_mm, page_height_mm,
                    montant_number_x, montant_number_y,
                    montant_letters_x, montant_letters_y,
                    beneficiaire_x, beneficiaire_y,
                    date_x, date_y,
                    lieu_x, lieu_y,
                    settings_json
                ) VALUES (
                    1, :pw, :ph,
                    :mnx, :mny,
                    :mlx, :mly,
                    :bx, :by,
                    :dx, :dy,
                    :lx, :ly,
                    :sj
                )
                ON CONFLICT(id) DO UPDATE SET
                    montant_number_x = excluded.montant_number_x,
                    montant_number_y = excluded.montant_number_y,
                    montant_letters_x = excluded.montant_letters_x,
                    montant_letters_y = excluded.montant_letters_y,
                    beneficiaire_x = excluded.beneficiaire_x,
                    beneficiaire_y = excluded.beneficiaire_y,
                    date_x = excluded.date_x,
                    date_y = excluded.date_y,
                    lieu_x = excluded.lieu_x,
                    lieu_y = excluded.lieu_y,
                    page_width_mm = excluded.page_width_mm,
                    page_height_mm = excluded.page_height_mm,
                    settings_json = COALESCE(excluded.settings_json, {self.TABLE}.settings_json)
                """,
                {
                    "pw": page_w,
                    "ph": page_h,
                    "mnx": layout.get("montant_number", {}).get("x", DEFAULT_LAYOUT["montant_number"]["x"]),
                    "mny": layout.get("montant_number", {}).get("y", DEFAULT_LAYOUT["montant_number"]["y"]),
                    # Save legacy single letters position from first box
                    "mlx": layout.get("montant_letters_1", {}).get("x", DEFAULT_LAYOUT["montant_letters_1"]["x"]),
                    "mly": layout.get("montant_letters_1", {}).get("y", DEFAULT_LAYOUT["montant_letters_1"]["y"]),
                    "bx": layout.get("beneficiaire", {}).get("x", DEFAULT_LAYOUT["beneficiaire"]["x"]),
                    "by": layout.get("beneficiaire", {}).get("y", DEFAULT_LAYOUT["beneficiaire"]["y"]),
                    "dx": layout.get("date", {}).get("x", 130.0),
                    "dy": layout.get("date", {}).get("y", 20.0),
                    "lx": layout.get("lieu", {}).get("x", 18.0),
                    "ly": layout.get("lieu", {}).get("y", 12.0),
                    "sj": settings_json,
                },
            )
            conn.commit()
        # Mirror to JSON file for portability across dev/frozen DB paths
        try:
            data = self._read_json()
            if not isinstance(data, dict):
                data = {}
            # Build portable layout payload
            lay_payload = {}
            for k, v in layout.items():
                if isinstance(v, dict):
                    vv = {}
                    for key2 in ("x","y","w","h"):
                        if key2 in v:
                            try:
                                vv[key2] = float(v[key2])
                            except Exception:
                                pass
                    if vv:
                        lay_payload[k] = vv
            data['layout'] = lay_payload
            # Preserve any existing settings payload
            self._write_json(data)
        except Exception:
            pass

    def get_settings(self) -> Dict[str, object]:
        """Return merged settings including page size and print parameters with defaults."""
        # Start with page size (prefer JSON via get_page_size_mm)
        w, h = self.get_page_size_mm()
        dflt = {
            "page_width_mm": w,
            "page_height_mm": h,
            "margins_mode": "zero",  # zero | physical | custom
            "margin_left_mm": 0.0,
            "margin_top_mm": 0.0,
            "shift_x_mm": 0.0,
            "shift_y_mm": 0.0,
            "orientation": "portrait",
            "rotate_deg": 0,
            "center_on_page": True,
            "sideways_from_montant": False,
            "vertical_align": "extreme-top",
            "vertical_offset_mm": 0.0,
        }
        try:
            with self._conn() as conn:
                cur = conn.execute(f"SELECT settings_json FROM {self.TABLE} WHERE id = 1")
                row = cur.fetchone()
                if row and row[0]:
                    sj = row[0]
                    try:
                        data = json.loads(sj)
                        if isinstance(data, dict):
                            dflt.update({k: data[k] for k in data})
                    except Exception:
                        pass
        except Exception:
            pass
        # Overlay from user JSON file last (highest priority)
        try:
            j = self._read_json()
            if isinstance(j, dict):
                s = j.get('settings') or j.get('print_settings')
                if isinstance(s, dict):
                    dflt.update(s)
                # If JSON included page size keys at top-level, honor them
                for key in ("page_width_mm","page_height_mm"):
                    if key in j and isinstance(j[key], (int, float)):
                        dflt[key] = float(j[key])
        except Exception:
            pass
        # At this point, dflt already reflects JSON-preferred page size via get_page_size_mm and overlay.
        # Ensure numeric types
        try:
            dflt["page_width_mm"] = float(dflt.get("page_width_mm", 175.0))
            dflt["page_height_mm"] = float(dflt.get("page_height_mm", 80.0))
        except Exception:
            dflt["page_width_mm"], dflt["page_height_mm"] = 175.0, 80.0
        return dflt

    def get_default_settings(self) -> Dict[str, object]:
        """Return baked default print settings (captured 2025-10-11).

        These are used for first-run seeding and when the user resets to defaults.
        """
        return {
            "page_width_mm": 175.0,
            "page_height_mm": 80.0,
            "margins_mode": "custom",
            "margin_left_mm": 0.0,
            "margin_top_mm": 0.0,
            "shift_x_mm": 0.0,
            "shift_y_mm": -94.0,
            "orientation": "landscape",
            "rotate_deg": 90,
            "center_on_page": True,
            "sideways_from_montant": True,
            "vertical_align": "extreme-top",
            "vertical_offset_mm": 94.0,
        }

    def save_settings(self, settings: Dict[str, object]) -> None:
        """Persist width/height columns and other settings as JSON."""
        # Extract width/height if present
        w = float(settings.get("page_width_mm", 175.0))
        h = float(settings.get("page_height_mm", 80.0))
        # Store other keys in JSON (avoid duplicating saved columns)
        payload = {k: v for k, v in settings.items() if k not in ("page_width_mm", "page_height_mm")}
        sj = json.dumps(payload)
        with self._conn() as conn:
            conn.execute(
                f"""
                INSERT INTO {self.TABLE} (id, page_width_mm, page_height_mm, settings_json)
                VALUES (1, :w, :h, :sj)
                ON CONFLICT(id) DO UPDATE SET
                    page_width_mm = excluded.page_width_mm,
                    page_height_mm = excluded.page_height_mm,
                    settings_json = excluded.settings_json
                """,
                {"w": w, "h": h, "sj": sj}
            )
            conn.commit()
        # Mirror to user JSON file for portability
        try:
            data = self._read_json()
            if not isinstance(data, dict):
                data = {}
            data['settings'] = payload
            # Also keep page size at top-level for quick access
            data['page_width_mm'] = w
            data['page_height_mm'] = h
            self._write_json(data)
        except Exception:
            pass
