import os
import tempfile
import sqlite3
import time
import unittest

import config.settings as settings


class TestSyncIntegration(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.local_db = os.path.join(self.tmpdir.name, 'stfoom.db')
        self.server_db = os.path.join(self.tmpdir.name, 'server_stfoom.db')

        # Monkeypatch get_db_path for local DB
        self._orig_get_db_path = settings.get_db_path
        settings.get_db_path = lambda: self.local_db

        # Ensure no preexisting files
        for p in (self.local_db, self.server_db):
            if os.path.exists(p):
                os.remove(p)

        # Reload sync_service so it picks up new get_db_path
        import importlib
        import app.stfoom.services.sync_service as ss
        importlib.reload(ss)
        self.SyncService = ss.SyncService

        # Create local and server tables used by test (use 'ranks' from table_pk_map)
        conn = sqlite3.connect(self.local_db)
        conn.execute("CREATE TABLE IF NOT EXISTS ranks (id INTEGER PRIMARY KEY, name TEXT, updated_at REAL DEFAULT 0, created_at REAL DEFAULT 0)")
        conn.commit()
        conn.close()

        conn = sqlite3.connect(self.server_db)
        conn.execute("CREATE TABLE IF NOT EXISTS ranks (id INTEGER PRIMARY KEY, name TEXT, updated_at REAL DEFAULT 0, created_at REAL DEFAULT 0)")
        conn.commit()
        conn.close()

    def tearDown(self):
        settings.get_db_path = self._orig_get_db_path
        # Try to close any lingering sqlite connections to avoid Windows file-lock
        try:
            import gc
            gc.collect()
            if os.path.exists(self.server_db):
                try:
                    conn = sqlite3.connect(self.server_db)
                    conn.close()
                except Exception:
                    pass
            if os.path.exists(self.local_db):
                try:
                    conn = sqlite3.connect(self.local_db)
                    conn.close()
                except Exception:
                    pass
        except Exception:
            pass

        # Finally cleanup tempdir
        self.tmpdir.cleanup()

    def test_push_insert_and_delete(self):
        svc = self.SyncService()

        # Redirect server path checks to our server_db
        svc.get_server_db_path = lambda: self.server_db
        svc._check_server_online = lambda: True

        # Queue an insert change for ranks
        svc.add_sync_change('ranks', '1', {'id': 1, 'name': 'RankLocal', 'created_at': time.time(), 'updated_at': time.time()}, 'insert')

        # Push changes
        res = svc.sync_to_server()
        self.assertTrue(res.success)

        # Verify server has the record
        conn = sqlite3.connect(self.server_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM ranks WHERE id = 1")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'RankLocal')

        # Now queue a delete and push
        svc.add_sync_change('ranks', '1', {}, 'delete')
        res2 = svc.sync_to_server()
        self.assertTrue(res2.success)

        conn = sqlite3.connect(self.server_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM ranks WHERE id = 1")
        row = cur.fetchone()
        conn.close()
        self.assertIsNone(row)

    def test_pull_updates(self):
        svc = self.SyncService()
        svc.get_server_db_path = lambda: self.server_db
        svc._check_server_online = lambda: True

        # Insert a record on server with newer timestamp
        now = time.time()
        conn = sqlite3.connect(self.server_db)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO ranks (id, name, created_at, updated_at) VALUES (?,?,?,?)", (2, 'ServerRank', now, now))
        conn.commit()
        conn.close()

        # Ensure local has an older record
        conn = sqlite3.connect(self.local_db)
        cur = conn.cursor()
        cur.execute("INSERT OR REPLACE INTO ranks (id, name, created_at, updated_at) VALUES (?,?,?,?)", (2, 'OldLocal', now - 1000, now - 1000))
        conn.commit()
        conn.close()

        # Run pull
        res = svc.sync_from_server()
        self.assertTrue(res.success)

        # Verify local updated
        conn = sqlite3.connect(self.local_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM ranks WHERE id = 2")
        row = cur.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'ServerRank')


if __name__ == '__main__':
    unittest.main()
