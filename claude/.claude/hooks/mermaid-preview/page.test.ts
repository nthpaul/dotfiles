import { describe, expect, test } from "bun:test";
import { buildPage, extractMermaidBlocks } from "./page.ts";

describe("extractMermaidBlocks", () => {
  test("returns every mermaid block in order", () => {
    const reply = [
      "Intro",
      "```mermaid",
      "flowchart TB",
      "  A --> B",
      "```",
      "Middle",
      "~~~mermaid",
      "sequenceDiagram",
      "  A->>B: hi",
      "~~~",
    ].join("\n");
    expect(extractMermaidBlocks(reply)).toEqual([
      "flowchart TB\n  A --> B",
      "sequenceDiagram\n  A->>B: hi",
    ]);
  });

  test("ignores other languages and blocks without a language", () => {
    const reply = "```ts\nconst a = 1;\n```\n```\nflowchart TB\n```";
    expect(extractMermaidBlocks(reply)).toEqual([]);
  });

  test("skips a mermaid example nested inside a longer fence", () => {
    const reply = "````markdown\n```mermaid\nflowchart TB\n  A --> B\n```\n````";
    expect(extractMermaidBlocks(reply)).toEqual([]);
  });

  test("matches the language case-insensitively and ignores extra info", () => {
    const reply = "```Mermaid title=x\nflowchart TB\n  A --> B\n```";
    expect(extractMermaidBlocks(reply)).toEqual(["flowchart TB\n  A --> B"]);
  });

  test("a shorter fence does not close a longer one", () => {
    const reply = "````mermaid\nflowchart TB\n```\n  A --> B\n````";
    expect(extractMermaidBlocks(reply)).toEqual(["flowchart TB\n```\n  A --> B"]);
  });

  test("an unclosed block runs to the end of the reply", () => {
    expect(extractMermaidBlocks("```mermaid\nflowchart TB\n  A --> B")).toEqual([
      "flowchart TB\n  A --> B",
    ]);
  });

  test("drops empty blocks and handles a reply with no fences", () => {
    expect(extractMermaidBlocks("```mermaid\n\n```")).toEqual([]);
    expect(extractMermaidBlocks("plain text")).toEqual([]);
  });
});

describe("buildPage", () => {
  const createdAt = new Date("2026-10-21T16:30:00");

  test("renders valid diagrams to inline SVG with their source", () => {
    const page = buildPage({ blocks: ["flowchart TB\n  A --> B"], project: "relay", createdAt });
    expect(page).toContain("<svg");
    expect(page).toContain("1 diagram<");
    expect(page).toContain("<summary>Source</summary>");
  });

  test("shows an error card for an invalid block and still renders the rest", () => {
    const page = buildPage({
      blocks: ["flowchart TB\n  A[unclosed", "flowchart TB\n  A --> B"],
      project: "relay",
      createdAt,
    });
    expect(page).toContain("Diagram 1 could not be rendered");
    expect(page).toContain("Parse error");
    expect(page).toContain("<h2>Diagram 2</h2>");
    expect(page.match(/<svg/g)).toHaveLength(1);
  });

  test("escapes the source and the project name", () => {
    const page = buildPage({
      blocks: ["not a diagram <script>alert(1)</script>"],
      project: "<b>repo</b>",
      createdAt,
    });
    expect(page).not.toContain("<script>alert(1)");
    expect(page).not.toContain("<b>repo</b>");
    expect(page).toContain("&lt;script&gt;");
  });

  test("allows only the download script, by hash", async () => {
    const page = buildPage({ blocks: ["flowchart TB\n  A --> B"], project: "My Repo", createdAt });
    expect(page).toContain("default-src 'none'");
    const hash = /script-src 'sha256-([^']+)'/.exec(page)?.[1];
    const script = /<script>([\s\S]*?)<\/script>/.exec(page)?.[1] ?? "";
    const digest = new Uint8Array(await crypto.subtle.digest("SHA-256", new TextEncoder().encode(script)));
    expect(hash).toBe(Buffer.from(digest).toString("base64"));
  });

  test("offers SVG and PNG downloads named after the project", () => {
    const page = buildPage({ blocks: ["flowchart TB\n  A --> B"], project: "My Repo", createdAt });
    expect(page).toContain('data-filename="my-repo-diagram-1"');
    expect(page).toContain('data-download="svg"');
    expect(page).toContain('data-download="png"');
  });
});
