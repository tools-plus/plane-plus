/**
 * PP-71: Agent Docs — editor pane.
 *
 * Intentionally boring: plain <textarea> + react-markdown preview.
 * NO Monaco, NO TipTap, NO Yjs. The whole point of Agent Docs is single-
 * writer with optimistic concurrency — collab editors break that contract.
 *
 * UX:
 *   - Tabs: Edit | Preview
 *     The active tab is mirrored to the URL via `?view=edit|preview` so a
 *     refresh (or copy-paste of the URL into another tab) restores the
 *     same view. Click handlers use `replace: true` to avoid piling
 *     entries onto the browser history stack — the URL just reflects
 *     the current view, same pattern as `?path=` in the VAULTS provider.
 *     The tab is intentionally a *session preference*, not a per-doc
 *     property: switching docs preserves your current tab choice.
 *   - Save button (disabled while clean / saving)
 *   - On 409 stale: banner appears with Reload button. Local edits stay in
 *     the textarea (we don't auto-discard) but the user has to either
 *     Reload (drop edits, refetch) or copy-paste their changes elsewhere.
 *   - Cmd/Ctrl+S triggers save.
 *
 * Note on the version label: we used to render "v{N} · synced/unsaved/saved"
 * next to the Save button, but with no history/revisions UI yet the version
 * number is just noise. The optimistic-concurrency machinery (If-Match
 * header derived from `state.doc.version`) is unchanged — only the visible
 * label was removed. Add the label back when a revisions UI lands.
 */

import { useCallback, useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router";
import { Loader2, RefreshCcw, Save } from "lucide-react";
import { cn } from "@plane/utils";
import { AgentDocStaleError, agentDocsClient, type TAgentDoc } from "@/services/agent-docs";
import { renderMarkdown } from "./iw-agent-docs-markdown";

type Props = {
  workspaceSlug: string;
  path: string;
  onAfterSave?: (doc: TAgentDoc) => void;
};

type LoadState = { kind: "loading" } | { kind: "ready"; doc: TAgentDoc } | { kind: "error"; message: string };

type ViewTab = "edit" | "preview";

/** Treat anything that isn't the literal "preview" string as the default Edit tab. */
function parseViewParam(raw: string | null): ViewTab {
  return raw === "preview" ? "preview" : "edit";
}

export function AgentDocsEditor({ workspaceSlug, path, onAfterSave }: Props) {
  const [state, setState] = useState<LoadState>({ kind: "loading" });
  const [draft, setDraft] = useState<string>("");
  const [searchParams, setSearchParams] = useSearchParams();
  const tab: ViewTab = parseViewParam(searchParams.get("view"));
  // Tab choice lives in the URL (`?view=edit|preview`) so a refresh
  // restores the same tab. We use `replace: true` to keep the browser
  // history clean — the URL is a view-state mirror, not a navigation
  // event. Default ("edit") is encoded by *omitting* the param so the
  // URL stays clean for first-load doc opens.
  const setTab = useCallback(
    (next: ViewTab) => {
      setSearchParams(
        (prev) => {
          const params = new URLSearchParams(prev);
          if (next === "preview") params.set("view", "preview");
          else params.delete("view");
          return params;
        },
        { replace: true }
      );
    },
    [setSearchParams]
  );
  const [saving, setSaving] = useState(false);
  const [stale, setStale] = useState<{ message: string } | null>(null);
  const [savedFlash, setSavedFlash] = useState(false);

  // load on path change
  useEffect(() => {
    let cancelled = false;
    setState({ kind: "loading" });
    setStale(null);
    agentDocsClient
      .retrieve(workspaceSlug, path)
      .then((doc) => {
        if (cancelled) return;
        setState({ kind: "ready", doc });
        setDraft(doc.content);
        return doc;
      })
      .catch((err) => {
        if (cancelled) return;
        setState({ kind: "error", message: err?.detail ?? err?.message ?? "Failed to load." });
      });
    return () => {
      cancelled = true;
    };
  }, [workspaceSlug, path]);

  const isDirty = state.kind === "ready" && draft !== state.doc.content;

  const handleSave = useMemo(
    () => async () => {
      if (state.kind !== "ready" || saving || !isDirty) return;
      setSaving(true);
      try {
        const updated = await agentDocsClient.write(workspaceSlug, path, draft, state.doc.version);
        setState({ kind: "ready", doc: updated });
        setDraft(updated.content);
        setStale(null);
        setSavedFlash(true);
        setTimeout(() => setSavedFlash(false), 1500);
        onAfterSave?.(updated);
      } catch (err) {
        if (err instanceof AgentDocStaleError) {
          setStale({
            message:
              "This doc was edited elsewhere — your version is stale. Reload to discard local edits, or copy them out first.",
          });
        } else {
          // any other error — surface inline; don't lose draft
          setStale({
            message:
              (err as { detail?: string; message?: string })?.detail ??
              (err as { message?: string })?.message ??
              "Save failed.",
          });
        }
      } finally {
        setSaving(false);
      }
    },
    [state, saving, isDirty, workspaceSlug, path, draft, onAfterSave]
  );

  // Cmd/Ctrl+S
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const isSave = (e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "s";
      if (isSave) {
        e.preventDefault();
        void handleSave();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleSave]);

  const handleReload = async () => {
    setStale(null);
    setState({ kind: "loading" });
    try {
      const doc = await agentDocsClient.retrieve(workspaceSlug, path);
      setState({ kind: "ready", doc });
      setDraft(doc.content);
    } catch (err) {
      setState({
        kind: "error",
        message: (err as { detail?: string })?.detail ?? "Failed to reload.",
      });
    }
  };

  if (state.kind === "loading") {
    return (
      <div className="flex size-full items-center justify-center text-tertiary">
        <Loader2 className="mr-2 size-4 animate-spin" /> Loading {path}…
      </div>
    );
  }

  if (state.kind === "error") {
    return (
      <div className="flex size-full flex-col items-center justify-center gap-2 text-center">
        <p className="text-red-500 text-13">{state.message}</p>
        <button
          type="button"
          onClick={handleReload}
          className="rounded-md border border-subtle px-3 py-1 text-13 text-secondary hover:bg-layer-transparent-hover"
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="flex size-full flex-col" data-testid="iw-agent-docs-editor">
      {/* toolbar — tab strip on the left, doc status + save on the right.
          Tabs use the same underline-on-active pattern as the issue
          detail epic-overview tabs (after-pseudo bottom border so the
          active tab visually anchors to the toolbar's bottom edge). */}
      <div className="flex items-center justify-between gap-2 border-b border-subtle px-4">
        <div className="flex items-center gap-0">
          <TabButton active={tab === "edit"} onClick={() => setTab("edit")}>
            Edit
          </TabButton>
          <TabButton active={tab === "preview"} onClick={() => setTab("preview")}>
            Preview
          </TabButton>
        </div>
        <div className="flex items-center gap-2 py-2">
          {/* The "v{N} · synced/unsaved/saved" indicator used to live here.
              Removed pending a revisions UI — see file header. The save
              button still surfaces "unsaved" implicitly via its disabled
              state, and the brief saved-flash check below mirrors the
              previous "saved ✓" affordance without leaking the version. */}
          {savedFlash && !isDirty && <span className="text-11 text-tertiary">saved ✓</span>}
          <button
            type="button"
            onClick={handleSave}
            disabled={!isDirty || saving}
            className={cn(
              "flex items-center gap-1.5 rounded-md border border-subtle px-3 py-1 text-13 font-medium",
              isDirty && !saving ? "bg-primary text-on-primary hover:opacity-90" : "text-tertiary",
              "disabled:cursor-not-allowed disabled:opacity-50"
            )}
          >
            {saving ? <Loader2 className="size-3.5 animate-spin" /> : <Save className="size-3.5" />}
            <span>{saving ? "Saving…" : "Save"}</span>
          </button>
        </div>
      </div>

      {stale && (
        <div className="border-yellow-500/40 bg-yellow-500/10 flex items-center justify-between gap-3 border-b px-4 py-2 text-13">
          <span className="text-yellow-700 dark:text-yellow-300">{stale.message}</span>
          <button
            type="button"
            onClick={handleReload}
            className="flex items-center gap-1.5 rounded-md border border-subtle bg-surface-1 px-2 py-1 text-12 hover:bg-layer-transparent-hover"
          >
            <RefreshCcw className="size-3" /> Reload
          </button>
        </div>
      )}

      {/* body */}
      <div className="relative flex-1 overflow-hidden">
        {tab === "edit" ? (
          <textarea
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            spellCheck={false}
            className="block size-full resize-none border-0 bg-transparent p-4 font-code text-13 leading-relaxed text-primary outline-none"
            placeholder="Write markdown here…"
            data-testid="iw-agent-docs-textarea"
          />
        ) : (
          <div
            className="prose-sm dark:prose-invert absolute inset-0 max-w-none overflow-y-auto p-4 prose"
            data-testid="iw-agent-docs-preview"
            // renderMarkdown returns sanitized HTML — escapes raw text first,
            // then applies a small set of inline transforms. NEVER pass raw
            // doc content here: see iw-agent-docs-markdown.ts for the contract.
            dangerouslySetInnerHTML={{ __html: renderMarkdown(draft) }}
          />
        )}
      </div>

      {/* footer
          The full doc path used to render here in code font. Now that
          the AI-layout breadcrumb at the top of the main pane shows
          every path segment, the bottom path was redundant — we kept
          one source of truth (the breadcrumb). The chars/lines counter
          is still useful editor info, so we keep it justified to the
          right. */}
      <div className="flex items-center justify-end border-t border-subtle px-4 py-1.5 text-11 text-tertiary">
        <span>
          {draft.length} chars · {draft.split(/\r?\n/).length} lines
        </span>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, children }: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        // Mirror Plane's issue-detail tab pattern: muted text, hover
        // lightens, active gets a 2px brand-color underline via an
        // ::after that hugs the toolbar's bottom border so the strip
        // reads as a real tab strip — not a row of buttons.
        "relative px-3 py-2 text-13 font-medium transition-colors",
        active
          ? "after:bg-primary text-primary after:absolute after:right-0 after:bottom-0 after:left-0 after:h-0.5"
          : "text-tertiary hover:text-secondary"
      )}
    >
      {children}
    </button>
  );
}
