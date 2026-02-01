---
name: repo-command-discovery
description: Discover test, lint, typecheck, build, and e2e commands in an unfamiliar repo. Use when commands are unknown or ambiguous, before running tests, or when CI fails and you need the right local commands. Works across Python, Node/TS, React, Nest, and mixed monorepos.
---

# Repo Command Discovery

## Overview
Find repo-specific commands with a portable POSIX script and confirm ambiguous cases with the user.

## Workflow

### 1) Choose a repo root
- Prefer the workspace root (with .git, package.json, pyproject.toml, or Makefile).
- For monorepos, run from the workspace root first.

### 2) Run discovery script (always)
- On skill invocation, immediately run the wrapper script.
- If no path is provided, use the current working directory.
- If the skill is symlinked into a repo at `.codex/skills`, use:
  - `sh .codex/skills/repo-command-discovery/scripts/run.sh [path]`
- Otherwise use the absolute path to this skill:
  - `sh <skills-root>/repo-command-discovery/scripts/run.sh [path]`
  - Common skills roots: `$CODEX_HOME/skills`, `~/.codex/skills`

### 3) Interpret output
- Use the highest-confidence commands first.
- If confidence is low or multiple options exist, ask the user to confirm.
- If multiple package.json files exist, ask which package or workspace to target.

### 4) Cache results
- Record the chosen commands in your notes and use them consistently.

## Script output
The script prints:
- ROOT, PACKAGE_MANAGER, CONFIDENCE
- FAST_TESTS, FULL_TESTS, LINT, TYPECHECK, BUILD, E2E
- NOTES about ambiguity or monorepo hints
