---
name: seo
description: SEO agent for AchieveIt. On the Friday before the third-Monday website and SEO review it posts last month's Search Console results (clicks, impressions, position, top pages, page-two queries, low-CTR pages) and Semrush site-audit health. Read-only. Use when the SEO routine fires or someone asks to "run SEO", "post the SEO pack" or "check search performance".
---

# SEO

Load `cmo-system` first. All numbers come from `scripts/seo.py`; never compute, round or restate a number yourself, and never
retype a connector result (save it with `shared/capture.py`). Reviewer: Cristina (website, SEO); approver for site changes: Amanda.

**Reads** Marketing Data Feeds.xlsx (GSC, GA4 tabs) and Semrush project 23016017. **Writes** only Slack posts to #marketing-cmo
through `shared/slack_post.py`. It never edits the site, Semrush, or any workbook: every fix is a suggestion for a person.

Set up: `R=<repo root>; S=$R/.claude/skills/seo/scripts/seo.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## 1. Which run
`python3 $S --which D`. `"run": false` = nothing today, finish with `SEO D: no pack today`. `"run": true` gives `month` (last
month; the review Monday is in `review`). If someone asks for the pack by name on another day, use last month and today's date.

## 2. Data (queries in `references/queries.md`)
1. Feeds workbook (`read_resource`, ids in cmo-system `references/ids.md`): Feed_Status (sheet 2) first. Mark any SEO input whose
   status is not OK as a gap and leave out what depends on it. Then GSC_Daily (7), GSC_Queries (8, first page only), GSC_Pages (9),
   GA4_Monthly_Channel (4). Capture each to `$W/in`.
2. Semrush: `site_audit` `info` -> `$W/in/audit_info.json`; position tracking is optional (see queries.md).
3. If GSC_Daily can't be read, post `:warning: SEO pack did not run: Search Console unavailable` and stop.

## 3. Pack
1. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = STOP: post
   `:warning: SEO pack stopped: <message>` and stop.
2. Top findings: read `$W/out/highlights.json`; pick at most three that matter most for Non-Field inbound growth and replace the line
   `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with one bullet each:
   `• <what, using the candidate's own numbers>. <so what for the goal>. Suggested: <owner and next step>.`
   Owners: Cristina (titles, descriptions, technical fixes), Amanda (content, new pages). Only numbers from the candidate's `text`.
   No candidates = delete the line. Edit the file with Python; do not retype the rest.
3. Post the parent with `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then each other file in
   `$W/out/slack/` with `--thread-ts <ts>`. A post without `"ok": true`: stop posting and say so in the run line.

## 4. Finish
One line: `SEO D: <month> pack, <n> findings, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Search volume comes from Search Console, never GA4: GA4 organic is undercounted since the cookie banner (known, nothing to fix).
- Month totals need every day of the month in the 90-day feed; partial months are left out and listed as a gap.
- Low CTR candidate: top-10 average position, 5,000+ impressions in 28 days, CTR under 0.5%.
- Page-two opportunity: average position 8 to 20, 300+ impressions in 28 days.
- Site audit: errors up, or warnings up by more than 500 in one crawl, become findings. A big jump after a crawl change is checked
  before it is called real.
