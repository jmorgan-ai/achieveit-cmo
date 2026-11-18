#!/usr/bin/env python3
"""Open items log helper. Builds the exact monday column values and reads the board; the agent never types ids or dates itself.

  openlog.py key --agent Paid --text "Add negative keyword 'free'"            -> stable key
  openlog.py create --key K --name N --kind Recommendation --agent Paid --owner amanda --raised D [--review D] --evidence E --next S [--thread URL]
        -> JSON {"name":..., "columnValues":"<json string>"} for monday create_items
  openlog.py update [--status Accepted] [--outcome T] [--owner jonathan] [--review D] -> columnValues JSON string for change_item_column_values
  openlog.py ledger --items board.json --asof D [--candidates candidates.json] --out DIR   -> DIR/ledger.json
"""
import argparse, datetime as dt, hashlib, json, os, re, sys

COL = {"status": "color_mm976x05", "kind": "color_mm97y5f3", "owner": "multiple_person_mm97hsta", "agent": "text_mm97y1ns",
       "raised": "date_mm97ppk7", "review": "date_mm97s6vh", "evidence": "long_text_mm9771m7", "next": "long_text_mm97mj3k",
       "outcome": "long_text_mm9757ey", "key": "text_mm97sdmw", "thread": "link_mm97ak"}
PEOPLE = {"jonathan": 10858197, "amanda": 4314775, "cristina": 108197534}
STATUSES = ["Open", "Accepted", "In progress", "Done", "Declined", "Stale", "Needs decision", "Parked"]
KINDS = ["Recommendation", "Rule change", "Data gap", "Question", "Conflict"]
STALE_DAYS = 14


def make_key(agent, text):
    t = re.sub(r"[0-9$,.%]+", "", (text or "").lower())
    t = re.sub(r"[^a-z ]", " ", t)
    t = " ".join(t.split()[:14])
    return f"{agent.lower()}-{hashlib.sha1(t.encode()).hexdigest()[:8]}"


def owners(s):
    ids = [PEOPLE[x.strip().lower()] for x in (s or "").split(",") if x.strip().lower() in PEOPLE]
    return {"personsAndTeams": [{"id": i, "kind": "person"} for i in ids]} if ids else None


def cv_create(a):
    if a.kind not in KINDS: sys.exit(f"kind must be one of {KINDS}")
    raised = dt.date.fromisoformat(a.raised)
    review = a.review or (raised + dt.timedelta(days=STALE_DAYS)).isoformat()
    v = {COL["status"]: {"label": "Open"}, COL["kind"]: {"label": a.kind}, COL["agent"]: a.agent,
         COL["raised"]: {"date": raised.isoformat()}, COL["review"]: {"date": review},
         COL["evidence"]: {"text": a.evidence or ""}, COL["next"]: {"text": a.next or ""}, COL["key"]: a.key}
    o = owners(a.owner)
    if o: v[COL["owner"]] = o
    if a.thread: v[COL["thread"]] = {"url": a.thread, "text": "pack post"}
    return {"name": a.name[:255], "columnValues": json.dumps(v)}


def cv_update(a):
    v = {}
    if a.status:
        if a.status not in STATUSES: sys.exit(f"status must be one of {STATUSES}")
        v[COL["status"]] = {"label": a.status}
    if a.outcome is not None: v[COL["outcome"]] = {"text": a.outcome}
    if a.owner:
        o = owners(a.owner)
        if o: v[COL["owner"]] = o
    if a.review: v[COL["review"]] = {"date": a.review}
    return json.dumps(v)


def read_items(path):
    t = open(path, encoding="utf-8").read()
    obj = json.JSONDecoder().raw_decode(t[t.index("{"):])[0]
    out = []
    for it in obj.get("items", []):
        c = it.get("column_values", {})
        out.append({"id": it["id"], "name": it["name"], "url": it.get("url"), "status": c.get(COL["status"]) or "Open",
                    "kind": c.get(COL["kind"]), "owner": c.get(COL["owner"]), "agent": c.get(COL["agent"]),
                    "raised": c.get(COL["raised"]), "review": c.get(COL["review"]), "key": c.get(COL["key"]),
                    "outcome": c.get(COL["outcome"])})
    return out


def ledger(a):
    items = read_items(a.items)
    d = dt.date.fromisoformat(a.asof)
    live = [i for i in items if i["status"] in ("Open", "Accepted", "In progress", "Needs decision", "Stale")]
    age = lambda i: (d - dt.date.fromisoformat(i["raised"])).days if i["raised"] else 0
    overdue = [i for i in items if i["status"] in ("Open", "Needs decision") and i["review"] and dt.date.fromisoformat(i["review"]) < d]
    out = {"asof": a.asof, "total": len(items),
           "by_status": {s: sum(1 for i in items if i["status"] == s) for s in STATUSES},
           "open_over_14_days": [{"id": i["id"], "name": i["name"], "owner": i["owner"], "age_days": age(i), "url": i["url"]} for i in sorted(live, key=lambda x: -age(x)) if age(i) > STALE_DAYS and i["status"] in ("Open", "Needs decision")][:10],
           "to_mark_stale": [{"id": i["id"], "name": i["name"], "key": i["key"]} for i in overdue if age(i) > STALE_DAYS and i["status"] == "Open"],
           "needs_decision": [{"id": i["id"], "name": i["name"], "owner": i["owner"], "url": i["url"]} for i in items if i["status"] == "Needs decision"]}
    if a.candidates:
        cands = json.load(open(a.candidates))["candidates"]
        byk = {i["key"]: i for i in items if i["key"]}
        out["new"], out["repeats"] = [], []
        for c in cands:
            hit = byk.get(c["key"])
            if not hit: out["new"].append(c)
            else: out["repeats"].append({**c, "item_id": hit["id"], "item_status": hit["status"], "item_name": hit["name"]})
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, "ledger.json"), "w"), indent=1)
    print(json.dumps({k: (len(v) if isinstance(v, list) else v) for k, v in out.items()}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd")
    for x in ("agent", "text", "key", "name", "kind", "owner", "raised", "review", "evidence", "next", "thread", "status", "outcome", "items", "asof", "candidates", "out"):
        ap.add_argument("--" + x)
    a = ap.parse_args()
    if a.cmd == "key": print(make_key(a.agent, a.text))
    elif a.cmd == "create": print(json.dumps(cv_create(a)))
    elif a.cmd == "update": print(cv_update(a))
    elif a.cmd == "ledger": ledger(a)
    else: ap.error("cmd: key | create | update | ledger")
