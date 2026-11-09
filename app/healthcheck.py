"""Checks the running HTTP process and SQLite without exposing private configuration."""
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from .config import Config

config = Config.from_env()
for game in ("recommander", "fraude"):
    request = Request(f"http://127.0.0.1:8080/{game}/api/health",
                      headers={"Host": urlsplit(config.origin).netloc})
    with urlopen(request, timeout=2) as response:
        if response.status != 200:
            raise SystemExit(1)
