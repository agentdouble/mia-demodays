"""Small WSGI boundary: explicit static allowlist, CSRF and bounded requests."""
from http import HTTPStatus
from http.cookies import SimpleCookie, CookieError
from urllib.parse import urlsplit
import hashlib
import hmac
import ipaddress
import json
import logging
import re
import secrets
import sqlite3
import time

from .config import Config
from .assets import load_assets
from .store import Store
from . import game

CSP = ("default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
       "font-src 'self'; img-src 'self' data:; connect-src 'self'; "
       "base-uri 'none'; frame-ancestors 'none'; form-action 'self'; object-src 'none'")


class Application:
    def __init__(self, config: Config, clock=time.time):
        self.config, self.clock = config, clock
        self.store = Store(config.database)
        self.cookie_name = "__Secure-mia_sid" if config.secure else "mia_sid"
        self.assets, self.page, self.privacy = load_assets()

    def sign(self, value):
        return hmac.new(self.config.secret.encode(), value.encode(), hashlib.sha256).hexdigest()

    def peer(self, env):
        # Only Caddy on the private Docker network is permitted to supply this header.
        value = env.get("HTTP_X_FORWARDED_FOR", "") if self.config.trust_proxy else ""
        value = value.rsplit(",", 1)[-1].strip() or env.get("REMOTE_ADDR", "")
        try:
            return str(ipaddress.ip_address(value))
        except ValueError:
            return "unknown"

    def __call__(self, env, start_response):
        headers = [("Content-Security-Policy", CSP), ("X-Content-Type-Options", "nosniff"),
                   ("X-Frame-Options", "DENY"), ("Referrer-Policy", "no-referrer"),
                   ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
                   ("Cache-Control", "no-store")]
        if self.config.secure:
            headers.append(("Strict-Transport-Security", "max-age=31536000"))
        else:
            headers.append(("X-Robots-Tag", "noindex, nofollow"))
        status, body, mime = 200, b"", "application/json; charset=utf-8"
        try:
            host = env.get("HTTP_HOST", "")
            if host != urlsplit(self.config.origin).netloc:
                raise game.Problem("invalid_host", 421)
            method, path = env.get("REQUEST_METHOD", "GET"), env.get("PATH_INFO", "")
            prefix = self.config.prefix
            if path in ("/", prefix + "/") and method in ("GET", "HEAD"):
                status = 308
                headers.append(("Location", prefix))
            elif path == prefix and method in ("GET", "HEAD"):
                body, mime = self.page, "text/html; charset=utf-8"
            elif path == prefix + "/donnees" and method in ("GET", "HEAD"):
                body, mime = self.privacy, "text/html; charset=utf-8"
            elif path.removeprefix(prefix) in self.assets and path.startswith(prefix + "/") and method in ("GET", "HEAD"):
                body, mime = self.assets[path[len(prefix):]]
                headers = [(k, v) for k, v in headers if k != "Cache-Control"]
                headers.append(("Cache-Control", "public, max-age=300"))
            elif path.startswith(prefix + "/api/"):
                body, extra = self.api(env, path[len(prefix + "/api/"):], method)
                headers.extend(extra)
                body = json.dumps(body, ensure_ascii=False, separators=(",", ":")).encode()
            else:
                raise game.Problem("not_found", 404)
        except game.Problem as exc:
            status, body = exc.status, json.dumps({"error": exc.code}).encode()
            if status == 429:
                headers.append(("Retry-After", "60"))
        except sqlite3.Error:
            logging.exception("SQLite request failed")
            status, body = 503, b'{"error":"unavailable"}'
        except Exception:
            logging.exception("Unhandled request failure")
            status, body = 500, b'{"error":"unavailable"}'
        headers.extend([("Content-Type", mime), ("Content-Length", str(len(body)))])
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [b"" if env.get("REQUEST_METHOD") == "HEAD" else body]

    def api(self, env, route, method):
        if route not in ("session", "leaderboard", "health", "claim", "start", "answer"):
            raise game.Problem("not_found", 404)
        if method != ("POST" if route in ("claim", "start", "answer") else "GET"):
            raise game.Problem("method_not_allowed", 405)
        if route == "health":
            with self.store.transaction() as db:
                db.execute("SELECT 1 FROM games LIMIT 1")
            return {"ok": True}, []
        now = self.clock()
        identity = self.sign("ip:" + str(int(now // 86400)) + ":" + self.peer(env))
        # Commit quotas independently, including rejected/invalid requests.
        with self.store.transaction() as db:
            db.execute("DELETE FROM limits WHERE window<?", (int(now // 60)-2,))
            game.rate_limit(db, identity, "read", now, count=600, period=60)
        cookies = SimpleCookie()
        try:
            cookies.load(env.get("HTTP_COOKIE", ""))
        except CookieError:
            pass
        cookie = cookies.get(self.cookie_name)
        sid = cookie.value if cookie else ""
        valid = bool(re.fullmatch(r"[A-Za-z0-9_-]{43}", sid))
        if method == "POST":
            if (not valid or env.get("HTTP_ORIGIN") != self.config.origin
                    or env.get("HTTP_SEC_FETCH_SITE", "same-origin") != "same-origin"
                    or not hmac.compare_digest(env.get("HTTP_X_CSRF_TOKEN", ""), self.sign("csrf:" + sid))):
                raise game.Problem("forbidden", 403)
            if env.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
                raise game.Problem("invalid_content_type", 415)
            length = env.get("CONTENT_LENGTH", "")
            if not length.isdecimal() or not 0 < int(length) <= 1024:
                raise game.Problem("invalid_body_size", 413)
            try:
                data = json.loads(env["wsgi.input"].read(int(length)))
            except (ValueError, UnicodeDecodeError):
                raise game.Problem("invalid_json")
            if not isinstance(data, dict):
                raise game.Problem("invalid_json")
        owner = self.sign("owner:" + sid)
        # HMAC addresses are ephemeral rate-limit keys; raw IP addresses are never stored.
        with self.store.transaction() as db:
            if route == "session":
                if not valid:
                    sid = secrets.token_urlsafe(32)
                cookie = f"{self.cookie_name}={sid}; Path={self.config.prefix}; HttpOnly; SameSite=Strict; Max-Age=86400"
                if self.config.secure:
                    cookie += "; Secure"
                own_game = game.participation(db, self.sign("owner:" + sid), now)
                return {"csrf": self.sign("csrf:" + sid), "participation": own_game}, [("Set-Cookie", cookie)]
            if route == "leaderboard":
                return game.leaderboard(db, now), []
            game.rate_limit(db, identity, "write", now, count=180, period=60)
            if route == "claim":
                game.rate_limit(db, identity, "claim", now, count=60, period=60)
        with self.store.transaction() as db:
            if route == "claim":
                if set(data) != {"tri"}:
                    raise game.Problem("invalid_trigram")
                return game.claim(db, owner, data["tri"], now), []
            if route == "start":
                if data:
                    raise game.Problem("invalid_body")
                return game.start(db, owner, now), []
            return game.answer(db, owner, data, now), []


def create_app(config=None, **kwargs):
    return Application(config or Config.from_env(), **kwargs)
