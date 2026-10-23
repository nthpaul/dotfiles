import { createHash } from "node:crypto";
import { render } from "pele";
import diagramCss from "./diagram.css" with { type: "text" };
import downloadScript from "./download.js" with { type: "text" };
import { applyTones } from "./tone.ts";

// The only script the page may run, allowed by its hash so the CSP still blocks everything else.
const SCRIPT_HASH = createHash("sha256").update(downloadScript).digest("base64");

// Fence scanning follows CommonMark: a fence opens with 3+ backticks or tildes (up to 3 spaces
// of indent) and closes with the same character, at least as long. Tracking the open fence is
// what keeps a ```mermaid example inside a ````markdown block from being rendered.
const FENCE_OPEN = /^ {0,3}(`{3,}|~{3,})(.*)$/;

export function extractMermaidBlocks(markdown: string): string[] {
  const blocks: string[] = [];
  let open: { char: string; length: number; isMermaid: boolean; lines: string[] } | null = null;

  for (const line of markdown.split("\n")) {
    if (open === null) {
      const match = FENCE_OPEN.exec(line);
      if (match === null) continue;
      const fence = match[1];
      const info = match[2].trim();
      // A backtick fence's info string may not contain backticks; such a line is inline code.
      if (fence[0] === "`" && info.includes("`")) continue;
      const language = info.split(/\s+/)[0].toLowerCase();
      open = { char: fence[0], length: fence.length, isMermaid: language === "mermaid", lines: [] };
      continue;
    }
    const close = new RegExp(`^ {0,3}\\${open.char}{${open.length},}\\s*$`);
    if (close.test(line)) {
      if (open.isMermaid) blocks.push(open.lines.join("\n"));
      open = null;
      continue;
    }
    open.lines.push(line);
  }
  // An unclosed fence runs to the end of the document in CommonMark.
  if (open !== null && open.isMermaid) blocks.push(open.lines.join("\n"));

  return blocks.filter((block) => block.trim() !== "");
}

function escapeHtml(text: string): string {
  return text
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function fileSlug(text: string): string {
  return text.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "") || "diagram";
}

function renderDiagram(source: string, index: number, filePrefix: string): string {
  const sourceDetails = `<details><summary>Source</summary><pre>${escapeHtml(source)}</pre></details>`;
  try {
    const svg = applyTones(render(source).svg);
    const filename = `${filePrefix}-diagram-${index + 1}`;
    const actions = `<div class="actions"><button type="button" data-download="svg">SVG</button><button type="button" data-download="png">PNG</button></div>`;
    return `<section class="diagram" data-filename="${filename}"><div class="bar"><h2>Diagram ${index + 1}</h2>${actions}</div><div class="svg">${svg}</div>${sourceDetails}</section>`;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    return `<section class="diagram error"><h2>Diagram ${index + 1} could not be rendered</h2><pre class="message">${escapeHtml(message)}</pre>${sourceDetails}</section>`;
  }
}

export interface PageInput {
  blocks: string[];
  project: string;
  createdAt: Date;
}

export function buildPage({ blocks, project, createdAt }: PageInput): string {
  const time = createdAt.toLocaleString();
  const title = `${project} · ${time}`;
  const filePrefix = fileSlug(project);
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; script-src 'sha256-${SCRIPT_HASH}'">
<title>${escapeHtml(title)}</title>
<style>
  :root {
    color-scheme: light dark;
    --page-bg: #f6f8fa; --page-fg: #1f2328; --page-muted: #59636e; --page-card: #ffffff;
    --page-border: #d0d7de; --page-error: #cf222e; --page-button: #f6f8fa; --page-button-hover: #eaeef2;
    --page-font: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --page-font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --page-bg: #010409; --page-fg: #e6edf3; --page-muted: #9198a1; --page-card: #0d1117;
      --page-border: #3d444d; --page-error: #f85149; --page-button: #212830; --page-button-hover: #2a313c;
    }
  }
  body { margin: 0; padding: 24px 16px 48px; background: var(--page-bg); color: var(--page-fg);
    font: 14px/1.5 var(--page-font); }
  main { max-width: 1100px; margin: 0 auto; }
  header { margin-bottom: 20px; }
  header h1 { font-size: 16px; margin: 0; }
  header p { margin: 2px 0 0; color: var(--page-muted); }
  .diagram { background: var(--page-card); border: 1px solid var(--page-border); border-radius: 10px;
    padding: 16px; margin-bottom: 16px; }
  .diagram h2 { font-size: 13px; font-weight: 600; color: var(--page-muted); margin: 0 0 12px; }
  .bar { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
  .actions { display: flex; gap: 6px; }
  button { font: 12px/1 var(--page-font); color: var(--page-fg); background: var(--page-button);
    border: 1px solid var(--page-border); border-radius: 6px; padding: 5px 10px; cursor: pointer; }
  button:hover { background: var(--page-button-hover); }
  .svg { display: flex; justify-content: center; overflow-x: auto; }
  .error h2, .message { color: var(--page-error); }
  details { margin-top: 12px; }
  summary { cursor: pointer; color: var(--page-muted); }
  pre { font: 12px/1.45 var(--page-font-mono); white-space: pre-wrap; margin: 8px 0 0; }
</style>
<style id="diagram-css">
${diagramCss}</style>
</head>
<body>
<main>
<header><h1>${escapeHtml(project)}</h1><p>${escapeHtml(time)} · ${blocks.length} diagram${blocks.length === 1 ? "" : "s"}</p></header>
${blocks.map((block, index) => renderDiagram(block, index, filePrefix)).join("\n")}
</main>
<script>${downloadScript}</script>
</body>
</html>
`;
}
