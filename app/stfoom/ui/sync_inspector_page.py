"""
Sync Inspector Page
===================
Provides a lightweight per-table comparison between the local DB and the configured
server DB (if reachable as a file path). Shows record counts, an approximate
size (sum of text lengths for visible columns) and a quick PASS/FAIL status.
"""
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
import os
import sqlite3

try:
    from app.tools.diagnostics import audit_sync_health as audit  # optional richer audit module
except Exception:
    audit = None


class SyncInspectorPage(ttk.Frame):
    def __init__(self, parent, go_home):
        super().__init__(parent)
        self.go_home = go_home
        self._build_ui()
        self._populate()

    def _build_ui(self):
        header = ttk.Frame(self)
        header.pack(fill="x", padx=20, pady=12)
        ttk.Label(header, text="Inspecteur de Synchronisation", font=("Segoe UI", 22, "bold")).pack(side="left")
        ttk.Button(header, text="← Retour", command=self.go_home, style="Main.TButton").pack(side="right")

        actions = ttk.Frame(self)
        actions.pack(fill="x", padx=20, pady=(0, 10))
        ttk.Button(actions, text="🔄 Actualiser", command=self._populate, style="Main.TButton").pack(side="left")
        ttk.Button(actions, text="� Export CSV", command=self._export_csv, style="Main.TButton").pack(side="left", padx=(8,0))

        cols = ("table", "local_count", "server_count", "local_size", "server_size", "status")
        self.tree = ttk.Treeview(self, columns=cols, show="headings", height=20)
        self.tree.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        headings = {
            "table": "Table",
            "local_count": "Local: #rows",
            "server_count": "Server: #rows",
            "local_size": "Local: approx size",
            "server_size": "Server: approx size",
            "status": "Status",
        }
        for c in cols:
            self.tree.heading(c, text=headings[c])
            self.tree.column(c, anchor="w", width=180 if c == "table" else 120)

        self.status = ttk.Label(self, text="", font=("Segoe UI", 10))
        self.status.pack(anchor="w", padx=20, pady=(0, 10))

    def _export_csv(self):
        try:
            import csv
            rows = []
            for iid in self.tree.get_children():
                rows.append(self.tree.item(iid)['values'])
            if not rows:
                messagebox.showinfo('Export', 'Aucune donnée à exporter')
                return
            from app.core.path_manager import path_manager
            out = path_manager.data_path / f"sync_inspector_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            with open(out, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['table','local_count','server_count','local_size','server_size','status'])
                writer.writerows(rows)
            messagebox.showinfo('Export', f'Exporté: {out}')
        except Exception as e:
            messagebox.showerror('Export', f'Export failed: {e}')

    def _populate(self):
        for i in self.tree.get_children():
            self.tree.delete(i)

        # Determine DB paths
        try:
            from app.core.path_manager import path_manager
            local_db = str(path_manager._db_path)
        except Exception:
            self.status.config(text='Erreur: impossible de localiser la base locale')
            return

        # Try to get server path from config
        try:
            from app.connection import sync_config
            server_dir = sync_config.get_server_path()
            
            # Check if server_dir is valid and accessible
            if not server_dir or not server_dir.strip():
                self.status.config(text='Avertissement: Aucun chemin serveur configuré')
                server_path = None
                server_db_exists = False
            else:
                # Server path is a directory, database file is stfoom.db inside it
                server_path = os.path.join(server_dir, "stfoom.db")
                server_db_exists = os.path.exists(server_path) and os.path.isfile(server_path)
                
                if not server_db_exists:
                    if not os.path.exists(server_dir):
                        self.status.config(text=f'Avertissement: Répertoire serveur inaccessible: {server_dir}')
                    else:
                        self.status.config(text=f'Avertissement: Base de données serveur non trouvée: {server_path}')
        except Exception as e:
            self.status.config(text=f'Erreur chargement config serveur: {e}')
            server_path = None
            server_db_exists = False

        # Build list of tables to inspect
        tables = []
        # Prefer audit module list if available
        if audit and hasattr(audit, 'SYNC_TABLES'):
            tables = list(audit.SYNC_TABLES.keys())
        else:
            # Discover tables from local DB
            try:
                with sqlite3.connect(local_db) as conn:
                    cur = conn.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
                    tables = [r[0] for r in cur.fetchall()]
            except Exception as e:
                self.status.config(text=f'Erreur listage tables: {e}')
                return

        issues = 0
        def _estimate_table_size_sqlite(db_path: str, table: str, sample_rows: int = 50):
            """Estimate table size in bytes by sampling up to sample_rows rows and extrapolating.

            Returns an integer number of bytes or None on error.
            """
            try:
                if not db_path or not os.path.exists(db_path):
                    return None
                with sqlite3.connect(db_path) as conn:
                    cur = conn.cursor()
                    # total rows
                    try:
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        total = cur.fetchone()[0] or 0
                    except Exception:
                        return None

                    if total == 0:
                        return 0

                    # pick sampling size
                    limit = min(sample_rows, max(1, int(total)))
                    # select all columns for sample rows
                    try:
                        cur.execute(f"SELECT * FROM {table} LIMIT {limit}")
                        rows = cur.fetchall()
                    except Exception:
                        return None

                    if not rows:
                        return 0

                    # compute average row bytes by converting values to str and measuring
                    sample_bytes = 0
                    for row in rows:
                        for v in row:
                            if v is None:
                                continue
                            try:
                                sample_bytes += len(str(v).encode('utf-8'))
                            except Exception:
                                sample_bytes += len(str(v))

                    avg_row = sample_bytes / len(rows)
                    est_total = int(avg_row * total)
                    return est_total
            except Exception:
                return None

        for table in tables:
            l_count = 'N/A'
            s_count = 'N/A'
            l_size = 'N/A'
            s_size = 'N/A'
            status = 'UNKNOWN'
            try:
                # Local counts and estimated size (sqlite)
                try:
                    with sqlite3.connect(local_db) as conn:
                        cur = conn.cursor()
                        cur.execute(f"SELECT COUNT(*) FROM {table}")
                        l_count = cur.fetchone()[0]
                except Exception:
                    l_count = 'ERR'

                l_est = _estimate_table_size_sqlite(local_db, table, sample_rows=50)
                if isinstance(l_est, int):
                    l_size = f"~{l_est/1024:.0f} KB" if l_est < 10*1024*1024 else f"~{l_est/1024/1024:.1f} MB"
                else:
                    l_size = 'N/A'

                if server_db_exists and os.path.isfile(server_path):
                    try:
                        with sqlite3.connect(server_path) as sconn:
                            scur = sconn.cursor()
                            scur.execute(f"SELECT COUNT(*) FROM {table}")
                            s_count = scur.fetchone()[0]
                    except Exception:
                        s_count = 'ERR'
                    s_est = _estimate_table_size_sqlite(server_path, table, sample_rows=50)
                    if isinstance(s_est, int):
                        s_size = f"~{s_est/1024:.0f} KB" if s_est < 10*1024*1024 else f"~{s_est/1024/1024:.1f} MB"
                    else:
                        s_size = 'N/A'
                else:
                    s_count = 'N/A'
                    s_size = 'N/A'

                # Determine status
                if isinstance(l_count, int) and isinstance(s_count, int):
                    status = 'PASS' if l_count == s_count else 'DIFF'
                elif isinstance(l_count, int) and (s_count == 'N/A' or s_count == 'ERR'):
                    status = 'OK'
                elif l_count == 'ERR':
                    status = 'ERROR'
                else:
                    status = 'UNKNOWN'

                if status not in ('PASS', 'OK'):
                    issues += 1
            except Exception as e:
                status = f'ERR: {e}'
                issues += 1

            self.tree.insert("", "end", values=(
                table,
                l_count,
                s_count,
                l_size,
                s_size,
                status
            ))

        self.status.config(text=f"Inspecteur: {len(tables)} tables inspectées, problèmes: {issues}")
