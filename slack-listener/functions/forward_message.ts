import { DefineFunction, Schema, SlackFunction } from "deno-slack-sdk/mod.ts";

/**
 * Loads the #marketing-cmo thread for a message and fires the Ask CMO routine with it as JSON
 * (env CMO_ROUTINE_ID / CMO_ROUTINE_TOKEN, set with `slack env add`).
 * Sends only: a message that mentions the CMO bot, or a reply in a thread the CMO bot started.
 */
export const ForwardMessageFunction = DefineFunction({
  callback_id: "forward_message",
  title: "Send message to Ask CMO",
  source_file: "functions/forward_message.ts",
  input_parameters: {
    properties: {
      channel_id: { type: Schema.types.string },
      message_ts: { type: Schema.types.string },
      user_id: { type: Schema.types.string },
    },
    required: ["channel_id", "message_ts", "user_id"],
  },
  output_parameters: {
    properties: { status: { type: Schema.types.string } },
    required: [],
  },
});

const PEOPLE = ["U45A7FFV4", "U32KHRMTJ", "U0BGWQLFBG8"]; // Jonathan, Amanda, Cristina
const CMO_BOT = "U0CJMSDSPGA"; // AchieveIt CMO bot (the one that posts)
const MAX_TEXT = 60_000; // routine `text` limit is 65,536 chars

// deno-lint-ignore no-explicit-any
type SlackMsg = Record<string, any>;

export default SlackFunction(
  ForwardMessageFunction,
  async ({ inputs, client, env }) => {
    const done = (status: string) => ({ outputs: { status } });
    if (!PEOPLE.includes(inputs.user_id)) return done("skipped: not on the team list");
    if (!env.CMO_ROUTINE_ID || !env.CMO_ROUTINE_TOKEN) {
      return { error: "CMO_ROUTINE_ID / CMO_ROUTINE_TOKEN not set (slack env add)" };
    }

    // 1. The whole thread (works for a top-level message or a reply).
    const messages: SlackMsg[] = [];
    let cursor: string | undefined;
    do {
      const page = await client.conversations.replies({
        channel: inputs.channel_id,
        ts: inputs.message_ts,
        limit: 200,
        cursor,
      });
      if (!page.ok) return { error: `conversations.replies failed: ${page.error}` };
      messages.push(...(page.messages ?? []));
      cursor = page.response_metadata?.next_cursor || undefined;
    } while (cursor);
    if (!messages.length) return done("skipped: message not found");

    const msg = messages.find((m) => m.ts === inputs.message_ts);
    const threadTs: string = messages[0].thread_ts ?? messages[0].ts;
    if (!msg || msg.subtype || msg.bot_id) return done("skipped: not a person's message");

    const isReply = inputs.message_ts !== threadTs;
    const mention = (msg.text ?? "").includes(`<@${CMO_BOT}`);
    const parentByBot = Boolean(messages[0].bot_id);
    if (!mention && !(isReply && parentByBot)) {
      return done("skipped: no mention and not a reply to a bot post");
    }

    // 2. Names for the people in the thread.
    const names: Record<string, string> = {};
    for (const id of new Set(messages.map((m) => m.user).filter(Boolean))) {
      const u = await client.users.info({ user: id });
      names[id] = u.ok ? (u.user?.real_name || u.user?.name || id) : id;
    }

    const payload = {
      source: "cmo-listener-slack-app",
      kind: "cmo_message",
      channel: { id: inputs.channel_id, name: "marketing-cmo" },
      thread_ts: threadTs,
      trigger_message_ts: inputs.message_ts,
      trigger_is_thread_reply: isReply,
      mention,
      trigger_user: { user_id: inputs.user_id, name: names[inputs.user_id] ?? inputs.user_id },
      messages: messages.map((m) => ({
        ts: m.ts,
        user_id: m.user ?? null,
        name: m.user ? names[m.user] : (m.bot_profile?.name ?? m.username ?? "bot"),
        is_bot: Boolean(m.bot_id),
        text: m.text ?? "",
      })),
      truncated: false,
    };

    // 3. Keep under the size limit: keep the first message, drop the oldest replies.
    let text = JSON.stringify(payload);
    while (text.length > MAX_TEXT && payload.messages.length > 2) {
      payload.messages.splice(1, 1);
      payload.truncated = true;
      text = JSON.stringify(payload);
    }

    // 4. Fire the routine.
    const res = await fetch(
      `https://api.anthropic.com/v1/claude_code/routines/${env.CMO_ROUTINE_ID}/fire`,
      {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.CMO_ROUTINE_TOKEN}`,
          "anthropic-version": "2023-06-01",
          "anthropic-beta": "experimental-cc-routine-2026-04-01",
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ text }),
      },
    );
    if (!res.ok) {
      const body = await res.text();
      return { error: `Routine fire failed (${res.status}): ${body.slice(0, 500)}` };
    }
    return done("sent to Ask CMO");
  },
);
