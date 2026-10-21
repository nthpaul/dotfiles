// Renderer behind mermaid-preview.sh. Reads the Stop hook input on stdin, renders every
// ```mermaid block in Claude's final reply with Pele, writes one HTML page, and opens it in a
// background browser tab. Built into render.mjs (Pele bundled in) by build.sh, and written
// against Node APIs so the same file runs under Bun or Node.
import { spawn } from "node:child_process";
import { mkdir, readdir, rm, stat, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, join } from "node:path";
import { buildPage, extractMermaidBlocks } from "./page.ts";

// Same config root Claude Code and Bazaar sync use, so a relocated config keeps its pages.
const CONFIG_DIR = process.env.CLAUDE_CONFIG_DIR || join(homedir(), ".claude");
const OUTPUT_DIR = join(CONFIG_DIR, "mermaid-preview");
const KEEP_MS = 7 * 24 * 60 * 60 * 1000;

interface StopInput {
  session_id?: string;
  cwd?: string;
  last_assistant_message?: string;
}

async function readStdin(): Promise<string> {
  const chunks: Buffer[] = [];
  for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks).toString("utf8");
}

async function pruneOldPages(now: number): Promise<void> {
  for (const name of await readdir(OUTPUT_DIR)) {
    if (!name.endsWith(".html")) continue;
    const path = join(OUTPUT_DIR, name);
    if (now - (await stat(path)).mtimeMs > KEEP_MS) await rm(path, { force: true });
  }
}

function fileStamp(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, "0");
  return `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}-${pad(date.getHours())}${pad(date.getMinutes())}${pad(date.getSeconds())}`;
}

async function main(): Promise<void> {
  const input = JSON.parse(await readStdin()) as StopInput;
  const blocks = extractMermaidBlocks(input.last_assistant_message ?? "");
  if (blocks.length === 0) return;

  const createdAt = new Date();
  await mkdir(OUTPUT_DIR, { recursive: true });
  await pruneOldPages(createdAt.getTime());

  const session = (input.session_id ?? "session").slice(0, 8);
  const path = join(OUTPUT_DIR, `${fileStamp(createdAt)}-${session}.html`);
  const project = input.cwd ? basename(input.cwd) : "Claude Code";
  await writeFile(path, buildPage({ blocks, project, createdAt }));

  // -g opens the tab without bringing the browser to the front.
  if (process.platform === "darwin") {
    const opener = spawn("open", ["-g", path], { detached: true, stdio: "ignore" });
    // Without a listener, a missing `open` would surface as an uncaught exception.
    opener.on("error", (error) => console.error("mermaid-preview: open failed:", error.message));
    opener.unref();
  }
}

try {
  await main();
} catch (error) {
  console.error("mermaid-preview:", error);
}
