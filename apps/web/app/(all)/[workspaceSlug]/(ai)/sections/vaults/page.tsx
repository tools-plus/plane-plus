/**
 * IW: AI panel — VAULTS section main pane.
 *
 * Renders the editor pane for the currently selected vault doc, or an
 * empty state if nothing is selected. Behavior identical to the PP-71
 * Agent Docs page; only the route + context name changed.
 *
 * Deep-link support: the layout reads `?path=<path>` from the URL on
 * mount and seeds the selection, so /ai/vaults?path=plans/surya.md
 * still opens the right doc. Path can contain `/`, so we keep it in a
 * query param rather than a path segment (same rationale as PP-71).
 */

import { NotebookText } from "lucide-react";
import { AgentDocsEditor } from "@/components/agent-docs/pp-agent-docs-editor";
import { useVaultsContext } from "./vaults-context";

function VaultsHomePage() {
  const { workspaceSlug, selectedPath, bumpListVersion } = useVaultsContext();

  if (!selectedPath) {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-4 text-center">
        <div className="flex size-16 items-center justify-center rounded-xl bg-layer-transparent-hover">
          <NotebookText className="size-8 text-tertiary" />
        </div>
        <div className="flex flex-col gap-1">
          <h2 className="text-xl font-semibold text-primary">Vaults</h2>
          <p className="text-sm max-w-md text-secondary">
            Workspace-level markdown notes. Pick a doc from the sidebar, or click <strong>New</strong> to create one.
          </p>
        </div>
      </div>
    );
  }

  return (
    <AgentDocsEditor
      workspaceSlug={workspaceSlug}
      path={selectedPath}
      // bump the sidebar list so updated_at refreshes; not strictly needed
      // for content-only changes but cheap and keeps things in sync.
      onAfterSave={() => bumpListVersion()}
    />
  );
}

export default VaultsHomePage;
