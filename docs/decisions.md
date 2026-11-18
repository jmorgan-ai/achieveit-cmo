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
- 2026-11-17 (Jonathan): Field (conference) spend uses a $75,000 a year placeholder (Finance plan, spread evenly) until actuals are pulled; the pack flags it as a placeholder (ops.py FIELD_PLACEHOLDER_ANNUAL).
- 2026-11-17 (Jonathan): The $390K / $1.2M / $4.7M on the Salesforce attribution dashboards is a new-pipeline goal at a standard ~$30K per opp (13 opps a month, about 39 a quarter, about 155 a year). Opps are not valued when created, so it is not tracked; the opp goals already carry it.
- 2026-11-17 (Jonathan): GA4 undercount is the CookieYes banner; nothing to fix. Use Search Console for search volume and treat GA4 traffic as undercounted.
- 2026-11-17: SEO agent built: posts the Friday before the third Monday (Search Console results, top pages, page-two queries, low-CTR pages, Semrush site audit). shared/capture.py now follows the `<persisted-output>` spill so a large sheet is never saved as a 2 KB preview.
- 2026-11-18: PM agent built (Mondays 5:20 AM MT): one short note from the monday.com board (done last week, focus now, needs a call). Read-only; Notion drafting and email wait for an approval path. CookieYes consent item is left on hold on purpose.
- 2026-11-18: Paid agent built (Google Ads; Fridays 5:25 AM MT, posts the Friday before the second Monday) and Website agent built (GA4; Fridays 5:45 AM MT, posts the Friday before the third Monday). Both read-only. Google Ads spend ties to the budget sheet ($3,037 in Oct).
- 2026-11-18: Connector reads of big feed tabs cut off near 190,000 characters, so GA4 landing pages keeps the top-traffic rows and GA4 key events only the newest ~19 days; the agents label this.
- 2026-11-18 (Jonathan): Paid and Website suggestions may be concrete moves (shift budget between campaigns, add negative keywords, pause, add CTAs, fix tracking) but never a higher total budget; shifts are judged on Salesforce opps by channel, not platform conversions.

## Open
- Pull Field conference actuals (QuickBooks GL 73400) to replace the $75,000 placeholder (Jonathan, later).
- Microsoft Ads Coefficient connection failing; tabs MSAds_* empty. Jonathan to contact Coefficient. Ops uses the budget sheet Bing row and Salesforce Custom Source "Paid - Bing" meanwhile.
- GA4 sessions are down 95% vs Oct 2025 and capture 44% of Search Console clicks; the monday item "Fix CookieYes settings for US visitors" is on hold (Jonathan decided nothing to do; revisit if GA4 matters).
- ICP organization size outside SalesRoads thresholds (Amanda).
