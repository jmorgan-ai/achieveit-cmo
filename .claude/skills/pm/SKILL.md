---
name: pm
description: PM agent for AchieveIt marketing. Mondays, posts one short "Marketing, week of ..." note from the monday.com 2026 Marketing Projects board: what got done, what to focus on now, and what needs a call (overdue, no owner, on hold). Read-only. Use when the PM routine fires or someone asks "run the PM agent", "what's on the marketing board" or "weekly marketing status".
---

# PM

Load `cmo-system` first. Keep it short: the post names the few things that matter, and the thread holds the rest. All counts, dates
and names come from `scripts/pm.py`; never count, date or retype board data yourself (save it with `shared/capture.py`).

**Reads** the monday.com board 2026 Marketing Projects (`18396405978`). **Writes** only Slack posts to #marketing-cmo through
`shared/slack_post.py`. It never creates or changes monday items, Notion pages, emails or meetings. It does not nudge people: it
posts to the channel, owners are named only as facts.

Set up: `R=<repo root>; S=$R/.claude/skills/pm/scripts/pm.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## Run
1. `python3 $S --which D`. `"run": false` = finish with `PM D: no post today` (it posts on Mondays).
2. Read every item: `get_board_items_page`, `boardId` 18396405978, `includeColumns` true, `columnIds`
   `["person","status","status_1","date4","requested_due_date","last_updated","completed_date"]`, `limit` 500, no filters.
   Capture: `python3 $C --tool get_board_items_page --out $W/in/board.json`. If the board can't be read, post
   `:warning: PM did not run: monday.com unavailable` and stop.
3. `python3 $S --asof D --in $W/in/board.json --out $W/out`. Exit 2 = post `:warning: PM stopped: <message>` and stop.
4. Post `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then `01_detail.txt` with `--thread-ts <ts>`.
   A post without `"ok": true`: stop and say so in the run line.
5. Finish with one line: `PM D: <open> open, <done> done last week, <overdue> overdue, <stale> stale, <no_owner> no owner`.

## Rules the script applies (change only by pull request)
- Last week = the Sunday to Saturday before the Monday. Done = Completed group with a completed date in that week.
- Focus = In Progress items with priority High, oldest update first. Stale = In Progress with no update in 14+ days (shown beside the item).
- Needs a call = overdue (due date passed), no owner, or On Hold in Scoping, Open Tickets or In Progress. Items Jonathan decided
  to leave on hold are listed in `HOLD_OK` in the script (CookieYes consent fix).
- Most board items have no due date, so priority and last update carry the weight; an item with a due date is overdue the day after.
- Not built yet: drafting the Notion "where we stand" section and email. Both write outside Slack and wait for an approval path.
