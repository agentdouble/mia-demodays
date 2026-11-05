"""Explicit public files with content-versioned references across releases."""
from pathlib import Path
import hashlib

STATIC = Path(__file__).parent.parent / "mia/mia-recommander"
TYPES = {"game.js": "text/javascript", "api.js": "text/javascript", "viewport.js": "text/javascript",
         "game.css": "text/css", "fonts/press-start.ttf": "font/ttf",
         "fonts/pixel-400.ttf": "font/ttf", "fonts/pixel-600.ttf": "font/ttf", "fonts/pixel-700.ttf": "font/ttf"}


def load_assets():
    data = {name: (STATIC/name).read_bytes() for name in TYPES}
    def version(name):
        return hashlib.sha256(data[name]).hexdigest()[:16]
    script = data["game.js"].decode()
    for module in ("api.js", "viewport.js"):
        script = script.replace(f'"./{module}"', f'"./{module}?v={version(module)}"')
    data["game.js"] = script.encode()
    def page(name):
        html = (STATIC/name).read_text()
        for asset in ("game.css", "game.js"):
            html = html.replace(f'"/recommander/{asset}"', f'"/recommander/{asset}?v={version(asset)}"')
        return html.encode()
    return ({"/"+name: (body, TYPES[name]) for name, body in data.items()},
            page("index.html"), page("privacy.html"))
