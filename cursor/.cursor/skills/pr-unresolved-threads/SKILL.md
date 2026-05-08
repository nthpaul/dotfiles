---
name: pr-unresolved-threads
description: >-
  List unresolved GitHub PR inline review threads for the current branch (trabapro/traba),
  with file and line, for triage and fixes.
---

# PR unresolved review threads

Use when you need **open (unresolved) inline review threads** on your PR—not every comment type.

## 1. Resolve PR number

```bash
PR="$(gh pr list --head "$(git branch --show-current)" --repo trabapro/traba --json number --jq '.[0].number')"
echo "$PR"
```

If empty, open a PR first or pass `--repo` explicitly.

## 2. Fetch all unresolved threads

GraphQL: `repository.pullRequest.reviewThreads`. Paginate until `pageInfo.hasNextPage` is false.

Pasteable helper (requires `gh` auth for `trabapro/traba`, Python 3):

```bash
pr-unresolved-threads() {
  local PR="${1:-$(gh pr list --head "$(git branch --show-current)" --repo trabapro/traba --json number --jq '.[0].number')}"
  [[ -n "$PR" ]] || { echo "No PR number" >&2; return 1; }
  python3 - "$PR" <<'PY'
import json, subprocess, sys

PR = sys.argv[1]
OWNER, NAME = "trabapro", "traba"

QUERY = """
query($owner: String!, $name: String!, $num: Int!, $after: String) {
  repository(owner: $owner, name: $name) {
    pullRequest(number: $num) {
      title
      reviewThreads(first: 100, after: $after) {
        pageInfo { hasNextPage endCursor }
        nodes {
          isResolved
          isOutdated
          comments(first: 1) {
            nodes {
              author { login }
              body
              path
              line
              originalLine
            }
          }
        }
      }
    }
  }
}
"""

def gql(after=None):
    args = [
        "gh", "api", "graphql",
        "-f", f"query={QUERY}",
        "-f", f"owner={OWNER}",
        "-f", f"name={NAME}",
        "-F", f"num={PR}",
    ]
    if after:
        args.extend(["-f", f"after={after}"])
    out = subprocess.check_output(args, text=True)
    return json.loads(out)

cursor = None
title_printed = False
while True:
    data = gql(cursor)
    pr = data["data"]["repository"]["pullRequest"]
    if pr is None:
        print("Pull request not found", file=sys.stderr)
        sys.exit(1)
    if not title_printed:
        print(f"PR #{PR}: {pr.get('title', '')}\n")
        title_printed = True
    rt = pr["reviewThreads"]
    for node in rt["nodes"]:
        if node.get("isResolved"):
            continue
        comments = (node.get("comments") or {}).get("nodes") or []
        c = comments[0] if comments else None
        if not c:
            continue
        path = c.get("path") or "(none)"
        line = c.get("line")
        if line is None:
            line = c.get("originalLine")
        if line is None:
            line = "(none)"
        author = (c.get("author") or {}).get("login") or "?"
        body = (c.get("body") or "").strip()
        print("---")
        print(f"File: {path}")
        print(f"Line: {line}")
        print(f"Author: {author}")
        print(f"Outdated thread: {node.get('isOutdated')}")
        print(f"Body:\n{body}\n")
    pi = rt["pageInfo"]
    if not pi.get("hasNextPage"):
        break
    cursor = pi.get("endCursor")
PY
}

pr-unresolved-threads
```

Optional first argument: explicit PR number, e.g. `pr-unresolved-threads 5418`.

## 3. Present format (when summarizing for humans)

Number threads **1..n**. For each:

1. **File** — `path`.
2. **Line** — `line`, else `originalLine`.
3. **Author** — first comment author.
4. **Summary** — short paraphrase (strip noisy HTML from bots if needed).
5. **Suggested fix** — concrete change or explicit deferral.

## 4. After addressing feedback

Re-run the helper; unresolved threads should disappear as reviewers resolve them or as you push fixes and they mark resolved.

## Limits

- **Review threads only** — not issue comments or the standalone review body unless you extend the query.
- Default **`trabapro/traba`** — edit `OWNER`/`NAME` in the script for other repos.
