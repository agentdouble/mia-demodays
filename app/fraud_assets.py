"""An explicit public manifest, with versioned assets and no private cases JSON."""
from pathlib import Path
import hashlib
import json

STATIC = Path(__file__).parent.parent / "mia/mia-fraude"


def load_assets():
    # Checked-in manifest, never a user-supplied path or recursive web root.
    names = json.loads((STATIC/"manifest.json").read_text())
    mime = {".js": "text/javascript", ".css": "text/css", ".ttf": "font/ttf",
            ".webp": "image/webp", ".svg": "image/svg+xml", ".txt": "text/plain; charset=utf-8"}
    data = {name: (STATIC/name).read_bytes() for name in names}
    def version(name):
        return hashlib.sha256(data[name]).hexdigest()[:16]
    script = data["game.js"].decode()
    for module in ("api.js", "viewport.js", "arcade.js", "geometry.js"):
        script = script.replace(f'"./{module}"', f'"./{module}?v={version(module)}"')
    data["game.js"] = script.encode()
    def page(name):
        html = (STATIC/name).read_text()
        for asset in ("game.css", "game.js"):
            html = html.replace(f'"/fraude/{asset}"', f'"/fraude/{asset}?v={version(asset)}"')
        return html.encode()
    return ({"/"+name: (body, mime[Path(name).suffix]) for name, body in data.items()},
            page("index.html"), page("privacy.html"))
