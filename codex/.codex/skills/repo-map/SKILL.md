---
name: repo-map
description: "Map an unfamiliar repo quickly: find entrypoints, package boundaries, build/test configs, and key modules. Use when onboarding to a repo or locating where code lives."
---

# Repo Map

## Overview
Build a short, accurate map of a repo's structure and entrypoints to reduce time-to-context.

## Workflow

### 1) Find the root
- Prefer directories with .git, package.json, pyproject.toml, or Makefile.
- For monorepos, map the workspace root first.

### 2) Identify languages and frameworks
- Scan for package.json, pyproject.toml, requirements.txt, go.mod, Cargo.toml.
- Note frameworks via config files (tsconfig, nest-cli.json, next.config, etc.).

### 3) Locate entrypoints
- For Node/TS: package.json scripts, src/index.*, app.ts, main.ts.
- For Python: __main__.py, app.py, manage.py, FastAPI/Flask entry files.
- For services: look for server start scripts or Docker entrypoints.

### 4) Identify key modules
- Find feature directories, shared libs, and API layers.
- Note tests and fixtures locations.

### 5) Summarize
- Provide a concise map with key paths and notes.

## Output template (adapt as needed)
- Repo root
- Languages/frameworks
- Entrypoints
- Key modules
- Test locations
