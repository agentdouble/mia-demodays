from contextlib import closing
from pathlib import Path
from tempfile import TemporaryDirectory
import sqlite3
import unittest

from app.config import Config
from app.portal import create_app
from test_public_game import Browser


class AgentBrowser(Browser):
    def api(self, route, data=None, **kw):
        return self.request("/mia-agent/api/" + route, data, **kw)


class MiaAgentTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1793894400.0
        self.db = Path(self.temp.name)/"mia.sqlite3"
        self.app = create_app(Config(self.db, "s"*48, origin="http://localhost:8080"), clock=lambda: self.now)
        self.browser = AgentBrowser(self.app)

    def rows(self):
        with closing(sqlite3.connect(self.db.with_name("agent.sqlite3"))) as db:
            return db.execute("SELECT tri FROM interests ORDER BY created").fetchall()

    def test_page_assets_and_privacy_are_served_with_versions(self):
        page = self.browser.request("/mia-agent")
        self.assertEqual(page["status"], 200)
        self.assertIn(b"MIA Agent", page["body"])
        self.assertIn(b"/mia-agent/agent.js?v=", page["body"])
        self.assertNotIn(b"<script>", page["body"])  # CSP: no inline script
        self.assertEqual(self.browser.request("/mia-agent/agent.css")["status"], 200)
        self.assertIn(b"fonts/doto-900.woff2?v=", self.browser.request("/mia-agent/agent.css")["body"])
        self.assertEqual(self.browser.request("/mia-agent/fonts/doto-900.woff2")["status"], 200)
        self.assertEqual(self.browser.request("/mia-agent/donnees")["status"], 200)
        self.assertEqual(self.browser.request("/mia-agent/index.html")["status"], 404)
        self.assertEqual(self.browser.request("/mia-agent/api/health")["status"], 200)

    def test_interest_is_stored_once_per_browser_and_can_be_corrected(self):
        first = self.browser.api("session")
        self.assertIsNone(first["json"]["tri"])
        self.browser.csrf = first["json"]["csrf"]
        self.assertEqual(self.browser.api("interest", {"tri": "ABC"})["json"], {"tri": "ABC"})
        self.assertEqual(self.browser.api("session")["json"]["tri"], "ABC")
        self.assertEqual(self.browser.api("interest", {"tri": "XYZ"})["status"], 200)
        self.assertEqual(self.rows(), [("XYZ",)])
        other = AgentBrowser(self.app, peer="192.0.2.11")
        other.csrf = other.api("session")["json"]["csrf"]
        self.assertIsNone(other.api("session")["json"]["tri"])
        other.api("interest", {"tri": "XYZ"})
        self.assertEqual(self.rows(), [("XYZ",), ("XYZ",)])

    def test_strict_input_csrf_and_isolation_from_games(self):
        self.browser.csrf = self.browser.api("session")["json"]["csrf"]
        for tri in ["ab", "abc", "ABCD", "A1C", "<x>", "ÉAB", 3, None]:
            self.assertEqual(self.browser.api("interest", {"tri": tri})["status"], 400)
        self.assertEqual(self.browser.api("interest", {"tri": "ABC", "x": 1})["status"], 400)
        self.assertEqual(self.browser.api("interest", {"tri": "ABC"}, headers={"HTTP_ORIGIN": "https://evil.example"})["status"], 403)
        self.assertEqual(self.browser.api("interest", {"tri": "ABC"}, headers={"HTTP_X_CSRF_TOKEN": ""})["status"], 403)
        self.assertEqual(self.browser.api("interest")["status"], 405)
        self.assertEqual(self.rows(), [])
        # The recommander game keeps its own database and routes.
        self.assertEqual(self.browser.request("/recommander")["status"], 200)
        with closing(sqlite3.connect(self.db)) as db:
            tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertNotIn("interests", tables)

    def test_owner_rate_limit(self):
        self.browser.csrf = self.browser.api("session")["json"]["csrf"]
        statuses = [self.browser.api("interest", {"tri": "ABC"})["status"] for _ in range(12)]
        self.assertEqual(statuses[:10], [200]*10)
        self.assertEqual(statuses[-1], 429)


if __name__ == "__main__":
    unittest.main()
