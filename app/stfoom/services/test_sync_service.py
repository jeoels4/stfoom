import os
import tempfile
import sqlite3
import json
import time
import unittest

import config.settings as settings


class TestSyncService(unittest.TestCase):
    def setUp(self):
        # Create temporary directory and DB paths
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.tmpdir.name, 'stfoom.db')
        # Monkeypatch get_db_path to point to our temp DB
        self._orig_get_db_path = settings.get_db_path
        settings.get_db_path = lambda: self.test_db

        # Ensure fresh files
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

    def tearDown(self):
        # Restore
        settings.get_db_path = self._orig_get_db_path
        self.tmpdir.cleanup()

    def test_add_and_mark_change(self):
        # Import here so SyncService picks up monkeypatched get_db_path
        # reload module so it picks up the monkeypatched get_db_path
        import importlib
        import app.stfoom.services.sync_service as ss
        importlib.reload(ss)
        SyncService = ss.SyncService

        svc = SyncService()
        # Ensure sync DB exists
        self.assertTrue(os.path.exists(svc.sync_db_path))

        # Add a change
        svc.add_sync_change('test_table', '1', {'a': 1}, 'insert')
        pending = svc.get_pending_changes()
        self.assertTrue(len(pending) >= 1)

        # Mark the first change as synced
        change_id = pending[0]['id']
        svc.mark_change_synced(change_id)
        pending2 = svc.get_pending_changes()
        # It should no longer be in pending list
        self.assertFalse(any(ch['id'] == change_id for ch in pending2))

    def test_apply_change_insert_update_delete(self):
        # reload module so it picks up the monkeypatched get_db_path
        import importlib
        import app.stfoom.services.sync_service as ss
        importlib.reload(ss)
        SyncService = ss.SyncService

        svc = SyncService()

        # Create a separate DB to act as server DB
        server_db = os.path.join(self.tmpdir.name, 'server.db')
        conn = sqlite3.connect(server_db)
        cur = conn.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS test_apply (id INTEGER PRIMARY KEY, name TEXT, created_at REAL DEFAULT 0, updated_at REAL DEFAULT 0)")
        conn.commit()
        conn.close()

        # Insert
        ok = svc.apply_change_to_database('test_apply', '1', {'id': 1, 'name': 'Alice', 'created_at': time.time()}, 'insert', server_db)
        self.assertTrue(ok)
        conn = sqlite3.connect(server_db)
        cur = conn.cursor()
        cur.execute("SELECT name FROM test_apply WHERE id = 1")
        row = cur.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'Alice')

        # Update
        ok = svc.apply_change_to_database('test_apply', '1', {'name': 'Bob'}, 'update', server_db)
        self.assertTrue(ok)
        cur.execute("SELECT name FROM test_apply WHERE id = 1")
        row = cur.fetchone()
        self.assertEqual(row[0], 'Bob')

        # Delete
        ok = svc.apply_change_to_database('test_apply', '1', {}, 'delete', server_db)
        self.assertTrue(ok)
        cur.execute("SELECT name FROM test_apply WHERE id = 1")
        row = cur.fetchone()
        self.assertIsNone(row)
        conn.close()


if __name__ == '__main__':
    unittest.main()
