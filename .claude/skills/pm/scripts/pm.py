#!/usr/bin/env python3
"""PM agent numbers and post text. The agent never counts, dates or retypes board data.

  pm.py --which DATE                       -> {"run": true|false}   (Mondays)
  pm.py --asof DATE --in board.json --out DIR

board.json = capture of get_board_items_page for board 18396405978 (all items, columns person, status, status_1, date4,
requested_due_date, last_updated, completed_date). Writes DIR/slack/00_parent.txt (short) and 01_detail.txt.
Exit 2 = board unreadable or incomplete.
"""
import argparse, datetime as dt, json, os, sys

STALE_DAYS = 14
# On hold on purpose (Jonathan, 2026-11-17): CookieYes consent fix, nothing to do. Don't raise it as needing a call.
HOLD_OK = {"13330303905"}
DONE_GROUPS = {"Completed", "Cancelled"}
SHOW = 3


def die(m):
    print(m, file=sys.stderr); sys.exit(2)


def sv(v):
    """column value as text: plain, or {"index","changed_at"} style objects (label unknown) -> None"""
    return v if isinstance(v, str) else None


def day(s):
    try: return dt.date.fromisoformat(str(s)[:10])
    except ValueError: return None


def short(n, k=58):
    n = " ".join(n.split())
    return n if len(n) <= k else n[:k - 1].rstrip() + "…"


def first(o):
    return (o or "Nobody").split(",")[0].split()[0] if o else "Nobody"


def link(i):
    return f"<{i['url']}|{short(i['name'])}>"


def run(a):
    asof = dt.date.fromisoformat(a.asof)
    try: d = json.load(open(a.inp))
    except (OSError, ValueError): die("board.json missing or unreadable")
    if d.get("pagination", {}).get("has_more"): die("board has more items than were read")
    items = d.get("items") or die("board has no items")
    rows = []
    for i in items:
        c = i["column_values"]
        rows.append({"id": i["id"], "name": i["name"], "url": i["url"], "group": i["group"]["title"],
                     "owner": c.get("person"), "status": sv(c.get("status")), "prio": sv(c.get("status_1")),
                     "due": day(c.get("date4")), "req": day(c.get("requested_due_date")),
                     "upd": day(c.get("last_updated")), "done": day(c.get("completed_date"))})
    # last week = the Sunday to Saturday before this Monday
    ws = asof - dt.timedelta(days=asof.weekday() + 1)
    we = ws + dt.timedelta(days=6)
    openi = [r for r in rows if r["group"] not in DONE_GROUPS]
    done = sorted([r for r in rows if r["group"] == "Completed" and r["done"] and ws <= r["done"] <= we], key=lambda r: r["done"])
    prog = [r for r in openi if r["group"] == "In Progress"]
    focus = sorted([r for r in prog if r["prio"] == "High"], key=lambda r: r["upd"] or dt.date.min)
    overdue = sorted([r for r in openi if r["due"] and r["due"] < asof], key=lambda r: r["due"])
    stale = sorted([r for r in prog if r["upd"] and (asof - r["upd"]).days >= STALE_DAYS and r not in overdue],
                   key=lambda r: r["upd"])
    noown = [r for r in prog + [x for x in openi if x["group"] in ("Open Tickets", "Scoping", "Up Next / Priority Items")]
             if not r["owner"]]
    hold = [r for r in openi if r["status"] == "On Hold" and r["id"] not in HOLD_OK and r["group"] in ("In Progress", "Scoping", "Open Tickets")]
    backhigh = [r for r in openi if r["group"] == "Backlog" and r["prio"] == "High"]
    own = {}
    for r in openi:
        for p in (r["owner"] or "Nobody").split(", "): own[p.split()[0]] = own.get(p.split()[0], 0) + 1

    def more(lst): return f" (+{len(lst) - SHOW} more in thread)" if len(lst) > SHOW else ""
    def line(r, extra=""): return f"• {link(r)} ({first(r['owner'])}{extra})"

    lab = f"week of {asof.strftime('%b')} {asof.day}"
    def age(r):
        n = (asof - r["upd"]).days if r["upd"] else 0
        return f", {n} days no update" if n >= STALE_DAYS else ""
    p = [f":clipboard: *Marketing, {lab}*  Done last week: {len(done)}. Open: {len(openi)}.",
         f"*Focus now* (high priority, in progress: {len(focus)}):"]
    p += [f"• {link(r)} ({first(r['owner'])}{age(r)})" for r in focus[:SHOW]] or ["• none marked High"]
    if len(focus) > SHOW: p.append(f"  +{len(focus) - SHOW} more in thread")
    need = ([f"• Overdue: {link(r)} ({first(r['owner'])}, due {r['due'].strftime('%b %-d')})" for r in overdue]
            + [f"• No owner: {link(r)}" for r in noown]
            + [f"• On hold since {r['upd'].strftime('%b %-d')}: {link(r)} ({first(r['owner'])})" for r in hold])
    if need:
        p.append("*Needs a call:*")
        p += need[:4]
        if len(need) > 4: p.append(f"  +{len(need) - 4} more in thread")
    if backhigh: p.append(f"*High priority not started:* {len(backhigh)} in Backlog (thread).")
    p.append(f"_{', '.join(f'{k} {v}' for k, v in sorted(own.items(), key=lambda kv: -kv[1]) if k != 'Nobody')}"
             f"{', no owner ' + str(own['Nobody']) if own.get('Nobody') else ''}. monday.com, as of {asof}._")
    t = ["*Detail*"]
    for title, lst in (("Focus now", focus), ("Done last week", done), ("Overdue", overdue), ("No update in 14+ days", stale),
                       ("No owner", noown), ("On hold", hold), ("High priority in Backlog", backhigh)):
        if lst: t.append(f"*{title} ({len(lst)})*"); t += [line(r) for r in lst]
    os.makedirs(os.path.join(a.out, "slack"), exist_ok=True)
    open(os.path.join(a.out, "slack", "00_parent.txt"), "w").write("\n".join(p))
    open(os.path.join(a.out, "slack", "01_detail.txt"), "w").write("\n".join(t))
    print(json.dumps({"week": lab, "open": len(openi), "done": len(done), "focus": len(focus), "overdue": len(overdue),
                      "stale": len(stale), "no_owner": len(noown), "on_hold": len(hold), "posts": 2}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--asof"); ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps({"run": dt.date.fromisoformat(a.which).weekday() == 0})); sys.exit(0)
    if not (a.asof and a.inp and a.out): ap.error("need --asof, --in, --out")
    run(a)
