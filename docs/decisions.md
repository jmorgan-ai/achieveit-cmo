# Decisions

- 2026-11-05: Separate marketing agent system modeled on the finance agents (scheduled runs, freshness check, run archive, named approvers).
- 2026-11-05: Marketing data comes through Coefficient (GA4, Search Console, Google Ads, Microsoft Ads, LinkedIn Pages) into one workbook. No custom API credentials.
- 2026-11-12: PM agent added. Work board = 2026 Marketing Projects (monday.com board 18396405978).
- 2026-11-17: Goals = Marketing Budget & Performance.xlsx 2026 plan. Non-Field is the main scorecard (525 MQLs, 155 opps, $720K ARR, $244,224 budget); Field on its own line (150, 60, $180K, $100,000); All is the total (675, 215, $900K, $344,224).
- 2026-11-17: Repo, Slack bot (AchieveIt CMO), channel #marketing-cmo (C0CJRL8KDRS) and cloud environment approved, separate from finance.
- 2026-11-17: Coefficient feeds live (13 of 15). Feed_Status reads tabs by name (INDIRECT), so renames don't break it.
- 2026-11-17: AchieveIt CMO Slack app live (chat:write only). Token is the AchieveIt CMO environment's network secret for slack.com; test post via shared/slack_post.py succeeded 3:17 PM MT.
- 2026-11-17: Marketing Budget & Performance.xlsx moved to Marketing Team > 00 - Key CMO Resources > Marketing Automation (new item 01IJF3MH3J7UDXQTLZMBEYDEP467WJHFJ4). Version history stays with the original on the Revenue Leadership Team site.
- 2026-11-17: Marketing Ops agent built. Weekdays 5:35 AM MT: flags new opps that break an attribution rule (posts only when one does). KPI pack for the first-Monday review, attribution and performance pack for the second-Monday review (both post the Friday before; see the next line). Fixes are proposals; the full list posts in the Slack thread, nothing is written to Salesforce or SharePoint.
- 2026-11-17: MQL = distinct people added to a Demo or Product Tour campaign in the month (Salesforce). Jan-Oct 2026: 282 vs 263 in the budget sheet's hand count.
- 2026-11-17: Review calendar confirmed by Jonathan: first Monday KPIs, second Monday attribution, each for last month, or last quarter when last month ends one. The KPI pack posts Monday morning instead of Friday when that Friday is before month end.
- 2026-11-17: Original Marketing Budget & Performance.xlsx deleted after the move (recycle bin, 93 days).
- 2026-11-17 (Jonathan): Commercial stays excluded from marketing campaigns and targeting, but counts in KPIs and inbound leads; reported as its own breakdown line.
- 2026-11-17 (Jonathan): 2027 goals are still being set; use the 2026 goals for 2027 until replaced. ops.py PLAN_YEARS now includes 2027; spend is left out until the budget sheet has a "2027 Spend" sheet.
- 2026-11-17 (Jonathan): Conference spend comes from the company budget files (Finance), not the marketing budget sheet. Finance "2026-2027 Expenses_20260722.xlsx" > "Vendors and Annual": Field Marketing Conferences (GL 73400) = $120,000 in 2025, $75,000 planned for 2026 and 2027. That is a plan figure, not actuals; actuals still to be pulled from QuickBooks (GL 73400).

## Open
- Field spend for cost per opp: the budget sheet shows $0 for conferences; Finance plans $75,000 for 2026. Decide whether Ops uses plan or QuickBooks actuals (73400) once pulled.
- Microsoft Ads Coefficient connection failing; tabs MSAds_* empty. Ops uses the budget sheet Bing row and Salesforce Custom Source "Paid - Bing" meanwhile.
- ICP organization size outside SalesRoads thresholds (Amanda).
- GA4 undercounting organic vs Search Console (CookieYes consent item on hold since 2026-10-19).
