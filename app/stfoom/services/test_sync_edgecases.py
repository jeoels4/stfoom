import os
import tempfile
import sqlite3
import time
import unittest

import config.settings as settings


class TestSyncEdgeCases(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.local_db = os.path.join(self.tmpdir.name, 'stfoom.db')
        self.server_db = os.path.join(self.tmpdir.name, 'server.db')
        self._orig_get_db_path = settings.get_db_path
        settings.get_db_path = lambda: self.local_db

        # Reload SyncService
        import importlib
        import app.stfoom.services.sync_service as ss
        importlib.reload(ss)
        self.SyncService = ss.SyncService

    def tearDown(self):
        settings.get_db_path = self._orig_get_db_path
        # Best-effort cleanup: force GC and retry cleanup to avoid Windows file-locks
        import gc, time, shutil
        gc.collect()
        for _ in range(6):
            try:
                self.tmpdir.cleanup()
                break
            except PermissionError:
                gc.collect()
                time.sleep(0.1)
        else:
            # Last resort: try removing files individually and ignore errors
            try:
                if os.path.exists(self.server_db):
                    try:
                        os.remove(self.server_db)
                    except Exception:
                        pass
                if os.path.exists(self.local_db):
                    try:
                        os.remove(self.local_db)
                    except Exception:
                        pass
            except Exception:
                pass

    def test_cheque_print_layout_check_id_1(self):
        # Table with CHECK(id = 1) — only id=1 allowed
        conn = sqlite3.connect(self.server_db)
        conn.execute('CREATE TABLE IF NOT EXISTS cheque_print_layout (id INTEGER PRIMARY KEY CHECK(id = 1), page_width_mm REAL NOT NULL DEFAULT 175.0)')
        conn.commit()
        conn.close()

        svc = self.SyncService()
        svc.get_server_db_path = lambda: self.server_db
        svc._check_server_online = lambda: True

        # Try to insert a record with id != 1 — SyncService should treat constraint as skip
        svc.add_sync_change('cheque_print_layout', '2', {'id': 2, 'page_width_mm': 123.4}, 'insert')
        res = svc.sync_to_server()
        self.assertTrue(res.success)

        # Insert id=1 should work
        svc.add_sync_change('cheque_print_layout', '1', {'id': 1, 'page_width_mm': 200.0}, 'insert')
        res2 = svc.sync_to_server()
        self.assertTrue(res2.success)

        conn = sqlite3.connect(self.server_db)
        cur = conn.cursor()
        cur.execute('SELECT page_width_mm FROM cheque_print_layout WHERE id = 1')
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)

    def test_notnull_and_unique_handling(self):
        conn = sqlite3.connect(self.server_db)
        conn.execute('CREATE TABLE IF NOT EXISTS bon_livraison (id INTEGER PRIMARY KEY, date_livraison DATE NOT NULL, numero TEXT UNIQUE NOT NULL)')
        conn.commit()
        conn.close()

        svc = self.SyncService()
        svc.get_server_db_path = lambda: self.server_db
        svc._check_server_online = lambda: True

        # Missing required date -> should be skipped (treated as success)
        svc.add_sync_change('bon_livraison', '10', {'id': 10, 'numero': 'X1'}, 'insert')
        res = svc.sync_to_server()
        self.assertTrue(res.success)

        # Provide date and unique numero -> should insert
        svc.add_sync_change('bon_livraison', '11', {'id': 11, 'numero': 'X2', 'date_livraison': '2025-10-24'}, 'insert')
        res2 = svc.sync_to_server()
        self.assertTrue(res2.success)

    def test_foreign_key_violation_skipped(self):
        conn = sqlite3.connect(self.server_db)
        conn.execute('PRAGMA foreign_keys = ON')
        conn.execute('CREATE TABLE IF NOT EXISTS parent (id INTEGER PRIMARY KEY)')
        conn.execute('CREATE TABLE IF NOT EXISTS child (id INTEGER PRIMARY KEY, parent_id INTEGER, FOREIGN KEY(parent_id) REFERENCES parent(id))')
        conn.commit()
        conn.close()

        svc = self.SyncService()
        svc.get_server_db_path = lambda: self.server_db
        svc._check_server_online = lambda: True

        # Child referencing non-existing parent should not block queue
        svc.add_sync_change('child', '1', {'id': 1, 'parent_id': 999}, 'insert')
        res = svc.sync_to_server()
        self.assertTrue(res.success)


if __name__ == '__main__':
    unittest.main()
