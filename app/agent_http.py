"""Isolated /mia-agent page: the MIA Agent cover and an "interested" trigram form.

It reuses the audited WSGI boundary of the games (headers, host check, CSRF,
bounded JSON) with its own cookie, signing namespace and SQLite database.
"""
from contextlib import closing
from http.cookies import SimpleCookie, CookieError
from pathlib import Path
from types import SimpleNamespace
import hashlib
import hmac
import json
import re
import secrets
import time

from .game import Problem, rate_limit
from .http import Application
from .store import Store

PREFIX = "/mia-agent"
STATIC = Path(__file__).with_name("agent")
TYPES = {"agent.css": "text/css", "agent.js": "text/javascript",
         "fonts/doto-900.woff2": "font/woff2", "fonts/ibm-plex-sans.woff2": "font/woff2",
         "fonts/ibm-plex-mono-500.woff2": "font/woff2"}


def database_path(config):
    path = config.database.with_name("agent.sqlite3")
    if path.resolve() == config.database.resolve():
        raise ValueError("MIA Agent and recommander databases must be distinct")
    return path


class AgentStore(Store):
    """One interest per browser; a later submission replaces its trigram."""
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS interests (
                    owner TEXT PRIMARY KEY,
                    tri TEXT NOT NULL CHECK(length(tri)=3),
                    created REAL NOT NULL,
                    updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS limits (
                    identity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    window INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY(identity, category)
                );
            """)


def load_assets():
    data = {name: (STATIC/name).read_bytes() for name in TYPES}
    version = {name: hashlib.sha256(body).hexdigest()[:16] for name, body in data.items()}
    css = data["agent.css"].decode()
    for name in TYPES:
        if name.startswith("fonts/"):
            css = css.replace(f'"./{name}"', f'"./{name}?v={version[name]}"')
    data["agent.css"] = css.encode()
    version["agent.css"] = hashlib.sha256(data["agent.css"]).hexdigest()[:16]

    def page(name):
        html = (STATIC/name).read_text(encoding="utf-8")
        for asset in ("agent.css", "agent.js"):
            html = html.replace(f'"{PREFIX}/{asset}"', f'"{PREFIX}/{asset}?v={version[asset]}"')
        return html.encode()
    return ({"/"+name: (body, TYPES[name]) for name, body in data.items()},
            page("index.html"), page("donnees.html"))


class AgentApplication(Application):
    def __init__(self, config, clock=time.time):
        # Config has already validated the public origin and secret.
        self.config = SimpleNamespace(origin=config.origin, secret=config.secret,
                                      secure=config.secure, trust_proxy=config.trust_proxy,
                                      prefix=PREFIX)
        self.clock = clock
        self.store = AgentStore(database_path(config))
        self.cookie_name = "__Secure-mia_agent_sid" if config.secure else "mia_agent_sid"
        self.assets, self.page, self.privacy = load_assets()

    def sign(self, value):
        return super().sign("agent:" + value)

    def api(self, env, route, method):
        if route not in ("session", "interest", "health"):
            raise Problem("not_found", 404)
        if method != ("POST" if route == "interest" else "GET"):
            raise Problem("method_not_allowed", 405)
        if route == "health":
            with self.store.transaction() as db:
                db.execute("SELECT 1 FROM interests LIMIT 1")
            return {"ok": True}, []
        now = self.clock()
        identity = self.sign("ip:" + str(int(now // 86400)) + ":" + self.peer(env))
        with self.store.transaction() as db:
            db.execute("DELETE FROM limits WHERE window<?", (int(now // 60) - 2,))
            # Visitors of the stand share the same Wi-Fi/NAT.
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
                    or not hmac.compare_digest(env.get("HTTP_X_CSRF_TOKEN", ""), self.sign("csrf:" + sid))):
                raise Problem("forbidden", 403)
            if env.get("CONTENT_TYPE", "").split(";", 1)[0] != "application/json":
                raise Problem("invalid_content_type", 415)
            length = env.get("CONTENT_LENGTH", "")
            if not length.isdecimal() or not 0 < int(length) <= 256:
                raise Problem("invalid_body_size", 413)
            try:
                data = json.loads(env["wsgi.input"].read(int(length)))
            except (ValueError, UnicodeDecodeError):
                raise Problem("invalid_json")
            if not isinstance(data, dict):
                raise Problem("invalid_json")
        with self.store.transaction() as db:
            if route == "session":
                if not valid:
                    sid = secrets.token_urlsafe(32)
                cookie = f"{self.cookie_name}={sid}; Path={PREFIX}; HttpOnly; SameSite=Strict; Max-Age=2592000"
                if self.config.secure:
                    cookie += "; Secure"
                row = db.execute("SELECT tri FROM interests WHERE owner=?",
                                 (self.sign("owner:" + sid),)).fetchone()
                return {"csrf": self.sign("csrf:" + sid), "tri": row["tri"] if row else None}, [("Set-Cookie", cookie)]
            owner = self.sign("owner:" + sid)
            rate_limit(db, identity, "write", now, count=120, period=60)
            rate_limit(db, owner, "owner_write", now, count=10, period=60)
        if set(data) != {"tri"} or not isinstance(data["tri"], str) or not re.fullmatch(r"[A-Z]{3}", data["tri"]):
            raise Problem("invalid_trigram")
        with self.store.transaction() as db:
            db.execute("INSERT INTO interests(owner,tri,created,updated) VALUES(?,?,?,?) "
                       "ON CONFLICT(owner) DO UPDATE SET tri=excluded.tri, updated=excluded.updated",
                       (owner, data["tri"], now, now))
        return {"tri": data["tri"]}, []
