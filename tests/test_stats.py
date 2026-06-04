"""Tests for get_stats analytics: win rate, expectancy, and streak ordering."""
import tempfile
import unittest
from pathlib import Path

from msn import store


def _closed(note_id, result, realized_r, closed_at, updated_at, template="wyckoff", symbol="BTC"):
    meta = store._default_meta(note_id, symbol=symbol, template=template)
    meta["status"] = "closed"
    meta["pnl"]["result"] = result
    meta["pnl"]["realized_r"] = realized_r
    meta["closed_at"] = closed_at
    meta["updated_at"] = updated_at
    return meta


class StatsTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        notes = Path(self._tmp.name)
        self._orig = (store.NOTES_DIR, store.STORE_FILE)
        store.NOTES_DIR = notes
        store.STORE_FILE = notes / ".msn.json"

    def tearDown(self):
        store.NOTES_DIR, store.STORE_FILE = self._orig
        self._tmp.cleanup()

    def _seed(self, metas):
        store.save_store({"version": 1, "notes": {m["id"]: m for m in metas}})

    def test_expectancy_and_win_rate(self):
        self._seed([
            _closed("a", "win", 2.0, "2026-01-01", "2026-01-01"),
            _closed("b", "loss", -1.0, "2026-01-02", "2026-01-02"),
            _closed("c", "win", 2.0, "2026-01-03", "2026-01-03"),
        ])
        perf = store.get_stats()["performance"]
        self.assertEqual(perf["wins"], 2)
        self.assertEqual(perf["losses"], 1)
        self.assertEqual(perf["win_rate"], 66.7)
        self.assertEqual(perf["expectancy"], 1.0)   # (2 - 1 + 2)/3
        self.assertEqual(perf["avg_win_r"], 2.0)
        self.assertEqual(perf["avg_loss_r"], -1.0)

    def test_streaks_order_by_closed_at_not_updated_at(self):
        # 'a' was edited long after it closed; ordering by updated_at would flip it.
        self._seed([
            _closed("a", "win", 2.0, closed_at="2026-01-01", updated_at="2026-12-01"),
            _closed("b", "loss", -1.0, closed_at="2026-01-02", updated_at="2026-01-02"),
        ])
        streaks = store.get_stats()["review"]["streaks"]
        # Correct chronology (by close): win then loss -> current streak is a loss.
        self.assertEqual(streaks["current"], -1)
        self.assertEqual(streaks["longest_win"], 1)
        self.assertEqual(streaks["longest_loss"], 1)

    def test_best_templates_ranked_by_expectancy(self):
        self._seed([
            _closed("a", "win", 1.0, "2026-01-01", "2026-01-01", template="wyckoff"),
            _closed("b", "win", 1.0, "2026-01-02", "2026-01-02", template="wyckoff"),
            _closed("c", "win", 5.0, "2026-01-03", "2026-01-03", template="smc"),
            _closed("d", "win", 5.0, "2026-01-04", "2026-01-04", template="smc"),
        ])
        best = store.get_stats()["review"]["best_templates"]
        self.assertEqual(best[0]["template"], "smc")
        self.assertEqual(best[0]["expectancy"], 5.0)

    def test_no_realized_r_means_expectancy_none(self):
        meta = _closed("a", "win", None, "2026-01-01", "2026-01-01")
        meta["pnl"]["realized_r"] = None
        self._seed([meta])
        perf = store.get_stats()["performance"]
        self.assertIsNone(perf["expectancy"])
        self.assertEqual(perf["win_rate"], 100.0)


if __name__ == "__main__":
    unittest.main()
