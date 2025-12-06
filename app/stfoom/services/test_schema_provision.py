import os
import tempfile
import sqlite3
import unittest

import config.settings as settings


class TestSchemaProvision(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.test_db = os.path.join(self.tmpdir.name, 'stfoom.db')
        self._orig_get_db_path = settings.get_db_path
        settings.get_db_path = lambda: self.test_db

    def tearDown(self):
        settings.get_db_path = self._orig_get_db_path
        self.tmpdir.cleanup()

    def test_ensure_schema_ready_creates_tables_and_timestamps(self):
        from app.stfoom.services.schema_provision import ensure_schema_ready
        from app.stfoom.services.sync_service import SyncService

        svc = SyncService()
        # Before running provision, db file may not exist
        if os.path.exists(self.test_db):
            os.remove(self.test_db)

        ensure_schema_ready()

        # DB should exist now
        self.assertTrue(os.path.exists(self.test_db))

        # Check a few tables from table_pk_map exist and have created_at/updated_at
        conn = sqlite3.connect(self.test_db)
        cur = conn.cursor()
        for table in list(svc.table_pk_map.keys())[:5]:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
            self.assertIsNotNone(cur.fetchone(), f"Table {table} should exist")
            cur.execute(f"PRAGMA table_info({table})")
            cols = {r[1] for r in cur.fetchall()}
            self.assertIn('created_at', cols)
            self.assertIn('updated_at', cols)
        conn.close()


if __name__ == '__main__':
    unittest.main()
