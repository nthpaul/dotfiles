#!/usr/bin/env bash
set -euo pipefail

base_branch="${1:-main}"

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

echo "== repo context =="
echo "repo_root: $repo_root"
echo "branch: $(git rev-parse --abbrev-ref HEAD)"
echo "base_branch: $base_branch"
if git rev-parse --verify "$base_branch" >/dev/null 2>&1; then
  merge_base="$(git merge-base HEAD "$base_branch")"
  echo "merge_base: $merge_base"
else
  echo "warning: base branch '$base_branch' not found locally"
fi

echo
echo "== guideline sources =="
find "$repo_root" -maxdepth 5 -name AGENTS.md -print | sed "s|$repo_root/||" || true
for f in package.json .eslintrc .eslintrc.js .eslintrc.cjs .eslintrc.json eslint.config.js eslint.config.mjs .prettierrc .prettierrc.js .prettierrc.cjs prettier.config.js prettier.config.cjs tsconfig.json; do
  if [[ -f "$f" ]]; then
    echo "$f"
  fi
done
if [[ -d .github/workflows ]]; then
  echo ".github/workflows/"
fi

echo
echo "== changed files =="
if git rev-parse --verify "$base_branch" >/dev/null 2>&1; then
  git diff --name-only "$base_branch"...HEAD
else
  git diff --name-only HEAD~1...HEAD
fi
