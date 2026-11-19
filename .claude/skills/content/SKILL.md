---
name: content
description: Content agent for AchieveIt (blog and SEO content, webinars, content strategy pillars, and social as one section). On the Friday before the fourth-Monday content and brand review it files last month's content results (blog pages from Search Console, page-two refresh and new-post candidates, pillar spread, webinar campaigns) and LinkedIn results with draft post ideas for Amanda and Cristina to approve. Read-only; never publishes. Use when the Content routine fires or someone asks to "run content", "what should we write", "blog performance", "check LinkedIn" or "post the social pack".
---

# Content (blog, SEO content, webinars, pillars, social)

Load `cmo-system` first (voice and checklist: `references/voice.md`). All numbers come from `scripts/content.py` (which runs `social.py` for the LinkedIn section); never compute,
round or restate a number yourself, and never retype a connector result (save it with `shared/capture.py`).
Reviewers: Amanda and Cristina (content and brand). Approver for anything public: Amanda. SEO owns site health and rankings; this agent owns **what to write, refresh and promote**,
and reads the same Search Console data to decide. The Product Marketing agent supplies the messages to test; the strategy doc (12/2 to 12/3 session) sets the pillars (`references/pillars.md`).

**Reads** Marketing Data Feeds.xlsx (GSC, GA4 and LI tabs), Buffer (read only: posts and their metrics) and Salesforce Campaign (read-only SOQL, webinars). **Writes** only Slack posts through `shared/slack_post.py`.
It never posts to LinkedIn, Buffer or the website, and uses only Buffer's read tools (`get_account`, `list_channels`, `list_posts`, `get_post`, `get_aggregated_post_metrics`); never `create_post`, `edit_post`, `delete_post`, ideas, tags or templates. Drafts are text in the Slack thread for a person to use.

Set up: `R=<repo root>; S=$R/.claude/skills/content/scripts/content.py; C=$R/shared/capture.py; W=$(mktemp -d); mkdir -p $W/in $W/out`.
`D` = today in America/Denver.

## 1. Which run
`python3 $S --which D`. `"run": false` = nothing today, finish with `Content D: no pack today`. `"run": true` gives `month`
(last month; review Monday in `review`). If someone asks by name on another day, use last month and today's date.

## 2. Data (`references/routine.md` lists the captures)
Feed_Status (sheet 2) first; mark any input whose status is not OK as a gap. Then LI_Posts (15), LI_Page_Daily (16), LI_Followers (17), GSC_Pages (9), GSC_Queries (8), GA4_Landing_Pages (5),
each captured to `$W/in`. Then Buffer sent posts for the month and the Salesforce webinar campaigns (`references/routine.md`). Everything but LI_Posts is optional: if it fails, mark the gap and continue.
If LI_Posts can't be read, post `:warning: Content pack did not run: LinkedIn feed unavailable` (top level, no `--weekly`) and stop.

## 3. Pack
1. `python3 $S --mode pack --month <month> --asof D --in $W/in --out $W/out`. Exit 2 = STOP: post `:warning: Content pack stopped: <message>` top level.
   It writes `00_parent.txt` (title and `{TOP_FINDINGS}`), `10_content.txt` (blog and content pages, pillar spread, page-two searches, webinars), `20_social.txt` (LinkedIn), `highlights.json`.
2. Top findings: from `$W/out/highlights.json` pick at most three, **content first** (a refresh or new-post candidate, a thin pillar, a webinar result) unless a social result is clearly bigger;
   replace `{TOP_FINDINGS}` in `00_parent.txt` with one bullet each: `• <what, using the candidate's own numbers>. <so what>. Suggested: <owner and next step>.`
   Owners: Cristina (writing, refreshes, images), Amanda (what to publish, approvals, webinars). Only numbers from the candidate's `text`. Edit the file with Python; do not retype the rest.
   Read small numbers honestly: most posts reach under 150 people, so one post is a signal, not a trend.
3. **Content ideas** (`$W/out/slack/05_ideas.txt`, titled `*Content ideas for next month*`): up to three, each one line: working title, the evidence (a page-two search or refresh candidate from `10_content.txt`, or a message from the
   Product Marketing pack if it is in the thread this week), pillar, format (blog, webinar, LinkedIn series), owner suggestion. Evidence only from the pack; no keyword volumes or rankings you did not copy.
   If the strategy doc session has not happened (before 2026-12-04), say the pillars are draft.
4. **Social drafts** (`$W/out/slack/30_drafts.txt`): up to four LinkedIn drafts for the coming month, each 60 to 120 words, headed
   `Draft n (pillar: <name>)`. Rules:
   - Pass every item of the voice checklist. Practitioner voice, one idea, a point of view, "strategy execution", no AI tells.
   - Use only facts you can cite: a number needs its primary source and year in a line under the draft; a customer is named only if
     public (public dashboards page or published story). No invented quotes, results or customer moments. Where a real customer moment or quote is needed,
     write `[Cristina: add a real customer moment]` rather than making one up.
   - Local government, state agencies and public health first; never aim copy at commercial.
   - Suggest an image or GIF idea in one line; do not generate or attach images. Follow `references/creative.md`.
   - Close with `Draft only. Nothing is scheduled or posted. Amanda approves before anything is used.`
5. Post: `python3 $R/shared/slack_post.py --weekly $W/out/slack/*.txt` (name order: parent, content, ideas, social, drafts; one reply in the week's Research log thread, see cmo-system, Posting). No `"ok": true`: stop and say so in the run line.

## 4. Finish
One line: `Content D: <month> pack, <n> findings, <n> ideas, <posts> posts[, gaps: ...]`.

## Rules the script applies (change only by pull request)
- Content pages = Search Console pages whose address contains `/blog/`, `/resources/`, `/podcast`, `/webinar` or `/case-studies`. Pillar sort is by keywords in the page address or query (`references/pillars.md`); it is rough and says so.
- Page-two = average position 8 to 20 with 300 or more impressions in 28 days. A query is matched to a page when they share two or more address words; otherwise it is a new-post candidate.
- GA4 undercounts (cookie banner): GA4 numbers show relative size only; Search Console is the volume source.
- Webinar counts are Salesforce campaign fields; the opps they produced are attributed by the attribution rules, not by the campaign count.
- Engagement rate is recomputed as (clicks + reactions + comments + shares) / impressions; the feed's own column is ignored.
- Month totals need every day of the month in the follower and page feeds (about 90 days kept); partial months are left out and listed as a gap.
- LinkedIn feed captions are cut at 25 characters. Buffer gives full captions, image, GIF or video, and reach. Posts made directly on LinkedIn (via network) show only a thumbnail in Buffer, so their image or GIF type is not reliable. Buffer has no click counts. Format comparisons need 3 or more posts per format. The pack does not label themes.
- Follower numbers are gains only (organic and paid), not the page total.
