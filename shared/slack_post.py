#!/usr/bin/env python3
"""slack_post.py - post as the AchieveIt CMO bot.

  slack_post.py FILE [FILE ...] [--weekly | --thread-ts TS] [--channel C0CJRL8KDRS] [--week-of YYYY-MM-DD] [--weekly-create]

Agent packs go in the week's "Research log" thread so the channel stays readable:
  --weekly         find this week's log post (or create it) and reply in its thread. Files are joined into as few messages as
                   fit (about 3,500 characters each), in the order given.
  --thread-ts TS   reply under a given post (Ask CMO, the Strategist's brief).
  neither          post at top level (the brief, Health warnings).
  --separate       one reply per file (the Strategist's per-agent replies); default is to join files that fit together.
  --weekly-create  skip the lookup and create a new log post (use only after the fallback in cmo-system found none).
Spacing is tidied on every post (blank line between findings, after titles, before section labels).
No Authorization header: the cloud environment's network proxy adds the bot token for slack.com.
Prints one JSON line per message ({"ok": true, "ts": ..., "thread_ts": ...}); exit 0 only when every message says "ok": true.
If the log post cannot be looked up (Slack refuses the history call) it prints {"ok": false, "error": "weekly_lookup_failed", ...}
and exits 3: do not post another way; follow the fallback in cmo-system (read the channel with the Slack tools, then --thread-ts).
Never falls back to another route.
"""
import sys, json, argparse, datetime as dt, re, urllib.request, urllib.parse
from zoneinfo import ZoneInfo

CH_DEFAULT = "C0CJRL8KDRS"
BOT = "U0CJMSDSPGA"
MAX = 3500
TZ = ZoneInfo("America/Denver")


def api(method, body=None, form=None):
    if form is not None:
        data, hdr = urllib.parse.urlencode(form).encode(), {"Content-type": "application/x-www-form-urlencoded"}
    else:
        data, hdr = json.dumps(body or {}).encode("utf-8"), {"Content-type": "application/json; charset=utf-8"}
    req = urllib.request.Request("https://slack.com/api/" + method, data=data, headers=hdr, method="POST")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def tidy(text):
    """Spacing only; never changes words or numbers."""
    lines = [ln.rstrip() for ln in text.strip().split("\n")]
    out = []
    for i, ln in enumerate(lines):
        s = ln.strip()
        prev = out[-1].strip() if out else ""
        is_bullet = s.startswith(("•", "- ", "• "))
        is_label = bool(re.match(r"^\*[^*]{2,60}\*:?$", s)) or bool(re.match(r"^\*[^*]{2,40}:\*", s)) and not is_bullet
        if out and prev != "":
            if i == 1 and lines[0].lstrip().startswith(":"):    # blank line after the title
                out.append("")
            elif is_label:   # blank line before a section label
                out.append("")
            elif is_bullet and prev.startswith(("•", "- ")) and (len(s) > 90 or len(prev) > 90):  # air between findings
                out.append("")
        out.append(ln)
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def chunks(texts):
    """Join texts (already tidied) into messages under MAX characters; a single longer text is split at blank lines."""
    msgs, cur = [], ""
    parts = []
    for t in texts:
        if len(t) <= MAX:
            parts.append(t); continue
        buf = ""
        for para in t.split("\n\n"):
            if buf and len(buf) + len(para) + 2 > MAX: parts.append(buf); buf = ""
            buf = (buf + "\n\n" + para) if buf else para
        if buf: parts.append(buf)
    for p in parts:
        if cur and len(cur) + len(p) + 2 <= MAX: cur += "\n\n" + p
        else:
            if cur: msgs.append(cur)
            cur = p
    if cur: msgs.append(cur)
    return msgs


def week_monday(week_of):
    d = dt.date.fromisoformat(week_of) if week_of else dt.datetime.now(TZ).date()
    return d - dt.timedelta(days=d.weekday())


def marker(mon):
    return f"Research log, week of {mon.strftime('%b')} {mon.day}"


def find_log(ch, mon):
    start = dt.datetime.combine(mon - dt.timedelta(days=1), dt.time.min, TZ).timestamp()
    r = api("conversations.history", form={"channel": ch, "oldest": f"{start:.0f}", "limit": "200"})
    if not r.get("ok"):
        raise RuntimeError(r.get("error", "unknown"))
    for m in r.get("messages", []):
        if m.get("user") == BOT and marker(mon) in m.get("text", "") and m.get("thread_ts", m["ts"]) == m["ts"]:
            return m["ts"]
    return None


def create_log(ch, mon):
    txt = (f":card_index_dividers: *{marker(mon)}*\n\nThe agents file their full packs in this thread. Nothing to read here: "
           f"the Monday CMO brief is the summary and links to each pack.")
    r = api("chat.postMessage", {"channel": ch, "text": txt, "unfurl_links": False, "unfurl_media": False})
    if not r.get("ok"):
        raise RuntimeError(r.get("error", "unknown"))
    return r["ts"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--thread-ts")
    ap.add_argument("--channel", default=CH_DEFAULT)
    ap.add_argument("--weekly", action="store_true")
    ap.add_argument("--weekly-create", action="store_true")
    ap.add_argument("--separate", action="store_true")
    ap.add_argument("--week-of")
    a = ap.parse_args()
    texts = []
    for f in a.files:
        t = open(f, encoding="utf-8").read().strip()
        if t: texts.append(t)
    if not a.separate:   # a pack's parent repeats its first lines in the detail file: show each long line once
        seen, deduped = set(), []
        for t in texts:
            keep = []
            for ln in t.split("\n"):
                k = ln.strip()
                if len(k) > 40 and k in seen: continue
                if len(k) > 40: seen.add(k)
                keep.append(ln)
            deduped.append("\n".join(keep))
        texts = deduped
    texts = [tidy(t) for t in texts if t.strip()]
    if not texts:
        print(json.dumps({"ok": True, "skipped": "empty message"})); return 0
    thread = a.thread_ts
    try:
        if a.weekly or a.weekly_create:
            mon = week_monday(a.week_of)
            if a.weekly_create:
                thread = create_log(a.channel, mon)
            else:
                try:
                    thread = find_log(a.channel, mon)
                except Exception as e:
                    print(json.dumps({"ok": False, "error": "weekly_lookup_failed", "detail": str(e), "marker": marker(mon)}))
                    return 3
                if not thread:
                    thread = create_log(a.channel, mon)
    except Exception as e:
        print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"})); return 1
    ok = True
    for m in (texts if a.separate else chunks(texts)):
        body = {"channel": a.channel, "text": m, "unfurl_links": False, "unfurl_media": False}
        if thread: body["thread_ts"] = thread
        try:
            resp = api("chat.postMessage", body)
        except Exception as e:
            print(json.dumps({"ok": False, "error": f"{type(e).__name__}: {e}"})); return 1
        print(json.dumps({"ok": resp.get("ok"), "ts": resp.get("ts"), "thread_ts": thread, "error": resp.get("error")}))
        if not resp.get("ok"): ok = False; break
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
