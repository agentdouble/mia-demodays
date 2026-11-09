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


def backup_database(environment, filename):
    source = BASE / environment / "data" / filename
    if not source.exists():
        return None
    BACKUPS.mkdir(mode=0o700, parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    tag = {"mia.sqlite3": "", "fraude.sqlite3": "-fraude", "agent.sqlite3": "-agent"}[filename]
    target = BACKUPS / f"{environment}{tag}-{stamp}.sqlite3"
    with closing(sqlite3.connect(f"file:{source}?mode=ro", uri=True)) as db:
        with closing(sqlite3.connect(target)) as snapshot:
            db.backup(snapshot)
            assert snapshot.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
        # Test restoration into another database, comparing canonical table content.
        with tempfile.TemporaryDirectory(prefix="mia-restore-") as temporary:
            with closing(sqlite3.connect(target)) as snapshot, closing(sqlite3.connect(Path(temporary)/"restore.sqlite3")) as restored:
                snapshot.backup(restored)
                assert restored.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
                tables = ("interests", "limits") if filename == "agent.sqlite3" else ("games", "limits")
                for table in tables:
                    assert snapshot.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall() == restored.execute(f"SELECT * FROM {table} ORDER BY rowid").fetchall()
    target.chmod(0o600)
    print(f"Backup and isolated restore check passed: {target.name}")
    return target


def backup(environment="production"):
    """Keep the old default return value; also snapshot Fraude and MIA Agent when they exist."""
    original = backup_database(environment, "mia.sqlite3")
    backup_database(environment, "fraude.sqlite3")
    backup_database(environment, "agent.sqlite3")
    return original


def daily():
    os.umask(0o077)
    backup()
    for filename in ("mia.sqlite3", "fraude.sqlite3"):
        source = BASE / "production/data" / filename
        if source.exists():
            with closing(sqlite3.connect(source, timeout=10)) as db:
                db.execute("DELETE FROM games WHERE created<?", (time.time()-30*86400,))
                db.execute("DELETE FROM limits WHERE window<?", (int(time.time()//60)-2,))
                db.commit()
    # MIA Agent interests are contact requests: only expired rate-limit windows are purged.
    source = BASE / "production/data/agent.sqlite3"
    if source.exists():
        with closing(sqlite3.connect(source, timeout=10)) as db:
            db.execute("DELETE FROM limits WHERE window<?", (int(time.time()//60)-2,))
            db.commit()
    for path in BACKUPS.glob("*.sqlite3"):
        if path.stat().st_mtime < time.time() - 14*86400:
            path.unlink()


if __name__ == "__main__":
    daily()
