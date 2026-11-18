---
name: icp
description: Product Marketing and ICP agent for AchieveIt. On the Friday before the second-Monday attribution review it posts inbound opps by market and segment (local government, state, education, commercial on its own line), year to date vs last year, with won, lost and open counts. Read-only. Use when the ICP routine fires or someone asks to "run ICP", "check ICP fit" or "which segments are producing opps".
---

# ICP fit (Product Marketing)

Load `cmo-system` first. All numbers come from `scripts/icp.py`; never compute, round or restate a number yourself, and never retype a
connector result (save it with `shared/capture.py`). Reviewer: Amanda (ICP and messaging).

**Reads** Salesforce Opportunity (read-only SOQL). **Writes** only Slack posts to #marketing-cmo through `shared/slack_post.py`.
It never edits Salesforce, targeting, campaigns or the website. Commercial stays excluded from targeting and is shown as its own line.

Set up: `R=<repo root>; S=$R/.claude/skills/icp/scripts/icp.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`. `D` = today in America/Denver.

## 1. Which run
`python3 $S --which D`. `"run": false` = finish with `ICP D: no pack today`. Otherwise it gives `month` (last month) and `review`.

## 2. Data (`references/queries.md`)
Run the one SOQL query in `references/queries.md` with `soqlQuery`, then
`python3 $C --tool soqlQuery --text --match-contains q="FROM Opportunity WHERE Type = 'New Business' AND CreatedDate >= 2025-01-01" --out $W/in/opps.json`.
The result is large and spills to a file; capture follows it. If it can't be read, post `:warning: ICP pack did not run: Salesforce unavailable` and stop.

## 3. Pack
1. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = STOP: post `:warning: ICP pack stopped: <message>`.
2. Top findings: from `$W/out/highlights.json` pick at most three; replace `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with one bullet each:
   `• <what, using the candidate's numbers>. <so what for the Non-Field goals>. Suggested: <owner and next step>.` Owner: Amanda
   (segments, messaging), Jonathan (goals). Only numbers from the candidate's `text`. Never recommend spend or targeting aimed at commercial.
   Edit the file with Python; do not retype the rest.
3. Post the parent with `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then `01_detail.txt` with `--thread-ts <ts>`.
   No `"ok": true`: stop and say so in the run line.

## 4. Finish
`ICP D: <month> pack, <n> findings, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Inbound = `Attribution_Source__c = 'Inbound'`, not `Demo_Attribution__c = 'Field Sourced'`, New Business, by created date.
- Segments come from `Market__c` and `Sub_Market__c`; Healthcare sits under Commercial in Salesforce and is shown inside Commercial.
- Win rates need 5 or more closed opps; segment win rates are direction only.
- Organization size against the SalesRoads thresholds is not checked (no field on opps); it is an open item for Amanda.
