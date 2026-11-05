"""Checks the running HTTP process and SQLite without exposing private configuration."""
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from .config import Config

config = Config.from_env()
request = Request("http://127.0.0.1:8080/recommander/api/health",
                  headers={"Host": urlsplit(config.origin).netloc})
with urlopen(request, timeout=4) as response:
    if response.status != 200:
        raise SystemExit(1)
