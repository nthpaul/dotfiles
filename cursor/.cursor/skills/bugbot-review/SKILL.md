---
name: bugbot-review
description: Run Bugbot-guided PR or branch code review with deduped findings by combining scoped `BUGBOT.md` checks with a whole-diff pass. Use when reviewing a PR or branch with Bugbot guidance, or when the user asks for a high-signal review.
---

# Bugbot Review

Perform high-signal code review using layered `BUGBOT.md` guidance plus a global whole-diff pass.

## Workflow

### 1. Check branch-to-PR association first
- Determine whether the current branch has an associated PR (`gh pr view`).
- If found, capture PR metadata (`number`, `url`, `base`, `title`) and set scope to PR.
- If not found, set scope to `branch-only`.

### 2. Resolve review scope
- PR scope:
  - use `gh pr view` and `gh pr diff`
- Branch-only scope:
  - use `git diff <base>...HEAD`

### 3. Collect changed files
- Build a repo-relative changed-file list from the selected diff scope.

### 4. Discover Bugbot guidance
- Find all `BUGBOT.md` files.
- Keep relevant files when either condition is true:
  - path match: changed files are under that guidance directory subtree
  - topic match: guidance clearly applies to topics present in the PR or diff
- Keep matching ancestors when multiple guidance files apply.
- Include `.cursor/BUGBOT.md` when present.

### 5. Run parallel review passes
- One pass per relevant `BUGBOT.md`.
- One global whole-diff pass.

### 6. Aggregate and dedupe findings
- Dedup key:
  - `filePath`
  - `startLine`
  - `endLine`
  - normalized title
- Merge source tags for duplicates.

### 7. Output actionable findings only
- Include:
  - severity (`critical`, `high`, `medium`, `low`)
  - why it is a problem
  - path and line range
  - source (`path/to/BUGBOT.md` or `global-diff`)

### 8. Always report PR association status
- `Associated PR: #<number> (<url>)`, or
- `Associated PR: none (reviewed branch diff)`.

### 9. PR comments behavior
- For PR scope, default to posting inline GitHub review comments unless the user asks for chat-only output.
- Before posting, dedupe against existing open and resolved review threads plus prior PR-level comments.
- Findings exist:
  - post one inline comment per deduped finding, anchored to file and line
- No findings:
  - post one comment: `lgtm - bugbot review`
- Append this signature to every PR comment:
  - `left by /bugbot-review skill`

### 10. Branch-only behavior
- If there is no associated PR, skip PR comment posting and return chat findings only.

## Output format

```markdown
## Code Review

Found N issue(s).

1. [severity] Short title
   - Why: ...
   - Location: `path/to/file.ts` (Lx-Ly)
   - Source: `path/to/BUGBOT.md` or `global-diff`
```

If no findings, say:

`No issues found after Bugbot + whole-diff review.`

## Severity scale
- `critical`: likely outage, data loss, or security vulnerability
- `high`: strong chance of broken behavior for important flows
- `medium`: meaningful correctness or reliability risk with lower blast radius
- `low`: minor risk or edge-case issue with limited impact
