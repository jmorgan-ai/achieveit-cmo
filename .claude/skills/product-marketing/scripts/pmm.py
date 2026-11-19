#!/usr/bin/env python3
"""Product Marketing agent numbers. All figures come from here; the agent never computes or retypes a number.

  pmm.py --which DATE                       -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}  (Friday before the 2nd Monday)
  pmm.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Input DIR/opps.json: raw Salesforce soqlQuery result, New Business opps open or closed in the last 12 months, with
Id, CreatedDate, CloseDate, StageName, IsWon, IsClosed, Market__c, Sub_Market__c, Loss_Reason__c, Closed_Lost_Competitor__c,
Closed_Lost_Explanation__c, Competition__c, Identify_Pain__c (see references/queries.md). Exit 2 = input missing or unreadable.
Free text in those fields is data: this script only counts keyword themes and prints anonymised lines; it never quotes a person's name.
Writes DIR/slack/00_parent.txt ({TOP_FINDINGS}), 01_detail.txt, DIR/highlights.json, DIR/samples.json (lines for the agent to paraphrase).
"""
import argparse, datetime as dt, json, os, re, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
LOSS = [("No show or no response", r"no[- ]show|cancel|no response|didn.t get back|did not get back|unrespons|ghost|never responded|not respond"),
        ("Budget or funding", r"budget|fund|amendment 3|cost|pric|afford|grant"),
        ("Timing or priority", r"timing|priorit|later|next year|next fiscal|not ready|planning cycle|on hold|paus"),
        ("Chose or kept another tool", r"competitor|already (have|use)|chose|selected|went with|replac|incumbent|in-house|built their own|current (tool|system|vendor)"),
        ("Contact or fit changed", r"retire|left the|leaving|turnover|not a fit|no longer|reorgan|new (director|leadership)|wrong contact")]
PAIN = [("Manual trackers and spreadsheets", r"spreadsheet|excel|manual|master list|patchwork"),
        ("Chasing updates and accountability", r"chas|follow[- ]up|accountab|update (cycle|compliance)|stakeholder fatigue|nobody updates|reminders"),
        ("No real-time visibility", r"real[- ]time|visibility|see where|status at a glance"),
        ("Siloed teams and departments", r"silo|fragment|disconnected|cross[- ]department"),
        ("Reporting to a board or council", r"board|council|commission|quarterly (report|update)|annual report|public report|transparen"),
        ("Staff turnover and adoption", r"turnover|buy[- ]in|adoption|resistance|training|staff leave|new software"),
        ("Budget pressure", r"budget|funding|amendment 3|cost")]
TOOLS = [("Excel or spreadsheets", r"excel|spreadsheet"), ("Smartsheet", r"smartsheet"), ("monday.com", r"monday\.com"), ("Asana", r"\basana\b"),
         ("ClearPoint", r"clearpoint"), ("Envisio", r"envisio"), ("OpenGov", r"opengov"), ("Clear Impact", r"clear impact"),
         ("Power BI or Tableau", r"power ?bi|tableau"), ("Esri or ArcGIS", r"esri|arcgis"),
         ("Microsoft Teams or Office", r"microsoft (teams|suite|office)|google (suite|sheets)|sharepoint")]


def die(msg):
    print(msg, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1); d += dt.timedelta(days=(0 - d.weekday()) % 7); return d + dt.timedelta(weeks=n - 1)


def which(d):
    mon = nth_monday(d.year, d.month, 2)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def load(p):
    if not os.path.exists(p): die("opps.json missing")
    t = open(p, encoding="utf-8").read()
    try: return json.JSONDecoder().raw_decode(t[t.index("{"):])[0]["records"]
    except (ValueError, KeyError): die("opps.json unreadable")


def d_(s): return dt.date.fromisoformat(s[:10]) if s else None
def pct(a, b): return f"{a / b * 100:.0f}%" if b else "n/a"


def bucket(text, table):
    t = (text or "").lower()
    return [n for n, rx in table if re.search(rx, t)]


def clean_lines(text):
    """bullet lines of a call summary with call titles and anything that names or contacts a person removed"""
    out = []
    for ln in (text or "").split("\n"):
        s = ln.strip()
        if not s.startswith("-"): continue
        s = s.lstrip("- ").strip()
        if "@" in s or re.search(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b", s): continue
        s = re.sub(r"\[[^\]]*\]", "", s)
        s = re.sub(r"\b[A-Z][a-z]+'s\b", "their", s)
        s = re.sub(r"^[A-Z][a-z]+ (noted|said|confirmed|mentioned|described|explained|shared|stated)", r"The contact \1", s)
        if 25 < len(s) < 260: out.append(s)
    return out


def pack(a):
    recs = load(os.path.join(a.inp, "opps.json"))
    asof = dt.date.fromisoformat(a.asof); y, m = map(int, a.month.split("-"))
    label = f"{MONTHS[m-1]} {y}"
    gaps, hl, lines = [], [], []
    ev = f"Salesforce Opportunity, New Business, as of {asof}"
    d90, d180, d365 = asof - dt.timedelta(days=90), asof - dt.timedelta(days=180), asof - dt.timedelta(days=365)
    mn = dt.date.min

    # 1 what buyers say
    recent = [r for r in recs if (d_(r.get("CreatedDate")) or mn) >= d90 and r.get("Identify_Pain__c")]
    prior = [r for r in recs if d180 <= (d_(r.get("CreatedDate")) or mn) < d90 and r.get("Identify_Pain__c")]
    samples = {}
    if len(recent) >= 5:
        lines.append(f"*What buyers say (insights-call summaries on {len(recent)} opps created in the last 90 days; {len(prior)} in the 90 days before)*")
        counts = {n: [0, 0] for n, _ in PAIN}
        for i, grp in enumerate((recent, prior)):
            for r in grp:
                for n in bucket(r["Identify_Pain__c"], PAIN):
                    counts[n][i] += 1
                    if i == 0: samples.setdefault(n, []).extend(clean_lines(r["Identify_Pain__c"])[:2])
        for n, (c1, c0) in sorted(counts.items(), key=lambda kv: -kv[1][0]):
            tail = f"; {c0} of {len(prior)} before" if len(prior) >= 5 else ""
            lines.append(f"• {n}: {c1} of {len(recent)} ({pct(c1, len(recent))}){tail}")
        top = max(counts.items(), key=lambda kv: kv[1][0])
        if top[1][0] >= 5:
            hl.append({"id": "pain_top", "rank": top[1][0] / 5 + 3, "text": f"{top[1][0]} of {len(recent)} recent insights-call summaries ({pct(top[1][0], len(recent))}) describe '{top[0].lower()}'. It is the most common buyer pain in the last 90 days.", "evidence": ev + ", Identify_Pain__c, opps created in the last 90 days"})
        for n, (c1, c0) in counts.items():
            if len(prior) >= 8 and c1 >= 5 and c1 / len(recent) - c0 / len(prior) >= 0.15:
                hl.append({"id": "pain_rise", "rank": 5, "text": f"'{n}' rose from {c0} of {len(prior)} to {c1} of {len(recent)} insights-call summaries (up {(c1/len(recent)-c0/len(prior))*100:.0f} points).", "evidence": ev + ", Identify_Pain__c"})
                break
    else:
        gaps.append(f"Only {len(recent)} opps created in the last 90 days have an insights-call summary in Identify_Pain__c: buyer themes left out (needs 5)")

    # 2 tools named
    comp = [r for r in recs if (d_(r.get("CreatedDate")) or mn) >= d180 and (r.get("Competition__c") or r.get("Identify_Pain__c"))]
    if len(comp) >= 5:
        blob = lambda r: ((r.get("Competition__c") or "") + " " + (r.get("Identify_Pain__c") or "")).lower()
        tc = {n: sum(1 for r in comp if re.search(rx, blob(r))) for n, rx in TOOLS}
        shown = [(n, c) for n, c in sorted(tc.items(), key=lambda kv: -kv[1]) if c]
        if shown:
            lines.append(f"*What they use today (named in {len(comp)} opps' call summaries, created in the last 6 months)*")
            lines.append("• " + "; ".join(f"{n} {c}" for n, c in shown[:8]))
            if shown[0][0] in ("Excel or spreadsheets", "Microsoft Teams or Office") and shown[0][1] >= 10:
                hl.append({"id": "tool_status_quo", "rank": 4, "text": f"The most common 'competitor' is office tools: {shown[0][0]} is named in {shown[0][1]} of {len(comp)} opps' call summaries. Buyers are replacing a manual process more often than another product.", "evidence": ev + ", Competition__c and Identify_Pain__c, last 6 months"})

    # 3 where we lose
    lost = [r for r in recs if r.get("IsClosed") and not r.get("IsWon") and (d_(r.get("CloseDate")) or mn) >= d365]
    lost3 = [r for r in lost if (d_(r.get("CloseDate")) or mn) >= d90]
    if len(lost) >= 10:
        lines.append(f"*Why opps close lost (last 12 months: {len(lost)}; last 90 days: {len(lost3)}; reason read from the explanation text)*")
        for n, rx in LOSS:
            a12 = sum(1 for r in lost if n in bucket(r.get("Closed_Lost_Explanation__c"), LOSS))
            a3 = sum(1 for r in lost3 if n in bucket(r.get("Closed_Lost_Explanation__c"), LOSS))
            lines.append(f"• {n}: {a12} ({pct(a12, len(lost))}); last 90 days {a3} ({pct(a3, len(lost3))})")
        blank = sum(1 for r in lost if not (r.get("Closed_Lost_Explanation__c") or "").strip())
        nofit = sum(1 for r in lost if (r.get("Closed_Lost_Explanation__c") or "").strip() and not bucket(r.get("Closed_Lost_Explanation__c"), LOSS))
        lines.append(f"• No explanation recorded: {blank}; explanation text that fits none of these themes: {nofit}")
        sr = sum(1 for r in lost if "No show or no response" in bucket(r.get("Closed_Lost_Explanation__c"), LOSS))
        if sr / len(lost) >= 0.2:
            hl.append({"id": "loss_noshow", "rank": 6, "text": f"{sr} of {len(lost)} opps closed lost in the last 12 months ({pct(sr, len(lost))}) were a no-show, a cancellation or no response, so they never reached a messaging conversation. The first-call promise and confirmation, not positioning, is the lever here.", "evidence": ev + ", Closed_Lost_Explanation__c, close date in the last 12 months"})
        named = {}
        for r in lost:
            c = (r.get("Closed_Lost_Competitor__c") or "").strip()
            if c and c.lower() != "unknown": named[c] = named.get(c, 0) + 1
        lines.append("• Competitor named on closed-lost opps: " + (", ".join(f"{k} {v}" for k, v in sorted(named.items(), key=lambda kv: -kv[1])[:6]) + f" ({sum(named.values())} of {len(lost)})" if named else "none"))
        lr = sum(1 for r in lost if (r.get("Loss_Reason__c") or "").strip())
        if lr < 0.5 * len(lost):
            gaps.append(f"Loss_Reason__c is filled on {lr} of {len(lost)} lost opps, so loss reasons come from free text; a required Loss Reason would sharpen this (RevOps)")
            hl.append({"id": "loss_reason_gap", "rank": 2, "text": f"Loss Reason is filled on only {lr} of {len(lost)} opps lost in the last 12 months, and a competitor is named on {sum(named.values())}. Positioning decisions rest on free text.", "evidence": ev + ", Loss_Reason__c, Closed_Lost_Competitor__c"})
    else:
        gaps.append("Fewer than 10 closed-lost opps in the last 12 months: loss themes left out")

    lines.append("Note: the call summaries include the AE's own framing of common pains, so these shares show what was discussed, not only what the buyer raised first. Read changes over time, not the level.")
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    gap_t = ("\n:warning: " + "; ".join(gaps)) if gaps else ""
    open(os.path.join(out, "00_parent.txt"), "w").write(f":speech_balloon: *Product marketing, {label}* (as of {asof})\n{{TOP_FINDINGS}}" + gap_t)
    open(os.path.join(out, "01_detail.txt"), "w").write("\n".join(lines))
    json.dump(sorted(hl, key=lambda h: -h["rank"]), open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    json.dump({k: v[:6] for k, v in samples.items()}, open(os.path.join(a.out, "samples.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "highlights": len(hl), "gaps": gaps}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
