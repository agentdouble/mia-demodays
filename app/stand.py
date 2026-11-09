"""Public QR displays with an explicit list of pages and assets."""
from pathlib import Path
from string import Template
from urllib.parse import urlsplit

from .http import CSP


STATIC = Path(__file__).with_name("stand")


class StandPages:
    def __init__(self, origin):
        self.host = urlsplit(origin).netloc
        self.pages = {}
        template = Template((STATIC / "index.html").read_text(encoding="utf-8"))
        stylesheet = (STATIC / "stand.css").read_bytes()
        for slug, title in (("recommander", "Recommander"), ("fraude", "Fraude")):
            route = f"/{slug}-qrcode"
            duel = ""
            if slug == "recommander":
                self.pages[f"{route}/duel.svg"] = ("image/svg+xml", (STATIC / "duel.svg").read_bytes())
                duel = f'<img class="stand-duel" src="{route}/duel.svg" width="328" height="76" alt="">'
            page = template.substitute(slug=slug, title=title, route=route, duel=duel)
            self.pages[route] = ("text/html; charset=utf-8", page.encode())
            self.pages[f"{route}/stand.css"] = ("text/css; charset=utf-8", stylesheet)
            self.pages[f"{route}/code.svg"] = ("image/svg+xml", (STATIC / f"{slug}.svg").read_bytes())

    def __call__(self, env, start_response):
        method = env.get("REQUEST_METHOD")
        headers = [("Content-Security-Policy", CSP), ("X-Content-Type-Options", "nosniff"),
                   ("Referrer-Policy", "no-referrer"), ("Cache-Control", "no-store")]
        if env.get("HTTP_HOST") != self.host:
            status, mime, body = "421 Misdirected Request", "text/plain", b"Invalid host"
        elif method not in ("GET", "HEAD"):
            status, mime, body = "405 Method Not Allowed", "text/plain", b"Method not allowed"
            headers.append(("Allow", "GET, HEAD"))
        else:
            status = "200 OK"
            mime, body = self.pages[env["PATH_INFO"]]
        headers.extend((("Content-Type", mime), ("Content-Length", str(len(body)))))
        start_response(status, headers)
        return [b"" if method == "HEAD" else body]
