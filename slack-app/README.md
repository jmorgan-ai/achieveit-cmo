# AchieveIt CMO Slack bot

Posting identity for the marketing agents. It only posts (scope `chat:write`) to channels it has been invited to, which is
#marketing-cmo (`C0CJRL8KDRS`). Agents post with `shared/slack_post.py`; the cloud environment proxy adds the bot token.

- `manifest.yml`: create the app from this manifest.
- `icon.png`: app icon (1024 x 1024). The CFO robot's sibling: growth-arrow antenna, megaphone. It watches performance and
  announces what it finds.

A reply listener (like the CFO Triage app) comes later, when the agents move past phase 0.
