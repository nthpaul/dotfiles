#!/usr/bin/env python3
"""Locate reusable guidance and local tools without changing installation state."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
TARGETS = (
    ("architecture", "architect", "pstack", "architecture.md"),
    ("architecture_principles", "principle-build-the-lever", "pstack", "architecture.md"),
    ("architecture_principles", "principle-model-the-domain", "pstack", "architecture.md"),
    ("architecture_principles", "principle-make-operations-idempotent", "pstack", "architecture.md"),
    ("architecture_principles", "principle-prove-it-works", "pstack", "architecture.md"),
    ("design", "traba-design", None, "design.md"),
    ("relay", "relay-design", None, "relay.md"),
)
CORE_READ_NAMES = {"architect", "principle-prove-it-works", "traba-design", "relay-design"}
PLATFORMS = ("codex", "cursor", "grok", "claude")


def _platform(tool_names):
    """Use the invocation path or callable catalog, never an installed app as host evidence."""
    for part in Path(sys.argv[0]).parts:
        if part in {"." + name for name in PLATFORMS}:
            return {"name": part[1:], "source": "invocation-path"}
    if any("cua_repl" in name for name in tool_names):
        return {"name": "codex", "source": "supplied-tool-catalog"}
    return {"name": None, "source": None}


def _platform_order(platform):
    name = platform["name"]
    return ([name] if name else []) + [item for item in PLATFORMS if item != name]


def _codex_home():
    return Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser()


def _name(path):
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        return None
    if not content.startswith("---\n"):
        return None
    frontmatter, separator, body = content[4:].partition("\n---")
    if not separator or not body.strip():
        return None
    match = re.search(r"^name:\s*([^\n]+?)\s*$", frontmatter, re.MULTILINE)
    if not match:
        return None
    return match.group(1).strip().strip("\"'")


def _is_pstack(path, name):
    if name.startswith(("pstack:", "pstack-plugin:")):
        return True
    return any(part in {"pstack", "pstack-plugin"} or part.startswith("pstack-plugin@")
               for part in path.parts)


def _version_key(path):
    version = next((part for part in reversed(path.parts)
                    if re.fullmatch(r"\d+(?:\.\d+)+(?:[-+].*)?", part)), None)
    if version is None:
        skills = next((parent for parent in [path, *path.parents] if parent.name == "skills"), None)
        if skills:
            for relative in [".cursor-plugin/plugin.json", ".claude-plugin/plugin.json"]:
                try:
                    version = json.loads((skills.parent / relative).read_text(encoding="utf-8")).get("version")
                except (OSError, ValueError):
                    continue
                if version:
                    break
    version = str(version or "0")
    return tuple(int(number) for number in re.findall(r"\d+", version.split("-")[0]))


def _skills_under(root):
    """Walk only a declared skill root; follow directory symlinks with cycle guards."""
    visited = set()
    pending = [Path(root).expanduser()]
    while pending:
        directory = pending.pop()
        try:
            resolved = directory.resolve(strict=True)
            if resolved in visited or not resolved.is_dir():
                continue
            visited.add(resolved)
            skill = directory / "SKILL.md"
            if skill.is_file():
                yield skill
                continue
            pending.extend(reversed(sorted(
                (child for child in directory.iterdir()
                 if child.is_dir() and not child.name.startswith(".")),
                key=lambda child: str(child),
            )))
        except (OSError, RuntimeError):
            continue


def _project_skill_roots(platform):
    home = Path.home().resolve()
    for directory in [Path.cwd(), *Path.cwd().parents]:
        if directory.resolve() == home:
            break
        for relative in ["." + name + "/skills" for name in _platform_order(platform)]:
            root = directory / relative
            if root.is_dir():
                yield root


def _plugin_skill_files(cache):
    """Inspect supported publisher/plugin/version layouts, not bundled vendor trees."""
    seen = set()
    roots = [root for pattern in ["*/skills", "*/*/skills", "*/*/*/skills"]
             for root in cache.glob(pattern)]
    for root in sorted(roots, key=lambda path: (_version_key(path), str(path)), reverse=True):
        try:
            resolved = root.resolve(strict=True)
        except (OSError, RuntimeError):
            continue
        if resolved not in seen:
            seen.add(resolved)
            yield from _skills_under(root)


def _skill_candidates(skills_roots, platform):
    configured = [Path(root).expanduser() for root in (skills_roots or [])]
    roots = [(root, "configured-root") for root in configured]
    roots.extend((root, "project-skills") for root in _project_skill_roots(platform))
    homes = {name: Path.home() / ("." + name) for name in PLATFORMS}
    homes["codex"] = _codex_home()
    for name in _platform_order(platform):
        roots.append((homes[name] / "skills", "active-skills"))
        if name == "cursor":
            roots.append((homes[name] / "skills-cursor", "active-skills"))
    caches = {"codex": [homes["codex"] / "plugins" / "cache"],
              "cursor": [homes["cursor"] / "plugins" / "cache", homes["cursor"] / "plugins" / "local"],
              "grok": [homes["grok"] / "installed-plugins"],
              "claude": [homes["claude"] / "plugins" / "cache"]}
    cache_roots = [root for name in _platform_order(platform) for root in caches[name]]
    seen_roots = set()
    candidates = []
    searched = []
    for root, source in roots + [(root, "plugin-cache") for root in cache_roots]:
        try:
            key = root.resolve()
        except (OSError, RuntimeError):
            continue
        if key in seen_roots:
            continue
        seen_roots.add(key)
        searched.append({"path": str(root), "source": source})
        files = list(_plugin_skill_files(root) if source == "plugin-cache" else _skills_under(root))
        for path in files:
            name = _name(path)
            if name:
                try:
                    resolved = path.resolve(strict=True)
                except (OSError, RuntimeError):
                    continue
                candidates.append({"name": name, "path": str(resolved),
                                   "discovered_path": str(path), "source": source})
    return candidates, searched


def _runtime_roots():
    roots = []
    explicit = os.environ.get("CODEX_RUNTIME_ROOT")
    if explicit:
        roots.append(Path(explicit).expanduser())
    for parent in [Path.home() / ".cache" / "codex-runtimes", _codex_home() / "runtimes"]:
        if parent.is_dir():
            roots.extend(sorted((child for child in parent.iterdir() if child.is_dir()), key=str))
    return roots


def _executable(name, relative_paths=(), extra=()):
    found = shutil.which(name)
    if found:
        return {"available": True, "path": str(Path(found).resolve()), "source": "PATH"}
    for path, source in extra:
        if path.is_file() and os.access(path, os.X_OK):
            return {"available": True, "path": str(path.resolve()), "source": source}
    for root in _runtime_roots():
        for relative in relative_paths:
            path = root / relative
            if path.is_file() and os.access(path, os.X_OK):
                return {"available": True, "path": str(path.resolve()), "source": "bundled-runtime"}
    return {"available": False, "path": None, "source": None}


def _viz(node):
    vendor = PACKAGE_ROOT / "assets" / "vendor"
    bundled_entry = vendor / "viz.js"
    try:
        metadata = json.loads((vendor / "vendor.json").read_text(encoding="utf-8"))
        digest = hashlib.sha256(bundled_entry.read_bytes()).hexdigest()
        if (metadata.get("name") == "@viz-js/viz" and metadata.get("version")
                and metadata.get("sha256") == digest):
            return {"available": True, "path": str(bundled_entry.resolve()),
                    "version": metadata["version"], "source": "bundled-asset"}
    except (OSError, ValueError):
        pass
    directories = []
    if node["path"]:
        node_root = Path(node["path"]).parent.parent
        directories.extend([node_root / "node_modules", node_root / "lib" / "node_modules"])
    for root in _runtime_roots():
        directories.extend([root / "dependencies" / "node" / "node_modules", root / "node_modules"])
    for modules in directories:
        package = modules / "@viz-js" / "viz"
        metadata = package / "package.json"
        entry = package / "dist" / "viz.js"
        if not metadata.is_file() or not entry.is_file():
            continue
        try:
            parsed = json.loads(metadata.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if parsed.get("name") == "@viz-js/viz":
            return {"available": True, "path": str(entry.resolve()),
                    "version": parsed.get("version"), "source": "local-package"}
    return {"available": False, "path": None, "version": None, "source": None}


def discover(skills_roots=None, standalone=False, tool_names=None):
    """Return verified guidance paths and capabilities; standalone selects packaged backups."""
    supplied = list(tool_names or [])
    platform = _platform(supplied)
    candidates, searched = ([], []) if standalone else _skill_candidates(skills_roots, platform)
    selected = []
    fallbacks = []
    for role, expected, scope, fallback_name in TARGETS:
        match = next((candidate for candidate in candidates
                      if candidate["name"].split(":")[-1] == expected
                      and (scope is None or _is_pstack(Path(candidate["path"]), candidate["name"])
                           or _is_pstack(Path(candidate["discovered_path"]), candidate["name"]))), None)
        if match:
            selected.append({"role": role, **match, "fallback": False, "reason": None})
        else:
            path = PACKAGE_ROOT / "references" / "fallbacks" / fallback_name
            if not path.is_file():
                raise FileNotFoundError(f"Required packaged fallback missing: {path}")
            reason = ("Standalone mode selects packaged guidance for reproducibility."
                      if standalone else f"No verified installed {scope + ' ' if scope else ''}{expected} skill found in declared roots.")
            entry = {"role": role, "name": expected, "path": str(path.resolve()),
                     "discovered_path": str(path), "source": "bundled-fallback",
                     "fallback": True, "reason": reason}
            selected.append(entry)
            fallbacks.append({"role": role, "name": expected, "path": entry["path"], "reason": reason})
    python = {"available": True, "path": str(Path(sys.executable).resolve()), "source": "running-runtime"}
    node = _executable("node", ["dependencies/node/bin/node", "bin/node"])
    relay = _executable("relay", extra=[(Path.home() / ".relay" / "bin" / "relay", "user-install")])
    browser_tools = [name for name in supplied if
                     ("cua_repl" in name and re.search(r"(?:__|\.|_)js$", name))
                     or re.search(r"(?:^|__|\.|_)browser_(?:navigate|snapshot|screenshot|click|open|tabs)$", name)]
    browser = {"available": bool(browser_tools), "tools": browser_tools,
               "source": "supplied-tool-catalog" if browser_tools else None,
               "reason": None if browser_tools else "Browser capability was not present in the supplied tool names; disk state is not evidence of browser access."}
    return {"platform": platform, "skills": selected,
            "read": list(dict.fromkeys(item["path"] for item in selected
                                       if item["name"].split(":")[-1] in CORE_READ_NAMES)),
            "fallbacks": fallbacks, "roots_searched": searched,
            "tools": {"python": python, "node": node, "viz": _viz(node), "relay": relay, "browser": browser}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--skills-root", action="append", default=[], help="Additional installed skill/catalog root; repeatable")
    parser.add_argument("--standalone", action="store_true", help="Use packaged guidance without external skill discovery")
    parser.add_argument("--tools", nargs="*", default=None, help="Available tool names; only these can establish browser availability")
    args = parser.parse_args()
    print(json.dumps(discover(args.skills_root, args.standalone, args.tools), indent=2))


if __name__ == "__main__":
    main()
