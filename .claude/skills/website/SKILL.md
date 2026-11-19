---
name: website
description: Website and CRO agent for AchieveIt. On the Friday before the third-Monday website and SEO review it posts last month's GA4 results (sessions, key events, channels, top landing pages, conversion-path candidates) with a data-health check against Search Console. Read-only. Use when the Website routine fires or someone asks to "run the website pack", "check the website" or "CRO findings".
---

# Website and CRO

Load `cmo-system` first. All numbers come from `scripts/web.py`; never compute, round or restate a number yourself, and never retype a
connector result (save it with `shared/capture.py`). Reviewers: Cristina (website), Amanda (approver for site changes).

**Reads** Marketing Data Feeds.xlsx (GA4 and Search Console tabs). **Writes** only Slack posts to #marketing-cmo through
`shared/slack_post.py`. It never edits the site, GA4, tag manager or any workbook; every change is a suggestion for a person.

Set up: `R=<repo root>; S=$R/.claude/skills/website/scripts/web.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## Run
1. `python3 $S --which D`. `"run": false` = finish with `Website D: no pack today`. `"run": true` gives `month` (last month).
2. Data (feeds workbook ids in cmo-system `references/ids.md`): Feed_Status (sheet 2) first; if GA4_Monthly_Channel is not OK, post
   `:warning: Website pack did not run: GA4 feed is stale` and stop. Capture, one sheet per call, with
   `python3 $C --tool read_resource --text --match-contains uri=01IJF3MH7JFUTNS7AE3NGLRUZMTQX56HIL --match startPage=<n> --out $W/in/<file>`:
   sheet 4 -> `ga4_monthly.txt`, 5 -> `ga4_landing.txt`, 6 -> `ga4_events.txt`, 7 -> `gsc_daily.txt`.
   The big tabs are cut by the connector at about 190,000 characters: landing pages keeps the highest-traffic rows and key events keeps only the
   newest ~19 days. The script knows this and labels it.
3. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = post `:warning: Website pack stopped: <message>` and stop.
4. Top findings: read `$W/out/highlights.json`; pick at most three and replace the line `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with one bullet
   each: `• <what, using the candidate's own numbers>. <so what for the goal>. Suggested: <Cristina or Amanda and the next step>.` Only numbers from the
   candidate's `text`. No candidates = delete the line. Edit the file with Python; do not retype the rest.
5. Post with `python3 $R/shared/slack_post.py --weekly $W/out/slack/00_parent.txt $W/out/slack/01_detail.txt` (one reply in the week's Research log thread; see cmo-system, Posting).
   A post without `"ok": true`: stop and say so in the run line.
6. One line: `Website D: <month> pack, <n> findings, <posts> posts[, gaps: ...]`.

## Recommendations (what "Suggested" may say)
Concrete page moves are welcome: add or move a call to action (demo, product tour, pricing) on a named page; fix or check a tracking tag or
redirect; test a form placement or headline; link a high-traffic blog page to the product tour; remove a dead path. Say which page and what to try.
Check the monday.com 2026 Marketing Projects board first (for example "Improve placement/promotion/CTAs of product tour") and point to the
existing item instead of suggesting a duplicate. Suggestions go to Cristina (build) and Amanda (approve); the agent changes nothing.

## Rules the script applies (change only by pull request)
- GA4 is undercounted since the cookie banner (Jonathan, 2026-11-17: nothing to fix now). It is used for direction and page-to-page comparison only;
  MQLs come from Salesforce and search volume from Search Console. The data-health line (GA4 organic sessions as a share of Search Console clicks)
  should rise toward 100% if tracking is fixed.
- Key events come from GA4 (forms, phone calls). Phone calls (CallTrackerFX) often have no page ("(not set)").
- Candidates: a landing page with 50+ sessions and under 30% engaged; a pricing, solution, industry, product or demo page with 30+ sessions and no key events.
- Year-over-year change is reported but flagged as unreliable while GA4 coverage is partial.
