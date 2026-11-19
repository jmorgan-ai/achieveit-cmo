#!/usr/bin/env python3
"""Things said in team meetings or team channels that are not on the board. The agent never judges or retypes text itself.

  gaps.py --week-page DATE                         -> prints the meeting page title to open, e.g. "Week of 11/16" (DATE = the Monday run)
  gaps.py --asof DATE --board board.json --notion page.json [--slack slack.json] --out DIR

page.json = capture of notion-fetch for the team meeting page (needs "path" and "text"). Only pages under the allowed path and titled
"Week of ..." are read, and only their unchecked to-do lines (the meeting action items). Talking points, summaries, notes and
transcripts are never read. slack.json = fetch_slack.py output (allowlisted team channels only).
Any line that touches a private topic is dropped before anything else and only counted. Writes DIR/slack/05_missing_on_board.txt.
Exit 2 = a page outside the allowed path or an unreadable board.
"""
import argparse, datetime as dt, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
CFG = json.load(open(os.path.join(HERE, "..", "references", "team_sources.json")))
# Private topics: the whole line is dropped, never shown or summarized.
DENY = re.compile(r"annual review|performance|\breview(s)? (of|for) (him|her|them)|\blattice\b|salary|compensation|\bcomp\b|raise|bonus|promotion|"
                  r"hiring|hire\b|interview|candidate|resign|terminat|fired|layoff|severance|\bpto\b|time off|vacation|sick|medical|doctor|"
                  r"health|maternity|leave of absence|\b1[:\- ]?1\b|one[- ]on[- ]one|feedback (on|for) (him|her|them)|disciplin|"
                  r"confidential|private|personal", re.I)
STOP = set("the and for with that this from have will about into your their our them then than also just need needs".split())
ACTION = re.compile(r"\b(to do|todo|action item|need to|needs to|should|can someone|can we|could we|please|remind|reminder|don't forget|"
                    r"follow up|follow-up|by (mon|tue|wed|thu|fri)\w*|by \d+/\d+|due|deadline|let's|lets|we'll|i'll|will send|will create)\b", re.I)


def die(m):
    print(m, file=sys.stderr); sys.exit(2)


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if len(w) > 3 and w not in STOP}


def clean(s):
    s = re.sub(r"\[\^[^\]]*\]", "", s)                       # Notion citation marks
    s = re.sub(r"<[^>]+>", "", s)                            # html tags
    s = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", s)           # markdown links keep the text
    s = re.sub(r"<@[A-Z0-9]+>", "", s)
    return " ".join(s.split()).strip(" -•")


def short(s, k=100):
    return s if len(s) <= k else s[:k - 1].rstrip() + "…"


def notion_lines(p):
    path, title = p.get("path", ""), p.get("title", "")
    if not path.startswith(CFG["notion_path_prefix"]) or not title.startswith("Week of"):
        die(f"refused: page '{title}' is not a team meeting page under {CFG['notion_path_prefix']}")
    out = []
    for ln in p.get("text", "").split("\n"):
        m = re.match(r"\s*-\s*\[ \]\s*(.+)$", ln)               # unchecked to-do lines only
        if m and clean(m.group(1)): out.append(clean(m.group(1)))
    return title, p.get("url", ""), out


def board_tokens(board):
    items = board.get("items") or die("board has no items")
    return [(i["name"], toks(i["name"])) for i in items]


def on_board(t, bt):
    ct = toks(t)
    if not ct: return True
    for name, bt_ in bt:
        o = len(ct & bt_)
        if o >= 3 or (o >= 2 and o / len(ct) >= 0.5): return True
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--week-page"); ap.add_argument("--asof"); ap.add_argument("--board"); ap.add_argument("--notion")
    ap.add_argument("--slack"); ap.add_argument("--out")
    a = ap.parse_args()
    if a.week_page:
        d = dt.date.fromisoformat(a.week_page); d -= dt.timedelta(days=d.weekday() + 7)
        print(f"Week of {d.month}/{d.day}"); return
    asof = dt.date.fromisoformat(a.asof)
    try: bt = board_tokens(json.load(open(a.board)))
    except (OSError, ValueError): die("board.json missing or unreadable")
    cands, dropped, read_n, read_s, notes = [], 0, 0, 0, []
    if a.notion and os.path.exists(a.notion):
        title, url, lines = notion_lines(json.load(open(a.notion)))
        read_n = len(lines)
        for t in lines:
            if DENY.search(t): dropped += 1; continue
            cands.append(("Notion " + title, url, t))
    else:
        notes.append("meeting page not read")
    if a.slack and os.path.exists(a.slack):
        s = json.load(open(a.slack))
        for c in s.get("channels", []):
            if c.get("error"): notes.append(f"#{c['name']} ({c['error']})")
        for m in s.get("messages", []):
            read_s += 1
            t = clean(m["text"])
            if DENY.search(t): dropped += 1; continue
            if not ACTION.search(t) or len(t) < 25: continue
            cands.append(("#" + m["channel"], m["url"], t))
    miss, seen = [], set()
    for src, url, t in cands:
        k = " ".join(sorted(toks(t)))
        if k in seen or on_board(t, bt): continue
        seen.add(k); miss.append((src, url, t))
    mon = asof if asof.weekday() == 0 else asof - dt.timedelta(days=asof.weekday())
    L = [f":mag: *Mentioned but not on the board, week of {mon.strftime('%b')} {mon.day}*", ""]
    if miss:
        L.append(f"{len(miss)} thing{'s' if len(miss) != 1 else ''} said in last week's team notes or team channels with no matching board item. "
                 "Each is a question for its owner: add it to the board, or drop it.")
        L.append("")
        for src, url, t in miss[:8]:
            t = short(t).rstrip(".?!")
            L.append(f"• {t}. <{url}|{src}>" if url else f"• {t}. {src}")
        if len(miss) > 8: L.append(f"(+{len(miss) - 8} more not shown)")
    else:
        L.append("Nothing found: every action item and request in last week's team notes and channels matches a board item.")
    L += ["", f"Read: {read_n} meeting action items and {read_s} channel messages. {dropped} lines on private topics were skipped without being read further."
              + (" Not read: " + "; ".join(notes) + "." if notes else "")]
    os.makedirs(os.path.join(a.out, "slack"), exist_ok=True)
    open(os.path.join(a.out, "slack", "05_missing_on_board.txt"), "w").write("\n".join(L) + "\n")
    print(json.dumps({"missing": len(miss), "notion_items": read_n, "slack_messages": read_s, "dropped": dropped, "notes": notes}))


if __name__ == "__main__":
    main()
