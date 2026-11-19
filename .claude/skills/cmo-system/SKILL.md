---
name: cmo-system
description: Shared rulebook for AchieveIt's marketing agents (ICP, messaging, KPI definitions, 2026 goals, attribution rules, sources of truth, reporting calendar, brand voice, finding format). Load first in every marketing routine (Marketing Ops, SEO, PM, Paid Media, Website and CRO, Content, Product Marketing, Customers, CMO Strategist, Ask CMO, Health) and whenever someone asks how marketing counts or attributes something.
---

# AchieveIt marketing rulebook

Follow `CLAUDE.md` at the repo root. IDs are in `references/ids.md`; brand voice and the content checklist are in
`references/voice.md`. If this rulebook doesn't cover a case, stop, flag it for the CMO brief, and don't guess.

## Who we sell to
- **ICP industries:** government (federal, state, local, public health, special districts), education (higher ed, K-12), healthcare.
  Local government is the growth priority.
- **Core four segments:** state agencies, local public health, cities, counties.
- **Thresholds (SalesRoads):** cities and counties 50,000+ population; local health departments serving 75,000+; universities
  5,000+ enrollment; school districts $500M+ operating budget; local police serving 250,000+; airports 5,000+ employees; state
  agencies under a main state department (DOT, public health or HHS, administration).
- **Personas:** primary = decision-makers with budget and authority (CSO, COO, strategic planning lead); secondary = people who run
  the planning process.
- **Excluded from campaigns and targeting:** commercial and nonprofit (decided by Jonathan 2026-11-17). Commercial that comes in
  inbound still counts in KPIs (MQLs, opps, won) and as inbound leads; always show Commercial as its own breakdown line
  (Salesforce `Market__c`) so ICP results can be read without it. Never recommend spend or targeting aimed at commercial.

## Definitions
- **Lifecycle:** Prospect, MQL, SAL, SQL, Opportunity, Customer, Advocate.
- **MQL:** hand-raiser with bottom-of-funnel intent (demo request, pricing request, product tour). Counted as distinct people added
  that month to a Salesforce campaign named `Demo - ...` or `Website - Product Tour...` (this covers the pricing request).
  Content downloads and lead scores never count. The budget sheet's hand count runs a little lower (263 vs 282, Jan to Oct 2026).
- **Opps:** `Type = 'New Business'`, `Attribution_Source__c = 'Inbound'`, excluding `Demo_Attribution__c = 'Field Sourced'`.
- **Late-stage pipeline:** those inbound opps in stage Proposal or Verbal.
- **Won / lost:** stage `5a - Closed Won` / `5b - Closed Lost`. Win rate = won / (won + lost); open opps excluded.
- **ARR:** `Amount` on a won New Business opp, treated as first-year ARR.
- **Field:** Field Sourced opps and event leads, always on their own line.

## 2026 goals (Marketing Budget & Performance.xlsx plan)
Non-Field is marketing's main scorecard; Field on its own line; All is the total.

| | All | Non-Field | Field |
|---|---|---|---|
| Budget | $344,224 | $244,224 | $100,000 |
| MQLs | 675 | 525 | 150 |
| MQL to opp | 32% | 30% | 40% |
| Opps | 215 | 155 | 60 |
| Opp to won | 14% | 15% | 10% |
| Won deals | 30 | 24 | 6 |
| ASP | $28,000 | $30,000 | $30,000 |
| ARR | $900,000 | $720,000 | $180,000 |
| CPL | $510 | $465 | $667 |
| Cost per opp | $1,601 | $1,576 | $1,667 |
| CAC | $11,474 | $10,176 | $16,667 |
| CAC payback (months) | 4.6 | 4.1 | 6.7 |
| Spend per $1 ARR | $0.38 | $0.34 | $0.56 |

Pacing is even through the year. Non-Field: 44 MQLs, 13 opps, $60K ARR a month; 10 MQLs and 4 opps a week; late-stage
pipeline over $325K. Field: about 12.5 MQLs, 5 opps, $15K ARR a month. The Salesforce dashboards' $390K / $1.2M / $4.7M
is a new-pipeline goal at a standard ~$30K per opp (the opp goals above); opps aren't valued when created, so it isn't tracked.
2027 goals are not set; until Jonathan replaces them, 2027 uses the 2026 numbers. Field spend uses a $75,000 a year placeholder
(Finance's conference plan) until actuals are pulled.

## Attribution rules (Confluence: AchieveIt Marketing Philosophy)
Fields: `Demo_Attribution__c` (Attribution), `Attribution_Source__c` (Inbound, Outbound, Growth, Partner), `CampaignId`
(Primary Campaign Source; name in `Primary_Campaign_Source_Name__c`). Channel detail: `Custom_Source__c`, UTM fields.
- **Marketing Sourced:** came in through a marketing campaign: website forms, marketing-run events **and webinars**, email, social.
- **Field Sourced:** met at a field event such as a conference. Inbound if they booked the meeting with us there; else Outbound.
- **OSDR Sourced:** SalesRoads outreach. Always Outbound.
- **AE Sourced:** the AE's own outreach, or a lead contacting the AE directly. Outbound.
- **Referral:** heard from a customer or other contact. **Partner Sourced:** brought by a third party; Attribution Source = Partner.
- **9-month rule for reopened opps:** under 9 months since the earlier opp closed lost, keep the original attribution. Over 9
  months and they simply reach back out, keep it. Over 9 months through a different channel, new attribution (a new AE
  Sourced needs a reply to the AE's outreach or steady outreach before it). Unclear cases go to revenue leadership.
- Every opp needs both Attribution and Attribution Source. Test records are flagged for deletion.

## Sources of truth
| Number | Source | Not this |
|---|---|---|
| MQLs, opps, pipeline, ARR, attribution | Salesforce | GA4 or ad-platform conversions |
| Traffic, landing pages, key events | GA4 tabs in Marketing Data Feeds.xlsx | Semrush estimates |
| Search clicks, impressions, position | GSC tabs | Semrush estimates |
| Rankings, site health, competitors | Semrush project 23016017 | older Semrush projects |
| Ad spend, clicks, search terms | GAds / MSAds tabs (`Cost Micros` is already in dollars) | budget sheet |
| Budget by line | Marketing Budget & Performance.xlsx | ad platforms |
| LinkedIn | LI tabs (`Engagement` column unreliable: recompute) | Buffer |
| Projects, owners, due dates | monday.com 2026 Marketing Projects | meeting notes |
| Meeting decisions and action items | Notion Marketing Meetings pages | memory |
| What prospects say about how they heard of us | Salesforce Opportunity `Lead_Source_Mentioned__c` (free text from the demo form) | tracked attribution |
| Whether we may name a customer, logo or story | Salesforce Account `PR_Status__c` | anyone's memory |
| Public dashboards | Salesforce Account `Public_Dashboard_Available__c`, `Public_Dashboard_s__c` (link) and achieveit.com/public-dashboards | |
| Published customer stories | achieveit.com/resources/case-studies | |
| Open suggestions and their status | monday.com board 18440658365 "Marketing Agent Open Items" | Slack threads |

Feed freshness: read the Feed_Status tab first. Coefficient tabs have a banner in row 1, headers in row 2, data from row 3.
GA4 organic volume is undercounted (consent); use GSC for search volume until that's fixed.

## Reporting calendar and timing
- Reviews are the Mondays of the month, each covering last month (and last quarter when last month ends one):
  first Monday KPIs (Jonathan; Ops pack), second Monday attribution (Amanda; Ops and Paid), third Monday website and SEO
  (Cristina, Amanda), fourth Monday content, social and brand (Amanda, Cristina). Packs post the Friday before the review Monday;
  when that Friday falls before the month has closed (first Monday on the 1st to 3rd), the KPI pack posts that Monday morning.
- Mondays: PM drafts the where-we-stand section of the week's Notion meeting page; the CMO Strategist posts the weekly CMO brief (6:10 AM, the one message to read; a short reply per agent links to each full pack in the Research log) and keeps the open items log.
- Weekdays: Health checks that what was due posted and nothing is paused or stale. Anytime: Ask CMO answers questions and records decisions when someone writes to the bot in #marketing-cmo.
- Weeks run Sunday to Saturday; calendar months; all dates America/Denver.
- Every scheduled run finishes before 9:00 AM Eastern. Coefficient refresh 5:00 AM MT. Avoid the finance slots
  (4:15, 4:40, 6:00, 6:20 AM MT).
- Small numbers: flag any rate built on fewer than 5 closed opps; show trailing 6 months beside the month.

## Finding format
- **What:** one sentence with the number.
- **Evidence:** source, record or page, value, as-of date.
- **So what:** impact on a goal or decision.
- **Suggested owner and next step:** a person, never an action taken.
Rank by impact on the Non-Field goals. Findings about people's work go to the meeting page or the CMO brief, never as direct nudges.

## Posting
**One quiet channel.** #marketing-cmo has three kinds of top-level posts and nothing else: the Monday **CMO brief** (the Strategist), the week's
**Research log** line (one short post per week, created by the first agent that posts), and `:warning:` / Health alerts.
Every agent's pack, daily flag and detail goes in the Research log thread, so a pack is one reply, not a parent plus replies.
- Write the message files, then post them all in one call: `python3 $R/shared/slack_post.py --weekly <file> [<file> ...]`.
  The script finds or creates this week's Research log post, tidies spacing, joins files into as few replies as fit, and prints `"ok": true` per reply.
- First line of a pack = its title: `:emoji: *<Agent title>, <month or week>*`. Keep the title strings in each skill; the Strategist and Health find packs by them.
- If it prints `weekly_lookup_failed` (exit 3), do not post another way. Read the channel for the week (`slack_read_channel`), find the bot post whose text contains the
  `marker` it printed, and post with `--thread-ts <that ts>`; if none exists, post with `--weekly-create`. If channel reading also fails, say so in the run line and stop.
- Failures (`:warning: ... did not run`) are the exception: post them top level, without `--weekly`, so someone sees them.
- Findings read best short: a title, then at most three bullets `• what. so what. Suggested: owner and next step.`, then details. Blank lines are added for you.
