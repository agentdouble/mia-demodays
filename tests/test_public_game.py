from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from io import BytesIO
from pathlib import Path
from tempfile import TemporaryDirectory
import json
import sqlite3
import unittest

from app.config import Config
from app.http import create_app
from app.game import CLIENTS


class Browser:
    def __init__(self, app, peer="192.0.2.10"):
        self.app, self.cookie, self.csrf, self.peer = app, "", "", peer

    def request(self, path, data=None, *, headers=None, method=None, raw=None):
        body = raw if raw is not None else json.dumps(data).encode() if data is not None else b""
        env = {"REQUEST_METHOD": method or ("POST" if data is not None or raw else "GET"),
               "PATH_INFO": path, "HTTP_HOST": "localhost:8080", "REMOTE_ADDR": self.peer,
               "HTTP_ORIGIN": "http://localhost:8080", "HTTP_COOKIE": self.cookie,
               "HTTP_X_CSRF_TOKEN": self.csrf, "CONTENT_TYPE": "application/json",
               "CONTENT_LENGTH": str(len(body)), "wsgi.input": BytesIO(body)}
        env.update(headers or {})
        response = {}
        def start(status, values):
            response["status"], response["headers"] = int(status.split()[0]), dict(values)
        response["body"] = b"".join(self.app(env, start))
        if "Set-Cookie" in response["headers"]:
            self.cookie = response["headers"]["Set-Cookie"].split(";", 1)[0]
        if response["headers"]["Content-Type"].startswith("application/json"):
            response["json"] = json.loads(response["body"]) if response["body"] else None
        return response

    def api(self, route, data=None, **kw):
        return self.request("/recommander/api/" + route, data, **kw)

    def session(self):
        response = self.api("session")
        self.csrf = response["json"]["csrf"]
        return response


class PublicGameTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.now = 1793894400.0
        self.app = create_app(Config(Path(self.temp.name)/"game.db", "s"*48,
                                     origin="http://localhost:8080"), clock=lambda: self.now)
        self.browser = Browser(self.app)
        self.browser.session()

    def test_csrf_origin_cookie_and_json_required(self):
        for headers in ({"HTTP_ORIGIN": "https://evil.example"},
                        {"HTTP_X_CSRF_TOKEN": ""}, {"HTTP_COOKIE": ""},
                        {"HTTP_SEC_FETCH_SITE": "cross-site"}):
            self.assertEqual(self.browser.api("claim", {"tri": "ABC"}, headers=headers)["status"], 403)
        self.assertEqual(self.browser.api("claim", {"tri": "ABC"}, headers={"CONTENT_TYPE": "text/plain"})["status"], 415)
        self.assertEqual(self.browser.api("claim", raw=b'x'*1025)["status"], 413)
        self.assertEqual(self.browser.api("claim", raw=b'not-json')["status"], 400)

    def test_invalid_input_and_no_arbitrary_score_endpoint(self):
        for tri in ["<x>", "A'B", "ABCD", "../", "éAB", 3, None]:
            self.assertEqual(self.browser.api("claim", {"tri": tri})["status"], 400)
        self.assertEqual(self.browser.api("result", {"score": 6, "timeMs": 1})["status"], 404)
        self.assertEqual(self.browser.api("claim", {"tri": "ABC", "score": 6})["status"], 400)

    def test_round_timing_score_and_retry_are_server_authoritative(self):
        response = self.browser.api("claim", {"tri": "ABC"})
        self.assertEqual(response["status"], 200)
        clients = response["json"]["clients"]
        self.assertEqual(len({c["name"] for c in clients}), 6)
        self.assertTrue(all("yes" not in c and "why" not in c for c in clients))
        self.assertEqual(self.browser.api("answer", {"index": 0, "yes": True})["status"], 409)
        self.browser.api("start", {})
        self.assertEqual(self.browser.api("answer", {"index": 0, "yes": True})["status"], 429)
        self.assertEqual(self.browser.api("answer", {"index": 1, "yes": True})["status"], 409)
        self.assertEqual(self.browser.api("answer", {"index": 0, "yes": True, "score": 6})["status"], 400)
        self.assertEqual(self.browser.api("answer", {"index": True, "yes": True})["status"], 400)
        answers = {c["name"]: c["yes"] for c in CLIENTS}
        for i, client in enumerate(clients):
            self.now += 1
            response = self.browser.api("answer", {"index": i, "yes": answers[client["name"]]})
            self.assertEqual(response["status"], 200)
            self.assertTrue(response["json"]["correct"])
        self.assertEqual(response["json"]["result"], {"score": 6, "timeMs": 6000, "grade": "S", "total": 6})
        self.now += 10
        retry = self.browser.api("answer", {"index": 5, "yes": answers[clients[5]["name"]]})
        self.assertEqual(retry["json"], response["json"])
        self.assertEqual(self.browser.api("answer", {"index": 5, "yes": not answers[clients[5]["name"]]})["status"], 409)
        board = self.browser.api("leaderboard")["json"]["rows"]
        self.assertEqual(board, [{"tri": "ABC", "score": 6, "timeMs": 6000, "grade": "S", "total": 6}])
        self.assertEqual(self.browser.api("claim", {"tri": "DEF"})["status"], 409)

    def test_concurrent_claim_is_unique_and_cannot_steal_round(self):
        other = Browser(self.app, "192.0.2.11")
        other.session()
        with ThreadPoolExecutor(2) as pool:
            results = list(pool.map(lambda b: b.api("claim", {"tri": "ABC"})["status"], [self.browser, other]))
        self.assertEqual(sorted(results), [200, 409])
        loser = self.browser if results[0] == 409 else other
        self.assertEqual(loser.api("answer", {"index": 0, "yes": True})["status"], 404)

    def test_session_reports_only_its_own_round_before_registration(self):
        self.assertIsNone(self.browser.session()["json"]["participation"])
        self.browser.api("claim", {"tri": "ABC"})
        self.assertEqual(self.browser.session()["json"]["participation"], {"tri": "ABC", "status": "reserved"})
        other = Browser(self.app)
        self.assertIsNone(other.session()["json"]["participation"])
        self.browser.api("start", {})
        self.assertEqual(self.browser.session()["json"]["participation"], {"tri": "ABC", "status": "playing"})
        for i in range(6):
            self.now += 1
            self.browser.api("answer", {"index": i, "yes": False})
        self.assertEqual(self.browser.session()["json"]["participation"], {"tri": "ABC", "status": "done"})
        self.assertEqual(self.browser.api("claim", {"tri": "DEF"})["status"], 409)
        self.assertIsNone(other.session()["json"]["participation"])
        self.now += 31 * 86400
        self.assertIsNone(self.browser.session()["json"]["participation"])

    def test_secrets_traversal_admin_and_database_are_not_served(self):
        for path in ["/.env", "/app/clients.json", "/data/mia.sqlite3", "/recommander/../app/clients.json",
                     "/recommander/data/game.db", "/recommander/api/admin", "/recommander/index.html"]:
            self.assertEqual(self.browser.request(path)["status"], 404, path)
        response = self.browser.request("/recommander")
        self.assertEqual(response["status"], 200)
        self.assertEqual(response["headers"]["X-Robots-Tag"], "noindex, nofollow")
        self.assertIn("script-src 'self'", response["headers"]["Content-Security-Policy"])
        self.assertNotIn(b"claude.use", response["body"])
        self.assertEqual(self.browser.request("/recommander", headers={"HTTP_HOST": "evil.example"})["status"], 421)

    def test_bad_claims_are_rate_limited_and_forwarded_headers_are_untrusted(self):
        for i in range(60):
            self.assertEqual(self.browser.api("claim", {"tri": "!"}, headers={"HTTP_X_FORWARDED_FOR": f"198.51.100.{i}"})["status"], 400)
        self.assertEqual(self.browser.api("claim", {"tri": "ABC"})["status"], 429)
        with closing(self.app.store.connect()) as db:
            for row in db.execute("SELECT identity FROM limits"):
                self.assertEqual(len(row[0]), 64)

    def test_secure_cookie_and_http_public_config_rejected(self):
        config = Config(Path(self.temp.name)/"secure.db", "s"*48)
        secure = Browser(create_app(config))
        response = secure.request("/recommander/api/session", headers={"HTTP_HOST": "mia-foyer.com"})
        cookie = response["headers"]["Set-Cookie"]
        self.assertIn("Secure", cookie)
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertIn("Strict-Transport-Security", response["headers"])
        with self.assertRaises(ValueError):
            Config(Path("unused"), "s"*48, origin="http://example.com")
        with self.assertRaises(ValueError):
            Config(Path("unused"), "short")

    def test_backup_restore_preserves_games_and_expiry(self):
        self.browser.api("claim", {"tri": "ABC"})
        backup = Path(self.temp.name)/"backup.sqlite3"
        self.app.store.backup(backup)
        with closing(sqlite3.connect(backup)) as db:
            self.assertEqual(db.execute("PRAGMA integrity_check").fetchone()[0], "ok")
            self.assertEqual(db.execute("SELECT tri FROM games").fetchone()[0], "ABC")
        with self.assertRaises(ValueError):
            self.app.store.backup(backup)
        self.now += 1801
        self.assertEqual(self.browser.api("claim", {"tri": "ABC"})["status"], 200)


if __name__ == "__main__":
    unittest.main()
