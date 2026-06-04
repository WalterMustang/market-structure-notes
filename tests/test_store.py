"""Tests for the metadata store: schema, migration, derivation, durability.

Isolated by pointing the module-level NOTES_DIR / STORE_FILE at a temp dir, so
nothing touches the real notes/.
"""
import tempfile
import unittest
from pathlib import Path

from msn import store


class StoreTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        notes = Path(self._tmp.name)
        self._orig = (store.NOTES_DIR, store.STORE_FILE)
        store.NOTES_DIR = notes
        store.STORE_FILE = notes / ".msn.json"

    def tearDown(self):
        store.NOTES_DIR, store.STORE_FILE = self._orig
        self._tmp.cleanup()


class TestSchema(StoreTestCase):
    def test_default_meta_has_new_fields(self):
        meta = store._default_meta("x")
        self.assertIn("closed_at", meta)
        for k in ("direction", "stop", "target", "realized_r"):
            self.assertIn(k, meta["pnl"])

    def test_ensure_schema_idempotent_and_nondestructive(self):
        old = {"id": "old", "status": "closed", "pnl": {"entry": 100, "result": "win"}}
        changed_first = store._ensure_schema(old)
        snapshot = dict(old)
        snapshot_pnl = dict(old["pnl"])
        changed_second = store._ensure_schema(old)

        self.assertTrue(changed_first)
        self.assertFalse(changed_second)          # second run is a no-op
        self.assertEqual(old["pnl"]["entry"], 100)  # existing values preserved
        self.assertEqual(old["pnl"]["result"], "win")
        self.assertIn("realized_r", old["pnl"])
        self.assertIn("closed_at", old)
        self.assertEqual(old, snapshot | {k: old[k] for k in old})  # sanity: no key removed
        self.assertEqual(snapshot_pnl["entry"], 100)


class TestDeriveR(StoreTestCase):
    def test_long_realized_r(self):
        pnl = {"direction": "long", "entry": 100, "stop": 90, "exit": 120}
        store._derive_r(pnl)
        self.assertEqual(pnl["realized_r"], 2.0)  # (120-100)/10

    def test_short_realized_r(self):
        pnl = {"direction": "short", "entry": 100, "stop": 110, "exit": 80}
        store._derive_r(pnl)
        self.assertEqual(pnl["realized_r"], 2.0)  # (100-80)/10

    def test_planned_rr_from_target(self):
        pnl = {"direction": "long", "entry": 100, "stop": 90, "target": 130}
        store._derive_r(pnl)
        self.assertEqual(pnl["rr"], 3.0)

    def test_manual_value_wins(self):
        pnl = {"direction": "long", "entry": 100, "stop": 90, "exit": 120, "realized_r": 9.9}
        store._derive_r(pnl)
        self.assertEqual(pnl["realized_r"], 9.9)

    def test_zero_risk_safe(self):
        pnl = {"direction": "long", "entry": 100, "stop": 100, "exit": 120}
        store._derive_r(pnl)  # must not raise / divide by zero
        self.assertIsNone(pnl.get("realized_r"))


class TestStatusAndPnl(StoreTestCase):
    def test_set_status_closed_stamps_closed_at_once(self):
        meta = store.set_status("n1", "closed")
        first = meta["closed_at"]
        self.assertTrue(first)
        # Re-closing must not overwrite the original close time.
        again = store.set_status("n1", "closed")
        self.assertEqual(again["closed_at"], first)

    def test_update_pnl_auto_derives(self):
        meta = store.update_pnl("n1", direction="long", entry=100, stop=90, exit=110)
        self.assertEqual(meta["pnl"]["realized_r"], 1.0)


class TestDurability(StoreTestCase):
    def test_corrupt_store_is_backed_up_not_lost(self):
        store.STORE_FILE.write_text("{ this is not json")
        data = store.load_store()
        self.assertEqual(data["notes"], {})
        backups = list(store.NOTES_DIR.glob(".msn.json.corrupt-*"))
        self.assertEqual(len(backups), 1)
        self.assertIn("not json", backups[0].read_text())

    def test_migration_idempotent(self):
        (store.NOTES_DIR / "2026-01-01-BTC-4H.md").write_text("# Wyckoff\nSymbol: BTC\n")
        s1 = store.load_store()
        n1 = store._migrate_existing_notes(s1)
        s2 = store.load_store()
        n2 = store._migrate_existing_notes(s2)
        self.assertEqual(n1, 1)
        self.assertEqual(n2, 0)


if __name__ == "__main__":
    unittest.main()
