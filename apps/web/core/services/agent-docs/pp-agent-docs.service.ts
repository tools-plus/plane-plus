/**
 * PP-71: Agent Docs — real REST client (session-authenticated).
 *
 * Endpoints (mirror of Vikrant's PP-70 X-Api-Key surface at /api/v1/, but
 * mounted under /api/ for cookie auth so the web UI can reach them — see
 * apps/api/plane/app/views/iw_agent_doc.py):
 *   GET    /api/workspaces/{slug}/agent-docs/?prefix=&q=        → list
 *   GET    /api/workspaces/{slug}/agent-docs/doc/?path=<path>   → retrieve one
 *   PUT    /api/workspaces/{slug}/agent-docs/doc/?path=<path>   → write
 *   DELETE /api/workspaces/{slug}/agent-docs/doc/?path=<path>   → delete
 *
 * NOTE: paths contain "/" (e.g. plans/surya.md). We pass the full path as a
 * query parameter rather than a path segment to avoid Django routing/URL-
 * encoding pain. The server URL-decodes once.
 *
 * Optimistic concurrency:
 *   - PUT with no If-Match → "create only" (412 if the doc already exists,
 *     matching Vikrant's adopted contract — RFC 7232 reserves 412 for
 *     precondition mismatch and we lean on that distinction).
 *   - PUT with If-Match: N → "update if version == N"; 409 (stale) if the
 *     server's version has moved on.
 *   - On success, server returns the doc with the new version and an ETag.
 *
 * The UI distinguishes only between "stale, server has moved on" (show a
 * Reload banner) and "everything else" (show the error toast). Both 409 and
 * 412 funnel into AgentDocStaleError — server_version on the body lets the
 * UI render "your version was N+1" without a follow-up GET.
 */

import { API_BASE_URL } from "@plane/constants";
import { APIService } from "@/services/api.service";
import {
  AgentDocStaleError,
  type IAgentDocsClient,
  type TAgentDoc,
  type TAgentDocListResponse,
} from "./iw-agent-docs.types";

export class AgentDocsService extends APIService implements IAgentDocsClient {
  constructor(BASE_URL?: string) {
    super(BASE_URL || API_BASE_URL);
  }

  async list(workspaceSlug: string, prefix?: string): Promise<TAgentDocListResponse> {
    const params = prefix ? { prefix } : {};
    return this.get(`/api/workspaces/${workspaceSlug}/agent-docs/`, { params })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async retrieve(workspaceSlug: string, path: string): Promise<TAgentDoc> {
    return this.get(`/api/workspaces/${workspaceSlug}/agent-docs/doc/`, {
      params: { path },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  async write(workspaceSlug: string, path: string, content: string, version?: number): Promise<TAgentDoc> {
    const headers: Record<string, string> = {};
    if (typeof version === "number") {
      headers["If-Match"] = String(version);
    }
    return this.put(`/api/workspaces/${workspaceSlug}/agent-docs/doc/`, { content }, { params: { path }, headers })
      .then((response) => response?.data)
      .catch((error) => {
        const status = error?.response?.status;
        // 409 = stale If-Match; 412 = precondition (e.g. update without
        // If-Match, or create on an already-present path). The UI flow
        // for both is the same: refetch, show "doc moved on" banner.
        if (status === 409 || status === 412) {
          throw new AgentDocStaleError(
            error?.response?.data?.detail ?? "stale version",
            error?.response?.data?.server_version
          );
        }
        throw error?.response?.data;
      });
  }

  async remove(workspaceSlug: string, path: string): Promise<void> {
    // The server requires If-Match on DELETE for symmetry with PUT. The
    // UI just wants "delete it", so we send `*` (RFC 7232 force-write).
    // If a callsite ever needs version-conditional deletes we can extend
    // the interface; today no UI surface needs that.
    return this.delete(`/api/workspaces/${workspaceSlug}/agent-docs/doc/`, undefined, {
      params: { path },
      headers: { "If-Match": "*" },
    })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
