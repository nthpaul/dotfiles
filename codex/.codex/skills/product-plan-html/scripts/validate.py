#!/usr/bin/env python3
"""Validate product-plan inputs and portable build outputs using the standard library."""

from __future__ import annotations

import argparse
import base64
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import xml.etree.ElementTree as ET


IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
RELATION = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\.([A-Za-z_][A-Za-z0-9_]*)$")
DIAGRAM_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
DOWNLOADS = ("build-plan.md", "diagrams.md", "data-model.json")


def existing_tables(plan: dict) -> dict[str, set[str] | None]:
    """Read explicit names; legacy descriptions may join existing names with '+'."""
    result: dict[str, set[str] | None] = {}
    for entry in [*plan.get("existing", []), *plan.get("existingTables", []), *plan.get("referenceTables", [])]:
        entry = {"name": entry} if isinstance(entry, str) else entry
        if not isinstance(entry, dict):
            continue
        names = entry.get("tables", re.split(r"\s*\+\s*|\s*,\s*", entry.get("name", "")))
        fields = entry.get("fields")
        field_names = None
        if isinstance(fields, list):
            field_names = {f.get("name", "") if isinstance(f, dict) else f for f in fields}
        for name in names:
            if isinstance(name, str) and IDENTIFIER.fullmatch(name):
                result[name] = field_names
    return result


def check_plan(plan: object) -> dict:
    errors: list[str] = []
    counts = {"tables": 0, "newTables": 0, "extendedTables": 0, "fields": 0, "relations": 0, "flows": 0, "steps": 0}
    if not isinstance(plan, dict):
        return {"ok": False, "errors": ["plan.json must contain an object"], "counts": counts}
    for key in ("tables", "existing", "flows", "decisions", "questions", "sources"):
        if key in plan and not isinstance(plan[key], list):
            errors.append(f"{key} must be an array")
    for key in ("document", "summary"):
        if not isinstance(plan.get(key, {}), dict):
            errors.append(f"{key} must be an object")
    selected = plan.get("schemaDiagrams", [])
    if (not isinstance(selected, list) or any(key not in ("model", "model-full") for key in selected)
            or len(selected) != len(set(selected))):
        errors.append("schemaDiagrams must be an array of unique model/model-full IDs")
    elif selected and not plan.get("tables"):
        errors.append("schemaDiagrams requires tables")
    if errors:
        return {"ok": False, "errors": errors, "counts": counts}
    tables: dict[str, set[str]] = {}
    for table in plan.get("tables", []):
        if not isinstance(table, dict):
            errors.append("Each table must be an object")
            continue
        name = table.get("name", "")
        if not isinstance(name, str) or not IDENTIFIER.fullmatch(name):
            errors.append(f"Invalid table name: {name!r}")
            continue
        if name in tables:
            errors.append(f"Duplicate table: {name}")
        storage = table.get("storage", "new")
        if storage not in ("new", "extension"):
            errors.append(f"{name}.storage must be new or extension")
        else:
            counts["extendedTables" if storage == "extension" else "newTables"] += 1
        fields = table.get("fields")
        if not isinstance(fields, list) or not fields:
            errors.append(f"{name}.fields must be a nonempty array")
            fields = []
        names: set[str] = set()
        for field in fields:
            if not isinstance(field, dict):
                errors.append(f"{name} contains a non-object field")
                continue
            field_name = field.get("name", "")
            if not isinstance(field_name, str) or not IDENTIFIER.fullmatch(field_name):
                errors.append(f"Invalid field name in {name}: {field_name!r}")
                continue
            if field_name in names:
                errors.append(f"Duplicate field: {name}.{field_name}")
            names.add(field_name)
            if not isinstance(field.get("type"), str) or not field["type"].strip():
                errors.append(f"{name}.{field_name}.type must be nonempty text")
            if "rule" in field and not isinstance(field["rule"], str):
                errors.append(f"{name}.{field_name}.rule must be text")
            if not isinstance(field.get("relation", ""), str):
                errors.append(f"{name}.{field_name}.relation must be text")
        tables[name] = names
        counts["fields"] += len(fields)
    counts["tables"] = len(plan.get("tables", []))
    targets = {**existing_tables(plan), **tables}
    for table in plan.get("tables", []):
        if not isinstance(table, dict):
            continue
        for field in table.get("fields", []) if isinstance(table.get("fields"), list) else []:
            if not isinstance(field, dict) or not field.get("relation"):
                continue
            relation = field["relation"]
            counts["relations"] += 1
            match = RELATION.fullmatch(relation) if isinstance(relation, str) else None
            label = f"{table.get('name')}.{field.get('name')}"
            if not match:
                errors.append(f"{label}: relation must be table.field, got {relation!r}")
                continue
            target, target_field = match.groups()
            if target not in targets:
                errors.append(f"{label}: undeclared relation target {target}; declare it in tables or existing")
            elif targets[target] is not None and target_field not in targets[target]:
                errors.append(f"{label}: relation target field {relation} does not exist")
    flow_ids: set[str] = set()
    for flow in plan.get("flows", []):
        if not isinstance(flow, dict):
            errors.append("Each flow must be an object")
            continue
        flow_id = flow.get("id", "")
        if not isinstance(flow_id, str) or not DIAGRAM_ID.fullmatch(flow_id):
            errors.append(f"Invalid flow id: {flow_id!r}")
            continue
        if flow_id in flow_ids:
            errors.append(f"Duplicate flow id: {flow_id}")
        flow_ids.add(flow_id)
        columns = flow.get("columns", ["Step", "Input", "Read / decide", "Write", "Output / next action"])
        if (not isinstance(columns, list) or not columns
                or not all(isinstance(value, str) and value.strip() for value in columns)):
            errors.append(f"{flow_id}.columns must be a nonempty array of text labels")
            continue
        if "owner" in flow and not isinstance(flow["owner"], str):
            errors.append(f"{flow_id}.owner must be text")
        steps = flow.get("steps")
        if not isinstance(steps, list):
            errors.append(f"{flow_id}.steps must be an array")
            continue
        counts["steps"] += len(steps)
        for index, step in enumerate(steps, 1):
            if not isinstance(step, list) or len(step) != len(columns) or not all(isinstance(v, str) for v in step):
                errors.append(f"{flow_id} step {index} needs {len(columns)} text columns matching its labels")
    counts["flows"] = len(plan.get("flows", []))
    return {"ok": not errors, "errors": errors, "counts": counts}


def local_path(root: Path, reference: str) -> Path:
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
        raise ValueError(f"Asset must be a relative local path: {reference}")
    path = (root / unquote(parsed.path)).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Asset escapes artifact directory: {reference}")
    return path


class ArtifactHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.assets: list[str] = []
        self.downloads: list[tuple[str, str]] = []
        self.inline_scripts: list[str] = []
        self.inline_styles: list[str] = []
        self._script: list[str] | None = None
        self._style: list[str] | None = None
        self.bad: list[str] = []
        self.structured = False
        self.title: list[str] = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "meta" and attrs.get("name") == "product-plan-format" and attrs.get("content") == "structured":
            self.structured = True
        if tag == "title":
            self._in_title = True
        if tag == "script" and "src" not in attrs:
            self._script = []
        if tag == "style":
            self._style = []
        for key in ("src", "poster"):
            if key in attrs:
                self.assets.append(attrs[key])
        if "srcset" in attrs:
            self.assets.extend(token.rstrip(",") for token in attrs["srcset"].split()
                               if not re.fullmatch(r"\d+(?:\.\d+)?[wx],?", token))
        if tag == "link" and attrs.get("rel") in ("stylesheet", "preload", "modulepreload", "icon"):
            self.assets.append(attrs.get("href", ""))
        if tag in ("image", "use"):
            for key in ("href", "xlink:href"):
                if key in attrs:
                    self.assets.append(attrs[key])
        if tag == "a" and "download" in attrs:
            self.downloads.append((attrs.get("download") or "", attrs.get("href", "")))
        if "style" in attrs:
            self.inline_styles.append(attrs["style"])

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag == "script" and self._script is not None:
            self.inline_scripts.append("".join(self._script))
            self._script = None
        if tag == "style" and self._style is not None:
            self.inline_styles.append("".join(self._style))
            self._style = None

    def handle_data(self, data):
        if self._in_title:
            self.title.append(data)
        if self._script is not None:
            self._script.append(data)
        if self._style is not None:
            self._style.append(data)


def _embedded_json(script: str, variable: str):
    match = re.match(rf"\s*window\.{variable}\s*=\s*(.*?)\s*;?\s*$", script, re.DOTALL)
    if not match:
        return None
    return json.loads(match.group(1))


def _svg_errors(text: str, label: str) -> list[str]:
    errors = []
    try:
        root = ET.fromstring(text)
        if root.tag.split("}")[-1] != "svg":
            errors.append(f"{label}: root element must be svg")
        box = [float(v) for v in re.split(r"[\s,]+", root.attrib.get("viewBox", "").strip())]
        if len(box) != 4 or not all(math.isfinite(v) for v in box) or box[2] <= 0 or box[3] <= 0:
            errors.append(f"{label}: valid positive viewBox required")
        for element in root.iter():
            tag = element.tag.split("}")[-1]
            if tag in ("script", "foreignObject"):
                errors.append(f"{label}: active SVG content is not allowed")
            if any(k.lower().startswith("on") for k in element.attrib):
                errors.append(f"{label}: event-handler attributes are not allowed")
            href = element.attrib.get("href", element.attrib.get("{http://www.w3.org/1999/xlink}href", ""))
            if href.lower().startswith(("javascript:", "vbscript:")):
                errors.append(f"{label}: active link protocols are not allowed")
            if tag in ("image", "use"):
                if href and not href.startswith(("#", "data:")):
                    errors.append(f"{label}: SVG depends on an external image or use reference")
    except (ET.ParseError, ValueError):
        errors.append(f"{label}: SVG could not be parsed or has an invalid viewBox")
    return errors


def _validate_bundle(html: str, plan=None, diagrams=None, downloads=None) -> dict:
    errors: list[str] = []
    counts: dict = {}
    parser = ArtifactHTML()
    parser.feed(html)
    errors.extend(parser.bad)
    for ref in parser.assets:
        if not ref.startswith(("data:", "#")):
            errors.append(f"Portable HTML has a runtime asset reference: {ref}")
    for css in parser.inline_styles:
        for ref in re.findall(r"url\(\s*['\"]?([^)'\"]+)['\"]?\s*\)", css, re.IGNORECASE):
            if not ref.startswith(("data:", "#")):
                errors.append(f"Portable CSS has a runtime asset reference: {ref}")
        if re.search(r"@import\b", css, re.IGNORECASE):
            errors.append("Portable CSS must not contain @import")
    structured = parser.structured or plan is not None
    if not structured:
        if not "".join(parser.title).strip():
            errors.append("Portable HTML needs a document title")
        for name, href in parser.downloads:
            if not href.startswith("data:"):
                errors.append(f"Portable download is not embedded: {name or href}")
        return {"ok": not errors, "errors": errors,
                "counts": {"downloads": len(parser.downloads), "inlineScripts": len(parser.inline_scripts)}}
    embedded_plan = None
    embedded_diagrams = None
    for script in parser.inline_scripts:
        parsed_plan = _embedded_json(script, "PLAN")
        parsed_diagrams = _embedded_json(script, "DIAGRAMS")
        if parsed_plan is not None:
            embedded_plan = parsed_plan
        if parsed_diagrams is not None:
            embedded_diagrams = parsed_diagrams
    model = check_plan(embedded_plan)
    errors.extend(model["errors"])
    counts.update(model["counts"])
    if plan is not None and embedded_plan != plan:
        errors.append("Bundled window.PLAN differs from data-model.json")
    if not isinstance(embedded_diagrams, list):
        errors.append("Bundled window.DIAGRAMS must be an array")
        embedded_diagrams = []
    if diagrams is not None and embedded_diagrams != diagrams:
        errors.append("Bundled window.DIAGRAMS differs from diagram manifest and SVGs")
    seen = set()
    for diagram in embedded_diagrams:
        if not isinstance(diagram, dict):
            errors.append("Bundled diagram must be an object")
            continue
        key = diagram.get("id", "")
        if not isinstance(key, str) or not DIAGRAM_ID.fullmatch(key) or key in seen:
            errors.append(f"Invalid or duplicate bundled diagram id: {key!r}")
            continue
        seen.add(key)
        if not isinstance(diagram.get("svg"), str):
            errors.append(f"{key}: bundled SVG is missing")
        else:
            errors.extend(_svg_errors(diagram["svg"], key))
    counts["diagrams"] = len(embedded_diagrams)
    declared = dict(parser.downloads)
    # Viewer template literals declare links that appear only after selecting a tab.
    for match in re.finditer(r"<a\b[^>]*\bdownload[^>]*>", html, re.IGNORECASE):
        anchor = ArtifactHTML()
        anchor.feed(match.group(0))
        declared.update(anchor.downloads)
    payloads = {}
    required_downloads = ["build-plan.md"]
    if embedded_diagrams:
        required_downloads.append("diagrams.md")
    if isinstance(embedded_plan, dict) and embedded_plan.get("tables"):
        required_downloads.append("data-model.json")
    for name in required_downloads:
        href = declared.get(name)
        if not href:
            errors.append(f"Missing declared source download: {name}")
            continue
        if not href.startswith("data:"):
            errors.append(f"Source download is not embedded: {name}")
            continue
        header, encoded = href.split(",", 1)
        payload = base64.b64decode(encoded, validate=True) if header.endswith(";base64") else unquote(encoded).encode()
        payloads[name] = payload
        if downloads is not None and payload != downloads.get(name):
            errors.append(f"Embedded download differs from source: {name}")
    if "data-model.json" in payloads and json.loads(payloads["data-model.json"]) != embedded_plan:
        errors.append("Embedded JSON download differs from bundled window.PLAN")
    counts["downloads"] = sum(name in declared for name in required_downloads)
    counts["inlineScripts"] = len(parser.inline_scripts)
    if counts["inlineScripts"] != 4:
        errors.append("Portable HTML must contain the four declared scripts and no injected script elements")
    return {"ok": not errors, "errors": errors, "counts": counts}


def validate(path: Path) -> dict:
    path = Path(path).resolve()
    errors: list[str] = []
    counts: dict = {}
    if path.is_file():
        try:
            return _validate_bundle(path.read_text(encoding="utf-8"))
        except (OSError, ValueError, TypeError) as exc:
            return {"ok": False, "errors": [f"Cannot validate portable HTML: {exc}"], "counts": counts}
    if not (path / "data-model.json").exists() and not (path / "build-info.json").exists():
        preview = path / "preview.html"
        if preview.is_file():
            return validate(preview)
    try:
        plan = json.loads((path / "data-model.json").read_text(encoding="utf-8"))
        model = check_plan(plan)
        errors.extend(model["errors"])
        counts.update(model["counts"])
    except (OSError, ValueError) as exc:
        return {"ok": False, "errors": [f"Cannot read data-model.json: {exc}"], "counts": counts}
    manifest = []
    try:
        manifest = json.loads((path / "diagrams/manifest.json").read_text(encoding="utf-8"))
        if not isinstance(manifest, list):
            raise ValueError("manifest must be an array")
        seen: set[str] = set()
        for diagram in manifest:
            if not isinstance(diagram, dict):
                errors.append("Diagram manifest entry must be an object")
                continue
            diagram_id = diagram.get("id", "")
            if not isinstance(diagram_id, str) or not DIAGRAM_ID.fullmatch(diagram_id):
                errors.append(f"Invalid diagram id: {diagram_id!r}")
                continue
            if diagram_id in seen:
                errors.append(f"Duplicate diagram id: {diagram_id}")
            seen.add(diagram_id)
            for suffix in ("dot", "mmd", "svg"):
                asset = local_path(path, f"diagrams/{diagram_id}.{suffix}")
                if not asset.is_file():
                    errors.append(f"Missing diagram file: {diagram_id}.{suffix}")
            svg = local_path(path, f"diagrams/{diagram_id}.svg")
            if svg.is_file():
                text = svg.read_text(encoding="utf-8")
                errors.extend(_svg_errors(text, diagram_id))
                if "svg" in diagram and diagram["svg"] != text:
                    errors.append(f"{diagram_id}: manifest SVG differs from downloadable SVG")
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"Cannot validate diagrams: {exc}")
    counts["diagrams"] = len(manifest)
    try:
        html = (path / "preview.html").read_text(encoding="utf-8")
        rendered_manifest = [
            {**item, "svg": local_path(path, f"diagrams/{item['id']}.svg").read_text(encoding="utf-8")}
            for item in manifest
            if isinstance(item, dict) and isinstance(item.get("id"), str) and DIAGRAM_ID.fullmatch(item["id"])
        ]
        downloads = {name: (path / name).read_bytes() for name in DOWNLOADS if (path / name).is_file()}
        bundle = _validate_bundle(html, plan, rendered_manifest, downloads)
        errors.extend(bundle["errors"])
        counts.update(bundle["counts"])
    except (OSError, ValueError, TypeError) as exc:
        errors.append(f"Cannot validate portable HTML: {exc}")
    outputs = ["index.html", "styles.css", "viewer.js", "prototype.js", "spec.js", "diagrams.js", "build-plan.md"]
    if manifest:
        outputs.append("diagrams.md")
    for name in outputs:
        if not (path / name).is_file():
            errors.append(f"Missing output: {name}")
    return {"ok": not errors, "errors": errors, "counts": counts}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    args = parser.parse_args()
    report = validate(args.artifact)
    print(json.dumps(report, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
