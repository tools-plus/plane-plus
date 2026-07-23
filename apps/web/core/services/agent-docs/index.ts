/**
 * PP-71: Agent Docs — service barrel.
 *
 * `agentDocsClient` is the single instance the UI imports. PP-70 (Vikrant)
 * merged into main in plane-plus#31, so the cutover is done — the UI now
 * talks to the real session-authenticated REST endpoints under
 * `/api/workspaces/{slug}/agent-docs/...`. The in-memory mock has been
 * deleted; tests that need a fake should construct one against
 * `IAgentDocsClient` directly.
 */

import { AgentDocsService } from "./pp-agent-docs.service";
import type { IAgentDocsClient } from "./pp-agent-docs.types";

export const agentDocsClient: IAgentDocsClient = new AgentDocsService();

export { AgentDocsService };
export * from "./pp-agent-docs.types";
