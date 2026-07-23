/**
 * PP-71: Build a folder tree from a flat list of paths by splitting on "/".
 *
 * Input:  ["plans/surya.md", "plans/vikrant.md", "specs/foo.md"]
 * Output: [
 *   { name: "plans", type: "folder", children: [
 *     { name: "surya.md", type: "file", path: "plans/surya.md" },
 *     { name: "vikrant.md", type: "file", path: "plans/vikrant.md" },
 *   ]},
 *   { name: "specs", type: "folder", children: [
 *     { name: "foo.md", type: "file", path: "specs/foo.md" },
 *   ]},
 * ]
 *
 * Folders are sorted alphabetically, files alphabetically within folders.
 * Folders sort before files at the same depth.
 *
 * Round 2 polish: `extraFolders` lets the tree show *empty* folders that
 * don't yet contain any files. The data model has no folder entity —
 * folders are synthesised from path prefixes — so when the user uses
 * the per-folder "Add folder" affordance we want to avoid persisting a
 * placeholder file. Instead the UI keeps the new prefix in client
 * state and passes it here as an extra folder; once a file is created
 * inside, the natural prefix takes over and the extra entry can be
 * dropped. Each entry is a slash-separated prefix like "blogs/wip".
 */

import type { TAgentDocTreeNode } from "@/services/agent-docs";

type MutableNode = TAgentDocTreeNode & { children: MutableNode[] };

// Folders before files; alphabetical within a kind. Recursive.
function sortNode(node: MutableNode): void {
  node.children.sort((a, b) => {
    if (a.type !== b.type) return a.type === "folder" ? -1 : 1;
    return a.name.localeCompare(b.name);
  });
  for (const c of node.children) sortNode(c);
}

export function buildAgentDocTree(paths: string[], extraFolders: Iterable<string> = []): TAgentDocTreeNode[] {
  const root: MutableNode = { name: "", path: "", type: "folder", children: [] };

  for (const fullPath of paths) {
    if (!fullPath) continue;
    const segments = fullPath.split("/").filter(Boolean);
    if (segments.length === 0) continue;

    let cursor: MutableNode = root;
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const isLeaf = i === segments.length - 1;
      const segPath = segments.slice(0, i + 1).join("/");

      let next = cursor.children.find((c) => c.name === seg && c.type === (isLeaf ? "file" : "folder"));
      if (!next) {
        next = {
          name: seg,
          path: isLeaf ? fullPath : segPath,
          type: isLeaf ? "file" : "folder",
          children: [],
        };
        cursor.children.push(next);
      }
      cursor = next;
    }
  }

  // Layer in client-state-only "ghost" folders — folders the user
  // wanted to create but for which no file exists yet. Walk segments
  // creating folder nodes only; never produce a file leaf. If a file
  // happened to already exist with the same name as one of the
  // intermediate segments (unlikely but possible), prefer the
  // pre-existing file and skip — folders and files can't share a
  // name at the same level.
  for (const extra of extraFolders) {
    if (!extra) continue;
    const segments = extra.split("/").filter(Boolean);
    if (segments.length === 0) continue;

    let cursor: MutableNode = root;
    let aborted = false;
    for (let i = 0; i < segments.length; i++) {
      const seg = segments[i];
      const segPath = segments.slice(0, i + 1).join("/");
      const conflictingFile = cursor.children.find((c) => c.name === seg && c.type === "file");
      if (conflictingFile) {
        aborted = true;
        break;
      }
      let next = cursor.children.find((c) => c.name === seg && c.type === "folder");
      if (!next) {
        next = { name: seg, path: segPath, type: "folder", children: [] };
        cursor.children.push(next);
      }
      cursor = next;
    }
    if (aborted) continue;
  }

  sortNode(root);
  return root.children;
}
