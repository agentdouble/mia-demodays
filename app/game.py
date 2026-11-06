"""Authoritative rounds, answers, timing and public leaderboard."""
from pathlib import Path
import json
import random
import re

CLIENTS = json.loads(Path(__file__).with_name("clients.json").read_text())
ROUND = 6
RETENTION = 30 * 86400
LEASE = 30 * 60


class Problem(Exception):
    def __init__(self, code, status=400):
        self.code, self.status = code, status


def rate_limit(db, identity, category, now, *, count, period):
    window = int(now // period)
    row = db.execute("SELECT window,count FROM limits WHERE identity=? AND category=?",
                     (identity, category)).fetchone()
    if row and row["window"] == window and row["count"] >= count:
        raise Problem("limited", 429)
    hits = row["count"] + 1 if row and row["window"] == window else 1
    db.execute("INSERT INTO limits VALUES(?,?,?,?) ON CONFLICT(identity,category) "
               "DO UPDATE SET window=excluded.window,count=excluded.count",
               (identity, category, window, hits))


def public_clients(ids):
    return [{k: v for k, v in CLIENTS[i].items() if k not in ("yes", "why")} for i in ids]


def participation(db, owner, now):
    """Report only this browser's unexpired reservation/round, without mutating it."""
    row = db.execute(
        "SELECT tri,started,finished FROM games WHERE owner=? AND created>=? "
        "AND (started IS NOT NULL OR created>=?) "
        "AND (finished IS NOT NULL OR started IS NULL OR started>=?)",
        (owner, now-RETENTION, now-LEASE, now-LEASE),
    ).fetchone()
    if not row:
        return None
    status = "done" if row["finished"] is not None else "playing" if row["started"] is not None else "reserved"
    return {"tri": row["tri"], "status": status}


def claim(db, owner, tri, now):
    if not isinstance(tri, str) or not re.fullmatch(r"[A-Z]{3}", tri):
        raise Problem("invalid_trigram")
    db.execute("DELETE FROM games WHERE created<? OR (started IS NULL AND created<?)",
               (now - RETENTION, now - LEASE))
    # A started but unfinished round also expires after 30 minutes.
    db.execute("DELETE FROM games WHERE finished IS NULL AND started<?", (now - LEASE,))
    row = db.execute("SELECT * FROM games WHERE tri=? OR owner=?", (tri, owner)).fetchone()
    if row:
        if row["owner"] == owner and row["tri"] == tri and row["started"] is None:
            return {"clients": public_clients(json.loads(row["clients"]))}
        raise Problem("taken" if row["tri"] == tri else "played", 409)
    rng = random.SystemRandom()
    yes = [i for i, c in enumerate(CLIENTS) if c["yes"]]
    no = [i for i, c in enumerate(CLIENTS) if not c["yes"]]
    n = rng.choice([2, 3, 4])
    ids = rng.sample(yes, n) + rng.sample(no, ROUND - n)
    rng.shuffle(ids)
    db.execute("INSERT INTO games(tri,owner,clients,created) VALUES(?,?,?,?)",
               (tri, owner, json.dumps(ids), now))
    return {"clients": public_clients(ids)}


def owned_game(db, owner, now):
    row = db.execute("SELECT * FROM games WHERE owner=?", (owner,)).fetchone()
    if not row:
        raise Problem("no_game", 404)
    if row["finished"] is None and now - row["created"] > LEASE:
        raise Problem("expired", 409)
    return row


def start(db, owner, now):
    row = owned_game(db, owner, now)
    if row["finished"] is not None:
        raise Problem("played", 409)
    if row["started"] is None:
        db.execute("UPDATE games SET started=? WHERE tri=?", (now, row["tri"]))
    return {"ok": True}


def answer(db, owner, data, now):
    if set(data) != {"index", "yes"} or type(data["index"]) is not int or type(data["yes"]) is not bool:
        raise Problem("invalid_answer")
    index = data["index"]
    if not 0 <= index < ROUND:
        raise Problem("invalid_answer")
    row = owned_game(db, owner, now)
    if row["started"] is None:
        raise Problem("not_started", 409)
    answers, ids = json.loads(row["answers"]), json.loads(row["clients"])
    if index > len(answers):
        raise Problem("out_of_order", 409)
    if index < len(answers):
        if answers[index] is not data["yes"]:
            raise Problem("answer_locked", 409)
        return answer_response(row, ids, index, data["yes"])
    if now - row["started"] < (index + 1) * 0.12:
        raise Problem("too_fast", 429)
    answers.append(data["yes"])
    db.execute("UPDATE games SET answers=? WHERE tri=?", (json.dumps(answers), row["tri"]))
    if len(answers) == ROUND:
        elapsed = max(1, round((now - row["started"]) * 1000))
        score = sum(value == CLIENTS[i]["yes"] for i, value in zip(ids, answers))
        grade = ("S" if elapsed < 18000 else "A") if score == ROUND else {5: "B", 4: "C"}.get(score, "D")
        db.execute("UPDATE games SET finished=?,time_ms=?,score=?,grade=? WHERE tri=?",
                   (now, elapsed, score, grade, row["tri"]))
        row = db.execute("SELECT * FROM games WHERE tri=?", (row["tri"],)).fetchone()
    return answer_response(row, ids, index, data["yes"])


def answer_response(row, ids, index, value):
    result = None
    if row["finished"] is not None:
        result = {"score": row["score"], "timeMs": row["time_ms"], "grade": row["grade"], "total": ROUND}
    return {"correct": value == CLIENTS[ids[index]]["yes"], "result": result}


def leaderboard(db, now):
    rows = db.execute("SELECT tri,score,time_ms,grade FROM games WHERE finished IS NOT NULL "
                      "AND created>=? ORDER BY score DESC,time_ms ASC,tri ASC LIMIT 17576",
                      (now - RETENTION,)).fetchall()
    return {"rows": [{"tri": r["tri"], "score": r["score"], "timeMs": r["time_ms"],
                      "grade": r["grade"], "total": ROUND} for r in rows]}
