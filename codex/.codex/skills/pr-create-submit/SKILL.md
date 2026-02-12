---
name: pr-create-submit
description: "Create a PR on top of the current Graphite stack without implementing product code: sync/restack, move to stack top, create a branch (empty-commit branch if no changes), submit, and update PR description from the repo template. Use when the user asks to create/update a PR branch and description only."
---

# pr-create-submit

## Workflow

### 1) establish clean stack context
- run `gt sync` and `gt restack` first.
- run `gt ls` and confirm current branch position in the stack.

### 2) move to top of stack
- move to the highest upstack branch before creating a new PR branch.
- prefer `gt up` until no further upstack branch exists.
- run `gt ls` again to confirm you are on stack top.

### 3) create the PR branch (no implementation)
- do not implement product code in this flow unless explicitly requested.
- create the new upstack branch with `gt create -m "<message>"`.
- if there are no working tree changes, still run `gt create -m "<message>"`; this creates an empty branch/commit.
- keep commit message concise and PR-oriented.

### 4) submit the branch/stack
- run `gt submit --stack --no-interactive` so the new branch gets a PR on top of the stack.
- if submit fails due to out-of-date stack metadata, rerun `gt sync`, then `gt restack`, then submit again.

### 5) update PR description from repository template
- locate template in this order:
  - `.github/pull_request_template.md`
  - `.github/PULL_REQUEST_TEMPLATE.md`
  - first matching file in `.github/pull_request_template/*.md`
- fill the template with branch-specific content:
  - objective
  - what changed (or explicitly: no product-code changes; branch/PR setup only)
  - checks run (if any)
  - follow-ups or risks
- update PR body using CLI (for example: `gh pr edit --body-file <file>`).
- if no template exists, use a structured fallback body with the same sections.

### 6) final verification output
- return:
  - created branch name
  - PR URL
  - whether it was empty-commit or code-change based
  - confirmation PR description was updated from template
  - any blockers

## Guardrails
- do not implement feature code in this workflow unless user explicitly asks.
- do not create a new root stack; keep the branch on top of the current stack.
- do not skip `gt sync` + `gt restack` before creation/submission.
- do not skip PR description update.
