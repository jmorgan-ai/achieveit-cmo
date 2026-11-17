---
name: cmo-system
description: Shared rulebook for AchieveIt's marketing agents (ICP, KPI definitions, 2026 goals, attribution rules, sources of truth, reporting calendar, brand voice, finding format). Load first in every marketing routine (Marketing Ops, SEO, PM, Paid Media, Website and CRO, Content and Social, Product and Customer, CMO Brief) and whenever someone asks how marketing counts or attributes something.
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
- **Excluded:** commercial and nonprofit. Under review: always report Commercial on its own line (Salesforce `Market__c`), never
  mixed into ICP figures.

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
pipeline over $325K. Field: about 12.5 MQLs, 5 opps, $15K ARR a month. The dashboards' unlabeled $390K / $1.2M / $4.7M goal
is left out until confirmed.

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

Feed freshness: read the Feed_Status tab first. Coefficient tabs have a banner in row 1, headers in row 2, data from row 3.
GA4 organic volume is undercounted (consent); use GSC for search volume until that's fixed.

## Reporting calendar and timing
- Reviews are the Mondays of the month, each covering last month (and last quarter when last month ends one):
  first Monday KPIs (Jonathan; Ops pack), second Monday attribution (Amanda; Ops and Paid), third Monday website and SEO
  (Cristina, Amanda), fourth Monday social and brand (Amanda, Cristina). Packs post the Friday before the review Monday;
  when that Friday falls before the month has closed (first Monday on the 1st to 3rd), the KPI pack posts that Monday morning.
- Mondays: PM drafts the where-we-stand section of the week's Notion meeting page; CMO posts the weekly brief.
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
One post per run, short parent plus detail in thread. Write the message to a file, then
`python3 shared/slack_post.py msg.txt [--thread-ts <ts>]`.
