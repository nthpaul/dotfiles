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


def scaffold(destination, example=None, structured=False):
    destination = Path(destination).expanduser().resolve()
    if destination.exists() and any(destination.iterdir()):
        raise ValueError(f"Scaffold destination must be empty: {destination}")
    if example:
        source = PACKAGE_ROOT / "assets" / "examples" / example
        if not source.is_dir():
            raise ValueError(f"Unknown packaged example: {example}")
        shutil.copytree(source, destination, dirs_exist_ok=True)
    elif structured:
        destination.mkdir(parents=True, exist_ok=True)
        plan = {
            "document": {"title": "Product plan", "pageTitle": "Product plan",
                         "date": "Draft", "brand": "traba", "eyebrow": "PRODUCT PLAN",
                         "subtitle": "", "sampleLabel": "Proposed design"},
            "summary": {"decision": "State the proposed decision.",
                        "nextAction": "State what the reader should decide or do next."}
        }
        (destination / "plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    else:
        destination.mkdir(parents=True, exist_ok=True)
        from build import data_url
        html = (PACKAGE_ROOT / "assets/document.html").read_text(encoding="utf-8")
        faces = []
        for name, weight in (("Regular", 400), ("SemiBold", 600)):
            font = PACKAGE_ROOT / f"assets/viewer/fonts/Poppins-{name}.ttf"
            faces.append(f'@font-face {{ font-family:Poppins; font-weight:{weight}; font-style:normal; font-display:swap; src:url("{data_url(font)}") format("truetype"); }}')
        faces.append("/*\n" + (PACKAGE_ROOT / "assets/viewer/fonts/OFL.txt").read_text(encoding="utf-8") + "\n*/")
        (destination / "preview.html").write_text(html.replace("{{FONT_FACES}}", "\n".join(faces)), encoding="utf-8")
    return {"project": str(destination), "example": example, "format": "structured" if example or structured else "html"}


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
    starter_mode = starter.add_mutually_exclusive_group()
    starter_mode.add_argument("--example", choices=["injury-rtw"])
    starter_mode.add_argument("--structured", action="store_true", help="Start the optional JSON-based builder")
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
        result = scaffold(args.project, args.example, args.structured)
    elif args.command == "build":
        from build import build
        node = args.node or capabilities["tools"]["node"]["path"]
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
