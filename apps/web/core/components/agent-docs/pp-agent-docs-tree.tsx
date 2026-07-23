/**
 * PP-71: Agent Docs — sidebar tree navigator.
 *
 * Receives the flat list of paths, builds a folder tree by splitting on "/",
 * renders a clickable hierarchy. Folders expand/collapse on click. Files are
 * leaves — clicking calls `onSelect(path)`.
 *
 * Round 2 polish (item 7): every folder row gets a hover-revealed "+"
 * button with a small dropdown — "Add file" or "Add folder". Picking
 * either reveals an inline input under the folder; submitting either
 * creates a file under that folder (via `onCreateFile`) or registers
 * a client-side ghost folder (no API call — folders are virtual in the
 * data model, see tree-builder for the rationale).
 *
 * Intentionally lightweight: no DnD, no rename, no MobX. v1 acceptance is
 * "tree shows the same shape MGupta sees in Obsidian today" + the polish
 * affordances above.
 */

import { useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";
import { ChevronRight, FileText, Folder, FolderOpen, FolderPlus, Plus, Trash2 } from "lucide-react";
import { CustomMenu } from "@plane/ui";
import { cn } from "@plane/utils";
import type { TAgentDocTreeNode } from "@/services/agent-docs";
import { buildAgentDocTree } from "./iw-agent-docs-tree-builder";

type CreateMode = "file" | "folder";
type CreateState = {
  parent: string; // "" for root, "blogs" for a top-level folder, etc.
  mode: CreateMode;
  value: string;
  error: string | null;
  busy: boolean;
};

type Props = {
  paths: string[];
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onDelete?: (path: string) => void;
  /**
   * Called when the user submits the inline "Add file" input under a
   * folder. The tree passes the *full* path (parent + filename, with
   * a `.md` suffix appended if the user omitted it). Returns null on
   * success or an error message on failure — the input row stays open
   * with the message displayed when the result is non-null.
   */
  onCreateFile?: (fullPath: string) => Promise<string | null>;
};

export function AgentDocsTree({ paths, selectedPath, onSelect, onDelete, onCreateFile }: Props) {
  // Client-side "ghost folders": prefixes the user added via "Add
  // folder" that don't have any persisted file inside yet. We hold
  // them as a Set of slash-joined paths. As soon as a file appears
  // under a ghost prefix (via the path list or a successful create)
  // the prefix becomes redundant; we prune it on every render so the
  // set stays minimal.
  const [ghostFolders, setGhostFolders] = useState<Set<string>>(new Set());

  // Prune any ghost folder that's now realised as a path prefix — no
  // need to keep it in client state once the data has caught up. This
  // also keeps the tree from showing duplicate folder nodes after the
  // path list refetches post-create.
  useEffect(() => {
    if (ghostFolders.size === 0) return;
    const realised = new Set<string>();
    for (const p of paths) {
      const parts = p.split("/").filter(Boolean);
      let acc = "";
      for (let i = 0; i < parts.length - 1; i++) {
        acc = acc ? `${acc}/${parts[i]}` : parts[i];
        realised.add(acc);
      }
    }
    let changed = false;
    const next = new Set<string>();
    for (const g of ghostFolders) {
      if (realised.has(g)) {
        changed = true;
      } else {
        next.add(g);
      }
    }
    if (changed) setGhostFolders(next);
  }, [paths, ghostFolders]);

  const tree = useMemo(() => buildAgentDocTree(paths, ghostFolders), [paths, ghostFolders]);

  // expand the folder containing the selected file by default
  const initialExpanded = useMemo(() => {
    const set = new Set<string>();
    if (selectedPath) {
      const parts = selectedPath.split("/").filter(Boolean);
      parts.pop(); // drop filename
      let acc = "";
      for (const p of parts) {
        acc = acc ? `${acc}/${p}` : p;
        set.add(acc);
      }
    }
    return set;
  }, [selectedPath]);
  const [expanded, setExpanded] = useState<Set<string>>(initialExpanded);

  // Inline create state. At most one create input is visible at a
  // time — the user is doing one thing. Lifting it here (instead of
  // inside each TreeNode) makes that constraint trivial to enforce.
  const [createState, setCreateState] = useState<CreateState | null>(null);

  const toggle = (path: string) => {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(path)) next.delete(path);
      else next.add(path);
      return next;
    });
  };

  const startCreate = (parent: string, mode: CreateMode) => {
    // Auto-expand the parent folder so the input shows up in context.
    if (parent && !expanded.has(parent)) {
      setExpanded((prev) => {
        const next = new Set(prev);
        next.add(parent);
        return next;
      });
    }
    setCreateState({ parent, mode, value: "", error: null, busy: false });
  };

  const cancelCreate = () => setCreateState(null);

  const submitCreate = async () => {
    if (!createState) return;
    const raw = createState.value.trim();
    if (!raw) {
      setCreateState({ ...createState, error: "Name can't be empty." });
      return;
    }
    if (raw.includes("/")) {
      setCreateState({ ...createState, error: "No slashes — pick the parent folder, then enter just the name." });
      return;
    }

    if (createState.mode === "folder") {
      const fullFolder = createState.parent ? `${createState.parent}/${raw}` : raw;
      // Refuse if a file already exists with that exact name at this
      // level — folders and files can't share a name.
      const conflict = paths.some((p) => p === fullFolder || p === `${fullFolder}.md`);
      if (conflict) {
        setCreateState({ ...createState, error: "A file with that name already exists here." });
        return;
      }
      setGhostFolders((prev) => {
        const next = new Set(prev);
        next.add(fullFolder);
        return next;
      });
      setExpanded((prev) => {
        const next = new Set(prev);
        next.add(fullFolder);
        return next;
      });
      setCreateState(null);
      return;
    }

    // Add-file: append .md if the user omitted it (matches the global
    // "+ New" prompt's contract).
    const filename = raw.toLowerCase().endsWith(".md") ? raw : `${raw}.md`;
    const fullPath = createState.parent ? `${createState.parent}/${filename}` : filename;
    if (!onCreateFile) {
      setCreateState({ ...createState, error: "Create not wired up." });
      return;
    }
    setCreateState({ ...createState, busy: true, error: null });
    const err = await onCreateFile(fullPath);
    if (err) {
      // Keep the input open with the error so the user can edit + retry.
      setCreateState((prev) => (prev ? { ...prev, busy: false, error: err } : null));
      return;
    }
    setCreateState(null);
  };

  if (tree.length === 0 && !createState) {
    return (
      <div className="px-3 py-4 text-13 text-tertiary">No docs yet. Click &ldquo;New&rdquo; above to create one.</div>
    );
  }

  return (
    <div className="flex flex-col gap-0.5 px-1.5 py-2" data-testid="iw-agent-docs-tree">
      {tree.map((node) => (
        <TreeNode
          key={node.path || node.name}
          node={node}
          depth={0}
          expanded={expanded}
          toggle={toggle}
          selectedPath={selectedPath}
          onSelect={onSelect}
          onDelete={onDelete}
          createState={createState}
          startCreate={startCreate}
          cancelCreate={cancelCreate}
          submitCreate={submitCreate}
          setCreateValue={(v) => setCreateState((prev) => (prev ? { ...prev, value: v, error: null } : prev))}
          canCreate={Boolean(onCreateFile)}
        />
      ))}
    </div>
  );
}

type NodeProps = {
  node: TAgentDocTreeNode;
  depth: number;
  expanded: Set<string>;
  toggle: (path: string) => void;
  selectedPath: string | null;
  onSelect: (path: string) => void;
  onDelete?: (path: string) => void;
  createState: CreateState | null;
  startCreate: (parent: string, mode: CreateMode) => void;
  cancelCreate: () => void;
  submitCreate: () => void;
  setCreateValue: (v: string) => void;
  canCreate: boolean;
};

function TreeNode({
  node,
  depth,
  expanded,
  toggle,
  selectedPath,
  onSelect,
  onDelete,
  createState,
  startCreate,
  cancelCreate,
  submitCreate,
  setCreateValue,
  canCreate,
}: NodeProps) {
  const indent = { paddingLeft: `${depth * 14 + 8}px` } as const;

  if (node.type === "folder") {
    const isOpen = expanded.has(node.path);
    const isCreatingHere = createState?.parent === node.path;
    return (
      <div className="flex flex-col">
        <div
          className={cn(
            "group/folder flex w-full items-center gap-1.5 rounded-md py-1 pr-1 text-left text-13 text-secondary hover:bg-layer-transparent-hover"
          )}
          style={indent}
        >
          <button
            type="button"
            onClick={() => toggle(node.path)}
            className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
          >
            <ChevronRight className={cn("size-3.5 flex-shrink-0 transition-transform", isOpen && "rotate-90")} />
            {isOpen ? (
              <FolderOpen className="size-3.5 flex-shrink-0 text-tertiary" />
            ) : (
              <Folder className="size-3.5 flex-shrink-0 text-tertiary" />
            )}
            <span className="truncate font-medium">{node.name}</span>
            <span className="ml-auto pr-1 text-11 text-tertiary">{node.children.length}</span>
          </button>
          {canCreate && (
            <FolderAddMenu
              onAddFile={() => startCreate(node.path, "file")}
              onAddFolder={() => startCreate(node.path, "folder")}
            />
          )}
        </div>
        {isOpen && (
          <>
            {isCreatingHere && createState && (
              <CreateInputRow
                depth={depth + 1}
                state={createState}
                onChange={setCreateValue}
                onSubmit={submitCreate}
                onCancel={cancelCreate}
              />
            )}
            {node.children.map((child) => (
              <TreeNode
                key={child.path || child.name}
                node={child}
                depth={depth + 1}
                expanded={expanded}
                toggle={toggle}
                selectedPath={selectedPath}
                onSelect={onSelect}
                onDelete={onDelete}
                createState={createState}
                startCreate={startCreate}
                cancelCreate={cancelCreate}
                submitCreate={submitCreate}
                setCreateValue={setCreateValue}
                canCreate={canCreate}
              />
            ))}
          </>
        )}
      </div>
    );
  }

  // file leaf
  const isSelected = selectedPath === node.path;
  return (
    <div
      className={cn(
        "group flex items-center gap-1.5 rounded-md pr-1 text-13 hover:bg-layer-transparent-hover",
        isSelected && "bg-layer-transparent-hover text-primary"
      )}
      style={indent}
    >
      <button
        type="button"
        onClick={() => onSelect(node.path)}
        className="flex min-w-0 flex-1 items-center gap-1.5 py-1 text-left"
      >
        <span className="size-3.5 flex-shrink-0" /> {/* spacer where chevron would be */}
        <FileText className={cn("size-3.5 flex-shrink-0", isSelected ? "text-primary" : "text-tertiary")} />
        <span className={cn("truncate", isSelected ? "font-medium text-primary" : "text-secondary")}>{node.name}</span>
      </button>
      {onDelete && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            if (window.confirm(`Delete ${node.path}?`)) onDelete(node.path);
          }}
          className="invisible flex-shrink-0 rounded p-1 text-tertiary group-hover:visible hover:bg-layer-transparent-hover hover:text-primary"
          title={`Delete ${node.path}`}
        >
          <Trash2 className="size-3" />
        </button>
      )}
    </div>
  );
}

/**
 * Per-folder action menu. Hidden until the folder row is hovered to
 * keep the tree visually quiet — same affordance pattern as the
 * delete icon on file rows. CustomMenu wraps `customButton` in its
 * own <button>, so visibility classes go on `customButtonClassName`
 * (the wrapper) rather than the inner content.
 */
function FolderAddMenu({ onAddFile, onAddFolder }: { onAddFile: () => void; onAddFolder: () => void }) {
  return (
    <CustomMenu
      placement="bottom-end"
      closeOnSelect
      ariaLabel="Add to folder"
      customButtonClassName="invisible flex size-5 flex-shrink-0 items-center justify-center rounded text-tertiary group-hover/folder:visible hover:bg-layer-transparent-hover hover:text-primary"
      customButton={<Plus className="size-3" />}
    >
      <CustomMenu.MenuItem onClick={onAddFile} className="flex items-center gap-2">
        <FileText className="size-3" />
        <span>Add file</span>
      </CustomMenu.MenuItem>
      <CustomMenu.MenuItem onClick={onAddFolder} className="flex items-center gap-2">
        <FolderPlus className="size-3" />
        <span>Add folder</span>
      </CustomMenu.MenuItem>
    </CustomMenu>
  );
}

/**
 * Inline input row used for both Add-file and Add-folder. Renders one
 * row deeper than its parent so it visually nests. Enter submits, Esc
 * cancels, blur cancels (unless we're mid-create — submitting takes
 * one tick and we don't want a blur during the await to wipe state).
 */
function CreateInputRow({
  depth,
  state,
  onChange,
  onSubmit,
  onCancel,
}: {
  depth: number;
  state: CreateState;
  onChange: (v: string) => void;
  onSubmit: () => void;
  onCancel: () => void;
}) {
  const indent = { paddingLeft: `${depth * 14 + 8}px` } as const;
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    inputRef.current?.focus();
    inputRef.current?.select();
  }, []);

  const onKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === "Enter") {
      e.preventDefault();
      onSubmit();
    } else if (e.key === "Escape") {
      e.preventDefault();
      onCancel();
    }
  };

  const Icon = state.mode === "folder" ? Folder : FileText;
  const placeholder = state.mode === "folder" ? "folder-name" : "name (.md optional)";

  return (
    <div className="flex flex-col" data-testid="iw-agent-docs-tree-create-input">
      <div className="flex items-center gap-1.5 rounded-md py-1 pr-1 text-13" style={indent}>
        <span className="size-3.5 flex-shrink-0" />
        <Icon className="size-3.5 flex-shrink-0 text-tertiary" />
        <input
          ref={inputRef}
          type="text"
          value={state.value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={onKeyDown}
          // Blur = cancel, but don't trigger while we're mid-submit
          // (the submit await would lose the "busy" state if we wiped
          // createState here).
          onBlur={() => {
            if (!state.busy) onCancel();
          }}
          placeholder={placeholder}
          disabled={state.busy}
          className="focus:border-primary min-w-0 flex-1 rounded-sm border border-subtle bg-surface-1 px-1.5 py-0.5 text-13 text-primary outline-none disabled:opacity-50"
        />
      </div>
      {state.error && (
        <div className="text-red-500 px-2 pb-1 text-11" style={indent}>
          {state.error}
        </div>
      )}
    </div>
  );
}
