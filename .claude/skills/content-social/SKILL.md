---
name: content-social
description: Content and Social agent for AchieveIt. On the Friday before the fourth-Monday social and brand review it posts last month's LinkedIn results (posts, impressions, engagement rate, top posts, followers, company page views) and a few draft post ideas for Amanda and Cristina to approve. Read-only; never publishes. Use when the Content and Social routine fires or someone asks to "run social", "post the social pack" or "check LinkedIn".
---

# Content and Social

Load `cmo-system` first (voice and checklist: `references/voice.md`). All numbers come from `scripts/social.py`; never compute,
round or restate a number yourself, and never retype a connector result (save it with `shared/capture.py`).
Reviewers: Amanda and Cristina (social and brand). Approver for anything public: Amanda.

**Reads** Marketing Data Feeds.xlsx (LI tabs). **Writes** only Slack posts to #marketing-cmo through `shared/slack_post.py`.
It never posts to LinkedIn, Buffer or the website; drafts are text in the Slack thread for a person to use.

Set up: `R=<repo root>; S=$R/.claude/skills/content-social/scripts/social.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## 1. Which run
`python3 $S --which D`. `"run": false` = nothing today, finish with `Social D: no pack today`. `"run": true` gives `month`
(last month; review Monday in `review`). If someone asks by name on another day, use last month and today's date.

## 2. Data (`references/routine.md` lists the captures)
Feed_Status (sheet 2) first; mark any LinkedIn input whose status is not OK as a gap. Then LI_Posts (15), LI_Page_Daily (16),
LI_Followers (17), each captured to `$W/in`. If LI_Posts can't be read, post `:warning: Social pack did not run: LinkedIn feed unavailable` and stop.

## 3. Pack
1. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = STOP: post `:warning: Social pack stopped: <message>`.
2. Top findings: from `$W/out/highlights.json` pick at most three; replace `{TOP_FINDINGS}` in `$W/out/slack/00_parent.txt` with one bullet each:
   `• <what, using the candidate's own numbers>. <so what>. Suggested: <owner and next step>.` Owners: Amanda (what to post, approvals),
   Cristina (writing and images). Only numbers from the candidate's `text`. Edit the file with Python; do not retype the rest.
   Read small numbers honestly: most posts reach under 150 people, so one post is a signal, not a trend.
3. Draft post ideas (`$W/out/slack/02_drafts.txt`): up to four LinkedIn drafts for the coming month, each 60 to 120 words, headed
   `Draft n (pillar: <name>)`. Rules:
   - Pass every item of the voice checklist. Practitioner voice, one idea, a point of view, "strategy execution", no AI tells.
   - Use only facts you can cite: a number needs its primary source and year in a line under the draft; a customer is named only if
     public (public dashboards page or published story). No invented quotes, results or customer moments. Where a real customer moment or quote is needed,
     write `[Cristina: add a real customer moment]` rather than making one up.
   - Local government, state agencies and public health first; never aim copy at commercial.
   - Suggest an image or GIF idea in one line (brand colors and Poppins from voice.md); do not generate or attach images.
   - Close with `Draft only. Nothing is scheduled or posted. Amanda approves before anything is used.`
4. Post the parent with `python3 $R/shared/slack_post.py $W/out/slack/00_parent.txt`, keep `ts`, then each other file with `--thread-ts <ts>`.
   A post without `"ok": true`: stop posting and say so in the run line.

## 4. Finish
One line: `Social D: <month> pack, <n> findings, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Engagement rate is recomputed as (clicks + reactions + comments + shares) / impressions; the feed's own column is ignored.
- Month totals need every day of the month in the follower and page feeds (about 90 days kept); partial months are left out and listed as a gap.
- Captions are cut at 25 characters and post type is not in the feed, so the pack does not label themes or formats.
- Follower numbers are gains only (organic and paid), not the page total.
