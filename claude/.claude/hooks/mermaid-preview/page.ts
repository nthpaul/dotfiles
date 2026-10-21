import { render } from "pele";

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

function renderDiagram(source: string, index: number): string {
  const sourceDetails = `<details><summary>Source</summary><pre>${escapeHtml(source)}</pre></details>`;
  try {
    const { svg } = render(source);
    return `<section class="diagram"><h2>Diagram ${index + 1}</h2><div class="svg">${svg}</div>${sourceDetails}</section>`;
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
  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:">
<title>${escapeHtml(title)}</title>
<style>
  :root {
    color-scheme: light dark;
    --page-bg: #fafafa; --page-fg: #1f1f1f; --page-muted: #6e6e6e; --page-card: #fff;
    --page-border: #e2e2e2; --page-error: #b3261e;
    --pele-bg: var(--page-card); --pele-fg: var(--page-fg); --pele-muted: var(--page-muted);
    --pele-line: #4a4a4a; --pele-surface: #f3f3f3; --pele-surface-alt: #e9e9e9;
    --pele-border: #c8c8c8; --pele-accent: #2f6fde; --pele-error: var(--page-error);
    --pele-font: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    --pele-font-mono: ui-monospace, SFMono-Regular, Menlo, monospace;
  }
  @media (prefers-color-scheme: dark) {
    :root {
      --page-bg: #161616; --page-fg: #e6e6e6; --page-muted: #9a9a9a; --page-card: #1f1f1f;
      --page-border: #333; --page-error: #f2867e;
      --pele-line: #b5b5b5; --pele-surface: #2a2a2a; --pele-surface-alt: #323232;
      --pele-border: #4a4a4a; --pele-accent: #7aa7ff;
    }
  }
  body { margin: 0; padding: 24px 16px 48px; background: var(--page-bg); color: var(--page-fg);
    font: 14px/1.5 var(--pele-font); }
  main { max-width: 1100px; margin: 0 auto; }
  header { margin-bottom: 20px; }
  header h1 { font-size: 16px; margin: 0; }
  header p { margin: 2px 0 0; color: var(--page-muted); }
  .diagram { background: var(--page-card); border: 1px solid var(--page-border); border-radius: 10px;
    padding: 16px; margin-bottom: 16px; }
  .diagram h2 { font-size: 13px; font-weight: 600; color: var(--page-muted); margin: 0 0 12px; }
  .svg { display: flex; justify-content: center; overflow-x: auto; }
  .error h2, .message { color: var(--page-error); }
  details { margin-top: 12px; }
  summary { cursor: pointer; color: var(--page-muted); }
  pre { font: 12px/1.45 var(--pele-font-mono); white-space: pre-wrap; margin: 8px 0 0; }
</style>
</head>
<body>
<main>
<header><h1>${escapeHtml(project)}</h1><p>${escapeHtml(time)} · ${blocks.length} diagram${blocks.length === 1 ? "" : "s"}</p></header>
${blocks.map(renderDiagram).join("\n")}
</main>
</body>
</html>
`;
}
