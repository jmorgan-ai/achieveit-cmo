#!/usr/bin/env python3
"""CMO Strategist inputs. Dates, review calendar and the week's suggestions come from here; the agent never works them out.

  strategist.py --which DATE                 -> {"run": bool, "monthly": bool}      (Mondays; monthly = first Monday)
  strategist.py facts --asof DATE --decisions docs/decisions.md --out DIR           -> DIR/facts.json
  strategist.py extract --channel FILE --asof DATE [--days 7] --out DIR
      FILE = saved Slack read of #marketing-cmo; thread reads of the Research log posts are saved next to it as thread_<parent ts>.json
      (pass --threads DIR). Writes DIR/messages.json (parsed), DIR/candidates.json (suggestions in bot posts, each with agent, key, text,
      post ts, link) and DIR/packs.json (latest pack per agent: agent, posted, link, first lines).
"""
import argparse, datetime as dt, importlib.util, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
BOT = "U0CJMSDSPGA"
APPROVERS = {"U45A7FFV4": "Jonathan", "U32KHRMTJ": "Amanda"}
REVIEWERS = {"U0BGWQLFBG8": "Cristina"}
LINK = "https://achieveit.slack.com/archives/C0CJRL8KDRS/p{}"
PLINK = "https://achieveit.slack.com/archives/C0CJRL8KDRS/p{}?thread_ts={}&cid=C0CJRL8KDRS"
HEADERS = [  # (text the post starts with, agent)
    ("*New opps that break an attribution rule", "Ops"), ("*Marketing KPIs", "Ops"), ("*Attribution and performance", "Ops"),
    ("*Paid,", "Paid"), ("*SEO,", "SEO"), ("*Website,", "Website"), ("*Content and social,", "Content"),
    ("*Product marketing,", "Product Marketing"), ("*Customer story candidates", "Customers"), ("*Marketing, week of", "PM"),
    ("*Health", "Health"), ("*CMO brief", "Strategist"),
]


def _import(rel):
    spec = importlib.util.spec_from_file_location("m", os.path.join(HERE, rel))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


def which(d):
    return {"run": d.weekday() == 0, "monthly": d.weekday() == 0 and d.day <= 7}


def agent_of(text):
    head = text.strip().split("\n")[0]
    for k, a in HEADERS:
        if k in head: return a
    if head.startswith(":warning:"): return "Warning"
    return None


def parse_slack(raw):
    """slack_read_channel text -> list of {ts, user, name, when, text}"""
    try:
        obj = json.JSONDecoder().raw_decode(raw[raw.index("{"):])[0]
        raw = obj.get("messages", raw) if isinstance(obj, dict) else raw
    except ValueError:
        pass
    out = []
    for blk in re.split(r"\n?=== Message from ", "\n" + raw)[1:]:
        m = re.match(r"(.*?) \((U[A-Z0-9]+)\) at (\d{4}-\d\d-\d\d \d\d:\d\d:\d\d) [A-Z]{3,4} ===\s*\nMessage TS: ([0-9.]+)\n(.*)", blk, re.S)
        if not m: continue
        name, uid, when, ts, text = m.groups()
        out.append({"ts": ts, "user": uid, "name": name.split(" <")[0], "when": when, "text": text.strip()})
    return out


def candidates(msgs, asof, days):
    sys.path.insert(0, HERE)
    import openlog
    cutoff = dt.datetime.combine(asof - dt.timedelta(days=days), dt.time.min)
    out = []
    for m in msgs:
        if m["user"] != BOT: continue
        if dt.datetime.strptime(m["when"], "%Y-%m-%d %H:%M:%S") < cutoff: continue
        ag = agent_of(m["text"])
        if ag in (None, "PM", "Health", "Warning", "Strategist"): continue
        for ln in m["text"].split("\n"):
            ln = ln.strip()
            if not ln.startswith("•") or "Suggested:" not in ln: continue
            body = ln.lstrip("• ").strip()
            sug = body.split("Suggested:", 1)[1].strip()
            out.append({"agent": ag, "key": openlog.make_key(ag, sug), "text": body, "suggested": sug, "post_ts": m["ts"],
                        "link": (PLINK.format(m["ts"].replace(".", ""), m["thread_ts"]) if m.get("thread_ts") else LINK.format(m["ts"].replace(".", ""))), "posted": m["when"]})
    return out


def main():
    if len(sys.argv) == 3 and sys.argv[1] == "--which":
        print(json.dumps(which(dt.date.fromisoformat(sys.argv[2])))); return
    ap = argparse.ArgumentParser(); ap.add_argument("cmd")
    ap.add_argument("--asof"); ap.add_argument("--decisions", default="docs/decisions.md"); ap.add_argument("--out")
    ap.add_argument("--channel"); ap.add_argument("--days", type=int, default=7); ap.add_argument("--threads")
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    asof = dt.date.fromisoformat(a.asof)
    if a.cmd == "facts":
        cmo = _import("../../cmo-brief/scripts/cmo.py")
        ns = argparse.Namespace(asof=a.asof, decisions=a.decisions, out=a.out)
        cmo.facts(ns)
        f = json.load(open(os.path.join(a.out, "facts.json"))); f["monthly"] = which(asof)["monthly"]
        json.dump(f, open(os.path.join(a.out, "facts.json"), "w"), indent=1)
    elif a.cmd == "extract":
        if not os.path.exists(a.channel): print("channel file missing", file=sys.stderr); sys.exit(2)
        msgs = parse_slack(open(a.channel, encoding="utf-8").read())
        if not msgs: print("no messages parsed", file=sys.stderr); sys.exit(2)
        for m in msgs: m["thread_ts"] = None
        if a.threads:
            import glob
            for fn in sorted(glob.glob(os.path.join(a.threads, "thread_*.json"))):
                parent = re.search(r"thread_([0-9.]+)\.json$", fn)
                if not parent: continue
                for m in parse_slack(open(fn, encoding="utf-8").read()):
                    if m["ts"] == parent.group(1): continue   # the log post itself
                    m["thread_ts"] = parent.group(1); msgs.append(m)
        json.dump(msgs, open(os.path.join(a.out, "messages.json"), "w"), indent=1)
        cands = candidates(msgs, asof, a.days)
        packs = {}
        for m in sorted(msgs, key=lambda x: x["when"]):
            if m["user"] != BOT or not m.get("thread_ts"): continue
            ag = agent_of(m["text"])
            if ag in (None, "Warning"): continue
            packs[ag] = {"agent": ag, "posted": m["when"], "ts": m["ts"], "link": PLINK.format(m["ts"].replace(".", ""), m["thread_ts"]),
                         "head": "\n".join(m["text"].split("\n")[:12])}
        json.dump({"packs": list(packs.values())}, open(os.path.join(a.out, "packs.json"), "w"), indent=1)
        json.dump({"candidates": cands}, open(os.path.join(a.out, "candidates.json"), "w"), indent=1)
        print(json.dumps({"messages": len(msgs), "candidates": len(cands), "agents": sorted({c["agent"] for c in cands}), "packs": sorted(packs)}))
    else:
        ap.error("cmd: facts | extract")


if __name__ == "__main__":
    main()
