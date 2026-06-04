"""Tests for frontmatter export/parse round-trip and `msn import`."""
import tempfile
import unittest
from pathlib import Path

from msn import store, cli


class IoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        notes = Path(self._tmp.name)
        self._orig = (store.NOTES_DIR, store.STORE_FILE)
        store.NOTES_DIR = notes
        store.STORE_FILE = notes / ".msn.json"

    def tearDown(self):
        store.NOTES_DIR, store.STORE_FILE = self._orig
        self._tmp.cleanup()

    def test_frontmatter_roundtrip(self):
        meta = store._default_meta("2026-01-01-BTC-4H", symbol="BTC", timeframe="4H", template="wyckoff")
        meta["status"] = "closed"
        meta["pnl"].update({"direction": "long", "entry": 100, "stop": 90,
                            "target": 130, "exit": 120, "rr": 3.0, "realized_r": 2.0, "result": "win"})
        meta["tags"] = ["liquidity", "spring"]
        meta["closed_at"] = "2026-01-02T00:00:00Z"

        fm = cli._build_yaml_frontmatter(meta)
        parsed = cli._parse_frontmatter(fm + "\n# note body\n")

        self.assertEqual(parsed["status"], "closed")
        self.assertEqual(parsed["symbol"], "BTC")
        self.assertEqual(parsed["pnl"]["direction"], "long")
        self.assertEqual(parsed["pnl"]["entry"], 100)
        self.assertEqual(parsed["pnl"]["realized_r"], 2.0)
        self.assertEqual(parsed["pnl"]["result"], "win")
        self.assertEqual(parsed["tags"], ["liquidity", "spring"])
        self.assertEqual(parsed["closed_at"], "2026-01-02T00:00:00Z")

    def test_import_rebuilds_store(self):
        meta = store._default_meta("2026-01-01-ETH-1D", symbol="ETH", timeframe="1D", template="smc")
        meta["status"] = "closed"
        meta["pnl"].update({"direction": "short", "entry": 200, "stop": 210, "exit": 180, "result": "win"})
        meta["updated_at"] = "2026-02-01T00:00:00Z"

        export_dir = Path(self._tmp.name) / "export"
        export_dir.mkdir()
        (export_dir / f"{meta['id']}.md").write_text(cli._build_yaml_frontmatter(meta) + "\n# body\n")

        # Store starts empty (simulating a lost .msn.json).
        cli.import_notes(str(export_dir))

        s = store.load_store()
        self.assertIn(meta["id"], s["notes"])
        rec = s["notes"][meta["id"]]
        self.assertEqual(rec["status"], "closed")
        self.assertEqual(rec["pnl"]["direction"], "short")
        self.assertEqual(rec["pnl"]["realized_r"], 2.0)  # derived on import

    def test_import_skips_when_store_is_newer(self):
        nid = "2026-01-01-BTC-4H"
        store.save_store({"version": 1, "notes": {
            nid: store._default_meta(nid) | {"updated_at": "2030-01-01T00:00:00Z", "status": "paper"}
        }})

        meta = store._default_meta(nid)
        meta["status"] = "closed"
        meta["updated_at"] = "2026-01-01T00:00:00Z"  # older than store
        export_dir = Path(self._tmp.name) / "export"
        export_dir.mkdir()
        (export_dir / f"{nid}.md").write_text(cli._build_yaml_frontmatter(meta) + "\n# body\n")

        cli.import_notes(str(export_dir))
        rec = store.load_store()["notes"][nid]
        self.assertEqual(rec["status"], "paper")  # newer store record kept


if __name__ == "__main__":
    unittest.main()
