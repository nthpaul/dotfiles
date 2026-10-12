#!/usr/bin/env python3
"""Build a portable HTML product plan without executing its prototype code."""

from __future__ import annotations

import argparse
import base64
from html import escape
from functools import lru_cache
import json
import math
import mimetypes
import os
from pathlib import Path
import re
import shutil
import subprocess
import struct
import sys
import tempfile

from validate import DIAGRAM_ID, IDENTIFIER, check_plan, existing_tables, local_path, validate


PACKAGE = Path(__file__).resolve().parent.parent
VIEWER = PACKAGE / "assets/viewer"
SCRIPT_ORDER = ("spec.js", "diagrams.js", "prototype.js", "viewer.js")


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def json_text(value) -> str:
    return json.dumps(value, ensure_ascii=True, indent=2) + "\n"


def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def resolve_node(explicit: str | None = None) -> str:
    if explicit:
        candidate = shutil.which(explicit) or explicit
        if not Path(candidate).is_file():
            raise ValueError(f"Node executable not found: {explicit}")
        return str(Path(candidate).resolve())
    candidate = shutil.which("node")
    if candidate:
        return candidate
    codex_home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()
    roots = [
        codex_home / "runtimes/codex-primary-runtime/dependencies/node/bin/node",
        codex_home / "cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        codex_home.parent / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
        Path.home() / ".cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node",
    ]
    for path in roots:
        if path.is_file():
            return str(path)
    raise ValueError("Node is required to render diagrams; pass --node or load Codex workspace dependencies")


def metadata(plan: dict) -> dict[str, str]:
    document = plan.get("document", {})
    title = str(document.get("title", "Product plan"))
    return {
        "TITLE": title,
        "PAGE_TITLE": str(document.get("pageTitle", title)),
        "DATE": str(document.get("date", "Proposed design")),
        "SUBTITLE": str(document.get("subtitle", "Data model, logic and data flow")),
        "SAMPLE_LABEL": str(document.get("sampleLabel", "Proposed design")),
        "BRAND": str(document.get("brand", "traba")),
        "EYEBROW": str(document.get("eyebrow", "PRODUCT REVIEW")),
    }


def source_rows(plan: dict) -> list[tuple[str, str]]:
    document = plan.get("document", {})
    sources = list(document.get("sources", [])) + list(plan.get("sources", []))
    if document.get("source"):
        sources.insert(0, document["source"])
    result = []
    for source in sources:
        if isinstance(source, (list, tuple)) and len(source) == 2:
            title, url = source
        elif isinstance(source, dict):
            title = source.get("title", source.get("label", "Source"))
            url = source.get("url", source.get("path", ""))
        elif isinstance(source, str):
            title, url = "Source", source
        else:
            raise ValueError("Sources must be [title, URL/path], an object, or a URL/path")
        if not isinstance(url, str) or not url:
            raise ValueError("Each source needs a URL or path")
        result.append((str(title), url))
    return result


def md_cell(value) -> str:
    return str(value or "").replace("|", "\\|").replace("\r", "").replace("\n", "<br>")


def diagram_markdown(diagrams: list[dict]) -> list[str]:
    lines = []
    for diagram in diagrams:
        lines += ["### " + diagram["title"], "", diagram["description"], "",
                  f"![{diagram['title']}](diagrams/{diagram['id']}.svg)", "",
                  "```mermaid", diagram["mermaid"], "```", ""]
    return lines


def markdown_plan(plan: dict, diagrams: list[dict]) -> str:
    doc = metadata(plan)
    authored = plan.get("document", {})
    summary = plan.get("summary", {})
    lines = ["# " + doc["TITLE"], "", doc["DATE"] + " · " + doc["SUBTITLE"], "",
             doc["SAMPLE_LABEL"], ""]
    if summary.get("decision"):
        lines += [str(summary["decision"]), ""]
    if summary.get("nextAction"):
        lines += ["Next action: " + str(summary["nextAction"]), ""]
    for key, title in (("reuse", "Reuse"), ("netNew", "Net new"), ("buildSequence", "Build sequence")):
        if summary.get(key):
            lines += ["## " + title, ""] + ["- " + str(value) for value in summary[key]] + [""]
    if summary.get("evidence"):
        lines += ["## Evidence", "", str(summary["evidence"]), ""]
    lines += ["## Source requirements and evidence", ""]
    lines += ["- [" + title.replace("]", "\\]") + "](" + url.replace(" ", "%20") + ")" for title, url in source_rows(plan)]
    if plan.get("decisions"):
        lines += ["", "## Design decisions", ""] + ["- " + str(v) for v in plan["decisions"]]
    lines += ["", "## Diagrams", "", "The HTML preview includes fit/zoom controls and editable SVG/Mermaid downloads.", "",
              "[All diagrams and editable sources](diagrams.md)", ""]
    if authored.get("diagramNote"):
        lines += [str(authored["diagramNote"]), ""]
    lines += diagram_markdown(diagrams)
    lines += ["## Complete data model", ""]
    if authored.get("modelIntro"):
        lines += ["### " + str(authored.get("modelConventionsTitle", "Storage and state conventions")), "",
                  str(authored["modelIntro"]), ""]
    for table in plan["tables"]:
        lines += ["### " + table["name"], "", table.get("purpose", ""), "",
                  "| Field | Type | Rule | Foreign key |", "| --- | --- | --- | --- |"]
        for field in table["fields"]:
            lines.append("| " + " | ".join(md_cell(field.get(k, "")) for k in ("name", "type", "rule", "relation")) + " |")
        lines += ["", "Relationships: " + table.get("relationships", ""), ""]
        lines += ["- " + str(v) for v in table.get("constraints", [])]
        lines.append("")
    if authored.get("notStored"):
        lines += ["### What is intentionally not stored", "", str(authored["notStored"]), ""]
    lines += ["## Existing tables and services", "", "| Table / service | Change | Why |", "| --- | --- | --- |"]
    lines += ["| " + " | ".join(md_cell(row.get(k, "")) for k in ("name", "change", "why")) + " |"
              for row in plan["existing"] if isinstance(row, dict)]
    lines += ["", "## Logic and data flow", ""]
    if authored.get("flowContract"):
        lines += [str(authored["flowContract"]), ""]
    for flow in plan["flows"]:
        lines += ["### " + flow.get("title", flow["id"]), "", flow.get("summary", ""), "",
                  "| Step | Input | Reads / decision | Writes | Output / next action |", "| --- | --- | --- | --- | --- |"]
        lines += ["| " + " | ".join(md_cell(v) for v in step) + " |" for step in flow["steps"]]
        lines.append("")
    for note in authored.get("flowNotes", []):
        lines += ["### " + str(note.get("title", "Flow note")), "", str(note.get("text", "")), ""]
    if plan.get("questions"):
        lines += ["## Decisions still needing input", ""] + ["- " + str(v) for v in plan["questions"]]
    return "\n".join(lines).rstrip() + "\n"


def dot_quote(text) -> str:
    return json.dumps(str(text), ensure_ascii=False)


def graph_start(direction: str) -> list[str]:
    if direction not in ("TB", "BT", "LR", "RL"):
        raise ValueError(f"Unsupported graph direction: {direction}")
    return [f'digraph G {{ graph [rankdir={direction}, bgcolor="white", pad=0.3, nodesep=0.5, ranksep=0.65];',
            'node [shape=box, style="rounded,filled", fillcolor="#f5ebff", color="#d9b3ff", fontname="Poppins", fontsize=12, fontcolor="#08105e", margin="0.18,0.13"];',
            'edge [fontname="Poppins", fontsize=10, fontcolor="#66788a", color="#9ca0c9", arrowsize=0.7];']


@lru_cache(maxsize=1)
def poppins_advances() -> tuple[dict[int, int], int]:
    """Read BMP glyph advances from the bundled regular TTF used by SVG text."""
    data = local_path(VIEWER, "fonts/Poppins-Regular.ttf").read_bytes()
    u16 = lambda offset: struct.unpack_from(">H", data, offset)[0]
    i16 = lambda offset: struct.unpack_from(">h", data, offset)[0]
    u32 = lambda offset: struct.unpack_from(">I", data, offset)[0]
    tables = {data[offset:offset + 4].decode("ascii"): u32(offset + 8)
              for offset in range(12, 12 + 16 * u16(4), 16)}
    units = u16(tables["head"] + 18)
    metric_count = u16(tables["hhea"] + 34)
    cmap = tables["cmap"]
    candidates = []
    for offset in range(cmap + 4, cmap + 4 + 8 * u16(cmap + 2), 8):
        subtable = cmap + u32(offset + 4)
        if u16(subtable) == 4:
            candidates.append((u16(offset) == 3 and u16(offset + 2) == 1, subtable))
    if not candidates:
        raise ValueError("Bundled Poppins needs a Unicode format-4 cmap")
    _, subtable = max(candidates)
    count = u16(subtable + 6) // 2
    ends = subtable + 14
    starts = ends + 2 * count + 2
    deltas = starts + 2 * count
    ranges = deltas + 2 * count
    advances = {}
    for index in range(count):
        delta = i16(deltas + 2 * index)
        relative = u16(ranges + 2 * index)
        first, last = u16(starts + 2 * index), u16(ends + 2 * index)
        for code in range(first, last + 1):
            if relative:
                glyph = u16(ranges + 2 * index + relative + 2 * (code - first))
                glyph = (glyph + delta) & 0xFFFF if glyph else 0
            else:
                glyph = (code + delta) & 0xFFFF
            advances[code] = u16(tables["hmtx"] + 4 * min(glyph, metric_count - 1))
    advances.setdefault(0, u16(tables["hmtx"]))
    return advances, units


def schema_cell_width(text: str) -> int:
    advances, units = poppins_advances()
    width = max(sum(advances.get(ord(char), advances[0]) for char in line) for line in text.split("\n"))
    return math.ceil(width * 12 / units) + 20


def schema_table_label(name: str, fields: list[dict], existing: bool = False) -> str:
    caption = name + (" · existing · referenced columns" if existing else " · new")
    name_width = max(schema_cell_width(field["name"]) for field in fields)
    type_width = max(schema_cell_width(field["type"]) for field in fields)
    rows = "".join(f'<TR><TD WIDTH="{name_width}" ALIGN="LEFT">{escape(field["name"])}</TD>'
                   f'<TD WIDTH="{type_width}" ALIGN="LEFT">{escape(field["type"])}</TD></TR>' for field in fields)
    border, fill = ("#a8d9c2", "#edf8f3") if existing else ("#e2e5e9", "#e6ccff")
    return f'<<TABLE BORDER="1" COLOR="{border}" BGCOLOR="white" CELLBORDER="0" CELLSPACING="0" CELLPADDING="6"><TR><TD WIDTH="{schema_cell_width(caption)}" COLSPAN="2" ALIGN="LEFT" BGCOLOR="{fill}">{escape(caption)}</TD></TR>{rows}</TABLE>>'


def schema_diagram(plan: dict, full: bool) -> dict:
    lines = graph_start("LR" if full else "TB")
    tables = {table["name"]: table for table in plan["tables"]}
    declared_fields = {}
    for entry in [*plan.get("existing", []), *plan.get("existingTables", []), *plan.get("referenceTables", [])]:
        if not isinstance(entry, dict) or not isinstance(entry.get("fields"), list):
            continue
        fields = {(field["name"] if isinstance(field, dict) else field): field if isinstance(field, dict) else {"name": field}
                  for field in entry["fields"]}
        for name in existing_tables({"existing": [entry]}):
            declared_fields[name] = fields
    used_targets = {field["relation"].split(".")[0] for table in tables.values()
                    for field in table["fields"] if field.get("relation")}
    target_columns = {}
    for table in tables.values():
        for field in table["fields"]:
            if field.get("relation"):
                target, column = field["relation"].split(".")
                target_columns.setdefault(target, set()).add(column)
    mermaid = ["erDiagram"]
    for name in sorted(used_targets - tables.keys()):
        if not full:
            lines.append(f'{dot_quote(name)} [label={dot_quote(name + chr(10) + "existing")},fillcolor="#edf8f3",color="#a8d9c2"];')
            continue
        fields = [{"name": column, "type": declared_fields.get(name, {}).get(column, {}).get("type") or "unknown"}
                  for column in sorted(target_columns[name])]
        label = schema_table_label(name, fields, existing=True)
        lines.append(f'{dot_quote(name)} [shape=plain,label={label}];')
        mermaid += [f"    %% {name}: existing · referenced columns", f"    {name} {{"]
        for field in fields:
            kind = re.sub(r"[^A-Za-z0-9_\[\]-]", "_", field["type"].split()[0])
            key = " PK" if " PK" in field["type"] else " FK" if " FK" in field["type"] else ""
            mermaid.append(f'        {kind} {field["name"]}{key} "existing · referenced columns"')
        mermaid.append("    }")
    for table in tables.values():
        fields = table["fields"]
        if not full:
            selected = [field for field in fields if " PK" in field["type"] or field.get("relation")]
            fields = selected or fields[:5]
        name = table["name"]
        label = schema_table_label(name, fields)
        lines.append(f'{dot_quote(name)} [shape=plain,label={label}];')
        mermaid.append(f"    {name} {{")
        for field in fields:
            kind = re.sub(r"[^A-Za-z0-9_\[\]-]", "_", field["type"].split()[0])
            key = " PK" if " PK" in field["type"] else " FK" if field.get("relation") else ""
            nullable = "nullable" if "nullable" in field["type"].lower() else "required"
            mermaid.append(f'        {kind} {field["name"]}{key} "{nullable}"')
        mermaid.append("    }")
    for table in tables.values():
        for field in table["fields"]:
            if not field.get("relation"):
                continue
            parent = field["relation"].split(".")[0]
            nullable = "nullable" in field["type"].lower()
            parent_count = "0..1" if nullable else "1"
            child_count = "0..1" if field.get("unique") else "0..N"
            label = f'{parent_count} → {child_count} · {field["name"]}'
            lines.append(f'{dot_quote(parent)} -> {dot_quote(table["name"])} [label={dot_quote(label)}];')
            parent_symbol = "o|" if nullable else "||"
            child_symbol = "|o" if field.get("unique") else "o{"
            mermaid.append(f'    {parent} {parent_symbol}--{child_symbol} {table["name"]} : "{field["name"]}"')
    lines.append("}")
    count = sum(len(table["fields"]) for table in tables.values())
    return {
        "id": "model-full" if full else "model",
        "title": "Every field & foreign key" if full else "Table relationships",
        "description": f"{count} fields across {len(tables)} proposed tables. Violet means new; green means existing. Nullable relationships are marked 0..1.",
        "dot": "\n".join(lines) + "\n", "mermaid": "\n".join(mermaid) + "\n",
        "canonical": "plan.json",
    }


def structured_graph(diagram: dict) -> tuple[str, str]:
    direction = diagram.get("direction", "TB")
    lines = graph_start(direction)
    mermaid = [f"flowchart {direction}"]
    nodes = diagram.get("nodes", [])
    ids = set()
    styles = {
        "new": "", "existing": ',fillcolor="#edf8f3",color="#a8d9c2"',
        "decision": ',shape=diamond,fillcolor="#fef4e7",color="#f0cc94"',
        "data": ',shape=cylinder,fillcolor="#e9effc",color="#bac9e7"',
        "result": ',fillcolor="#f7f7f8",color="#e2e5e9"',
    }
    for node in nodes:
        key = node.get("id", "")
        if not isinstance(key, str) or not IDENTIFIER.fullmatch(key) or key in ids:
            raise ValueError(f"Invalid or duplicate graph node id: {key!r}")
        ids.add(key)
        kind = {"input": "result", "state": "data"}.get(node.get("kind"), node.get("kind", "new"))
        if kind not in styles:
            raise ValueError(f"Unsupported graph node kind: {kind}")
        label = str(node.get("label", key))
        lines.append(f'{dot_quote(key)} [label={dot_quote(label)}{styles[kind]}];')
        encoded = escape(label, quote=True).replace("\n", "<br/>")
        mermaid.append(f'  {key}' + ('{"' + encoded + '"}' if kind == "decision" else '["' + encoded + '"]'))
    for edge in diagram.get("edges", []):
        source, target = edge.get("from"), edge.get("to")
        if source not in ids or target not in ids:
            raise ValueError(f"Graph edge references unknown node: {source!r} → {target!r}")
        label = str(edge.get("label", ""))
        dashed = bool(edge.get("dashed", False))
        lines.append(f'{dot_quote(source)} -> {dot_quote(target)} [label={dot_quote(label)}' + (",style=dashed" if dashed else "") + "];")
        arrow = "-.->" if dashed else "-->"
        encoded = escape(label, quote=True).replace("\n", "<br/>").replace("|", "&#124;")
        mermaid.append(f"  {source} {arrow}" + (f'|"{encoded}"|' if label else "") + f" {target}")
    lines.append("}")
    return "\n".join(lines) + "\n", "\n".join(mermaid) + "\n"


def load_diagrams(project: Path, plan: dict) -> list[dict]:
    path = local_path(project, "diagrams.json")
    if not path.exists():
        return [schema_diagram(plan, False), schema_diagram(plan, True)]
    diagrams = read_json(path)
    if not isinstance(diagrams, list) or not diagrams:
        raise ValueError("diagrams.json must be a nonempty array")
    result = []
    seen = set()
    for diagram in diagrams:
        if not isinstance(diagram, dict):
            raise ValueError("Each diagram must be an object")
        key = diagram.get("id", "")
        if not isinstance(key, str) or not DIAGRAM_ID.fullmatch(key) or key in seen:
            raise ValueError(f"Invalid or duplicate diagram id: {key!r}")
        seen.add(key)
        if "nodes" in diagram:
            dot, mermaid = structured_graph(diagram)
        else:
            dot, mermaid = diagram.get("dot"), diagram.get("mermaid")
            if not isinstance(dot, str) or not dot.strip() or not isinstance(mermaid, str):
                raise ValueError(f"{key} needs DOT and Mermaid text, or structured nodes/edges")
        result.append({"id": key, "title": str(diagram.get("title", key)),
                       "description": str(diagram.get("description", "")), "dot": dot, "mermaid": mermaid,
                       "canonical": diagram.get("canonical", "nodes" if "nodes" in diagram else "dot")})
    automatic = [schema_diagram(plan, full) for full in (False, True)
                 if ("model-full" if full else "model") not in seen]
    return automatic + result


def data_url(path: Path) -> str:
    mime = {".ttf": "font/ttf", ".md": "text/markdown", ".json": "application/json"}.get(path.suffix)
    mime = mime or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return f"data:{mime};base64,{base64.b64encode(path.read_bytes()).decode('ascii')}"


def safe_script(script: str) -> str:
    return re.sub(r"</script", lambda match: "<\\/" + match.group(0)[2:], script, flags=re.IGNORECASE).replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")


def bundle(out: Path) -> str:
    html = (out / "index.html").read_text(encoding="utf-8")
    css = (out / "styles.css").read_text(encoding="utf-8")
    def css_url(match):
        ref = match.group(2).strip()
        if ref.startswith(("data:", "#")):
            return match.group(0)
        asset = local_path(out, ref)
        if not asset.is_file():
            raise ValueError(f"Missing CSS asset: {ref}")
        return 'url("' + data_url(asset) + '")'
    css = re.sub(r"url\(\s*(['\"]?)(.*?)\1\s*\)", css_url, css, flags=re.IGNORECASE)
    if re.search(r"@import\b", css, re.IGNORECASE):
        raise ValueError("Viewer CSS must not use @import")
    def stylesheet(match):
        tag = match.group(0)
        if not re.search(r"\brel\s*=\s*['\"]stylesheet['\"]", tag, re.IGNORECASE):
            return tag
        href = re.search(r"\bhref\s*=\s*['\"]([^'\"]+)['\"]", tag, re.IGNORECASE)
        if not href or href.group(1) != "styles.css":
            raise ValueError("Viewer must declare its bundled stylesheet as styles.css")
        return "<style>" + css + "</style>"
    html = re.sub(r"<link\b[^>]*>", stylesheet, html, flags=re.IGNORECASE)
    declared = []
    def script_tag(match):
        src = re.search(r"\bsrc\s*=\s*['\"]([^'\"]+)['\"]", match.group(1), re.IGNORECASE)
        if not src:
            return match.group(0)
        name = src.group(1)
        if name not in SCRIPT_ORDER:
            raise ValueError(f"Undeclared viewer script: {name}")
        declared.append(name)
        return ""
    html = re.sub(r"<script\b([^>]*)>\s*</script\s*>", script_tag, html, flags=re.IGNORECASE)
    if tuple(declared) != SCRIPT_ORDER:
        raise ValueError("Viewer must declare scripts in order: " + ", ".join(SCRIPT_ORDER))
    scripts = "\n".join("<script>" + safe_script(local_path(out, name).read_text(encoding="utf-8")) + "</script>" for name in SCRIPT_ORDER)
    html = re.sub(r"</body\s*>", lambda _: scripts + "\n</body>", html, count=1, flags=re.IGNORECASE)
    for name in ("build-plan.md", "diagrams.md", "data-model.json"):
        pattern = re.compile(r'<a\b([^>]*?)\bhref=["\']' + re.escape(name) + r'["\']([^>]*)>', re.IGNORECASE)
        def download(match, filename=name):
            attrs = match.group(1) + match.group(2)
            attrs = re.sub(r'\s*\bdownload(?:\s*=\s*["\'][^"\']*["\'])?', "", attrs, flags=re.IGNORECASE)
            return '<a' + attrs + ' href="' + data_url(out / filename) + '" download="' + filename + '">'
        html = pattern.sub(download, html)
    return html


def build(project: Path, out: Path, node: str | None = None) -> dict:
    project, out = Path(project).expanduser().resolve(), Path(out).expanduser().resolve()
    if not project.is_dir():
        raise ValueError(f"Project directory not found: {project}")
    if project.is_relative_to(out) or PACKAGE.is_relative_to(out) or out.is_relative_to(PACKAGE):
        raise ValueError("Output must not overwrite the project or package source assets")
    if out.exists() and (not out.is_dir() or (any(out.iterdir()) and not (out / "build-info.json").is_file())):
        raise ValueError("Refusing to replace a nonempty directory that is not a product-plan build")
    plan = read_json(local_path(project, "plan.json"))
    checked = check_plan(plan)
    if not checked["ok"]:
        raise ValueError("Invalid plan: " + "; ".join(checked["errors"]))
    diagrams = load_diagrams(project, plan)
    executable = resolve_node(node)
    out.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{out.name}-build-", dir=out.parent))
    try:
        for name in ("index.html", "styles.css", "viewer.js"):
            source = local_path(VIEWER, name)
            if not source.is_file():
                raise ValueError(f"Missing package viewer asset: {source}")
            shutil.copyfile(source, stage / name)
        fonts = local_path(VIEWER, "fonts")
        if fonts.is_dir():
            for font in sorted(fonts.iterdir()):
                local_path(VIEWER, str(font.relative_to(VIEWER)))
                if font.is_file():
                    (stage / "fonts").mkdir(exist_ok=True)
                    shutil.copyfile(font, stage / "fonts" / font.name)
        prototype = local_path(project, "prototype.js")
        write(stage / "prototype.js", prototype.read_text(encoding="utf-8") if prototype.is_file() else "// This plan has no custom prototype.\n")
        shell = (stage / "index.html").read_text(encoding="utf-8")
        for token, value in metadata(plan).items():
            shell = shell.replace("{{" + token + "}}", escape(value, quote=True))
        if re.search(r"\{\{[A-Z_]+\}\}", shell):
            raise ValueError("Unresolved metadata token in viewer template")
        write(stage / "index.html", shell)
        write(stage / "data-model.json", json_text(plan))
        write(stage / "spec.js", "window.PLAN = " + json_text(plan).rstrip() + ";\n")
        manifest = [{k: v for k, v in diagram.items() if k != "dot"} for diagram in diagrams]
        write(stage / "diagrams/manifest.json", json_text(manifest))
        for diagram in diagrams:
            write(stage / "diagrams" / (diagram["id"] + ".dot"), diagram["dot"])
            write(stage / "diagrams" / (diagram["id"] + ".mmd"), diagram["mermaid"])
        write(stage / "diagrams.md", "# " + metadata(plan)["TITLE"] + " · diagrams\n\n" + "\n".join(diagram_markdown(diagrams)).rstrip() + "\n")
        write(stage / "build-plan.md", markdown_plan(plan, diagrams))
        rendered = subprocess.run([executable, str(PACKAGE / "scripts/render-diagrams.mjs"), str(stage)], capture_output=True, text=True)
        if rendered.returncode:
            raise ValueError("Diagram render failed: " + (rendered.stderr or rendered.stdout).strip())
        write(stage / "preview.html", bundle(stage))
        report = validate(stage)
        if not report["ok"]:
            raise ValueError("Build validation failed: " + "; ".join(report["errors"]))
        info = {"format": "product-plan-html/1", "counts": report["counts"],
                "files": sorted(str(path.relative_to(stage)) for path in stage.rglob("*") if path.is_file())}
        write(stage / "build-info.json", json_text(info))
        if out.exists():
            shutil.rmtree(out)
        stage.rename(out)
        return {"ok": True, "output": str(out), "preview": str(out / "preview.html"), "counts": report["counts"], "validation": report}
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("project", type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--node")
    args = parser.parse_args()
    try:
        result = build(args.project, args.out, args.node)
    except (OSError, ValueError, TypeError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
