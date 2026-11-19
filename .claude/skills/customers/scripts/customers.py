#!/usr/bin/env python3
"""Customer Marketing agent numbers. All figures come from here; the agent never computes or retypes a number.

Usage:
  customers.py --which DATE                       -> {"run": bool, "month": "YYYY-MM", "review": "YYYY-MM-DD"}  (Friday before the 4th Monday)
  customers.py --mode pack --month YYYY-MM --asof DATE --in DIR --out DIR

Input DIR/opps.json: raw Salesforce soqlQuery result (first JSON object), same fields as the ICP query (see references/queries.md).
Optional DIR/buffer_posts.json: raw Buffer list_posts result (sent posts, last 12 months) to see which customers were already featured.
Exit 2 = input missing or unreadable.
"""
import argparse, datetime as dt, json, os, re, sys

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
MIN_MONTHS = 6          # a win must be at least this old before we suggest a story
TOP_N = 8


def die(msg):
    print(msg, file=sys.stderr); sys.exit(2)


def nth_monday(y, m, n):
    d = dt.date(y, m, 1)
    d += dt.timedelta(days=(0 - d.weekday()) % 7)
    return d + dt.timedelta(weeks=n - 1)


def which(d):
    mon = nth_monday(d.year, d.month, 4)
    if d != mon - dt.timedelta(days=3): return {"run": False}
    first = mon.replace(day=1) - dt.timedelta(days=1)
    return {"run": True, "month": f"{first.year}-{first.month:02d}", "review": mon.isoformat()}


def fmt(n): return f"{n:,.0f}"


def first_json(p, what):
    if not os.path.exists(p): return None
    t = open(p, encoding="utf-8").read()
    try:
        return json.JSONDecoder().raw_decode(t[t.index("{"):])[0]
    except ValueError: die(f"{what} unreadable")


def months_between(a, b):
    return (b.year - a.year) * 12 + (b.month - a.month) - (1 if b.day < a.day else 0)


CLEARED = ("Can use name & logo", "Logo/news release approved")
NAME_ONLY = ("Mention as client only",)
ASK_FIRST = ("Approval required", "Pre-approval required")
TEST_ACCOUNTS = ("morgan test",)


def clearance(r):
    v = ((r.get("Account") or {}).get("PR_Status__c")) or ""
    if v in CLEARED: return 0, "cleared (" + v + ")"
    if v in NAME_ONLY: return 1, "name only, no logo or story"
    if v in ASK_FIRST: return 2, "approval needed first"
    if v == "Cannot use": return 9, "cannot use"
    return 3, "unknown (" + (v or "blank") + ")"


def read_names(path):
    """one 'Name | url' (url optional) per line; returns list of (name, url)"""
    if not os.path.exists(path): return None
    out = []
    for ln in open(path, encoding="utf-8").read().splitlines():
        ln = ln.strip()
        if not ln: continue
        n, _, u = ln.partition("|")
        out.append((n.strip(), u.strip()))
    return out


def site_key(name):
    n = re.sub(r",\s*[A-Za-z .]+$", "", name or "")          # drop ", CA" or ", Florida"
    n = re.sub(r"\([^)]*\)", "", n)                         # drop "(CHIP)"
    n = norm(n)
    return re.sub(r"^(city|town|village|county) of ", "", n)


def on_site(name, listing):
    """exact match on the cleaned name only, so 'Georgia Department of ...' never matches 'Macon-Bibb County, Georgia'"""
    if not listing: return None
    k = site_key(name)
    for n, u in listing:
        if site_key(n) == k: return u or "listed"
    return None


def norm(s): return re.sub(r"[^a-z0-9 ]", "", (s or "").lower().replace("&", "and")).strip()


def short(name):
    """Name without a leading 'City of' or trailing 'Department' words so 'City of Tempe' matches 'Tempe'."""
    n = norm(name)
    n = re.sub(r"^(city|county|town|state|village) of ", "", n)
    n = re.sub(r" (county|city|department|dept)( of .*)?$", "", n)
    return n if len(n) >= 5 else norm(name)


def featured(rows, posts):
    """Account name -> list of (date, text start) for Buffer posts that mention it."""
    out = {}
    for p in posts:
        text = norm(p.get("text") or "")
        d = (p.get("sentAt") or p.get("dueAt") or "")[:10]
        for r in rows:
            nm = r["_name"]
            if nm and (short(nm) in text or norm(nm) in text):
                out.setdefault(nm, []).append((d, (p.get("text") or "")[:60].replace("\n", " ")))
    return out


def pack(a):
    y, m = map(int, a.month.split("-"))
    obj = first_json(os.path.join(a.inp, "opps.json"), "opps.json")
    if not obj or "records" not in obj: die("opps.json missing or unreadable")
    asof = dt.date.fromisoformat(a.asof)
    label = f"{MONTHS[m-1]} {y}"
    won = [r for r in obj["records"] if r.get("IsWon")]
    for r in won:
        r["_close"] = dt.date.fromisoformat(r["CloseDate"])
        r["_name"] = (r.get("Account") or {}).get("Name") or "(no account)"
    newest = max((r["CloseDate"] for r in won), default="none")
    gov = [r for r in won if r.get("Market__c") == "Government"]
    com = [r for r in won if r.get("Market__c") == "Commercial"]
    gaps, hl = [], []
    # one row per account: the largest won opp
    by = {}
    for r in gov:
        if r["_name"] not in by or (r.get("Amount") or 0) > (by[r["_name"]].get("Amount") or 0): by[r["_name"]] = r
    accts = list(by.values())
    ripe = [r for r in accts if months_between(r["_close"], asof) >= MIN_MONTHS]
    young = [r for r in accts if months_between(r["_close"], asof) < MIN_MONTHS]
    prio = lambda r: 0 if r.get("Sub_Market__c") == "Local Government" else (1 if r.get("Sub_Market__c") == "State Government" else 2)
    ripe = [r for r in ripe if clearance(r)[0] < 9 and norm(r["_name"]) not in TEST_ACCOUNTS]
    stories = read_names(os.path.join(a.inp, "site_stories.txt"))
    dashes = read_names(os.path.join(a.inp, "site_dashboards.txt"))
    if stories is None: gaps.append("Website customer stories not read, so existing stories are not excluded")
    else: gaps.append("The stories page loads more on a button; only the first batch is visible to the agent")
    has_story = [r for r in ripe if on_site(r["_name"], stories)]
    ripe = [r for r in ripe if r not in has_story]
    ripe.sort(key=lambda r: (clearance(r)[0], prio(r), -(r.get("Amount") or 0)))
    # Buffer check
    posts = None
    bp = first_json(os.path.join(a.inp, "buffer_posts.json"), "buffer_posts.json")
    if bp is not None:
        posts = [{"text": (e.get("node") or {}).get("text"), "sentAt": (e.get("node") or {}).get("sentAt"), "dueAt": (e.get("node") or {}).get("dueAt")}
                 for e in bp.get("edges", [])]
        if not posts: gaps.append("Buffer returned no sent posts, so featured-before check is blank")
    else:
        gaps.append("Buffer check not run: no posts file, so we cannot tell which customers were already featured")
    feat = featured(ripe, posts) if posts else {}
    cand = ripe[:TOP_N]
    lines = [f"*Customer story candidates* (government wins closed {MIN_MONTHS}+ months ago; local government first, then state, then education and other; one per account):"]
    lines.append("Account | sub market | closed | ARR | permission (Salesforce PR status) | public dashboard | featured on LinkedIn in last 12 months")
    for r in cand:
        f = feat.get(r["_name"])
        fs = ("yes: " + f[0][0]) if f else ("no" if posts else "not checked")
        ac = r.get("Account") or {}
        dsite = on_site(r["_name"], dashes)
        dash = "yes, on site" if dsite else ("yes in Salesforce, not on site page" if ac.get("Public_Dashboard_Available__c") else "no")
        lines.append(f"• {r['_name']} | {r.get('Sub_Market__c') or 'n/a'} | {r['CloseDate']} | ${fmt(r.get('Amount') or 0)} | {clearance(r)[1]} | {dash} | {fs}")
    if len(ripe) > TOP_N: lines.append(f"({len(ripe) - TOP_N} more government wins this old are not shown.)")
    if has_story: lines.append(f"Already have a customer story on the website (left out): {', '.join(sorted(r['_name'] for r in has_story))}.")
    lines.append(f"Too new for a story (closed under {MIN_MONTHS} months ago): {len(young)} accounts.")
    lines.append(f"Commercial wins ({len(com)}) are not listed: commercial is not a story focus.")
    lines.append("Salesforce PR status is the permission source. Anything other than cleared needs Amanda's or Cristina's check with the account owner before any draft; 'cannot use' accounts are left out. This agent contacts no one.")
    ev = f"Salesforce Opportunity (New Business, Closed Won), close dates through {newest}"
    lg = [r for r in ripe if r.get("Sub_Market__c") == "Local Government"]
    if cand:
        top = cand[0]
        hl.append({"id": "top_story", "rank": 10,
                   "text": f"{top['_name']} ({top.get('Sub_Market__c')}, ${fmt(top.get('Amount') or 0)} ARR, closed {top['CloseDate']}) is the first story candidate.",
                   "evidence": ev})
    hl.append({"id": "lg_pool", "rank": 9,
               "text": f"{len(lg)} local government customers closed won 6 or more months ago, {'have no story on the website and ' if stories is not None else 'were not checked against the website stories (not read), and '}are not marked 'cannot use'; {len(ripe)} government accounts in all.",
               "evidence": ev})
    if posts:
        nf = [r for r in cand if r["_name"] not in feat]
        hl.append({"id": "not_featured", "rank": 8,
                   "text": f"{len(nf)} of the top {len(cand)} candidates have no LinkedIn post naming them in the last 12 months.",
                   "evidence": "Buffer sent posts, matched on account name"})
    out = os.path.join(a.out, "slack"); os.makedirs(out, exist_ok=True)
    head = f":handshake: *Customer story candidates, {label}* (as of {asof}; fourth-Monday review)\n{{TOP_FINDINGS}}\n" \
           f"{len(ripe)} government accounts closed {MIN_MONTHS}+ months ago; top {len(cand)} listed below." + (("\n:warning: " + "; ".join(gaps)) if gaps else "")
    open(os.path.join(out, "00_parent.txt"), "w").write(head)
    open(os.path.join(out, "01_detail.txt"), "w").write("*Detail*\n" + "\n".join(lines))
    json.dump(sorted(hl, key=lambda h: -h["rank"]), open(os.path.join(a.out, "highlights.json"), "w"), indent=1)
    print(json.dumps({"mode": "pack", "month": a.month, "candidates": len(cand), "highlights": len(hl), "gaps": gaps, "posts": 2}))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--which"); ap.add_argument("--mode"); ap.add_argument("--month"); ap.add_argument("--asof")
    ap.add_argument("--in", dest="inp"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.which: print(json.dumps(which(dt.date.fromisoformat(a.which)))); sys.exit(0)
    if a.mode == "pack": pack(a)
    else: ap.error("use --which DATE or --mode pack")
