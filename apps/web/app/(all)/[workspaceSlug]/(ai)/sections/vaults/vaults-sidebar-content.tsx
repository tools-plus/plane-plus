/**
 * IW: AI panel — VAULTS section sidebar (tree).
 *
 * Lifted from the PP-71 AgentDocsSidebarContent. Round 2 polish moved
 * the "+ New" button up into the section header row (rendered by the
 * AI sidebar shell via section.HeaderAction). What's left here is just
 * the path-list fetch + tree render + per-folder create plumbing.
 *
 * Per-folder create: the tree exposes "+ Add file / Add folder"
 * affordances on each folder row (round 2 polish, item 7). When the
 * user picks "Add file" we POST to the API; when they pick "Add
 * folder" the tree handles it client-side (no folder entity in the
 * data model — folders are synthesized from path prefixes, so a ghost
 * folder lives in tree state until the user creates a file inside it).
 */

import { useEffect, useState } from "react";
import { Loader2 } from "lucide-react";
import { agentDocsClient, AgentDocStaleError } from "@/services/agent-docs";
import { AgentDocsTree } from "@/components/agent-docs/pp-agent-docs-tree";
import { useVaultsContext } from "./vaults-context";

export function VaultsSidebarContent() {
  const { workspaceSlug, selectedPath, setSelectedPath, listVersion, bumpListVersion } = useVaultsContext();
  const [paths, setPaths] = useState<string[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    agentDocsClient
      .list(workspaceSlug)
      .then((res) => {
        if (cancelled) return;
        setPaths(res.docs.map((d) => d.path));
        setError(null);
        return res;
      })
      .catch((err) => {
        if (cancelled) return;
        setError(err?.detail ?? "Failed to load docs.");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceSlug, listVersion]);

  // Tree's per-folder "Add file" affordance funnels here. The tree
  // computed the full path (parent + filename); we just persist + select.
  // Returns a string error message on failure so the tree can surface
  // it inline (e.g. the input row stays open with a red hint).
  const handleCreateFile = async (fullPath: string): Promise<string | null> => {
    try {
      await agentDocsClient.write(workspaceSlug, fullPath, `# ${fullPath}\n\n`);
      bumpListVersion();
      setSelectedPath(fullPath);
      return null;
    } catch (err) {
      if (err instanceof AgentDocStaleError) {
        return `A doc already exists at ${fullPath}.`;
      }
      return (err as { detail?: string; message?: string })?.detail ?? (err as Error)?.message ?? "Create failed.";
    }
  };

  const handleDelete = async (path: string) => {
    try {
      await agentDocsClient.remove(workspaceSlug, path);
      if (selectedPath === path) setSelectedPath(null);
      bumpListVersion();
    } catch (err) {
      window.alert((err as { detail?: string })?.detail ?? "Delete failed.");
    }
  };

  return (
    <div className="flex w-full flex-col">
      <div className="flex-1 overflow-auto">
        {loading ? (
          <div className="flex items-center gap-2 px-3 py-2 text-13 text-tertiary">
            <Loader2 className="size-3.5 animate-spin" />
            Loading…
          </div>
        ) : error ? (
          <div className="text-red-500 px-3 py-2 text-13">{error}</div>
        ) : (
          <AgentDocsTree
            paths={paths}
            selectedPath={selectedPath}
            onSelect={setSelectedPath}
            onDelete={handleDelete}
            onCreateFile={handleCreateFile}
          />
        )}
      </div>
    </div>
  );
}
