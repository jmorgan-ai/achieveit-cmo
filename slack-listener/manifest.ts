import { Manifest } from "deno-slack-sdk/mod.ts";
import { ForwardMessageFunction } from "./functions/forward_message.ts";
import CmoMessageWorkflow from "./workflows/cmo_message.ts";

// Ask CMO listener. It only listens: messages from Jonathan, Amanda or Cristina in #marketing-cmo that mention the CMO bot or reply
// in a thread the CMO bot started are sent to the "Ask CMO" Claude routine, which answers in the thread as the AchieveIt CMO bot.
// This app never posts.
export default Manifest({
  name: "CMO Listener",
  description:
    "Sends questions and replies in #marketing-cmo to the Ask CMO routine. Listens only; the AchieveIt CMO bot answers.",
  icon: "icon.png",
  functions: [ForwardMessageFunction],
  workflows: [CmoMessageWorkflow],
  // The only outside host the app calls: the Claude routine "fire" endpoint.
  outgoingDomains: ["api.anthropic.com"],
  botScopes: [
    "channels:history",
    "groups:history",
    "channels:read",
    "groups:read",
    "users:read",
  ],
});
