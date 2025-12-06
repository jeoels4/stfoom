"""
Ciment Page - Construction Materials Management
==============================================
Handles cement and construction materials operations.
Simplified version without old logic dependencies.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime, date
from typing import Optional, Dict, List, Any
import sqlite3
import os
from tkcalendar import DateEntry
from .notification_system import notification_manager

class CimentPage(ttk.Frame):
    """
    Ciment Page for construction materials management.
    
    This page handles:
    - Construction materials inventory
    - Delivery notes (Bon de Livraison)
    - Supplier management
    - Basic statistics
    """
    
    def __init__(self, parent, go_home):
        super().__init__(parent)
        self.go_back = go_home  # Use go_home parameter like other pages
        
        # Database path
        self.db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'data', 'stfoom.db')
        
        # Ensure required tables and columns exist to prevent load failures
        try:
            self._ensure_schema()
        except Exception as e:
            print(f"[CIMENT_PAGE] Schema ensure failed: {e}")
        
        # Initialize data storage (database-backed)
        self.materials = []
        self.suppliers = []
        self.delivery_notes = []
        
        # Load data from database
        self.load_data_from_database()
        # Repair any historical ciment→achat dates stored in non-ISO format
        self._backfill_ciment_achats_dates()
        # Normalize older avoir suppliers to Carthage Cement where applicable
        self._backfill_carthage_avoir_supplier()
        
        self.setup_ui()
        print("[CIMENT_PAGE] ✅ Simplified Ciment Page initialized successfully")

    # --------------------
    # Date utilities
    # --------------------
    def _normalize_date_for_db(self, date_str: str) -> str:
        """Normalize various UI date formats to ISO YYYY-MM-DD for DB.
        Accepts formats like dd/mm/yy, dd/mm/yyyy, or already-ISO.
        Returns the input unchanged if no known formats match.
        """
        try:
            if not date_str:
                return date_str
            # Try dd/mm/yy
            try:
                d = datetime.strptime(date_str, "%d/%m/%y")
                return d.strftime("%Y-%m-%d")
            except ValueError:
                pass
            # Try dd/mm/yyyy
            try:
                d = datetime.strptime(date_str, "%d/%m/%Y")
                return d.strftime("%Y-%m-%d")
            except ValueError:
                pass
            # Try already ISO
            try:
                d = datetime.strptime(date_str, "%Y-%m-%d")
                return d.strftime("%Y-%m-%d")
            except ValueError:
                pass
            # Fallback unchanged
            return date_str
        except Exception:
            return date_str

    def _backfill_ciment_achats_dates(self):
        """One-time backfill to fix achats.date created from Ciment with wrong formats.
        Targets rows with notes starting with 'Facture ciment générée' or '[AVOIR]'.
        """
        if getattr(self, "_date_backfill_done", False):
            return
        try:
            with self.get_db_connection() as conn:
                cur = conn.execute(
                    """
                    SELECT id, date, notes
                    FROM achats
                    WHERE notes LIKE 'Facture ciment générée%' OR notes LIKE '[AVOIR]%'
                    """
                )
                rows = cur.fetchall()
                updates = 0
                for _id, d, _notes in rows:
                    try:
                        d_new = self._normalize_date_for_db(d if isinstance(d, str) else str(d))
                        if d_new and d_new != d:
                            conn.execute("UPDATE achats SET date = ? WHERE id = ?", (d_new, _id))
                            updates += 1
                    except Exception:
                        continue
                if updates:
                    conn.commit()
                    print(f"[CIMENT_PAGE] Backfilled {updates} achat dates to ISO format")
        except Exception as e:
            print(f"[CIMENT_PAGE] Date backfill skipped due to error: {e}")
        finally:
            self._date_backfill_done = True

    def _priority_sort_suppliers(self, names: List[str]) -> List[str]:
        """Return supplier names sorted with 'Carthage Cement' first, case-insensitive.
        Keeps stable alphabetical order for the rest. Also treats 'Carthage Ciment' as Carthage Cement.
        """
        def is_carthage(name: str) -> bool:
            n = (name or '').strip().lower()
            return ('carthage' in n) and ('cement' in n or 'ciment' in n)

        # Deduplicate while preserving input order
        seen = set()
        deduped = []
        for n in names:
            if n not in seen:
                seen.add(n)
                deduped.append(n)

        # Stable sort with key: 0 for Carthage, 1 otherwise; then alphabetical
        return sorted(deduped, key=lambda x: (0 if is_carthage(x) else 1, (x or '').lower()))

    def _backfill_carthage_avoir_supplier(self):
        """One-time backfill to ensure existing cement avoirs are linked to Carthage Cement supplier text.
        - If an avoir achat is already linked to any BL whose fournisseur is Carthage, normalize its fournisseur
          to '[CIMENT] Carthage Cement'.
        - Additionally, normalize avoirs whose fournisseur text fuzzy-matches Carthage without the '[CIMENT]' prefix.
        """
        if getattr(self, "_carthage_avoir_supplier_backfill_done", False):
            return
        try:
            with self.get_db_connection() as conn:
                # 1) Based on existing BL ↔ Avoir links
                try:
                    cur = conn.execute(
                        """
                        SELECT a.id
                        FROM achats a
                        JOIN bon_livraison_avoirs bla ON bla.achat_id = a.id
                        JOIN bon_livraison bl ON bl.id = bla.bl_id
                        LEFT JOIN fournisseurs f ON f.code_fournisseur = bl.code_fournisseur
                        WHERE a.notes LIKE '[AVOIR]%' AND (
                              LOWER(COALESCE(f.nom_fournisseur, '')) LIKE '%carthage%' AND 
                              (LOWER(COALESCE(f.nom_fournisseur, '')) LIKE '%cement%' OR LOWER(COALESCE(f.nom_fournisseur, '')) LIKE '%ciment%')
                        ) AND (a.fournisseur IS NULL OR a.fournisseur NOT LIKE '[CIMENT]%')
                        """
                    )
                    ids = [row[0] for row in cur.fetchall()]
                    if ids:
                        qmarks = ",".join(["?"] * len(ids))
                        conn.execute(f"UPDATE achats SET fournisseur='[CIMENT] Carthage Cement' WHERE id IN ({qmarks})", ids)
                        conn.commit()
                        print(f"[CIMENT_PAGE] Backfilled {len(ids)} avoir(s) supplier to '[CIMENT] Carthage Cement' via link detection")
                except Exception as e:
                    print(f"[CIMENT_PAGE] Link-based avoir supplier backfill skipped: {e}")

                # 2) Fuzzy-match existing avoirs with Carthage naming but missing prefix
                try:
                    cur = conn.execute(
                        """
                        SELECT COUNT(*) FROM achats
                        WHERE notes LIKE '[AVOIR]%' 
                          AND (LOWER(COALESCE(fournisseur, '')) LIKE '%carthage%cemen%' OR LOWER(COALESCE(fournisseur, '')) LIKE '%carthage%cimen%')
                          AND (fournisseur NOT LIKE '[CIMENT]%' OR fournisseur IS NULL)
                        """
                    )
                    count = cur.fetchone()[0]
                    if count and count > 0:
                        conn.execute(
                            """
                            UPDATE achats
                            SET fournisseur='[CIMENT] Carthage Cement'
                            WHERE notes LIKE '[AVOIR]%' 
                              AND (LOWER(COALESCE(fournisseur, '')) LIKE '%carthage%cemen%' OR LOWER(COALESCE(fournisseur, '')) LIKE '%carthage%cimen%')
                              AND (fournisseur NOT LIKE '[CIMENT]%' OR fournisseur IS NULL)
                            """
                        )
                        conn.commit()
                        print(f"[CIMENT_PAGE] Backfilled {count} fuzzy-matched avoir(s) supplier to '[CIMENT] Carthage Cement'")
                except Exception as e:
                    print(f"[CIMENT_PAGE] Fuzzy avoir supplier backfill skipped: {e}")
        except Exception as e:
            print(f"[CIMENT_PAGE] Avoir supplier backfill skipped due to error: {e}")
        finally:
            self._carthage_avoir_supplier_backfill_done = True
    
    def get_db_connection(self):
        """Get database connection."""
        return sqlite3.connect(self.db_path)
    
    def _ensure_schema(self):
        """Ensure cement-related tables and columns exist with expected schema.
        This prevents fallback to sample data due to SELECTs failing on missing columns.
        """
        with self.get_db_connection() as conn:
            cur = conn.cursor()
            # Materials table (align with create_materials_table.py; harmless if exists)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS materials (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    quantity REAL NOT NULL DEFAULT 0,
                    unit TEXT NOT NULL DEFAULT 'tonnes',
                    price REAL NOT NULL DEFAULT 0,
                    supplier TEXT,
                    minimum_stock REAL DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Trigger for updated_at
            cur.execute(
                """
                CREATE TRIGGER IF NOT EXISTS update_materials_timestamp 
                AFTER UPDATE ON materials
                BEGIN
                    UPDATE materials SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
                """
            )
            
            # Fournisseurs table (minimal definition; if a richer one exists, this is a no-op)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS fournisseurs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    code_fournisseur TEXT UNIQUE NOT NULL,
                    nom_fournisseur TEXT NOT NULL,
                    adresse TEXT,
                    telephone TEXT,
                    email TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            
            # bon_livraison table (use code_fournisseur; include avoir_* flags and material_id)
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bon_livraison (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero TEXT UNIQUE NOT NULL,
                    date_livraison DATE NOT NULL,
                    code_fournisseur TEXT,
                    quantite REAL NOT NULL,
                    unite TEXT DEFAULT 'tonnes',
                    montant REAL NOT NULL,
                    description TEXT,
                    material_id INTEGER,
                    statut TEXT DEFAULT 'en_attente' CHECK (statut IN ('en_attente', 'facturee', 'annulee')),
                    avoir_payment_before_20_days INTEGER DEFAULT 1,
                    avoir_total_factures_200t_month INTEGER DEFAULT 1,
                    avoir_sur_livraison INTEGER DEFAULT 0,
                    avoir_par_annee INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            # Ensure missing columns exist (covers older DBs)
            cur.execute("PRAGMA table_info(bon_livraison)")
            bl_cols = {row[1] for row in cur.fetchall()}
            # Add code_fournisseur if missing
            if 'code_fournisseur' not in bl_cols:
                cur.execute("ALTER TABLE bon_livraison ADD COLUMN code_fournisseur TEXT")
            # Add unite if missing
            if 'unite' not in bl_cols:
                cur.execute("ALTER TABLE bon_livraison ADD COLUMN unite TEXT DEFAULT 'tonnes'")
            # Add material_id if missing
            cur.execute("PRAGMA table_info(bon_livraison)")
            bl_cols = {row[1] for row in cur.fetchall()}
            if 'material_id' not in bl_cols:
                cur.execute("ALTER TABLE bon_livraison ADD COLUMN material_id INTEGER")
            # Add avoir columns if missing
            for col, default_val in [
                ('avoir_payment_before_20_days', 1),
                ('avoir_total_factures_200t_month', 1),
                ('avoir_sur_livraison', 0),
                ('avoir_par_annee', 0),
            ]:
                cur.execute("PRAGMA table_info(bon_livraison)")
                current_cols = {r[1] for r in cur.fetchall()}
                if col not in current_cols:
                    cur.execute(f"ALTER TABLE bon_livraison ADD COLUMN {col} INTEGER DEFAULT {default_val}")
            # Timestamps trigger for BL
            cur.execute(
                """
                CREATE TRIGGER IF NOT EXISTS update_bon_livraison_timestamp 
                AFTER UPDATE ON bon_livraison
                BEGIN
                    UPDATE bon_livraison SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
                END
                """
            )

            # Link tables: BL ↔ Factures and BL ↔ Avoirs
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bon_livraison_factures (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bl_id INTEGER NOT NULL,
                    achat_id INTEGER NOT NULL
                )
                """
            )
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS bon_livraison_avoirs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    bl_id INTEGER NOT NULL,
                    achat_id INTEGER NOT NULL
                )
                """
            )
            # Indexes for faster lookups
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blf_bl ON bon_livraison_factures(bl_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_blf_achat ON bon_livraison_factures(achat_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bla_bl ON bon_livraison_avoirs(bl_id)")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_bla_achat ON bon_livraison_avoirs(achat_id)")
            conn.commit()
    
    def load_data_from_database(self):
        """Load materials, suppliers, and delivery notes from database.
        Make each section resilient so one failure doesn't erase all data.
        """
        loaded_any = False
        with self.get_db_connection() as conn:
            # Load materials
            try:
                cursor = conn.execute("SELECT id, name, quantity, unit, price, supplier FROM materials ORDER BY name")
                self.materials = []
                for row in cursor.fetchall():
                    self.materials.append({
                        'id': row[0],
                        'name': row[1],
                        'quantity': row[2],
                        'unit': row[3],
                        'price': row[4],
                        'supplier': row[5] or ''
                    })
                loaded_any = loaded_any or bool(self.materials)
            except Exception as e:
                print(f"[CIMENT_PAGE] Error loading materials: {e}")
            
            # Load suppliers
            try:
                cursor = conn.execute("SELECT code_fournisseur, nom_fournisseur FROM fournisseurs ORDER BY nom_fournisseur")
                self.suppliers = []
                for row in cursor.fetchall():
                    self.suppliers.append({
                        'id': row[0],
                        'name': row[1],
                        'contact': '',
                        'phone': '',
                        'materials': '',
                        'last_delivery': ''
                    })
                loaded_any = loaded_any or bool(self.suppliers)
            except Exception as e:
                print(f"[CIMENT_PAGE] Error loading suppliers: {e}")
            
            # Load delivery notes
            try:
                cursor = conn.execute(
                    """
                    SELECT bl.id, bl.numero, bl.date_livraison, f.nom_fournisseur, 
                           bl.quantite, bl.unite, bl.montant, bl.statut, bl.description,
                           bl.avoir_payment_before_20_days, bl.avoir_total_factures_200t_month,
                           bl.avoir_sur_livraison, bl.avoir_par_annee
                    FROM bon_livraison bl
                    LEFT JOIN fournisseurs f ON bl.code_fournisseur = f.code_fournisseur
                    ORDER BY bl.date_livraison DESC
                    """
                )
                self.delivery_notes = []
                status_map = {
                    'en_attente': 'En attente',
                    'facturee': 'Facturé',
                    'annulee': 'Annulé'
                }
                for row in cursor.fetchall():
                    db_status = row[7] or 'en_attente'
                    display_status = status_map.get(db_status, 'En attente')
                    date_str = row[2]
                    if date_str and len(date_str) >= 10:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            formatted_date = date_obj.strftime("%d/%m/%Y")
                        except ValueError:
                            formatted_date = date_str
                    else:
                        formatted_date = date_str or ""
                    self.delivery_notes.append({
                        'id': row[0],
                        'number': row[1],
                        'date': formatted_date,
                        'supplier': row[3] or '',
                        'quantity': f"{row[4]} {row[5]}" if row[5] else str(row[4]),
                        'amount': str(row[6]) if row[6] else '0',
                        'status': display_status,
                        'material': row[8] or '',
                        'avoir_payment_before_20_days': row[9] if row[9] is not None else 0,
                        'avoir_total_factures_200t_month': row[10] if row[10] is not None else 0,
                        'avoir_sur_livraison': row[11] if row[11] is not None else 0,
                        'avoir_par_annee': row[12] if row[12] is not None else 0
                    })
                loaded_any = loaded_any or bool(self.delivery_notes)
            except Exception as e:
                print(f"[CIMENT_PAGE] Error loading delivery notes: {e}")

            # Backfill missing BL↔Facture links by parsing achats notes (best effort)
            try:
                self._sync_bl_links_from_achats(conn)
            except Exception as e:
                print(f"[CIMENT_PAGE] Link sync skipped due to error: {e}")

            # Build maps for BL having factures/avoirs
            try:
                self._bl_has_facture = {}
                self._bl_has_avoir = {}
                # Factures
                cur = conn.execute("SELECT bl_id, COUNT(*) FROM bon_livraison_factures GROUP BY bl_id")
                for bl_id, cnt in cur.fetchall():
                    self._bl_has_facture[int(bl_id)] = cnt > 0
                # Avoirs
                cur = conn.execute("SELECT bl_id, COUNT(*) FROM bon_livraison_avoirs GROUP BY bl_id")
                for bl_id, cnt in cur.fetchall():
                    self._bl_has_avoir[int(bl_id)] = cnt > 0
                # Build avoir types map for composite status
                self._build_bl_avoir_types_map(conn)
            except Exception as e:
                print(f"[CIMENT_PAGE] Error building BL link maps: {e}")
        
        print(f"[CIMENT_PAGE] Loaded {len(self.materials)} materials, {len(self.suppliers)} suppliers, {len(self.delivery_notes)} delivery notes")
        
        # Only add sample data if absolutely nothing loaded
        if not loaded_any and not (self.materials or self.suppliers or self.delivery_notes):
            self.add_sample_data()
        else:
            # Check for monthly quantity notifications when BLs are available
            try:
                if self.delivery_notes:
                    self.check_monthly_quantity_notifications()
            except Exception as e:
                print(f"[CIMENT_PAGE] Notification check failed: {e}")
    
    def check_monthly_quantity_notifications(self):
        """Check if any supplier has exceeded 200 tonnes this month and add notification (quiet mode)."""
        try:
            from datetime import datetime
            current_month = datetime.now().strftime('%Y-%m')
            debug = getattr(self, '_debug_ciment', False)
            if debug:
                print(f"[CIMENT_PAGE] Checking 200t notifications for {current_month}")

            # Ensure tracking table exists
            try:
                with self.get_db_connection() as _cinit:
                    _cinit.execute(
                        """
                        CREATE TABLE IF NOT EXISTS ciment_notif_sent (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            notif_type TEXT NOT NULL,
                            supplier TEXT NOT NULL,
                            month TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(notif_type, supplier, month)
                        )
                        """
                    )
                    _cinit.commit()
            except Exception as _e:
                if debug:
                    print(f"[CIMENT_PAGE] Tracking table issue: {_e}")

            with self.get_db_connection() as conn:
                # Aggregate suppliers over 200t any month
                all_months_cursor = conn.execute(
                    """
                    SELECT strftime('%Y-%m', bl.date_livraison) as month, f.nom_fournisseur, SUM(bl.quantite) as total_quantity
                    FROM bon_livraison bl
                    LEFT JOIN fournisseurs f ON bl.code_fournisseur = f.code_fournisseur
                    GROUP BY strftime('%Y-%m', bl.date_livraison), f.nom_fournisseur
                    HAVING SUM(bl.quantite) >= 200
                    ORDER BY month DESC, total_quantity DESC
                    """
                )
                over200 = all_months_cursor.fetchall()
                if debug:
                    print(f"[CIMENT_PAGE] Over-200T records count={len(over200)}")

                # Load sent cache
                sent_cache = set()
                try:
                    cur_sent = conn.execute("SELECT supplier, month FROM ciment_notif_sent WHERE notif_type='200T'")
                    sent_cache = {(r[0], r[1]) for r in cur_sent.fetchall()}
                except Exception as _e:
                    if debug:
                        print(f"[CIMENT_PAGE] Sent cache load fail: {_e}")

                to_record = []
                for month, supplier, qty in over200:
                    key = (supplier or '', month or '')
                    if key in sent_cache:
                        continue
                    self.add_200t_notification([(supplier, qty)], month)
                    to_record.append(key)

                if to_record:
                    try:
                        for supplier, month in to_record:
                            try:
                                conn.execute(
                                    "INSERT OR IGNORE INTO ciment_notif_sent (notif_type, supplier, month) VALUES ('200T', ?, ?)",
                                    (supplier, month)
                                )
                            except Exception:
                                continue
                        conn.commit()
                    except Exception as _e:
                        if debug:
                            print(f"[CIMENT_PAGE] Persist new notif rows fail: {_e}")
                elif debug:
                    print("[CIMENT_PAGE] No new 200T notifications to record")
        except Exception as e:
            if debug:
                print(f"[CIMENT_PAGE] Error checking monthly quantities: {e}")
    
    def add_200t_notification(self, suppliers_data, month):
        """Add notification for suppliers over 200 tonnes this month"""
        try:
            print(f"[CIMENT_PAGE] Adding 200t notification for {len(suppliers_data)} suppliers")
            
            # Format month display in French
            french_months = {
                '01': 'Janvier', '02': 'Février', '03': 'Mars', '04': 'Avril',
                '05': 'Mai', '06': 'Juin', '07': 'Juillet', '08': 'Août',
                '09': 'Septembre', '10': 'Octobre', '11': 'Novembre', '12': 'Décembre'
            }
            
            year, month_num = month.split('-')
            month_name = french_months.get(month_num, month_num)
            month_formatted = f"{month_name} {year}"
            
            # Build supplier list message
            supplier_list = []
            for supplier_name, quantity in suppliers_data:
                supplier_list.append(f"• {supplier_name}: {quantity:.1f} tonnes")
                print(f"[CIMENT_PAGE] Supplier: {supplier_name} = {quantity:.1f}t")
            
            message = f"Les fournisseurs suivants ont dépassé 200 tonnes en {month_formatted}:\n\n"
            message += "\n".join(supplier_list)
            message += "\n\n💡 Pensez à générer un avoir 'Total factures 200 tonnes/mois' pour ces fournisseurs."
            
            print(f"[CIMENT_PAGE] Notification message: {message[:100]}...")
            
            # Add to central notification system
            notification_manager.add_notification(
                title="🔔 Avoir 200 Tonnes - Éligibilité",
                message=message,
                type_="warning",
                data={
                    "suppliers": suppliers_data,
                    "month": month,
                    "action": "avoir_200t_eligible"
                }
            )
            
            print(f"[CIMENT_PAGE] Successfully added 200t notification for {len(suppliers_data)} suppliers")
                    
        except Exception as e:
            print(f"[CIMENT_PAGE] Error adding 200t notification: {e}")
            import traceback
            traceback.print_exc()
    
    def add_sample_data(self):
        """Add sample data to demonstrate functionality"""
        # Sample materials
        self.materials = [
            {'id': 1, 'name': 'Ciment CPJ 42.5', 'quantity': 150.0, 'unit': 'sacs', 'price': 850.0, 'supplier': 'GICA Hadjar Soud'},
            {'id': 2, 'name': 'Gravier 8/15', 'quantity': 25.5, 'unit': 'tonnes', 'price': 1200.0, 'supplier': 'Carrière Boumerdès'},
            {'id': 3, 'name': 'Sable 0/5', 'quantity': 30.2, 'unit': 'tonnes', 'price': 950.0, 'supplier': 'Sablière Tipasa'},
        ]
        
        # Sample suppliers
        self.suppliers = [
            {'id': 1, 'name': 'GICA Hadjar Soud', 'contact': 'Ahmed Benali', 'phone': '0561234567', 'materials': 'Ciment', 'last_delivery': '2025-08-25'},
            {'id': 2, 'name': 'Carrière Boumerdès', 'contact': 'Karim Meziane', 'phone': '0551234567', 'materials': 'Gravier, Pierre', 'last_delivery': '2025-08-22'},
            {'id': 3, 'name': 'Sablière Tipasa', 'contact': 'Farid Hamidi', 'phone': '0541234567', 'materials': 'Sable', 'last_delivery': '2025-08-20'},
        ]
        
        # Sample delivery notes
        self.delivery_notes = [
            {'id': 1, 'number': 'BL001', 'date': '28/08/25', 'supplier': 'GICA Hadjar Soud', 'material': 'Ciment CPJ 42.5', 'quantity': '50 sacs', 'amount': '42500', 'status': 'En attente'},
            {'id': 2, 'number': 'BL002', 'date': '27/08/25', 'supplier': 'Carrière Boumerdès', 'material': 'Gravier 8/15', 'quantity': '10 tonnes', 'amount': '12000', 'status': 'Facturé'},
        ]
    
    def setup_ui(self):
        """Setup the main UI layout"""
        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header section
        self.create_header(main_frame)
        
        # Create tabbed interface
        self.create_tabs(main_frame)
        
        # Status bar
        self.create_status_bar(main_frame)
        
        # Load initial data
        self.refresh_all_data()
    
    def create_header(self, parent):
        """Create header with title and navigation"""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill="x", pady=(0, 10))
        
        # Back button
        if self.go_back:
            back_btn = ttk.Button(
                header_frame, 
                text="🏠 Retour",
                command=self.go_back,
                style="Accent.TButton"
            )
            back_btn.pack(side="left")
        
        # Title
        title_label = ttk.Label(
            header_frame,
            text="🏗️ Ciment / Matière Première",
            font=("Segoe UI", 18, "bold")
        )
        title_label.pack(side="left", padx=(20, 0))
        
        # Status indicator
        self.status_indicator = ttk.Label(
            header_frame,
            text="✅ Système opérationnel",
            font=("Segoe UI", 10),
            foreground="green"
        )
        self.status_indicator.pack(side="right")
    
    def create_tabs(self, parent):
        """Create tabbed interface"""
        self.notebook = ttk.Notebook(parent)
        self.notebook.pack(fill="both", expand=True)
        
        # Tab 1: Materials Inventory
        self.create_inventory_tab()
        
        # Tab 2: Delivery Notes
        self.create_delivery_tab()
        
        # Tab 3: Suppliers
        self.create_suppliers_tab()
        
        # Tab 4: Avoir (Credit Notes)
        self.create_avoir_tab()
        
        # Tab 5: Statistics
        self.create_statistics_tab()
    
    def create_inventory_tab(self):
        """Create materials inventory tab"""
        inventory_frame = ttk.Frame(self.notebook)
        self.notebook.add(inventory_frame, text="📦 Inventaire")
        
        # Toolbar
        toolbar = ttk.Frame(inventory_frame)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(
            toolbar, 
            text="➕ Ajouter Matériau",
            command=self.add_material,
            style="Success.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="✏️ Modifier",
            command=self.edit_material
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="🗑️ Supprimer",
            command=self.delete_material
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="🔄 Actualiser",
            command=self.refresh_materials
        ).pack(side="left")
        
        # Materials list
        list_frame = ttk.LabelFrame(inventory_frame, text="Matériaux", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Create Treeview
        columns = ("name", "quantity", "unit", "price", "supplier")
        self.materials_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")
        
        self.materials_tree.heading("#0", text="ID")
        self.materials_tree.heading("name", text="Nom")
        self.materials_tree.heading("quantity", text="Quantité")
        self.materials_tree.heading("unit", text="Unité")
        self.materials_tree.heading("price", text="Prix")
        self.materials_tree.heading("supplier", text="Fournisseur")
        
        # Configure column widths
        self.materials_tree.column("#0", width=50)
        self.materials_tree.column("name", width=150)
        self.materials_tree.column("quantity", width=100)
        self.materials_tree.column("unit", width=80)
        self.materials_tree.column("price", width=100)
        self.materials_tree.column("supplier", width=120)
        
        self.materials_tree.pack(fill="both", expand=True)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.materials_tree.yview)
        self.materials_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        
        # Context menu
        self.create_material_context_menu()
        self.materials_tree.bind("<Button-3>", self.show_material_context_menu)
    
    def create_delivery_tab(self):
        """Create delivery notes tab"""
        delivery_frame = ttk.Frame(self.notebook)
        self.notebook.add(delivery_frame, text="📝 Bons de Livraison")
        
        # Toolbar
        toolbar = ttk.Frame(delivery_frame)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(
            toolbar, 
            text="➕ Nouveau BL",
            command=self.create_delivery_note,
            style="Success.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="✏️ Modifier",
            command=self.edit_delivery_note
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="🗑️ Supprimer",
            command=self.delete_delivery_note
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="📄 Générer Facture",
            command=self.generate_invoice
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="� Générer Avoir",
            command=self.generate_avoir_from_bl,
            style="Warning.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="�🔄 Actualiser",
            command=self.refresh_deliveries
        ).pack(side="left")

        # Separator
        sep = ttk.Separator(toolbar, orient='vertical')
        sep.pack(side="left", fill="y", padx=10)

        # BL Supplier filter: only suppliers present in BLs, no 'All' option
        ttk.Label(toolbar, text="Fournisseur BL:").pack(side="left", padx=(0, 6))
        self.delivery_supplier_var = tk.StringVar()
        self.delivery_supplier_combo = ttk.Combobox(toolbar, textvariable=self.delivery_supplier_var, state="readonly", width=32)
        self.delivery_supplier_combo.pack(side="left")

        def _on_delivery_supplier_selected(event=None):
            # Reload the delivery list when filter changes
            self.refresh_deliveries()
            # Update BC display for selected supplier
            self._update_bc_display()
        self.delivery_supplier_combo.bind("<<ComboboxSelected>>", _on_delivery_supplier_selected)
        
        # Bon de Commande Tracking Panel
        bc_frame = ttk.LabelFrame(delivery_frame, text="📋 Bon de Commande (Suivi)", padding=10)
        bc_frame.pack(fill="x", padx=10, pady=(5, 5))
        
        # BC Input Row
        bc_input_row = ttk.Frame(bc_frame)
        bc_input_row.pack(fill="x")
        
        # BC Number
        ttk.Label(bc_input_row, text="N° BC:").pack(side="left", padx=(0, 5))
        self.bc_numero_var = tk.StringVar()
        bc_numero_entry = ttk.Entry(bc_input_row, textvariable=self.bc_numero_var, width=15)
        bc_numero_entry.pack(side="left", padx=(0, 15))
        
        # BC Date
        ttk.Label(bc_input_row, text="Date BC:").pack(side="left", padx=(0, 5))
        self.bc_date_entry = DateEntry(
            bc_input_row,
            width=12,
            background='darkblue',
            foreground='white',
            borderwidth=2,
            date_pattern='dd/mm/yy'
        )
        self.bc_date_entry.pack(side="left", padx=(0, 15))
        
        # BC Quantity
        ttk.Label(bc_input_row, text="Qté BC:").pack(side="left", padx=(0, 5))
        self.bc_quantite_var = tk.StringVar()
        bc_quantite_entry = ttk.Entry(bc_input_row, textvariable=self.bc_quantite_var, width=10)
        bc_quantite_entry.pack(side="left", padx=(0, 5))
        ttk.Label(bc_input_row, text="T").pack(side="left", padx=(0, 15))
        
        # Save BC Button
        ttk.Button(
            bc_input_row,
            text="💾 Enregistrer BC",
            command=self._save_bon_commande,
            style="Success.TButton"
        ).pack(side="left", padx=(0, 10))
        
        # BC Status Display Row
        bc_status_row = ttk.Frame(bc_frame)
        bc_status_row.pack(fill="x", pady=(10, 0))
        
        self.bc_status_label = ttk.Label(
            bc_status_row,
            text="Aucun BC actif pour ce fournisseur",
            font=("Segoe UI", 10),
            foreground="gray"
        )
        self.bc_status_label.pack(side="left")
        
        # Progress bar for BC tracking
        self.bc_progress_var = tk.DoubleVar(value=0)
        self.bc_progress = ttk.Progressbar(
            bc_status_row,
            variable=self.bc_progress_var,
            maximum=100,
            length=200,
            mode='determinate'
        )
        self.bc_progress.pack(side="right", padx=(10, 0))
        
        self.bc_progress_label = ttk.Label(bc_status_row, text="0%", font=("Segoe UI", 9))
        self.bc_progress_label.pack(side="right", padx=(0, 5))
        
        # Delivery notes list
        list_frame = ttk.LabelFrame(delivery_frame, text="Bons de Livraison", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 5))
        
        # Create Treeview with EXTENDED selection mode (Excel-style multi-select)
        columns = ("date", "number", "supplier", "material", "quantity", "amount", "status")
        self.delivery_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings", selectmode="extended")
        
        self.delivery_tree.heading("#0", text="ID")
        self.delivery_tree.heading("date", text="Date")
        self.delivery_tree.heading("number", text="Numéro")
        self.delivery_tree.heading("supplier", text="Fournisseur")
        self.delivery_tree.heading("material", text="Matériau")
        self.delivery_tree.heading("quantity", text="Quantité")
        self.delivery_tree.heading("amount", text="Montant")
        self.delivery_tree.heading("status", text="État")
        
        # Configure column widths
        self.delivery_tree.column("#0", width=50)
        self.delivery_tree.column("date", width=100)
        self.delivery_tree.column("number", width=100)
        self.delivery_tree.column("supplier", width=120)
        self.delivery_tree.column("material", width=100)
        self.delivery_tree.column("quantity", width=80)
        self.delivery_tree.column("amount", width=100)
        # Wider composite status: F/20j/200t/TR/AN
        self.delivery_tree.column("status", width=180)
        
        self.delivery_tree.pack(fill="both", expand=True)
        
        # Configure color tags for status visualization
        self.delivery_tree.tag_configure('red', background='#ffebee', foreground='#c62828')     # en attente
        self.delivery_tree.tag_configure('yellow', background='#fff9c4', foreground='#f57f17')  # facturé
        self.delivery_tree.tag_configure('green', background='#e8f5e8', foreground='#2e7d32')   # facturé + avoir réalisé
        
        # Add scrollbar
        scrollbar2 = ttk.Scrollbar(list_frame, orient="vertical", command=self.delivery_tree.yview)
        self.delivery_tree.configure(yscrollcommand=scrollbar2.set)
        scrollbar2.pack(side="right", fill="y")
        
        # Bind selection change to update summary
        self.delivery_tree.bind("<<TreeviewSelect>>", self._update_selection_summary)
        
        # Add Ctrl+A for select all
        self.delivery_tree.bind("<Control-a>", self._select_all_deliveries)
        
        # Selection Summary Bar (bottom)
        summary_frame = ttk.Frame(delivery_frame, relief="sunken", borderwidth=1)
        summary_frame.pack(fill="x", padx=10, pady=(0, 5))
        
        # Summary labels with modern styling
        summary_inner = ttk.Frame(summary_frame, padding=8)
        summary_inner.pack(fill="x")
        
        ttk.Label(summary_inner, text="📦 Sélection:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 10))
        
        self.selection_count_label = ttk.Label(summary_inner, text="0 BL", font=("Segoe UI", 9))
        self.selection_count_label.pack(side="left", padx=(0, 15))
        
        ttk.Label(summary_inner, text="📊 Qté:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 5))
        self.selection_qty_label = ttk.Label(summary_inner, text="0", font=("Segoe UI", 9))
        self.selection_qty_label.pack(side="left", padx=(0, 15))
        
        ttk.Label(summary_inner, text="💰 Facture:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 5))
        self.selection_facture_label = ttk.Label(summary_inner, text="0.000 DA", font=("Segoe UI", 9))
        self.selection_facture_label.pack(side="left", padx=(0, 15))
        
        ttk.Label(summary_inner, text="💳 Avoir:", font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 5))
        self.selection_avoir_label = ttk.Label(summary_inner, text="0.000 DA", font=("Segoe UI", 9), foreground="#1976d2")
        self.selection_avoir_label.pack(side="left")
        
        # Help text on the right
        help_label = ttk.Label(summary_inner, text="💡 Ctrl+Click = sélection multiple | Shift+Click = plage | Ctrl+A = tout", 
                              font=("Segoe UI", 8, "italic"), foreground="gray")
        help_label.pack(side="right")
    
    def create_suppliers_tab(self):
        """Create suppliers management tab"""
        suppliers_frame = ttk.Frame(self.notebook)
        self.notebook.add(suppliers_frame, text="🏭 Fournisseurs")
        
        # Toolbar
        toolbar = ttk.Frame(suppliers_frame)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Button(
            toolbar, 
            text="➕ Ajouter Fournisseur",
            command=self.add_supplier,
            style="Success.TButton"
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="✏️ Modifier",
            command=self.edit_supplier
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="🗑️ Supprimer",
            command=self.delete_supplier
        ).pack(side="left", padx=(0, 5))
        
        ttk.Button(
            toolbar, 
            text="🔄 Actualiser",
            command=self.refresh_suppliers
        ).pack(side="left")
        
        # Suppliers list
        list_frame = ttk.LabelFrame(suppliers_frame, text="Fournisseurs", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Create Treeview
        columns = ("name", "contact", "phone", "materials", "last_delivery")
        self.suppliers_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")
        
        self.suppliers_tree.heading("#0", text="ID")
        self.suppliers_tree.heading("name", text="Nom")
        self.suppliers_tree.heading("contact", text="Contact")
        self.suppliers_tree.heading("phone", text="Téléphone")
        self.suppliers_tree.heading("materials", text="Matériaux")
        self.suppliers_tree.heading("last_delivery", text="Dernière Livraison")
        
        # Configure column widths
        self.suppliers_tree.column("#0", width=50)
        self.suppliers_tree.column("name", width=150)
        self.suppliers_tree.column("contact", width=120)
        self.suppliers_tree.column("phone", width=100)
        self.suppliers_tree.column("materials", width=150)
        self.suppliers_tree.column("last_delivery", width=100)
        
        self.suppliers_tree.pack(fill="both", expand=True)
        
        # Add scrollbar
        scrollbar3 = ttk.Scrollbar(list_frame, orient="vertical", command=self.suppliers_tree.yview)
        self.suppliers_tree.configure(yscrollcommand=scrollbar3.set)
        scrollbar3.pack(side="right", fill="y")
    
    def create_avoir_tab(self):
        """Create avoir (credit notes) tab"""
        avoir_frame = ttk.Frame(self.notebook)
        self.notebook.add(avoir_frame, text="📋 Avoir")
        
        # Toolbar
        toolbar = ttk.Frame(avoir_frame)
        toolbar.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(
            toolbar, 
            text="💡 Conseil: Générez les avoirs depuis l'onglet 'Bons de Livraison'",
            font=("Segoe UI", 9, "italic")
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            toolbar, 
            text="🔄 Actualiser",
            command=self.refresh_avoirs
        ).pack(side="right")
        
        # Avoirs list
        list_frame = ttk.LabelFrame(avoir_frame, text="Avoirs Générés", padding=10)
        list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))
        
        # Create Treeview for avoirs
        columns = ("date", "fournisseur", "numero", "mt_ht", "tva", "ttc", "statut")
        self.avoirs_tree = ttk.Treeview(list_frame, columns=columns, show="tree headings")
        
        self.avoirs_tree.heading("#0", text="ID")
        self.avoirs_tree.heading("date", text="Date")
        self.avoirs_tree.heading("fournisseur", text="Fournisseur")
        self.avoirs_tree.heading("numero", text="N° Avoir")
        self.avoirs_tree.heading("mt_ht", text="Montant HT")
        self.avoirs_tree.heading("tva", text="TVA")
        self.avoirs_tree.heading("ttc", text="Total TTC")
        self.avoirs_tree.heading("statut", text="Statut")
        
        # Column widths
        self.avoirs_tree.column("#0", width=50)
        self.avoirs_tree.column("date", width=80)
        self.avoirs_tree.column("fournisseur", width=150)
        self.avoirs_tree.column("numero", width=120)
        self.avoirs_tree.column("mt_ht", width=100)
        self.avoirs_tree.column("tva", width=80)
        self.avoirs_tree.column("ttc", width=100)
        self.avoirs_tree.column("statut", width=100)
        
        # Scrollbar
        scrollbar_avoir = ttk.Scrollbar(list_frame, orient="vertical", command=self.avoirs_tree.yview)
        self.avoirs_tree.configure(yscrollcommand=scrollbar_avoir.set)
        
        self.avoirs_tree.pack(side="left", fill="both", expand=True)
        scrollbar_avoir.pack(side="right", fill="y")
        
        # Load initial data
        self.refresh_avoirs()
    
    def create_statistics_tab(self):
        """Create statistics and reports tab"""
        stats_frame = ttk.Frame(self.notebook)
        self.notebook.add(stats_frame, text="📊 Statistiques")
        
        # Statistics content
        content_frame = ttk.Frame(stats_frame)
        content_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        ttk.Label(
            content_frame, 
            text="📊 Statistiques et Rapports",
            font=("Segoe UI", 16, "bold")
        ).pack(pady=(0, 20))
        
        # Quick stats frame
        quick_stats_frame = ttk.LabelFrame(content_frame, text="Statistiques Rapides", padding=15)
        quick_stats_frame.pack(fill="x", pady=(0, 20))
        
        # Stats labels
        self.stats_materials = ttk.Label(quick_stats_frame, text="Matériaux: 0", font=("Segoe UI", 12))
        self.stats_materials.pack(anchor="w", pady=2)
        
        self.stats_suppliers = ttk.Label(quick_stats_frame, text="Fournisseurs: 0", font=("Segoe UI", 12))
        self.stats_suppliers.pack(anchor="w", pady=2)
        
        self.stats_deliveries = ttk.Label(quick_stats_frame, text="BL ce mois: 0", font=("Segoe UI", 12))
        self.stats_deliveries.pack(anchor="w", pady=2)
        
        # Actions frame
        actions_frame = ttk.LabelFrame(content_frame, text="Actions", padding=15)
        actions_frame.pack(fill="x", pady=(0, 20))
        
        ttk.Button(
            actions_frame, 
            text="📈 Actualiser Statistiques",
            command=self.update_statistics
        ).pack(anchor="w", pady=2)
        
        ttk.Button(
            actions_frame, 
            text="📄 Rapport Mensuel",
            command=self.generate_monthly_report
        ).pack(anchor="w", pady=2)
        
        # Initialize stats
        self.update_statistics()
    
    def create_status_bar(self, parent):
        """Create status bar"""
        status_frame = ttk.Frame(parent)
        status_frame.pack(fill="x", pady=(10, 0))
        
        self.status_label = ttk.Label(status_frame, text="Prêt", relief="sunken")
        self.status_label.pack(side="left", fill="x", expand=True)
        
        self.items_count_label = ttk.Label(status_frame, text="0 éléments", relief="sunken")
        self.items_count_label.pack(side="right")
    
    def create_material_context_menu(self):
        """Create context menu for materials"""
        self.material_context_menu = tk.Menu(self, tearoff=0)
        self.material_context_menu.add_command(label="✏️ Modifier", command=self.edit_material)
        self.material_context_menu.add_command(label="🗑️ Supprimer", command=self.delete_material)
        self.material_context_menu.add_separator()
        self.material_context_menu.add_command(label="📊 Détails", command=self.show_material_details)
    
    def show_material_context_menu(self, event):
        """Show context menu for materials"""
        item = self.materials_tree.identify_row(event.y)
        if item:
            self.materials_tree.selection_set(item)
            self.material_context_menu.post(event.x_root, event.y_root)
    
    # Event handlers
    def add_material(self):
        """Add new material"""
        dialog = MaterialDialog(self, "Ajouter Matériau")
        if dialog.result:
            material = dialog.result
            try:
                with self.get_db_connection() as conn:
                    cursor = conn.execute("""
                        INSERT INTO materials (name, quantity, unit, price, supplier, minimum_stock)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        material['name'],
                        material['quantity'],
                        material['unit'],
                        material['price'],
                        material.get('supplier', ''),
                        material.get('minimum_stock', 0)
                    ))
                    material_id = cursor.lastrowid
                    material['id'] = material_id
                    self.materials.append(material)
                    self.refresh_materials()
                    self.update_status(f"Matériau '{material['name']}' ajouté avec succès")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'ajout du matériau: {e}")
    
    def edit_material(self):
        """Edit selected material"""
        selection = self.materials_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        material_id = int(self.materials_tree.item(item, "text"))
        
        # Find material
        material = next((m for m in self.materials if m['id'] == material_id), None)
        if not material:
            return
        
        dialog = MaterialDialog(self, "Modifier Matériau", material)
        if dialog.result:
            updated_material = dialog.result
            try:
                with self.get_db_connection() as conn:
                    conn.execute("""
                        UPDATE materials 
                        SET name=?, quantity=?, unit=?, price=?, supplier=?, minimum_stock=?
                        WHERE id=?
                    """, (
                        updated_material['name'],
                        updated_material['quantity'],
                        updated_material['unit'],
                        updated_material['price'],
                        updated_material.get('supplier', ''),
                        updated_material.get('minimum_stock', 0),
                        material_id
                    ))
                    material.update(updated_material)
                    self.refresh_materials()
                    self.update_status(f"Matériau '{material['name']}' modifié")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la modification: {e}")
    
    def delete_material(self):
        """Delete selected material"""
        selection = self.materials_tree.selection()
        if not selection:
            messagebox.showwarning("Attention", "Sélectionnez un matériau à supprimer")
            return
        
        if messagebox.askyesno("Confirmer", "Êtes-vous sûr de vouloir supprimer ce matériau?"):
            item = selection[0]
            material_id = int(self.materials_tree.item(item, "text"))
            try:
                with self.get_db_connection() as conn:
                    conn.execute("DELETE FROM materials WHERE id = ?", (material_id,))
                    conn.commit()  # CRITICAL FIX: Commit the deletion!
                    self.materials = [m for m in self.materials if m['id'] != material_id]
                    self.refresh_materials()
                    self.update_status(f"Matériau supprimé - ID: {material_id}")
                    print(f"[CIMENT] Successfully deleted material {material_id}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
    
    def show_material_details(self):
        """Show material details"""
        selection = self.materials_tree.selection()
        if not selection:
            return
        
        item = selection[0]
        material_id = int(self.materials_tree.item(item, "text"))
        material = next((m for m in self.materials if m['id'] == material_id), None)
        
        if material:
            details = f"Détails du Matériau\\n\\n"
            details += f"Nom: {material['name']}\\n"
            details += f"Quantité: {material['quantity']} {material['unit']}\\n"
            details += f"Prix: {material['price']} DA\\n"
            details += f"Fournisseur: {material['supplier']}\\n"
            
            messagebox.showinfo("Détails du Matériau", details)
    
    def create_delivery_note(self):
        """Create new delivery note with proper inventory integration"""
        if not self.materials:
            messagebox.showwarning("Attention", "Veuillez d'abord ajouter des matériaux")
            return
        
        if not self.suppliers:
            messagebox.showwarning("Attention", "Veuillez d'abord ajouter des fournisseurs")
            return
        
        dialog = DeliveryDialog(self, "Nouveau Bon de Livraison", self.materials, self.suppliers)
        if dialog.result:
            delivery = dialog.result
            try:
                with self.get_db_connection() as conn:
                    # Find supplier code
                    supplier_code = None
                    for supplier in self.suppliers:
                        if supplier['name'] == delivery['supplier']:
                            supplier_code = supplier['id']
                            break
                    
                    if not supplier_code:
                        messagebox.showerror("Erreur", "Fournisseur non trouvé")
                        return
                    
                    # Find material ID for proper inventory integration
                    material_id = None
                    selected_material = None
                    for material in self.materials:
                        if material.get('name', '') == delivery.get('material', ''):
                            material_id = material.get('id')
                            selected_material = material
                            break
                    
                    if not material_id:
                        messagebox.showerror("Erreur", "Matériau non trouvé dans l'inventaire")
                        return
                    
                    # Convert date from dd/mm/yy to YYYY-MM-DD for database
                    try:
                        date_obj = datetime.strptime(delivery['date'], "%d/%m/%y")
                        db_date = date_obj.strftime("%Y-%m-%d")
                    except ValueError:
                        # Try other date formats before falling back
                        try:
                            date_obj = datetime.strptime(delivery['date'], "%d/%m/%Y")
                            db_date = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            # If all parsing fails, keep the original date format
                            print(f"[CIMENT] Warning: Could not parse date '{delivery['date']}', using as-is")
                            db_date = delivery['date']
                    
                    # Parse quantity
                    quantity_value = float(delivery['quantity'].split()[0]) if ' ' in delivery['quantity'] else float(delivery['quantity'])
                    unit_value = delivery['quantity'].split()[1] if ' ' in delivery['quantity'] else 'tonnes'
                    
                    cursor = conn.execute("""
                        INSERT INTO bon_livraison (numero, date_livraison, code_fournisseur, quantite, unite, montant, 
                                                  description, material_id, statut,
                                                  avoir_payment_before_20_days, avoir_total_factures_200t_month, 
                                                  avoir_sur_livraison, avoir_par_annee)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        delivery['number'],
                        db_date,  # Use converted date
                        supplier_code,
                        quantity_value,
                        unit_value,
                        float(delivery['amount']),
                        selected_material['name'],  # Use full material name as description
                        material_id,  # Link to inventory
                        'en_attente',
                        delivery.get('avoir_payment_before_20_days', 1),
                        delivery.get('avoir_total_factures_200t_month', 1),
                        delivery.get('avoir_sur_livraison', 0),
                        delivery.get('avoir_par_annee', 0)
                    ))
                    
                    delivery_id = cursor.lastrowid
                    
                    # Update material inventory quantity if it's an incoming delivery
                    # Note: This is a delivery FROM supplier TO us, so we ADD to our inventory
                    if selected_material:
                        current_quantity = selected_material.get('quantity', 0)
                        new_quantity = current_quantity + quantity_value
                        
                        cursor.execute("""
                            UPDATE materials 
                            SET quantity = ?, updated_at = CURRENT_TIMESTAMP 
                            WHERE id = ?
                        """, (new_quantity, material_id))
                        
                        print(f"[CIMENT] Updated inventory for {selected_material['name']}: {current_quantity} + {quantity_value} = {new_quantity} {unit_value}")
                    
                    # Prepare delivery object for UI
                    delivery['id'] = delivery_id
                    delivery['status'] = "En attente"
                    
                    # Update status with inventory info
                    self.update_status(f"BL {delivery['number']} créé avec succès - Stock {selected_material['name']}: {new_quantity:.1f} {unit_value}")
                    
                    # Reload from DB to reflect latest BL and inventory, then refresh UI lists
                    self.load_data_from_database()
                    self.refresh_materials()
                    self.refresh_deliveries()
                    
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la création du BL: {e}")
                print(f"[CIMENT] Error creating delivery note: {e}")
                import traceback
                traceback.print_exc()
    
    def generate_bl_number(self):
        """Generate automatic BL number - DISABLED: No auto-fill requested"""
        # Return empty string instead of auto-generating
        return ""
    
    def generate_invoice(self):
        """Generate invoice from selected delivery notes"""
        # Get selected delivery notes
        selected_deliveries = []
        total_qty = 0.0
        selection = self.delivery_tree.selection()
        
        if not selection:
            # If no selection, show all pending deliveries
            pending_deliveries = [d for d in self.delivery_notes if d['status'] == "En attente"]
            if not pending_deliveries:
                messagebox.showinfo("Information", "Aucun BL en attente pour facturation")
                return
            selected_deliveries = pending_deliveries
        else:
            # Get selected delivery notes
            for item in selection:
                try:
                    delivery_id = int(self.delivery_tree.item(item, "text"))
                    delivery = next((d for d in self.delivery_notes if d['id'] == delivery_id), None)
                    if delivery and delivery['status'] == "En attente":
                        selected_deliveries.append(delivery)
                except (ValueError, TypeError):
                    continue
        
        if not selected_deliveries:
            messagebox.showwarning("Attention", "Sélectionnez des BL en attente pour facturation")
            return
        
        # Calculate total quantity
        for delivery in selected_deliveries:
            qty_str = str(delivery.get('quantity', '0'))
            try:
                if ' ' in qty_str:
                    qty = float(qty_str.split()[0])
                else:
                    qty = float(qty_str)
                total_qty += qty
            except (ValueError, IndexError):
                pass
        
        # Show confirmation with quantity total
        confirm_msg = f"📄 Générer facture pour {len(selected_deliveries)} BL\n\n"
        confirm_msg += f"📊 Quantité totale: {total_qty:.1f} tonnes\n\n"
        confirm_msg += "Continuer?"
        
        if not messagebox.askyesno("Confirmation", confirm_msg):
            return
        
        # Open auto-filled achat dialog
        dialog = CimentFactureDialog(self, selected_deliveries, self.materials)
        if dialog.result:
            facture_data = dialog.result
            
            try:
                with self.get_db_connection() as conn:
                    # Normalize date format to ISO for DB
                    date_for_db = self._normalize_date_for_db(facture_data['date'])
                    
                    # Convert taxes from list to JSON string for database
                    import json
                    taxes_json = json.dumps(facture_data['taxes']) if facture_data['taxes'] else '[]'
                    
                    # Insert into achats table
                    cursor = conn.execute("""
                        INSERT INTO achats (date, fournisseur, num_facture, mt_ht, ttc, timbre, taxes, notes, paiement_statut, paiement_methode, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        date_for_db,
                        facture_data['fournisseur'],
                        facture_data['num_facture'],
                        facture_data['mt_ht'],
                        facture_data['ttc'],
                        facture_data['timbre'],
                        taxes_json,
                        facture_data['notes'],
                        facture_data['paiement_statut'],
                        facture_data['paiement_methode'],
                        facture_data['created_at']
                    ))
                    
                    achat_id = cursor.lastrowid
                    print(f"[CIMENT] Facture saved to achats table with ID: {achat_id}")
                    
                    # Mark deliveries as invoiced in database
                    for delivery in selected_deliveries:
                        conn.execute("""
                            UPDATE bon_livraison 
                            SET statut = 'facturee'
                            WHERE id = ?
                        """, (delivery['id'],))
                        # Link BL ↔ facture
                        try:
                            conn.execute(
                                "INSERT INTO bon_livraison_factures (bl_id, achat_id) VALUES (?, ?)",
                                (delivery['id'], achat_id)
                            )
                        except Exception as link_err:
                            print(f"[CIMENT] Link insert skipped for BL {delivery['id']}: {link_err}")
                        delivery['status'] = "Facturé"  # Update in memory too
                    
                    conn.commit()
                    print(f"[CIMENT] Updated {len(selected_deliveries)} BL status to 'facturee'")
                    
                    success_msg = f"✅ Facture {facture_data['num_facture']} enregistrée avec succès!\n\n"
                    success_msg += f"💾 Enregistrée dans le module Achat avec ID: {achat_id}\n"
                    success_msg += f"📋 {len(selected_deliveries)} BL marqués comme facturés"
                    
                    messagebox.showinfo("Succès", success_msg)
                    
            except Exception as e:
                print(f"[CIMENT] Error saving facture to achats: {e}")
                import traceback
                traceback.print_exc()
                messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement de la facture:\n{e}")
                return
            
            self.refresh_deliveries()
            self.update_status(f"Facture générée et enregistrée pour {len(selected_deliveries)} BL")
    
    def add_supplier(self):
        """Add new supplier"""
        dialog = SupplierDialog(self, "Ajouter Fournisseur")
        if dialog.result:
            supplier = dialog.result
            try:
                with self.get_db_connection() as conn:
                    # Generate code_fournisseur
                    cursor = conn.execute("SELECT COUNT(*) FROM fournisseurs")
                    count = cursor.fetchone()[0]
                    code_fournisseur = f"F{count + 1:03d}"
                    
                    conn.execute("""
                        INSERT INTO fournisseurs (code_fournisseur, nom_fournisseur)
                        VALUES (?, ?)
                    """, (code_fournisseur, supplier['name']))
                    
                    supplier['id'] = code_fournisseur
                    supplier['last_delivery'] = "Jamais"
                    self.suppliers.append(supplier)
                    self.refresh_suppliers()
                    self.update_status(f"Fournisseur '{supplier['name']}' ajouté avec succès")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de l'ajout du fournisseur: {e}")
    
    def edit_delivery_note(self):
        """Edit selected delivery note"""
        item = self.delivery_tree.selection()
        if not item:
            messagebox.showwarning("Attention", "Sélectionnez un bon de livraison à modifier")
            return
        
        delivery_id = int(self.delivery_tree.item(item[0], "text"))
        delivery_note = next((d for d in self.delivery_notes if d['id'] == delivery_id), None)
        
        if delivery_note:
            dialog = DeliveryDialog(self, "Modifier Bon de Livraison", self.materials, self.suppliers, delivery_note)
            if dialog.result:
                updated_delivery = dialog.result
                try:
                    with self.get_db_connection() as conn:
                        # Convert date from dd/mm/yy to YYYY-MM-DD for database if needed
                        date_for_db = updated_delivery['date']
                        try:
                            date_obj = datetime.strptime(updated_delivery['date'], "%d/%m/%y")
                            date_for_db = date_obj.strftime("%Y-%m-%d")
                        except ValueError:
                            try:
                                date_obj = datetime.strptime(updated_delivery['date'], "%d/%m/%Y")
                                date_for_db = date_obj.strftime("%Y-%m-%d")
                            except ValueError:
                                # If parsing fails, assume it's already in YYYY-MM-DD format
                                print(f"[CIMENT] Warning: Could not parse date '{updated_delivery['date']}', using as-is")
                                date_for_db = updated_delivery['date']

                        # Parse quantity and unit robustly
                        qty_str = str(updated_delivery.get('quantity', '')).strip().replace(',', '.')
                        qty_val = None
                        unit_val = None
                        try:
                            # Try split form like "50 sacs"
                            parts = qty_str.split()
                            if len(parts) >= 1:
                                qty_val = float(parts[0])
                                if len(parts) >= 2:
                                    unit_val = parts[1]
                        except Exception:
                            pass
                        # Fallbacks
                        if qty_val is None:
                            try:
                                qty_val = float(qty_str)
                            except Exception:
                                qty_val = 0.0

                        # Preserve existing unit if not provided by user
                        if not unit_val:
                            cur = conn.execute("SELECT unite FROM bon_livraison WHERE id = ?", (delivery_id,)).fetchone()
                            unit_val = (cur[0] if cur and cur[0] else 'tonnes')

                        # Resolve supplier code if changed
                        supplier_name = updated_delivery.get('supplier') or ''
                        supplier_code = None
                        if supplier_name:
                            for s in self.suppliers:
                                if (s.get('name') or '').strip() == supplier_name.strip():
                                    supplier_code = s.get('id')  # 'id' holds code_fournisseur in this page
                                    break

                        # Resolve material_id by name and also set description to material name
                        material_name = updated_delivery.get('material') or ''
                        material_id = None
                        if material_name:
                            for m in self.materials:
                                if (m.get('name') or '').strip() == material_name.strip():
                                    material_id = m.get('id')
                                    break

                        # Build UPDATE with all relevant fields so changes persist
                        conn.execute(
                            """
                            UPDATE bon_livraison 
                            SET date_livraison = ?,
                                code_fournisseur = COALESCE(?, code_fournisseur),
                                quantite = ?,
                                unite = ?,
                                montant = ?,
                                description = ?,
                                material_id = COALESCE(?, material_id),
                                avoir_payment_before_20_days = ?,
                                avoir_total_factures_200t_month = ?,
                                avoir_sur_livraison = ?,
                                avoir_par_annee = ?,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = ?
                            """,
                            (
                                date_for_db,
                                supplier_code,
                                float(qty_val),
                                unit_val,
                                float(updated_delivery.get('amount', 0) or 0),
                                material_name,
                                material_id,
                                updated_delivery.get('avoir_payment_before_20_days', 1),
                                updated_delivery.get('avoir_total_factures_200t_month', 1),
                                updated_delivery.get('avoir_sur_livraison', 0),
                                updated_delivery.get('avoir_par_annee', 0),
                                delivery_id,
                            ),
                        )

                        conn.commit()

                        # Reload from DB then refresh UI to ensure consistency
                        self.load_data_from_database()
                        self.refresh_deliveries()
                        self.update_status(f"Bon de livraison modifié avec succès - ID: {delivery_id}")
                        print(f"[CIMENT] Successfully updated BL ID {delivery_id}")
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la modification: {e}")
    
    def delete_delivery_note(self):
        """Delete selected delivery note"""
        item = self.delivery_tree.selection()
        if not item:
            messagebox.showwarning("Attention", "Sélectionnez un bon de livraison à supprimer")
            return
        
        if messagebox.askyesno("Confirmer", "Êtes-vous sûr de vouloir supprimer ce bon de livraison?"):
            delivery_id = int(self.delivery_tree.item(item[0], "text"))
            try:
                with self.get_db_connection() as conn:
                    conn.execute("DELETE FROM bon_livraison WHERE id = ?", (delivery_id,))
                    conn.commit()  # CRITICAL FIX: Commit the deletion!
                    # Reload from DB and refresh UI to reflect deletion immediately
                    self.load_data_from_database()
                    self.refresh_deliveries()
                    self.update_status(f"Bon de livraison supprimé - ID: {delivery_id}")
                    print(f"[CIMENT] Successfully deleted BL ID {delivery_id}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
    
    # ============================================================================
    # BON DE COMMANDE (PURCHASE ORDER) TRACKING METHODS
    # ============================================================================
    
    def _save_bon_commande(self):
        """Save or update Bon de Commande for currently selected supplier"""
        selected_supplier = self._get_selected_delivery_supplier()
        
        if not selected_supplier:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur pour enregistrer le BC")
            return
        
        bc_numero = self.bc_numero_var.get().strip()
        bc_date_str = self.bc_date_entry.get()
        bc_quantite_str = self.bc_quantite_var.get().strip()
        
        if not bc_date_str or not bc_quantite_str:
            messagebox.showwarning("Attention", "Date BC et Quantité sont requis")
            return
        
        try:
            bc_quantite = float(bc_quantite_str)
            if bc_quantite <= 0:
                messagebox.showerror("Erreur", "La quantité doit être positive")
                return
        except ValueError:
            messagebox.showerror("Erreur", "Quantité invalide")
            return
        
        # Normalize date
        bc_date = self._normalize_date_for_db(bc_date_str)
        
        try:
            with self.get_db_connection() as conn:
                # Check if BC already exists for this supplier
                existing = conn.execute("""
                    SELECT id FROM bon_commande
                    WHERE fournisseur = ? AND statut = 'actif'
                """, (selected_supplier,)).fetchone()
                
                if existing:
                    # Update existing BC
                    conn.execute("""
                        UPDATE bon_commande
                        SET numero = ?, date_bc = ?, quantite_totale = ?, updated_at = ?
                        WHERE id = ?
                    """, (bc_numero, bc_date, bc_quantite, datetime.now().isoformat(), existing[0]))
                    message = f"BC mis à jour pour {selected_supplier}"
                else:
                    # Create new BC
                    conn.execute("""
                        INSERT INTO bon_commande (fournisseur, numero, date_bc, quantite_totale, statut)
                        VALUES (?, ?, ?, ?, 'actif')
                    """, (selected_supplier, bc_numero, bc_date, bc_quantite))
                    message = f"BC créé pour {selected_supplier}"
                
                conn.commit()
                
            # Update display
            self._update_bc_display()
            self._check_bc_limit()
            
            self.update_status(message)
            messagebox.showinfo("Succès", message)
            
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de l'enregistrement du BC: {e}")
    
    def _update_bc_display(self):
        """Update BC status display for currently selected supplier"""
        selected_supplier = self._get_selected_delivery_supplier()
        
        if not selected_supplier:
            self.bc_status_label.config(text="Aucun fournisseur sélectionné", foreground="gray")
            self.bc_progress_var.set(0)
            self.bc_progress_label.config(text="0%")
            return
        
        try:
            with self.get_db_connection() as conn:
                # Get active BC for supplier
                bc = conn.execute("""
                    SELECT id, numero, date_bc, quantite_totale, quantite_livree
                    FROM bon_commande
                    WHERE fournisseur = ? AND statut = 'actif'
                    ORDER BY date_bc DESC
                    LIMIT 1
                """, (selected_supplier,)).fetchone()
                
                if not bc:
                    self.bc_status_label.config(
                        text=f"Aucun BC actif pour {selected_supplier}",
                        foreground="gray"
                    )
                    self.bc_progress_var.set(0)
                    self.bc_progress_label.config(text="0%")
                    
                    # Clear inputs
                    self.bc_numero_var.set("")
                    self.bc_quantite_var.set("")
                    return
                
                bc_id, numero, date_bc, qte_totale, qte_livree = bc
                
                # Calculate delivered quantity from BLs after BC date
                total_delivered = conn.execute("""
                    SELECT COALESCE(SUM(quantite), 0)
                    FROM bon_livraison
                    WHERE code_fournisseur = ?
                      AND date_livraison >= ?
                """, (selected_supplier, date_bc)).fetchone()[0]
                
                # Update quantite_livree in database
                conn.execute("""
                    UPDATE bon_commande
                    SET quantite_livree = ?, updated_at = ?
                    WHERE id = ?
                """, (total_delivered, datetime.now().isoformat(), bc_id))
                conn.commit()
                
                # Calculate progress
                progress_pct = (total_delivered / qte_totale * 100) if qte_totale > 0 else 0
                remaining = max(0, qte_totale - total_delivered)
                
                # Update status label with color
                if progress_pct >= 100:
                    status_text = f"⚠️ BC ATTEINT! {total_delivered:.1f}T / {qte_totale:.1f}T (Dépassement: {total_delivered - qte_totale:.1f}T)"
                    color = "red"
                elif progress_pct >= 90:
                    status_text = f"⚠️ BC proche limite: {total_delivered:.1f}T / {qte_totale:.1f}T (Reste: {remaining:.1f}T)"
                    color = "orange"
                else:
                    status_text = f"✓ BC {numero or 'N/A'}: {total_delivered:.1f}T / {qte_totale:.1f}T (Reste: {remaining:.1f}T)"
                    color = "green"
                
                self.bc_status_label.config(text=status_text, foreground=color)
                self.bc_progress_var.set(min(100, progress_pct))
                self.bc_progress_label.config(text=f"{progress_pct:.0f}%")
                
                # Populate inputs for editing
                self.bc_numero_var.set(numero or "")
                self.bc_quantite_var.set(str(qte_totale))
                
        except Exception as e:
            print(f"[CIMENT] Error updating BC display: {e}")
            self.bc_status_label.config(text="Erreur chargement BC", foreground="red")
    
    def _check_bc_limit(self):
        """Check if BC limit reached and send notification"""
        selected_supplier = self._get_selected_delivery_supplier()
        
        if not selected_supplier:
            return
        
        try:
            with self.get_db_connection() as conn:
                # Get active BC
                bc = conn.execute("""
                    SELECT id, numero, date_bc, quantite_totale, quantite_livree
                    FROM bon_commande
                    WHERE fournisseur = ? AND statut = 'actif'
                    ORDER BY date_bc DESC
                    LIMIT 1
                """, (selected_supplier,)).fetchone()
                
                if not bc:
                    return
                
                bc_id, numero, date_bc, qte_totale, qte_livree = bc
                
                # Calculate delivered quantity
                total_delivered = conn.execute("""
                    SELECT COALESCE(SUM(quantite), 0)
                    FROM bon_livraison
                    WHERE code_fournisseur = ?
                      AND date_livraison >= ?
                """, (selected_supplier, date_bc)).fetchone()[0]
                
                # Check if limit reached or exceeded
                if total_delivered >= qte_totale:
                    depassement = total_delivered - qte_totale
                    
                    notification_title = f"BC {numero or ''} - Limite Atteinte"
                    notification_message = (
                        f"Fournisseur: {selected_supplier}\n"
                        f"Quantité BC: {qte_totale:.1f}T\n"
                        f"Quantité livrée: {total_delivered:.1f}T\n"
                        f"Dépassement: {depassement:.1f}T"
                    )
                    
                    # Send notification via notification system
                    try:
                        notification_manager.add_notification(
                            title=notification_title,
                            message=notification_message,
                            notification_type="warning",
                            priority="high"
                        )
                    except Exception as notif_error:
                        print(f"[CIMENT] Failed to send BC notification: {notif_error}")
                    
                    # Also show messagebox
                    messagebox.showwarning(
                        "Bon de Commande Atteint",
                        notification_message
                    )
                    
        except Exception as e:
            print(f"[CIMENT] Error checking BC limit: {e}")
    
    def edit_supplier(self):
        """Edit selected supplier"""
        item = self.suppliers_tree.selection()
        if not item:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur à modifier")
            return
        
        supplier_id = self.suppliers_tree.item(item[0], "text")
        supplier = next((s for s in self.suppliers if s['id'] == supplier_id), None)
        
        if supplier:
            dialog = SupplierDialog(self, "Modifier Fournisseur", supplier)
            if dialog.result:
                updated_supplier = dialog.result
                try:
                    with self.get_db_connection() as conn:
                        conn.execute("""
                            UPDATE fournisseurs 
                            SET nom_fournisseur = ?
                            WHERE code_fournisseur = ?
                        """, (
                            updated_supplier['name'],
                            supplier_id
                        ))
                        conn.commit()  # CRITICAL FIX: Commit the update!
                        supplier.update(updated_supplier)
                        self.refresh_suppliers()
                        self.update_status(f"Fournisseur '{supplier['name']}' modifié avec succès")
                        print(f"[CIMENT] Successfully updated supplier {supplier_id}")
                except Exception as e:
                    messagebox.showerror("Erreur", f"Erreur lors de la modification: {e}")
    
    def delete_supplier(self):
        """Delete selected supplier"""
        item = self.suppliers_tree.selection()
        if not item:
            messagebox.showwarning("Attention", "Sélectionnez un fournisseur à supprimer")
            return
        
        if messagebox.askyesno("Confirmer", "Êtes-vous sûr de vouloir supprimer ce fournisseur?"):
            supplier_id = self.suppliers_tree.item(item[0], "text")
            try:
                with self.get_db_connection() as conn:
                    conn.execute("DELETE FROM fournisseurs WHERE code_fournisseur = ?", (supplier_id,))
                    conn.commit()  # CRITICAL FIX: Commit the deletion!
                    self.suppliers = [s for s in self.suppliers if s['id'] != supplier_id]
                    self.refresh_suppliers()
                    self.update_status(f"Fournisseur supprimé - ID: {supplier_id}")
                    print(f"[CIMENT] Successfully deleted supplier {supplier_id}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la suppression: {e}")
    
    def generate_avoir_from_bl(self):
        """Generate avoir from selected delivery notes"""
        selected_items = self.delivery_tree.selection()
        if not selected_items:
            messagebox.showwarning("Attention", "Sélectionnez au moins un bon de livraison pour générer un avoir")
            return
        
        # Get selected delivery notes and calculate total quantity
        selected_deliveries = []
        total_qty = 0.0
        
        for item in selected_items:
            delivery_id = int(self.delivery_tree.item(item, "text"))
            delivery_note = next((d for d in self.delivery_notes if d['id'] == delivery_id), None)
            if delivery_note:
                selected_deliveries.append(delivery_note)
                
                # Calculate quantity
                qty_str = str(delivery_note.get('quantity', '0'))
                try:
                    if ' ' in qty_str:
                        qty = float(qty_str.split()[0])
                    else:
                        qty = float(qty_str)
                    total_qty += qty
                except (ValueError, IndexError):
                    pass
        
        if not selected_deliveries:
            messagebox.showwarning("Attention", "Aucun bon de livraison valide sélectionné")
            return
        
        # Show confirmation with quantity total
        confirm_msg = f"📦 Générer avoir pour {len(selected_deliveries)} BL\n\n"
        confirm_msg += f"📊 Quantité totale: {total_qty:.1f} tonnes\n\n"
        confirm_msg += "Continuer?"
        
        if not messagebox.askyesno("Confirmation", confirm_msg):
            return
        
        # Create avoir dialog with pre-selected delivery notes
        dialog = CimentAvoirDialog(self, selected_deliveries, self.materials, preselected=True)
        if dialog.result:
            avoir_data = dialog.result
            try:
                # Save avoir to achat table with avoir semantics:
                # - mt_ht and ttc stored negative (credit)
                # - timbre stored positive (refund of previously negative stamp in avoir UI)
                # - taxes (e.g., TVA) stored negative
                with self.get_db_connection() as conn:
                    import json
                    # Prepare taxes with negative values
                    try:
                        taxes_list = avoir_data.get('taxes', []) or []
                        adjusted_taxes = []
                        for t in taxes_list:
                            name = t.get('name', '')
                            val_raw = t.get('value', 0)
                            try:
                                val = float(val_raw)
                            except Exception:
                                val = 0.0
                            adjusted_taxes.append({'name': name, 'value': -abs(val)})
                    except Exception:
                        adjusted_taxes = avoir_data.get('taxes', [])
                    # Convert core amounts with correct sign
                    # Include BL numbers in notes for traceability (preserve TYPE tag if present)
                    try:
                        bl_numbers = ", ".join(d.get('number', '') for d in selected_deliveries)
                        # Preserve [TYPE: CODE] tag from dialog if present
                        base_notes = avoir_data['notes']
                        notes_enriched = f"{base_notes} [AVOIR] | BLs: {bl_numbers}"
                    except Exception:
                        notes_enriched = f"{avoir_data['notes']} [AVOIR]"

                    # Normalize date to ISO for DB
                    _date_db = self._normalize_date_for_db(avoir_data.get('date', ''))
                    cursor = conn.execute(
                        """
                        INSERT INTO achats (date, fournisseur, num_facture, mt_ht, ttc, timbre, taxes, notes, paiement_statut, paiement_methode, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            _date_db,
                            avoir_data['fournisseur'],
                            avoir_data['num_facture'],
                            -abs(float(avoir_data['mt_ht'])),  # Negative
                            -abs(float(avoir_data['ttc'])),    # Negative
                            abs(float(avoir_data['timbre'])),  # Positive
                            json.dumps(adjusted_taxes),        # Taxes stored negative
                            notes_enriched,
                            avoir_data['paiement_statut'],
                            avoir_data['paiement_methode'],
                            avoir_data['created_at'],
                        ),
                    )
                    avoir_achat_id = cursor.lastrowid
                    # Link BLs ↔ avoir
                    for delivery in selected_deliveries:
                        try:
                            conn.execute(
                                "INSERT INTO bon_livraison_avoirs (bl_id, achat_id) VALUES (?, ?)",
                                (delivery['id'], avoir_achat_id)
                            )
                        except Exception as link_err:
                            print(f"[CIMENT] Avoir link skipped for BL {delivery['id']}: {link_err}")
                    
                    # Rebuild avoir types map to pick up the new avoir (CRITICAL FIX!)
                    self._build_bl_avoir_types_map(conn)
                    
                    self.refresh_avoirs()
                    # Refresh deliveries to update BL color status (CRITICAL FIX!)
                    self.refresh_deliveries()
                    self.update_status(f"Avoir {avoir_data['num_facture']} créé avec succès")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la création de l'avoir: {e}")
    
    def create_avoir(self):
        """Create new avoir (credit note)"""
        if not self.delivery_notes:
            messagebox.showwarning("Attention", "Aucun bon de livraison disponible pour créer un avoir")
            return
        
        dialog = CimentAvoirDialog(self, self.delivery_notes, self.materials)
        if dialog.result:
            avoir_data = dialog.result
            # Get selected delivery IDs from dialog
            selected_deliveries = []
            if hasattr(dialog, 'delivery_vars'):
                for delivery in self.delivery_notes:
                    if delivery['id'] in dialog.delivery_vars and dialog.delivery_vars[delivery['id']].get():
                        selected_deliveries.append(delivery)
            
            try:
                # Save avoir to achat table with avoir semantics:
                # - mt_ht and ttc stored negative (credit)
                # - timbre stored positive (refund of previously negative stamp in avoir UI)
                # - taxes (e.g., TVA) stored negative
                with self.get_db_connection() as conn:
                    import json
                    # Prepare taxes with negative values
                    try:
                        taxes_list = avoir_data.get('taxes', []) or []
                        adjusted_taxes = []
                        for t in taxes_list:
                            name = t.get('name', '')
                            val_raw = t.get('value', 0)
                            try:
                                val = float(val_raw)
                            except Exception:
                                val = 0.0
                            adjusted_taxes.append({'name': name, 'value': -abs(val)})
                    except Exception:
                        adjusted_taxes = avoir_data.get('taxes', [])
                    
                    # Include BL numbers in notes for traceability (preserve TYPE tag if present)
                    notes_base = avoir_data['notes']
                    try:
                        bl_numbers = ", ".join(d.get('number', '') for d in selected_deliveries)
                        # Preserve [TYPE: CODE] tag from dialog if present
                        notes_enriched = f"{notes_base} [AVOIR] | BLs: {bl_numbers}"
                    except Exception:
                        notes_enriched = f"{notes_base} [AVOIR]"
                    
                    # Convert core amounts with correct sign
                    # Normalize date to ISO for DB
                    _date_db = self._normalize_date_for_db(avoir_data.get('date', ''))
                    cursor = conn.execute("""
                        INSERT INTO achats (date, fournisseur, num_facture, mt_ht, ttc, timbre, taxes, notes, paiement_statut, paiement_methode, created_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        _date_db,
                        avoir_data['fournisseur'],
                        avoir_data['num_facture'],
                        -abs(float(avoir_data['mt_ht'])),  # Negative
                        -abs(float(avoir_data['ttc'])),    # Negative
                        abs(float(avoir_data['timbre'])),  # Positive
                        json.dumps(adjusted_taxes),        # Taxes stored negative
                        notes_enriched,
                        avoir_data['paiement_statut'],
                        avoir_data['paiement_methode'],
                        avoir_data['created_at']
                    ))
                    avoir_achat_id = cursor.lastrowid
                    
                    # Link BLs ↔ avoir (CRITICAL FIX: This was missing!)
                    for delivery in selected_deliveries:
                        try:
                            conn.execute(
                                "INSERT INTO bon_livraison_avoirs (bl_id, achat_id) VALUES (?, ?)",
                                (delivery['id'], avoir_achat_id)
                            )
                        except Exception as link_err:
                            print(f"[CIMENT] Avoir link skipped for BL {delivery['id']}: {link_err}")
                    
                    # Commit happens when WITH block exits
                
                # Refresh UI AFTER commit (outside WITH block to ensure changes are visible)
                self.refresh_avoirs()
                self.refresh_deliveries()  # This will rebuild avoir types map with committed data
                self.update_status(f"Avoir {avoir_data['num_facture']} créé avec succès")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur lors de la création de l'avoir: {e}")
    
    def refresh_avoirs(self):
        """Refresh avoirs list from achat table (negative entries)"""
        if not hasattr(self, 'avoirs_tree'):
            return
            
        # Clear existing items
        for item in self.avoirs_tree.get_children():
            self.avoirs_tree.delete(item)
        
        try:
            with self.get_db_connection() as conn:
                # Get negative achat entries (avoirs)
                cursor = conn.execute("""
                    SELECT id, date, fournisseur, num_facture, mt_ht, ttc, timbre, taxes, paiement_statut, notes
                    FROM achats 
                    WHERE mt_ht < 0 AND notes LIKE '[AVOIR]%'
                    ORDER BY date DESC
                """)
                avoirs = cursor.fetchall()
                
                for avoir in avoirs:
                    achat_id, date, fournisseur, num_facture, mt_ht, ttc, timbre, taxes_str, statut, notes = avoir
                    
                    # Parse taxes to get TVA
                    tva = 0.0
                    try:
                        import json
                        taxes = json.loads(taxes_str) if taxes_str else []
                        for tax in taxes:
                            if 'TVA' in tax.get('name', ''):
                                tva = float(tax.get('value', 0))
                                break
                    except:
                        pass
                    
                    # Display absolute values in tree (but store as negative in DB)
                    # Ensure date displayed as DD/MM/YYYY
                    try:
                        from datetime import datetime as _dt
                        display_date = _dt.strptime(date, "%Y-%m-%d").strftime("%d/%m/%Y") if isinstance(date, str) else str(date)
                    except Exception:
                        display_date = str(date)
                    self.avoirs_tree.insert("", "end", text=str(achat_id), values=(
                        display_date,
                        fournisseur,
                        num_facture,
                        f"{abs(mt_ht):.3f} DA",
                        f"{abs(tva):.3f} DA", 
                        f"{abs(ttc):.3f} DA",
                        statut
                    ))
        except Exception as e:
            print(f"Erreur lors du chargement des avoirs: {e}")
    
    def generate_monthly_report(self):
        """Generate monthly report"""
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Handle different date formats for monthly deliveries
        monthly_deliveries = []
        for d in self.delivery_notes:
            try:
                date_str = d.get('date', '')
                if not date_str:
                    continue
                    
                # Try to parse dd/mm/yy format first
                if '/' in date_str and len(date_str.split('/')) == 3:
                    try:
                        date_obj = datetime.strptime(date_str, "%d/%m/%y")
                    except ValueError:
                        # Try dd/mm/yyyy format
                        try:
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                        except ValueError:
                            continue
                # Try to parse YYYY-MM-DD format as fallback
                elif '-' in date_str and len(date_str) >= 10:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue
                else:
                    continue
                
                # Check if the date is in current month and year
                if date_obj.month == current_month and date_obj.year == current_year:
                    monthly_deliveries.append(d)
                    
            except Exception:
                # Skip dates that can't be parsed
                continue
        
        if not monthly_deliveries:
            messagebox.showinfo("Rapport", "Aucune donnée pour le mois en cours")
            return
        
        total_amount = sum(float(d['amount']) for d in monthly_deliveries)
        
        report = f"Rapport Mensuel - {datetime.now().strftime('%B %Y')}\\n\\n"
        report += f"Nombre de livraisons: {len(monthly_deliveries)}\\n"
        report += f"Montant total: {total_amount:.3f} DA\\n"
        
        messagebox.showinfo("Rapport Mensuel", report)
    
    # Refresh methods
    def refresh_all_data(self):
        """Refresh all data displays"""
        self.refresh_materials()
        self.refresh_deliveries()
        self.refresh_suppliers()
        self.update_statistics()
    
    def refresh_materials(self):
        """Refresh materials list"""
        # Clear existing items
        for item in self.materials_tree.get_children():
            self.materials_tree.delete(item)
        
        # Add materials
        for material in self.materials:
            self.materials_tree.insert("", "end", text=material['id'], values=(
                material['name'], material['quantity'], material['unit'],
                f"{material['price']} DA", material['supplier']
            ))
        
        self.items_count_label.config(text=f"{len(self.materials)} matériaux")
        self.update_statistics()
    
    def refresh_deliveries(self):
        """Refresh delivery notes list - ordered by date (nearest to farthest), filtered by selected supplier."""
        # Rebuild avoir types map and update 200T eligibility to pick up any database changes
        try:
            with self.get_db_connection() as conn:
                # Update 200T eligibility based on monthly tonnage
                self._update_200t_eligibility(conn)
                # Rebuild avoir types map
                self._build_bl_avoir_types_map(conn)
        except Exception as e:
            print(f"[CIMENT] Failed to rebuild avoir map during refresh: {e}")
        
        # Clear existing items
        for item in self.delivery_tree.get_children():
            self.delivery_tree.delete(item)
        
        # Ensure supplier filter values are up to date and a selection is made
        self._populate_delivery_supplier_filter()

        # Apply supplier filter (no 'All' option; if none selected and suppliers exist, default to first)
        selected_supplier = self._get_selected_delivery_supplier()

        # Sort deliveries by date (newest first) to ensure consistent ordering
        filtered = self.delivery_notes
        if selected_supplier:
            filtered = [d for d in self.delivery_notes if (d.get('supplier') or '').strip() == selected_supplier]
        sorted_deliveries = sorted(filtered, key=lambda d: self._parse_date_for_sorting(d.get('date', '')), reverse=True)
        
        # Add deliveries in sorted order with composite status and color
        for delivery in sorted_deliveries:
            bl_id = delivery.get('id')
            # Facture acquired?
            has_facture = bool(getattr(self, '_bl_has_facture', {}).get(bl_id, False)) or (
                (delivery.get('status','').strip().lower() in ['facturé','facture','factured','invoiced'])
            )

            acquired_types = set(getattr(self, '_bl_avoir_types', {}).get(bl_id, set())) if hasattr(self, '_bl_avoir_types') else set()

            # Eligibility flags
            elig_20j = 1 if delivery.get('avoir_payment_before_20_days', 0) == 1 else 0
            elig_200t = 1 if delivery.get('avoir_total_factures_200t_month', 0) == 1 else 0
            elig_tr = 1 if delivery.get('avoir_sur_livraison', 0) == 1 else 0
            elig_annee = 1 if delivery.get('avoir_par_annee', 0) == 1 else 0

            def chk(eligible: int, code: str) -> str:
                if not eligible:
                    return '–'
                return '✓' if code in acquired_types else '✗'

            f_mark = '✓' if has_facture else '✗'
            s20 = chk(elig_20j, '20J')
            s200 = chk(elig_200t, '200T')
            strr = chk(elig_tr, 'TR')
            sann = chk(elig_annee, 'ANNEE')
            display_status = f"F:{f_mark} 20j:{s20} 200t:{s200} TR:{strr} AN:{sann}"

            # Color: green only when factured and all eligible avoir types are acquired
            required = []
            if elig_20j: required.append('20J')
            if elig_200t: required.append('200T')
            if elig_tr: required.append('TR')
            if elig_annee: required.append('ANNEE')
            all_acquired = has_facture and all(code in acquired_types for code in required)
            if all_acquired:
                color_tag = 'green'
            elif has_facture or len(acquired_types) > 0:
                color_tag = 'yellow'
            else:
                color_tag = 'red'

            self.delivery_tree.insert("", "end", text=delivery['id'], values=(
                delivery['date'], delivery['number'], delivery['supplier'],
                delivery['material'], delivery['quantity'], f"{delivery['amount']} DA",
                display_status
            ), tags=(color_tag,))
        
        self.items_count_label.config(text=f"{len(sorted_deliveries)} BL")
        
        # Update BC display and check limit
        self._update_bc_display()
        self._check_bc_limit()

    def _populate_delivery_supplier_filter(self):
        """Populate the BL supplier selector with distinct suppliers present in delivery notes.
        No 'All' option; default-select the first if nothing is selected.
        """
        try:
            # Build distinct supplier list from current delivery notes
            suppliers = []
            seen = set()
            for d in self.delivery_notes:
                name = (d.get('supplier') or '').strip()
                if not name:
                    continue
                if name in seen:
                    continue
                seen.add(name)
                suppliers.append(name)

            suppliers = self._priority_sort_suppliers(suppliers)

            # Preserve previous selection if still present
            prev = (self.delivery_supplier_var.get() or '').strip()

            # Update combobox values
            self.delivery_supplier_combo['values'] = suppliers

            # Choose selection
            to_select = None
            if prev and prev in suppliers:
                to_select = prev
            elif suppliers:
                to_select = suppliers[0]

            if to_select:
                # Avoid triggering multiple refreshes unnecessarily
                if (self.delivery_supplier_var.get() or '').strip() != to_select:
                    self.delivery_supplier_var.set(to_select)
            else:
                self.delivery_supplier_var.set("")
        except Exception as e:
            print(f"[CIMENT_PAGE] Error populating delivery supplier filter: {e}")

    def _get_selected_delivery_supplier(self) -> str:
        """Return the currently selected supplier display name for BL filtering."""
        try:
            sel = (self.delivery_supplier_var.get() or '').strip()
            return sel if sel else ''
        except Exception:
            return ''
    
    def _parse_date_for_sorting(self, date_str):
        """Parse date string for sorting purposes"""
        if not date_str:
            return datetime.min
        
        try:
            # Try to parse dd/mm/yy format first
            if '/' in date_str and len(date_str.split('/')) == 3:
                try:
                    return datetime.strptime(date_str, "%d/%m/%y")
                except ValueError:
                    # Try dd/mm/yyyy format
                    try:
                        return datetime.strptime(date_str, "%d/%m/%Y")
                    except ValueError:
                        pass
            # Try to parse YYYY-MM-DD format as fallback
            elif '-' in date_str and len(date_str) >= 10:
                try:
                    return datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass
        except Exception:
            pass
        
        # Return minimum date if parsing fails
        return datetime.min
    
    def _get_delivery_color_tag(self, delivery):
        """Deprecated: color and status are computed in refresh_deliveries."""
        return 'red'
    
    def _select_all_deliveries(self, event=None):
        """Select all deliveries in the tree (Ctrl+A)"""
        try:
            all_items = self.delivery_tree.get_children()
            self.delivery_tree.selection_set(all_items)
            return "break"  # Prevent default behavior
        except Exception as e:
            print(f"[CIMENT] Error selecting all: {e}")
    
    def _update_selection_summary(self, event=None):
        """Update the selection summary bar with totals"""
        try:
            selection = self.delivery_tree.selection()
            
            if not selection:
                # No selection - reset summary
                self.selection_count_label.config(text="0 BL")
                self.selection_qty_label.config(text="0")
                self.selection_facture_label.config(text="0.000 DA")
                self.selection_avoir_label.config(text="0.000 DA")
                return
            
            # Calculate totals
            total_qty = 0.0
            total_facture = 0.0
            total_avoir_eligible = 0.0
            
            for item in selection:
                try:
                    # Get delivery ID and find the full delivery object
                    delivery_id = int(self.delivery_tree.item(item, "text"))
                    delivery = next((d for d in self.delivery_notes if d['id'] == delivery_id), None)
                    
                    if not delivery:
                        continue
                    
                    # Get quantity (parse from string like "50 tonnes")
                    qty_str = str(delivery.get('quantity', '0'))
                    try:
                        if ' ' in qty_str:
                            qty = float(qty_str.split()[0])
                        else:
                            qty = float(qty_str)
                        total_qty += qty
                    except (ValueError, IndexError):
                        pass
                    
                    # Get facture amount (total BL amount)
                    try:
                        amount_str = str(delivery.get('amount', '0')).replace(' DA', '').replace(',', '.')
                        amount = float(amount_str)
                        total_facture += amount
                    except (ValueError, TypeError):
                        pass
                    
                    # Calculate eligible avoir amount based on enabled avoir types
                    # Use settings to get avoir rates
                    try:
                        from app.stfoom.ui.ciment_avoir_settings import SimpleSettingsManager
                        settings_manager = SimpleSettingsManager()
                        
                        # 20J avoir
                        if delivery.get('avoir_payment_before_20_days', 0) == 1:
                            rate_20j = float(settings_manager.get_setting('carthage_cement_avoir_payment_before_20_days', '0.0'))
                            total_avoir_eligible += qty * rate_20j
                        
                        # 200T avoir
                        if delivery.get('avoir_total_factures_200t_month', 0) == 1:
                            rate_200t = float(settings_manager.get_setting('carthage_cement_avoir_total_factures_200t_month', '0.0'))
                            total_avoir_eligible += qty * rate_200t
                        
                        # TR avoir
                        if delivery.get('avoir_sur_livraison', 0) == 1:
                            rate_tr = float(settings_manager.get_setting('carthage_cement_avoir_sur_livraison', '0.0'))
                            total_avoir_eligible += qty * rate_tr
                        
                        # ANNEE avoir
                        if delivery.get('avoir_par_annee', 0) == 1:
                            rate_annee = float(settings_manager.get_setting('carthage_cement_avoir_par_annee', '0.0'))
                            total_avoir_eligible += rate_annee  # Fixed amount per BL
                    except Exception as e:
                        print(f"[CIMENT] Error calculating avoir for BL {delivery_id}: {e}")
                
                except (ValueError, TypeError) as e:
                    print(f"[CIMENT] Error processing selection item: {e}")
                    continue
            
            # Update summary labels
            self.selection_count_label.config(text=f"{len(selection)} BL")
            self.selection_qty_label.config(text=f"{total_qty:.1f}")
            self.selection_facture_label.config(text=f"{total_facture:.3f} DA")
            self.selection_avoir_label.config(text=f"{total_avoir_eligible:.3f} DA")
            
        except Exception as e:
            print(f"[CIMENT] Error updating selection summary: {e}")
            import traceback
            traceback.print_exc()

    def _update_200t_eligibility(self, conn):
        """
        Auto-calculate 200T eligibility based on monthly tonnage totals.
        A BL is eligible for 200T avoir if the total quantity of BLs from 
        the same supplier in the same month is >= 200 tonnes.
        """
        from collections import defaultdict
        
        try:
            # Get all BLs
            cur = conn.execute("""
                SELECT 
                    id,
                    numero,
                    date_livraison,
                    code_fournisseur,
                    quantite,
                    avoir_total_factures_200t_month
                FROM bon_livraison
                ORDER BY date_livraison
            """)
            
            bls = cur.fetchall()
            
            # Group by supplier + month
            monthly_groups = defaultdict(list)
            
            for bl in bls:
                try:
                    # Parse date to get year-month
                    date_str = bl[2]  # date_livraison
                    if not date_str:
                        continue
                    
                    # Try different date formats
                    from datetime import datetime as dt
                    date_obj = None
                    for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y']:
                        try:
                            date_obj = dt.strptime(date_str, fmt)
                            break
                        except:
                            continue
                    
                    if not date_obj:
                        continue
                    
                    year_month = date_obj.strftime('%Y-%m')
                    supplier = (bl[3] or '').strip()  # code_fournisseur
                    
                    if not supplier:
                        continue
                    
                    key = (supplier, year_month)
                    monthly_groups[key].append(bl)
                    
                except Exception:
                    continue
            
            # Calculate eligibility and update
            update_count = 0
            
            for (supplier, year_month), group_bls in monthly_groups.items():
                # Calculate total quantity for this supplier-month
                total_qty = sum(bl[4] or 0 for bl in group_bls)  # quantite
                
                # Determine eligibility: >= 200 tonnes
                eligible_flag = 1 if total_qty >= 200 else 0
                
                # Update all BLs in this group if needed
                for bl in group_bls:
                    current_flag = bl[5]  # avoir_total_factures_200t_month
                    
                    if current_flag != eligible_flag:
                        conn.execute("""
                            UPDATE bon_livraison
                            SET avoir_total_factures_200t_month = ?
                            WHERE id = ?
                        """, (eligible_flag, bl[0]))  # id
                        update_count += 1
            
            if update_count > 0:
                conn.commit()
                print(f"[CIMENT] Updated 200T eligibility for {update_count} BLs")
                
        except Exception as e:
            print(f"[CIMENT] Failed to update 200T eligibility: {e}")

    def _build_bl_avoir_types_map(self, conn):
        """Build BL -> set of acquired avoir codes from achats.notes [TYPE: CODE]."""
        import re
        self._bl_avoir_types = {}
        try:
            cur = conn.execute(
                """
                SELECT bla.bl_id, a.notes
                FROM bon_livraison_avoirs bla
                JOIN achats a ON a.id = bla.achat_id
                WHERE a.notes IS NOT NULL
                """
            )
            for bl_id, notes in cur.fetchall():
                if not notes:
                    continue
                m = re.search(r"\[TYPE:\s*([A-Za-z0-9]+)\]", notes, re.IGNORECASE)
                if not m:
                    continue
                code = m.group(1).upper().strip()
                if code:
                    self._bl_avoir_types.setdefault(int(bl_id), set()).add(code)
        except Exception as e:
            print(f"[CIMENT_PAGE] Failed to build avoir type map: {e}")

    def _sync_bl_links_from_achats(self, conn):
        """Best-effort backfill of BL↔Facture/Avoir links by parsing achats notes.
        - Factures: parse notes generated by CimentFactureDialog which list BL numbers.
        - Avoirs: parse enriched notes that include 'BLs:' tokens (available after this fix).
        """
        import re
        from datetime import datetime as _dt

        created_facture_links = 0
        created_avoir_links = 0

        # Map BL numero to id for quick lookup
        bl_map = {}
        try:
            cur = conn.execute("SELECT id, numero FROM bon_livraison")
            for bl_id, numero in cur.fetchall():
                if numero:
                    bl_map[str(numero).strip()] = int(bl_id)
        except Exception:
            pass

        # Helper: parse date string in multiple legacy formats -> 'YYYY-MM'
        def _extract_year_month(ds: str):
            if not ds:
                return None
            ds = str(ds).strip()
            # Try ISO first
            for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d/%m/%y"):
                try:
                    return _dt.strptime(ds[:10], fmt).strftime("%Y-%m")
                except Exception:
                    continue
            # Fallback: if ds already looks like YYYY-MM
            if re.match(r"^\d{4}-\d{2}$", ds):
                return ds
            return None

        # Parse factures
        try:
            cur = conn.execute("SELECT id, notes FROM achats WHERE notes LIKE '%Facture ciment générée%' OR notes LIKE '%BL %' OR notes LIKE '%- %:%'")
            for achat_id, notes in cur.fetchall():
                if not notes:
                    continue
                # Try to find BL numbers in multiple formats
                found_numbers = set()
                # Format 1: 'BL 001' or 'BL001'
                for match in re.findall(r"\bBL\s*([A-Za-z0-9_-]+)", notes):
                    found_numbers.add(match.strip())
                # Format 2: list lines like '- BL001:' capture token before colon
                for match in re.findall(r"-\s*([A-Za-z0-9_-]+)\s*:", notes):
                    found_numbers.add(match.strip())
                for numero in found_numbers:
                    bl_id = bl_map.get(numero)
                    if bl_id:
                        try:
                            exists = conn.execute(
                                "SELECT 1 FROM bon_livraison_factures WHERE bl_id=? AND achat_id=?",
                                (bl_id, achat_id)
                            ).fetchone()
                            if not exists:
                                conn.execute(
                                    "INSERT INTO bon_livraison_factures (bl_id, achat_id) VALUES (?, ?)",
                                    (bl_id, achat_id)
                                )
                                created_facture_links += 1
                        except Exception:
                            pass
        except Exception:
            pass

        # Parse avoirs with enriched notes containing 'BLs:'
        try:
            cur = conn.execute("SELECT id, notes FROM achats WHERE notes LIKE '[AVOIR]%' AND notes LIKE '%BLs:%'")
            for achat_id, notes in cur.fetchall():
                if not notes:
                    continue
                # Extract list after 'BLs:'
                try:
                    bls_part = notes.split('BLs:')[1]
                    # split by comma
                    for token in bls_part.split(','):
                        numero = token.strip().strip('|').strip()
                        if not numero:
                            continue
                        bl_id = bl_map.get(numero)
                        if bl_id:
                            exists = conn.execute(
                                "SELECT 1 FROM bon_livraison_avoirs WHERE bl_id=? AND achat_id=?",
                                (bl_id, achat_id)
                            ).fetchone()
                            if not exists:
                                conn.execute(
                                    "INSERT INTO bon_livraison_avoirs (bl_id, achat_id) VALUES (?, ?)",
                                    (bl_id, achat_id)
                                )
                                created_avoir_links += 1
                except Exception:
                    continue
        except Exception:
            pass

        # Additional legacy pattern parsing for older avoir notes WITHOUT 'BLs:' marker
        try:
            cur = conn.execute("SELECT id, notes FROM achats WHERE notes LIKE '[AVOIR]%' AND (notes NOT LIKE '%BLs:%' OR notes IS NULL)")
            for achat_id, notes in cur.fetchall():
                if not notes:
                    continue
                # Find patterns like 'BL123', 'BL 123', 'BL-123'
                found_numbers = set()
                for match in re.findall(r"\bBL[-\s]*([A-Za-z0-9_-]+)", notes):
                    found_numbers.add(match.strip())
                if not found_numbers:
                    continue
                for numero in found_numbers:
                    bl_id = bl_map.get(numero)
                    if not bl_id:
                        continue
                    try:
                        exists = conn.execute(
                            "SELECT 1 FROM bon_livraison_avoirs WHERE bl_id=? AND achat_id=?",
                            (bl_id, achat_id)
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                "INSERT INTO bon_livraison_avoirs (bl_id, achat_id) VALUES (?, ?)",
                                (bl_id, achat_id)
                            )
                            created_avoir_links += 1
                    except Exception:
                        continue
        except Exception:
            pass
        
        # Heuristic backfill: link avoir achats to BLs by supplier and month when links are missing
        try:
            # Find avoir achats without any BL link
            rows = conn.execute(
                """
                SELECT a.id, a.date, a.fournisseur, a.notes
                FROM achats a
                LEFT JOIN bon_livraison_avoirs bla ON bla.achat_id = a.id
                WHERE a.notes LIKE '[AVOIR]%' AND bla.id IS NULL
                """
            ).fetchall()

            for achat_id, a_date, a_fournisseur, a_notes in rows:
                # Normalize supplier name: strip [CIMENT] prefix
                supplier_name = (a_fournisseur or '')
                supplier_name = re.sub(r"^\[CIMENT\]\s*", "", supplier_name).strip()

                # Extract avoir type code if present
                type_code = None
                m = re.search(r"\[TYPE:\s*([A-Za-z0-9]+)\]", a_notes or "", re.IGNORECASE)
                if m:
                    type_code = m.group(1).upper().strip()

                # Compute YYYY-MM for matching with robust parsing
                yyyy_mm = _extract_year_month(a_date) if isinstance(a_date, str) else None
                if not (supplier_name and yyyy_mm):
                    continue

                # Build WHERE filters
                where = [
                    "LOWER(COALESCE(f.nom_fournisseur,'')) = LOWER(?)",
                    "strftime('%Y-%m', bl.date_livraison) = ?",
                ]
                params = [supplier_name, yyyy_mm]

                # Filter by avoir type eligibility if we know the type
                type_to_field = {
                    '20J': 'avoir_payment_before_20_days',
                    '200T': 'avoir_total_factures_200t_month',
                    'TR': 'avoir_sur_livraison',
                    'ANNEE': 'avoir_par_annee',
                }
                if type_code in type_to_field:
                    where.append(f"COALESCE(bl.{type_to_field[type_code]},0) = 1")

                sql = (
                    "SELECT bl.id FROM bon_livraison bl "
                    "LEFT JOIN fournisseurs f ON f.code_fournisseur = bl.code_fournisseur "
                    f"WHERE {' AND '.join(where)}"
                )
                try:
                    bl_ids = [row[0] for row in conn.execute(sql, params).fetchall()]
                except Exception:
                    bl_ids = []

                # Insert links
                for bl_id in bl_ids:
                    try:
                        exists = conn.execute(
                            "SELECT 1 FROM bon_livraison_avoirs WHERE bl_id=? AND achat_id=?",
                            (bl_id, achat_id)
                        ).fetchone()
                        if not exists:
                            conn.execute(
                                "INSERT INTO bon_livraison_avoirs (bl_id, achat_id) VALUES (?, ?)",
                                (bl_id, achat_id)
                            )
                            created_avoir_links += 1
                    except Exception:
                        continue
        except Exception as e:
            print(f"[CIMENT_PAGE] Heuristic avoir link backfill skipped: {e}")
        conn.commit()
        if created_facture_links or created_avoir_links:
            print(f"[CIMENT_PAGE] Link sync created {created_facture_links} facture links and {created_avoir_links} avoir links.")
    
    def refresh_suppliers(self):
        """Refresh suppliers list"""
        # Clear existing items
        for item in self.suppliers_tree.get_children():
            self.suppliers_tree.delete(item)
        
        # Add suppliers
        for supplier in self.suppliers:
            self.suppliers_tree.insert("", "end", text=supplier['id'], values=(
                supplier['name'], supplier['contact'], supplier['phone'],
                supplier['materials'], supplier['last_delivery']
            ))
        
        self.items_count_label.config(text=f"{len(self.suppliers)} fournisseurs")
        self.update_statistics()
    
    def update_statistics(self):
        """Update statistics display"""
        current_month = datetime.now().month
        current_year = datetime.now().year
        
        # Handle different date formats for monthly deliveries counting
        monthly_deliveries = 0
        for d in self.delivery_notes:
            try:
                date_str = d.get('date', '')
                if not date_str:
                    continue
                    
                # Try to parse dd/mm/yy format first
                if '/' in date_str and len(date_str.split('/')) == 3:
                    try:
                        date_obj = datetime.strptime(date_str, "%d/%m/%y")
                    except ValueError:
                        # Try dd/mm/yyyy format
                        try:
                            date_obj = datetime.strptime(date_str, "%d/%m/%Y")
                        except ValueError:
                            continue
                # Try to parse YYYY-MM-DD format as fallback
                elif '-' in date_str and len(date_str) >= 10:
                    try:
                        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                    except ValueError:
                        continue
                else:
                    continue
                
                # Check if the date is in current month and year
                if date_obj.month == current_month and date_obj.year == current_year:
                    monthly_deliveries += 1
                    
            except Exception:
                # Skip dates that can't be parsed
                continue
        
        self.stats_materials.config(text=f"Matériaux: {len(self.materials)}")
        self.stats_suppliers.config(text=f"Fournisseurs: {len(self.suppliers)}")
        self.stats_deliveries.config(text=f"BL ce mois: {monthly_deliveries}")
    
    def update_status(self, message: str):
        """Update status bar message"""
        self.status_label.config(text=message)
        # Reset to default after 3 seconds
        self.after(3000, lambda: self.status_label.config(text="Prêt"))


# Dialog classes
class MaterialDialog:
    """Dialog for adding/editing materials"""
    
    def __init__(self, parent, title, material=None):
        self.result = None
        self.parent = parent  # Store parent reference to access suppliers
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(material)
        self.dialog.wait_window()
    
    def setup_ui(self, material):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name
        ttk.Label(main_frame, text="Nom:").pack(anchor="w")
        self.name_var = tk.StringVar(value=material['name'] if material else "")
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Quantity
        ttk.Label(main_frame, text="Quantité:").pack(anchor="w")
        self.quantity_var = tk.StringVar(value=material['quantity'] if material else "0")
        ttk.Entry(main_frame, textvariable=self.quantity_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Unit
        ttk.Label(main_frame, text="Unité:").pack(anchor="w")
        self.unit_var = tk.StringVar(value=material['unit'] if material else "tonnes")
        unit_combo = ttk.Combobox(main_frame, textvariable=self.unit_var, values=["tonnes", "sacs", "m³", "unités"])
        unit_combo.pack(fill="x", pady=(0, 10))
        
        # Price
        ttk.Label(main_frame, text="Prix (DA):").pack(anchor="w")
        self.price_var = tk.StringVar(value=material['price'] if material else "0")
        ttk.Entry(main_frame, textvariable=self.price_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Supplier - CHANGED: Use dropdown from fournisseur tab
        ttk.Label(main_frame, text="Fournisseur:").pack(anchor="w")
        self.supplier_var = tk.StringVar(value=material['supplier'] if material else "")
        
        # Get suppliers list from parent
        supplier_names = []
        if hasattr(self.parent, 'suppliers') and self.parent.suppliers:
            supplier_names = [s['name'] for s in self.parent.suppliers]
        
        supplier_combo = ttk.Combobox(main_frame, textvariable=self.supplier_var, values=supplier_names, width=37)
        supplier_combo.pack(fill="x", pady=(0, 10))
        
        # Make combobox editable so user can also type new supplier names
        supplier_combo.bind('<KeyRelease>', self._on_supplier_keyrelease)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side="right")
    
    def _on_supplier_keyrelease(self, event):
        """Handle supplier combobox key release for filtering"""
        typed_text = self.supplier_var.get().lower()
        if not typed_text:
            return
        
        # Filter supplier names based on typed text
        if hasattr(self.parent, 'suppliers') and self.parent.suppliers:
            filtered_suppliers = [s['name'] for s in self.parent.suppliers 
                                if typed_text in s['name'].lower()]
            
            # Update combobox values
            event.widget.configure(values=filtered_suppliers)
    
    def ok(self):
        """OK button clicked"""
        try:
            self.result = {
                'name': self.name_var.get().strip(),
                'quantity': float(self.quantity_var.get()),
                'unit': self.unit_var.get(),
                'price': float(self.price_var.get()),
                'supplier': self.supplier_var.get().strip()
            }
            
            if not self.result['name']:
                messagebox.showerror("Erreur", "Le nom est requis")
                return
            
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides")
    
    def cancel(self):
        """Cancel button clicked"""
        self.result = None
        self.dialog.destroy()


class DeliveryDialog:
    """Dialog for creating delivery notes"""
    
    def __init__(self, parent, title, materials, suppliers, delivery_note=None):
        self.result = None
        self.materials = materials
        self.suppliers = suppliers
        self.parent = parent  # Store parent reference
        self.delivery_note = delivery_note  # Existing delivery data for editing
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x600")  # Increased height for avoir checkboxes and buttons
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui()
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # No auto-generate BL number - leave empty
        
        # Number
        ttk.Label(main_frame, text="Numéro BL:").pack(anchor="w")
        self.number_var = tk.StringVar(value=self.delivery_note.get('number', '') if self.delivery_note else "")
        number_entry = ttk.Entry(main_frame, textvariable=self.number_var, width=40)
        number_entry.pack(fill="x", pady=(0, 10))
        number_entry.bind('<KeyRelease>', self.check_fields_completion)
        
        # Date with calendar picker
        ttk.Label(main_frame, text="Date:").pack(anchor="w")
        date_frame = ttk.Frame(main_frame)
        date_frame.pack(fill="x", pady=(0, 10))
        
        # Calendar widget with dd/mm/yy format
        initial_date = datetime.now()
        if self.delivery_note and 'date' in self.delivery_note:
            try:
                # Parse existing date - handle different formats
                date_str = self.delivery_note['date']
                print(f"[CIMENT] Parsing date: '{date_str}'")
                
                # Try multiple date formats
                date_formats = ['%d/%m/%Y', '%d/%m/%y', '%Y-%m-%d', '%m/%d/%Y', '%m/%d/%y']
                parsed = False
                
                for fmt in date_formats:
                    try:
                        initial_date = datetime.strptime(date_str, fmt)
                        print(f"[CIMENT] Successfully parsed date with format {fmt}: {initial_date}")
                        parsed = True
                        break
                    except ValueError:
                        continue
                
                if not parsed:
                    print(f"[CIMENT] Could not parse date '{date_str}', using current date")
                    initial_date = datetime.now()
                    
            except Exception as e:
                print(f"[CIMENT] Date parsing error: {e}")
                initial_date = datetime.now()
        
        self.date_entry = DateEntry(
            date_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='dd/mm/yy',
            year=initial_date.year,
            month=initial_date.month,
            day=initial_date.day
        )
        self.date_entry.pack(side="left")
        self.date_entry.bind('<<DateEntrySelected>>', self.check_fields_completion)
        
        # Material - MOVED UP: Material selection comes before supplier selection
        ttk.Label(main_frame, text="Matériau:").pack(anchor="w")
        self.material_var = tk.StringVar()
        material_combo = ttk.Combobox(main_frame, textvariable=self.material_var,
                                    values=[m['name'] for m in self.materials])
        material_combo.pack(fill="x", pady=(0, 10))
        material_combo.bind('<<ComboboxSelected>>', self.on_material_selected)  # NEW: Autofill supplier
        material_combo.bind('<KeyRelease>', self.check_fields_completion)
        
        # Pre-populate material if editing
        if self.delivery_note and 'material' in self.delivery_note:
            self.material_var.set(self.delivery_note.get('material', ''))
        
        # Supplier - MOVED DOWN: Supplier comes after material and gets autofilled
        ttk.Label(main_frame, text="Fournisseur:").pack(anchor="w")
        self.supplier_var = tk.StringVar()
        # Prepare supplier list with priority (Carthage first)
        _supplier_names = [s['name'] for s in self.suppliers]
        if hasattr(self.parent, '_priority_sort_suppliers'):
            _supplier_names = self.parent._priority_sort_suppliers(_supplier_names)
        self.supplier_combo = ttk.Combobox(main_frame, textvariable=self.supplier_var,
                                    values=_supplier_names)
        self.supplier_combo.pack(fill="x", pady=(0, 10))
        self.supplier_combo.bind('<<ComboboxSelected>>', self.check_fields_completion)
        self.supplier_combo.bind('<KeyRelease>', self.check_fields_completion)
        
        # Pre-populate supplier if editing
        if self.delivery_note and 'supplier' in self.delivery_note:
            # The supplier field in loaded data is already the supplier name
            self.supplier_var.set(self.delivery_note['supplier'])
        
        # Quantity
        ttk.Label(main_frame, text="Quantité:").pack(anchor="w")
        # Strip unit from quantity if present, e.g., "50 sacs" or "10 tonnes"
        if self.delivery_note:
            qraw = str(self.delivery_note.get('quantity', '')).strip()
            try:
                qnum = qraw.split()[0]
            except Exception:
                qnum = qraw
            quantity_value = qnum
        else:
            quantity_value = ""
        self.quantity_var = tk.StringVar(value=quantity_value)
        quantity_entry = ttk.Entry(main_frame, textvariable=self.quantity_var, width=40)
        quantity_entry.pack(fill="x", pady=(0, 10))
        quantity_entry.bind('<KeyRelease>', self.check_fields_completion)
        
        # Amount
        ttk.Label(main_frame, text="Montant (DA):").pack(anchor="w")
        amount_value = self.delivery_note.get('amount', '').replace(' DA', '') if self.delivery_note else ""
        self.amount_var = tk.StringVar(value=amount_value)
        amount_entry = ttk.Entry(main_frame, textvariable=self.amount_var, width=40)
        amount_entry.pack(fill="x", pady=(0, 10))
        amount_entry.bind('<KeyRelease>', self.check_fields_completion)
        
        # Avoir Eligibility Section
        avoir_frame = ttk.LabelFrame(main_frame, text="Éligibilité aux Avoirs", padding=10)
        avoir_frame.pack(fill="x", pady=(10, 10))
        
        # Create avoir checkboxes with default values
        self.avoir_vars = {}
        avoir_types = [
            ("avoir_payment_before_20_days", "Paiement avant 20 jours", True),
            ("avoir_total_factures_200t_month", "Total factures 200 tonnes/mois", True),
            ("avoir_sur_livraison", "Sur livraison", False),
            ("avoir_par_annee", "Par année", False)
        ]
        
        for field_name, label_text, default_checked in avoir_types:
            var = tk.BooleanVar()
            
            # Set value based on editing existing delivery or defaults
            if self.delivery_note and field_name in self.delivery_note:
                var.set(bool(self.delivery_note[field_name]))
            else:
                var.set(default_checked)  # Default: first 2 checked
                
            self.avoir_vars[field_name] = var
            
            check = ttk.Checkbutton(avoir_frame, text=label_text, variable=var)
            check.pack(anchor="w", pady=2)
        
        # Buttons
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(self.button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        
        # Create button initially hidden
        self.create_btn = ttk.Button(self.button_frame, text="Créer", command=self.ok)
        # Do not pack initially - button is hidden
    
    def on_material_selected(self, event=None):
        """Handle material selection - autofill supplier and price from materials inventory"""
        try:
            selected_material = self.material_var.get()
            if not selected_material:
                return
            
            # Find the material in the materials list
            for material in self.materials:
                if material.get('name', '') == selected_material:
                    # Found the material, autofill its supplier and price
                    material_supplier = material.get('supplier', '')
                    material_price = material.get('price', 0)
                    material_quantity = material.get('quantity', 0)
                    
                    # Autofill supplier
                    if material_supplier:
                        self.supplier_var.set(material_supplier)
                    
                    # Autofill price if amount field is empty
                    current_amount = self.amount_var.get().strip()
                    if not current_amount and material_price > 0:
                        # Calculate amount based on quantity if quantity is filled
                        current_quantity = self.quantity_var.get().strip()
                        if current_quantity:
                            try:
                                qty = float(current_quantity)
                                suggested_amount = qty * material_price
                                self.amount_var.set(f"{suggested_amount:.3f}")
                            except ValueError:
                                # Just set the unit price
                                self.amount_var.set(f"{material_price:.3f}")
                    
                    # Show inventory info as status message if possible
                    if hasattr(self.parent, 'update_status'):
                        self.parent.update_status(f"Matériau sélectionné: {selected_material} - Stock: {material_quantity} {material.get('unit', 'tonnes')} - Prix: {material_price:.3f} DA/tonne")
                    
                    # Trigger field completion check
                    self.check_fields_completion()
                    break
        except Exception as e:
            print(f"[DELIVERY_DIALOG] Error autofilling material data: {e}")
    
    def check_fields_completion(self, event=None):
        """Check if all required fields are filled and show/hide Create button"""
        try:
            # Check if all required fields have values
            number = self.number_var.get().strip()
            supplier = self.supplier_var.get().strip()
            material = self.material_var.get().strip()
            quantity = self.quantity_var.get().strip()
            amount = self.amount_var.get().strip()
            
            # Check if all fields are filled and quantity/amount are valid numbers
            all_filled = (number and supplier and material and 
                         quantity and amount and
                         quantity != "0" and amount != "0")
            
            if all_filled:
                try:
                    float(quantity)
                    float(amount)
                    # All validations passed - show the Create button
                    self.create_btn.pack(side="right")
                except ValueError:
                    # Invalid numbers - hide button
                    self.create_btn.pack_forget()
            else:
                # Not all fields filled - hide button
                self.create_btn.pack_forget()
                
        except Exception:
            # Any error - hide button
            self.create_btn.pack_forget()
    
    def ok(self):
        """OK button clicked"""
        try:
            # Get date from calendar widget in dd/mm/yy format
            date_selected = self.date_entry.get()
            
            self.result = {
                'number': self.number_var.get().strip(),
                'date': date_selected,
                'supplier': self.supplier_var.get(),
                'material': self.material_var.get(),
                'quantity': self.quantity_var.get(),
                'amount': self.amount_var.get()
            }
            
            # Add avoir eligibility data
            for field_name, var in self.avoir_vars.items():
                self.result[field_name] = 1 if var.get() else 0
            
            if not all([self.result['number'], self.result['supplier'], 
                       self.result['material']]):
                messagebox.showerror("Erreur", "Tous les champs sont requis")
                return
            
            # Validate quantity and amount
            float(self.result['quantity'])
            float(self.result['amount'])
            
            self.dialog.destroy()
        except ValueError:
            messagebox.showerror("Erreur", "Valeurs numériques invalides")
    
    def cancel(self):
        """Cancel button clicked"""
        self.result = None
        self.dialog.destroy()


class SupplierDialog:
    """Dialog for adding suppliers"""
    
    def __init__(self, parent, title, supplier=None):
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("400x400")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui(supplier)
        self.dialog.wait_window()
    
    def setup_ui(self, supplier):
        """Setup dialog UI"""
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Name
        ttk.Label(main_frame, text="Nom:").pack(anchor="w")
        self.name_var = tk.StringVar(value=supplier['name'] if supplier else "")
        ttk.Entry(main_frame, textvariable=self.name_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Contact
        ttk.Label(main_frame, text="Contact:").pack(anchor="w")
        self.contact_var = tk.StringVar(value=supplier['contact'] if supplier else "")
        ttk.Entry(main_frame, textvariable=self.contact_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Phone
        ttk.Label(main_frame, text="Téléphone:").pack(anchor="w")
        self.phone_var = tk.StringVar(value=supplier['phone'] if supplier else "")
        ttk.Entry(main_frame, textvariable=self.phone_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Materials
        ttk.Label(main_frame, text="Matériaux fournis:").pack(anchor="w")
        self.materials_var = tk.StringVar(value=supplier['materials'] if supplier else "")
        ttk.Entry(main_frame, textvariable=self.materials_var, width=40).pack(fill="x", pady=(0, 10))
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x", pady=(20, 0))
        
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="OK", command=self.ok).pack(side="right")
    
    def ok(self):
        """OK button clicked"""
        self.result = {
            'name': self.name_var.get().strip(),
            'contact': self.contact_var.get().strip(),
            'phone': self.phone_var.get().strip(),
            'materials': self.materials_var.get().strip()
        }
        
        if not self.result['name']:
            messagebox.showerror("Erreur", "Le nom est requis")
            return
        
        self.dialog.destroy()
    
    def cancel(self):
        """Cancel button clicked"""
        self.result = None
        self.dialog.destroy()


class CimentFactureDialog:
    """Dialog for creating auto-filled achat facture from cement delivery notes"""
    
    def __init__(self, parent, selected_deliveries, materials=None):
        self.parent = parent
        self.selected_deliveries = selected_deliveries
        self.materials = materials or []
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Générer Facture - Auto-remplie")
        self.dialog.geometry("650x650")  # Slightly wider and shorter
        self.dialog.resizable(True, True)  # Allow resizing
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui()
        self.calculate_totals()
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Setup dialog UI similar to achat page add dialog but auto-filled"""
        # Create main scrollable canvas
        main_canvas = tk.Canvas(self.dialog, highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=main_canvas.yview)
        scrollable_frame = ttk.Frame(main_canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: main_canvas.configure(scrollregion=main_canvas.bbox("all"))
        )
        
        main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        main_canvas.configure(yscrollcommand=scrollbar.set)
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            main_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        main_canvas.bind("<MouseWheel>", on_mousewheel)
        
        # Pack canvas and scrollbar
        scrollbar.pack(side="right", fill="y")
        main_canvas.pack(side="left", fill="both", expand=True)
        
        # Make canvas responsive
        def configure_canvas_width(event):
            canvas_width = event.width
            main_canvas.itemconfig(main_canvas.create_window((0, 0), window=scrollable_frame, anchor="nw"), width=canvas_width)
        main_canvas.bind("<Configure>", configure_canvas_width)
        
        # Main content frame (now inside scrollable area)
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_label = ttk.Label(main_frame, text="Générer Facture Ciment", font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Info section - Show selected BLs
        info_frame = ttk.LabelFrame(main_frame, text="Bons de Livraison sélectionnés", padding=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_text = tk.Text(info_frame, height=4, width=60, state="disabled")
        info_text.pack(fill="x")
        
        # Populate BL info
        info_content = ""
        for i, delivery in enumerate(self.selected_deliveries, 1):
            info_content += f"{i}. BL {delivery['number']} - {delivery['material']} - {delivery['quantity']} - {delivery['amount']} DA\n"
        
        info_text.config(state="normal")
        info_text.insert("1.0", info_content)
        info_text.config(state="disabled")
        
        # Facture form - similar to achat dialog but auto-filled
        form_frame = ttk.LabelFrame(main_frame, text="Détails de la Facture", padding=15)
        form_frame.pack(fill="both", expand=True, pady=(0, 15))
        
        # Fournisseur (auto-filled from first delivery)
        ttk.Label(form_frame, text="Fournisseur:").pack(anchor="w")
        self.fournisseur_var = tk.StringVar()
        if self.selected_deliveries:
            # Get supplier from first delivery
            first_supplier = self.selected_deliveries[0].get("supplier", "")
            self.fournisseur_var.set(f"[CIMENT] {first_supplier}")
        fournisseur_entry = ttk.Entry(form_frame, textvariable=self.fournisseur_var, width=50)
        fournisseur_entry.pack(fill="x", pady=(0, 10))
        fournisseur_entry.bind('<KeyRelease>', self.check_facture_fields_completion)
        
        # Numéro Facture (no auto-generation)
        ttk.Label(form_frame, text="Numéro Facture:").pack(anchor="w")
        self.num_facture_var = tk.StringVar()
        self.num_facture_var.set("")  # No auto-fill
        num_facture_entry = ttk.Entry(form_frame, textvariable=self.num_facture_var, width=30)
        num_facture_entry.pack(anchor="w", pady=(0, 10))
        num_facture_entry.bind('<KeyRelease>', self.check_facture_fields_completion)
        
        # Date with calendar picker
        ttk.Label(form_frame, text="Date:").pack(anchor="w")
        date_frame = ttk.Frame(form_frame)
        date_frame.pack(anchor="w", pady=(0, 10))
        
        # Calendar widget with dd/mm/yy format
        self.date_entry = DateEntry(
            date_frame, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='dd/mm/yy',
            year=datetime.now().year
        )
        self.date_entry.pack(side="left")
        self.date_entry.bind('<<DateEntrySelected>>', self.check_facture_fields_completion)
        
        # Calculations section
        calc_frame = ttk.LabelFrame(form_frame, text="Calculs Automatiques", padding=10)
        calc_frame.pack(fill="x", pady=(0, 10))
        
        # Montant HT (auto-calculated)
        ht_frame = ttk.Frame(calc_frame)
        ht_frame.pack(fill="x", pady=2)
        ttk.Label(ht_frame, text="Montant HT:").pack(side="left")
        self.mt_ht_var = tk.StringVar()
        ttk.Entry(ht_frame, textvariable=self.mt_ht_var, width=15).pack(side="right")
        
        # TVA 19% (auto-calculated)
        tva_frame = ttk.Frame(calc_frame)
        tva_frame.pack(fill="x", pady=2)
        ttk.Label(tva_frame, text="TVA 19%:").pack(side="left")
        self.tva_var = tk.StringVar()
        ttk.Entry(tva_frame, textvariable=self.tva_var, width=15).pack(side="right")
        
        # Fond de soutien (1 DT / quantity)
        fond_frame = ttk.Frame(calc_frame)
        fond_frame.pack(fill="x", pady=2)
        ttk.Label(fond_frame, text="Fond de Soutien (1DT/qty):").pack(side="left")
        self.fond_soutien_var = tk.StringVar()
        ttk.Entry(fond_frame, textvariable=self.fond_soutien_var, width=15).pack(side="right")
        
        # Droit de Timbre (1 DT)
        timbre_frame = ttk.Frame(calc_frame)
        timbre_frame.pack(fill="x", pady=2)
        ttk.Label(timbre_frame, text="Droit de Timbre:").pack(side="left")
        self.timbre_var = tk.StringVar()
        ttk.Entry(timbre_frame, textvariable=self.timbre_var, width=15).pack(side="right")
        
        # Total TTC (editable)
        ttc_frame = ttk.Frame(calc_frame)
        ttc_frame.pack(fill="x", pady=2)
        ttk.Label(ttc_frame, text="Total TTC:", font=("Segoe UI", 10, "bold")).pack(side="left")
        self.ttc_var = tk.StringVar()
        ttc_entry = ttk.Entry(ttc_frame, textvariable=self.ttc_var, width=15, font=("Segoe UI", 10, "bold"))
        ttc_entry.pack(side="right")
        
        # Notes
        ttk.Label(form_frame, text="Notes:").pack(anchor="w", pady=(10, 0))
        self.notes_text = tk.Text(form_frame, height=3, width=50)
        self.notes_text.pack(fill="x", pady=(0, 10))
        
        # Auto-fill notes with BL summary
        notes_content = f"Facture ciment générée à partir de {len(self.selected_deliveries)} BL:\n"
        for delivery in self.selected_deliveries:
            notes_content += f"- {delivery['number']}: {delivery['material']} ({delivery['quantity']})\n"
        self.notes_text.insert("1.0", notes_content)
        
        # Buttons
        self.button_frame = ttk.Frame(main_frame)
        self.button_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(self.button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        
        # Generate button initially hidden
        self.generate_btn = ttk.Button(self.button_frame, text="Générer Facture", command=self.generate_facture)
        # Do not pack initially - button is hidden
    
    def check_facture_fields_completion(self, event=None):
        """Check if all required fields are filled and show/hide Generate button"""
        try:
            # Check if all required fields have values
            fournisseur = self.fournisseur_var.get().strip()
            num_facture = self.num_facture_var.get().strip()
            
            # Check if all required fields are filled
            all_filled = fournisseur and num_facture
            
            if all_filled:
                # All validations passed - show the Generate button
                self.generate_btn.pack(side="right")
            else:
                # Not all fields filled - hide button
                self.generate_btn.pack_forget()
                
        except Exception:
            # Any error - hide button
            self.generate_btn.pack_forget()
    
    def generate_facture_number(self):
        """Generate automatic facture number - DISABLED: No auto-fill requested"""
        # Return empty string instead of auto-generating
        return ""
    
    def calculate_totals(self):
        """Calculate all totals automatically"""
        try:
            # Calculate HT (quantity × price from materials inventory)
            total_ht = 0.0
            total_quantity = 0.0
            
            for delivery in self.selected_deliveries:
                # Extract quantity (remove unit text)
                quantity_str = delivery.get("quantity", "0")
                try:
                    # Extract number from strings like "50 sacs", "10 tonnes"
                    quantity_num = float(quantity_str.split()[0]) if " " in quantity_str else float(quantity_str)
                    total_quantity += quantity_num
                    
                    # Find material price from inventory
                    material_name = delivery.get("material", "")
                    material_price = 0.0
                    
                    # Look for matching material in inventory
                    for material in self.materials:
                        if material.get("name", "").lower() == material_name.lower():
                            material_price = float(material.get("price", 0))
                            break
                    
                    # Calculate HT for this delivery: quantity × price
                    delivery_ht = quantity_num * material_price
                    total_ht += delivery_ht
                    
                except (ValueError, IndexError):
                    pass
            
            # Calculate taxes from settings (remove hardcoding)
            try:
                from ..logic import taxes as tax_system
                
                # Get TVA rate from settings (default 19% if not found)
                tva_tax = tax_system.get_tax_by_name("TVA 19%")
                tva_rate = tva_tax['value'] / 100.0 if tva_tax else 0.19
                tva_amount = total_ht * tva_rate
                
                # Get Fond de Soutien from settings (default 1.0 per quantity)
                fond_tax = tax_system.get_tax_by_name("Fond de Soutien")
                fond_rate = fond_tax['value'] if fond_tax else 1.0
                fond_soutien = total_quantity * fond_rate
                
                # Get Droit de Timbre from settings (default 1.0 fixed)
                timbre_tax = tax_system.get_tax_by_name("Droit de Timbre")
                timbre = timbre_tax['value'] if timbre_tax else 1.0
                
                print(f"[CIMENT] Using dynamic taxes: TVA={tva_rate*100:.1f}%, Fond={fond_rate}, Timbre={timbre}")
                
            except Exception as tax_error:
                print(f"[CIMENT] Error loading taxes from settings, using defaults: {tax_error}")
                # Fallback to hardcoded values if settings fail
                tva_amount = total_ht * 0.19
                fond_soutien = total_quantity * 1.0
                timbre = 1.0
            
            # Calculate TTC
            total_ttc = total_ht + tva_amount + fond_soutien + timbre
            
            # Update fields
            self.mt_ht_var.set(f"{total_ht:.3f}")
            self.tva_var.set(f"{tva_amount:.3f}")
            self.fond_soutien_var.set(f"{fond_soutien:.3f}")
            self.timbre_var.set(f"{timbre:.3f}")
            self.ttc_var.set(f"{total_ttc:.3f}")
            
        except Exception as e:
            print(f"[CIMENT] Error calculating totals: {e}")
            # Set default values with fallback tax rates
            try:
                from ..logic import taxes as tax_system
                timbre_tax = tax_system.get_tax_by_name("Droit de Timbre")
                default_timbre = timbre_tax['value'] if timbre_tax else 1.0
            except:
                default_timbre = 1.0
                
            self.mt_ht_var.set("0.000")
            self.tva_var.set("0.000")
            self.fond_soutien_var.set("0.000")
            self.timbre_var.set(f"{default_timbre:.3f}")
            self.ttc_var.set(f"{default_timbre:.3f}")
    
    def generate_facture(self):
        """Generate facture and save to achat table"""
        try:
            # Validate inputs
            fournisseur = self.fournisseur_var.get().strip()
            num_facture = self.num_facture_var.get().strip()
            date_str = self.date_entry.get()  # Get date from calendar widget
            
            if not fournisseur or not num_facture:
                messagebox.showerror("Erreur", "Fournisseur et numéro de facture sont requis")
                return
            
            # Get calculated values
            mt_ht = float(self.mt_ht_var.get())
            tva = float(self.tva_var.get())
            fond_soutien = float(self.fond_soutien_var.get())
            timbre = float(self.timbre_var.get())
            ttc = float(self.ttc_var.get())
            notes = self.notes_text.get("1.0", tk.END).strip()
            
            # Create achat record data
            achat_data = {
                "date": date_str,
                "fournisseur": fournisseur,
                "num_facture": num_facture,
                "mt_ht": mt_ht,
                "ttc": ttc,
                "timbre": timbre,
                "taxes": [
                    {"name": "TVA 19%", "value": tva},
                    {"name": "Fond de Soutien", "value": fond_soutien}
                ],
                "notes": notes,
                "paiement_statut": "en_attente",
                "paiement_methode": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Show success message
            success_msg = f"Facture {num_facture} générée avec succès!\n\n"
            success_msg += f"Fournisseur: {fournisseur}\n"
            success_msg += f"Montant HT: {mt_ht:.3f} DA\n"
            success_msg += f"TVA 19%: {tva:.3f} DA\n"
            success_msg += f"Fond de Soutien: {fond_soutien:.3f} DA\n"
            success_msg += f"Droit de Timbre: {timbre:.3f} DA\n"
            success_msg += f"Total TTC: {ttc:.3f} DA"
            
            messagebox.showinfo("Succès", success_msg)
            
            self.result = achat_data
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Erreur", f"Erreur dans les calculs: {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération: {e}")
    
    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.dialog.destroy()


class CimentAvoirDialog:
    """Dialog for creating avoir (credit note) from cement delivery notes"""
    
    def __init__(self, parent, delivery_notes, materials=None, preselected=False):
        self.parent = parent
        self.delivery_notes = delivery_notes
        self.materials = materials or []
        self.preselected = preselected  # If True, all delivery_notes are pre-selected
        self.result = None
        
        # Create dialog
        self.dialog = tk.Toplevel(parent)
        title = "Générer Avoir - BL Sélectionnés" if preselected else "Générer Avoir - Auto-rempli"
        self.dialog.title(title)
        self.dialog.geometry("600x550")  # Reduced height
        self.dialog.resizable(True, True)  # Allow resizing
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Center dialog
        self.dialog.geometry("+%d+%d" % (parent.winfo_rootx() + 50, parent.winfo_rooty() + 50))
        
        self.setup_ui()
        self.calculate_totals()
        self.dialog.wait_window()
    
    def setup_ui(self):
        """Setup dialog UI similar to facture but for avoir"""
        # Create main scrollable frame
        canvas = tk.Canvas(self.dialog)
        scrollbar = ttk.Scrollbar(self.dialog, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Main content frame (now inside scrollable area)
        main_frame = ttk.Frame(scrollable_frame, padding=20)
        main_frame.pack(fill="both", expand=True)
        
        # Title
        title_text = "Générer Avoir - BL Sélectionnés" if self.preselected else "Générer Avoir Ciment"
        title_label = ttk.Label(main_frame, text=title_text, font=("Segoe UI", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Header info frame
        header_frame = ttk.LabelFrame(main_frame, text="Informations de l'Avoir", padding=15)
        header_frame.pack(fill="x", pady=(0, 15))
        
        # Two columns for header
        col1 = ttk.Frame(header_frame)
        col1.pack(side="left", fill="both", expand=True)
        col2 = ttk.Frame(header_frame)
        col2.pack(side="right", fill="both", expand=True, padx=(20, 0))
        
        # Date
        ttk.Label(col1, text="Date:").pack(anchor="w")
        self.date_entry = DateEntry(
            col1, 
            width=12, 
            background='darkblue',
            foreground='white', 
            borderwidth=2,
            date_pattern='dd/mm/yy'
        )
        self.date_entry.pack(anchor="w", pady=(0, 10))
        
        # Numéro avoir
        ttk.Label(col1, text="Numéro Avoir:").pack(anchor="w")
        self.num_avoir_var = tk.StringVar(value=f"AV-{datetime.now().strftime('%Y%m%d')}-001")
        ttk.Entry(col1, textvariable=self.num_avoir_var, width=20).pack(anchor="w", pady=(0, 10))
        
        # Fournisseur
        ttk.Label(col2, text="Fournisseur:").pack(anchor="w")
        self.fournisseur_var = tk.StringVar()
        fournisseur_combo = ttk.Combobox(col2, textvariable=self.fournisseur_var, width=25)
        
        # Get suppliers from delivery notes
        suppliers = list(set(d['supplier'] for d in self.delivery_notes if 'supplier' in d))
        # Apply priority sort (Carthage first) if available
        if hasattr(self.parent, '_priority_sort_suppliers'):
            suppliers = self.parent._priority_sort_suppliers(suppliers)
        fournisseur_combo['values'] = suppliers
        if suppliers:
            # Prefer Carthage Cement as default if present
            preferred = None
            for n in suppliers:
                nn = (n or '').lower()
                if 'carthage' in nn and ('cement' in nn or 'ciment' in nn):
                    preferred = n
                    break
            if preferred:
                fournisseur_combo.set(preferred)
            elif self.preselected and self.delivery_notes:
                fournisseur_combo.set(self.delivery_notes[0]['supplier'])
            else:
                fournisseur_combo.set(suppliers[0])
        fournisseur_combo.pack(anchor="w", pady=(0, 10))
        fournisseur_combo.bind('<<ComboboxSelected>>', self.on_fournisseur_change)
        
        # Avoir Type Selection  
        ttk.Label(col2, text="Type d'Avoir:").pack(anchor="w")
        self.avoir_type_var = tk.StringVar()
        self.avoir_type_combo = ttk.Combobox(col2, textvariable=self.avoir_type_var, width=25, state="readonly")
        self.avoir_type_combo['values'] = [
            "Paiement avant 20 jours",
            "Total factures 200 tonnes/mois", 
            "Sur livraison",
            "Par année"
        ]
        self.avoir_type_combo.pack(anchor="w", pady=(0, 10))
        self.avoir_type_combo.bind('<<ComboboxSelected>>', self.on_avoir_type_change)
        
        # Delivery notes selection
        selection_title = "Bons de Livraison Sélectionnés" if self.preselected else "Bons de Livraison à Inclure"
        delivery_frame = ttk.LabelFrame(main_frame, text=selection_title, padding=15)
        delivery_frame.pack(fill="x", pady=(0, 15))  # Changed from fill="both" expand=True
        
        # Create frame for delivery selection with smaller scrollbar
        canvas_delivery = tk.Canvas(delivery_frame, height=100)  # Fixed smaller height
        scrollbar_delivery = ttk.Scrollbar(delivery_frame, orient="vertical", command=canvas_delivery.yview)
        scrollable_delivery_frame = ttk.Frame(canvas_delivery)
        
        self.delivery_vars = {}
        self.delivery_labels = {}
        
        for delivery in self.delivery_notes:
            var = tk.BooleanVar()
            # Auto-select if coming from BL tab with preselected deliveries
            if self.preselected:
                var.set(True)
            self.delivery_vars[delivery['id']] = var
            
            frame = ttk.Frame(scrollable_delivery_frame)
            frame.pack(fill="x", pady=2)
            
            check = ttk.Checkbutton(frame, variable=var, command=self.calculate_totals)
            check.pack(side="left")
            
            label = ttk.Label(frame, text=f"BL {delivery.get('number', '')} - {delivery.get('material', '')} - {delivery.get('amount', '')} DA")
            label.pack(side="left", padx=(5, 0))
            self.delivery_labels[delivery['id']] = label
        
        scrollable_delivery_frame.bind("<Configure>", lambda e: canvas_delivery.configure(scrollregion=canvas_delivery.bbox("all")))
        canvas_delivery.create_window((0, 0), window=scrollable_delivery_frame, anchor="nw")
        canvas_delivery.configure(yscrollcommand=scrollbar_delivery.set)
        
        canvas_delivery.pack(side="left", fill="both", expand=True)
        scrollbar_delivery.pack(side="right", fill="y")
        
        # Totals frame
        totals_frame = ttk.LabelFrame(main_frame, text="Calculs de l'Avoir", padding=15)
        totals_frame.pack(fill="x", pady=(0, 15))

        # Lock flags to protect fields edited by user; auto-calc won't override locked fields
        self._lock_ht = False
        self._lock_tva = False
        self._lock_timbre = False
        self._lock_ttc = False
        self._updating = False  # internal flag to avoid feedback loops

        # Create calculation fields (without fond de soutien)
        calc_frame = ttk.Frame(totals_frame)
        calc_frame.pack(fill="x")
        
        # Montant HT
        ttk.Label(calc_frame, text="Montant HT:").grid(row=0, column=0, sticky="w", padx=(0, 10))
        self.mt_ht_var = tk.StringVar(value="0.000")
        self._mt_ht_entry = ttk.Entry(calc_frame, textvariable=self.mt_ht_var, width=15)
        self._mt_ht_entry.grid(row=0, column=1, padx=(0, 5))
        ttk.Label(calc_frame, text="DA").grid(row=0, column=2, sticky="w")
        self._mt_ht_entry.bind('<KeyRelease>', lambda e: self._mark_lock_and_recompute('ht'))
        
        # TVA 19%
        ttk.Label(calc_frame, text="TVA 19%:").grid(row=1, column=0, sticky="w", padx=(0, 10))
        self.tva_var = tk.StringVar(value="0.000")
        self._tva_entry = ttk.Entry(calc_frame, textvariable=self.tva_var, width=15)
        self._tva_entry.grid(row=1, column=1, padx=(0, 5))
        ttk.Label(calc_frame, text="DA").grid(row=1, column=2, sticky="w")
        self._tva_entry.bind('<KeyRelease>', lambda e: self._mark_lock_and_recompute('tva'))
        
        # Droit de timbre - Load from taxes table as negative amount for avoir
        ttk.Label(calc_frame, text="Droit de Timbre:").grid(row=2, column=0, sticky="w", padx=(0, 10))
        
        # Get timbre value from taxes table as negative for avoir
        try:
            from ..logic import taxes as tax_system
            timbre_tax = tax_system.get_tax_by_name("Droit de Timbre")
            timbre_value = timbre_tax['value'] if timbre_tax else 1.0
            # Make it negative for avoir (credit note)
            timbre_negative = -abs(timbre_value)
        except:
            timbre_negative = -1.0  # Default negative timbre
        
        self.timbre_var = tk.StringVar(value=f"{timbre_negative:.3f}")
        self._timbre_entry = ttk.Entry(calc_frame, textvariable=self.timbre_var, width=15)
        self._timbre_entry.grid(row=2, column=1, padx=(0, 5))
        ttk.Label(calc_frame, text="DA").grid(row=2, column=2, sticky="w")
        # Recompute TTC when user edits timbre, without locking TTC if user edits TTC directly
        self._timbre_entry.bind('<KeyRelease>', lambda e: self._mark_lock_and_recompute('timbre'))
        
        # Total TTC
        ttk.Label(calc_frame, text="Total TTC:", font=("Segoe UI", 10, "bold")).grid(row=3, column=0, sticky="w", padx=(0, 10), pady=(10, 0))
        self.ttc_var = tk.StringVar(value="0.000")
        self._ttc_entry = ttk.Entry(calc_frame, textvariable=self.ttc_var, width=15, font=("Segoe UI", 10, "bold"))
        self._ttc_entry.grid(row=3, column=1, padx=(0, 5), pady=(10, 0))
        ttk.Label(calc_frame, text="DA", font=("Segoe UI", 10, "bold")).grid(row=3, column=2, sticky="w", pady=(10, 0))
        self._ttc_entry.bind('<KeyRelease>', lambda e: self._mark_lock_and_recompute('ttc'))

        # Reset button to clear locks and return to full auto updates
        reset_frame = ttk.Frame(totals_frame)
        reset_frame.pack(fill="x", pady=(6, 0))
        ttk.Button(reset_frame, text="↺ Réinitialiser auto", command=self._reset_auto).pack(anchor="w")
        
        # Notes
        ttk.Label(main_frame, text="Notes:").pack(anchor="w")
        self.notes_text = tk.Text(main_frame, height=3, width=50)
        self.notes_text.pack(fill="x", pady=(0, 15))
        self.notes_text.insert("1.0", "Avoir pour retour de marchandise")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill="x")
        
        ttk.Button(button_frame, text="Annuler", command=self.cancel).pack(side="right", padx=(5, 0))
        ttk.Button(button_frame, text="Générer Avoir", command=self.generate_avoir, style="Accent.TButton").pack(side="right")
    
    def on_fournisseur_change(self, event=None):
        """Filter delivery notes by selected supplier"""
        selected_supplier = self.fournisseur_var.get()
        
        # Update delivery notes visibility based on supplier
        for delivery in self.delivery_notes:
            if delivery.get('supplier') == selected_supplier:
                # Show this delivery note
                if delivery['id'] in self.delivery_labels:
                    self.delivery_labels[delivery['id']].pack()
            else:
                # Hide this delivery note
                if delivery['id'] in self.delivery_labels:
                    self.delivery_labels[delivery['id']].pack_forget()
        
        self.calculate_totals()
    
    def on_avoir_type_change(self, event=None):
        """Validate avoir type selection against delivery note eligibility"""
        selected_type = self.avoir_type_var.get()
        
        # Map display names to database field names
        type_mapping = {
            "Paiement avant 20 jours": "avoir_payment_before_20_days",
            "Total factures 200 tonnes/mois": "avoir_total_factures_200t_month",
            "Sur livraison": "avoir_sur_livraison", 
            "Par année": "avoir_par_annee"
        }
        
        if selected_type not in type_mapping:
            return
            
        field_name = type_mapping[selected_type]
        
        # Check if any selected delivery notes have this avoir type enabled
        eligible_deliveries = []
        ineligible_deliveries = []
        
        for delivery in self.delivery_notes:
            if delivery['id'] in self.delivery_vars and self.delivery_vars[delivery['id']].get():
                # Check if this delivery has the selected avoir type enabled
                is_eligible = delivery.get(field_name, 0) == 1
                if is_eligible:
                    eligible_deliveries.append(delivery)
                else:
                    ineligible_deliveries.append(delivery)
        
        # Show creative notification if some deliveries are not eligible
        if ineligible_deliveries:
            ineligible_count = len(ineligible_deliveries)
            total_selected = len(eligible_deliveries) + len(ineligible_deliveries)
            
            if ineligible_count == total_selected:
                # All selected deliveries are ineligible
                messagebox.showwarning(
                    "🚫 Avoir Non Applicable",
                    f"Aucun des bons de livraison sélectionnés n'est éligible pour l'avoir '{selected_type}'.\n\n"
                    f"💡 Conseil: Vérifiez l'éligibilité des BL lors de leur création ou sélectionnez un autre type d'avoir."
                )
                # Reset selection to allow user to choose again
                self.avoir_type_var.set("")
            else:
                # Some deliveries are ineligible
                messagebox.showinfo(
                    "⚠️ Attention - Éligibilité Partielle",
                    f"Sur {total_selected} BL sélectionnés, {ineligible_count} ne sont pas éligibles pour l'avoir '{selected_type}'.\n\n"
                    f"✅ {len(eligible_deliveries)} BL éligibles seront inclus dans l'avoir\n"
                    f"❌ {ineligible_count} BL seront exclus automatiquement\n\n"
                    f"💡 Les calculs se baseront uniquement sur les BL éligibles."
                )
        
        # Trigger recalculation with eligibility filtering
        self.calculate_totals()
    
    def calculate_totals(self, *args):
        """Calculate totals for selected delivery notes with avoir type logic; respects field locks."""

        selected_type = self.avoir_type_var.get()
        
        # Map display names to database field names
        type_mapping = {
            "Paiement avant 20 jours": "avoir_payment_before_20_days",
            "Total factures 200 tonnes/mois": "avoir_total_factures_200t_month",
            "Sur livraison": "avoir_sur_livraison", 
            "Par année": "avoir_par_annee"
        }
        
        # Calculate avoir based on selected type
        if selected_type == "Paiement avant 20 jours":
            # Special calculation for "Paiement avant 20 jours": total quantity * avoir rate
            total_quantity = 0.0
            
            for delivery in self.delivery_notes:
                if (delivery['id'] in self.delivery_vars and 
                    self.delivery_vars[delivery['id']].get() and
                    delivery.get(type_mapping.get(selected_type, ''), 0) == 1):
                    
                    # Get quantity from delivery
                    quantity_str = delivery.get('quantity', '0')
                    if isinstance(quantity_str, str):
                        quantity_str = quantity_str.replace(' tonnes', '').replace(',', '.')
                    
                    try:
                        quantity = float(quantity_str)
                        total_quantity += quantity
                    except ValueError:
                        continue
            
            # Get avoir rate from settings (amount per tonne in DA)
            try:
                from app.stfoom.ui.ciment_avoir_settings import SimpleSettingsManager
                settings_manager = SimpleSettingsManager()
                amount_str = settings_manager.get_setting('carthage_cement_avoir_payment_before_20_days', '0.0')
                rate_per_tonne = float(amount_str)
            except:
                rate_per_tonne = 0.0
            
            total_ht = total_quantity * rate_per_tonne
            
        elif selected_type == "Total factures 200 tonnes/mois":
            # Special calculation for "Total factures 200 tonnes/mois": total quantity * avoir rate
            total_quantity = 0.0
            
            for delivery in self.delivery_notes:
                if (delivery['id'] in self.delivery_vars and 
                    self.delivery_vars[delivery['id']].get() and
                    delivery.get(type_mapping.get(selected_type, ''), 0) == 1):
                    
                    # Get quantity from delivery
                    quantity_str = delivery.get('quantity', '0')
                    if isinstance(quantity_str, str):
                        quantity_str = quantity_str.replace(' tonnes', '').replace(',', '.')
                    
                    try:
                        quantity = float(quantity_str)
                        total_quantity += quantity
                    except ValueError:
                        continue
            
            # Get avoir rate from settings (amount per tonne in DA)
            try:
                from app.stfoom.ui.ciment_avoir_settings import SimpleSettingsManager
                settings_manager = SimpleSettingsManager()
                amount_str = settings_manager.get_setting('carthage_cement_avoir_total_factures_200t_month', '0.0')
                rate_per_tonne = float(amount_str)
            except:
                rate_per_tonne = 0.0
            
            total_ht = total_quantity * rate_per_tonne
            
        elif selected_type == "Sur livraison":
            # Special calculation for "sur livraison": total quantity * amount per tonne
            total_quantity = 0.0
            
            for delivery in self.delivery_notes:
                if (delivery['id'] in self.delivery_vars and 
                    self.delivery_vars[delivery['id']].get() and
                    delivery.get(type_mapping.get(selected_type, ''), 0) == 1):
                    
                    # Get quantity from delivery
                    quantity_str = delivery.get('quantity', '0')
                    if isinstance(quantity_str, str):
                        quantity_str = quantity_str.replace(' tonnes', '').replace(',', '.')
                    
                    try:
                        quantity = float(quantity_str)
                        total_quantity += quantity
                    except ValueError:
                        continue
            
            # Get avoir amount from settings (amount per tonne in DA)
            try:
                from app.stfoom.ui.ciment_avoir_settings import SimpleSettingsManager
                settings_manager = SimpleSettingsManager()
                amount_str = settings_manager.get_setting('carthage_cement_avoir_sur_livraison', '0.0')
                amount_per_tonne = float(amount_str)
            except:
                amount_per_tonne = 0.0
            
            total_ht = total_quantity * amount_per_tonne
            
        else:
            # Standard calculation for other types: count eligible BLs * fixed amount
            eligible_bl_count = 0
            
            for delivery in self.delivery_notes:
                if (delivery['id'] in self.delivery_vars and 
                    self.delivery_vars[delivery['id']].get()):
                    
                    # Check eligibility if avoir type is selected
                    if selected_type and selected_type in type_mapping:
                        field_name = type_mapping[selected_type]
                        if delivery.get(field_name, 0) != 1:
                            continue  # Skip ineligible deliveries
                    
                    eligible_bl_count += 1
            
            # Get avoir amount from settings for the selected type
            if selected_type and selected_type in type_mapping:
                setting_key = f"carthage_cement_avoir_{type_mapping[selected_type].replace('avoir_', '')}"
                try:
                    from app.stfoom.ui.ciment_avoir_settings import SimpleSettingsManager
                    settings_manager = SimpleSettingsManager()
                    amount_str = settings_manager.get_setting(setting_key, '0.0')
                    amount_per_bl = float(amount_str)
                except:
                    amount_per_bl = 0.0
                
                total_ht = eligible_bl_count * amount_per_bl
            else:
                total_ht = 0.0
        
        # Calculate taxes (no fond de soutien for avoir)
        tva = total_ht * 0.19  # 19% TVA
        
        # Get timbre value
        try:
            timbre = float(self.timbre_var.get())
        except ValueError:
            timbre = 0.0
        
        # Calculate TTC
        ttc = total_ht + tva + timbre
        
        # Update display without overwriting user-edited (locked) fields
        try:
            self._updating = True
            if not self._lock_ht:
                self.mt_ht_var.set(f"{total_ht:.3f}")
            if not self._lock_tva:
                self.tva_var.set(f"{tva:.3f}")
            if not self._lock_ttc:
                self.ttc_var.set(f"{ttc:.3f}")
        finally:
            self._updating = False

    def _mark_lock_and_recompute(self, field: str):
        """Mark a field as user-edited (locked) and recompute TTC when appropriate."""
        if field == 'ht':
            self._lock_ht = True
        elif field == 'tva':
            self._lock_tva = True
        elif field == 'timbre':
            self._lock_timbre = True
        elif field == 'ttc':
            self._lock_ttc = True

        # If user changed HT/TVA/Timbre, keep TTC in sync unless TTC itself is locked
        if field in ('ht', 'tva', 'timbre') and not self._lock_ttc:
            try:
                ht = float(self.mt_ht_var.get()) if self.mt_ht_var.get().strip() else 0.0
            except ValueError:
                ht = 0.0
            try:
                tva = float(self.tva_var.get()) if self.tva_var.get().strip() else 0.0
            except ValueError:
                tva = 0.0
            try:
                timbre = float(self.timbre_var.get()) if self.timbre_var.get().strip() else 0.0
            except ValueError:
                timbre = 0.0
            try:
                self._updating = True
                self.ttc_var.set(f"{(ht + tva + timbre):.3f}")
            finally:
                self._updating = False

    def _reset_auto(self):
        """Clear all locks and recompute values with auto-calculation."""
        self._lock_ht = self._lock_tva = self._lock_timbre = self._lock_ttc = False
        self.calculate_totals()
    
    def generate_avoir(self):
        """Generate avoir and save to achat table"""
        try:
            # Get values
            date_str = self.date_entry.get()
            num_avoir = self.num_avoir_var.get().strip()
            fournisseur = f"[CIMENT] {self.fournisseur_var.get()}"
            
            if not num_avoir or not fournisseur:
                messagebox.showerror("Erreur", "Veuillez remplir tous les champs obligatoires")
                return
            
            # Get calculated values
            mt_ht = float(self.mt_ht_var.get())
            tva = float(self.tva_var.get())
            timbre = float(self.timbre_var.get())
            ttc = float(self.ttc_var.get())
            notes = self.notes_text.get("1.0", tk.END).strip()
            # Prefix notes with selected avoir type code for status tracking
            type_map = {
                "Paiement avant 20 jours": "20J",
                "Total factures 200 tonnes/mois": "200T",
                "Sur livraison": "TR",
                "Par année": "ANNEE",
            }
            sel = self.avoir_type_var.get().strip() if hasattr(self, 'avoir_type_var') else ''
            code = type_map.get(sel)
            if code and "[TYPE:" not in notes:
                notes = f"[TYPE: {code}] " + notes
            
            # Tag notes with avoir type for downstream tracking
            type_map = {
                "Paiement avant 20 jours": "20J",
                "Total factures 200 tonnes/mois": "200T",
                "Sur livraison": "TR",
                "Par année": "ANNEE",
            }
            type_sel = self.avoir_type_var.get().strip() if hasattr(self, 'avoir_type_var') else ''
            type_code = type_map.get(type_sel)
            if type_code:
                notes = f"[TYPE: {type_code}] " + notes

            # Create avoir data (will be saved as negative in the method that calls this)
            avoir_data = {
                "date": date_str,
                "fournisseur": fournisseur,
                "num_facture": num_avoir,
                "mt_ht": mt_ht,
                "ttc": ttc,
                "timbre": timbre,
                "taxes": [
                    {"name": "TVA 19%", "value": tva}
                    # No fond de soutien for avoir
                ],
                "notes": notes,
                "paiement_statut": "en_attente",
                "paiement_methode": "",
                "created_at": datetime.now().isoformat(),
                "updated_at": datetime.now().isoformat()
            }
            
            # Show success message
            success_msg = f"Avoir {num_avoir} généré avec succès!\n\n"
            success_msg += f"Fournisseur: {fournisseur}\n"
            success_msg += f"Montant HT: -{mt_ht:.3f} DA\n"
            success_msg += f"TVA 19%: -{tva:.3f} DA\n"
            success_msg += f"Droit de Timbre: -{timbre:.3f} DA\n"
            success_msg += f"Total TTC: -{ttc:.3f} DA"
            
            messagebox.showinfo("Succès", success_msg)
            
            self.result = avoir_data
            self.dialog.destroy()
            
        except ValueError as e:
            messagebox.showerror("Erreur", f"Erreur dans les calculs: {e}")
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur lors de la génération: {e}")
    
    def cancel(self):
        """Cancel dialog"""
        self.result = None
        self.dialog.destroy()

