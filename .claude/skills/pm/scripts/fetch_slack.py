#!/usr/bin/env python3
"""Read the last N days of the allowlisted team channels, as the CMO bot. Nothing else is ever read.

  fetch_slack.py --out slack.json
Channels come only from references/team_sources.json (public or private channels, IDs starting with C). A DM or group DM ID is refused.
No Authorization header: the cloud environment's network proxy adds the bot token. A channel that cannot be read is listed with its
error, never worked around. Always exits 0 so the PM run continues; the gaps script reports what could not be read.
"""
import argparse, json, os, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "..", "references", "team_sources.json")))


def api(method, form):
    req = urllib.request.Request("https://slack.com/api/" + method, urllib.parse.urlencode(form).encode(),
                                 {"Content-type": "application/x-www-form-urlencoded"}, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--out", required=True); a = ap.parse_args()
    oldest = f"{time.time() - CFG['days'] * 86400:.0f}"
    out = {"days": CFG["days"], "channels": [], "messages": []}
    for ch in CFG["slack"]:
        cid, name = ch.get("id"), ch["name"]
        if not cid:
            out["channels"].append({"name": name, "error": "channel_id_not_set"}); continue
        if not cid.startswith("C"):
            out["channels"].append({"name": name, "error": "refused_not_a_channel"}); continue
        try:
            r = api("conversations.history", {"channel": cid, "oldest": oldest, "limit": "200"})
        except Exception as e:
            out["channels"].append({"name": name, "error": f"{type(e).__name__}"}); continue
        if not r.get("ok"):
            out["channels"].append({"name": name, "error": r.get("error", "unknown")}); continue
        n = 0
        for m in r.get("messages", []):
            if m.get("subtype") or m.get("bot_id") or not m.get("text"): continue
            n += 1
            out["messages"].append({"channel": name, "ts": m["ts"], "text": m["text"],
                                    "url": f"https://achieveit.slack.com/archives/{cid}/p{m['ts'].replace('.', '')}"})
        out["channels"].append({"name": name, "read": n})
    json.dump(out, open(a.out, "w"))
    print(json.dumps(out["channels"]))


if __name__ == "__main__":
    main()
