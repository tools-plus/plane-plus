/**
 * PP-71 / GFM extensions: Tiny markdown → HTML renderer for the AI/VAULTS preview pane.
 *
 * Why hand-roll instead of pulling react-markdown / marked / markdown-it:
 *   - The repo has react-markdown@8 installed but transitively breaks vite
 *     dep-optimization (mdast-util-to-hast 13 dropped `all`/`one` exports
 *     remark-rehype@10 still tries to import). It's effectively dead code in
 *     the repo today (only one unused MarkdownRenderer wrapper imports it).
 *   - We want preview to be deterministic and collab-free; the v1 spec is
 *     "code blocks, lists, headings, links, tables all visible" — solvable
 *     in a couple hundred lines without dragging in a transitive dep tree.
 *   - The same renderer can ship to the backend later if we want
 *     server-side previews; pure-string in/out, no DOM.
 *
 * SAFETY: Input is HTML-escaped FIRST. Then a fixed set of regex transforms
 * apply markdown patterns. We never accept raw HTML through. Callers may
 * use `dangerouslySetInnerHTML` on the result.
 *
 * What it handles (CommonMark + GFM subset):
 *   # ## ### #### headings
 *   **bold**, __bold__
 *   *italic*, _italic_
 *   ~~strikethrough~~                              (GFM)
 *   `inline code`
 *   ```fenced code blocks```
 *   - bullet, * bullet, 1. ordered (single-level only, v1)
 *   - [ ] task / - [x] checked task                (GFM)
 *   [text](url) links — http/https only, opened in new tab
 *   bare http(s)://… autolinks                     (GFM)
 *   [^id] footnote refs + [^id]: definition rows   (GFM-ish, single-line defs only)
 *   > blockquotes
 *   --- horizontal rule
 *   | col | col |  with |---|:---:|---:| separator (GFM tables, with alignment)
 *   blank line → paragraph break
 *
 * What it punts on:
 *   - Nested lists (one level only)
 *   - Inline HTML (intentionally rejected)
 *   - Definition lists
 *   - Multi-line table cells / multi-line footnote bodies
 */

const ESCAPE_MAP: Record<string, string> = {
  "&": "&amp;",
  "<": "&lt;",
  ">": "&gt;",
  '"': "&quot;",
  "'": "&#39;",
};

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ESCAPE_MAP[c]);
}

/** Footnote-definition map shared across the parse → render pipeline. */
type FootnoteCtx = {
  /** order in which refs first appear (drives the rendered list ordering) */
  order: string[];
  /** id → already-escaped + inline-applied HTML */
  defs: Map<string, string>;
  /** ids actually referenced in the body (to avoid orphan defs printing) */
  referenced: Set<string>;
};

function newFootnoteCtx(): FootnoteCtx {
  return { order: [], defs: new Map(), referenced: new Set() };
}

// Apply inline transforms (bold/italic/strike/code/link/autolink/footnote-ref).
// Operates on already-escaped text. The `fn` ctx, if passed, lets us collect
// footnote-reference order so the rendered footnote list matches the body order.
function applyInline(escaped: string, fn?: FootnoteCtx): string {
  let out = escaped;
  // inline code first so * / ~ inside backticks isn't picked up
  out = out.replace(/`([^`\n]+)`/g, (_m, code) => `<code>${code}</code>`);
  // bold then italic
  out = out.replace(/\*\*([^*\n]+)\*\*/g, "<strong>$1</strong>");
  out = out.replace(/__([^_\n]+)__/g, "<strong>$1</strong>");
  out = out.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, "$1<em>$2</em>");
  out = out.replace(/(^|[^_])_([^_\n]+)_(?!_)/g, "$1<em>$2</em>");
  // strikethrough — GFM uses ~~text~~
  out = out.replace(/~~([^~\n]+)~~/g, "<del>$1</del>");
  // footnote refs `[^id]` — must run BEFORE link transform so we don't get
  // confused with `[text](url)`. Refs have no parens immediately after.
  if (fn) {
    out = out.replace(/\[\^([A-Za-z0-9_-]+)\](?!:)/g, (_m, id: string) => {
      fn.referenced.add(id);
      if (!fn.order.includes(id)) fn.order.push(id);
      return `<sup class="footnote-ref"><a id="fnref-${escapeHtml(id)}" href="#fn-${escapeHtml(
        id
      )}">[${escapeHtml(id)}]</a></sup>`;
    });
  }
  // explicit links — only http(s) — text + url already escaped
  out = out.replace(/\[([^\]]+)\]\((https?:[^\s)]+)\)/g, (_m, text, url) => {
    return `<a href="${url}" target="_blank" rel="noopener noreferrer">${text}</a>`;
  });
  // autolinks — bare http(s)://… not already inside an <a href="…"> attribute.
  // Anchored to start-of-string OR a whitespace boundary so `href="https://`
  // doesn't double-link. Trailing sentence punctuation (.,;:!?) is GFM-stripped
  // off the URL and pushed back into the surrounding text.
  out = out.replace(/(^|[\s(])(https?:\/\/[^\s<>"')]+)/g, (_m, before: string, url: string) => {
    let trail = "";
    while (url.length > 0 && /[.,;:!?]/.test(url[url.length - 1])) {
      trail = url[url.length - 1] + trail;
      url = url.slice(0, -1);
    }
    return `${before}<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>${trail}`;
  });
  return out;
}

type ListItem = { text: string; task?: "checked" | "unchecked" };
type Align = "left" | "center" | "right" | null;

type Block =
  | { kind: "p"; text: string }
  | { kind: "h"; level: 1 | 2 | 3 | 4; text: string }
  | { kind: "code"; lang: string; body: string }
  | { kind: "ul"; items: ListItem[] }
  | { kind: "ol"; items: ListItem[] }
  | { kind: "blockquote"; text: string }
  | { kind: "hr" }
  | { kind: "table"; head: string[]; rows: string[][]; align: Align[] };

/** Split a `| a | b | c |` row into trimmed cells (border pipes optional). */
function splitTableRow(s: string): string[] {
  let row = s.trim();
  if (row.startsWith("|")) row = row.slice(1);
  if (row.endsWith("|")) row = row.slice(0, -1);
  return row.split("|").map((c) => c.trim());
}

/** Try to parse a GFM table starting at `lines[start]`. Returns the block + lines consumed, or null. */
function tryParseTable(lines: string[], start: number): { block: Block; consumed: number } | null {
  if (start + 1 >= lines.length) return null;
  const headLine = lines[start];
  const sepLine = lines[start + 1];
  if (!headLine.includes("|")) return null;
  if (!sepLine.includes("|") && !sepLine.includes("-")) return null;

  const sepCells = splitTableRow(sepLine);
  if (sepCells.length === 0) return null;

  const align: Align[] = [];
  for (const cell of sepCells) {
    const m = /^(:?)-{1,}(:?)$/.exec(cell);
    if (!m) return null;
    if (m[1] === ":" && m[2] === ":") align.push("center");
    else if (m[2] === ":") align.push("right");
    else if (m[1] === ":") align.push("left");
    else align.push(null);
  }

  const head = splitTableRow(headLine);
  if (head.length !== sepCells.length) return null;

  const rows: string[][] = [];
  let i = start + 2;
  while (i < lines.length && lines[i].includes("|") && lines[i].trim() !== "") {
    const r = splitTableRow(lines[i]);
    while (r.length < head.length) r.push("");
    if (r.length > head.length) r.length = head.length;
    rows.push(r);
    i++;
  }

  return {
    block: { kind: "table", head, rows, align },
    consumed: i - start,
  };
}

/**
 * First pass: pluck `[^id]: body` lines out into the footnote ctx so they
 * don't render as paragraphs. v1 supports single-line defs only — anything
 * after the first line of the def is just treated as its own block.
 */
function extractFootnoteDefs(input: string, fn: FootnoteCtx): string {
  const lines = input.replace(/\r\n/g, "\n").split("\n");
  const out: string[] = [];
  for (const line of lines) {
    const m = /^\s*\[\^([A-Za-z0-9_-]+)\]:\s*(.*)$/.exec(line);
    if (m) {
      const id = m[1];
      const body = applyInline(escapeHtml(m[2]), fn);
      fn.defs.set(id, body);
      // drop this line — definition is hoisted into the footnotes section
      continue;
    }
    out.push(line);
  }
  return out.join("\n");
}

function parse(input: string): Block[] {
  const lines = input.split("\n");
  const blocks: Block[] = [];
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    // fenced code
    const fence = /^```(\S*)\s*$/.exec(line);
    if (fence) {
      const lang = fence[1] || "";
      const body: string[] = [];
      i++;
      while (i < lines.length && !/^```\s*$/.test(lines[i])) {
        body.push(lines[i]);
        i++;
      }
      i++; // skip closing fence (or EOF)
      blocks.push({ kind: "code", lang, body: body.join("\n") });
      continue;
    }

    // GFM table — must be tried BEFORE paragraph fallback (and BEFORE hr,
    // since a single `---` separator on the second line could otherwise be
    // misclassified as an hr if we happened to peek at it via paragraph).
    const tbl = tryParseTable(lines, i);
    if (tbl) {
      blocks.push(tbl.block);
      i += tbl.consumed;
      continue;
    }

    // hr
    if (/^\s*(---|\*\*\*|___)\s*$/.test(line)) {
      blocks.push({ kind: "hr" });
      i++;
      continue;
    }

    // heading
    const h = /^(#{1,4})\s+(.+?)\s*#*\s*$/.exec(line);
    if (h) {
      blocks.push({ kind: "h", level: h[1].length as 1 | 2 | 3 | 4, text: h[2] });
      i++;
      continue;
    }

    // bullet list (with optional GFM task-list prefix on each item)
    if (/^\s*[-*]\s+/.test(line)) {
      const items: ListItem[] = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) {
        const raw = lines[i].replace(/^\s*[-*]\s+/, "");
        const tm = /^\[([ xX])\]\s+(.*)$/.exec(raw);
        if (tm) items.push({ text: tm[2], task: tm[1] === " " ? "unchecked" : "checked" });
        else items.push({ text: raw });
        i++;
      }
      blocks.push({ kind: "ul", items });
      continue;
    }

    // ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      const items: ListItem[] = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) {
        items.push({ text: lines[i].replace(/^\s*\d+\.\s+/, "") });
        i++;
      }
      blocks.push({ kind: "ol", items });
      continue;
    }

    // blockquote
    if (/^\s*>\s?/.test(line)) {
      const buf: string[] = [];
      while (i < lines.length && /^\s*>\s?/.test(lines[i])) {
        buf.push(lines[i].replace(/^\s*>\s?/, ""));
        i++;
      }
      blocks.push({ kind: "blockquote", text: buf.join("\n") });
      continue;
    }

    // blank line — skip
    if (/^\s*$/.test(line)) {
      i++;
      continue;
    }

    // paragraph: gather until blank or block boundary. We re-check `tryParseTable`
    // at each line so a table mid-paragraph still wins.
    const buf: string[] = [line];
    i++;
    while (
      i < lines.length &&
      !/^\s*$/.test(lines[i]) &&
      !lines[i].startsWith("```") &&
      !/^#{1,4}\s+/.test(lines[i]) &&
      !/^\s*[-*]\s+/.test(lines[i]) &&
      !/^\s*\d+\.\s+/.test(lines[i]) &&
      !/^\s*>/.test(lines[i]) &&
      !/^\s*(---|\*\*\*|___)\s*$/.test(lines[i]) &&
      !tryParseTable(lines, i)
    ) {
      buf.push(lines[i]);
      i++;
    }
    blocks.push({ kind: "p", text: buf.join("\n") });
  }
  return blocks;
}

function renderListItem(it: ListItem, fn: FootnoteCtx): string {
  const inner = applyInline(escapeHtml(it.text), fn);
  if (it.task) {
    const checked = it.task === "checked" ? " checked" : "";
    // GFM convention: `class="task-list-item"` so prose / custom CSS can target
    // task list rows (remove default bullet, align checkbox).
    return `<li class="task-list-item"><input type="checkbox" disabled${checked}/> ${inner}</li>`;
  }
  return `<li>${inner}</li>`;
}

function renderBlock(b: Block, fn: FootnoteCtx): string {
  switch (b.kind) {
    case "h": {
      const inner = applyInline(escapeHtml(b.text), fn);
      return `<h${b.level}>${inner}</h${b.level}>`;
    }
    case "p": {
      const inner = applyInline(escapeHtml(b.text), fn).replace(/\n/g, "<br/>");
      return `<p>${inner}</p>`;
    }
    case "code": {
      const langClass = b.lang ? ` class="language-${escapeHtml(b.lang)}"` : "";
      return `<pre><code${langClass}>${escapeHtml(b.body)}</code></pre>`;
    }
    case "ul": {
      const lis = b.items.map((it) => renderListItem(it, fn)).join("");
      // mark the whole list as a task list when EVERY item has a checkbox —
      // lets prose CSS strip the default bullet via `ul.task-list`.
      const allTasks = b.items.length > 0 && b.items.every((it) => !!it.task);
      const cls = allTasks ? ' class="contains-task-list"' : "";
      return `<ul${cls}>${lis}</ul>`;
    }
    case "ol": {
      const lis = b.items.map((it) => renderListItem(it, fn)).join("");
      return `<ol>${lis}</ol>`;
    }
    case "blockquote": {
      const inner = applyInline(escapeHtml(b.text), fn).replace(/\n/g, "<br/>");
      return `<blockquote>${inner}</blockquote>`;
    }
    case "hr":
      return "<hr/>";
    case "table": {
      const renderCell = (text: string, idx: number, isHead: boolean) => {
        const tag = isHead ? "th" : "td";
        const a = b.align[idx];
        const styleAttr = a ? ` style="text-align:${a}"` : "";
        return `<${tag}${styleAttr}>${applyInline(escapeHtml(text), fn)}</${tag}>`;
      };
      const headHtml = `<thead><tr>${b.head.map((c, idx) => renderCell(c, idx, true)).join("")}</tr></thead>`;
      const bodyHtml = `<tbody>${b.rows
        .map((row) => `<tr>${row.map((c, idx) => renderCell(c, idx, false)).join("")}</tr>`)
        .join("")}</tbody>`;
      return `<table>${headHtml}${bodyHtml}</table>`;
    }
  }
}

/** Render the trailing footnotes section, if any refs were seen in the body. */
function renderFootnotes(fn: FootnoteCtx): string {
  const ids = fn.order.filter((id) => fn.referenced.has(id) && fn.defs.has(id));
  if (ids.length === 0) return "";
  const lis = ids
    .map((id) => {
      const body = fn.defs.get(id) ?? "";
      const safeId = escapeHtml(id);
      // back-link arrow → returns to the inline reference
      return `<li id="fn-${safeId}">${body} <a href="#fnref-${safeId}" class="footnote-back" aria-label="Back to reference">↩</a></li>`;
    })
    .join("");
  return `<section class="footnotes"><hr/><ol>${lis}</ol></section>`;
}

export function renderMarkdown(input: string): string {
  if (!input) return "";
  const fn = newFootnoteCtx();
  const stripped = extractFootnoteDefs(input, fn);
  const body = parse(stripped)
    .map((b) => renderBlock(b, fn))
    .join("\n");
  return body + renderFootnotes(fn);
}
