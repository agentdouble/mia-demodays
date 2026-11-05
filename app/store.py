"""SQLite persistence. Every game mutation uses an immediate transaction."""
from contextlib import closing, contextmanager
from pathlib import Path
import sqlite3


class Store:
    def __init__(self, path: Path):
        self.path = path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    tri TEXT PRIMARY KEY CHECK(length(tri)=3),
                    owner TEXT NOT NULL UNIQUE,
                    clients TEXT NOT NULL,
                    answers TEXT NOT NULL DEFAULT '[]',
                    created REAL NOT NULL,
                    started REAL,
                    finished REAL,
                    time_ms INTEGER,
                    score INTEGER CHECK(score BETWEEN 0 AND 6),
                    grade TEXT
                );
                CREATE INDEX IF NOT EXISTS leaderboard
                    ON games(score DESC, time_ms ASC) WHERE finished IS NOT NULL;
                CREATE TABLE IF NOT EXISTS limits (
                    identity TEXT NOT NULL,
                    category TEXT NOT NULL,
                    window INTEGER NOT NULL,
                    count INTEGER NOT NULL,
                    PRIMARY KEY(identity, category)
                );
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA synchronous=FULL")
        db.execute("PRAGMA max_page_count=32768")  # At most 128 MiB at 4 KiB/page.
        return db

    @contextmanager
    def transaction(self):
        with closing(self.connect()) as db:
            db.execute("BEGIN IMMEDIATE")
            try:
                yield db
                db.commit()
            except BaseException:
                db.rollback()
                raise

    def backup(self, destination: Path):
        if destination.exists():
            raise ValueError("Refusing to overwrite an existing backup")
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self.connect()) as source, closing(sqlite3.connect(destination)) as target:
            source.backup(target)
            if target.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
                raise ValueError("Backup integrity check failed")
        destination.chmod(0o600)
