"""Security regression tests for the web viewer and untrusted-input paths.

The pure-function checks run with the stdlib only; the HTTP-level tests need
the `[web]` extra plus httpx (for FastAPI's TestClient) and are skipped without.
"""

import io
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from msn import cli, store  # noqa: E402

try:
    from fastapi.testclient import TestClient
    HAVE_WEB = True
except Exception:  # fastapi or httpx missing
    HAVE_WEB = False

NOTE_ID = "2026-01-01-BTC-4H"
XSS = '"><script>alert(1)</script>'


class _IsolatedNotes(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.notes = self.tmp / "notes"
        self.notes.mkdir()
        self._saved = (cli.NOTES_DIR, cli.ROOT, cli.TEMPLATES_DIR, store.NOTES_DIR, store.STORE_FILE)
        shutil.copytree(cli.TEMPLATES_DIR, self.tmp / "templates")
        cli.TEMPLATES_DIR = self.tmp / "templates"
        cli.NOTES_DIR = self.notes
        cli.ROOT = self.tmp
        store.NOTES_DIR = self.notes
        store.STORE_FILE = self.notes / ".msn.json"
        (self.notes / f"{NOTE_ID}.md").write_text("# Note\n")

    def tearDown(self):
        cli.NOTES_DIR, cli.ROOT, cli.TEMPLATES_DIR, store.NOTES_DIR, store.STORE_FILE = self._saved
        shutil.rmtree(self.tmp)


class TestInputValidation(_IsolatedNotes):
    def test_template_name_cannot_traverse(self):
        (self.tmp / "secret.md").write_text("SECRET")
        with self.assertRaises(FileNotFoundError):
            cli.load_template("../secret")

    def test_create_note_rejects_unsafe_symbol_and_timeframe(self):
        for sym, tf in (("../x", "4H"), ("BTC", "4H/../../x"), ("<b>", "4H"), ("", "4H")):
            with self.assertRaises(ValueError):
                cli.create_note("minimal", sym, tf)
        with self.assertRaises(ValueError):
            cli.create_note("minimal", "BTC", "4H", date_str="../../x")
        self.assertEqual(sorted(p.name for p in self.notes.glob("*.md")), [f"{NOTE_ID}.md"])

    def test_create_note_still_accepts_normal_input(self):
        with redirect_stdout(io.StringIO()):
            path = cli.create_note("minimal", "btc", "15m", date_str="2026-02-02")
        self.assertEqual(path.name, "2026-02-02-BTC-15M.md")

    def test_import_skips_unsafe_ids(self):
        src = self.tmp / "import"
        src.mkdir()
        (src / "evil.md").write_text("---\nid: ../../etc/x\nstatus: idea\n---\n")
        (src / "xss.md").write_text("---\nid: <img src=x onerror=alert(1)>\nstatus: idea\n---\n")
        (src / "ok.md").write_text(f"---\nid: {NOTE_ID}\nstatus: paper\nupdated_at: 2999-01-01\n---\n")
        with redirect_stdout(io.StringIO()):
            cli.import_notes(str(src))
        self.assertEqual(list(store.load_store()["notes"]), [NOTE_ID])


class TestRequestGuard(unittest.TestCase):
    hosts = cli.LOOPBACK_HOSTS

    def allowed(self, method, path, **headers):
        headers = {k.replace("_", "-"): v for k, v in headers.items()}
        headers.setdefault("host", "localhost:8765")
        return cli._request_allowed(method, path, headers, self.hosts)

    def test_same_origin_requests_pass(self):
        self.assertTrue(self.allowed("GET", "/"))
        self.assertTrue(self.allowed("POST", "/save/a.md", origin="http://localhost:8765",
                                     sec_fetch_site="same-origin"))
        self.assertTrue(self.allowed("POST", "/save/a.md"))  # non-browser client (curl)
        self.assertTrue(self.allowed("GET", "/", host="127.0.0.1:8765"))
        self.assertTrue(self.allowed("GET", "/", host="[::1]:8765"))

    def test_dns_rebinding_host_rejected(self):
        self.assertFalse(self.allowed("GET", "/export/json", host="attacker.example:8765"))

    def test_cross_site_writes_rejected(self):
        self.assertFalse(self.allowed("POST", "/save/a.md", origin="https://evil.example"))
        self.assertFalse(self.allowed("POST", "/save/a.md", origin="null"))
        self.assertFalse(self.allowed("POST", "/create", sec_fetch_site="cross-site"))
        self.assertFalse(self.allowed("GET", "/delete/a.md", sec_fetch_site="cross-site"))
        # Cross-site *reads* of plain pages (e.g. a link click) stay allowed.
        self.assertTrue(self.allowed("GET", "/", sec_fetch_site="cross-site"))

    def test_host_check_can_be_disabled(self):
        self.assertTrue(cli._request_allowed("GET", "/", {"host": "proxy.example"}, None))
        self.assertFalse(cli._request_allowed("POST", "/create", {"host": "proxy.example",
                                              "origin": "https://evil.example"}, None))


@unittest.skipUnless(HAVE_WEB, "web extra / httpx not installed")
class TestWebRoutes(_IsolatedNotes):
    def setUp(self):
        super().setUp()
        self.client = TestClient(cli.create_app(), base_url="http://localhost")

    def test_index_renders(self):
        # Regression: index used to KeyError on stats['win_rate'] (HTTP 500).
        r = self.client.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertIn(NOTE_ID, r.text)
        self.assertEqual(r.headers["x-frame-options"], "DENY")

    def test_reflected_query_params_escaped(self):
        r = self.client.get("/", params={"q": XSS, "symbol": XSS, "status": XSS})
        self.assertEqual(r.status_code, 200)
        self.assertNotIn("<script>alert(1)", r.text)

    def test_note_content_cannot_break_out_of_textarea(self):
        (self.notes / f"{NOTE_ID}.md").write_text("</textarea><script>alert(1)</script>")
        r = self.client.get(f"/edit/{NOTE_ID}.md")
        self.assertNotIn("</textarea><script>", r.text)
        self.assertIn("DOMPurify.sanitize", r.text)

    def test_status_and_pnl_require_existing_note(self):
        bad = "<img src=x onerror=alert(1)>"
        r1 = self.client.post(f"/set-status/{bad}", data={"status": "idea"}, follow_redirects=False)
        r2 = self.client.post("/set-pnl/missing", data={"entry": "1"}, follow_redirects=False)
        self.assertEqual((r1.status_code, r2.status_code), (404, 404))
        self.assertNotIn(bad, store.load_store()["notes"])

    def test_pnl_rejects_unexpected_values(self):
        with redirect_stdout(io.StringIO()):
            self.client.post(f"/set-pnl/{NOTE_ID}",
                             data={"result": "<script>", "direction": "long"},
                             follow_redirects=False)
            self.client.post(f"/set-pnl/{NOTE_ID}", data={"entry": "nan"}, follow_redirects=False)
        pnl = store.get_note_meta(NOTE_ID)["pnl"]
        self.assertIsNone(pnl["result"])
        self.assertIsNone(pnl["entry"])
        with redirect_stdout(io.StringIO()):
            self.client.post(f"/set-pnl/{NOTE_ID}", data={"result": "win", "entry": "100"},
                             follow_redirects=False)
        pnl = store.get_note_meta(NOTE_ID)["pnl"]
        self.assertEqual((pnl["result"], pnl["entry"]), ("win", 100.0))

    def test_create_rejects_traversal(self):
        (self.tmp / "secret.md").write_text("SECRET")
        r = self.client.post("/create", data={"template": "../secret", "symbol": "X", "timeframe": "Y"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/create", data={"template": "minimal", "symbol": "a/../b", "timeframe": "4H"},
                             follow_redirects=False)
        self.assertEqual(r.status_code, 400)

    def test_cross_site_save_and_delete_blocked(self):
        path = self.notes / f"{NOTE_ID}.md"
        r = self.client.post(f"/save/{NOTE_ID}.md", data={"content": "pwned"},
                             headers={"Origin": "https://evil.example"}, follow_redirects=False)
        self.assertEqual(r.status_code, 403)
        r = self.client.get(f"/delete/{NOTE_ID}.md", headers={"Sec-Fetch-Site": "cross-site"},
                            follow_redirects=False)
        self.assertEqual(r.status_code, 403)
        self.assertEqual(path.read_text(), "# Note\n")
        # Same-origin save still works.
        r = self.client.post(f"/save/{NOTE_ID}.md", data={"content": "ok"},
                             headers={"Origin": "http://localhost"}, follow_redirects=False)
        self.assertEqual(r.status_code, 303)
        self.assertEqual(path.read_text(), "ok")

    def test_foreign_host_rejected(self):
        r = self.client.get("/export/json", headers={"Host": "attacker.example"})
        self.assertEqual(r.status_code, 403)


if __name__ == "__main__":
    unittest.main()
