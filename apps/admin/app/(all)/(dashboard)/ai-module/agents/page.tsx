// IW PP-83: /ai-module/agents/ page

import type { Route } from "./+types/page";
import { IWGlobalAgents } from "./iw-global-agents";

export const meta: Route.MetaFunction = () => [{ title: "Global Agents — AI Setup | God Mode" }];

export default function AgentsPage(_props: Route.ComponentProps) {
  return <IWGlobalAgents />;
}
