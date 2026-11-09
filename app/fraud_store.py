"""Fraud games have their own database; recommander's schema is never migrated."""
from contextlib import closing
from .store import Store


def database_path(config):
    path = config.database.with_name("fraude.sqlite3")
    if path.resolve() == config.database.resolve():
        raise ValueError("Fraud and recommander databases must be distinct")
    return path


class FraudStore(Store):
    def __init__(self, path):
        self.path = path
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        with closing(self.connect()) as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    tri TEXT PRIMARY KEY CHECK(length(tri)=3),
                    owner TEXT NOT NULL UNIQUE,
                    cases TEXT NOT NULL,
                    answers TEXT NOT NULL DEFAULT '[]',
                    created REAL NOT NULL,
                    started REAL,
                    card_index INTEGER NOT NULL DEFAULT 0,
                    card_started REAL,
                    finished REAL,
                    time_ms INTEGER,
                    score INTEGER CHECK(score BETWEEN 0 AND 6),
                    bonus INTEGER CHECK(bonus BETWEEN 0 AND 6),
                    grade TEXT
                );
                CREATE INDEX IF NOT EXISTS leaderboard
                    ON games(score DESC, bonus DESC, time_ms ASC) WHERE finished IS NOT NULL;
                CREATE TABLE IF NOT EXISTS limits (
                    identity TEXT NOT NULL, category TEXT NOT NULL,
                    window INTEGER NOT NULL, count INTEGER NOT NULL,
                    PRIMARY KEY(identity, category)
                );
            """)
