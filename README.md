# AchieveIt CMO

Claude agents and routines that run AchieveIt's marketing reporting, watch its marketing systems, and draft work for the
marketing team to approve. Plan: "AchieveIt Marketing Agent Team: Build Plan" (Claude doc).

**Status: phase 0, read-only and recommend-only.** No agent changes a record, publishes content, spends money or contacts
a customer or prospect.

## How it fits together
- Routines run in the **AchieveIt CMO** cloud environment with this repo attached. Skills load from `.claude/skills/`.
- Posts go to **#marketing-cmo** (private, channel `C0CJRL8KDRS`) as the **AchieveIt CMO** Slack bot via `shared/slack_post.py`.
- Marketing data arrives through Coefficient in **Marketing Data Feeds.xlsx** (SharePoint: Marketing Team > 00 - Key CMO
  Resources > Marketing Automation), refreshed daily at 5:00 AM Mountain. Agents read it; they never write to it.
- Separate from the finance agents (`achieveit-cfo`): different repo, bot, channel and environment. No shared code.

## Agents
| Agent | Skill | Phase |
|---|---|---|
| Shared rules | `cmo-system` | 0 |
| Marketing Ops (KPIs, attribution checks and performance, budget) | `marketing-ops` | 1 |
| SEO | `seo` | 1 |
| PM (board, meetings, follow-ups) | `marketing-pm` | 1 |
| CMO (weekly brief, monthly review) | `cmo-brief` | 1 |
| Paid Media; Website and CRO | `paid-media`, `website-cro` | 2 |
| Content and Social; Product and Customer | `content-social`, `product-customer` | 3 |

## Layout
| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules every agent follows |
| `.claude/skills/cmo-system/` | Shared rulebook: ICP, KPI definitions, goals, attribution rules, sources of truth, voice, IDs |
| `shared/slack_post.py` | The only way agents post to Slack |
| `docs/decisions.md` | Decisions and open items |

## Changing what agents do
Only through a pull request reviewed by Jonathan (or Amanda for content and voice rules). Agents never edit their own instructions.
