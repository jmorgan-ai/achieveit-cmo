#!/usr/bin/env python3
"""Paid agent numbers (Google Ads). The agent never computes or retypes a number.

  paid.py --which DATE   -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}   (Friday before the second Monday)
  paid.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Inputs in DIR (text saved by shared/capture.py; Coefficient tabs: banner row 1, headers row 2, data row 3+):
  gads_campaign.txt   GAds_Campaign_Daily (90 days)   required
  gads_terms.txt      GAds_Search_Terms (30 days)     optional
  budget.txt          Marketing Budget & Performance.xlsx "<year> Spend" sheet text   optional
Exit 2 = a required input is missing or unreadable.
"""
import argparse, calendar, datetime as dt, importlib.util, json, os, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
BRAND = "Branded_and_Competitor"          # brand traffic is not judged on conversions
TERM_MIN_COST = 25.0                       # search term review threshold, dollars in 30 days
LOST_BUDGET = 0.40                         # average search impression share lost to budget
TIE = 0.05                                 # feed vs budget sheet tolerance


def die(m):
    print(m, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    mon = nth_monday(d.year, d.month, 2)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def table(text, first_col="Date"):
    if not text: return None
    lines = text.split("\n"); hdr = None; rows = []
    for ln in lines:
        c = ln.split("\t")
        if hdr is None:
            if c[0].strip() == first_col and len(c) >= 4: hdr = [h.strip() for h in c]
            continue
        if ln.startswith("Formulas:") or ln.startswith("## Sheet:"): break
        if len(c) >= len(hdr) - 2 and c[0].strip() and "/" in c[0]:
            rows.append(dict(zip(hdr, [x.strip() for x in c])))
    return rows


def pdate(s):
    m, d, y = map(int, s.split("/")); return dt.date(y, m, d)


def f(x):
    try: return float(str(x).replace(",", "").replace("$", ""))
    except ValueError: return 0.0


def read(p): return open(p, encoding="utf-8").read() if os.path.exists(p) else None


def money(x): return f"${x:,.0f}"


def cpc(x): return f"${x:,.2f}"


def short(c): return c.replace("AchieveIt_-_", "").replace("_", " ")


def ops_module():
    p = os.path.join(os.path.dirname(__file__), "..", "..", "marketing-ops", "scripts", "ops.py")
    spec = importlib.util.spec_from_file_location("ops", p); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m


def pack(a):
    y, m = map(int, a.month.split("-"))
    asof = dt.date.fromisoformat(a.asof)
    raw = table(read(os.path.join(a.inp, "gads_campaign.txt")))
    if not raw: die("gads_campaign.txt missing or unreadable")
    rows = [{"d": pdate(r["Date"]), "camp": r["Campaign Name"], "status": r["Campaign Status"], "imp": f(r["Impressions"]),
             "clk": f(r["Clicks"]), "cost": f(r["Cost Micros"]), "conv": f(r["Conversions"]),
             "lost": f(r["Search Budget Lost Impression Share"]) if r.get("Search Budget Lost Impression Share") else None,
             "is": f(r["Search Impression Share"]) if r.get("Search Impression Share") else None} for r in raw]
    if not rows: die("gads_campaign.txt has no rows")
    lo, hi = min(r["d"] for r in rows), max(r["d"] for r in rows)
    ms, me = dt.date(y, m, 1), dt.date(y, m, calendar.monthrange(y, m)[1])
    py, pm = (y, m - 1) if m > 1 else (y - 1, 12)
    label, plabel = f"{MONTHS[m-1]} {y}", f"{MONTHS[pm-1]} {py}"
    gaps = ["Microsoft Ads is not connected (Coefficient): Google Ads only",
            "Platform conversions are not counted as results; opps and won ARR by channel are in the Ops attribution post"]
    hl, lines = [], []

    def month(yy, mm):
        s, e = dt.date(yy, mm, 1), dt.date(yy, mm, calendar.monthrange(yy, mm)[1])
        if lo > s + dt.timedelta(days=3) or hi < e - dt.timedelta(days=3): return None
        r = [x for x in rows if s <= x["d"] <= e]
        return r or None

    cur, prev = month(y, m), month(py, pm)
    if not cur:
        die(f"Google Ads feed does not cover {label} (feed runs {lo} to {hi})")
    tc, tp = sum(x["cost"] for x in cur), sum(x["cost"] for x in prev) if prev else None
    clk = sum(x["clk"] for x in cur); imp = sum(x["imp"] for x in cur)
    ev = f"Google Ads, GAds_Campaign_Daily, {lo} to {hi}"
    head = f"*Google Ads, {label}:* {money(tc)} spend, {clk:,.0f} clicks, {cpc(tc / clk) if clk else 'n/a'} per click, {imp:,.0f} impressions."
    if tp is not None:
        ch = (tc - tp) / tp * 100 if tp else 0
        head += f" {plabel}: {money(tp)}" + (f" ({ch:+.0f}%)." if abs(ch) >= 0.5 else " (flat).")
    lines.append(head)
    # budget sheet tie-out
    try:
        ops = ops_module(); brows = ops.budget_rows(read(os.path.join(a.inp, "budget.txt")), y)
    except Exception:
        brows = None
    sheet = brows.get("Google Ads") if brows else None
    if sheet and sheet[m - 1]:
        sv = sheet[m - 1]; diff = (tc - sv) / sv
        if abs(diff) <= TIE:
            lines.append(f"Budget sheet {label} Google Ads {money(sv)}: ties to the feed.")
        else:
            lines.append(f"Budget sheet {label} Google Ads {money(sv)} vs {money(tc)} in the feed ({diff*100:+.0f}%).")
            hl.append({"id": "tie", "rank": abs(diff) * 100, "text": f"Google Ads spend is {money(tc)} in the feed but {money(sv)} on the budget sheet for {label}.",
                       "evidence": f"{ev}; Marketing Budget & Performance.xlsx {y} Spend row Google Ads"})
    else:
        gaps.append("Budget sheet Google Ads row not read for the month: no tie-out")
    # campaigns
    camps = {}
    for x in cur:
        c = camps.setdefault(x["camp"], {"cost": 0, "clk": 0, "imp": 0, "conv": 0, "lostw": 0, "lostimp": 0, "is": [], "status": x["status"]})
        c["cost"] += x["cost"]; c["clk"] += x["clk"]; c["imp"] += x["imp"]; c["conv"] += x["conv"]; c["status"] = x["status"]
        if x["lost"] is not None: c["lostw"] += x["lost"] * x["imp"]; c["lostimp"] += x["imp"]
        if x["is"] is not None: c["is"].append(x["is"])
    lines.append("*By campaign:*")
    for k, c in sorted(camps.items(), key=lambda kv: -kv[1]["cost"]):
        if c["cost"] <= 0: continue
        lost = c["lostw"] / c["lostimp"] if c["lostimp"] else None
        isv = sum(c["is"]) / len(c["is"]) if c["is"] else None
        extra = ""
        if isv is not None: extra += f", impression share {'under 10%' if isv <= 0.1 else f'{isv*100:.0f}%'}"
        if lost is not None: extra += f", {lost*100:.0f}% lost to budget"
        lines.append(f"• {short(k)}{' (paused)' if c['status'] == 'PAUSED' else ''}: {money(c['cost'])}, {c['clk']:,.0f} clicks, "
                     f"{cpc(c['cost'] / c['clk']) if c['clk'] else 'n/a'} per click{extra}")
        if lost is not None and lost >= LOST_BUDGET and k.find(BRAND) < 0 and c["status"] == "ENABLED":
            hl.append({"id": "budget_limited", "rank": lost * 100,
                       "text": f"{short(k)} loses {lost*100:.0f}% of its search impressions to budget in {label} ({money(c['cost'])} spent, {c['clk']:,.0f} clicks).",
                       "evidence": f"{ev}, campaign {k}, impression-weighted Search Budget Lost Impression Share"})
    # mix: spend share vs click share for the priciest enabled non-brand campaign
    nb = {k: c for k, c in camps.items() if BRAND not in k and c["status"] == "ENABLED" and c["clk"] > 0}
    if len(nb) >= 2 and tc > 0 and clk > 0:
        k, c = max(nb.items(), key=lambda kv: kv[1]["cost"] / kv[1]["clk"])
        acct = tc / clk
        hl.append({"id": "mix", "rank": (c["cost"] / c["clk"]) / acct * 10,
                   "text": f"{short(k)} is {c['cost']/tc*100:.0f}% of {label} spend but {c['clk']/clk*100:.0f}% of clicks at {cpc(c['cost']/c['clk'])} a click, against {cpc(acct)} across the account. Platform conversions are too few to rank campaigns on, so judge any shift on Salesforce opps by channel.",
                   "evidence": f"{ev}, campaign {k}"})
    # search terms
    terms = table(read(os.path.join(a.inp, "gads_terms.txt")))
    if terms:
        tlo, thi = min(pdate(r["Date"]) for r in terms), max(pdate(r["Date"]) for r in terms)
        agg = {}; adg = {}
        for r in terms:
            if BRAND in r["Campaign Name"]: continue
            adg[(r["Campaign Name"], r["Search Term View Search Term"])] = r.get("Ad Group Name", "")
            t = agg.setdefault((r["Campaign Name"], r["Search Term View Search Term"]), [0, 0, 0.0, 0.0])
            t[0] += f(r["Impressions"]); t[1] += f(r["Clicks"]); t[2] += f(r["Cost Micros"]); t[3] += f(r["Conversions"])
        waste = sorted([(k, v) for k, v in agg.items() if v[3] == 0 and v[2] >= TERM_MIN_COST], key=lambda kv: -kv[1][2])
        if waste:
            lines.append(f"*Search terms with {money(TERM_MIN_COST)}+ spend and no platform conversion, {tlo} to {thi} (non-brand):*")
            for (camp, term), v in waste[:5]:
                lines.append(f"• \"{term}\" {money(v[2])}, {v[1]:,.0f} clicks ({short(camp)})")
            tot = sum(v2[2] for _, v2 in waste)
            top3 = "; ".join(f"\"{t}\" {money(v2[2])} ({v2[1]:,.0f} clicks, {short(c)} / {adg[(c, t)]})" for (c, t), v2 in waste[:3])
            hl.append({"id": "terms", "rank": tot / 10,
                       "text": f"{len(waste)} non-brand search terms spent {money(tot)} with no platform conversion in {tlo} to {thi}. Biggest: {top3}.",
                       "evidence": f"Google Ads, GAds_Search_Terms, {tlo} to {thi}"})
    else:
        gaps.append("GAds_Search_Terms not read: search term review left out")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    gap_t = "\n:warning: " + "; ".join(gaps)
    open(os.path.join(out, "00_parent.txt"), "w").write(f":moneybag: *Paid, {label}* (as of {asof})\n{{TOP_FINDINGS}}\n" + "\n".join(lines[:2]) + gap_t)
    open(os.path.join(out, "01_detail.txt"), "w").write("*Detail*\n" + "\n".join(lines))
    json.dump(sorted(hl, key=lambda h: -h["rank"]), open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "spend": round(tc), "highlights": len(hl), "gaps": gaps, "posts": 2}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
