#!/usr/bin/env bash
# Prints the canonical filesystem path for a git worktree of this repository.
# Deterministic: same branch name -> same path. Safe to run before the worktree exists.
set -euo pipefail

usage() {
  echo "Usage: wt-path.sh [branch-name]" >&2
  echo "  Uses current branch when branch-name is omitted." >&2
  echo "  Env: TRABA_WORKTREES_ROOT (default: ~/.traba/worktrees)" >&2
  echo "  Env: TRABA_WORKTREE_REPO_SLUG (default: basename of git top-level)" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
fi

REPO_ROOT=$(git rev-parse --show-toplevel 2>/dev/null) || {
  echo "wt-path.sh: not inside a git repository" >&2
  exit 1
}

BRANCH=${1:-"$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD)"}
# Deterministic slug: / is the only char in ref names that is invalid or awkward in
# a single path segment; map to - so the path is stable and human-readable.
SLUG=$(printf '%s' "$BRANCH" | tr '/' '-')

ROOT=${TRABA_WORKTREES_ROOT:-"$HOME/.traba/worktrees"}
if [[ -n "${TRABA_WORKTREE_REPO_SLUG:-}" ]]; then
  REPO_SLUG=$TRABA_WORKTREE_REPO_SLUG
else
  REPO_SLUG=$(basename "$REPO_ROOT")
fi

printf '%s\n' "$ROOT/$REPO_SLUG/$SLUG"
