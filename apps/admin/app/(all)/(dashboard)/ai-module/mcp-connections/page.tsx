// IW PP-83: /ai-module/mcp-connections/ page

import type { Route } from "./+types/page";
import { IWGlobalMCPConnections } from "./iw-global-mcp-connections";

export const meta: Route.MetaFunction = () => [{ title: "MCP Connections — AI Setup | God Mode" }];

export default function MCPConnectionsPage(_props: Route.ComponentProps) {
  return <IWGlobalMCPConnections />;
}
