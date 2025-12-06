"""
stfoom.ui.sync_page
==================
Sync management page for viewing and controlling synchronization.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from app.connection import sync
from app.connection import sync_config
from datetime import datetime
import threading
import time
import os

class SyncPage(ttk.Frame):
    """Page for managing synchronization settings and status."""
    
    def __init__(self, parent, go_home):
        super().__init__(parent)
        self.go_home = go_home
        self.setup_ui()
        # When the page is actually mapped (shown), ensure interval control is focused
        try:
            self.bind('<Map>', lambda e: self._on_mapped())
        except Exception:
            pass
        self.update_status()

    def _on_mapped(self):
        """Called when the SyncPage is displayed (mapped); focus the interval entry and print geometry."""
        try:
            self.update_idletasks()
            if hasattr(self, 'interval_entry'):
                try:
                    self.interval_entry.focus_set()
                    self.interval_entry.selection_range(0, 'end')
                except Exception:
                    pass
                try:
                    w = self.interval_entry.winfo_width(); h = self.interval_entry.winfo_height()
                    print(f"[SYNC PAGE][MAPPED] interval_entry size: {w}x{h}")
                except Exception:
                    pass
        except Exception:
            pass
        
    def setup_ui(self):
        """Setup the user interface."""
        # Header
        header_frame = ttk.Frame(self)
        header_frame.pack(fill="x", padx=20, pady=20)
        ttk.Label(header_frame, text="Gestion de la Synchronisation", font=("Segoe UI", 24, "bold")).pack(side="left")
        ttk.Button(header_frame, text="← Retour", command=self.go_home, style="Main.TButton").pack(side="right")

        # Watcher control section
        watcher_frame = ttk.Frame(self)
        watcher_frame.pack(fill="x", padx=20, pady=(0, 10))
        self.watcher_status_var = tk.StringVar(value="Arrêté")
        self.watcher_status_label = ttk.Label(watcher_frame, textvariable=self.watcher_status_var, font=("Segoe UI", 11, "italic"))
        self.watcher_status_label.pack(side="left", padx=(0, 10))
        ttk.Button(watcher_frame, text="Démarrer le Watcher", command=self.start_watcher, style="Main.TButton").pack(side="left", padx=(0, 5))
        ttk.Button(watcher_frame, text="Arrêter le Watcher", command=self.stop_watcher, style="Main.TButton").pack(side="left", padx=(0, 5))

        # Create scrollable container for main content
        self.create_scrollable_content_area()

        # Test Sync System button
        test_frame = ttk.Frame(self)
        test_frame.pack(fill="x", padx=20, pady=(10, 0))
        ttk.Button(test_frame, text="Tester le Système de Sync", command=self.run_full_sync_test, style="Accent.TButton").pack(side="left")
        self.test_result_var = tk.StringVar(value="")
        self.test_result_label = ttk.Label(test_frame, textvariable=self.test_result_var, font=("Segoe UI", 10))
        self.test_result_label.pack(side="left", padx=(10, 0))

        # Quick inspect button
        ttk.Button(test_frame, text="Inspecter le Sync", command=self.open_inspector, style="Main.TButton").pack(side="right")

    def create_scrollable_content_area(self):
        """Create a scrollable container for the main content."""
        # Create a canvas and scrollbar for scrolling
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        # Pack the canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True, padx=20, pady=(0, 10))
        self.scrollbar.pack(side="right", fill="y", pady=(0, 10))

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

        def _bind_to_mousewheel(event):
            self.canvas.bind_all("<MouseWheel>", _on_mousewheel)

        def _unbind_from_mousewheel(event):
            self.canvas.unbind_all("<MouseWheel>")

        self.canvas.bind('<Enter>', _bind_to_mousewheel)
        self.canvas.bind('<Leave>', _unbind_from_mousewheel)

        # Configuration quick-access placed directly under header so it's visible
        self.create_config_section(self.scrollable_frame)

        # Main content sections
        self.create_status_section(self.scrollable_frame)
        self.create_manual_sync_section(self.scrollable_frame)
        self.create_log_section(self.scrollable_frame)

    def start_watcher(self):
        try:
            from app.connection import sync
            sync.start_server_watcher(self.on_server_update)
            self.watcher_status_var.set("En cours")
            self.log_message("Watcher démarré.")
        except Exception as e:
            self.log_message(f"Erreur lors du démarrage du watcher: {e}")
            self.watcher_status_var.set("Erreur")

    def stop_watcher(self):
        try:
            from app.connection import sync
            sync.stop_server_watcher()
            self.watcher_status_var.set("Arrêté")
            self.log_message("Watcher arrêté.")
        except Exception as e:
            self.log_message(f"Erreur lors de l'arrêt du watcher: {e}")
            self.watcher_status_var.set("Erreur")

    def on_server_update(self):
        self.log_message("Changement détecté sur le serveur!")
        self.update_status()

    def run_full_sync_test(self):
        self.test_result_var.set("Test en cours...")
        self.log_message("🚀 DÉMARRAGE DU TEST COMPLET DU SYSTÈME DE SYNCHRONISATION")
        self.log_message("=" * 80)
        start_time = datetime.now()

        def test_thread():
            try:
                from datetime import datetime
                # Import repositories
                self.log_message("📦 Chargement des repositories...")
                from app.stfoom.data.facture_repository import FactureRepository
                from app.stfoom.data.calendar_repository import CalendarRepository
                from app.stfoom.data.devis_repository import DevisRepository
                from app.stfoom.data.caisse_repository import CaisseRepository
                from app.stfoom.data.bank_repository import BankRepository
                from app.stfoom.data.achat_repository import AchatRepository
                from app.stfoom.data.settings_repository import SettingsRepository
                from app.stfoom.data.retenu_repository import RetenuRepository
                from app.stfoom.data.user_repository import UserRepository
                from app.stfoom.data.voiture_repository import VoitureRepository
                from app.stfoom.data.vente_repository import VenteRepository
                self.log_message("✅ Tous les repositories chargés avec succès")

                # Initialize repositories
                self.log_message("🔧 Initialisation des repositories...")
                repositories = {
                    'facture': FactureRepository(),
                    'calendar': CalendarRepository(),
                    'devis': DevisRepository(),
                    'caisse': CaisseRepository(),
                    'bank': BankRepository(),
                    'achat': AchatRepository(),
                    'settings': SettingsRepository(),
                    'retenu': RetenuRepository(),
                    'user': UserRepository(),
                    'voiture': VoitureRepository(),
                    'vente': VenteRepository()
                }
                self.log_message(f"✅ {len(repositories)} repositories initialisés")

                # Define test data for each repository
                self.log_message("📋 Configuration des données de test...")
                repo_tests = [
                    ("Facture", FactureRepository, {"nfacture": 999999, "client": "SYNC_TEST", "created_at": datetime.now().isoformat()}),
                    ("Calendar", CalendarRepository, {"title": "SYNC_TEST", "date_str": datetime.now().strftime("%Y-%m-%d"), "category": "Test"}),
                    ("Devis", DevisRepository, {"client": "SYNC_TEST", "created_at": datetime.now().isoformat()}),
                    ("Caisse", CaisseRepository, {"montant": 123.45, "date_str": datetime.now().strftime("%Y-%m-%d"), "type_": "SYNC_TEST"}),
                    ("Bank", BankRepository, {"nom_banque": "SYNC_TEST", "numero_compte": "999999", "solde_initial": 1.23}),
                    ("Achat", AchatRepository, {"fournisseur": "SYNC_TEST", "montant": 1.23, "date_achat": datetime.now().strftime("%Y-%m-%d")}),
                    ("Settings", SettingsRepository, {"category": "SYNC_TEST", "key": "test", "value": "1"}),
                    ("Retenu", RetenuRepository, {"date": datetime.now().strftime("%Y-%m-%d"), "client": "SYNC_TEST", "nfacture": 999999, "percent": 5.0, "amount": 100.0, "source": "SYNC_TEST"}),
                    ("User", UserRepository, {"username": "sync_test_user", "password": "test", "full_name": "Sync Test", "rank": "user"}),
                    ("Voiture", VoitureRepository, {"matricule": "SYNC-TEST", "marque": "Test", "genre": "Test"}),
                    ("Vente", VenteRepository, {"client_nom": "SYNC_TEST", "produit": "Test", "quantite": 1.0}),
                ]
                self.log_message(f"✅ {len(repo_tests)} tests de repository configurés")

                results = []

                # Helpers: fallback SQL update/delete using detected table and pk column
                def _fallback_update(table, pk_col, pk_val, update_fields):
                    try:
                        from app.core.path_manager import PathManager
                        import sqlite3
                        pm = PathManager()
                        pm.initialize()
                        dbp = str(pm._db_path)
                        if not update_fields:
                            return False
                        set_clause = ", ".join([f"{k} = ?" for k in update_fields.keys()])
                        params = list(update_fields.values()) + [pk_val]
                        q = f"UPDATE {table} SET {set_clause} WHERE {pk_col} = ?"
                        conn = sqlite3.connect(dbp)
                        cur = conn.cursor()
                        cur.execute(q, params)
                        conn.commit()
                        conn.close()
                        return cur.rowcount > 0
                    except Exception as e:
                        results.append(f"[FALLBACK_UPDATE:{table}] Exception: {e}")
                        return False

                def _fallback_delete(table, pk_col, pk_val):
                    try:
                        from app.core.path_manager import PathManager
                        import sqlite3
                        pm = PathManager()
                        pm.initialize()
                        dbp = str(pm._db_path)
                        q = f"DELETE FROM {table} WHERE {pk_col} = ?"
                        conn = sqlite3.connect(dbp)
                        cur = conn.cursor()
                        cur.execute(q, (pk_val,))
                        conn.commit()
                        conn.close()
                        return cur.rowcount > 0
                    except Exception as e:
                        results.append(f"[FALLBACK_DELETE:{table}] Exception: {e}")
                        return False

                # Test each repository
                self.log_message("🧪 DÉBUT DES TESTS DE REPOSITORY...")
                for name, repo_cls, test_data in repo_tests:
                    try:
                        self.log_message(f"🔍 Test du repository: {name}")
                        repo = repo_cls()
                        
                        # Initialize result variables at the start
                        create_result = False
                        update_result = False
                        delete_result = False
                        record_id = None
                        # Determine backing table name heuristically
                        table_name = None
                        for attr in ('table_name', '_table', 'TABLE_NAME', 'table'):
                            if hasattr(repo, attr):
                                table_name = getattr(repo, attr)
                                break
                        if not table_name:
                            # Fallback: infer from class name (VenteRepository -> ventes)
                            # But override with known correct table names for repositories that don't expose table_name
                            repo_class_name = repo.__class__.__name__
                            if repo_class_name == 'CalendarRepository':
                                table_name = 'calendar_events'
                            elif repo_class_name == 'CaisseRepository':
                                table_name = 'caisse_transactions'
                            elif repo_class_name == 'BankRepository':
                                table_name = 'banques'
                            elif repo_class_name == 'SettingsRepository':
                                table_name = 'application_settings'
                            else:
                                guessed = repo_class_name.replace('Repository', '').lower()
                                if not guessed.endswith('s'):
                                    guessed = guessed + 's'
                                table_name = guessed

                        self.log_message(f"📋 Table détectée: '{table_name}'")

                        # Introspect DB columns for that table and only use compatible fields
                        compatible_data = {}
                        cols = []
                        cols_info = []
                        pk_column = None
                        try:
                            # Resolve DB path via path manager (repositories use same DB)
                            from app.core.path_manager import PathManager
                            pm = PathManager()
                            pm.initialize()
                            db_path = str(pm._db_path)
                            import sqlite3
                            conn = sqlite3.connect(db_path)
                            cur = conn.cursor()
                            cur.execute(f"PRAGMA table_info('{table_name}')")
                            fetched = cur.fetchall()
                            for r in fetched:
                                # r: (cid, name, type, notnull, dflt_value, pk)
                                col = {
                                    'name': r[1],
                                    'type': (r[2] or '').upper(),
                                    'notnull': bool(r[3]),
                                    'default': r[4],
                                    'pk': int(r[5])
                                }
                                cols_info.append(col)
                                cols.append(col['name'])
                                if col['pk'] and not pk_column:
                                    pk_column = col['name']
                            conn.close()

                            self.log_message(f"📊 Colonnes trouvées: {len(cols)} ({', '.join(cols[:5])}{'...' if len(cols) > 5 else ''})")
                            self.log_message(f"🔑 Colonne PK détectée: {pk_column or 'aucune'}")

                            # If table exists but no explicit PK flagged, try heuristics to find likely PK
                            if not pk_column:
                                # common names
                                for cand in ('id', 'nfacture', 'numero', 'number', 'no'):
                                    if cand in cols:
                                        pk_column = cand
                                        break
                            if not pk_column:
                                for col in cols_info:
                                    if 'INT' in (col.get('type') or '') or col['name'].endswith('_id'):
                                        pk_column = col['name']
                                        break
                            if not pk_column:
                                for col in cols_info:
                                    if 'INT' in (col.get('type') or '') or col['name'].endswith('_id'):
                                        pk_column = col['name']
                                        break
                        except Exception as db_e:
                            self.log_message(f"⚠️ Erreur introspection DB: {db_e}")
                            cols = []
                            cols_info = []
                            pk_column = None

                        # Build compatible_data from test_data (only keys that exist)
                        if cols:
                            for k, v in test_data.items():
                                if k in cols:
                                    compatible_data[k] = v

                            # Ensure NOT NULL columns without defaults are present by synthesizing values
                            for col in cols_info:
                                if col['notnull'] and col['default'] is None and col['name'] not in compatible_data:
                                    # Synthesize conservative defaults based on column name/type
                                    cname = col['name'].lower()
                                    ctype = col['type']
                                    if 'date' in cname or 'created_at' in cname or 'date_' in cname or 'date' in ctype:
                                        compatible_data[col['name']] = datetime.now().strftime('%Y-%m-%d')
                                    elif 'time' in cname or 'timestamp' in cname:
                                        compatible_data[col['name']] = datetime.now().isoformat()
                                    elif any(kword in cname for kword in ('client','nom','name','produit','title','marque')):
                                        compatible_data[col['name']] = 'SYNC_TEST'
                                    elif 'amount' in cname or 'montant' in cname or 'solde' in cname or 'prix' in cname or 'quantite' in cname or 'price' in cname:
                                        compatible_data[col['name']] = 0
                                    else:
                                        # default to simple text placeholder
                                        compatible_data[col['name']] = 'SYNC_TEST'

                            self.log_message(f"📝 Données compatibles préparées: {len(compatible_data)} champs")
                        else:
                            # if we couldn't get columns, fall back to trying the original test_data
                            compatible_data = test_data.copy()
                            self.log_message(f"⚠️ Introspection impossible, utilisation données brutes: {len(compatible_data)} champs")

                        # If no compatible columns, skip creating a record for this repo
                        if not compatible_data:
                            results.append(f"[{name}] Création: SKIPPED (no compatible columns in table '{table_name}')")
                            create_result = False
                            record_id = None
                            self.log_message(f"⏭️ Création ignorée: aucune colonne compatible")
                        else:
                            # Try a sequence of create-style methods, but pass filtered data
                            create_result = False
                            record_id = None
                            try:
                                if hasattr(repo, "create"):
                                    record_id = repo.create(compatible_data)
                                    create_result = record_id is not None
                                    self.log_message(f"✅ Méthode create() utilisée, ID retourné: {record_id}")
                                elif hasattr(repo, "add_event"):
                                    # Calendar repository - map 'date' to 'date_str'
                                    calendar_data = compatible_data.copy()
                                    if 'date' in calendar_data:
                                        calendar_data['date_str'] = calendar_data.pop('date')
                                    create_result = repo.add_event(**calendar_data)
                                    self.log_message(f"✅ Méthode add_event() utilisée")
                                elif hasattr(repo, "ajouter_banque") and "nom_banque" in compatible_data:
                                    # Bank creation - use ajouter_banque for bank data
                                    create_result = repo.ajouter_banque(
                                        nom_banque=compatible_data.get("nom_banque", "SYNC_TEST"),
                                        numero_compte=compatible_data.get("numero_compte", ""),
                                        solde_initial=compatible_data.get("solde_initial", 0)
                                    )
                                    self.log_message(f"✅ Méthode ajouter_banque() utilisée")
                                elif hasattr(repo, "ajouter_transaction") and "banque_id" in compatible_data:
                                    # Transaction creation - use ajouter_transaction for transaction data
                                    create_result = repo.ajouter_transaction(**compatible_data)
                                    self.log_message(f"✅ Méthode ajouter_transaction() utilisée")
                                elif hasattr(repo, "create_user") and "username" in compatible_data:
                                    create_result = repo.create_user(**compatible_data)
                                    self.log_message(f"✅ Méthode create_user() utilisée")
                                elif hasattr(repo, "create_devis"):
                                    record_id = repo.create_devis(compatible_data)
                                    create_result = record_id is not None
                                    self.log_message(f"✅ Méthode create_devis() utilisée, ID: {record_id}")
                                elif hasattr(repo, "create_vente"):
                                    record_id = repo.create_vente(**compatible_data)
                                    create_result = record_id is not None
                                    self.log_message(f"✅ Méthode create_vente() utilisée, ID: {record_id}")
                                elif hasattr(repo, "add_retenu") and all(k in test_data for k in ["percent", "amount"]):
                                    # Retenu repository - call add_retenu directly with correct parameters
                                    record_id = repo.add_retenu(
                                        date=test_data['date'],
                                        client=test_data['client'],
                                        nfacture=test_data.get('nfacture'),
                                        percent=test_data['percent'],
                                        amount=test_data['amount'],
                                        source=test_data['source'],
                                        notes=test_data.get('notes', ''),
                                        party_type=test_data.get('party_type')
                                    )
                                    create_result = record_id is not None
                                    self.log_message(f"✅ Méthode add_retenu() utilisée, ID: {record_id}")
                                elif hasattr(repo, "add_voiture"):
                                    create_result = repo.add_voiture(compatible_data)
                                    self.log_message(f"✅ Méthode add_voiture() utilisée")
                                else:
                                    create_result = False
                                    self.log_message(f"❌ Aucune méthode de création trouvée")
                            except ImportError as ie:
                                # Missing optional module (e.g., connection.sync_wrapper) - skip repo
                                results.append(f"[{name}] SKIPPED due to missing dependency: {ie}")
                                create_result = False
                                record_id = None
                                self.log_message(f"⚠️ Dépendance manquante: {ie}")
                            except Exception as ce:
                                results.append(f"[{name}] Création Exception: {ce}")
                                create_result = False
                                self.log_message(f"❌ Exception lors de la création: {ce}")

                        results.append(f"[{name}] Création: {'OK' if create_result else ('SKIPPED' if record_id is None and not create_result else 'ÉCHEC')}")

                        # Verify timestamps on created records
                        if create_result and hasattr(repo, "get_all"):
                            try:
                                all_records = repo.get_all()
                                if all_records:
                                    latest_record = all_records[-1] if isinstance(all_records[-1], dict) else None
                                    if latest_record and 'created_at' in latest_record:
                                        created_at = latest_record.get('created_at')
                                        if created_at:
                                            results.append(f"[{name}] ✅ Horodatage automatique vérifié (created_at: {created_at[:19]})")
                                            self.log_message(f"🕒 Horodatage automatique confirmé: {created_at[:19]}")
                                        else:
                                            results.append(f"[{name}] ⚠️ Pas d'horodatage created_at trouvé")
                                            self.log_message(f"⚠️ Aucun horodatage created_at trouvé")
                                    else:
                                        results.append(f"[{name}] ⚠️ Impossible de vérifier l'horodatage automatique")
                                        self.log_message(f"⚠️ Vérification horodatage impossible")
                                else:
                                    self.log_message(f"⚠️ Aucun enregistrement trouvé après création")
                            except Exception as ts_e:
                                results.append(f"[{name}] Erreur vérification horodatage: {ts_e}")
                                self.log_message(f"❌ Erreur vérification horodatage: {ts_e}")

                        # Update operation
                        self.log_message(f"🔄 Test de mise à jour...")
                        update_data = test_data.copy()
                        update_data["updated_at"] = datetime.now().isoformat()
                        # Filter update_data to compatible columns if possible
                        try:
                            if cols:
                                update_data = {k: v for k, v in update_data.items() if k in cols}
                        except Exception:
                            pass

                        if not update_data:
                            results.append(f"[{name}] Mise à jour: SKIPPED (no compatible columns)")
                            update_result = True  # Consider this a successful skip
                            self.log_message(f"⏭️ Mise à jour ignorée: aucune colonne compatible")
                        else:
                            try:
                                # Ensure we have a usable record_id; if not, try to discover last pk via DB
                                if not record_id:
                                    try:
                                        # if pk_column discovered earlier, use it; otherwise, try rowid
                                        if pk_column:
                                            import sqlite3
                                            from app.core.path_manager import PathManager
                                            pm = PathManager()
                                            pm.initialize()
                                            conn = sqlite3.connect(str(pm._db_path))
                                            cur = conn.cursor()
                                            cur.execute(f"SELECT {pk_column} FROM {table_name} ORDER BY {pk_column} DESC LIMIT 1")
                                            row = cur.fetchone()
                                            conn.close()
                                            if row:
                                                record_id = row[0]
                                                self.log_message(f"🔍 ID récupéré depuis DB: {record_id}")
                                        else:
                                            # fallback to sqlite rowid
                                            import sqlite3
                                            from app.core.path_manager import PathManager
                                            pm = PathManager()
                                            pm.initialize()
                                            conn = sqlite3.connect(str(pm._db_path))
                                            cur = conn.cursor()
                                            cur.execute(f"SELECT rowid FROM {table_name} ORDER BY rowid DESC LIMIT 1")
                                            row = cur.fetchone()
                                            conn.close()
                                            if row:
                                                record_id = row[0]
                                                self.log_message(f"🔍 RowID récupéré depuis DB: {record_id}")
                                    except Exception as id_e:
                                        record_id = None
                                        self.log_message(f"❌ Impossible de récupérer l'ID: {id_e}")

                                if hasattr(repo, "update") and record_id:
                                    # Check if the update method accepts id_column parameter
                                    import inspect
                                    update_sig = inspect.signature(repo.update)
                                    if 'id_column' in update_sig.parameters:
                                        if pk_column:
                                            update_result = repo.update(record_id, update_data, id_column=pk_column)
                                            self.log_message(f"✅ Mise à jour avec colonne PK '{pk_column}'")
                                        else:
                                            update_result = repo.update(record_id, update_data)
                                            self.log_message(f"✅ Mise à jour sans colonne PK spécifiée")
                                    else:
                                        # Method doesn't accept id_column parameter
                                        update_result = repo.update(record_id, update_data)
                                        self.log_message(f"✅ Mise à jour (méthode sans paramètre id_column)")
                                elif hasattr(repo, "update"):
                                    # Try to get last inserted id from repo.get_all() as fallback
                                    if hasattr(repo, "get_all"):
                                        all_records = repo.get_all()
                                        if all_records:
                                            # try a few common id keys
                                            last = all_records[-1]
                                            possible_keys = ('id', 'pk', 'rowid', table_name + '_id')
                                            last_id = None
                                            for k in possible_keys:
                                                if isinstance(last, dict) and k in last:
                                                    last_id = last.get(k)
                                                    break
                                            if last_id is None:
                                                # attempt to use any integer-like value
                                                for v in last.values():
                                                    if isinstance(v, int):
                                                        last_id = v
                                                        break
                                            if last_id:
                                                update_result = repo.update(last_id, update_data)
                                                self.log_message(f"✅ Mise à jour avec ID déduit: {last_id}")
                                elif hasattr(repo, "update_event") and record_id:
                                    # Calendar repository - get existing event data and merge with updates
                                    try:
                                        existing_event = repo.get_event_by_id(record_id)
                                        if existing_event:
                                            calendar_update_data = existing_event.copy()
                                            calendar_update_data.update(update_data)
                                            # Ensure required fields are present
                                            if 'date_str' not in calendar_update_data and 'date' in calendar_update_data:
                                                calendar_update_data['date_str'] = calendar_update_data.pop('date')
                                            if 'date_str' not in calendar_update_data:
                                                calendar_update_data['date_str'] = datetime.now().strftime("%Y-%m-%d")
                                            if 'description' not in calendar_update_data:
                                                calendar_update_data['description'] = "SYNC_TEST_UPDATE"
                                            # Filter to only include fields that update_event accepts
                                            allowed_fields = {'title', 'date_str', 'category', 'description', 'done'}
                                            calendar_update_data = {k: v for k, v in calendar_update_data.items() if k in allowed_fields}
                                            repo.update_event(record_id, **calendar_update_data)
                                            update_result = True  # update_event doesn't return a value, assume success
                                            self.log_message(f"✅ Mise à jour via update_event()")
                                        else:
                                            update_result = False
                                            self.log_message(f"❌ Événement {record_id} introuvable pour mise à jour")
                                    except Exception as cal_e:
                                        update_result = False
                                        self.log_message(f"❌ Erreur récupération événement: {cal_e}")
                                elif hasattr(repo, "modifier_transaction") and record_id:
                                    # Caisse repository - ensure required parameters are present
                                    caisse_update_data = update_data.copy()
                                    # Map table column names to method parameter names
                                    param_mapping = {
                                        'type': 'type_transaction',
                                        'date': 'date_transaction',
                                        'num_facture': 'nom_client'  # This is how the method expects it
                                    }
                                    for table_col, method_param in param_mapping.items():
                                        if table_col in caisse_update_data:
                                            caisse_update_data[method_param] = caisse_update_data.pop(table_col)

                                    # Ensure required parameters are present with defaults if missing
                                    if 'type_transaction' not in caisse_update_data:
                                        caisse_update_data['type_transaction'] = 'encaissement'  # Default type
                                    if 'montant' not in caisse_update_data:
                                        caisse_update_data['montant'] = 123.45  # Default amount
                                    if 'date_transaction' not in caisse_update_data:
                                        caisse_update_data['date_transaction'] = datetime.now().strftime("%Y-%m-%d")

                                    # Remove parameters that the method doesn't accept
                                    allowed_params = {'type_transaction', 'montant', 'date_transaction', 'nfacture', 'nom_client', 'numero_recu', 'description', 'mode_paiement', 'echeance'}
                                    caisse_update_data = {k: v for k, v in caisse_update_data.items() if k in allowed_params}

                                    # Ensure we have at least the required parameters
                                    if all(k in caisse_update_data for k in ['type_transaction', 'montant', 'date_transaction']):
                                        update_result = repo.modifier_transaction(record_id, **caisse_update_data)
                                        self.log_message(f"✅ Mise à jour via modifier_transaction()")
                                    else:
                                        update_result = True  # Skip if required parameters missing
                                        self.log_message(f"⏭️ Mise à jour ignorée: paramètres requis manquants")
                                elif hasattr(repo, "modifier_banque") and record_id:
                                    update_result = repo.modifier_banque(record_id, **update_data)
                                    self.log_message(f"✅ Mise à jour via modifier_banque()")
                                elif hasattr(repo, "update_user") and record_id:
                                    update_result = repo.update_user(record_id, **update_data)
                                    self.log_message(f"✅ Mise à jour via update_user()")
                                else:
                                    # No update method available - skip this test
                                    results.append(f"[{name}] Mise à jour: SKIPPED (no update method)")
                                    update_result = True  # Consider this a successful skip
                                    self.log_message(f"⏭️ Mise à jour ignorée: aucune méthode disponible")
                            except Exception as ue:
                                results.append(f"[{name}] Mise à jour Exception: {ue}")
                                update_result = False
                                self.log_message(f"❌ Exception lors de la mise à jour: {ue}")

                        if not results[-1].startswith(f"[{name}] Mise à jour: SKIPPED"):
                            results.append(f"[{name}] Mise à jour: {'OK' if update_result else 'ÉCHEC'}")

                        if not results[-1].startswith(f"[{name}] Suppression: SKIPPED"):
                            results.append(f"[{name}] Suppression: {'OK' if delete_result else 'ÉCHEC'}")

                        # Delete operation
                        self.log_message(f"🗑️ Test de suppression...")
                        try:
                            # Ensure we have a record id for deletion; if not, try to discover it
                            if not record_id:
                                try:
                                    if pk_column:
                                        import sqlite3
                                        from app.core.path_manager import PathManager
                                        pm = PathManager()
                                        pm.initialize()
                                        conn = sqlite3.connect(str(pm._db_path))
                                        cur = conn.cursor()
                                        cur.execute(f"SELECT {pk_column} FROM {table_name} ORDER BY {pk_column} DESC LIMIT 1")
                                        row = cur.fetchone()
                                        conn.close()
                                        if row:
                                            record_id = row[0]
                                            self.log_message(f"🔍 ID récupéré pour suppression: {record_id}")
                                    else:
                                        import sqlite3
                                        from app.core.path_manager import PathManager
                                        pm = PathManager()
                                        pm.initialize()
                                        conn = sqlite3.connect(str(pm._db_path))
                                        cur = conn.cursor()
                                        cur.execute(f"SELECT rowid FROM {table_name} ORDER BY rowid DESC LIMIT 1")
                                        row = cur.fetchone()
                                        conn.close()
                                        if row:
                                            record_id = row[0]
                                            self.log_message(f"🔍 RowID récupéré pour suppression: {record_id}")
                                except Exception as id_e:
                                    record_id = None
                                    self.log_message(f"❌ Impossible de récupérer l'ID pour suppression: {id_e}")

                            if hasattr(repo, "delete") and record_id:
                                # Check if the delete method accepts id_column parameter
                                import inspect
                                delete_sig = inspect.signature(repo.delete)
                                if 'id_column' in delete_sig.parameters:
                                    if pk_column:
                                        delete_result = repo.delete(record_id, id_column=pk_column)
                                        self.log_message(f"✅ Suppression avec colonne PK '{pk_column}'")
                                    else:
                                        delete_result = repo.delete(record_id)
                                        self.log_message(f"✅ Suppression sans colonne PK spécifiée")
                                else:
                                    # Method doesn't accept id_column parameter
                                    delete_result = repo.delete(record_id)
                                    self.log_message(f"✅ Suppression (méthode sans paramètre id_column)")
                            elif hasattr(repo, "delete"):
                                if hasattr(repo, "get_all"):
                                    all_records = repo.get_all()
                                    if all_records:
                                        last = all_records[-1]
                                        last_id = None
                                        if isinstance(last, dict):
                                            last_id = last.get('id') or last.get('pk') or last.get('rowid')
                                        if last_id is None:
                                            for v in last.values():
                                                if isinstance(v, int):
                                                    last_id = v
                                                    break
                                        if last_id:
                                            delete_result = repo.delete(last_id)
                                            self.log_message(f"✅ Suppression avec ID déduit: {last_id}")
                            elif hasattr(repo, "delete_event") and record_id:
                                repo.delete_event(record_id)
                                delete_result = True
                                self.log_message(f"✅ Suppression via delete_event()")
                            elif hasattr(repo, "supprimer_transaction") and record_id:
                                delete_result = repo.supprimer_transaction(record_id)
                                self.log_message(f"✅ Suppression via supprimer_transaction()")
                            elif hasattr(repo, "supprimer_banque") and record_id:
                                delete_result = repo.supprimer_banque(record_id)
                                self.log_message(f"✅ Suppression via supprimer_banque()")
                            elif hasattr(repo, "delete_user") and record_id:
                                delete_result = repo.delete_user(record_id)
                                self.log_message(f"✅ Suppression via delete_user()")
                            else:
                                # No delete method available - skip this test
                                results.append(f"[{name}] Suppression: SKIPPED (no delete method)")
                                delete_result = True  # Consider this a successful skip
                                self.log_message(f"⏭️ Suppression ignorée: aucune méthode disponible")
                        except Exception as de:
                            results.append(f"[{name}] Suppression Exception: {de}")
                            delete_result = False
                            self.log_message(f"❌ Exception lors de la suppression: {de}")

                        self.log_message(f"🏁 Test du repository {name} terminé")
                    except Exception as e:
                        results.append(f"[{name}] Exception: {e}")
                        self.log_message(f"💥 Exception générale pour {name}: {e}")

                # Sync push/pull - but first estimate transfer and confirm with user.
                self.log_message("🔄 PRÉPARATION DE LA SYNCHRONISATION RÉSEAU...")
                push_ok = False
                pull_ok = False
                try:
                    try:
                        # Note: get_estimated_transfer_bytes method doesn't exist in current sync service
                        # We'll skip the estimation for now
                        est_push = est_pull = 0
                        self.log_message(f"📊 Estimation transfert - Push: inconnu, Pull: inconnu")
                    except Exception as est_e:
                        est_push = est_pull = 0
                        self.log_message(f"⚠️ Impossible d'estimer la taille du transfert: {est_e}")

                    # Show human-friendly sizes
                    def _fmt(n):
                        for u in ('B','KB','MB','GB'):
                            if n < 1024.0:
                                return f"{n:.2f} {u}"
                            n /= 1024.0
                        return f"{n:.2f} TB"

                    msg = (
                        f"Estimated push size (local -> server): Unknown\n"
                        f"Estimated pull size (server -> local): Unknown\n\n"
                        "Do you want to perform the network push and pull NOW?\n"
                        "(If you cancel, the test will run create/update/delete locally but skip network transfer.)"
                    )

                    # In headless or automated runs we may auto-confirm via env var
                    if os.environ.get('HEADLESS_CONFIRM_NETWORK') == '1':
                        proceed_network = True
                        self.log_message("🤖 Mode headless détecté - confirmation automatique")
                    else:
                        # Ask the user on the main thread and wait for answer
                        evt = threading.Event()
                        ans = {'value': False}
                        def _ask():
                            try:
                                ans['value'] = messagebox.askyesno("Confirm network sync", msg)
                            finally:
                                evt.set()
                        self.after(0, _ask)
                        evt.wait()
                        proceed_network = ans['value']
                        self.log_message(f"👤 Confirmation utilisateur: {'OUI' if proceed_network else 'NON'}")

                    if proceed_network:
                        # perform push then pull; report progress to UI via after()
                        self.log_message("📤 Démarrage du push vers le serveur...")
                        def _do_push():
                            try:
                                ok = sync.sync_to_server()
                                last = 0  # No get_last_transfer_bytes method available
                                self.after(0, lambda: self.log_message(f"Sync push: {'OK' if ok else 'FAILED'} (transferred ~{_fmt(last)})"))
                                return ok
                            except Exception as e:
                                self.after(0, lambda: self.log_message(f"Sync push exception: {e}"))
                                return False

                        def _do_pull():
                            try:
                                self.log_message("📥 Démarrage du pull depuis le serveur...")
                                ok = sync.sync_from_server()
                                self.after(0, lambda: self.log_message(f"Sync pull: {'OK' if ok else 'FAILED'}"))
                                return ok
                            except Exception as e:
                                self.after(0, lambda: self.log_message(f"Sync pull exception: {e}"))
                                return False

                        push_ok = _do_push()
                        pull_ok = _do_pull()
                        results.append(f"Sync push: {'OK' if push_ok else 'FAILED'}")
                        results.append(f"Sync pull: {'OK' if pull_ok else 'FAILED'}")
                        self.log_message(f"🔄 Résultats réseau - Push: {'✅' if push_ok else '❌'}, Pull: {'✅' if pull_ok else '❌'}")
                    else:
                        results.append("Sync push/pull: SKIPPED by user (dry-run)")
                        self.log_message("⏭️ Synchronisation réseau ignorée par l'utilisateur")
                except Exception as e:
                    results.append(f"Sync push/pull: Exception: {e}")
                    self.log_message(f"💥 Exception synchronisation réseau: {e}")

                # Verification step (timestamp and sync queue checks)
                try:
                    # Test automatic timestamping
                    self.log_message("=== VÉRIFICATION DES HORODATAGES AUTOMATIQUES ===")
                    timestamp_checks = []
                    
                    for name, repo_cls, test_data in repo_tests:
                        try:
                            repo = repo_cls()
                            table_name = None
                            for attr in ('table_name', '_table', 'TABLE_NAME', 'table'):
                                if hasattr(repo, attr):
                                    table_name = getattr(repo, attr)
                                    break
                            if not table_name:
                                guessed = repo.__class__.__name__.replace('Repository', '').lower()
                                if not guessed.endswith('s'):
                                    guessed = guessed + 's'
                                # Override with known correct table names
                                repo_class_name = repo.__class__.__name__
                                if repo_class_name == 'CalendarRepository':
                                    table_name = 'calendar_events'
                                elif repo_class_name == 'CaisseRepository':
                                    table_name = 'caisse_transactions'
                                elif repo_class_name == 'BankRepository':
                                    table_name = 'banques'
                                elif repo_class_name == 'SettingsRepository':
                                    table_name = 'application_settings'
                                else:
                                    table_name = guessed
                            
                            # Check if table has sync fields
                            from app.core.path_manager import PathManager
                            import sqlite3
                            pm = PathManager()
                            pm.initialize()
                            conn = sqlite3.connect(str(pm._db_path))
                            cur = conn.cursor()
                            cur.execute(f"PRAGMA table_info('{table_name}')")
                            cols = [row[1] for row in cur.fetchall()]
                            conn.close()
                            
                            has_created_at = 'created_at' in cols
                            has_updated_at = 'updated_at' in cols
                            has_deleted_at = 'deleted_at' in cols
                            
                            timestamp_checks.append(f"[{name}] Table '{table_name}': created_at={has_created_at}, updated_at={has_updated_at}, deleted_at={has_deleted_at}")
                            
                        except Exception as e:
                            timestamp_checks.append(f"[{name}] Timestamp check failed: {e}")
                    
                    for check in timestamp_checks:
                        self.log_message(check)
                    
                    # Test sync queue integration - UPDATED: Use timestamp-based sync status
                    self.log_message("=== VÉRIFICATION DE L'INTÉGRATION SYNC (TIMESTAMP-BASED) ===")
                    
                    # Check if sync service has pending changes using the new timestamp-based approach
                    try:
                        from app.stfoom.services.sync_service import SyncService
                        sync_service = SyncService()
                        
                        # Get sync queue status (timestamp-based pending changes)
                        queue_status = sync_service.get_sync_queue_status()
                        pending_count = queue_status.get('total_pending', 0)
                        pending_by_table = queue_status.get('pending_by_table', {})
                        
                        self.log_message(f"Changements locaux en attente de sync: {pending_count}")
                        
                        if pending_count > 0:
                            self.log_message("✅ Système de sync timestamp-based actif - changements détectés")
                            # Show details of pending changes by table
                            for table, count in pending_by_table.items():
                                self.log_message(f"  📋 {table}: {count} changements")
                        else:
                            self.log_message("ℹ️ Aucun changement local détecté depuis le dernier sync")
                            
                        # Check last successful sync time
                        last_sync = sync_service._get_last_successful_sync()
                        if last_sync > 0:
                            last_sync_str = datetime.fromtimestamp(last_sync).strftime("%Y-%m-%d %H:%M:%S")
                            self.log_message(f"🕒 Dernier sync réussi: {last_sync_str}")
                        else:
                            self.log_message("🕒 Aucun sync réussi enregistré")
                            
                        # Check server status
                        server_online = sync_service.server_online()
                        self.log_message(f"🌐 Serveur en ligne: {'OUI' if server_online else 'NON'}")
                            
                    except Exception as e:
                        self.log_message(f"Erreur vérification sync timestamp-based: {e}")
                    
                except Exception as e:
                    results.append(f"Vérifications avancées: Exception: {e}")
                    self.log_message(f"Vérifications avancées échouées: {e}")

                # Final summary
                end_time = datetime.now()
                duration = end_time - start_time
                self.log_message(f"🎯 TEST COMPLET TERMINÉ en {duration.total_seconds():.1f} secondes")
                self.log_message("=" * 80)
            except Exception as e:
                self.test_result_var.set("Test échoué.")
                self.log_message(f"Test échoué: {e}")

        threading.Thread(target=test_thread, daemon=True).start()
        
    def create_status_section(self, parent):
        """Create the sync status section."""
        status_frame = ttk.LabelFrame(parent, text="Statut de la Synchronisation", padding=15)
        status_frame.pack(fill="x", pady=(0, 20))
        
        # Server connection
        self.server_status_label = ttk.Label(status_frame, text="Vérification...", font=("Segoe UI", 11))
        self.server_status_label.pack(anchor="w", pady=2)
        
        # Pending changes
        self.pending_label = ttk.Label(status_frame, text="Vérification...", font=("Segoe UI", 11))
        self.pending_label.pack(anchor="w", pady=2)
        
        # Last sync
        self.last_sync_label = ttk.Label(status_frame, text="Vérification...", font=("Segoe UI", 11))
        self.last_sync_label.pack(anchor="w", pady=2)
        
        # Sync errors
        self.errors_label = ttk.Label(status_frame, text="Vérification...", font=("Segoe UI", 11))
        self.errors_label.pack(anchor="w", pady=2)
        
    def create_manual_sync_section(self, parent):
        """Create the manual sync controls section."""
        sync_frame = ttk.LabelFrame(parent, text="Synchronisation Manuelle", padding=15)
        sync_frame.pack(fill="x", pady=(0, 20))
        
        # Sync buttons
        btn_frame = ttk.Frame(sync_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="🔄 Synchroniser Maintenant", 
                  command=self.manual_sync, style="Main.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_frame, text="📥 Télécharger du Serveur", 
                  command=self.sync_from_server, style="Main.TButton").pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_frame, text="📤 Envoyer au Serveur", 
                  command=self.sync_to_server, style="Main.TButton").pack(side="left")
        
        # Progress bar
        self.progress_var = tk.StringVar()
        self.progress_label = ttk.Label(sync_frame, textvariable=self.progress_var, font=("Segoe UI", 10))
        self.progress_label.pack(anchor="w", pady=(10, 0))
        
    def create_config_section(self, parent):
        """Create the configuration section."""
        config_frame = ttk.LabelFrame(parent, text="Configuration", padding=15)
        config_frame.pack(fill="x", pady=(0, 20))
        
        # Server path
        path_frame = ttk.Frame(config_frame)
        path_frame.pack(fill="x", pady=(0, 10))
        
        ttk.Label(path_frame, text="Chemin du serveur:", font=("Segoe UI", 11)).pack(anchor="w")
        
        self.server_path_var = tk.StringVar(value=sync_config.get_server_path())
        self.server_path_entry = ttk.Entry(path_frame, textvariable=self.server_path_var, width=50)
        self.server_path_entry.pack(fill="x", pady=(5, 0))
        
        ttk.Button(path_frame, text="Sauvegarder", 
                  command=self.save_server_path, style="Main.TButton").pack(anchor="w", pady=(5, 0))
        
        # Sync interval
        interval_frame = ttk.Frame(config_frame)
        interval_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Label(interval_frame, text="Intervalle de synchronisation (secondes):", font=("Segoe UI", 11)).pack(anchor="w")
        
        self.interval_var = tk.StringVar(value=str(sync_config.get_sync_interval()))
        self.interval_entry = ttk.Entry(interval_frame, textvariable=self.interval_var, width=10)
        self.interval_entry.pack(anchor="w", pady=(5, 0))
        
        ttk.Button(interval_frame, text="Sauvegarder", 
                  command=self.save_sync_interval, style="Main.TButton").pack(anchor="w", pady=(5, 0))
        # Diagnostic: print widget geometry so we can tell if elements are off-screen
        try:
            # Force layout update then print positions/sizes
            self.update_idletasks()
            x = self.interval_entry.winfo_rootx()
            y = self.interval_entry.winfo_rooty()
            w = self.interval_entry.winfo_width()
            h = self.interval_entry.winfo_height()
            print(f"[SYNC PAGE] Interval entry geometry - x={x} y={y} w={w} h={h}")
            # Find the save button (last child of interval_frame)
            for child in interval_frame.winfo_children():
                if isinstance(child, ttk.Button):
                    bx = child.winfo_rootx(); by = child.winfo_rooty(); bw = child.winfo_width(); bh = child.winfo_height()
                    print(f"[SYNC PAGE] Interval save button geometry - x={bx} y={by} w={bw} h={bh}")
                    break
        except Exception as _e:
            print(f"[SYNC PAGE] Geometry diagnostic failed: {_e}")
        
    def create_log_section(self, parent):
        """Create the sync log section."""
        log_frame = ttk.LabelFrame(parent, text="Journal de Synchronisation", padding=15)
        log_frame.pack(fill="both", expand=True)
        
        # Create a frame for the text widget and scrollbars
        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)
        
        # Log text area with both horizontal and vertical scrollbars
        self.log_text = tk.Text(text_frame, height=15, font=("Consolas", 9), wrap="none")
        
        # Vertical scrollbar
        v_scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=v_scrollbar.set)
        
        # Horizontal scrollbar
        h_scrollbar = ttk.Scrollbar(text_frame, orient="horizontal", command=self.log_text.xview)
        self.log_text.configure(xscrollcommand=h_scrollbar.set)
        
        # Pack the text widget and scrollbars
        self.log_text.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")
        
        # Configure grid weights
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        
        # Clear log button
        ttk.Button(log_frame, text="Effacer le journal", 
                  command=self.clear_log, style="Main.TButton").pack(anchor="w", pady=(10, 0))
        
    def update_status(self):
        """Update the status display."""
        try:
            # Get sync status
            status = sync.get_sync_status()
            
            # Server connection
            if status.get("server_online", False):
                self.server_status_label.config(text="🟢 Connecté au serveur", foreground="green")
            else:
                self.server_status_label.config(text="🔴 Déconnecté du serveur", foreground="red")
            
            # Pending changes
            pending_count = 0
            try:
                pending_count = sync.get_pending_changes_count()
            except Exception:
                # If API missing, keep 0 and log
                pending_count = 0
            if pending_count > 0:
                self.pending_label.config(text=f"⏳ {pending_count} changements en attente", foreground="orange")
            else:
                self.pending_label.config(text="✓ Aucun changement en attente", foreground="green")
            
            # Last sync
            last_sync = status.get("last_sync")
            if last_sync:
                last_sync_str = datetime.fromtimestamp(last_sync).strftime("%d/%m/%Y %H:%M:%S")
                self.last_sync_label.config(text=f"🕒 Dernière sync: {last_sync_str}")
            else:
                self.last_sync_label.config(text="🕒 Aucune synchronisation")
            
            # Sync errors
            errors = status.get("sync_errors", 0)
            if errors > 0:
                self.errors_label.config(text=f"⚠ {errors} erreurs de synchronisation", foreground="red")
            else:
                self.errors_label.config(text="✓ Aucune erreur de synchronisation", foreground="green")
                
        except Exception as e:
            self.log_message(f"Erreur lors de la mise à jour du statut: {e}")
        
        # Update every 5 seconds
        self.after(5000, self.update_status)
        
    def manual_sync(self):
        """Perform manual sync."""
        self.progress_var.set("Synchronisation en cours...")
        self.log_message("Début de la synchronisation manuelle...")
        
        def sync_thread():
            try:
                result = sync.force_sync()
                if result:
                    self.progress_var.set("Synchronisation réussie ✓")
                    self.log_message("Synchronisation manuelle réussie")
                    messagebox.showinfo("Succès", "Synchronisation réussie!")
                else:
                    self.progress_var.set("Échec de la synchronisation ✗")
                    self.log_message("Échec de la synchronisation manuelle")
                    messagebox.showerror("Erreur", "Échec de la synchronisation")
            except Exception as e:
                self.progress_var.set("Erreur de synchronisation ✗")
                self.log_message(f"Erreur lors de la synchronisation: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de la synchronisation: {e}")
        
        threading.Thread(target=sync_thread, daemon=True).start()
        
    def sync_from_server(self):
        """Sync from server only."""
        self.progress_var.set("Téléchargement depuis le serveur...")
        self.log_message("Début du téléchargement depuis le serveur...")
        
        def sync_thread():
            try:
                result = sync.sync_from_server()
                if result:
                    self.progress_var.set("Téléchargement réussi ✓")
                    self.log_message("Téléchargement depuis le serveur réussi")
                    messagebox.showinfo("Succès", "Téléchargement réussi!")
                else:
                    self.progress_var.set("Échec du téléchargement ✗")
                    self.log_message("Échec du téléchargement depuis le serveur")
                    messagebox.showerror("Erreur", "Échec du téléchargement")
            except Exception as e:
                self.progress_var.set("Erreur de téléchargement ✗")
                self.log_message(f"Erreur lors du téléchargement: {e}")
                messagebox.showerror("Erreur", f"Erreur lors du téléchargement: {e}")
        
        threading.Thread(target=sync_thread, daemon=True).start()
        
    def sync_to_server(self):
        """Sync to server only."""
        self.progress_var.set("Envoi vers le serveur...")
        self.log_message("Début de l'envoi vers le serveur...")
        
        def sync_thread():
            try:
                result = sync.sync_to_server()
                if result:
                    self.progress_var.set("Envoi réussi ✓")
                    self.log_message("Envoi vers le serveur réussi")
                    messagebox.showinfo("Succès", "Envoi réussi!")
                else:
                    self.progress_var.set("Échec de l'envoi ✗")
                    self.log_message("Échec de l'envoi vers le serveur")
                    messagebox.showerror("Erreur", "Échec de l'envoi")
            except Exception as e:
                self.progress_var.set("Erreur d'envoi ✗")
                self.log_message(f"Erreur lors de l'envoi: {e}")
                messagebox.showerror("Erreur", f"Erreur lors de l'envoi: {e}")
        
        threading.Thread(target=sync_thread, daemon=True).start()
        
    def save_server_path(self):
        """Save the server path configuration."""
        try:
            new_path = self.server_path_var.get().strip()
            if new_path:
                sync_config.set_server_path(new_path)
                self.log_message(f"Chemin du serveur mis à jour: {new_path}")
                messagebox.showinfo("Succès", "Chemin du serveur sauvegardé")
            else:
                messagebox.showerror("Erreur", "Le chemin du serveur ne peut pas être vide")
        except Exception as e:
            self.log_message(f"Erreur lors de la sauvegarde du chemin: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
            
    def save_sync_interval(self):
        """Save the sync interval configuration."""
        try:
            interval = int(self.interval_var.get())
            if interval > 0:
                sync_config.set_sync_interval(interval)
                self.log_message(f"Intervalle de synchronisation mis à jour: {interval} secondes")
                messagebox.showinfo("Succès", "Intervalle de synchronisation sauvegardé")
            else:
                messagebox.showerror("Erreur", "L'intervalle doit être supérieur à 0")
        except ValueError:
            messagebox.showerror("Erreur", "L'intervalle doit être un nombre entier")
        except Exception as e:
            self.log_message(f"Erreur lors de la sauvegarde de l'intervalle: {e}")
            messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde: {e}")
            
    def log_message(self, message):
        """Add a message to the log."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert("end", log_entry)
        self.log_text.see("end")
        
    def clear_log(self):
        """Clear the log display."""
        self.log_text.delete(1.0, "end")
        self.log_message("Journal effacé") 

    def open_inspector(self):
        """Open a lightweight inspector window showing per-table status."""
        try:
            from app.stfoom.ui.sync_inspector_page import SyncInspectorPage
            win = tk.Toplevel(self)
            win.title("Inspecteur de synchronisation")
            win.geometry("900x600")
            page = SyncInspectorPage(win, go_home=win.destroy)
            page.pack(fill='both', expand=True)
        except Exception as e:
            self.log_message(f"Impossible d'ouvrir l'inspecteur: {e}")
            messagebox.showerror("Erreur", f"Impossible d'ouvrir l'inspecteur: {e}")