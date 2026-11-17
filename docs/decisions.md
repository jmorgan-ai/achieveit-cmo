# Decisions

- 2026-11-05: Separate marketing agent system modeled on the finance agents (scheduled runs, freshness check, run archive, named approvers).
- 2026-11-05: Marketing data comes through Coefficient (GA4, Search Console, Google Ads, Microsoft Ads, LinkedIn Pages) into one workbook. No custom API credentials.
- 2026-11-12: PM agent added. Work board = 2026 Marketing Projects (monday.com board 18396405978).
- 2026-11-17: Goals = Marketing Budget & Performance.xlsx 2026 plan. Non-Field is the main scorecard (525 MQLs, 155 opps, $720K ARR, $244,224 budget); Field on its own line (150, 60, $180K, $100,000); All is the total (675, 215, $900K, $344,224).
- 2026-11-17: Repo, Slack bot (AchieveIt CMO), channel #marketing-cmo (C0CJRL8KDRS) and cloud environment approved, separate from finance.
- 2026-11-17: Coefficient feeds live (13 of 15). Feed_Status reads tabs by name (INDIRECT), so renames don't break it.
- 2026-11-17: AchieveIt CMO Slack app live (chat:write only). Token is the AchieveIt CMO environment's network secret for slack.com; test post via shared/slack_post.py succeeded 3:17 PM MT.
- 2026-11-17: Marketing Budget & Performance.xlsx moved to Marketing Team > 00 - Key CMO Resources > Marketing Automation (new item 01IJF3MH3J7UDXQTLZMBEYDEP467WJHFJ4). Version history stays with the original on the Revenue Leadership Team site.

## Open
- Microsoft Ads Coefficient connection failing; tabs MSAds_* empty.
- Commercial organizations: keep excluded from the ICP or add segments that close (Jonathan, Amanda).
- Unlabeled dashboard goal $390K / $1.2M / $4.7M (Jonathan).
- ICP organization size outside SalesRoads thresholds (Amanda).
- GA4 undercounting organic vs Search Console (CookieYes consent item on hold since 2026-10-19).
