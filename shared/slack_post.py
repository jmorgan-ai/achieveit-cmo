#!/usr/bin/env python3
"""slack_post.py - post a message as the AchieveIt CMO bot.

  python3 slack_post.py <message-file> [--thread-ts 1729350000.123456] [--channel C0CJRL8KDRS]

No Authorization header: the cloud environment's network proxy adds the bot token for slack.com.
Prints Slack's JSON response; exit 0 only when it says "ok": true. Never falls back to another route.
"""
import sys, json, argparse, urllib.request

ap = argparse.ArgumentParser()
ap.add_argument("file")
ap.add_argument("--thread-ts")
ap.add_argument("--channel", default="C0CJRL8KDRS")
a = ap.parse_args()
text = open(a.file, encoding="utf-8").read().strip()
if not text:
    print(json.dumps({"ok": True, "skipped": "empty message"}))
    sys.exit(0)
body = {"channel": a.channel, "text": text, "unfurl_links": False, "unfurl_media": False}
if a.thread_ts:
    body["thread_ts"] = a.thread_ts
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=json.dumps(body).encode("utf-8"),
    headers={"Content-type": "application/json; charset=utf-8"},
    method="POST",
)
try:
    with urllib.request.urlopen(req, timeout=30) as r:
        resp = json.loads(r.read().decode("utf-8"))
except Exception as e:
    print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"}))
    sys.exit(1)
print(json.dumps(resp))
sys.exit(0 if resp.get("ok") else 1)
