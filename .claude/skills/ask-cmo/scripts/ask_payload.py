#!/usr/bin/env python3
"""ask_payload.py - check and summarize the Slack event the Ask CMO routine was fired with. No network.

  python3 ask_payload.py payload.json      (payload = the JSON inside <routine-fire-payload>)

Exit 0 and print a JSON summary when the event is a message in #marketing-cmo from Jonathan, Amanda or Cristina that either mentions
the CMO bot or is a reply in a thread the CMO bot started, and nobody has answered it yet. Exit 3 (print the reason) to stop quietly.
Approvers: Jonathan (everything) and Amanda (content, paid and website items). Cristina can ask and comment; her messages never change a status.
"""
import json, sys

CHANNEL = "C0CJRL8KDRS"
BOT = "U0CJMSDSPGA"   # AchieveIt CMO bot (posts with shared/slack_post.py)
PEOPLE = {"U45A7FFV4": ("Jonathan", "approver"), "U32KHRMTJ": ("Amanda", "approver_content_paid_website"), "U0BGWQLFBG8": ("Cristina", "reviewer")}


def stop(why): print(json.dumps({"stop": why})); sys.exit(3)


p = json.load(open(sys.argv[1], encoding="utf-8"))
if p.get("kind") != "cmo_message": stop(f"kind is {p.get('kind')!r}, not cmo_message")
if (p.get("channel") or {}).get("id") != CHANNEL: stop("not #marketing-cmo")
u = (p.get("trigger_user") or {}).get("user_id")
if u not in PEOPLE: stop("message is not from Jonathan, Amanda or Cristina")
msgs = p.get("messages") or []
if not msgs: stop("no messages")
trig = next((m for m in msgs if m.get("ts") == p.get("trigger_message_ts")), None)
if trig is None: stop("trigger message not found")
if trig.get("user_id") == BOT or trig.get("is_bot"): stop("trigger is a bot message")
thread_ts = p.get("thread_ts") or trig["ts"]
parent = msgs[0]
parent_by_bot = bool(parent.get("is_bot") or parent.get("user_id") == BOT)
mention = f"<@{BOT}" in (trig.get("text") or "") or bool(p.get("mention"))
is_reply = trig["ts"] != thread_ts
if not (mention or (is_reply and parent_by_bot)): stop("not a mention and not a reply to a bot post")
# already answered: a bot message after the trigger
if any((m.get("is_bot") or m.get("user_id") == BOT) and float(m["ts"]) > float(trig["ts"]) for m in msgs): stop("already answered")
name, role = PEOPLE[u]
earlier = [dict(ts=m["ts"], who=m.get("name"), by_bot=bool(m.get("is_bot")), text=m.get("text", "")) for m in msgs if m.get("ts") != trig["ts"]]
print(json.dumps(dict(stop=None, by=name, by_id=u, role=role, thread_ts=thread_ts, reply_ts=trig["ts"], is_reply=is_reply,
                      mention=mention, parent_by_bot=parent_by_bot, text=trig.get("text", ""), parent_text=(parent.get("text") or "")[:4000],
                      earlier=earlier[-12:], truncated=p.get("truncated", False)), indent=1, ensure_ascii=False))
