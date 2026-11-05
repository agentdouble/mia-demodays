"""Validated deployment settings, shared by HTTP and maintenance commands."""
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit
import os


@dataclass(frozen=True)
class Config:
    database: Path
    secret: str
    origin: str = "https://mia-foyer.com"
    prefix: str = "/recommander"
    trust_proxy: bool = False

    def __post_init__(self):
        url = urlsplit(self.origin)
        if (url.scheme not in ("http", "https") or not url.netloc
                or url.path or url.query or url.fragment or url.username):
            raise ValueError("PUBLIC_ORIGIN must be a single origin without a path")
        local = url.hostname in ("localhost", "127.0.0.1") or (url.hostname or "").endswith(".localhost")
        if url.scheme != "https" and not local:
            raise ValueError("Public deployments require HTTPS")
        if len(self.secret) < 32:
            raise ValueError("APP_SECRET must contain at least 32 characters")
        if self.prefix != "/recommander":
            raise ValueError("The application is mounted at /recommander")

    @property
    def secure(self):
        return self.origin.startswith("https://")

    @classmethod
    def from_env(cls):
        return cls(Path(os.environ.get("DATABASE_PATH", "/data/mia.sqlite3")),
                   os.environ.get("APP_SECRET", ""),
                   os.environ.get("PUBLIC_ORIGIN", "https://mia-foyer.com"),
                   trust_proxy=os.environ.get("TRUST_PROXY") == "1")
