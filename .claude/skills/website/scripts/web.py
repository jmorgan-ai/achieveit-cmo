#!/usr/bin/env python3
"""Website and CRO agent numbers (GA4 + Search Console). The agent never computes or retypes a number.

  web.py --which DATE   -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}   (Friday before the third Monday)
  web.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Inputs in DIR (text saved by shared/capture.py from Marketing Data Feeds.xlsx):
  ga4_monthly.txt   GA4_Monthly_Channel (sheet 4)   required
  ga4_landing.txt   GA4_Landing_Pages (sheet 5)     optional (read is cut at about 2,200 rows, highest sessions first)
  ga4_events.txt    GA4_Key_Events (sheet 6)        optional (read covers only the newest ~19 days)
  gsc_daily.txt     GSC_Daily (sheet 7)             optional (data-health ratio)
Exit 2 = a required input is missing or the month is not in it.
"""
import argparse, calendar, datetime as dt, json, os, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MONEY_PAGES = ("/pricing", "/solutions", "/industry", "/product", "/demo-request", "/live-product-tour", "/contact")
MIN_SESSIONS = 30


def die(m):
    print(m, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    mon = nth_monday(d.year, d.month, 3)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def read(p): return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def body(text):
    if not text or "## Sheet:" not in text: return []
    b = text.split("## Sheet:", 1)[1].split("\nFormulas:", 1)[0]
    return b.split("\n")[1:]


def num(x):
    try: return float(str(x).replace(",", ""))
    except ValueError: return 0.0


def ym(y, m): return f"{MONTHS[m-1]}-{str(y)[2:]}"


def pdate(s):
    m, d, y = map(int, s.split("/")); return dt.date(y, m, d)


def pct(a, b): return None if not b else (a - b) / b * 100


def monthly(text):
    L = body(text); hdr = None; rows = []
    for ln in L:
        c = ln.split("\t")
        if hdr is None:
            if c[0].strip() == "Year month": hdr = [h.strip() for h in c]
            continue
        if len(c) >= len(hdr) - 1 and c[0].strip():
            rows.append(dict(zip(hdr, [x.strip() for x in c])))
    return rows


def pack(a):
    y, m = map(int, a.month.split("-"))
    asof = dt.date.fromisoformat(a.asof)
    mrows = monthly(read(os.path.join(a.inp, "ga4_monthly.txt")))
    if not mrows: die("ga4_monthly.txt missing or unreadable")
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    label, plabel, ylabel = f"{MONTHS[m-1]} {y}", f"{MONTHS[pm-1]} {py}", f"{MONTHS[m-1]} {y-1}"
    present = {r["Year month"] for r in mrows}
    if ym(y, m) not in present: die(f"GA4_Monthly_Channel has no rows for {label}")

    def tot(yy, mm):
        k = ym(yy, mm)
        r = [x for x in mrows if x["Year month"] == k]
        if not r: return None
        t = {"s": sum(num(x["Sessions"]) for x in r), "e": sum(num(x["Engaged sessions"]) for x in r),
             "k": sum(num(x["Key events"]) for x in r), "ch": {}}
        for x in r:
            c = t["ch"].setdefault(x["Session default channel group"], [0, 0]); c[0] += num(x["Sessions"]); c[1] += num(x["Key events"])
        return t
    cur, prev, yago = tot(y, m), tot(py, pm), tot(y - 1, m)
    gaps = ["GA4 undercounts since the cookie banner: use it for direction and page comparisons, Salesforce for MQLs, Search Console for search volume"]
    hl, lines = [], []
    ev = "Google Analytics 4, GA4_Monthly_Channel"
    ln = f"*GA4, {label}:* {cur['s']:,.0f} sessions, {cur['e']/cur['s']*100:.0f}% engaged, {cur['k']:,.0f} key events."
    if prev: ln += f" vs {plabel}: sessions {pct(cur['s'], prev['s']):+.0f}%, key events {pct(cur['k'], prev['k']):+.0f}%."
    lines.append(ln)
    if prev:
        hl.append({"id": "month", "rank": abs(pct(cur["s"], prev["s"]) or 0),
                   "text": f"GA4 sessions {cur['s']:,.0f} in {label} ({pct(cur['s'], prev['s']):+.0f}% vs {plabel}); key events {cur['k']:,.0f} ({pct(cur['k'], prev['k']):+.0f}%).",
                   "evidence": ev})
    if yago:
        lines.append(f"vs {ylabel}: sessions {yago['s']:,.0f} ({pct(cur['s'], yago['s']):+.0f}%), key events {yago['k']:,.0f} ({pct(cur['k'], yago['k']):+.0f}%).")
        hl.append({"id": "yoy", "rank": abs(pct(cur["s"], yago["s"]) or 0) / 3,
                   "text": f"GA4 sessions are {pct(cur['s'], yago['s']):+.0f}% vs {ylabel} ({cur['s']:,.0f} vs {yago['s']:,.0f}), so treat GA4 trends as unreliable until tracking is checked.",
                   "evidence": f"{ev}, {label} and {ylabel}"})
    chs = sorted(cur["ch"].items(), key=lambda kv: -kv[1][0])[:5]
    lines.append("*Channels:* " + "; ".join(f"{k} {v[0]:,.0f} sessions, {v[1]:,.0f} key events" for k, v in chs) + ".")
    # data health: GA4 organic vs Search Console clicks
    g = read(os.path.join(a.inp, "gsc_daily.txt"))
    if g:
        clicks, days = 0.0, 0
        for l in body(g):
            c = l.split("\t")
            if len(c) >= 2 and "/" in c[0]:
                d = pdate(c[0])
                if d.year == y and d.month == m: clicks += num(c[1]); days += 1
        org = cur["ch"].get("Organic Search", [0, 0])[0]
        if days == calendar.monthrange(y, m)[1] and clicks:
            r = org / clicks * 100
            lines.append(f"*Data health:* GA4 organic sessions {org:,.0f} vs Search Console clicks {clicks:,.0f} ({r:.0f}% captured). Should be near 100%; watch this rise if the banner is changed.")
            hl.append({"id": "health", "rank": max(0, 100 - r) / 2,
                       "text": f"GA4 organic sessions are {r:.0f}% of Search Console clicks in {label} ({org:,.0f} vs {clicks:,.0f}).",
                       "evidence": f"{ev}; Google Search Console, GSC_Daily"})
        else:
            gaps.append(f"Search Console covers {days} of {calendar.monthrange(y, m)[1]} days of {label}: data-health ratio left out")
    # landing pages
    L = read(os.path.join(a.inp, "ga4_landing.txt"))
    if L:
        agg = {}
        for l in body(L):
            c = l.split("\t")
            if len(c) >= 7 and c[1].strip() == ym(y, m):
                t = agg.setdefault(c[2].strip(), [0, 0, 0]); t[0] += num(c[0]); t[1] += num(c[4]); t[2] += num(c[6])
        top = sorted(agg.items(), key=lambda kv: -kv[1][0])
        if top:
            lines.append(f"*Top landing pages, {label} (GA4; the feed read keeps the highest-traffic rows):*")
            for p, v in top[:5]:
                lines.append(f"• {p} : {v[0]:,.0f} sessions, {v[1]/v[0]*100:.0f}% engaged, {v[2]:,.0f} key events")
            for p, v in top:
                if v[0] >= 50 and v[1] / v[0] < 0.3:
                    hl.append({"id": "low_engage", "rank": v[0] / 5,
                               "text": f"Landing page {p} had {v[0]:,.0f} sessions in {label} but only {v[1]/v[0]*100:.0f}% engaged: likely a tracking or redirect issue." if p == "(not set)" else
                                       f"Landing page {p} had {v[0]:,.0f} sessions in {label} with only {v[1]/v[0]*100:.0f}% engaged.",
                               "evidence": f"Google Analytics 4, GA4_Landing_Pages, {label}, page {p}"})
                elif v[0] >= 50 and v[2] == 0 and p.startswith("/resources/blog"):
                    hl.append({"id": "blog_cta", "rank": v[0] / 10,
                               "text": f"Blog page {p} had {v[0]:,.0f} sessions in {label}, {v[1]/v[0]*100:.0f}% engaged, and no key events: readers stay but nothing in the page moves them to a demo, tour or pricing.",
                               "evidence": f"Google Analytics 4, GA4_Landing_Pages, {label}, page {p}"})
                elif v[0] >= MIN_SESSIONS and v[2] == 0 and p.startswith(MONEY_PAGES):
                    hl.append({"id": "no_events", "rank": v[0] / 8,
                               "text": f"{p} had {v[0]:,.0f} sessions in {label} and no key events: a conversion-path check candidate.",
                               "evidence": f"Google Analytics 4, GA4_Landing_Pages, {label}, page {p}"})
        else:
            gaps.append(f"GA4_Landing_Pages read has no {label} rows: landing page review left out")
    else:
        gaps.append("GA4_Landing_Pages not read: landing page review left out")
    # key events, newest window the read covers
    E = read(os.path.join(a.inp, "ga4_events.txt"))
    if E:
        rows = []
        for l in body(E):
            c = l.split("\t")
            if len(c) >= 5 and "/" in c[0]: rows.append((pdate(c[0]), c[1], c[2], c[3], num(c[4])))
        if rows:
            hi = max(r[0] for r in rows); lo = min(r[0] for r in rows)
            if (hi - lo).days >= 13:
                w0 = hi - dt.timedelta(days=13)
                evc, pg = {}, {}
                for d, e, p, s, k in rows:
                    if d >= w0 and k: evc[e] = evc.get(e, 0) + k; pg[(p, e)] = pg.get((p, e), 0) + k
                lines.append(f"*Key events, {w0} to {hi} (last 14 days):* " + "; ".join(f"{e} {v:,.0f}" for e, v in sorted(evc.items(), key=lambda kv: -kv[1])[:5]) + ".")
                lines.append("Top pages for them: " + "; ".join(f"{p} ({e}) {v:,.0f}" for (p, e), v in sorted(pg.items(), key=lambda kv: -kv[1])[:3]) + ".")
            else:
                gaps.append("GA4_Key_Events read covers under 14 days: key event pages left out")
    else:
        gaps.append("GA4_Key_Events not read: key event pages left out")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    open(os.path.join(out, "00_parent.txt"), "w").write(f":globe_with_meridians: *Website, {label}* (as of {asof}; review Monday)\n{{TOP_FINDINGS}}\n" + "\n".join(lines[:2]) + "\n:warning: " + "; ".join(gaps))
    open(os.path.join(out, "01_detail.txt"), "w").write("*Detail*\n" + "\n".join(lines))
    json.dump(sorted(hl, key=lambda h: -h["rank"]), open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "highlights": len(hl), "gaps": len(gaps), "posts": 2}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
