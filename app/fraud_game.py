"""One current case at a time; decisions, clue hits and timing are server-owned.

State: reserved -> decision -> locate -> feedback -> next (six times) -> done.
Identical retries never reset a clock or award a bonus twice.
"""
from pathlib import Path
import json
import math
import random
from .game import Problem, RETENTION, LEASE, validate_trigram

CASES = json.loads(Path(__file__).with_name("fraud_cases.json").read_text())
ROUND = 6


def purge(db, now):
    db.execute("DELETE FROM games WHERE created<? OR "
               "(finished IS NULL AND COALESCE(started,created)<?)", (now-RETENTION, now-LEASE))


def owned(db, owner, now):
    row = db.execute("SELECT * FROM games WHERE owner=?", (owner,)).fetchone()
    if not row:
        raise Problem("no_game", 404)
    if row["created"] < now-RETENTION or (row["finished"] is None and (row["started"] or row["created"]) < now-LEASE):
        raise Problem("expired", 409)
    return row


def result(row):
    return {"tri": row["tri"], "score": row["score"], "bonus": row["bonus"],
            "timeMs": row["time_ms"], "grade": row["grade"], "total": ROUND}


def current_case(row):
    return CASES[json.loads(row["cases"])[row["card_index"]]]


def state(row, now):
    index = row["card_index"]
    answers = json.loads(row["answers"])
    phase = "reserved" if row["started"] is None else "decision"
    if len(answers) > index:
        phase = "feedback" if answers[index]["located"] else "locate"
    case = current_case(row)
    response = {"tri": row["tri"], "index": index, "phase": phase,
                "timeMs": sum(a["decision_ms"] for a in answers),
                "runningMs": max(0, round((now-row["card_started"])*1000)) if phase == "decision" else 0,
                "progress": [{"correct": a["review"] == CASES[i]["review"]} for i, a in
                             zip(json.loads(row["cases"]), answers) if a["located"]]}
    if phase != "reserved":
        response["case"] = {k: case[k] for k in ("title", "context", "panels")}
    if phase == "feedback":
        a = answers[index]
        response["feedback"] = {"correct": a["review"] == case["review"], "review": case["review"],
                                "hit": a["hit"], "explanation": case["explanation"],
                                "zones": case["zones"], "selection": a["selection"]}
    if row["finished"] is not None:
        response["result"] = result(row)
    return response


def participation(db, owner, now):
    try:
        row = owned(db, owner, now)
    except Problem:
        return None
    return {"tri": row["tri"], "status": "done" if row["finished"] is not None else
            "reserved" if row["started"] is None else "playing"}


def claim(db, owner, tri, now):
    validate_trigram(tri)
    purge(db, now)
    row = db.execute("SELECT * FROM games WHERE tri=? OR owner=?", (tri, owner)).fetchone()
    if row:
        if row["owner"] == owner and row["tri"] == tri and row["started"] is None:
            return state(row, now)
        raise Problem("played" if row["owner"] == owner else "taken", 409)
    ids = list(range(len(CASES)))
    random.SystemRandom().shuffle(ids)
    db.execute("INSERT INTO games(tri,owner,cases,created) VALUES(?,?,?,?)", (tri, owner, json.dumps(ids), now))
    return state(owned(db, owner, now), now)


def start(db, owner, now):
    row = owned(db, owner, now)
    if row["started"] is None:
        db.execute("UPDATE games SET started=?,card_started=? WHERE owner=?", (now, now, owner))
    return state(owned(db, owner, now), now)


def validate_index(data, keys):
    if set(data) != keys or type(data.get("index")) is not int or not 0 <= data["index"] < ROUND:
        raise Problem("invalid_body")


def answer(db, owner, data, now):
    validate_index(data, {"index", "review"})
    if type(data["review"]) is not bool:
        raise Problem("invalid_answer")
    row = owned(db, owner, now)
    answers, index = json.loads(row["answers"]), data["index"]
    if row["started"] is None or index != row["card_index"]:
        raise Problem("out_of_order", 409)
    if len(answers) > index:
        if answers[index]["review"] != data["review"]:
            raise Problem("answer_locked", 409)
        return state(row, now)
    elapsed = now-row["card_started"]
    if elapsed < .18:
        raise Problem("too_fast", 429)
    answers.append({"review": data["review"], "decision_ms": round(elapsed*1000),
                    "located": False, "hit": False, "selection": None})
    db.execute("UPDATE games SET answers=? WHERE owner=?", (json.dumps(answers), owner))
    return state(owned(db, owner, now), now)


def locate(db, owner, data, now):
    skip = set(data) == {"index", "skip"} and data["skip"] is True
    validate_index(data, {"index", "skip"} if skip else {"index", "panel", "x", "y"})
    selection = None
    if not skip:
        if type(data["panel"]) is not int or not all(type(data[k]) in (int, float) and math.isfinite(data[k]) and 0 <= data[k] <= 1 for k in ("x", "y")):
            raise Problem("invalid_point")
        selection = {k: data[k] for k in ("panel", "x", "y")}
    row = owned(db, owner, now)
    index, answers = data["index"], json.loads(row["answers"])
    if index != row["card_index"] or len(answers) <= index:
        raise Problem("out_of_order", 409)
    case, a = current_case(row), answers[index]
    if selection is not None and not 0 <= selection["panel"] < len(case["panels"]):
        raise Problem("invalid_point")
    if a["located"]:
        if a["selection"] != selection:
            raise Problem("clue_locked", 409)
        return state(row, now)
    a["located"], a["selection"] = True, selection
    # Slight padding accommodates a finger at the border, not an entire page tap.
    a["hit"] = bool(selection and any(z["panel"] == selection["panel"] and
        z["x"]-.025 <= selection["x"] <= z["x"]+z["w"]+.025 and
        z["y"]-.025 <= selection["y"] <= z["y"]+z["h"]+.025 for z in case["zones"]))
    db.execute("UPDATE games SET answers=? WHERE owner=?", (json.dumps(answers), owner))
    if index == ROUND-1:
        score = sum(a["review"] == CASES[i]["review"] for i, a in zip(json.loads(row["cases"]), answers))
        bonus = sum(a["hit"] for a in answers)
        grade = ("S" if bonus == ROUND else "A") if score == ROUND else {5: "B", 4: "C"}.get(score, "D")
        db.execute("UPDATE games SET finished=?,score=?,bonus=?,time_ms=?,grade=? WHERE owner=?",
                   (now, score, bonus, sum(a["decision_ms"] for a in answers), grade, owner))
    return state(owned(db, owner, now), now)


def next_case(db, owner, data, now):
    validate_index(data, {"index"})
    row = owned(db, owner, now)
    index, answers = data["index"], json.loads(row["answers"])
    if index == row["card_index"]-1:
        return state(row, now)  # Lost response retry: don't restart the next timer.
    if index != row["card_index"] or len(answers) <= index or not answers[index]["located"]:
        raise Problem("out_of_order", 409)
    if row["finished"] is None:
        db.execute("UPDATE games SET card_index=card_index+1,card_started=? WHERE owner=?", (now, owner))
    return state(owned(db, owner, now), now)


def leaderboard(db, now):
    rows = db.execute("SELECT * FROM games WHERE finished IS NOT NULL AND created>=? "
                      "ORDER BY score DESC,bonus DESC,time_ms ASC,tri ASC LIMIT 17576", (now-RETENTION,)).fetchall()
    return {"rows": [result(row) for row in rows]}
