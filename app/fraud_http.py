"""Isolated /fraude HTTP boundary, reusing the existing audited WSGI headers."""
from http.cookies import SimpleCookie, CookieError
from types import SimpleNamespace
import hmac
import json
import re
import secrets
import time
from .http import Application
from .fraud_assets import load_assets
from .fraud_store import FraudStore, database_path
from .game import Problem, rate_limit
from . import fraud_game as game


class FraudApplication(Application):
    def __init__(self, config, clock=time.time):
        # Config has already validated the public origin and secret. Its original
        # /recommander restriction and its database are deliberately left intact.
        self.config = SimpleNamespace(origin=config.origin, secret=config.secret,
                                      secure=config.secure, trust_proxy=config.trust_proxy,
                                      prefix="/fraude")
        self.clock = clock
        self.store = FraudStore(database_path(config))
        self.cookie_name = "__Secure-mia_fraud_sid" if config.secure else "mia_fraud_sid"
        self.assets, self.page, self.privacy = load_assets()

    def sign(self, value):
        return super().sign("fraud:" + value)

    def api(self, env, route, method):
        writes = ("claim", "start", "answer", "locate", "next")
        if route not in (*writes, "session", "health", "leaderboard"):
            raise Problem("not_found", 404)
        if method != ("POST" if route in writes else "GET"):
            raise Problem("method_not_allowed", 405)
        if route == "health":
            with self.store.transaction() as db:
                db.execute("SELECT 1 FROM games LIMIT 1")
            return {"ok": True}, []
        now = self.clock()
        identity = self.sign("ip:"+str(int(now//86400))+":"+self.peer(env))
        with self.store.transaction() as db:
            db.execute("DELETE FROM limits WHERE window<?", (int(now//60)-2,))
            # Several visitors may share the event's Wi-Fi/NAT.
            rate_limit(db, identity, "read", now, count=1800, period=60)
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
                    or not hmac.compare_digest(env.get("HTTP_X_CSRF_TOKEN", ""), self.sign("csrf:"+sid))):
                raise Problem("forbidden", 403)
            if env.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
                raise Problem("invalid_content_type", 415)
            length = env.get("CONTENT_LENGTH", "")
            if not length.isdecimal() or not 0 < int(length) <= 1024:
                raise Problem("invalid_body_size", 413)
            try:
                data = json.loads(env["wsgi.input"].read(int(length)))
            except (ValueError, UnicodeDecodeError):
                raise Problem("invalid_json")
            if not isinstance(data, dict):
                raise Problem("invalid_json")
        owner = self.sign("owner:"+sid)
        with self.store.transaction() as db:
            if route == "session":
                if not valid:
                    sid = secrets.token_urlsafe(32)
                cookie = f"{self.cookie_name}={sid}; Path=/fraude; HttpOnly; SameSite=Strict; Max-Age=86400"
                if self.config.secure:
                    cookie += "; Secure"
                return {"csrf": self.sign("csrf:"+sid), "participation": game.participation(db, self.sign("owner:"+sid), now)}, [("Set-Cookie", cookie)]
            if route == "leaderboard":
                return game.leaderboard(db, now), []
            rate_limit(db, identity, "write", now, count=600, period=60)
            rate_limit(db, owner, "owner_write", now, count=120, period=60)
            if route == "claim":
                rate_limit(db, identity, "claim", now, count=120, period=60)
        with self.store.transaction() as db:
            if route == "claim":
                if set(data) != {"tri"}:
                    raise Problem("invalid_trigram")
                response = game.claim(db, owner, data["tri"], now)
            elif route == "start":
                if data:
                    raise Problem("invalid_body")
                response = game.start(db, owner, now)
            else:
                response = {"answer": game.answer, "locate": game.locate, "next": game.next_case}[route](db, owner, data, now)
            return response, []
