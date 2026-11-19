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
| Agent | Skill |
|---|---|
| Shared rules | `cmo-system` |
| Marketing Ops (KPIs, attribution checks, performance, budget) | `marketing-ops` |
| Paid | `paid` |
| SEO; Website and CRO | `seo`, `website` |
| Content (blog, SEO content, webinars, pillars, social) | `content` |
| Product Marketing (messaging, positioning, win/loss, competitors) | `product-marketing` |
| Customers (story candidates) | `customers` |
| PM (board, weekly status) | `pm` |
| CMO Strategist (Monday brief, open items log) | `strategist` |
| Health; Ask CMO | `health`, `ask-cmo` |

Output goes to one quiet channel: the Monday CMO brief, a weekly Research log post whose thread holds every agent's pack, and alerts. See `cmo-system`, Posting.

## Layout
| Path | Purpose |
|---|---|
| `CLAUDE.md` | Rules every agent follows |
| `.claude/skills/cmo-system/` | Shared rulebook: ICP, KPI definitions, goals, attribution rules, sources of truth, voice, IDs |
| `shared/slack_post.py` | The only way agents post to Slack |
| `shared/capture.py` | Saves connector results to files byte for byte, so agents never retype data |
| `docs/decisions.md` | Decisions and open items |

## Changing what agents do
Only through a pull request reviewed by Jonathan (or Amanda for content and voice rules). Agents never edit their own instructions.
