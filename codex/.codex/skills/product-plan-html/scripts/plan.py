#!/usr/bin/env python3
"""Build, inspect, preview and explicitly publish a portable product plan."""

import argparse
import functools
import hashlib
import http.server
import json
from pathlib import Path
import shutil
import subprocess
import sys
import zipfile

from capabilities import PACKAGE_ROOT, discover


def scaffold(destination, example=None):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Scaffold destination must be empty: {destination}")
    if example:
        source = PACKAGE_ROOT / "assets" / "examples" / example
        if not source.is_dir():
            raise ValueError(f"Unknown packaged example: {example}")
        shutil.copytree(source, destination, dirs_exist_ok=True)
    else:
        destination.mkdir(parents=True, exist_ok=True)
        plan = {
            "document": {"title": "Review requests", "pageTitle": "Product plan · Review requests",
                         "date": "Draft", "brand": "traba", "eyebrow": "PRODUCT PLAN",
                         "subtitle": "Illustrative starter. Replace with verified requirements.",
                         "sampleLabel": "Fictional sample data"},
            "summary": {"decision": "One request owns review state", "nextAction": "Replace this starter with the feature requirements.",
                        "reuse": [], "netNew": ["A request record and review command"], "buildSequence": []},
            "tables": [{"name": "review_requests", "purpose": "Illustrative review state.",
                        "fields": [{"name": "id", "type": "uuid PK", "rule": "Stable request identity.", "relation": ""},
                                   {"name": "status", "type": "text", "rule": "PENDING or APPROVED.", "relation": ""},
                                   {"name": "createdAt", "type": "timestamptz", "rule": "Creation instant.", "relation": ""}],
                        "constraints": ["A review command can approve only a pending request."], "relationships": "No external references in this starter."}],
            "referenceTables": [], "existing": [], "decisions": ["The backend owns review transitions."],
            "questions": ["Which actors can approve?"], "sources": [],
            "flows": [{"id": "review", "title": "Review a request", "summary": "An authorized decision changes one request.",
                       "steps": [["Approve", "Request ID and authenticated actor", "Load pending request and check permission", "Persist APPROVED and audit event", "Updated request projection"]]}]
        }
        diagrams = [{"id": "review", "title": "Review a request", "description": "Illustrative command flow.",
                     "nodes": [{"id": "input", "label": "Request + actor", "kind": "input"},
                               {"id": "check", "label": "Authorized and pending?", "kind": "decision"},
                               {"id": "write", "label": "Persist approval", "kind": "state"}],
                     "edges": [{"from": "input", "to": "check"}, {"from": "check", "to": "write", "label": "Yes"}]}]
        for name, value in [("plan.json", plan), ("diagrams.json", diagrams)]:
            (destination / name).write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    return {"project": str(destination), "example": example}


def publish(html, destination, executable):
    html = Path(html).expanduser().resolve()
    if html.suffix.lower() != ".html" or not html.is_file():
        raise ValueError("Publish requires an existing HTML file.")
    if not destination.startswith("/") or not destination.endswith(".html") or ".." in Path(destination).parts:
        raise ValueError("Relay destination must be an absolute library path ending in .html.")
    from validate import validate
    result = validate(html)
    if not result["ok"]:
        raise ValueError(f"Artifact validation failed: {result['errors']}")
    subprocess.run([executable, "library", "put", destination, str(html)], check=True)
    readback = html.with_name(html.stem + ".relay-readback.html")
    subprocess.run([executable, "library", "get", destination, "--out", str(readback)], check=True)
    if readback.read_bytes() != html.read_bytes():
        raise ValueError(f"Published readback differs. Inspect {readback}")
    return {"url": "https://relay.traba.work/library" + destination,
            "readback": str(readback), "sha256": hashlib.sha256(html.read_bytes()).hexdigest()}


def package(destination):
    destination = Path(destination).expanduser().resolve()
    if destination.is_relative_to(PACKAGE_ROOT):
        raise ValueError("Write the archive outside the installed skill.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(p for p in PACKAGE_ROOT.rglob("*") if p.is_file()
                   and "__pycache__" not in p.parts and p.suffix not in {".pyc", ".zip"}
                   and not p.name.startswith("."))
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            item = zipfile.ZipInfo("product-plan-html/" + path.relative_to(PACKAGE_ROOT).as_posix(), (2026, 1, 1, 0, 0, 0))
            item.compress_type = zipfile.ZIP_DEFLATED
            item.external_attr = 0o644 << 16
            archive.writestr(item, path.read_bytes())
    return {"archive": str(destination), "files": len(files), "bytes": destination.stat().st_size}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--standalone", action="store_true", help="Select bundled guidance instead of external skills")
    parser.add_argument("--skills-root", action="append", default=[], help="Additional skill root; repeatable")
    parser.add_argument("--tools", action="append", help="Available browser tool name; repeatable")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("detect")
    starter = commands.add_parser("scaffold")
    starter.add_argument("project")
    starter.add_argument("--example", choices=["injury-rtw"])
    builder = commands.add_parser("build")
    builder.add_argument("project")
    builder.add_argument("--out", required=True)
    builder.add_argument("--node", help="Node executable override")
    checker = commands.add_parser("validate")
    checker.add_argument("path")
    server = commands.add_parser("serve")
    server.add_argument("directory")
    server.add_argument("--port", type=int, default=8771)
    publisher = commands.add_parser("publish")
    publisher.add_argument("html")
    publisher.add_argument("--path", required=True, help="User-authorized Relay library destination")
    publisher.add_argument("--relay", help="Relay executable override")
    archiver = commands.add_parser("package")
    archiver.add_argument("zip")
    args = parser.parse_args()
    capabilities = discover(args.skills_root, args.standalone, args.tools)
    if args.command == "detect":
        result = capabilities
    elif args.command == "scaffold":
        result = scaffold(args.project, args.example)
    elif args.command == "build":
        from build import build
        node = args.node or capabilities["tools"]["node"]["path"]
        if not node:
            raise ValueError("Node is required for bundled Graphviz. Supply --node or use an existing Node runtime.")
        result = build(Path(args.project).expanduser().resolve(), Path(args.out).expanduser().resolve(), node)
        (Path(args.out).expanduser().resolve() / "capabilities.json").write_text(json.dumps(capabilities, indent=2) + "\n", encoding="utf-8")
        result["guidance"] = {"external": len(capabilities["skills"]) - len(capabilities["fallbacks"]),
                              "fallbacks": len(capabilities["fallbacks"])}
    elif args.command == "validate":
        from validate import validate
        result = validate(Path(args.path).expanduser().resolve())
    elif args.command == "serve":
        directory = Path(args.directory).expanduser().resolve()
        if not (directory / "preview.html").is_file():
            raise ValueError(f"No preview.html in {directory}")
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(directory))
        with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as httpd:
            print(f"http://127.0.0.1:{args.port}/preview.html", flush=True)
            httpd.serve_forever()
        return
    elif args.command == "publish":
        executable = args.relay or capabilities["tools"]["relay"]["path"]
        if not executable:
            raise ValueError("Relay CLI is unavailable. The local HTML is ready; publishing requires relay.")
        result = publish(args.html, args.path, executable)
    else:
        result = package(args.zip)
    print(json.dumps(result, indent=2))
    if result.get("ok") is False:
        raise SystemExit(1)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"product-plan-html: {error}", file=sys.stderr)
        raise SystemExit(1)
