---
name: linear-ticket-work
description: Pick up a Linear engineering issue, start work on it, implement only the ticketed scope, run the repo-specific validation commands and targeted tests until they pass, and raise an atomic Graphite PR. Use when working a Linear ticket end to end from issue pickup through local verification, PR submission, and issue follow-up.
---

# Linear Ticket Work

Execute a Linear issue from pickup to PR using the workspace-standard engineering workflow.

## Workflow

### 1. Pick up the issue

1. Read the Linear issue completely.
2. Confirm the issue is scoped to one atomic PR.
3. Check dependencies before starting implementation.
4. For each prerequisite:
   - treat the prerequisite as satisfied if the ticket is already implemented
   - implementation is satisfied when either:
     - the prerequisite ticket is `In Progress`, `In Review`, or `Done`
     - an associated prerequisite PR already exists and is open or merged
   - block only when neither the ticket state nor the PR status shows the prerequisite has been implemented
5. Check the repo worktree for unrelated existing changes before editing.
6. If dependencies are satisfied and the issue is not already started:

```bash
linear issue start <ISSUE_ID>
```

7. Use the issue identifier in branch and PR context.

### 2. Build context

1. Inspect the repo before making changes.
2. Load repo-level authoring guidance before changing code:
   - open the repo root `AGENTS.md`
   - open the repo root `CLAUDE.md` if it exists
   - open the closest relevant `.cursor/BUGBOT.md` or `.cursor/BUGBOT-NITS.md` files for the paths you expect to touch
3. Treat `AGENTS.md` as the highest-priority repo instruction file. If `CLAUDE.md` or BUGBOT guidance conflicts with it, follow `AGENTS.md`.
4. Follow the ticket instructions exactly.
5. Keep scope limited to the issue unless expanding it is required for correctness.
6. If the ticket conflicts with existing code, source-of-truth docs, or another in-flight change, stop and surface the conflict.

### 3. Implement the ticket

1. Make only the code changes required for the issue.
2. Keep the change atomic so one PR can pass CI independently.
3. Preserve stackability if the work is part of a Graphite stack.
4. Do not combine unrelated contract work, migrations, runtime behavior, or rollout changes in one PR.

### 4. Run required repo checks before commit

Run the required commands for the repo. If any command fails, fix the problem and rerun the full repo command set until all required commands pass.

Repo matrix:

- `/Users/ple/projects/traba-server-node`

```bash
yarn lint:fix --quiet
yarn typecheck
yarn format
```

- `/Users/ple/projects/traba`

```bash
pnpm lint:fix --quiet
pnpm format
```

- `/Users/ple/projects/traba-app`

```bash
yarn format
```

- `/Users/ple/projects/traba-server-firebase`

```bash
yarn format
```

Rules:

- Do not create a commit or PR until the required repo commands pass.
- Run targeted tests for the changed area before committing.
- If formatting changes unrelated files, review them and keep only what belongs in the ticket.

### 5. Final review before commit

1. Review the final diff.
2. Remove unrelated changes.
3. Confirm the PR is still atomic and matches the ticket scope.
4. If the work is too broad for one PR, stop and escalate instead of committing.

### 6. Raise the PR with Graphite

After required repo checks and targeted tests pass:

1. Create the commit and branch with Graphite:

```bash
gt create
```

2. Submit with Graphite:

```bash
gt submit --no-interactive
```

3. Generate a PR description from the Linear ticket and the completed local validation.
4. Apply the PR description to the created PR. Because `gt submit --no-interactive` may skip body entry, update the PR body after submission if needed.
5. Use this standard PR body shape:

```md
## Summary

- What behavior changed in this PR.

## Testing

- Repo validation commands that passed.
- Targeted tests that passed.

## Linear

- <ISSUE_ID>
```

6. Build the PR description from the ticket scope and the actual checks you ran. Keep it short and factual.
7. If the branch is part of a stack, use the appropriate stack submit flow.
8. Because non-interactive Graphite submission may create a draft PR by default, mark the PR ready for review once all checks have passed, the diff is final, and the PR body is set.
9. Keep the PR in draft only when there is a concrete reason, such as:
   - the branch is intentionally mid-implementation
   - a prerequisite PR only needs to exist first
   - CI should run before requesting review
   - there is known follow-up work still landing on the branch

### 7. Link back to Linear

1. Ensure the PR references the Linear issue.
2. Attach the PR to the Linear issue if needed.
3. Leave a concise issue comment summarizing:
   - what changed
   - what repo checks were run
   - what targeted tests passed
   - the PR link

## Quality bar

- One Linear issue maps to one atomic PR.
- Required repo commands must pass before `gt create`.
- Targeted tests for the changed area must pass before `gt create`.
- The PR description should be populated from the Linear ticket before requesting review.
- If the PR is complete and validated, it should be ready for review rather than left in draft.
- Fix failures first; do not defer known lint, type, format, or test failures into CI.
- Do not submit a PR with known local validation failures.
- Do not expand scope beyond the ticket without a concrete reason.

## When to escalate

Escalate instead of forcing progress when:

- a prerequisite ticket has not been implemented yet
- there is no evidence of implementation via ticket state (`In Progress`, `In Review`, or `Done`) or an open or merged prerequisite PR
- the issue scope is too broad for one PR
- the repo validation commands are missing or broken
- the ticket instructions conflict with the codebase or source-of-truth docs
- the repo has unrelated worktree changes that cannot be safely separated from the ticket
