# CMO Listener Slack app

A listen-only, Slack-hosted app, modeled on the CFO Triage app. When Jonathan, Amanda or Cristina posts in #marketing-cmo and the message
either mentions the AchieveIt CMO bot or replies in a thread the bot started, it loads the thread and fires the **Ask CMO** Claude routine with it
(`.claude/skills/ask-cmo`). The routine answers in the thread as the AchieveIt CMO bot. This app never posts. It is separate from the posting bot
(`slack-app/`) on purpose.

Deploy from a GitHub Codespace on this repo (the `.devcontainer` has Deno and the Slack CLI), working in this folder.

## First-time setup
1. In Claude, create the **Ask CMO** scheduled task with no schedule and add an API trigger to it (copy `.claude/skills/ask-cmo/references/routine.md`); note its `trig_...` id and token.
2. `cd slack-listener` and `slack login` (paste the `/slackauthticket` command into Slack, then the code back).
3. `slack deploy` -> **Create a new app**, workspace **achieveit**. This writes `.slack/apps.json`.
4. `slack env add CMO_ROUTINE_ID <trig_... id>` and `slack env add CMO_ROUTINE_TOKEN <its API token>`.
5. `slack trigger create --trigger-def triggers/cmo_messages.ts`.
6. In Slack: `/invite @CMO Listener` in #marketing-cmo (private channel; Amanda and Cristina must be members to see posts).
7. Commit `.slack/apps.json` from the Codespace: `git add .slack && git commit -m "Link CMO Listener Slack app" && git push`.

Test: reply "what's open on paid?" in a pack thread, or write `@AchieveIt CMO what is open for Amanda?`; the bot should answer in the thread within a minute or two.

## Changing it
- Code (`manifest.ts`, `functions/`, `workflows/`): change on GitHub, then `git pull && slack deploy` in a Codespace.
- Trigger (`triggers/`): after deploy, `slack trigger update --trigger-id <Ft...> --trigger-def triggers/cmo_messages.ts`.
- What Ask CMO does: `.claude/skills/ask-cmo/SKILL.md` only; used on the next message, no deploy.

Secrets are never in this repo: the routine token lives in `slack env` and the password manager. Logs: `slack activity --tail`.
