#!/usr/bin/env python3
"""ICP fit agent numbers. All figures come from here; the agent never computes or retypes a number.

Usage:
  icp.py --which DATE                       -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}  (Friday before the 2nd Monday)
  icp.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Input DIR/opps.json: raw Salesforce soqlQuery result (first JSON object) with records for New Business opps created since
2025-01-01: Id, Account.Name, CreatedDate, CloseDate, StageName, IsWon, IsClosed, Amount, Market__c, Sub_Market__c,
Attribution_Source__c, Demo_Attribution__c. Exit 2 = input missing or unreadable.
"""
import argparse, calendar, datetime as dt, json, os, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
GROUPS = [("Local government", lambda m, s: m == "Government" and s == "Local Government"),
          ("State government", lambda m, s: m == "Government" and s == "State Government"),
          ("Education (higher ed, K-12)", lambda m, s: m == "Government" and s in ("Higher Education", "K-12 Education")),
          ("Other government (federal, international)", lambda m, s: m == "Government" and s in ("Federal Government", "International Government")),
          ("Commercial (all)", lambda m, s: m == "Commercial"),
          ("No market set", lambda m, s: not m)]


def die(msg):
    print(msg, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    mon = nth_monday(d.year, d.month, 2)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def fmt(n): return f"{n:,.0f}"


def load(p):
    if not os.path.exists(p): die("opps.json missing")
    t = open(p, encoding="utf-8").read()
    try:
        obj, _ = json.JSONDecoder().raw_decode(t[t.index("{"):])
        return obj["records"]
    except (ValueError, KeyError): die("opps.json unreadable")


def inbound(r):
    return r.get("Attribution_Source__c") == "Inbound" and r.get("Demo_Attribution__c") != "Field Sourced"


def stats(rows):
    won = [r for r in rows if r["IsWon"]]; lost = [r for r in rows if r["IsClosed"] and not r["IsWon"]]
    return {"n": len(rows), "won": len(won), "lost": len(lost), "open": len(rows) - len(won) - len(lost),
            "arr": sum(r.get("Amount") or 0 for r in won)}


def pack(a):
    y, m = map(int, a.month.split("-"))
    recs = [r for r in load(os.path.join(a.inp, "opps.json")) if inbound(r)]
    for r in recs: r["_d"] = dt.date.fromisoformat(r["CreatedDate"][:10])
    asof = dt.date.fromisoformat(a.asof)
    newest = max(r["_d"] for r in recs)
    label = f"{MONTHS[m-1]} {y}"
    month = [r for r in recs if (r["_d"].year, r["_d"].month) == (y, m)]
    ytd = [r for r in recs if r["_d"].year == y and r["_d"].month <= m]
    prior = [r for r in recs if r["_d"].year == y - 1]
    gaps, lines, hl = [], [], []
    ev = f"Salesforce Opportunity (New Business, Inbound, not Field Sourced), created dates through {newest}"
    if not month: gaps.append(f"No inbound opps created in {label}")
    lines.append(f"*Inbound opps by market ({label}, Jan to {MONTHS[m-1]} {y}, full year {y-1}):*")
    lines.append("Market | month | YTD (won / lost / open, won ARR) | share of YTD | share in " + str(y - 1))
    for name, f in GROUPS:
        g = lambda rows: [r for r in rows if f(r.get("Market__c"), r.get("Sub_Market__c"))]
        sm, sy, sp = stats(g(month)), stats(g(ytd)), stats(g(prior))
        shy = sy["n"] / len(ytd) * 100 if ytd else 0
        shp = sp["n"] / len(prior) * 100 if prior else 0
        lines.append(f"• {name}: {sm['n']} | {sy['n']} ({sy['won']} / {sy['lost']} / {sy['open']}, ${fmt(sy['arr'])}) | {shy:.0f}% | {shp:.0f}%")
    t = stats(ytd)
    lines.append(f"Total inbound: {len(month)} in {label}; {t['n']} year to date ({t['won']} won, {t['lost']} lost, {t['open']} open, ${fmt(t['arr'])} won ARR).")
    closed = t["won"] + t["lost"]
    lines.append("Win rate year to date: " + (f"{t['won'] / closed * 100:.0f}% on {closed} closed opps" if closed >= 5 else "not shown, fewer than 5 closed opps")
                 + ". Small numbers: read segment win rates as direction only.")
    lg = [r for r in ytd if GROUPS[0][1](r.get("Market__c"), r.get("Sub_Market__c"))]
    lgp = [r for r in prior if GROUPS[0][1](r.get("Market__c"), r.get("Sub_Market__c"))]
    cm = [r for r in ytd if GROUPS[4][1](r.get("Market__c"), r.get("Sub_Market__c"))]
    nm = [r for r in recs if not r.get("Market__c") and r["_d"].year == y]
    if ytd:
        hl.append({"id": "lg_share", "rank": 10, "text": f"Local government is {len(lg) / len(ytd) * 100:.0f}% of inbound opps in {y} to date "
                   f"({len(lg)} of {len(ytd)}), vs {len(lgp) / len(prior) * 100:.0f}% in {y-1}." if prior else
                   f"Local government is {len(lg) / len(ytd) * 100:.0f}% of inbound opps in {y} to date ({len(lg)} of {len(ytd)}).",
                   "evidence": ev})
        sl = stats(lg)
        hl.append({"id": "lg_wins", "rank": 12, "text": f"Local government, the growth priority, has {sl['n']} inbound opps in {y} to date: {sl['won']} won, {sl['lost']} lost, "
                   f"{sl['open']} open (${fmt(sl['arr'])} won ARR)." , "evidence": ev})
        hl.append({"id": "commercial", "rank": 8, "text": f"Commercial is {len(cm) / len(ytd) * 100:.0f}% of inbound opps in {y} to date "
                   f"({len(cm)} of {len(ytd)}) and ${fmt(stats(cm)['arr'])} of ${fmt(t['arr'])} won ARR; it stays out of targeting.",
                   "evidence": ev})
    if nm:
        hl.append({"id": "no_market", "rank": 5, "text": f"{len(nm)} inbound opps created in {y} have no market set, so they cannot be read by segment.",
                   "evidence": ev})
    # closed-won by close date, all attribution (local government wins often come from outbound or field)
    allr = load(os.path.join(a.inp, "opps.json"))
    wy = [r for r in allr if r["IsWon"] and r["CloseDate"][:4] == str(y) and int(r["CloseDate"][5:7]) <= m]
    lines.append(f"*Closed won in {y} to date, all sources, by market (close date):*")
    for name, f in GROUPS[:5]:
        w = [r for r in wy if f(r.get("Market__c"), r.get("Sub_Market__c"))]
        if not w: lines.append(f"• {name}: 0"); continue
        by = {}
        for r in w: by[r.get("Demo_Attribution__c") or "none"] = by.get(r.get("Demo_Attribution__c") or "none", 0) + 1
        lines.append(f"• {name}: {len(w)} won, ${fmt(sum(r.get('Amount') or 0 for r in w))} ARR (" + ", ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda kv: -kv[1])) + ")")
    lgw = [r for r in wy if GROUPS[0][1](r.get("Market__c"), r.get("Sub_Market__c"))]
    if lgw:
        inb = [r for r in lgw if inbound(r)]
        hl.append({"id": "lg_won_sources", "rank": 11, "text": f"Local government has {len(lgw)} deals closed won in {y} to date; {len(inb)} came in as inbound "
                   f"(marketing or referral, not Field Sourced) and {len(lgw) - len(inb)} through outbound, field or other routes.",
                   "evidence": "Salesforce Opportunity, StageName 5a - Closed Won, close dates in " + str(y) + ", all attribution"})
    gaps.append("Organization size (SalesRoads thresholds) is not checked: Salesforce opps carry no population or enrollment; open item for Amanda")
    gaps.append("Sub market splits government only; Healthcare appears under Commercial in Salesforce")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    head = f":dart: *ICP fit, {label}* (as of {asof}; second-Monday review)\n{{TOP_FINDINGS}}\n" + lines[-3] + "\n:warning: " + "; ".join(gaps)
    open(os.path.join(out, "00_parent.txt"), "w").write(head)
    open(os.path.join(out, "01_detail.txt"), "w").write("*Detail*\n" + "\n".join(lines))
    json.dump(sorted(hl, key=lambda h: -h["rank"]), open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "highlights": len(hl), "gaps": gaps, "posts": 2}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
