#!/usr/bin/env python3
"""Content and Social agent numbers. All figures come from here; the agent never computes or retypes a number.

  content.py --which DATE                -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}   (Friday before the 4th Monday)
  content.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Inputs in DIR (text saved byte for byte by shared/capture.py):
  li_posts.txt li_page.txt li_followers.txt buffer_posts.json   LinkedIn and Buffer (see social.py); li_posts.txt required
  gsc_pages.txt     GSC_Pages (sheet 9)                optional  content pages by clicks, impressions, position
  gsc_queries.txt   GSC_Queries (sheet 8)              optional  page-two queries to match against content pages
  ga4_landing.txt   GA4_Landing_Pages (sheet 5)        optional  sessions and key events by content page
  campaigns.json    Salesforce soqlQuery of Campaign   optional  webinars (see references/routine.md)
Writes DIR/slack/00_parent.txt, 10_content.txt, 20_social.txt (agent adds 30_drafts.txt), DIR/highlights.json. Exit 2 = LinkedIn feed missing.
"""
import importlib.util, json, os, re, sys, datetime as dt

HERE = os.path.dirname(os.path.abspath(__file__))


def _imp(path, name):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


social = _imp(os.path.join(HERE, "social.py"), "social")
seo = _imp(os.path.join(HERE, "..", "..", "seo", "scripts", "seo.py"), "seo")
MONTHS = social.MONTHS
PATHS = ("/blog/", "/resources/", "/podcast", "/webinar", "/case-studies")
PILLARS = [("Alignment", ("strategic plan", "strategy", "alignment", "goals", "objectives", "okr", "priorities", "mission")),
           ("Execution", ("execution", "implementation", "action plan", "project", "initiative", "accountability", "tracking progress", "operational plan")),
           ("Visibility", ("dashboard", "reporting", "transparency", "performance report", "metrics", "kpi", "measure"))]
STOP = {"the", "and", "for", "with", "how", "to", "of", "in", "a", "an", "your", "what", "is", "are", "best", "guide", "plan", "plans"}


def which(d):
    mon = social.nth_monday(d.year, d.month, 4)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def path(u): return re.sub(r"^https?://[^/]+", "", u or "").split("?")[0] or "/"
def is_content(u): return any(p in path(u) for p in PATHS)
def pillar(text):
    t = (text or "").lower().replace("-", " ").replace("_", " ")
    for name, kws in PILLARS:
        if any(k in t for k in kws): return name
    return None
def tokens(s): return {w for w in re.findall(r"[a-z0-9]+", s.lower().replace("-", " ")) if w not in STOP and len(w) > 2}


def content_section(a, hl, gaps):
    lines = []
    pages = seo.table(seo.read(os.path.join(a.inp, "gsc_pages.txt")))
    qs = seo.table(seo.read(os.path.join(a.inp, "gsc_queries.txt")))
    num, fmt = seo.num, seo.fmt
    cp = []
    if pages:
        cp = [p for p in pages if is_content(p.get("Page")) and num(p.get("Clicks")) is not None]
        lines.append("*Blog and content pages, last 28 days (Search Console)*")
        if not cp:
            gaps.append("No content pages found in GSC_Pages (paths: " + ", ".join(PATHS) + ")")
        for p in sorted(cp, key=lambda p: -num(p["Clicks"]))[:5]:
            lines.append(f"• {path(p['Page'])}: {fmt(num(p['Clicks']))} clicks, {fmt(num(p['Impressions']))} impressions, position {num(p['Position']):.1f}")
        # pillar spread
        spread = {}
        for p in cp:
            k = pillar(path(p["Page"])) or "Unsorted"
            s = spread.setdefault(k, [0, 0, 0]); s[0] += 1; s[1] += num(p["Clicks"]); s[2] += num(p["Impressions"])
        if spread:
            lines.append("*By pillar (keyword sort of page address)*")
            for k in [n for n, _ in PILLARS] + ["Unsorted"]:
                v = spread.get(k, [0, 0, 0])
                lines.append(f"• {k}: {v[0]} page{"" if v[0]==1 else "s"}, {fmt(v[1])} clicks, {fmt(v[2])} impressions")
            thin = [n for n, _ in PILLARS if spread.get(n, [0])[0] == 0 or spread[n][0] < max(1, 0.15 * len(cp))]
            if thin and len(cp) >= 10:
                hl.append({"id": "pillar_thin", "rank": 3, "text": f"Few or no content pages sort to the {', '.join(thin)} pillar ({len(cp)} content pages in Search Console). The page-address sort is rough, so this is a prompt for the 12/2 strategy session, not a count.",
                           "evidence": "Search Console, GSC_Pages, last 28 days; pillar keywords in references/pillars.md"})
        # content pages stuck on page two
        two = [p for p in cp if num(p.get("Position")) and 8 <= num(p["Position"]) <= 20 and num(p.get("Impressions")) and num(p["Impressions"]) >= 300]
        for p in sorted(two, key=lambda p: -num(p["Impressions"]))[:3]:
            hl.append({"id": "refresh_page", "rank": num(p["Impressions"]) / 1000 + 2,
                       "text": f"{path(p['Page'])} averages position {num(p['Position']):.1f} with {fmt(num(p['Impressions']))} impressions in 28 days and {fmt(num(p['Clicks']))} clicks: a refresh candidate to reach page one.",
                       "evidence": "Search Console, GSC_Pages, last 28 days"})
        # CTR candidates on content
        low = [p for p in cp if num(p.get("Impressions")) and num(p["Impressions"]) >= 2000 and num(p["Position"]) <= 10 and num(p["Clicks"]) / num(p["Impressions"]) < 0.01]
        for p in sorted(low, key=lambda p: -num(p["Impressions"]))[:2]:
            hl.append({"id": "content_ctr", "rank": num(p["Impressions"]) / 1000 + 1,
                       "text": f"{path(p['Page'])} ranks in the top 10 (position {num(p['Position']):.1f}) with {fmt(num(p['Impressions']))} impressions but {num(p['Clicks'])/num(p['Impressions'])*100:.2f}% CTR: a title and description rewrite.",
                       "evidence": "Search Console, GSC_Pages, last 28 days"})
    else:
        gaps.append("GSC_Pages not read: blog performance left out")
    if qs:
        sd = [q for q in qs if num(q.get("Position")) and 8 <= num(q["Position"]) <= 20 and num(q.get("Impressions")) and num(q["Impressions"]) >= 300]
        sd = sorted(sd, key=lambda q: -num(q["Impressions"]))[:6]
        if sd:
            lines.append("*Page-two searches and the content that could win them*")
        for q in sd:
            qt = tokens(q["Query"]); best, bs = None, 0
            for p in cp:
                sc = len(qt & tokens(path(p["Page"])))
                if sc > bs: best, bs = p, sc
            if best is not None and bs >= 2:
                lines.append(f"• \"{q['Query']}\" (position {num(q['Position']):.1f}, {fmt(num(q['Impressions']))} impressions): refresh {path(best['Page'])}")
            else:
                lines.append(f"• \"{q['Query']}\" (position {num(q['Position']):.1f}, {fmt(num(q['Impressions']))} impressions): no content page matches, new post candidate" + (f" ({pillar(q['Query'])} pillar)" if pillar(q['Query']) else ""))
        for q in sd[:2]:
            if not any(h["id"] == "new_post" for h in hl) and all(len(tokens(q['Query']) & tokens(path(p['Page']))) < 2 for p in cp) and cp:
                hl.append({"id": "new_post", "rank": num(q["Impressions"]) / 1000 + 1.5,
                           "text": f"\"{q['Query']}\" sits at position {num(q['Position']):.1f} with {fmt(num(q['Impressions']))} impressions and no content page matches it: a new post candidate.",
                           "evidence": "Search Console, GSC_Queries, last 28 days; page match by address words"})
    else:
        gaps.append("GSC_Queries not read: page-two content ideas left out")
    # GA4 sessions and key events on content pages
    ga = seo.table(seo.read(os.path.join(a.inp, "ga4_landing.txt")))
    if ga and "Landing page" in (ga[0] if ga else {}):
        mrows = [r for r in ga if is_content(r.get("Landing page"))]
        if mrows:
            agg = {}
            for r in mrows:
                v = agg.setdefault(r["Landing page"], [0, 0]); v[0] += num(r.get("Sessions")) or 0; v[1] += num(r.get("Key events")) or 0
            top = sorted(agg.items(), key=lambda kv: -kv[1][0])[:3]
            lines.append("*Content pages as a landing page (GA4; undercounts, use for relative size only)*")
            for p, v in top: lines.append(f"• {p}: {fmt(v[0])} sessions, {fmt(v[1])} key events")
    return lines


def webinars(a, gaps):
    p = os.path.join(a.inp, "campaigns.json")
    if not os.path.exists(p): gaps.append("Webinar campaigns not read from Salesforce"); return []
    t = open(p, encoding="utf-8").read()
    try:
        recs = json.JSONDecoder().raw_decode(t[t.index("{"):])[0]["records"]
    except (ValueError, KeyError):
        gaps.append("Webinar campaigns unreadable"); return []
    out = ["*Webinars and events (Salesforce campaigns, last 12 months)*"]
    rows = sorted(recs, key=lambda r: r.get("StartDate") or "", reverse=True)[:5]
    if not rows: return []
    for r in rows:
        out.append(f"• {r.get('Name')} ({r.get('StartDate') or 'no date'}): {r.get('NumberOfContacts') or 0} contacts, {r.get('NumberOfLeads') or 0} leads, "
                   f"{r.get('NumberOfResponses') or 0} responses, {r.get('NumberOfOpportunities') or 0} opps")
    out.append("Attendance and opps come from the campaign fields as Salesforce holds them; a webinar's opps are attributed by the Attribution rules, not by this count.")
    return out


def pack(a):
    hl, gaps = [], []
    social.pack(a)                                            # writes 20_social.txt, highlights_social.json; exits 2 itself if li_posts missing
    shl = json.load(open(os.path.join(a.out, "highlights_social.json")))
    gaps += [g for g in getattr(a, "social_gaps", [])]
    label = getattr(a, "social_label", a.month)
    cl = content_section(a, hl, gaps)
    wl = webinars(a, gaps)
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    gap_t = ("\n:warning: " + "; ".join(g for g in gaps if "LinkedIn feed captions" not in g and "Buffer has no click" not in g)) if gaps else ""
    open(os.path.join(out, "00_parent.txt"), "w").write(f":writing_hand: *Content and social, {label}* (as of {a.asof})\n{{TOP_FINDINGS}}" + gap_t)
    open(os.path.join(out, "10_content.txt"), "w").write("\n".join(cl + ([""] if cl and wl else []) + wl))
    allhl = sorted(hl + shl, key=lambda h: -h["rank"])
    json.dump(allhl, open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "highlights": len(allhl), "gaps": gaps, "files": sorted(os.listdir(out))}))


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
