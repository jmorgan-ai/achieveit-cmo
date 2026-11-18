import { DefineWorkflow, Schema } from "deno-slack-sdk/mod.ts";
import { ForwardMessageFunction } from "../functions/forward_message.ts";

const CmoMessageWorkflow = DefineWorkflow({
  callback_id: "cmo_message_workflow",
  title: "Message in #marketing-cmo → Ask CMO",
  input_parameters: {
    properties: {
      channel_id: { type: Schema.types.string },
      message_ts: { type: Schema.types.string },
      user_id: { type: Schema.types.string },
    },
    required: ["channel_id", "message_ts", "user_id"],
  },
});

CmoMessageWorkflow.addStep(ForwardMessageFunction, {
  channel_id: CmoMessageWorkflow.inputs.channel_id,
  message_ts: CmoMessageWorkflow.inputs.message_ts,
  user_id: CmoMessageWorkflow.inputs.user_id,
});

export default CmoMessageWorkflow;
