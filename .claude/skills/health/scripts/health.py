#!/usr/bin/env python3
"""Health check numbers. Which posts were due, which tasks failed, which feeds are stale: all decided here.

  health.py check --asof DATE --channel FILE [--triggers FILE] [--feeds FILE] [--known known.json] --out DIR
     channel  = saved Slack read of #marketing-cmo (last 2 days); with --threads DIR, replies saved there as thread_<ts>.json count too
     triggers = saved list_triggers result (scheduled tasks, with last_run)
     feeds    = saved read of Feed_Status (sheet 2)
     known    = optional JSON list of keys already on the open items log, e.g. ["data-msads-feed"]
  Writes DIR/health.json, DIR/post.txt (empty when everything is fine and it is not Monday), DIR/rerun.json (plan only).
Exit 2 = channel input unreadable.
"""
import argparse, datetime as dt, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
TASKS = {  # scheduled task name -> trigger id
    "Marketing Ops": "trig_01K2Xx1kTeSjPvQ6H9iStoj6", "SEO - Friday pack": "trig_01T6ScY3MofkEeQVWSmW14ZU",
    "PM - Monday note": "trig_013jSdfYdyKM3saKXfXLWnH6", "Paid - Friday pack": "trig_01MuJd79dgwF5fEckbz2FcCF",
    "Website - Friday pack": "trig_01Wv98FKuWvx6acfjtzRqy9a", "Content - Friday pack": "trig_01YY7gN6FCwsWHf348ztUdCZ",
    "CMO - Monday brief": "trig_01B4T3M1pR5pX84YrnMJjmGx", "Product Marketing - Friday pack": "trig_01Xcki5iUQewftM8ryrjyZQN",
    "Customers - Friday pack": "trig_01DJKGsXR3Ev2v3uyJZei4KF"}
# agent label -> (text its post starts with, scheduled task that makes it)
POSTS = {"Ops KPI pack": ("*Marketing KPIs", "Marketing Ops"), "Ops attribution pack": ("*Attribution and performance", "Marketing Ops"),
         "Paid pack": ("*Paid,", "Paid - Friday pack"), "Product marketing pack": ("*Product marketing,", "Product Marketing - Friday pack"),
         "SEO pack": ("*SEO,", "SEO - Friday pack"), "Website pack": ("*Website,", "Website - Friday pack"),
         "Content pack": ("*Content and social,", "Content - Friday pack"), "Customers pack": ("*Customer story candidates", "Customers - Friday pack"),
         "PM note": ("*Marketing, week of", "PM - Monday note"), "CMO brief": ("*CMO brief", "CMO - Monday brief")}
FRIDAY_PACKS = {1: ["Ops KPI pack"], 2: ["Ops attribution pack", "Paid pack", "Product marketing pack"], 3: ["SEO pack", "Website pack"], 4: ["Content pack", "Customers pack"]}
KNOWN_FEED_KEYS = {"MSAds_Campaign_Daily": "data-msads-feed", "MSAds_Search_Query": "data-msads-feed"}


def _imp(rel):
    spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, rel)); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def nth_monday(y, m, n):
    d = dt.date(y, m, 1); d += dt.timedelta(days=(0 - d.weekday()) % 7); return d + dt.timedelta(weeks=n - 1)


def due_today(d):
    """posts that should exist for date d (after their scheduled slot). KPI pack day: see marketing-ops which(); Ops daily is silent when clean, so not expected."""
    out = []
    if d.weekday() == 0:
        out += ["PM note", "CMO brief"]
    if d.weekday() == 4:
        mon = d + dt.timedelta(days=3)
        if mon.day <= 28 and (mon.day - 1) // 7 + 1 <= 4 and mon.weekday() == 0:
            n = (mon.day - 1) // 7 + 1
            out += FRIDAY_PACKS.get(n, [])
    # KPI pack: Friday before the first Monday when that Friday is in the new month, else the Monday itself
    first = d.replace(day=1); mon1 = first + dt.timedelta(days=(0 - first.weekday()) % 7)
    kpi_day = mon1 - dt.timedelta(days=3) if (mon1 - dt.timedelta(days=3)).month == d.month else mon1
    if d == kpi_day and "Ops KPI pack" not in out: out.append("Ops KPI pack")
    if d == mon1 and d != kpi_day and "Ops KPI pack" in out: out.remove("Ops KPI pack")
    return out


def posts_today(msgs, d):
    got = {}
    for m in msgs:
        if m["user"] != "U0CJMSDSPGA": continue
        if not m["when"].startswith(d.isoformat()): continue
        head = m["text"].strip().split("\n")[0]
        for label, (key, _) in POSTS.items():
            if key in head: got[label] = m["ts"]
        if head.startswith(":warning:"): got.setdefault("_warnings", []).append(head[:200])
    return got


def feed_rows(text):
    rows, on = [], False
    for ln in text.splitlines():
        c = ln.split("\t")
        if c and c[0] == "Tab": on = True; continue
        if on and len(c) >= 6 and re.fullmatch(r"[A-Za-z0-9_]+", c[0] or ""):
            rows.append({"tab": c[0], "source": c[1], "newest": c[3], "lag": c[4], "status": c[5].strip()})
        elif on and not c[0].strip(): break
    return rows


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("cmd")
    for x in ("asof", "channel", "triggers", "feeds", "known", "out", "threads"): ap.add_argument("--" + x)
    a = ap.parse_args()
    d = dt.date.fromisoformat(a.asof); os.makedirs(a.out, exist_ok=True)
    st = _imp("../../strategist/scripts/strategist.py")
    if not a.channel or not os.path.exists(a.channel): print("channel file missing", file=sys.stderr); sys.exit(2)
    msgs = st.parse_slack(open(a.channel, encoding="utf-8").read())
    if not msgs: print("channel unreadable", file=sys.stderr); sys.exit(2)
    if a.threads:
        import glob
        for fn in sorted(glob.glob(os.path.join(a.threads, "thread_*.json"))):
            msgs += st.parse_slack(open(fn, encoding="utf-8").read())
    known = set(json.load(open(a.known))) if a.known and os.path.exists(a.known) else set()
    issues, rerun = [], []

    # 1 posts due today
    want, got = due_today(d), posts_today(msgs, d)
    for label in want:
        if label in got: continue
        task = POSTS[label][1]
        if got.get("_warnings"):
            issues.append({"kind": "post", "label": "Explained", "what": f"{label} did not post; a warning was posted: {got['_warnings'][0]}", "owner": "Jonathan", "task": task})
        else:
            issues.append({"kind": "post", "label": "Unexplained", "what": f"{label} was due today and no post was found", "owner": "Jonathan", "task": task})
        rerun.append({"task": task, "trigger_id": TASKS[task], "reason": f"{label} missing on {d}", "same_day_only": True})
    # warnings from any agent in the last day, not tied to a missing post
    for w in got.get("_warnings", []):
        if not any(w[:60] in i["what"] for i in issues):
            issues.append({"kind": "warning", "label": "Explained", "what": f"An agent posted: {w}", "owner": "Jonathan", "task": None})

    # 2 scheduled tasks
    if a.triggers and os.path.exists(a.triggers):
        t = open(a.triggers, encoding="utf-8").read()
        obj = json.JSONDecoder().raw_decode(t[t.index("{"):])[0]
        for tr in obj.get("data", []):
            if tr.get("name") not in TASKS: continue
            lr = tr.get("last_run") or {}
            if not tr.get("enabled", True) or tr.get("ended_reason") or tr.get("suspension_reason"):
                issues.append({"kind": "task", "label": "Likely cause", "what": f"Scheduled task '{tr['name']}' is not enabled" + (f" ({tr.get('ended_reason') or tr.get('suspension_reason')})" if (tr.get('ended_reason') or tr.get('suspension_reason')) else " (paused)"), "owner": "Jonathan", "task": tr["name"]})
            elif lr and lr.get("status") not in ("SUCCEEDED", None):
                issues.append({"kind": "task", "label": "Unexplained", "what": f"'{tr['name']}' last run {lr.get('status')} at {lr.get('fired_at')}", "owner": "Jonathan", "task": tr["name"]})
                if tr["name"] == "Marketing Ops" or any(POSTS[w][1] == tr["name"] for w in want):
                    rerun.append({"task": tr["name"], "trigger_id": TASKS[tr["name"]], "reason": f"last run {lr.get('status')}", "same_day_only": True})
    # 3 feeds
    if a.feeds and os.path.exists(a.feeds):
        for r in feed_rows(open(a.feeds, encoding="utf-8").read()):
            if r["status"] == "OK": continue
            key = KNOWN_FEED_KEYS.get(r["tab"])
            if key and key in known: continue  # already on the log: quiet
            issues.append({"kind": "feed", "label": "Likely cause" if r["status"] == "Empty" else "Unexplained",
                           "what": f"Feed {r['tab']} ({r['source']}) is {r['status']}" + (f", newest {r['newest']}" if r["newest"] else ""),
                           "owner": "Jonathan", "task": None, "log_key": key})
    # 4 heartbeat and post text
    monday = d.weekday() == 0
    lines = []
    if issues:
        lines.append(f":stethoscope: *Health, {d.strftime('%a %b %-d')}*: {len(issues)} thing{'s' if len(issues) != 1 else ''} to look at")
        for i in issues[:5]:
            lines.append(f"• {i['what']}. {i['label']}. Owner: {i['owner']}.")
        if len(issues) > 5: lines.append(f"…and {len(issues) - 5} more on the log.")
    elif monday:
        lines.append(f":stethoscope: *Health, {d.strftime('%a %b %-d')}*: all checks passed.")
    res = {"asof": d.isoformat(), "due": want, "found": [k for k in got if not k.startswith("_")], "issues": issues, "rerun_plan": rerun,
           "post": bool(lines)}
    json.dump(res, open(os.path.join(a.out, "health.json"), "w"), indent=1)
    open(os.path.join(a.out, "post.txt"), "w").write("\n".join(lines))
    json.dump(rerun, open(os.path.join(a.out, "rerun.json"), "w"), indent=1)
    print(json.dumps({"due": len(want), "found": len(res["found"]), "issues": len(issues), "post": res["post"], "rerun_plan": len(rerun)}))


if __name__ == "__main__":
    main()
