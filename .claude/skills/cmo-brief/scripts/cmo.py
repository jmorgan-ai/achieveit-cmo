#!/usr/bin/env python3
"""CMO weekly brief facts. Dates, review calendar and open decisions come from here; the agent never works them out.

Usage:
  cmo.py --which DATE            -> {"run": true|false}   (Mondays only)
  cmo.py --mode facts --asof DATE --decisions docs/decisions.md --out DIR
    writes DIR/facts.json: week, reviews this week, packs due this week, open items (from decisions.md '## Open')
"""
import argparse, datetime as dt, json, os, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
REVIEWS = {1: ("KPIs", "Jonathan", "Marketing Ops KPI pack"),
           2: ("attribution", "Amanda", "Marketing Ops attribution and performance pack, Paid pack"),
           3: ("website and SEO", "Cristina and Amanda", "SEO pack, Website pack"),
           4: ("social and brand", "Amanda and Cristina", "Content and Social pack")}


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def review_on(d):
    """(n, name, owners, packs) if d is a review Monday (1st to 4th Monday of its month)"""
    if d.weekday() != 0: return None
    n = (d.day - 1) // 7 + 1
    if n > 4: return None
    name, who, packs = REVIEWS[n]
    last = (d.replace(day=1) - dt.timedelta(days=1))
    return {"date": d.isoformat(), "n": n, "review": name, "owners": who, "covers": f"{MONTHS[last.month-1]} {last.year}", "packs": packs}


def facts(a):
    d = dt.date.fromisoformat(a.asof)
    mon = d - dt.timedelta(days=d.weekday())
    this = review_on(mon)
    nxt = review_on(mon + dt.timedelta(days=7))
    friday = mon + dt.timedelta(days=4)
    # packs that post this Friday are the ones for the review the following Monday
    due = review_on(friday + dt.timedelta(days=3))
    open_items = []
    if os.path.exists(a.decisions):
        on = False
        for ln in open(a.decisions, encoding="utf-8"):
            if ln.startswith("## "): on = ln.strip().lower() == "## open"; continue
            if on and ln.startswith("- "): open_items.append(ln[2:].strip())
    out = {"week_of": mon.isoformat(), "review_today": this, "review_next_week": nxt,
           "packs_posting_friday": due, "open_items": open_items, "open_count": len(open_items)}
    os.makedirs(a.out, exist_ok=True)
    json.dump(out, open(os.path.join(a.out, "facts.json"), "w"), indent=1)
    print(json.dumps(out))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--asof")
    ap.add_argument("--decisions", default="docs/decisions.md"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which:
        print(json.dumps({"run": dt.date.fromisoformat(a.which).weekday() == 0})); sys.exit(0)
    if a.mode == "facts": facts(a)
    else: ap.error("use --which DATE or --mode facts")
