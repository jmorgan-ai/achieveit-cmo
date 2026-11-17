#!/usr/bin/env python3
"""ops.py - Marketing Ops agent: attribution check, scorecard and performance tables.

  python3 ops.py --mode pack --part kpi|attribution --asof 2026-11-17 [--month 2026-10] --in IN --out OUT
  python3 ops.py --mode daily --asof 2026-11-17 --in IN --out OUT
  python3 ops.py --which 2026-11-17     -> {"part": "kpi"|"attribution"|null, "month": "2026-10", ...}

Inputs (captured connector results, never retyped):
  IN/opps.json    query A (pack) or D (daily)          required
  IN/osdr.json    query B (OSDR aggregate)             pack
  IN/lost_YYYY.json query C, one file per close year (this year and the two before)  required
  IN/mql.json     query E (demo/tour members by month) pack
  IN/budget.txt   Marketing Budget & Performance.xlsx sheet "2026 Spend" text   pack, optional
Outputs:
  OUT/fixes.csv           every proposed attribution fix (kept with the run; the full list is also posted in the thread)
  OUT/slack/00_parent.txt draft parent post (the agent adds the top findings)
  OUT/slack/NN_*.txt      thread posts
  OUT/highlights.json     ranked candidate findings, with numbers and evidence
  OUT/summary.json        counts for the run line
Exit 2 = input incomplete (Salesforce result not done, or a required file missing).
"""
import argparse, csv, datetime as dt, json, os, re, sys
from collections import defaultdict

SF = "https://achieveit.lightning.force.com/lightning/r/Opportunity/{}/view"
LATE = {"Proposal", "Verbal"}
WON, LOST = "5a - Closed Won", "5b - Closed Lost"
NINE_MONTHS = 270

# 2026 plan (cmo-system rulebook). Monthly = annual / 12. A new year needs a new plan here (pull request).
PLAN_YEARS = {2026}
GOALS = {
    "Non-Field": {"mqls": 525, "opps": 155, "won": 24, "arr": 720000, "budget": 244224, "cpl": 465, "cpo": 1576},
    "Field": {"mqls": 150, "opps": 60, "won": 6, "arr": 180000, "budget": 100000, "cpl": 667, "cpo": 1667},
}

# Custom Source -> channel, and the budget-sheet rows that pay for it (2026 Spend sheet labels).
CHANNELS = [
    ("Google Ads", {"Paid - Google"}, ["Google Ads"]),
    ("Microsoft Ads", {"Paid - Bing"}, ["Bing/Microsoft Advertising"]),
    ("Organic search", {"Organic - Google", "Organic - Bing"}, ["WebFX - SEO"]),
    ("Review sites", {"Referral - Capterra", "Referral - GetApp", "Referral - G2", "Referral - SoftwareSelect",
                      "Referral - Software Advice"}, ["Review Sites"]),
    ("ChatGPT / AI search", {"Referral - ChatGPT", "Referral - Perplexity", "Referral - Gemini", "Referral - Claude"}, []),
    ("Word of mouth", {"Word of Mouth"}, []),
    ("Direct", {"Direct"}, []),
    ("Webinars", {"Webinars"}, []),
]
OFFERS = [
    ("Demo request (website)", lambda c: c.startswith("Demo - ") and "Pricing" not in c),
    ("Product tour", lambda c: c.startswith("Website - Product Tour")),
    ("Pricing request", lambda c: c == "Demo - Website - Pricing"),
    ("Contact us", lambda c: c.startswith("Contact Us")),
    ("Webinar", lambda c: c.startswith("Webinar")),
]
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def die(msg):
    print("STOP: " + msg); sys.exit(2)


def load(path, required=True):
    if not os.path.exists(path):
        if required: die(f"missing input {os.path.basename(path)}")
        return None
    d = json.load(open(path))
    if not d.get("done", True): die(f"{os.path.basename(path)} is not complete (done=false); page the query")
    return d["records"]


def d8(s):  # date part of a Salesforce date or datetime
    return dt.date.fromisoformat(s[:10]) if s else None


def money(x):
    return f"${x:,.0f}"


def k(x):
    return f"${x/1000:,.0f}K" if x >= 1000 else money(x)


def pct(a, b):
    return f"{100*a/b:.0f}%" if b else "n/a"


def rate(won, lost):
    n = won + lost
    if not n: return "none closed"
    s = pct(won, n)
    return s + (" (n<5)" if n < 5 else "")


def table(header, rows):
    w = [max(len(str(r[i])) for r in [header] + rows) for i in range(len(header))]
    line = lambda r: "  ".join(str(c).ljust(w[i]) if i == 0 else str(c).rjust(w[i]) for i, c in enumerate(r))
    return "```\n" + "\n".join([line(header), line(["-" * x for x in w])] + [line(r) for r in rows]) + "\n```"


# ---------------------------------------------------------------- opp helpers
def opp(r):
    return {
        "id": r["Id"], "name": r["Name"], "account_id": r.get("AccountId"),
        "account": (r.get("Account") or {}).get("Name") or "", "owner": (r.get("Owner") or {}).get("Name") or "",
        "created": d8(r["CreatedDate"]), "close": d8(r.get("CloseDate")), "stage": r["StageName"],
        "closed": r["IsClosed"], "won": r["IsWon"], "amount": r.get("Amount") or 0.0,
        "attr": r.get("Demo_Attribution__c"), "src": r.get("Attribution_Source__c"),
        "campaign": r.get("Primary_Campaign_Source_Name__c") or "", "custom": r.get("Custom_Source__c"),
        "market": r.get("Market__c"),
    }


def non_field(o):  # rulebook: inbound new business, excluding Field Sourced
    return o["src"] == "Inbound" and o["attr"] != "Field Sourced"


def marketing_campaign(c):
    return c.startswith(("Demo - ", "Website - ", "Webinar", "Contact Us"))


def is_test(o):
    return bool(re.search(r"\btest\b", o["name"], re.I))


# ---------------------------------------------------------------- attribution rules
def check(opps, lost):
    """Return proposed fixes. One row per (opp, issue)."""
    prior = defaultdict(list)
    for r in lost:
        prior[r.get("AccountId")].append((d8(r["CloseDate"]), r.get("Demo_Attribution__c"), r["Id"], r["Name"]))
    fixes = []

    def add(o, issue, rule, proposed, evidence=""):
        fixes.append({"issue": issue, "opp": o["name"], "opp_id": o["id"], "link": SF.format(o["id"]),
                      "account": o["account"], "owner": o["owner"], "created": o["created"].isoformat(),
                      "stage": o["stage"], "attribution": o["attr"] or "", "attribution_source": o["src"] or "",
                      "campaign": o["campaign"], "custom_source": o["custom"] or "", "proposed": proposed,
                      "rule": rule, "evidence": evidence})

    for o in opps:
        if is_test(o):
            add(o, "Test record in live data", "Keep test data out of reporting", "Delete")
            continue
        # 9-month rule against the most recent lost new-business opp on the account, closed before this one was created
        before = sorted([p for p in prior.get(o["account_id"], []) if p[2] != o["id"] and p[0] and p[0] <= o["created"]],
                        reverse=True)
        p = before[0] if before else None
        reverted = False
        if p and p[1] and o["attr"] and p[1] != o["attr"]:
            days = (o["created"] - p[0]).days
            if days < NINE_MONTHS:
                add(o, "Reopened within 9 months, attribution changed",
                    "Under 9 months since the earlier opp closed lost: keep the original attribution",
                    f"Revert to {p[1]}", f"Lost opp {p[3]} ({p[2]}) closed {p[0]} as {p[1]}; {days} days before")
                reverted = True
        if p and p[1] and o["attr"] == p[1] and o["attr"] != "Marketing Sourced" and marketing_campaign(o["campaign"]):
            days = (o["created"] - p[0]).days
            if days >= NINE_MONTHS:
                add(o, "Reopened after 9 months through a marketing channel, attribution not updated",
                    "Over 9 months and a new channel: new attribution",
                    "Marketing Sourced (confirm the channel)",
                    f"Lost opp {p[3]} closed {p[0]} as {p[1]}; {days} days before; campaign {o['campaign']}")
                reverted = True
        recent_prior = p and p[0] and (o["created"] - p[0]).days < NINE_MONTHS
        if not reverted and not recent_prior:
            if o["campaign"].startswith("Webinar") and o["attr"] in ("Field Sourced", "OSDR Sourced", "AE Sourced"):
                add(o, "Webinar opp not tagged Marketing Sourced",
                    "Marketing-run events and webinars are Marketing Sourced; Field is for conferences",
                    "Marketing Sourced", f"Campaign {o['campaign']}")
            elif o["attr"] == "OSDR Sourced" and o["campaign"].startswith(("Demo - ", "Website - ", "Contact Us")):
                add(o, "OSDR Sourced but came in through the website",
                    "An inbound website request with no lost opp in the last 9 months is Marketing Sourced",
                    "Check for an earlier SalesRoads touch; if none, Marketing Sourced", f"Campaign {o['campaign']}")
        if not o["attr"]:
            sr = "SalesRoads" in o["campaign"]
            add(o, "Attribution blank", "Every opp needs an Attribution",
                "OSDR Sourced" if sr else "Owner to confirm", f"Campaign {o['campaign'] or 'none'}")
        if not o["src"] and o["attr"] and o["attr"] != "OSDR Sourced":
            prop = {"AE Sourced": "Outbound", "Partner Sourced": "Partner", "Referral": "Inbound",
                    "Marketing Sourced": "Inbound", "Upsell Growth": "Growth",
                    "Field Sourced": "Inbound if the meeting was booked at the event, else Outbound"}.get(o["attr"], "Owner to confirm")
            add(o, "Attribution Source blank", "Every opp needs Inbound, Outbound, Growth or Partner", prop)
        if o["campaign"].startswith(("Event", "Webinar")) and not o["custom"]:
            add(o, "Event or webinar opp with no Custom Source", "Custom Source should show the channel",
                "Webinars" if o["campaign"].startswith("Webinar") else "Events", f"Campaign {o['campaign']}")
        if not o["market"] and not o["closed"]:
            add(o, "Market blank on an open opp", "Needed for segment reporting", "Fill from the account")
    return fixes


# ---------------------------------------------------------------- budget sheet
def budget_rows(text, year):
    """{label: [Jan..Dec floats or None]} from the '<year> Spend' sheet text. First occurrence of each label wins."""
    tag = f"## Sheet: {year} Spend"
    if not text or tag not in text: return None
    body = text.split(tag, 1)[1].split("\n## Sheet:", 1)[0].split("\nFormulas:", 1)[0]
    rows = {}
    for line in body.splitlines():
        c = line.split("\t")
        if len(c) < 15: continue
        label = c[0].strip()
        if not label or label in rows: continue
        vals = []
        for v in c[3:15]:
            v = v.strip().replace("$", "").replace(",", "")
            if v in ("", "-"): vals.append(None); continue
            neg = v.startswith("(") and v.endswith(")")
            try: vals.append(-float(v.strip("()")) if neg else float(v))
            except ValueError: vals.append(None)
        rows[label] = vals
    return rows if "Total" in rows else None


def spend(rows, labels, months):
    """sum of the given rows over month numbers; None if any needed month is blank on the Total row"""
    if rows is None: return None
    if any(rows["Total"][m - 1] in (None, 0.0) for m in months): return None
    tot = 0.0
    for lab in labels:
        r = rows.get(lab)
        if r is None: return None
        tot += sum(r[m - 1] or 0.0 for m in months)
    return tot


# ---------------------------------------------------------------- pack
def pack(a, opps_all, osdr, lost, mql, btxt):
    asof = a.asof
    if a.month:
        y, m = map(int, a.month.split("-"))
    else:
        first = asof.replace(day=1) - dt.timedelta(days=1)
        y, m = first.year, first.month
    mstart = dt.date(y, m, 1)
    mend = (dt.date(y + (m == 12), m % 12 + 1, 1) - dt.timedelta(days=1))
    ytd = range(1, m + 1)
    label = f"{MONTHS[m-1]} {y}"
    opps = [o for o in opps_all]
    cur = [o for o in opps if o["created"].year == y]
    os.makedirs(os.path.join(a.out, "slack"), exist_ok=True)
    rows = budget_rows(btxt, y)
    if y not in PLAN_YEARS: die(f"no goals in the rulebook for {y}; update GOALS in ops.py and the cmo-system rulebook")
    highlights, gaps = [], []

    # ---- scorecard: the month, the quarter when the month ends one, and the year to date
    mq = {(int(r["y"]), int(r["m"])): int(r["d"]) for r in mql}
    q = (m - 1) // 3 + 1
    windows = [(label, [m])]
    if m % 3 == 0: windows.append((f"Q{q} {y}", [m - 2, m - 1, m]))
    windows.append((f"YTD to {MONTHS[m-1]}", list(ytd)))

    def measure(name, months):
        f = non_field if name == "Non-Field" else (lambda o: o["attr"] == "Field Sourced")
        lo = dt.date(y, months[0], 1)
        hi = dt.date(y + (months[-1] == 12), months[-1] % 12 + 1, 1) - dt.timedelta(days=1)
        inw = lambda d: d and lo <= d <= hi
        S = [o for o in opps if f(o) and not is_test(o)]
        won = [o for o in S if o["won"] and inw(o["close"])]
        return {"mqls": sum(mq.get((y, i), 0) for i in months) if name == "Non-Field" else None,
                "opps": sum(bool(inw(o["created"])) for o in S), "won": len(won), "arr": sum(o["amount"] for o in won),
                "spend": spend(rows, ["Total"] if name == "Non-Field" else ["Conferences"], months), "n": len(months),
                "late": [o for o in S if o["stage"] in LATE]}

    sc, lines = {}, []
    for s in ("Non-Field", "Field"):
        g = GOALS[s]; mg = {x: g[x] / 12 for x in g}
        W = [(lab, measure(s, ms)) for lab, ms in windows]
        def cell(v, fmt=str): return "n/a" if v is None else fmt(v)
        hdr, rws = [""], [["MQLs"], ["Opps"], ["Won deals"], ["Won ARR"], ["Spend"]]
        for lab, r in W:
            hdr += [lab, "Goal"]
            rws[0] += [cell(r["mqls"]), f"{mg['mqls']*r['n']:.0f}"]
            rws[1] += [r["opps"], f"{mg['opps']*r['n']:.0f}"]
            rws[2] += [r["won"], f"{mg['won']*r['n']:.1f}".rstrip("0").rstrip(".")]
            rws[3] += [k(r["arr"]), k(mg["arr"] * r["n"])]
            rws[4] += [cell(r["spend"], k) if r["spend"] is not None else "not entered", k(mg["budget"] * r["n"])]
        if s == "Non-Field":
            cpl, cpo = ["Cost per MQL"], ["Cost per opp"]
            for lab, r in W:
                cpl += [money(r["spend"] / r["mqls"]) if r["spend"] and r["mqls"] else "n/a", money(g["cpl"])]
                cpo += [money(r["spend"] / r["opps"]) if r["spend"] and r["opps"] else "n/a", money(g["cpo"])]
            rws += [cpl, cpo]
        late_list = W[0][1]["late"]; late = sum(o["amount"] for o in late_list)
        lines.append(f"*{s}*\n" + table(hdr, rws)
                     + f"\nLate-stage pipeline now (Proposal + Verbal): {k(late)} in {len(late_list)} opps"
                     + (" (goal over $325K)" if s == "Non-Field" else ""))
        M, Y = W[0][1], W[-1][1]
        sc[s] = {"mql_m": M["mqls"], "mql_ytd": Y["mqls"], "opps_m": M["opps"], "opps_ytd": Y["opps"],
                 "arr_m": M["arr"], "arr_y": Y["arr"], "spend_m": M["spend"], "spend_ytd": Y["spend"],
                 "late_amt": late, "late": late_list, "qtr": W[1][1] if len(W) == 3 else None}
    nf = sc["Non-Field"]
    if rows is None: gaps.append("Budget sheet not readable: spend, cost per MQL and cost per opp left out")
    elif nf["spend_m"] is None: gaps.append(f"Budget sheet has no {label} spend yet: spend figures for {label} left out")
    if rows is not None and sc["Field"]["spend_ytd"] == 0:
        gaps.append("Conference spend is $0 in the budget sheet this year, so Field cost per opp can't be measured")
    period = f"{label} and Q{q}" if m % 3 == 0 else label
    sc_text = (f":dart: *Scorecard, {period}* (Salesforce as of {asof}; spend from Marketing Budget & Performance.xlsx)\n"
               + "\n\n".join(lines)
               + "\n_MQLs = people added to a Demo or Product Tour campaign in the period (Salesforce). Opps = new business, "
                 "Attribution Source Inbound, not Field Sourced. Won = closed won in the period. Goals are the 2026 plan spread evenly by month._")
    for nm, actual, goal in [("opps", nf["opps_ytd"], GOALS["Non-Field"]["opps"] / 12 * m),
                             ("MQLs", nf["mql_ytd"], GOALS["Non-Field"]["mqls"] / 12 * m),
                             ("won ARR", nf["arr_y"], GOALS["Non-Field"]["arr"] / 12 * m)]:
        if actual is not None and goal:
            highlights.append({"kind": "pace", "metric": nm, "actual": actual, "pace_goal": round(goal), "ratio": round(actual / goal, 2),
                               "text": f"Non-Field {nm} YTD {k(actual) if nm=='won ARR' else actual} vs pace {k(goal) if nm=='won ARR' else round(goal)} ({pct(actual, goal)} of pace)",
                               "evidence": f"Salesforce, as of {asof}"})
    highlights.append({"kind": "late", "actual": nf["late_amt"], "goal": 325000,
                       "text": f"Non-Field late-stage pipeline {k(nf['late_amt'])} in {len(nf['late'])} opps vs over $325K goal",
                       "evidence": f"Salesforce opps in Proposal or Verbal, as of {asof}"})

    # ---- attribution fixes (this year's opps)
    fixes = check(cur, lost)
    osdr_blank = sum(int(r["n"]) for r in osdr if int(r["y"]) == y and r.get("Attribution_Source__c") is None)
    with open(os.path.join(a.out, "fixes.csv"), "w", newline="") as f:
        cols = ["issue", "opp", "opp_id", "link", "account", "owner", "created", "stage", "attribution",
                "attribution_source", "campaign", "custom_source", "proposed", "rule", "evidence"]
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader(); w.writerows(fixes)
    by = defaultdict(list)
    for x in fixes: by[x["issue"]].append(x)
    order = ["Reopened within 9 months, attribution changed", "Webinar opp not tagged Marketing Sourced",
             "Reopened after 9 months through a marketing channel, attribution not updated",
             "OSDR Sourced but came in through the website", "Attribution blank", "Attribution Source blank",
             "Event or webinar opp with no Custom Source", "Market blank on an open opp", "Test record in live data"]
    fl = [f":mag: *Attribution check, {y} opps* ({len(fixes)} proposed fixes for Amanda or the opp owner to confirm; nothing was changed in Salesforce)"]
    for iss in order + sorted(set(by) - set(order)):
        if iss not in by: continue
        xs = by[iss]
        names = "; ".join(f"<{x['link']}|{x['opp']}>" for x in xs[:6]) + (f"; and {len(xs)-6} more" if len(xs) > 6 else "")
        props = sorted(set(x["proposed"] for x in xs))
        fl.append(f"• *{iss} ({len(xs)})*: {names}. Fix: {props[0] if len(props) == 1 else 'see list'}.")
    if osdr_blank:
        fl.append(f"• *Attribution Source blank on OSDR opps ({osdr_blank} created in {y})*: OSDR is always Outbound. One bulk update.")
    fl.append("Every opp is listed in the next messages, one issue per message.")
    detail = []
    for iss in order + sorted(set(by) - set(order)):
        if iss not in by: continue
        xs = by[iss]
        ls = [f"• <{x['link']}|{x['opp']}> ({x['owner']}, {x['stage']}): {x['attribution'] or 'blank'} → {x['proposed']}"
              + (f". _{x['evidence']}_" if x["evidence"] else "") for x in xs]
        for i in range(0, len(ls), 30):
            part = f" (part {i//30 + 1})" if len(ls) > 30 else ""
            detail.append(f"*{iss}*{part}. Rule: {xs[0]['rule']}.\n" + "\n".join(ls[i:i + 30]))
    to_marketing = sum(len(by.get(i, [])) for i in ["Webinar opp not tagged Marketing Sourced",
                                                     "Reopened after 9 months through a marketing channel, attribution not updated"])
    if to_marketing:
        highlights.append({"kind": "attribution", "actual": to_marketing,
                           "text": f"{to_marketing} opps would move into Marketing Sourced under the written rules (webinars and channel changes after 9 months)",
                           "evidence": f"Salesforce, {y} new-business opps, as of {asof}"})

    # ---- results by attribution (created-year cohorts)
    years = [y - 1, y]
    agg = defaultdict(lambda: {"opps": 0, "won": 0, "lost": 0, "won_arr": 0.0, "open": 0.0})
    for o in opps:
        if o["attr"] == "OSDR Sourced" or is_test(o) or o["created"].year not in years: continue
        g = agg[(o["attr"] or "(blank)", o["created"].year)]
        g["opps"] += 1
        if o["won"]: g["won"] += 1; g["won_arr"] += o["amount"]
        elif o["closed"]: g["lost"] += 1
        else: g["open"] += o["amount"]
    for r in osdr:
        g = agg[("OSDR Sourced", int(r["y"]))]
        n, amt = int(r["n"]), float(r.get("amt") or 0)
        g["opps"] += n
        if r["IsWon"]: g["won"] += n; g["won_arr"] += amt
        elif r["IsClosed"]: g["lost"] += n
        else: g["open"] += amt
    attrs = ["Marketing Sourced", "OSDR Sourced", "Field Sourced", "Referral", "AE Sourced", "Partner Sourced"]
    attrs += sorted({a_ for a_, _ in agg} - set(attrs))
    tr = []
    for at in attrs:
        p_, c_ = agg[(at, y - 1)], agg[(at, y)]
        if not p_["opps"] and not c_["opps"]: continue
        tr.append([at, p_["opps"], rate(p_["won"], p_["lost"]), k(p_["won_arr"]),
                   c_["opps"], rate(c_["won"], c_["lost"]), k(c_["won_arr"]), k(c_["open"])])
    res_text = (f":bar_chart: *Results by attribution* (opps grouped by the year created; win rate = won / (won + lost))\n"
                + table(["Attribution", f"{y-1} opps", "win rate", "won ARR", f"{y} opps", "win rate", "won ARR", "open"], tr))
    ms_p, ms_c = agg[("Marketing Sourced", y - 1)], agg[("Marketing Sourced", y)]
    if ms_p["won"] + ms_p["lost"] and ms_c["won"] + ms_c["lost"]:
        highlights.append({"kind": "winrate", "prior": round(ms_p["won"] / (ms_p["won"] + ms_p["lost"]), 3),
                           "current": round(ms_c["won"] / (ms_c["won"] + ms_c["lost"]), 3), "open_pipeline": ms_c["open"],
                           "text": f"Marketing Sourced win rate {rate(ms_c['won'], ms_c['lost'])} for {y} opps vs {rate(ms_p['won'], ms_p['lost'])} for {y-1}; {k(ms_c['open'])} still open",
                           "evidence": f"Salesforce, new-business opps created {y-1} to {asof}"})

    # ---- channel economics, YTD through the review month
    ch_rows = []
    nf_ytd = [o for o in opps if non_field(o) and not is_test(o) and dt.date(y, 1, 1) <= o["created"] <= mend]
    for name, srcs, labs in CHANNELS:
        xs = [o for o in nf_ytd if o["custom"] in srcs]
        sp = spend(rows, labs, ytd) if labs else 0.0
        won_arr = sum(o["amount"] for o in xs if o["won"])
        open_ = sum(o["amount"] for o in xs if not o["closed"])
        cpo = (sp / len(xs)) if (sp and xs) else None
        ch_rows.append([name, ("not entered" if sp is None else ("$0 direct" if not labs else k(sp))), len(xs),
                        money(cpo) if cpo else ("n/a" if labs else "none"), sum(o["won"] for o in xs), k(won_arr), k(open_)])
        if labs and sp and len(xs) and sum(o["won"] for o in xs) == 0 and cpo and cpo > 2 * GOALS["Non-Field"]["cpo"]:
            highlights.append({"kind": "channel", "channel": name, "spend": sp, "opps": len(xs), "cpo": cpo,
                               "text": f"{name}: {k(sp)} spent Jan to {MONTHS[m-1]} for {len(xs)} opps ({money(cpo)} each) and no wins",
                               "evidence": f"Budget sheet rows {', '.join(labs)}; Salesforce Custom Source"})
        if not labs and open_ >= 100000:
            highlights.append({"kind": "free_channel", "channel": name, "opps": len(xs), "open": open_,
                               "text": f"{name}: {len(xs)} opps, {k(open_)} open, no direct spend",
                               "evidence": "Salesforce Custom Source"})
    other = [o for o in nf_ytd if not any(o["custom"] in s for _, s, _ in CHANNELS)]
    ch_rows.append(["Other or blank", "", len(other), "", sum(o["won"] for o in other),
                    k(sum(o["amount"] for o in other if o["won"])), k(sum(o["amount"] for o in other if not o["closed"]))])
    ch_text = (f":moneybag: *Channel economics, Jan to {MONTHS[m-1]} {y}* (Non-Field opps by Salesforce Custom Source; "
               "spend is media or fee from the budget sheet, WebFX PPC management not split)\n"
               + table(["Channel", "Spend", "Opps", "Cost/opp", "Won", "Won ARR", "Open"], ch_rows))

    # ---- offers and markets
    ms = [o for o in opps if o["attr"] in ("Marketing Sourced", "Referral") and not is_test(o) and o["created"].year in years]
    of_rows = []
    for name, fn in OFFERS + [("No campaign recorded", lambda c: c == "")]:
        xs = [o for o in ms if fn(o["campaign"])]
        if not xs: continue
        won = [o for o in xs if o["won"]]; lostn = sum(1 for o in xs if o["closed"] and not o["won"])
        days = sorted((o["close"] - o["created"]).days for o in won if o["close"])
        med = days[len(days) // 2] if days else None
        of_rows.append([name, len(xs), len(won), rate(len(won), lostn), k(sum(o["amount"] for o in won)), med if med is not None else "n/a"])
    mk_rows = []
    msrc = [o for o in opps if o["attr"] == "Marketing Sourced" and not is_test(o)]
    for mkt in ["Government", "Commercial"]:
        r_ = [mkt]
        for yy in years:
            xs = [o for o in msrc if o["market"] == mkt and o["created"].year == yy]
            w_ = sum(o["won"] for o in xs); l_ = sum(o["closed"] and not o["won"] for o in xs)
            r_ += [len(xs), rate(w_, l_), k(sum(o["amount"] for o in xs if o["won"]))]
        r_.append(k(sum(o["amount"] for o in msrc if o["market"] == mkt and o["created"].year == y and not o["closed"])))
        mk_rows.append(r_)
    com = [o for o in msrc if o["created"].year == y and o["market"] == "Commercial"]
    if com:
        highlights.append({"kind": "commercial", "actual": len(com), "of": sum(o["created"].year == y for o in msrc),
                           "text": f"{len(com)} of {sum(o['created'].year == y for o in msrc)} Marketing Sourced opps in {y} are commercial (outside the ICP)",
                           "evidence": "Salesforce Market__c"})
    of_text = (f":package: *Offers* (Marketing Sourced and Referral opps created {y-1} to date, by Primary Campaign Source)\n"
               + table(["Offer", "Opps", "Won", "Win rate", "Won ARR", "Median days to win"], of_rows)
               + f"\n*Markets* (Marketing Sourced opps)\n"
               + table(["Market", f"{y-1} opps", "win rate", "won ARR", f"{y} opps", "win rate", "won ARR", "open"], mk_rows)
               + "\n_Commercial is outside the ICP; reported on its own line until that decision is made._")

    # ---- write
    head = (f"Non-Field {label}: {nf['mql_m'] if nf['mql_m'] is not None else 'n/a'} MQLs (goal 44), {nf['opps_m']} opps (goal 13), "
            f"{k(nf['arr_m'])} won ARR (goal $60K)."
            + (f" Q{q}: {nf['qtr']['mqls']} MQLs (goal {525/4:.0f}), {nf['qtr']['opps']} opps (goal {155/4:.0f}), "
               f"{k(nf['qtr']['arr'])} won ARR (goal $180K)." if nf["qtr"] else "")
            + f" Late-stage pipeline now {k(nf['late_amt'])} (goal over $325K).")
    fix_line = (f"Attribution: {len(fixes)} opp fixes" + (f" plus one bulk update ({osdr_blank} OSDR opps with no Attribution Source)" if osdr_blank else "")
                + " proposed for Amanda.")
    if a.part == "kpi":
        parent = f":dart: *Marketing KPIs, {period}* (for the first-Monday review)\n{head}\n{{TOP_FINDINGS}}\nScorecard in thread."
        posts = {"00_parent.txt": parent, "01_scorecard.txt": sc_text}
        keep = {"pace", "late", "winrate"}
    else:
        parent = (f":mag: *Attribution and performance, {period}* (for the second-Monday review)\n{{TOP_FINDINGS}}\n{fix_line} "
                  "The fix list, results by attribution, channel economics, and offers and markets are in the thread.")
        posts = {"00_parent.txt": parent, "02_attribution.txt": "\n".join(fl)}
        for i, t in enumerate(detail): posts[f"02_attribution_{i+1:02d}.txt"] = t
        posts.update({"03_results.txt": res_text, "04_channels.txt": ch_text, "05_offers.txt": of_text})
        keep = {"winrate", "channel", "attribution", "free_channel", "commercial"}
    if gaps: posts["00_parent.txt"] += "\n:warning: " + "; ".join(gaps)
    for fn, t in posts.items():
        open(os.path.join(a.out, "slack", fn), "w").write(t + "\n")
    highlights = [h for h in highlights if h["kind"] in keep]
    order_kind = {"pace": 0, "late": 1, "winrate": 2, "channel": 3, "attribution": 4, "free_channel": 5, "commercial": 6}
    highlights.sort(key=lambda h: (order_kind.get(h["kind"], 9), h.get("ratio", 0)))
    json.dump(highlights, open(os.path.join(a.out, "highlights.json"), "w"), indent=1, default=str)
    summ = {"mode": "pack", "part": a.part, "month": f"{y}-{m:02d}", "fixes": len(fixes), "osdr_source_blank": osdr_blank,
            "nf_mqls": nf["mql_m"], "nf_opps": nf["opps_m"], "nf_arr": nf["arr_m"], "late": nf["late_amt"], "gaps": gaps,
            "posts": len(posts)}
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"), indent=1)
    print(json.dumps(summ))


# ---------------------------------------------------------------- daily
def daily(a, opps, lost):
    os.makedirs(os.path.join(a.out, "slack"), exist_ok=True)
    fixes = check(opps, lost)
    with open(os.path.join(a.out, "fixes.csv"), "w", newline="") as f:
        if fixes:
            w = csv.DictWriter(f, fieldnames=list(fixes[0])); w.writeheader(); w.writerows(fixes)
    if fixes:
        lines = [f":mag: *New opps that break an attribution rule* ({len(fixes)}; nothing was changed in Salesforce)"]
        for x in fixes[:10]:
            lines.append(f"• <{x['link']}|{x['opp']}> ({x['owner']}): {x['issue']}. Proposed: {x['proposed']}."
                         + (f" _{x['evidence']}_" if x["evidence"] else ""))
        if len(fixes) > 10: lines.append(f"…and {len(fixes)-10} more; all go into the monthly attribution pack.")
        open(os.path.join(a.out, "slack", "00_parent.txt"), "w").write("\n".join(lines) + "\n")
    summ = {"mode": "daily", "checked": len(opps), "fixes": len(fixes), "post": bool(fixes)}
    json.dump(summ, open(os.path.join(a.out, "summary.json"), "w"))
    print(json.dumps(summ))


def which(d):
    """What a run on date d should do. KPI pack: for the first Monday of the month, posted the Friday before when that
    Friday is already in the new month (the month under review is closed), otherwise on the Monday itself.
    Attribution pack: the Friday before the second Monday. Review period = last month (plus its quarter at quarter end)."""
    first = d.replace(day=1)
    mon1 = first + dt.timedelta(days=(0 - first.weekday()) % 7)
    mon2 = mon1 + dt.timedelta(days=7)
    kpi_day = mon1 - dt.timedelta(days=3) if (mon1 - dt.timedelta(days=3)).month == d.month else mon1
    att_day = mon2 - dt.timedelta(days=3)
    prev = first - dt.timedelta(days=1)
    part = "kpi" if d == kpi_day else "attribution" if d == att_day else None
    return {"date": d.isoformat(), "part": part, "month": f"{prev.year}-{prev.month:02d}", "quarter_end": prev.month % 3 == 0,
            "kpi_day": kpi_day.isoformat(), "attribution_day": att_day.isoformat()}


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--which":
        print(json.dumps(which(dt.date.fromisoformat(sys.argv[2])))); return
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["pack", "daily"], required=True)
    ap.add_argument("--asof", required=True, type=dt.date.fromisoformat)
    ap.add_argument("--month")
    ap.add_argument("--part", choices=["kpi", "attribution"], default="attribution")
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    opps = [opp(r) for r in load(os.path.join(a.inp, "opps.json"))]
    lf = sorted(f for f in os.listdir(a.inp) if re.fullmatch(r"lost_\d{4}\.json", f))
    if not lf: die("missing input lost_<year>.json")
    lost, seen = [], set()
    for f in lf:
        for r in load(os.path.join(a.inp, f)):
            if r["Id"] not in seen: seen.add(r["Id"]); lost.append(r)
    if a.mode == "daily":
        return daily(a, opps, lost)
    osdr = load(os.path.join(a.inp, "osdr.json"))
    mql = load(os.path.join(a.inp, "mql.json"))
    bp = os.path.join(a.inp, "budget.txt")
    btxt = open(bp).read() if os.path.exists(bp) else None
    pack(a, opps, osdr, lost, mql, btxt)


if __name__ == "__main__":
    main()
