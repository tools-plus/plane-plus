/**
 * PP-71: Agent Docs — types.
 *
 * Workspace-level markdown notes (replaces local Obsidian vault).
 * Pure markdown, NO Yjs/CRDT, optimistic-concurrency on writes via integer
 * version field (mapped to/from HTTP `If-Match`).
 *
 * Mock contract — frontend defines this so Vikrant (PP-70 backend) can match.
 * See README at .claude/exchanges/84e6879661d6/response.json for the OpenAPI shape.
 */

/** A doc summary returned in list responses (no content). */
export type TAgentDocSummary = {
  path: string; // unique within workspace, e.g. "plans/surya.md"
  version: number; // monotonic, increments on each PUT
  updated_at: string; // ISO-8601
};

/** A full doc returned by GET. */
export type TAgentDoc = TAgentDocSummary & {
  content: string;
  created_at: string;
  created_by?: string;
  updated_by?: string;
};

/** Body for PUT /agent-docs. */
export type TAgentDocWritePayload = {
  content: string;
};

/** Result of a list query. */
export type TAgentDocListResponse = {
  docs: TAgentDocSummary[];
};

/** Tree node for the navigator (built client-side from the path list). */
export type TAgentDocTreeNode = {
  name: string; // segment, e.g. "sarah.md" or "plans"
  path: string; // full path for files; folder marker (no trailing slash) for folders
  type: "folder" | "file";
  children: TAgentDocTreeNode[]; // empty for files
};

/**
 * Thrown when a PUT comes back 409 Conflict (stale version).
 * UI shows a "doc was edited elsewhere — Reload?" banner.
 */
export class AgentDocStaleError extends Error {
  readonly serverVersion?: number;
  constructor(message = "stale version", serverVersion?: number) {
    super(message);
    this.name = "AgentDocStaleError";
    this.serverVersion = serverVersion;
  }
}

/**
 * Service interface — implemented by both the mock and the real (PP-70) client.
 * Lets the rest of the app code stay transport-agnostic until cutover.
 */
export interface IAgentDocsClient {
  list(workspaceSlug: string, prefix?: string): Promise<TAgentDocListResponse>;
  retrieve(workspaceSlug: string, path: string): Promise<TAgentDoc>;
  /**
   * Create-or-update.
   * - On create (doc does not exist): pass `version` undefined.
   *   If a doc already exists at that path the server returns 409 (caller should retrieve + retry as an update).
   * - On update: pass the last-known `version` from the previous retrieve.
   *   If that version is stale the server returns 409 → throws AgentDocStaleError.
   */
  write(workspaceSlug: string, path: string, content: string, version?: number): Promise<TAgentDoc>;
  remove(workspaceSlug: string, path: string): Promise<void>;
}
