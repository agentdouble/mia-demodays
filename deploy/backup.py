"""Root-only host backup; the application cannot read or alter these snapshots."""
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import os
import sqlite3
import tempfile
import time

BASE = Path("/srv/mia-demodays")
BACKUPS = Path("/var/backups/mia-demodays")


def backup(environment="production"):
    source = BASE / environment / "data/mia.sqlite3"
    if not source.exists():
        return None
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    target = BACKUPS / f"{environment}-{stamp}.sqlite3"
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as db:
        with closing(sqlite3.connect(target)) as snapshot:
            db.backup(snapshot)
            assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # Test restoration into another database, comparing canonical table content.
        with tempfile.TemporaryDirectory(prefix="mia-restore-") as temporary:
            with closing(sqlite3.connect(target)) as snapshot, closing(sqlite3.connect(Path(temporary)/"restore.sqlite3")) as restored:
                snapshot.backup(restored)
                assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                for table in ("games", "limits"):
                    assert snapshot.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() == restored.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    target.chmod(0o600)
    print(f"Backup and isolated restore check passed: {target.name}")
    return target


def daily():
    os.umask(0o077)
    backup()
    source = BASE / "production/data/mia.sqlite3"
    if source.exists():
        with closing(sqlite3.connect(source, timeout=10)) as db:
            db.execute("DELETE FROM games WHERE created<?", (time.time()-30*86400,))
            db.execute("DELETE FROM limits WHERE window<?", (int(time.time()//60)-2,))
            db.commit()
    for path in BACKUPS.glob("*.sqlite3"):
        if path.stat().st_mtime < time.time() - 14*86400:
            path.unlink()


if __name__ == "__main__":
    daily()
