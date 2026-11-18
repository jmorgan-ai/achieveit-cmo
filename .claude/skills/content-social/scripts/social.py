#!/usr/bin/env python3
"""Content and Social agent numbers. All figures come from here; the agent never computes or retypes a number.

Usage:
  social.py --which DATE                       -> {"run": true|false, "month": "YYYY-MM", "quarter_end": bool, "review": "YYYY-MM-DD"}
  social.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Inputs in DIR (text saved byte for byte by shared/capture.py; Coefficient tabs: banner row 1, headers row 2, data row 3+):
  li_posts.txt      Marketing Data Feeds.xlsx LI_Posts (every post, captions cut at 25 characters)  required
  li_page.txt       LI_Page_Daily (about 90 days)                                                    optional
  li_followers.txt  LI_Followers (about 90 days)                                                     optional
  feed_status.txt   Feed_Status                                                                      optional
Exit 2 = a required input is missing or unreadable; message on stderr.
"""
import argparse, calendar, datetime as dt, json, os, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def die(msg):
    print(msg, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    """Run on the Friday before the fourth Monday; covers the month before that Monday."""
    mon = nth_monday(d.year, d.month, 4)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "quarter_end": first.month % 3 == 0,
            "review": mon.isoformat()}


def table(text, keys):
    if not text: return None
    lines = text.split("\n")
    for i, ln in enumerate(lines):
        c = [x.strip() for x in ln.split("\t")]
        if len(c) >= 3 and c[0] in keys:
            rows = []
            for l2 in lines[i + 1:]:
                if l2.startswith("Formulas:") or l2.startswith("## Sheet:"): break
                v = l2.split("\t")
                if len(v) < 3 or not v[0].strip(): continue
                rows.append(dict(zip(c, [x.strip() for x in v])))
            return rows
    return None


def num(x):
    try: return float(str(x).replace(",", ""))
    except ValueError: return 0.0


def pdt(s):
    d, t = (s.split(" ") + ["0:00"])[:2]
    m, dd, y = map(int, d.split("/")); return dt.date(y, m, dd)


def read(p):
    return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def fmt(n): return f"{n:,.0f}"


def pct(a, b): return None if not b else (a - b) / b * 100


def month_stats(posts, y, m):
    r = [p for p in posts if p["d"].year == y and p["d"].month == m]
    if not r: return None
    imp = sum(p["imp"] for p in r)
    act = sum(p["clk"] + p["lik"] + p["com"] + p["shr"] for p in r)
    return {"n": len(r), "imp": imp, "clk": sum(p["clk"] for p in r), "lik": sum(p["lik"] for p in r),
            "com": sum(p["com"] for p in r), "shr": sum(p["shr"] for p in r), "act": act,
            "er": act / imp * 100 if imp else None, "ctr": sum(p["clk"] for p in r) / imp * 100 if imp else None,
            "med": sorted(p["imp"] for p in r)[len(r) // 2], "posts": r}


def pack(a):
    y, m = map(int, a.month.split("-"))
    asof = dt.date.fromisoformat(a.asof)
    raw = table(read(os.path.join(a.inp, "li_posts.txt")), ("Published At",))
    if not raw: die("li_posts.txt missing or unreadable")
    posts = []
    for r in raw:
        try:
            posts.append({"d": pdt(r["Published At"]), "cap": r["Post Caption"], "imp": num(r["Impression Count"]),
                          "clk": num(r["Click Count"]), "lik": num(r["Like Count"]), "com": num(r["Comment Count"]),
                          "shr": num(r["Share Count"])})
        except (KeyError, ValueError): continue
    if not posts: die("li_posts.txt has no rows")
    newest = max(p["d"] for p in posts)
    gaps, hl, lines = [], [], []
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    label, pl = f"{MONTHS[m-1]} {y}", f"{MONTHS[pm-1]} {py}"
    cur, prev = month_stats(posts, y, m), month_stats(posts, py, pm)
    ev = f"LinkedIn Pages, LI_Posts, newest post {newest}"
    if not cur:
        gaps.append(f"No LinkedIn posts found in {label}")
    else:
        lines.append(f"*Posts, {label}:* {cur['n']} posts, {fmt(cur['imp'])} impressions (median {fmt(cur['med'])} per post), "
                     f"{fmt(cur['clk'])} clicks, {fmt(cur['lik'])} reactions, {fmt(cur['com'])} comments, {fmt(cur['shr'])} shares.")
        lines.append(f"Engagement rate {cur['er']:.1f}% (clicks, reactions, comments and shares over impressions, recomputed), "
                     f"click rate {cur['ctr']:.1f}%.")
        if prev:
            di, dn = pct(cur["imp"], prev["imp"]), cur["n"] - prev["n"]
            lines.append(f"vs {pl}: {prev['n']} posts ({dn:+d}), impressions {di:+.0f}%, engagement rate {prev['er']:.1f}%, "
                         f"click rate {prev['ctr']:.1f}%.")
            hl.append({"id": "li_month", "rank": abs(di),
                       "text": f"LinkedIn posts drew {fmt(cur['imp'])} impressions in {label} ({di:+.0f}% vs {pl}) from {cur['n']} posts; "
                               f"engagement rate {cur['er']:.1f}% vs {prev['er']:.1f}%.", "evidence": ev})
        tr = []
        for (yy, mm) in sorted({(p["d"].year, p["d"].month) for p in posts}):
            if (yy, mm) > (y, m) or (yy, mm) < ((y, m - 5) if m > 5 else (y - 1, m + 7)): continue
            g = month_stats(posts, yy, mm)
            tr.append(f"{MONTHS[mm-1]} {g['n']} posts / {fmt(g['imp'])} imp / {g['er']:.1f}%")
        if tr: lines.append("Trailing 6 months: " + "; ".join(tr) + ".")
        top = sorted(cur["posts"], key=lambda p: -p["imp"])[:3]
        lines.append("*Top posts by impressions:*")
        for p in top:
            lines.append(f"• {p['d']}: \"{p['cap']}\" {fmt(p['imp'])} imp, {fmt(p['clk'])} clicks, "
                         f"{fmt(p['lik'] + p['com'] + p['shr'])} reactions, comments and shares")
        t = top[0]
        hl.append({"id": "li_top", "rank": t["imp"] / 100,
                   "text": f"Top post of {label} ({t['d']}, \"{t['cap']}\") reached {fmt(t['imp'])} impressions against a median of "
                           f"{fmt(cur['med'])}.", "evidence": f"{ev}; post published {t['d']}"})
        clk = sorted(cur["posts"], key=lambda p: -p["clk"])[:1]
        if clk and clk[0]["clk"] >= 10 and clk[0] is not t:
            c = clk[0]
            lines.append(f"Most clicks: {c['d']}, \"{c['cap']}\" with {fmt(c['clk'])} clicks on {fmt(c['imp'])} impressions.")
            hl.append({"id": "li_clicks", "rank": c["clk"],
                       "text": f"The post of {c['d']} (\"{c['cap']}\") earned the most clicks, {fmt(c['clk'])}, "
                               f"{c['clk'] / c['imp'] * 100:.1f}% of its impressions.", "evidence": f"{ev}; post published {c['d']}"})
        nocap = [p for p in cur["posts"] if p["cap"].lower().startswith("no caption")]
        if nocap: lines.append(f"{len(nocap)} post(s) show no caption in the feed (the feed may not carry the text).")
        wk = sorted({p["d"] for p in cur["posts"]})
        quiet = [d for d in (dt.date(y, m, 1) + dt.timedelta(days=i) for i in range(calendar.monthrange(y, m)[1]))
                 if d.weekday() < 5 and d not in wk]
        if quiet: lines.append(f"Weekdays with no post: {len(quiet)} of {sum(1 for i in range(calendar.monthrange(y, m)[1]) if (dt.date(y, m, 1) + dt.timedelta(days=i)).weekday() < 5)}.")
    # followers
    fol = table(read(os.path.join(a.inp, "li_followers.txt")), ("Date",))
    if fol:
        def fsum(yy, mm):
            r = [x for x in fol if pdt(x["Date"]).year == yy and pdt(x["Date"]).month == mm]
            return (len(r), sum(num(x["Organic Followers Gained"]) for x in r), sum(num(x["Paid Followers Gained"]) for x in r)) if r else None
        f1, f0 = fsum(y, m), fsum(py, pm)
        dim = calendar.monthrange(y, m)[1]
        if f1 and f1[0] >= dim:
            lines.append(f"*Followers:* net organic {f1[1]:+.0f} in {label}" + (f" ({f0[1]:+.0f} in {pl})" if f0 and f0[0] >= calendar.monthrange(py, pm)[1] else "") +
                         f"; paid {f1[2]:+.0f}. The feed gives gains only, not the total.")
            hl.append({"id": "li_followers", "rank": 5,
                       "text": f"Net organic followers {f1[1]:+.0f} in {label} while the page posted {cur['n'] if cur else 0} times.",
                       "evidence": f"LinkedIn Pages, LI_Followers, {label}"})
        else:
            gaps.append(f"LI_Followers covers part of {label}: follower change left out")
    else:
        gaps.append("LI_Followers not read: follower change left out")
    pg = table(read(os.path.join(a.inp, "li_page.txt")), ("Date",))
    if pg:
        def psum(yy, mm):
            r = [x for x in pg if pdt(x["Date"]).year == yy and pdt(x["Date"]).month == mm]
            if not r: return None
            return {"days": len(r), "v": sum(num(x["All Page Views"]) for x in r), "u": sum(num(x["Unique All Page Views"]) for x in r),
                    "prod": sum(num(x["Products Page Views"]) for x in r)}
        p1, p0 = psum(y, m), psum(py, pm)
        if p1 and p1["days"] >= calendar.monthrange(y, m)[1]:
            s = f"*Company page:* {fmt(p1['v'])} page views, {fmt(p1['u'])} unique (daily uniques summed), {fmt(p1['prod'])} on the Products tab"
            if p0 and p0["days"] >= calendar.monthrange(py, pm)[1]:
                s += f"; {pl}: {fmt(p0['v'])} views ({pct(p1['v'], p0['v']):+.0f}%)"
            lines.append(s + ". Custom button clicks: none recorded.")
        else:
            gaps.append(f"LI_Page_Daily covers part of {label}: page views left out")
    else:
        gaps.append("LI_Page_Daily not read: page views left out")
    gaps.append("LinkedIn captions are cut at 25 characters and post type (image, video, link) is not in the feed; themes are judged from the full posts by Cristina and Amanda")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    gap_t = ("\n:warning: " + "; ".join(gaps)) if gaps else ""
    head = f":speech_balloon: *Social and brand, {label}* (as of {asof}; review Monday)\n{{TOP_FINDINGS}}\n" + "\n".join(lines[:2]) + gap_t
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
