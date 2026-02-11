---
name: pr-review-implement-submit
description: "Implement selected PR review feedback while enforcing repository coding/style guidelines, run repository checks/formatting, update the existing PR with Graphite, and reply on addressed review threads in a requested style. Use when the user gives numbered review decisions (listen/ignore) and wants execution end-to-end without opening a new PR."
---

# pr-review-implement-submit

## Workflow

### 1) confirm scope from review directions
- map user decisions to review threads: implement only selected points.
- keep ignored points untouched.
- if one point is "assess only", provide reasoning in review reply without code changes.

### 2) run guideline compliance gate before coding
- run the `$pr-style-guideline-review` workflow first on the current PR context.
- load and cite repository-local rules (`AGENTS.md`, lint/format/type configs, and nearby module patterns).
- identify any style/architecture violations in the selected implementation points before editing.
- if violations exist, align the implementation plan to those rules first; do not proceed with a conflicting plan.

### 3) implement selected code changes
- keep each change directly tied to a review point.
- avoid opportunistic refactors unless required for correctness.
- preserve atomicity of the current PR.
- follow rules from the guideline gate consistently during implementation.

### 4) run required checks by repo
- detect repo from current directory name.
- if in `traba-server-node`, run:
```bash
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use >/dev/null && yarn typecheck && yarn lint --fix --quiet && yarn format
```
- if in `traba`, run:
```bash
pnpm lint --fix --quiet && pnpm format
```
- if in `traba-app`, run:
```bash
yarn format
```
- if typecheck or lint fails, report exact failure and continue with what can be completed safely.

### 5) validate touched area
- run focused tests around changed modules when feasible.
- call out any unresolved global failures that are unrelated to the edited files.

### 6) restack after checks
- run `gt restack` after checks/tests complete and before submission.
- do not restack before checks, since restack can propagate changes upstack.

### 7) update the existing PR (not a new PR)
- stage only intended files.
- use Graphite update flow:
```bash
git add <intended-files>
gt modify -m "<concise message>"
export NVM_DIR="$HOME/.nvm" && . "$NVM_DIR/nvm.sh" && nvm use >/dev/null && gt submit --no-interactive
```
- if submit fails on hooks due node version, rerun with explicit `nvm use`.

### 8) reply on addressed review threads
- reply only to threads tied to selected points.
- style defaults when requested: all lowercase, succinct, kind, acknowledging.
- never start replies with AI-centric praise openers such as "great point", "you’re absolutely right", or similar.
- keep phrasing natural and context-aware; do not force canned lead-ins on every reply.
- vary opening style across replies: sometimes acknowledge briefly, sometimes go straight to the change.
- avoid repetitive openers (for example repeating "valid" / "this is true" across many comments).
- resolve addressed threads after replying.
- leave ignored threads unresolved.

### 9) final response format
- summarize implemented points.
- list checks run and outcomes.
- include PR update status.
- include any blockers or residual risks.

## Guardrails
- guideline compliance is mandatory: do not knowingly merge style/architecture violations against repo-local rules.
- do not create a new PR when user says update current PR.
- do not include unrelated staged files; verify latest commit file list.
- keep responses to reviewers factual and short.
- if shell interpolation can corrupt markdown in API calls, avoid backticks in inline review replies.
