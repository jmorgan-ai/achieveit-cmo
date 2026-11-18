import type { Trigger } from "deno-slack-api/types.ts";
import { TriggerEventTypes, TriggerTypes } from "deno-slack-api/mod.ts";
import CmoMessageWorkflow from "../workflows/cmo_message.ts";

// Messages in #marketing-cmo from Jonathan, Amanda or Cristina only. Bot posts and other people are ignored here; the function then
// forwards only messages that mention the CMO bot or reply in a thread the CMO bot started.
const trigger: Trigger<typeof CmoMessageWorkflow.definition> = {
  type: TriggerTypes.Event,
  name: "Message in #marketing-cmo",
  workflow: `#/workflows/${CmoMessageWorkflow.definition.callback_id}`,
  event: {
    event_type: TriggerEventTypes.MessagePosted,
    channel_ids: ["C0CJRL8KDRS"],
    filter: {
      version: 1,
      root: {
        operator: "OR",
        inputs: [
          { statement: "{{data.user_id}} == U45A7FFV4" },
          { statement: "{{data.user_id}} == U32KHRMTJ" },
          { statement: "{{data.user_id}} == U0BGWQLFBG8" },
        ],
      },
    },
  },
  inputs: {
    channel_id: { value: "{{data.channel_id}}" },
    message_ts: { value: "{{data.message_ts}}" },
    user_id: { value: "{{data.user_id}}" },
  },
};

export default trigger;
