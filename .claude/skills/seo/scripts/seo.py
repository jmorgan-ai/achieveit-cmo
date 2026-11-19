#!/usr/bin/env python3
"""SEO agent numbers. All figures come from here; the agent never computes or retypes a number.

Usage:
  seo.py --which DATE                       -> {"run": true|false, "month": "YYYY-MM", "quarter_end": bool, "review": "YYYY-MM-DD"}
  seo.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Inputs in DIR (text saved byte for byte by shared/capture.py; Coefficient tabs: banner row 1, headers row 2, data row 3+):
  gsc_daily.txt    Marketing Data Feeds.xlsx GSC_Daily (90 days)            required
  gsc_pages.txt    GSC_Pages (last 28 days)                                  optional
  gsc_queries.txt  GSC_Queries page 1 (sorted by impressions, last 28 days)  optional
  ga4_monthly.txt  GA4_Monthly_Channel                                       optional
  feed_status.txt  Feed_Status                                               optional
  audit_info.json  Semrush site_audit info (project 23016017)                optional
  pt_overview.json Semrush tracking_overview_organic                         optional
Exit 2 = a required input is missing or unreadable; message on stderr.
"""
import argparse, calendar, datetime as dt, json, os, re, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def die(msg):
    print(msg, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    """Run the SEO pack on the Friday before the third Monday; covers the month before that Monday."""
    mon = nth_monday(d.year, d.month, 3)
    fri = mon - dt.timedelta(days=3)
    if d != fri: return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "quarter_end": first.month % 3 == 0,
            "review": mon.isoformat()}


def table(text, tab_hint=None):
    """rows (list of dicts) from a captured Coefficient tab."""
    if not text: return None
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        c = ln.split("\t")
        if len(c) >= 3 and c[0].strip() in ("Date", "Page", "Page (1)", "Query", "Year month", "Tab"):
            hdr = [h.strip() for h in c]
            rows = []
            for l2 in lines[i + 1:]:
                if l2.startswith("Formulas:") or l2.startswith("## Sheet:"): break
                v = l2.split("\t")
                if len(v) < 3 or not v[0].strip() or v[0].startswith("["): continue
                rows.append(dict(zip(hdr, [x.strip() for x in v])))
            return rows
    return None


def num(x):
    try: return float(str(x).replace(",", "").replace("$", ""))
    except ValueError: return None


def pdate(s):
    m, d, y = map(int, s.split("/")); return dt.date(y, m, d)


def read(p):
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def agg(daily, y, m):
    """clicks, impressions, impression-weighted position, days with data for a calendar month"""
    r = [x for x in daily if x["_d"].year == y and x["_d"].month == m]
    if not r: return None
    imp = sum(x["_i"] for x in r)
    return {"clicks": sum(x["_c"] for x in r), "imp": imp, "days": len(r),
            "pos": sum(x["_p"] * x["_i"] for x in r) / imp if imp else None}


def qpage(q):
    """GSC_Queries puts the page in column A (header 'Page (1)'); a blank 'Page' column trails the row"""
    return q.get("Page (1)") or q.get("Page") or ""


def pct(a, b):
    return None if not b else (a - b) / b * 100


def fmt(n): return f"{n:,.0f}"


def pack(a):
    y, m = map(int, a.month.split("-"))
    asof = dt.date.fromisoformat(a.asof)
    raw = table(read(os.path.join(a.inp, "gsc_daily.txt")))
    if not raw: die("gsc_daily.txt missing or unreadable")
    daily = []
    for r in raw:
        try:
            daily.append({"_d": pdate(r["Date"]), "_c": num(r["Clicks"]), "_i": num(r["Impressions"]), "_p": num(r["Position"])})
        except (KeyError, ValueError): continue
    if not daily: die("gsc_daily.txt has no rows")
    newest = max(x["_d"] for x in daily)
    gaps, hl, lines = [], [], []
    cur = agg(daily, y, m)
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    prev = agg(daily, py, pm)
    label = f"{MONTHS[m-1]} {y}"
    dim = calendar.monthrange(y, m)[1]
    if not cur or cur["days"] < dim:
        gaps.append(f"Search Console data covers {cur['days'] if cur else 0} of {dim} days of {label}: month totals left out")
        cur = None
    pl = f"{MONTHS[pm-1]} {py}"
    if prev and prev["days"] < calendar.monthrange(py, pm)[1]:
        gaps.append(f"Search Console data covers only part of {pl} (feed keeps 90 days): no month-over-month comparison")
        prev = None
    ev = f"Google Search Console, GSC_Daily, newest day {newest}"
    if cur:
        lines.append(f"*Search Console, {label}:* {fmt(cur['clicks'])} clicks, {fmt(cur['imp'])} impressions, "
                     f"average position {cur['pos']:.1f}.")
        if prev:
            dc, di, dp = pct(cur["clicks"], prev["clicks"]), pct(cur["imp"], prev["imp"]), cur["pos"] - prev["pos"]
            lines.append(f"vs {pl}: clicks {dc:+.0f}%, impressions {di:+.0f}%, position {dp:+.1f} (lower is better).")
            hl_text = (f"Search clicks {fmt(cur['clicks'])} in {label} ({dc:+.0f}% vs {pl}); impressions {fmt(cur['imp'])} "
                       f"({di:+.0f}%); average position {cur['pos']:.1f} ({dp:+.1f}).")
            hl.append({"id": "gsc_month", "rank": abs(dc), "text": hl_text, "evidence": ev,
                       "numbers": {"clicks": cur["clicks"], "imp": cur["imp"], "pos": round(cur["pos"], 1)}})
    # trailing months available in the 90-day feed
    ms = sorted({(x["_d"].year, x["_d"].month) for x in daily})
    tr = []
    for (yy, mm) in ms:
        g = agg(daily, yy, mm)
        if g["days"] >= calendar.monthrange(yy, mm)[1]:
            tr.append(f"{MONTHS[mm-1]} {fmt(g['clicks'])} clicks / {fmt(g['imp'])} imp / pos {g['pos']:.1f}")
    if tr: lines.append("Full months in the feed: " + "; ".join(tr) + ".")
    # last 7 days vs the 7 before
    l7 = [x for x in daily if newest - dt.timedelta(days=6) <= x["_d"] <= newest]
    p7 = [x for x in daily if newest - dt.timedelta(days=13) <= x["_d"] <= newest - dt.timedelta(days=7)]
    if len(l7) == 7 and len(p7) == 7:
        c1, c0 = sum(x["_c"] for x in l7), sum(x["_c"] for x in p7)
        lines.append(f"Last 7 days to {newest}: {fmt(c1)} clicks vs {fmt(c0)} the 7 days before ({pct(c1, c0):+.0f}%).")
    # pages
    pages = table(read(os.path.join(a.inp, "gsc_pages.txt")))
    if pages:
        pr = sorted([p for p in pages if num(p.get("Clicks")) is not None], key=lambda p: -num(p["Clicks"]))[:5]
        lines.append("*Top pages, last 28 days (Search Console):*")
        for p in pr:
            lines.append(f"• {p['Page'].replace('https://www.achieveit.com','')} : {fmt(num(p['Clicks']))} clicks, "
                         f"{fmt(num(p['Impressions']))} imp, pos {num(p['Position']):.1f}")
        # high impressions, very low CTR, ranking top 10
        low = [p for p in pages if num(p.get("Impressions")) and num(p["Impressions"]) >= 5000 and num(p["Position"]) <= 10
               and num(p["Clicks"]) / num(p["Impressions"]) < 0.005]
        for p in sorted(low, key=lambda p: -num(p["Impressions"]))[:3]:
            ctr = num(p["Clicks"]) / num(p["Impressions"]) * 100
            hl.append({"id": "low_ctr", "rank": num(p["Impressions"]) / 1000,
                       "text": f"{p['Page']} ranks in the top 10 (pos {num(p['Position']):.1f}) with {fmt(num(p['Impressions']))} "
                               f"impressions but only {ctr:.2f}% CTR ({fmt(num(p['Clicks']))} clicks): a title and description rewrite candidate.",
                       "evidence": f"Google Search Console, GSC_Pages (last 28 days), page {p['Page']}"})
    else:
        gaps.append("GSC_Pages not read: top pages and CTR candidates left out")
    # queries: striking distance (position 8-20, impressions high)
    qs = table(read(os.path.join(a.inp, "gsc_queries.txt")))
    if qs:
        sd = [q for q in qs if num(q.get("Position")) and 8 <= num(q["Position"]) <= 20 and num(q.get("Impressions")) and num(q["Impressions"]) >= 300]
        sd = sorted(sd, key=lambda q: -num(q["Impressions"]))[:5]
        if sd:
            lines.append("*Page-two opportunities (position 8 to 20, 28 days):*")
            for q in sd:
                lines.append(f"• \"{q['Query']}\" pos {num(q['Position']):.1f}, {fmt(num(q['Impressions']))} imp, {fmt(num(q['Clicks']))} clicks "
                             f"({qpage(q).replace('https://www.achieveit.com','')})")
            q = sd[0]
            hl.append({"id": "striking", "rank": num(q["Impressions"]) / 1000,
                       "text": f"\"{q['Query']}\" sits at position {num(q['Position']):.1f} with {fmt(num(q['Impressions']))} impressions in 28 days "
                               f"on {qpage(q)}: the closest query to page one.",
                       "evidence": "Google Search Console, GSC_Queries (last 28 days)"})
    else:
        gaps.append("GSC_Queries not read: page-two opportunities left out")
    # GA4 vs GSC organic
    g4 = table(read(os.path.join(a.inp, "ga4_monthly.txt")))
    if g4 and cur:
        ym = f"{y}{m:02d}"
        def org(ymv):
            return sum(num(r.get("Sessions")) or 0 for r in g4 if r.get("Year month", "").replace("-", "") == ymv
                       and r.get("Session default channel group", "").lower() == "organic search")
        o_now, o_prev = org(ym), org(f"{py}{pm:02d}")
        if o_now and o_prev:
            lines.append(f"GA4 organic search sessions: {fmt(o_now)} in {label} vs {fmt(o_prev)} in {pl} ({pct(o_now, o_prev):+.0f}%). "
                         "GA4 undercounts since the cookie banner; use Search Console for search volume.")
    gaps.append("GA4 organic is undercounted by the cookie banner (known cause: the cookie banner; Jonathan is working on the banner setting, so use Search Console for search volume until then)")
    # Semrush
    ai = read(os.path.join(a.inp, "audit_info.json"))
    if ai:
        try:
            d = json.loads(ai)["data"]
            when = dt.datetime.fromtimestamp(d["last_audit"] / 1000, dt.timezone.utc).date()
            lines.append(f"*Site audit (Semrush, {when}):* {d['errors']} errors ({d['errors_delta']:+d} vs previous crawl), "
                         f"{d['warnings']:,} warnings ({d['warnings_delta']:+,}), {d['notices']:,} notices; {d['pages_crawled']:,} pages crawled; "
                         f"{d['broken']} broken, {d['blocked']} blocked.")
            if d["errors_delta"] > 0:
                hl.append({"id": "audit_errors", "rank": d["errors_delta"],
                           "text": f"Site audit errors rose by {d['errors_delta']} to {d['errors']}.",
                           "evidence": f"Semrush site audit project 23016017, crawl {when}"})
            if d["warnings_delta"] > 500:
                hl.append({"id": "audit_warnings", "rank": d["warnings_delta"] / 100,
                           "text": f"Site audit warnings rose by {d['warnings_delta']:,} to {d['warnings']:,} in one crawl (check what changed before treating it as real).",
                           "evidence": f"Semrush site audit project 23016017, crawl {when}"})
        except (KeyError, ValueError):
            gaps.append("Semrush site audit result unreadable: site health left out")
    else:
        gaps.append("Semrush site audit not read: site health left out")
    pt = read(os.path.join(a.inp, "pt_overview.json"))
    if pt:
        lines.append("*Rank tracking (Semrush, 21 keywords):* see thread.")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    gap_t = ("\n:warning: " + "; ".join(gaps)) if gaps else ""
    head = f":mag: *SEO, {label}* (as of {asof}; review Monday)\n{{TOP_FINDINGS}}\n" + "\n".join(lines[:3]) + gap_t
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
