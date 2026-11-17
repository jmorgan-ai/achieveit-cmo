---
name: marketing-ops
description: Marketing Ops agent for AchieveIt. Weekdays, flags new Salesforce opps that break the attribution rules. Before the first-Monday review it posts the KPI scorecard for last month (and the quarter at quarter end; Non-Field and Field vs the 2026 plan); on the Friday before the second-Monday review it posts the attribution check (proposed fixes) and performance (results by attribution, channel economics, offers and markets). Read-only. Use when the Marketing Ops routine fires or someone asks to "run marketing ops", "check attribution" or "post the KPI pack".
---

# Marketing Ops

Load `cmo-system` first. Queries are in `references/queries.md`. All numbers come from `scripts/ops.py`; never compute,
round or restate a number yourself, and never retype a connector result (capture it with `shared/capture.py`).

**Reads** Salesforce and Marketing Budget & Performance.xlsx. **Writes** only Slack posts to #marketing-cmo through
`shared/slack_post.py`. It never changes Salesforce: every fix is a proposal for Amanda or the opp owner.

Set up: `R=<repo root>; S=$R/.claude/skills/marketing-ops/scripts/ops.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## 1. Which run
Every weekday: the **daily check** (step 2). Then `python3 $S --which D`:
- `"part": "kpi"`: the **KPI pack** for the first-Monday review (posted the Friday before, or on the Monday itself when
  that Friday is still in the month under review).
- `"part": "attribution"`: the **attribution pack** for the second-Monday review (posted the Friday before).
- `null`: no pack today.
The period is last month (`"month"`); when last month ends a quarter, the scorecard adds the quarter. Pass
`--month <month>` to the pack. If someone asks for a pack by name on another day, run that part for last month.

## 2. Daily check
1. Query D (since the previous weekday) and query C for this year and the two before. Capture to `$W/in/opps.json`
   and `$W/in/lost_<year>.json`.
2. `python3 $S --mode daily --asof D --in $W/in --out $W/out`.
3. If `$W/out/slack/00_parent.txt` exists, post it: `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`.
   No file = nothing broke a rule: post nothing.
Use a fresh `$W` for the pack.

## 3. Pack (KPI or attribution)
1. Queries A, B, C (three years), E and F (queries.md). Capture each to its file in `$W/in`.
   If Salesforce fails, post `:warning: Marketing Ops <part> pack did not run: Salesforce unavailable` and stop.
   If the budget sheet can't be read, carry on without `budget.txt`.
2. `python3 $S --mode pack --part kpi|attribution --month <month> --asof D --in $W/in --out $W/out`.
   Exit 2 = STOP: post `:warning: Marketing Ops <part> pack stopped: <message>` and stop.
3. Top findings. Read `$W/out/highlights.json` (ranked candidates, each with its numbers and evidence). Pick at most three
   that matter most for the Non-Field goals, and replace the line `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with
   one bullet each in the finding format, compressed to one line:
   `• <what, using the candidate's own numbers>. <so what for the goal>. Suggested: <owner and next step>.`
   Owners: Jonathan (spend, goals, Salesforce process), Amanda (channels, content, attribution fixes), Cristina (website,
   SEO), the opp owner (a single opp). Use only numbers that appear in the candidate's `text`. If there are no candidates,
   delete the line. Edit the file with Python (read, replace, write); do not retype the rest of it.
4. Post: `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt` and keep the `ts`. Then every other file in
   `$W/out/slack/` in name order with `--thread-ts <ts>`.
5. A post that does not return `"ok": true`: stop posting, and say so in the run line (CLAUDE.md rule 9).

## 4. Finish
One line: `Marketing Ops D: daily <n checked>/<n flagged>[, <part> pack <month>: <fixes> fixes, <posts> posts][, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Attribution checks, this year's new-business opps: test records; reopened within 9 months of a lost opp with a different
  attribution (revert); reopened after 9 months through a marketing campaign but still on the old attribution (Marketing
  Sourced, confirm); webinar opps not Marketing Sourced; OSDR opps that came in through the website; Attribution blank;
  Attribution Source blank (OSDR ones counted as one bulk update); event or webinar opps with no Custom Source; Market blank
  on open opps.
- Scorecard: definitions and goals from the cmo-system rulebook. Non-Field spend = budget sheet "Total" row; Field spend =
  "Conferences" row. MQLs = distinct people added to a `Demo - ` or `Website - Product Tour` campaign in the month.
- Channel economics: Non-Field opps by Custom Source, spend from the budget sheet rows named in `CHANNELS`.
- Rates on fewer than 5 closed opps are marked `(n<5)`.
