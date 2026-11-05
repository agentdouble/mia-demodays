"""Administrative CLI; no administrative route is exposed over HTTP."""
from contextlib import closing
from pathlib import Path
import argparse
import sqlite3

from .config import Config
from .store import Store
from .game import RETENTION
import time


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("backup", "check", "purge"))
    parser.add_argument("path", nargs="?")
    args = parser.parse_args()
    if args.action == "check":
        if not args.path:
            parser.error("check requires an existing SQLite file")
        with closing(sqlite3.connect(f"file:{Path(args.path).resolve()}?mode=ro", uri=True)) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            print("SQLite integrity: OK; games:", db.execute("SELECT count(*) FROM games").fetchone()[0])
        return
    store = Store(Config.from_env().database)
    if args.action == "backup":
        if not args.path:
            parser.error("backup requires a new destination path")
        store.backup(Path(args.path))
        print("SQLite backup and integrity check: OK")
    else:
        with store.transaction() as db:
            db.execute("DELETE FROM games WHERE created<?", (time.time() - RETENTION,))
            db.execute("DELETE FROM limits")
        print("Expired game data purged")


if __name__ == "__main__":
    main()
