---
name: paid
description: Paid media agent for AchieveIt (Google Ads; Microsoft Ads when connected). On the Friday before the second-Monday attribution review it posts last month's ad spend, clicks and cost per click by campaign, a tie-out to the budget sheet, campaigns losing impressions to budget, and search terms that spent with no conversion. Read-only: never changes budgets, bids or campaigns. Use when the Paid routine fires or someone asks to "run paid", "check Google Ads" or "post the paid pack".
---

# Paid

Load `cmo-system` first. All numbers come from `scripts/paid.py`; never compute, round or restate a number yourself, and never
retype a connector result (save it with `shared/capture.py`). Reviewer and approver for any paid change: Amanda.

**Reads** Marketing Data Feeds.xlsx (Google Ads tabs) and the budget sheet. **Writes** only Slack posts to #marketing-cmo through
`shared/slack_post.py`. No spend: it never changes budgets, bids, keywords or campaigns. Every change is a suggestion for Amanda.

Set up: `R=<repo root>; S=$R/.claude/skills/paid/scripts/paid.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## Run
1. `python3 $S --which D`. `"run": false` = finish with `Paid D: no pack today`. `"run": true` gives `month` (last month).
2. Data (feeds workbook ids in cmo-system `references/ids.md`; sheets 2, 10, 11): Feed_Status first; if GAds_Campaign_Daily is not OK, post
   `:warning: Paid pack did not run: Google Ads feed is stale` and stop. Capture:
   `python3 $C --tool read_resource --text --match-contains uri=01IJF3MH7JFUTNS7AE3NGLRUZMTQX56HIL --match startPage=10 --out $W/in/gads_campaign.txt`
   and the same with `startPage=11 --out $W/in/gads_terms.txt`. Budget sheet: query F in `marketing-ops/references/queries.md`,
   saved to `$W/in/budget.txt` (optional; without it the tie-out is left out and the post says so).
3. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = post `:warning: Paid pack stopped: <message>` and stop.
4. Top findings: read `$W/out/highlights.json`; pick at most three and replace the line `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with one
   bullet each: `• <what, using the candidate's own numbers>. <so what for the goal>. Suggested: <Amanda and the next step>.` Only numbers from the
   candidate's `text`. No candidates = delete the line. Edit the file with Python; do not retype the rest.
5. Post the parent with `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then `01_detail.txt` with `--thread-ts <ts>`.
   A post without `"ok": true`: stop and say so in the run line.
6. One line: `Paid D: <month> pack, <n> findings, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Spend, clicks and impressions are Google Ads. Platform-reported conversions are never counted as results (Salesforce is the source of truth);
  opps and won ARR by channel live in the Ops attribution post.
- Tie-out: feed spend vs the budget sheet's Google Ads row; more than 5% apart becomes a finding.
- Budget-limited: an enabled non-brand campaign losing 40% or more of search impressions to budget.
- Search terms: non-brand terms with $25+ spend and no platform conversion in the 30-day feed. These are review candidates, not automatic
  negatives: a core term (for example "strategic planning software") may just need more time or a better page.
- The feed has weekday rows only; months are checked for coverage before they are totalled.
- Microsoft Ads: not connected (Coefficient). Until it is, the post says Google only, and Microsoft spend is visible only on the budget sheet.
