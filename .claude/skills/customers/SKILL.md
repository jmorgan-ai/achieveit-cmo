---
name: customers
description: Customer Marketing agent for AchieveIt. On the Friday before the fourth-Monday social and brand review it posts customer story candidates (government customers closed won 6+ months ago, local government first) and whether each was already featured on LinkedIn. Read-only; contacts no customer. Use when the Customers routine fires or someone asks "who could we feature", "customer story ideas" or "run customers".
---

# Customer Marketing

Load `cmo-system` first. All numbers come from `scripts/customers.py`; never compute or retype a number, and save connector results with `shared/capture.py`.
Reviewers: Amanda and Cristina. **Reads** Salesforce Opportunity and Buffer sent posts (read-only). **Writes** only Slack posts to #marketing-cmo via `shared/slack_post.py`.
It never contacts a customer, drafts to one, or posts or publishes anything. Customer names only go to the team in Slack; a story is public only after the customer agrees.

Set up: `R=<repo root>; S=$R/.claude/skills/customers/scripts/customers.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`. `D` = today in America/Denver.

## 1. Which run
`python3 $S --which D`. `"run": false` = finish with `Customers D: no pack today`. Otherwise it gives `month` and `review`.

## 2. Data (`references/queries.md`)
Run the Salesforce query, capture to `$W/in/opps.json`. If unreadable, post `:warning: Customers pack did not run: Salesforce unavailable` and stop.
Then the Buffer `list_posts` capture to `$W/in/buffer_posts.json`; if Buffer fails, continue without it (the pack says the check was not run).

## 3. Pack
1. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = post `:warning: Customers pack stopped: <message>` and stop.
2. Top findings: from `$W/out/highlights.json` pick at most three; replace `{TOP_FINDINGS}` in `00_parent.txt` with one bullet each:
   `• <what, using the candidate's numbers>. <so what for social and content>. Suggested: <owner and next step>.` Owner: Cristina (public check, story draft), Amanda (approval). Only numbers from the candidate's `text`.
   Next step is always to check public status first; never "email the customer" or "ask the customer" as something the agent does.
3. Post the parent with `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then `01_detail.txt` with `--thread-ts <ts>`. No `"ok": true`: stop and say so.

## 4. Finish
`Customers D: <month> pack, <n> candidates, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Government accounts only (commercial is not a story focus); one row per account, largest won opp; ripe = closed 6 or more months ago.
- Order: Local Government, State Government, then others, each by ARR.
- Featured = a sent Buffer post names the account in the last 12 months; posts made directly on LinkedIn may be missing.
- Public status (case study, press release) is not checked by any source yet; every candidate needs a human check.
